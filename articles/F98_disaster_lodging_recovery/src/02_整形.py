"""02 整形：都道府県×月の縦長の表（date, pref, total, japanese, foreign）。全国は除く"""
import pandas as pd
from common import RAW, DATA
d = pd.read_csv(RAW / "lodging_pref_monthly_2011_2025.csv")
d = d[d.pref != "全国"].copy()
d["date"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1))
d = d[["date", "pref", "total", "japanese", "foreign"]].sort_values(["pref", "date"])
assert d.groupby("pref").size().eq(180).all() and d.pref.nunique() == 47
d.to_csv(DATA / "panel.csv", index=False)
print(d.shape)
