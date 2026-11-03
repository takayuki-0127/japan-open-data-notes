"""3つの月次系列に整える（data/monthly_series.csv）。
- power：東京エリアの月平均需要（GW）、月平均気温、冷房度日・暖房度日（日平均気温の 22℃超・14℃未満の合計）
- inbound：訪日外客数の総数（人）と主な国・地域。2020年2月〜2022年12月は入国制限の期間として分析から外す
- births：出生数と1日あたりの出生数
"""
import pandas as pd, numpy as np
from common import RAW, DATA

b = pd.read_csv(RAW / "births_monthly_2000_2025.csv")
bl = b.melt(id_vars=["year", "total"], var_name="m", value_name="births")
bl["month"] = bl.m.str[1:].astype(int)
bl["date"] = pd.to_datetime(dict(year=bl.year, month=bl.month, day=1))
bl["days"] = bl.date.dt.days_in_month
bl["births_per_day"] = bl.births / bl.days
births = bl[["date", "births", "births_per_day"]].sort_values("date")

h = pd.read_csv(RAW / "hourly_tokyo.csv", usecols=["date", "demand", "temp_mean"], parse_dates=["date"])
d = h.groupby("date").agg(demand=("demand", "mean"), temp=("temp_mean", "first")).reset_index()
d["cdd"] = (d.temp - 22).clip(lower=0)
d["hdd"] = (14 - d.temp).clip(lower=0)
d["date"] = d.date.dt.to_period("M").dt.to_timestamp()
power = d.groupby("date").agg(power_gw=("demand", lambda x: x.mean() / 1000), temp=("temp", "mean"),
                               cdd=("cdd", "sum"), hdd=("hdd", "sum"), ndays=("demand", "size")).reset_index()
power = power[power.ndays >= 28]

j = pd.read_csv(RAW / "jnto_monthly_2003_2026.csv")
j = j[(j.year <= 2025)]
j["date"] = pd.to_datetime(dict(year=j.year, month=j.month, day=1))
mk = {"総数": "inbound", "韓国": "inb_kr", "中国": "inb_cn", "台湾": "inb_tw", "香港": "inb_hk", "米国": "inb_us", "タイ": "inb_th", "豪州": "inb_au"}
inb = j[j.market.isin(mk)].pivot_table(index="date", columns="market", values="visitors").rename(columns=mk).reset_index()

df = births.merge(power, on="date", how="outer").merge(inb, on="date", how="outer").sort_values("date")
df.to_csv(DATA / "monthly_series.csv", index=False)
print(df.describe().T[["count", "min", "max"]])
