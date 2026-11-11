"""架空の会社の KPI 10個 × 36か月（2023-01〜2025-12）と目標を作る（seed 278）"""
import numpy as np, pandas as pd
from common import DATA
rng = np.random.default_rng(278)
# 名前, 水準, 季節の振れ幅（比率）, 年の伸び, ノイズ, 向き(1:大きいほど良い), 単位
K = [("売上", 100.0, 0.18, 0.04, 0.03, 1, "百万円"), ("来店客数", 50.0, 0.15, 0.01, 0.03, 1, "千人"),
     ("客単価", 2000.0, 0.05, 0.03, 0.015, 1, "円"), ("新規会員数", 3.0, 0.25, 0.05, 0.08, 1, "千人"),
     ("ネット注文数", 12.0, 0.20, 0.10, 0.05, 1, "千件"), ("粗利率", 30.0, 0.02, 0.00, 0.01, 1, "%"),
     ("在庫日数", 25.0, 0.10, -0.02, 0.03, -1, "日"), ("廃棄率", 2.0, 0.12, -0.03, 0.06, -1, "%"),
     ("返品率", 1.5, 0.04, 0.00, 0.05, -1, "%"), ("人時売上", 8.0, 0.08, 0.02, 0.025, 1, "千円")]
ym = pd.period_range("2023-01", "2025-12", freq="M")
rows = []
for name, lvl, amp, g, sd, d, unit in K:
    phase = rng.uniform(0, 2 * np.pi)
    m = np.arange(len(ym))
    season = amp * (0.7 * np.sin(2 * np.pi * (m % 12) / 12 + phase) + 0.3 * np.sin(4 * np.pi * (m % 12) / 12 + 2 * phase))
    val = lvl * (1 + g) ** (m / 12) * (1 + season) * (1 + rng.normal(0, sd, len(m)))
    for i, p in enumerate(ym):
        rows.append((name, str(p), round(float(val[i]), 3), d, unit))
df = pd.DataFrame(rows, columns=["kpi", "ym", "value", "direction", "unit"])
# 目標：前年同月の実績 × (1 + 年の伸びの目標)。2023年は前年がないので目標なし
gt = {k[0]: k[3] + (0.01 if k[5] == 1 else -0.01) for k in K}
df["target"] = np.nan
for k, g in df.groupby("kpi"):
    t = g["value"].shift(12) * (1 + gt[k]) if g["direction"].iloc[0] == 1 else g["value"].shift(12) * (1 + gt[k])
    df.loc[g.index, "target"] = t.round(3)
df.to_csv(DATA / "kpi_monthly.csv", index=False)
print(df.shape)
