"""244：架空の小売チェーンの月次実績（5部門×24か月、予算つき）を乱数で作る。seed 244"""
import numpy as np, pandas as pd
from common import DATA
rng = np.random.default_rng(244)
dept = {"食品": 520, "日用品": 210, "衣料": 140, "家電": 90, "その他": 40}  # 月の売上の水準（百万円）
season = {"食品": [0, -3, 1, 0, 1, 0, 3, 4, -1, 0, 1, 8], "日用品": [0, -2, 3, 1, 0, 0, 1, 1, 0, 0, 0, 4],
          "衣料": [-6, -12, 4, 6, 2, -4, 5, -2, -6, 6, 8, 14], "家電": [2, -6, 10, -4, -2, 4, 12, 6, -6, -4, 4, 18],
          "その他": [0, -4, 6, 2, 0, -2, 4, 2, 0, -2, 2, 12]}  # %
trend = {"食品": 3.0, "日用品": 1.5, "衣料": -4.0, "家電": 2.0, "その他": 6.0}  # 年率%
rows = []
for t, ym in enumerate(pd.date_range("2024-01-01", "2025-12-01", freq="MS")):
    for d, lv in dept.items():
        base = lv * (1 + trend[d] / 100) ** (t / 12) * (1 + season[d][ym.month - 1] / 100)
        sd = {"食品": 0.015, "日用品": 0.02, "衣料": 0.06, "家電": 0.09, "その他": 0.08}[d]
        act = base * (1 + rng.normal(0, sd))
        bud = lv * (1 + trend[d] / 100 + 0.01) ** (t / 12) * (1 + season[d][ym.month - 1] / 100)  # 予算は少し強気
        rows.append({"dept": d, "ym": ym.date(), "actual": round(act, 1), "budget": round(bud, 1)})
pd.DataFrame(rows).to_csv(DATA / "monthly_dept.csv", index=False)
print(len(rows))
