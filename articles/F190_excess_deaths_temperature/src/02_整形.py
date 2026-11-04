"""全国・月別の死亡数と気温をつなぐ -> data/monthly_panel.csv"""
import calendar
import numpy as np, pandas as pd
from common import RAW, DATA

d = pd.read_csv(RAW / "deaths_monthly_F172.csv")[["year", "month", "deaths"]]
d = d[d.year >= 2000].copy()
d["days"] = [calendar.monthrange(y, m)[1] for y, m in zip(d.year, d.month)]

t = pd.read_csv(RAW / "jma_temp_monthly_national.csv")
w = t.pivot_table(index=["year", "month"], columns="el", values=["popw", "unw", "tokyo"]).reset_index()
w.columns = ["year", "month"] + [f"{a}_{b}" for a, b in w.columns[2:]]
w = w.rename(columns={"popw_mean": "t", "popw_mean_max": "tx", "popw_mean_min": "tn",
                      "unw_mean": "t_unw", "tokyo_mean": "t_tokyo", "unw_mean_max": "tx_unw",
                      "tokyo_mean_max": "tx_tokyo"})
w = w[["year", "month", "t", "tx", "tn", "t_unw", "tx_unw", "t_tokyo", "tx_tokyo"]]

j = pd.read_csv(RAW / "jma_mon_jpn_anomaly.csv")
j.columns = ["year"] + list(range(1, 13))
j = j.melt(id_vars="year", var_name="month", value_name="anom15")
j["month"] = j.month.astype(int)
j["anom15"] = pd.to_numeric(j.anom15, errors="coerce")

p = d.merge(w, on=["year", "month"], how="left").merge(j, on=["year", "month"], how="left")
# 平年（1991〜2020年の月平均）との差。気温は1995年からなので 1995〜2020 で代用
base = w[(w.year >= 1995) & (w.year <= 2020)].groupby("month")[["t", "tx", "tn", "t_unw", "t_tokyo", "tx_unw", "tx_tokyo"]].mean()
for c in base.columns:
    p[c + "_anom"] = p[c] - p.month.map(base[c])
# 前の月の気温差（冬の遅れ）
p = p.sort_values(["year", "month"]).reset_index(drop=True)
p["t_anom_lag1"] = p["t_anom"].shift(1)
p["per_day"] = p.deaths / p.days
p.to_csv(DATA / "monthly_panel.csv", index=False)
base.round(3).to_csv(DATA / "temp_base_1995_2020.csv")
print(p.shape, p.year.min(), p.year.max(), p[["t", "anom15"]].isna().sum().to_dict())
