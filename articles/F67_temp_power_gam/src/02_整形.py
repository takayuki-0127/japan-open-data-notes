"""02 整形：1時間ごとの需要を日ごとの合計（GWh）にし、暦の情報を付ける"""
import pandas as pd
import numpy as np
from common import RAW, DATA


def daily(name):
    h = pd.read_csv(RAW / name, parse_dates=["ts", "date"])  # .csv.gz
    g = h.groupby("date").agg(demand_gwh=("demand", lambda s: s.sum() / 1000), n=("demand", "size"),
                              peak_mw=("demand", "max"),
                              temp_mean=("temp_mean", "first"), temp_max=("temp_max", "first"),
                              temp_min=("temp_min", "first"), humid=("humid_mean", "first"),
                              precip=("precip_mm", "first"), holiday=("holiday", "first"),
                              area=("area", "first")).reset_index()
    g = g[g.n == 24].copy()
    g["dow"] = g.date.dt.dayofweek
    g["year"] = g.date.dt.year
    g["fy"] = np.where(g.date.dt.month >= 4, g.year, g.year - 1)
    g["month"] = g.date.dt.month
    md = g.date.dt.month * 100 + g.date.dt.day
    g["obon"] = ((md >= 810) & (md <= 820)).astype(int)
    g["nenmatsu"] = ((md >= 1228) | (md <= 104)).astype(int)
    g["gw"] = ((md >= 429) & (md <= 506)).astype(int)
    g["offday"] = ((g.dow >= 5) | (g.holiday == 1)).astype(int)
    g["covid"] = ((g.date >= "2020-04-01") & (g.date <= "2021-09-30")).astype(int)
    g["temp_lag1"] = g.temp_mean.shift(1)
    g["log_d"] = np.log(g.demand_gwh)
    return g.dropna(subset=["temp_mean", "temp_lag1"])


if __name__ == "__main__":
    for src, out in [("hourly_tokyo.csv.gz", "daily_tokyo.csv"), ("hourly_kansai.csv.gz", "daily_kansai.csv")]:
        d = daily(src)
        d.to_csv(DATA / out, index=False)
        print(out, len(d), d.date.min().date(), d.date.max().date(), round(d.demand_gwh.mean(), 1))
