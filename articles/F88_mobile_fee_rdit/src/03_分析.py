"""時間の回帰不連続（RDiT）で、携帯料金の値下げ（2021年4月）による物価の段差を測る。"""
import json
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import DATA, RES, EVENT, EVENT2, SEED

s = pd.read_csv(DATA / "cpi_monthly.csv", index_col=0)
s.index = pd.PeriodIndex(s.index, freq="M")
w = pd.read_csv(DATA / "weights_2020base.csv", index_col=0).iloc[:, 0]
L = 100 * np.log(s)  # 対数×100（段差はおよそ％）

def rdit(series, event, pre=24, post=6, order=1, month_dummies=False, donut=0):
    ev = pd.Period(event, "M")
    y = series.loc[ev - pre: ev + post - 1].dropna()
    r = np.array([(p - ev).n for p in y.index], float)
    keep = ~((r < 0) & (r >= -donut))
    y, r = y[keep], r[keep]
    D = (r >= 0).astype(float)
    X = {"D": D}
    for k in range(1, order + 1):
        X[f"r{k}"] = r ** k; X[f"Dr{k}"] = D * r ** k
    X = pd.DataFrame(X, index=y.index)
    if month_dummies:
        md = pd.get_dummies(y.index.month, prefix="m", drop_first=True).astype(float)
        md.index = y.index; X = pd.concat([X, md], axis=1)
    X = sm.add_constant(X)
    m = sm.OLS(y.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    b, se = m.params["D"], m.bse["D"]
    return dict(jump=float(b), se=float(se), lo=float(b - 1.96 * se), hi=float(b + 1.96 * se), n=int(len(y)))

out = {}
# 1. 本体
for c in ["通信", "情報通信関係費", "総合", "生鮮食品を除く総合", "生鮮食品及びエネルギーを除く総合"]:
    out[f"base_{c}"] = rdit(L[c], EVENT)

# 2. 2回の段差を同時に（2019/4〜2022/6、共通の傾き）
y = L["通信"].loc["2019-04":"2022-06"]
r = np.array([(p - pd.Period(EVENT, "M")).n for p in y.index], float)
D1 = (y.index >= pd.Period(EVENT, "M")).astype(float); D2 = (y.index >= pd.Period(EVENT2, "M")).astype(float)
X = sm.add_constant(pd.DataFrame({"r": r, "D1": D1, "D2": D2}, index=y.index))
m2 = sm.OLS(y.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
out["two_breaks_通信"] = {k: [float(m2.params[k]), float(m2.bse[k])] for k in ["D1", "D2"]}
out["two_breaks_total_logpts"] = float(m2.params["D1"] + m2.params["D2"])

# 3. 総合・コアの前年比への寄与度（2020年基準のウエイト）
def contrib(item, total, wi, wt):
    return (wi / wt) * (s[item] - s[item].shift(12)) / s[total].shift(12) * 100
yoy = (s / s.shift(12) - 1) * 100
cc = pd.DataFrame({
    "総合_前年比": yoy["総合"], "通信_寄与_総合": contrib("通信", "総合", w["通信"], 10000),
    "コア_前年比": yoy["生鮮食品を除く総合"], "通信_寄与_コア": contrib("通信", "生鮮食品を除く総合", w["通信"], w["生鮮食品を除く総合"]),
    "通信_前年比": yoy["通信"]})
cc["コア_通信除く"] = cc["コア_前年比"] - cc["通信_寄与_コア"]
cc["総合_通信除く"] = cc["総合_前年比"] - cc["通信_寄与_総合"]
cc.loc["2018-01":].round(3).to_csv(RES / "contribution_monthly.csv")
p1 = cc.loc["2021-04":"2022-03"].mean(); p0 = cc.loc["2020-04":"2021-03"].mean(); p2 = cc.loc["2022-04":"2023-03"].mean()
out["contrib"] = {
    "2021/4-2022/3": p1.round(3).to_dict(), "2020/4-2021/3": p0.round(3).to_dict(), "2022/4-2023/3": p2.round(3).to_dict(),
    "min_通信_寄与_コア": [str(cc["通信_寄与_コア"].idxmin()), float(cc["通信_寄与_コア"].min())],
    "コア_2022-03": float(cc.loc["2022-03", "コア_前年比"]), "コア_2022-04": float(cc.loc["2022-04", "コア_前年比"]),
    "寄与_2022-03": float(cc.loc["2022-03", "通信_寄与_コア"]), "寄与_2022-04": float(cc.loc["2022-04", "通信_寄与_コア"]),
}
# 通信の段差から見込まれる総合の段差（ウエイト×指数の変化）
ev = pd.Period(EVENT, "M")
imp = w["通信"] / 10000 * (s.loc[ev, "通信"] - s.loc[ev - 1, "通信"]) / s.loc[ev - 1, "総合"] * 100
out["implied_総合_jump_pct"] = float(imp)
for c in ["生鮮食品を除く総合", "生鮮食品及びエネルギーを除く総合"]:
    out[f"implied_{c}_jump_pct"] = float(w["通信"] / w[c] * (s.loc[ev, "通信"] - s.loc[ev - 1, "通信"]) / s.loc[ev - 1, c] * 100)
out["level"] = {"通信_2021-03": float(s.loc["2021-03", "通信"]), "通信_2021-04": float(s.loc["2021-04", "通信"]),
                "通信_2021-10": float(s.loc["2021-10", "通信"]), "通信_2026-09": float(s.loc["2026-09", "通信"]),
                "総合_2021-03": float(s.loc["2021-03", "総合"]), "総合_2021-04": float(s.loc["2021-04", "総合"])}

# 4. プラセボ：値下げのない月を「境」にして同じ推定
pl = []
for p in pd.period_range("2003-01", "2020-10", freq="M"):
    a = rdit(L["通信"], str(p)); b = rdit(L["総合"], str(p)); c = rdit(L["生鮮食品及びエネルギーを除く総合"], str(p))
    pl.append({"month": str(p), "通信": a["jump"], "総合": b["jump"], "コアコア": c["jump"]})
pl = pd.DataFrame(pl); pl.to_csv(RES / "placebo.csv", index=False)
out["placebo"] = {
    "n": int(len(pl)),
    "通信_abs_max": float(pl["通信"].abs().max()), "通信_abs_max_month": pl.loc[pl["通信"].abs().idxmax(), "month"],
    "通信_p95_abs": float(pl["通信"].abs().quantile(0.95)),
    "総合_abs_p95": float(pl["総合"].abs().quantile(0.95)),
    "総合_top3": pl.reindex(pl["総合"].abs().sort_values(ascending=False).index).head(3).round(3).to_dict("records"),
    "総合_share_abs_ge_actual": float((pl["総合"].abs() >= abs(out["base_総合"]["jump"])).mean()),
    "コアコア_abs_p95": float(pl["コアコア"].abs().quantile(0.95)),
    "コアコア_share_abs_ge_actual": float((pl["コアコア"].abs() >= abs(out["base_生鮮食品及びエネルギーを除く総合"]["jump"])).mean()),
    "コアコア_top3": pl.reindex(pl["コアコア"].abs().sort_values(ascending=False).index).head(3).round(3).to_dict("records"),
    "通信_share_abs_ge_actual": float((pl["通信"].abs() >= abs(out["base_通信"]["jump"])).mean()),
}

# 5. 頑健性
rob = []
specs = [("本体（前24・後6か月、1次）", {}), ("前12か月", {"pre": 12}), ("前36か月", {"pre": 36}),
         ("後3か月", {"post": 3}), ("2次の多項式", {"order": 2}), ("月のダミー", {"month_dummies": True}),
         ("2021年3月を除く（ドーナツ）", {"donut": 1})]
for name, kw in specs:
    for c in ["通信", "総合", "生鮮食品を除く総合", "生鮮食品及びエネルギーを除く総合"]:
        rr = rdit(L[c], EVENT, **kw); rr.update(spec=name, series=c); rob.append(rr)
rr = rdit(L["情報通信関係費"], EVENT); rr.update(spec="情報通信関係費で測る", series="通信"); rob.append(rr)
rob = pd.DataFrame(rob); rob.round(4).to_csv(RES / "robustness.csv", index=False)
out["robust_range"] = {c: [float(rob[rob.series == c].jump.min()), float(rob[rob.series == c].jump.max())] for c in ["通信", "総合", "生鮮食品を除く総合", "生鮮食品及びエネルギーを除く総合"]}
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])
