"""架空のチェーン（店×部門×日）の POS の書き出し CSV を作る（seed 279）。
実際の書き出しに多い形にする：BOM つき UTF-8、金額は「1,234」のような桁区切りつきの文字。"""
import csv, numpy as np, pandas as pd
from common import DATA
rng = np.random.default_rng(279)
stores = [f"S{i:02d}" for i in range(1, 10)]  # S09 は 2025-10 に開いた新しい店
depts = ["食品", "日用品", "衣料", "家電", "その他"]
base = {"食品": 900, "日用品": 300, "衣料": 200, "家電": 150, "その他": 60}  # 千円/日
size = {s: rng.uniform(0.7, 1.4) for s in stores}  # 店の大きさ（月によらず同じ）
for ym, days in [("2025-09", 30), ("2025-10", 31)]:
    rows = []
    for s in stores:
        if s == "S09" and ym == "2025-09":
            continue
        for d in depts:
            for day in range(1, days + 1):
                v = base[d] * size[s] * rng.lognormal(0, 0.15)
                rows.append([s, d, f"{ym}-{day:02d}", f"{int(round(v * 1000)):,}", int(rng.poisson(v / 2.5))])
    with open(DATA / f"pos_{ym}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["店", "部門", "日付", "売上", "客数"]); w.writerows(rows)
    print(ym, len(rows))
