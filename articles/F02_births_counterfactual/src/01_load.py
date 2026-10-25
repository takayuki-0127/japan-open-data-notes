"""e-Stat の確定数（月別出生数・届出月別婚姻件数、都道府県別の年次出生数）を整形して data/ に保存"""
import calendar
import pandas as pd
from common import RAW, DATA

rows = []
for kind, f in [("births", "births_monthly_2000_2025.csv"), ("marriages", "marriages_monthly_2000_2025.csv")]:
    d = pd.read_csv(RAW / f)
    assert (d.filter(like="m").sum(axis=1) == d.total).all(), f  # 月の合計＝年計
    long = d.melt(id_vars=["year", "total"], var_name="m", value_name=kind)
    long["month"] = long.m.str[1:].astype(int)
    rows.append(long[["year", "month", kind]])
m = rows[0].merge(rows[1], on=["year", "month"]).sort_values(["year", "month"])
m["date"] = pd.to_datetime(dict(year=m.year, month=m.month, day=1))
m["days"] = [calendar.monthrange(y, mo)[1] for y, mo in zip(m.year, m.month)]
m["births_per_day"] = m.births / m.days
m["marriages_12m"] = m.marriages.rolling(12).sum()   # 届出月のばらつき（縁起のよい日など）をならす
m[["date", "year", "month", "days", "births", "births_per_day", "marriages", "marriages_12m"]].to_csv(DATA / "monthly.csv", index=False)

p = pd.read_csv(RAW / "births_pref_annual.csv", dtype={"code": str})
p.melt(id_vars="code", var_name="year", value_name="births").astype({"year": int}).to_csv(DATA / "pref_annual.csv", index=False)
print(m.tail(3)); print("rows", len(m))
