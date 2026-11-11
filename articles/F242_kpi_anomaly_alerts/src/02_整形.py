"""02 整形：1時間ごとの需要を1日の合計にし、特別な日（祝日・年末年始・お盆）の印をつける。"""
import pandas as pd
def daily(path):
    d = pd.read_csv(path, usecols=["date", "demand", "holiday", "holiday_name", "temp_mean", "temp_max", "temp_min"])
    g = d.groupby("date").agg(demand=("demand", "sum"), n=("demand", "size"), holiday=("holiday", "max"),
                              holiday_name=("holiday_name", "first"), tmean=("temp_mean", "first"),
                              tmax=("temp_max", "first"), tmin=("temp_min", "first")).reset_index()
    g = g[g.n == 24].drop(columns="n")
    g["date"] = pd.to_datetime(g["date"])
    md = g.date.dt.month * 100 + g.date.dt.day
    g["yearend"] = ((md >= 1229) | (md <= 103)).astype(int)
    g["obon"] = ((md >= 813) & (md <= 816)).astype(int)
    return g
for a in ["tokyo", "kansai"]:
    g = daily(f"data/raw/hourly_{a}.csv")
    g.to_csv(f"data/daily_power_{a}.csv", index=False)
    print(a, len(g), g.date.min().date(), g.date.max().date())
