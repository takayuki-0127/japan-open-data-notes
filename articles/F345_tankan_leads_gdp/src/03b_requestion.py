"""問い直し（結果を見てから足した）。
Q：大きな落ち込みの期を除くと、ΔDI を足した改善は、最新の GDP では17.5%なのに、1次速報では3.3%だった。
   ΔDI は「あとで直された分」（最新 − 1次速報）と関係があるのか。つまり、DI は1次速報より、直されたあとの GDP に近い動きをしているのか。
結果は results/requestion.json と results/requestion_revisions.csv。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "panel_quarterly.csv")
c = "TK99F0000601GCQ00000"
d["dDI"] = d[c] - d[c].shift(1)
d["rev"] = d["gdp_latest"] - d["gdp_first"]
CRISIS = {(2008, 4), (2009, 1), (2009, 2), (2020, 1), (2020, 2), (2020, 3), (2020, 4)}
d["crisis"] = [(y, q) in CRISIS for y, q in zip(d.year, d.q)]
s = d.dropna(subset=["rev", "dDI", "gdp_first"])
s[["year", "q", "gdp_first", "gdp_latest", "rev", "dDI", "crisis"]].to_csv(R / "requestion_revisions.csv", index=False)
out = {}
for lab, q in [("all", s), ("excl_crisis", s[~s.crisis])]:
    X = sm.add_constant(q[["gdp_first", "dDI"]])
    fit = sm.OLS(q["rev"], X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    out[lab] = {"n": int(len(q)), "corr_rev_dDI": round(float(np.corrcoef(q.rev, q.dDI)[0, 1]), 3),
                "coef_dDI": round(float(fit.params["dDI"]), 4), "se_dDI": round(float(fit.bse["dDI"]), 4), "p_dDI": round(float(fit.pvalues["dDI"]), 4),
                "coef_first": round(float(fit.params["gdp_first"]), 4), "p_first": round(float(fit.pvalues["gdp_first"]), 4),
                "mean_abs_rev": round(float(q.rev.abs().mean()), 3),
                "corr_first_dDI": round(float(np.corrcoef(q.gdp_first, q.dDI)[0, 1]), 3), "corr_latest_dDI": round(float(np.corrcoef(q.gdp_latest, q.dDI)[0, 1]), 3)}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
