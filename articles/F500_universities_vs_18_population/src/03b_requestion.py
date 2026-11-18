"""問い直し（結果を見てから足した）：大学が増えた分、1校あたりの学生は減ったのか。設置者別。
あわせて、大学の数が前の年より減った年を数える。"""
import json
import pandas as pd
from common import ROOT

R = ROOT / "results"
p = pd.read_csv(ROOT / "data" / "panel.csv", index_col="year")
B, E = 1992, 2025
rows = []
for y in range(1980, 2026):
    r = {"year": y, "pop18_per_univ": round(p.pop18[y] / p.univ_total[y], 1),
         "ent_univ_per_univ": round(p.ent_univ[y] / p.univ_total[y], 1)}
    for s in ["total", "national", "public", "private"]:
        r[f"students_per_univ_{s}"] = round(p[f"univ_students_{s}"][y] / p[f"univ_{s}"][y], 1)
    rows.append(r)
t = pd.DataFrame(rows).set_index("year")
t.to_csv(R / "per_school.csv")
q = {}
for c in t.columns:
    q[c] = {str(B): float(t.at[B, c]), str(E): float(t.at[E, c]), "change_pct": round(100 * (t.at[E, c] / t.at[B, c] - 1), 1),
            "max_year": int(t.loc[1980:2025, c].idxmax()), "max": float(t.loc[1980:2025, c].max())}
du = p.univ_total.loc[1980:2025].diff()
q["univ_decrease_years"] = [int(y) for y in du[du < 0].index]
q["univ_increase_years_since_1992"] = int((du.loc[1993:2025] > 0).sum())
q["univ_change_by_period"] = {f"{a}-{b}": int(p.univ_total[b] - p.univ_total[a]) for a, b in [(1992, 2000), (2000, 2010), (2010, 2020), (2020, 2025)]}
q["jc_change_by_period"] = {f"{a}-{b}": int(p.jc_total[b] - p.jc_total[a]) for a, b in [(1992, 2000), (2000, 2010), (2010, 2020), (2020, 2025)]}
json.dump(q, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(q, ensure_ascii=False, indent=0))
