"""02 整形：F98 で整えた縦長の表をそのまま使う。ここでは形と欠けがないことだけ確かめる"""
from pathlib import Path
import pandas as pd
B = Path(__file__).resolve().parents[1]
d = pd.read_csv(B / "data/lodging_pref_monthly_2011_2025.csv", parse_dates=["date"])
assert d.pref.nunique() == 47 and d.date.nunique() == 180, (d.pref.nunique(), d.date.nunique())
assert d[["total", "japanese", "foreign"]].notna().all().all()
assert ((d.japanese + d.foreign - d.total).abs() <= 10).mean() > 0.99
print("47都道府県 × 180か月（2011-01〜2025-12）、欠けなし")
