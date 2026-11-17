"""data/raw の CSV（cp932）から、1時間ごとの表 data/hourly.csv を作る。ネットにはつながない。
- 2016〜2023年度：1時間値（MWh）。DATE_TIME はその1時間の始まり。
- 2024年度〜：30分値（MW平均）。TIME はその30分の終わり（0:30 は 0:00〜0:30）。×0.5 で MWh にして1時間ごとに足す。
"""
import pathlib, io
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def read(p, skip):
    return pd.read_csv(io.StringIO(p.read_bytes().decode("cp932")), skiprows=skip, header=0, thousands=",")


old = []
for p in sorted(RAW.glob("area_jyukyu_jisseki_*.csv")):
    d = read(p, 1)
    d = d.iloc[:, [0, 1, 7, 8, 9, 10]]
    d.columns = ["dt", "demand", "pv", "pv_cut", "wind", "wind_cut"]
    d = d.dropna(subset=["dt"])
    d["dt"] = pd.to_datetime(d["dt"], format="%Y/%m/%d %H:%M")
    old.append(d)
old = pd.concat(old)

new = []
for p in sorted(RAW.glob("eria_jukyu_*_09.csv")):
    d = read(p, 1)
    d = d[["DATE", "TIME", "エリア需要", "太陽光発電実績", "太陽光出力制御量", "風力発電実績", "風力出力制御量"]].copy()
    d.columns = ["date", "time", "demand", "pv", "pv_cut", "wind", "wind_cut"]
    hm = d["time"].astype(str).str.split(":", expand=True)
    ds = d["date"].astype(str)
    base = pd.to_datetime(ds, format="%Y/%m/%d") if ds.str.contains("/").all() else pd.to_datetime(ds, format="%Y%m%d")
    mins = (hm[0].astype("int64") * 60 + hm[1].astype("int64") - 30).to_numpy()
    d["dt"] = (base + pd.to_timedelta(mins, unit="min")).dt.floor("h")
    for c in ["demand", "pv", "pv_cut", "wind", "wind_cut"]:
        d[c] = pd.to_numeric(d[c]) * 0.5
    new.append(d.groupby("dt", sort=True)[["demand", "pv", "pv_cut", "wind", "wind_cut"]].sum().reset_index())
new = pd.concat(new)

h = pd.concat([old[old.dt < "2024-04-01"], new[new.dt >= "2024-04-01"]]).sort_values("dt").reset_index(drop=True)
h = h[(h.dt >= "2016-04-01") & (h.dt < "2026-04-01")]
for c in ["demand", "pv", "pv_cut", "wind", "wind_cut"]:
    h[c] = pd.to_numeric(h[c]).astype(float)
assert h.dt.is_unique
# 休日：土日・祝日・振替休日・12/29〜1/3
sy = pd.read_csv(io.StringIO((RAW / "syukujitsu.csv").read_bytes().decode("cp932")))
hol = set(pd.to_datetime(sy.iloc[:, 0], format="%Y/%m/%d").dt.date)
day = h.dt.dt.normalize()
md = h.dt.dt.month * 100 + h.dt.dt.day
h["holiday"] = ((h.dt.dt.dayofweek >= 5) | day.dt.date.isin(hol) | (md >= 1229) | (md <= 103)).astype(int)
h["fy"] = h.dt.dt.year - (h.dt.dt.month <= 3).astype(int)
h["month"] = h.dt.dt.month
h["hour"] = h.dt.dt.hour
h["dt"] = h.dt.dt.strftime("%Y-%m-%d %H:%M")
h.to_csv(ROOT / "data" / "hourly.csv", index=False, float_format="%.1f")
print(len(h), h.fy.min(), h.fy.max())
