"""2026年10月の東京エリアの1時間値と日別値を、F22・F92 と同じ形で作る（共通の関数）"""
from pathlib import Path
import pandas as pd
import holidays

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT.parent
RAW = ROOT / "data" / "raw"
LAST_DAY = "2026-10-28"   # 24時間がそろう最後の日


def oct_hourly():
    t = pd.read_csv(RAW / "tepco_eria_jukyu_202610_30min.csv")
    t["hour"] = t["time"].str.split(":").str[0].astype(int)
    t["ts"] = pd.to_datetime(t["date"]) + pd.to_timedelta(t["hour"], unit="h")
    s = t.groupby("ts")["mw"].mean().round()
    s = s[s.index <= LAST_DAY + " 23:00"]
    w = pd.read_csv(RAW / "jma_daily_tokyo_202610.csv", parse_dates=["date"])
    idx = pd.date_range("2026-10-01", LAST_DAY + " 23:00", freq="h")
    d = pd.DataFrame({"demand": s.reindex(idx)})
    d["date"] = d.index.normalize()
    d["hour"] = d.index.hour
    d = d.join(w.set_index("date")[["temp_mean", "temp_max", "temp_min", "humid_mean", "precip_mm"]], on="date")
    jp = holidays.Japan(years=range(2015, 2028))
    d["holiday"] = d["date"].map(lambda x: x in jp).astype(int)
    d["holiday_name"] = d["date"].map(lambda x: jp.get(x, ""))
    d["area"] = "東京"
    d.index.name = "ts"
    return d


def oct_daily():
    h = oct_hourly()
    g = h.groupby("date")
    d = pd.DataFrame({"demand_gwh": g["demand"].sum() / 1000, "n": g["demand"].count(), "peak_mw": g["demand"].max(),
                      "temp_mean": g["temp_mean"].first(), "temp_max": g["temp_max"].first(),
                      "temp_min": g["temp_min"].first(), "humid": g["humid_mean"].first(),
                      "precip": pd.to_numeric(g["precip_mm"].first().replace("--", 0), errors="coerce"),
                      "holiday": g["holiday"].first()}).reset_index()
    d["area"] = "東京"
    return d
