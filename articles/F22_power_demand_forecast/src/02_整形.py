"""02 整形：1時間ごとの需要（MW）と、日ごとの気象・暦の表を作る"""
import pandas as pd
import numpy as np
import holidays
from common import RAW, DATA

END = "2026-09-30"


def tepco():
    old = pd.read_csv(RAW / "tepco_area_2016_2023.csv", header=None, usecols=[0, 1, 2],
                      names=["date", "time", "v"], dtype=str)
    old["mw"] = old["v"].str.replace(",", "").astype(float) * 10  # 万kWh/時 → MW
    old["hour"] = old["time"].str.split(":").str[0].astype(int)
    old["ts"] = pd.to_datetime(old["date"]) + pd.to_timedelta(old["hour"], unit="h")
    new = pd.read_csv(RAW / "tepco_monthly_2024on_hourly.csv")
    new["ts"] = pd.to_datetime(new["date"]) + pd.to_timedelta(new["hour"], unit="h")
    new["mw"] = new["demand_mw"]
    s = pd.concat([old.loc[old.ts < "2024-02-01", ["ts", "mw"]], new[["ts", "mw"]]]).set_index("ts")["mw"]
    return s[~s.index.duplicated()].sort_index()


def kansai():
    k = pd.read_csv(RAW / "kansai_area_2024on.csv", header=None, usecols=[0, 1, 2],
                    names=["date", "time", "mw"])
    k["hour"] = k["time"].str.split(":").str[0].astype(int)
    k["ts"] = pd.to_datetime(k["date"]) + pd.to_timedelta(k["hour"], unit="h")
    return k.groupby("ts")["mw"].mean().round()


def weather():
    w = pd.read_csv(RAW / "jma_daily_tokyo_osaka.csv", na_values=["///", "×", ""])
    w["precip_mm"] = pd.to_numeric(w["precip_mm"].replace("--", "0"), errors="coerce")
    w["date"] = pd.to_datetime(w["date"])
    return w


def build(series, wx, area):
    idx = pd.date_range(series.index.min().normalize(), END + " 23:00", freq="h")
    d = pd.DataFrame({"demand": series.reindex(idx)})
    d["date"] = d.index.normalize()
    d["hour"] = d.index.hour
    w = wx.set_index("date")[["temp_mean", "temp_max", "temp_min", "humid_mean", "precip_mm"]]
    d = d.join(w, on="date")
    jp = holidays.Japan(years=range(2015, 2028))
    d["holiday"] = d["date"].map(lambda x: x in jp).astype(int)
    d["holiday_name"] = d["date"].map(lambda x: jp.get(x, ""))
    d["area"] = area
    return d


if __name__ == "__main__":
    wx = weather()
    t = build(tepco(), wx[wx.station == "tokyo"], "東京")
    k = build(kansai(), wx[wx.station == "osaka"], "関西")
    for name, d in [("hourly_tokyo.csv", t), ("hourly_kansai.csv", k)]:
        d.index.name = "ts"
        d.to_csv(DATA / name)
        print(name, len(d), "需要の欠け", int(d.demand.isna().sum()), "気温の欠け", int(d.temp_mean.isna().sum()),
              d.index.min(), d.index.max())
    # 古い形式と新しい形式のつなぎ目の確認（2024年1月と2月の平均）
    print(t.loc["2023-12":"2024-03", "demand"].resample("MS").mean().round())
