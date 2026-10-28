"""02 整形：2つのデータの説明変数どうしの相関（強く相関する組）を数える"""
import numpy as np, pandas as pd
from common import load_land, load_power, L_NUM, P_LABEL, L_LABEL, RES

rows = []
d = load_land()
c = d[L_NUM].corr(method="spearman")
lp, F = load_power()
c2 = lp[F].corr(method="spearman")
for name, cm, lab in [("地価", c, L_LABEL), ("電力需要", c2, P_LABEL)]:
    cols = list(cm.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = cm.iloc[i, j]
            if abs(r) >= 0.7:
                rows.append(dict(data=name, a=lab.get(cols[i], cols[i]), b=lab.get(cols[j], cols[j]), spearman=round(r, 3)))
    print(name, "n変数", len(cols), "|r|>=0.7 の組", sum(1 for r in rows if r["data"] == name))
out = pd.DataFrame(rows).sort_values(["data", "spearman"], key=lambda s: s.abs() if s.dtype != object else s, ascending=[True, False])
out.to_csv(RES / "corr_pairs.csv", index=False)
print(out.head(30).to_string(index=False))
print("地価 n=", len(d), "電力 n=", len(lp), lp.index.min(), lp.index.max())
