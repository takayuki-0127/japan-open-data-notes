"""問い直し（結果を見てから足した）：2020→2025年に小さな町村ほど1,000人あたりの職員が増えたのは、職員が増えたからか、人口が減ったからか。
規模別に、1,000人あたり（加重）の変化を、職員数の変化と人口の変化に分ける（対数の差）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
c = pd.read_csv(R / "change_2020_2025.csv", index_col=0)
rows = []
for s, q in c.iterrows():
    ds = np.log(1 + q.staff_change_pct / 100); dp = np.log(1 + q.pop_change_pct / 100)
    tot = ds - dp
    rows.append({"size": s, "per1000_change_pct": round(100 * (np.exp(tot) - 1), 2), "share_from_pop_decline_pct": round(100 * (-dp) / tot, 1),
                 "share_from_staff_pct": round(100 * ds / tot, 1)})
t = pd.DataFrame(rows).set_index("size")
t.to_csv(R / "requestion_decomposition.csv")
(R / "requestion.json").write_text(json.dumps({s: {k: float(v) for k, v in q.items()} for s, q in t.iterrows()}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(t)
