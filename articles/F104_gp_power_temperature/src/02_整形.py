"""02 整形：日ごとの表に、GP に入れる列（年単位の時刻・曜日のダミー）を足し、週ごとの表も作る"""
import numpy as np
import pandas as pd
from common import DATA


def prep(name):
    d = pd.read_csv(DATA / name, parse_dates=["date"])
    d = d[["date", "area", "demand_gwh", "log_d", "temp_mean", "holiday", "dow", "obon", "nenmatsu", "gw", "covid", "offday"]].copy()
    d["t"] = (d.date - pd.Timestamp("2016-04-01")).dt.days / 365.25  # 年単位
    for k in range(1, 7):
        d[f"dow{k}"] = (d.dow == k).astype(int)
    return d


if __name__ == "__main__":
    for a, n in [("tokyo", "daily_tokyo.csv"), ("kansai", "daily_kansai.csv")]:
        d = prep(n)
        d.to_csv(DATA / f"gp_daily_{a}.csv", index=False)
        # 週ごと（月曜はじまり、7日そろう週だけ）
        w = d.assign(week=d.date.dt.to_period("W-SUN").dt.start_time).groupby("week").agg(
            n=("log_d", "size"), demand_gwh=("demand_gwh", "mean"), temp_mean=("temp_mean", "mean"),
            obon=("obon", "mean"), nenmatsu=("nenmatsu", "mean"), gw=("gw", "mean"), holiday=("holiday", "sum"),
            covid=("covid", "max")).reset_index()
        w = w[w.n == 7].copy()
        w["log_d"] = np.log(w.demand_gwh)
        w["t"] = (w.week - pd.Timestamp("2016-04-01")).dt.days / 365.25
        w.to_csv(DATA / f"gp_weekly_{a}.csv", index=False)
        print(a, len(d), d.date.min().date(), d.date.max().date(), "週", len(w))
