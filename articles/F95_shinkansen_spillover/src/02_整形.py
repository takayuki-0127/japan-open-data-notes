"""02 整形：都道府県×月の長い表（date, pref, total, japanese, foreign）"""
import pandas as pd
from common import RAW, DATA
d = pd.read_csv(RAW / "lodging_pref_monthly_2011_2025.csv")
d = d[d.pref != "全国"].copy()
# 「17石川県」→「石川」：先頭の番号と、都・府・県を外す（北海道はそのまま）
d["pref"] = d.pref.str.replace(r"^\d+", "", regex=True).str.replace(r"(都|府|県)$", "", regex=True)
d["date"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1))
d = d[["date", "pref", "total", "japanese", "foreign"]].sort_values(["pref", "date"])
assert d.groupby("pref").size().nunique() == 1 and d.pref.nunique() == 47
d.to_csv(DATA / "monthly_pref.csv", index=False)
print(d.shape, d.date.min().date(), d.date.max().date())
