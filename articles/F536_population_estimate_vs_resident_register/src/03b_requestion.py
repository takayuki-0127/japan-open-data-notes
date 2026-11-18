"""03b_requestion.py（問い直し、結果を見てから足した）
都道府県のずれ（住民基本台帳が人口推計より少ない県・多い県）は、15〜29歳の若い人のずれでどこまで説明できるか。
あわせて頑健性：日本人だけの都道府県のずれ、按分しない比べ方。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
A = pd.read_csv(R / "age_gap.csv")
P = pd.read_csv(R / "pref_gap.csv")
NAT = pd.read_csv(R / "national_gap.csv")
out = {}
rows = []
for t in [2020, 2024]:
    a = A[(A["year"] == t) & (A["pref"] > 0)].copy()
    a["diff"] = a["juki_oct"] - a["suikei"]
    w = a.pivot_table(index=["pref", "name", "region"], columns="age", values="diff").reset_index()
    g = a.pivot_table(index="pref", columns="age", values="gap_pct")
    w["young_15_29"] = w[["15-19", "20-24", "25-29"]].sum(axis=1)
    w["other"] = w["total"] - w["young_15_29"]
    w["year"] = t
    w["gap_total_pct"] = g["total"].values
    w["gap_20_24_pct"] = g["20-24"].values
    rows.append(w[["year", "pref", "name", "region", "total", "young_15_29", "other", "gap_total_pct", "gap_20_24_pct"]])
    neg = w[w["total"] < 0]
    out[str(t)] = dict(
        corr_total_vs_20_24=round(float(np.corrcoef(w["gap_total_pct"], w["gap_20_24_pct"])[0, 1]), 3),
        n_same_sign_young_total=int((np.sign(w["young_15_29"]) == np.sign(w["total"])).sum()),
        juki_less_prefs=neg["name"].tolist(),
        juki_less_young_share=round(float(neg["young_15_29"].sum() / neg["total"].sum()), 3),
        juki_less_young_persons=int(neg["young_15_29"].sum()), juki_less_total_persons=int(neg["total"].sum()))
Y = pd.concat(rows, ignore_index=True).round(3)  # レビューで直した：図4の点が0.1刻みに丸まらないよう3桁に
Y.to_csv(R / "requestion_young.csv", index=False)

# 頑健性
jp = P[P["kind"] == "japanese"]
rob = {
    "japanese_n_juki_more": {str(t): int((jp[jp["year"] == t]["gap_pct"] > 0).sum()) for t in [2014, 2020, 2024]},
    "japanese_juki_less": {str(t): jp[(jp["year"] == t) & (jp["gap_pct"] < 0)]["name"].tolist() for t in [2020, 2024]},
    "noint_national_total_pct": {str(int(r.year)): float(r.gap_noint_total_pct) for r in NAT.itertuples()},
}
out["robustness"] = rob
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
