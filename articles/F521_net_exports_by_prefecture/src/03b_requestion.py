"""問い直し：移出入が大きく赤字の県は、外から稼いでいないのか。
県の外で働く人や、県外の資産から入る所得（域外からの要素所得・純）を足すと、どうなるか。2019〜2023年度の平均。"""
import json, pathlib
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "pref_year.csv", dtype={"code": str})
g = d[(d.year >= 2019) & (d.year <= 2023)].copy()
g["nx"] = 100 * g.netexp / g.gdp_exp
g["fi"] = 100 * g.factor_income / g.gdp_exp
g["both"] = g.nx + g.fi
P = g.groupby(["code", "pref"], as_index=False)[["nx", "fi", "both"]].mean().sort_values("code")
P.to_csv(R / "requestion_factor_income.csv", index=False, float_format="%.3f")
r_all = stats.pearsonr(P.nx, P.fi)[0]
neg = P[P.nx < -5]
out = {"question": "移出入が赤字の県は、県外で働いたり県外の資産から得る所得で補っているか",
       "r_nx_fi": round(float(r_all), 3),
       "n_nx_below_minus5": int(len(neg)),
       "n_fi_positive_among_them": int((neg.fi > 0).sum()),
       "prefs_fi_over5": P[P.fi > 5].pref.tolist(),
       "fi_over5_nx_mean": round(float(P[P.fi > 5].nx.mean()), 2),
       "fi_over5_both_mean": round(float(P[P.fi > 5].both.mean()), 2),
       "tokyo_fi": round(float(P[P.pref == "東京都"].fi.iloc[0]), 2),
       "n_both_positive": int((P.both > 0).sum()),
       "sd_nx": round(float(P.nx.std()), 2), "sd_both": round(float(P.both.std()), 2)}
m = json.loads((R / "main.json").read_text(encoding="utf-8"))
m["requestion"] = out
(R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(out); print(P.round(1).to_string())
