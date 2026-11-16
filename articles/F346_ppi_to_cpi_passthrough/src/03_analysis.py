"""段階ごとの伝わり方：ずらし相関、分布ラグ回帰（12か月の累積）、2021〜23年の山の時期。results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "prices_monthly.csv", index_col=0)
d.index = pd.PeriodIndex([f"{i // 100}-{i % 100:02d}" for i in d.index], freq="M")
TAX = [pd.Period(p, "M") for p in ["1989-04", "1997-04", "2014-04", "2019-10"]]
mom = 100 * np.log(d).diff()
yoy = 100 * (d / d.shift(12) - 1)
main = {}


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def peak_lag(up, down, start="1980-01", end="2022-04", maxlag=24, src=yoy):
    s = src.loc[start:end]
    cs = []
    for k in range(0, maxlag + 1):
        a = s[up].shift(k); b = s[down]
        ok = a.notna() & b.notna()
        cs.append(np.corrcoef(a[ok], b[ok])[0, 1])
    k = int(np.argmax(cs))
    return k, cs


CHAIN = [("素原材料", "中間財"), ("中間財", "最終財_消費財"), ("最終財_消費財", "CPI_工業製品")]
xc_rows = []
lags = {}
for up, down in CHAIN:
    k, cs = peak_lag(up, down)
    lags[f"{up}→{down}"] = {"peak_lag_months": k, "corr_at_peak": r(cs[k]), "corr_lag0": r(cs[0])}
    for kk, c in enumerate(cs):
        xc_rows.append({"pair": f"{up}→{down}", "lag": kk, "corr": c})
k, cs = peak_lag("素原材料", "CPI_工業製品")
lags["素原材料→CPI_工業製品（直接）"] = {"peak_lag_months": k, "corr_at_peak": r(cs[k]), "corr_lag0": r(cs[0])}
for kk, c in enumerate(cs):
    xc_rows.append({"pair": "素原材料→CPI_工業製品（直接）", "lag": kk, "corr": c})
pd.DataFrame(xc_rows).round(4).to_csv(R / "crosscorr_yoy_1980_2022.csv", index=False)
main["peak_lags_1980_2022"] = lags
main["sum_chain_lags"] = int(sum(lags[f"{u}→{v}"]["peak_lag_months"] for u, v in CHAIN))


def dl(y, x, start="1980-01", end="2022-04", L=12, tax=True, month_dummies=True):
    s = mom.loc[start:end]
    X = pd.DataFrame({f"x{k}": s[x].shift(k) for k in range(L + 1)})
    if tax:
        for t in TAX:
            X[f"tax{t}"] = (s.index == t).astype(float)
    if month_dummies:
        for m in range(2, 13):
            X[f"m{m}"] = (s.index.month == m).astype(float)
    df = pd.concat([s[y].rename("y"), X], axis=1).dropna()
    df = df.loc[:, (df != 0).any(axis=0)]
    fit = sm.OLS(df["y"], sm.add_constant(df.drop(columns="y"))).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    names = [f"x{k}" for k in range(L + 1)]
    b = fit.params[names]; V = fit.cov_params().loc[names, names]
    cum = float(b.sum()); se = float(np.sqrt(np.ones(len(names)) @ V.values @ np.ones(len(names))))
    path = np.cumsum(b.values)
    return {"cum": r(cum), "se": r(se), "ci95": [r(cum - 1.96 * se), r(cum + 1.96 * se)], "n": int(fit.nobs), "contemp": r(b.iloc[0]),
            "cum_by_lag": [r(v) for v in path]}


pt = {}
for x in ["最終財_消費財", "中間財", "素原材料"]:
    pt[x] = dl("CPI_工業製品", x)
pt["最終財_消費財→最終財（参考：消費財の上流）"] = dl("最終財_消費財", "中間財")
pt["中間財←素原材料"] = dl("中間財", "素原材料")
main["passthrough_1980_2022_cpi_industrial"] = pt
pd.DataFrame({k: v["cum_by_lag"] for k, v in pt.items()}).to_csv(R / "dl_cumulative_paths.csv")

# 頑健性
rob = {}
for lab, kw in {"1980-1999": dict(start="1980-01", end="1999-12"), "2000-2022": dict(start="2000-01", end="2022-04"),
                "L6": dict(L=6), "L18": dict(L=18), "no_tax_dummy": dict(tax=False)}.items():
    rob[lab] = {"消費財→CPI工業製品": dl("CPI_工業製品", "最終財_消費財", **kw)["cum"], "素原材料→CPI工業製品": dl("CPI_工業製品", "素原材料", **kw)["cum"]}
rob["CPI生鮮除く財"] = {"消費財→": dl("CPI_生鮮除く財", "最終財_消費財")["cum"], "素原材料→": dl("CPI_生鮮除く財", "素原材料")["cum"]}
for lab, (st, en) in {"1980-1999": ("1980-01", "1999-12"), "2000-2022": ("2000-01", "2022-04")}.items():
    rob[f"peak_lags_{lab}"] = {f"{u}→{v}": peak_lag(u, v, start=st, end=en)[0] for u, v in CHAIN}
main["robust"] = rob

# 2015〜2026：ステージ別の前年同月比の山（2021〜2024年の間）
win = yoy.loc["2021-01":"2024-12"]
peaks = {}
for c in ["ステージ1_財", "ステージ2_財", "ステージ3_財", "ステージ4_財", "最終需要_財", "CPI_生鮮除く財", "CPI_工業製品", "CPI_食料工業製品", "最終需要_食料品"]:
    p = win[c].idxmax()
    peaks[c] = {"peak": str(p), "yoy_at_peak": r(win[c].max(), 1)}
main["peaks_2021_2024"] = peaks
def mdiff(a, b):
    pa, pb = pd.Period(peaks[a]["peak"], "M"), pd.Period(peaks[b]["peak"], "M")
    return int((pb - pa).n)
main["peak_gap_stage1_to_cpi_goods_months"] = mdiff("ステージ1_財", "CPI_生鮮除く財")
main["peak_gap_stage1_to_final_months"] = mdiff("ステージ1_財", "最終需要_財")
yoy.loc["2016-01":"2026-09", ["ステージ1_財", "ステージ2_財", "ステージ3_財", "ステージ4_財", "最終需要_財", "CPI_生鮮除く財", "CPI_工業製品"]].round(3).to_csv(R / "yoy_fdid_2016_2026.csv")
# 2015〜2026 のずらし相関（ステージ1→CPI生鮮除く財）
k, cs = peak_lag("ステージ1_財", "CPI_生鮮除く財", start="2016-01", end="2026-09")
main["fdid_peak_lag_stage1_to_cpi"] = {"lag": k, "corr": r(cs[k])}
k, cs = peak_lag("最終需要_財", "CPI_生鮮除く財", start="2016-01", end="2026-09")
main["fdid_peak_lag_final_to_cpi"] = {"lag": k, "corr": r(cs[k])}
yoy.loc["1980-01":"2022-04", ["素原材料", "中間財", "最終財_消費財", "CPI_工業製品"]].round(3).to_csv(R / "yoy_stages_1980_2022.csv")

main["hypotheses"] = {
    "H1": {"sum_lags": main["sum_chain_lags"], "verdict": "支持" if main["sum_chain_lags"] >= 6 else "外れ"},
    "H2": {"cum": pt["最終財_消費財"]["cum"], "verdict": "支持" if 0.5 <= pt["最終財_消費財"]["cum"] <= 1.5 else "外れ"},
    "H3": {"cum": pt["素原材料"]["cum"], "verdict": "支持" if pt["素原材料"]["cum"] < 0.2 else "外れ"},
    "H4": {"gap": main["peak_gap_stage1_to_cpi_goods_months"], "verdict": "支持" if main["peak_gap_stage1_to_cpi_goods_months"] >= 6 else "外れ"},
}
with open(R / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in main.items()}, ensure_ascii=False, indent=0)[:6000])
