"""問い直し（結果を見てから足した）。
Q：時期のずれは小さい（前年同月比の相関は0〜1か月のずれで最大）のに、素原材料からの伝わり方は小さい（12か月で0.045）。
   値上がりは段階を下るごとに「薄まる」のか。2021〜23年の局面で、段階ごとの前年同月比の山の高さを比べる。
   あわせて、最終需要の財 → CPI 生鮮食品を除く財 の伝わり方が、2016〜2020年と2021〜2026年で違うかを見る。
結果は results/requestion.json と results/requestion_dl_periods.csv。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "prices_monthly.csv", index_col=0)
d.index = pd.PeriodIndex([f"{i // 100}-{i % 100:02d}" for i in d.index], freq="M")
mom = 100 * np.log(d).diff(); yoy = 100 * (d / d.shift(12) - 1)
win = yoy.loc["2021-01":"2024-12"]
st = ["ステージ1_財", "ステージ2_財", "ステージ3_財", "ステージ4_財", "最終需要_財", "CPI_生鮮除く財"]
amp = {c: round(float(win[c].max()), 1) for c in st}
ratio = {f"{a}→{b}": round(amp[b] / amp[a], 3) for a, b in zip(st[:-1], st[1:])}
# 段階ごとの「上がった幅」：2020年平均から2024年平均への上昇率
lvl = {c: round(float(100 * (d.loc["2024-01":"2024-12", c].mean() / d.loc["2020-01":"2020-12", c].mean() - 1)), 1) for c in st}


def dl(y, x, start, end, L=12):
    s = mom.loc[start:end]
    X = pd.DataFrame({f"x{k}": s[x].shift(k) for k in range(L + 1)})
    X["tax"] = (s.index == pd.Period("2019-10", "M")).astype(float)
    for m in range(2, 13):
        X[f"m{m}"] = (s.index.month == m).astype(float)
    df = pd.concat([s[y].rename("y"), X], axis=1).dropna()
    df = df.loc[:, (df != 0).any(axis=0)]
    fit = sm.OLS(df["y"], sm.add_constant(df.drop(columns="y"))).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    names = [f"x{k}" for k in range(L + 1)]
    cum = float(fit.params[names].sum()); V = fit.cov_params().loc[names, names].values
    se = float(np.sqrt(np.ones(L + 1) @ V @ np.ones(L + 1)))
    return {"cum": round(cum, 3), "ci95": [round(cum - 1.96 * se, 3), round(cum + 1.96 * se, 3)], "n": int(fit.nobs)}


rows = []
for lab, (a, b) in {"2016-2020": ("2016-01", "2020-12"), "2021-2026": ("2021-01", "2026-09"), "2016-2026": ("2016-01", "2026-09")}.items():
    rr = dl("CPI_生鮮除く財", "最終需要_財", a, b)
    rows.append({"period": lab, **rr})
dlp = pd.DataFrame(rows)
dlp.to_csv(R / "requestion_dl_periods.csv", index=False)
out = {"peak_yoy_2021_2024": amp, "peak_ratio_next_over_prev": ratio, "level_rise_2020_to_2024_pct": lvl,
       "dl_final_goods_to_cpi_goods_ex_fresh": dlp.set_index("period").to_dict(orient="index")}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
