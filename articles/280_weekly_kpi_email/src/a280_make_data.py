"""架空の会社の週次 KPI（2025年の52週）と、集計が毎週月曜に終わる時刻を作る（seed 280）"""
import numpy as np, pandas as pd
from common import DATA
rng = np.random.default_rng(280)
weeks = pd.date_range("2025-01-06", periods=52, freq="W-MON")
k = {"売上（百万円）": 120, "客数（千人）": 60, "ネット注文（千件）": 9, "新規会員（人）": 800}
rows = []
for name, lvl in k.items():
    v = lvl * (1 + 0.15 * np.sin(2 * np.pi * np.arange(52) / 52 + 1)) * rng.lognormal(0, 0.04, 52)
    rows += [(w.date().isoformat(), name, round(float(x), 1)) for w, x in zip(weeks, v)]
pd.DataFrame(rows, columns=["week_start", "kpi", "value"]).to_csv(DATA / "weekly_kpi.csv", index=False)
# 集計が終わる時刻（月曜、時）：ふだんは 6:30 前後（ばらつき 18分）。ときどき前のシステムが遅れて数時間ずれる
# 遅れる週の割合は 10% と置いた（架空の前提。図3で 5%・20% も試す）
ready = 6.5 + rng.normal(0, 0.3, 52)
late = rng.random(52) < 0.10
ready[late] += rng.uniform(1, 5, late.sum())
pd.DataFrame({"week_start": weeks.date, "ready_hour": ready.round(3), "late": late}).to_csv(DATA / "ready_time.csv", index=False)
print(late.sum(), "late weeks")
