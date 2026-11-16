"""問い直し（結果を見てから足した）：
ラグ6か月では時給は効かず、ラグ12か月でだけ正で有意だった。人件費は食材より遅れて効くのか。
食料工業製品はラグ3か月に固定し、時給のラグを0〜24か月で動かして、係数の形を見る。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
m = pd.read_csv(RES / "monthly_yoy.csv", index_col=0)
r3 = lambda x: round(float(x), 3)
rows = []
for L in range(0, 25, 3):
    d = pd.DataFrame({"y": m.y_cpi_eatout, "food": m.y_cpi_processed_food.shift(3), "wage": m.y_wage_restaurant.shift(L), "tax": m.tax})
    d = d.loc[2010 * 12:2026 * 12 + 8]; d = d[~d.tax.astype(bool)].dropna()
    r = sm.OLS(d.y, sm.add_constant(d[["food", "wage"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    rows.append(dict(wage_lag=L, n=int(r.nobs), b_wage=r3(r.params["wage"]), lo=r3(r.conf_int().loc["wage", 0]), hi=r3(r.conf_int().loc["wage", 1]),
                     p_wage=r3(r.pvalues["wage"]), b_food=r3(r.params["food"]), r2=r3(r.rsquared)))
t = pd.DataFrame(rows); t.to_csv(RES / "requestion_wage_lags.csv", index=False)
best = t.loc[t.b_wage.idxmax()]
out = dict(max_b_wage=r3(best.b_wage), max_lag=int(best.wage_lag), max_p=r3(best.p_wage), n_sig=int((t.p_wage < 0.05).sum()),
           sig_lags=[int(x) for x in t[t.p_wage < 0.05].wage_lag], b_food_range=[r3(t.b_food.min()), r3(t.b_food.max())])
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False)); print(t.to_string())
