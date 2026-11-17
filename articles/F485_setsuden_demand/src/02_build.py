"""data/raw から、1時間ごとの需要を日ごと・夕方に集計し、気温・休日の印と合わせた data/daily.csv を作る。ネットにはつながない。"""
import pathlib, io, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def read(p):
    return pd.read_csv(io.StringIO(p.read_bytes().decode("cp932")), skiprows=1, header=0, thousands=",")


old = []
for p in sorted(RAW.glob("area_jyukyu_jisseki_*.csv")):
    d = read(p).iloc[:, [0, 1]]
    d.columns = ["dt", "demand"]
    d = d.dropna(subset=["dt"])
    d["dt"] = pd.to_datetime(d["dt"], format="%Y/%m/%d %H:%M")
    old.append(d)
old = pd.concat(old)
new = []
for p in sorted(RAW.glob("eria_jukyu_*_09.csv")):
    d = read(p)[["DATE", "TIME", "エリア需要"]].copy()
    hm = d["TIME"].astype(str).str.split(":", expand=True)
    ds = d["DATE"].astype(str)
    base = pd.to_datetime(ds, format="%Y/%m/%d") if ds.str.contains("/").all() else pd.to_datetime(ds, format="%Y%m%d")
    mins = (hm[0].astype("int64") * 60 + hm[1].astype("int64") - 30).to_numpy()
    d["dt"] = (base + pd.to_timedelta(mins, unit="min")).dt.floor("h")
    d["demand"] = pd.to_numeric(d["エリア需要"]) * 0.5
    new.append(d.groupby("dt", sort=True).demand.sum().reset_index())
new = pd.concat(new)
h = pd.concat([old[old.dt < "2024-04-01"], new[new.dt >= "2024-04-01"]]).sort_values("dt")
h = h[(h.dt >= "2018-04-01") & (h.dt < "2025-04-01")]
assert h.dt.is_unique
h["date"] = h.dt.dt.normalize()
h["evening"] = h.dt.dt.hour.isin([17, 18, 19])
d = pd.DataFrame({"demand_gwh": h.groupby("date").demand.sum() / 1000,
                  "evening_gwh": h[h.evening].groupby("date").demand.sum() / 1000,
                  "hours": h.groupby("date").size()})
for st in ["fukuoka", "kagoshima"]:
    t = pd.read_csv(RAW / f"jma_daily_{st}.csv", dtype=str)
    t["v"] = pd.to_numeric(t.temp_mean_raw.str.extract(r"(-?\d+\.?\d*)")[0], errors="coerce")
    d[f"temp_{st}"] = t.set_index(pd.to_datetime(t.date)).v.reindex(d.index).values
sy = pd.read_csv(io.StringIO((RAW / "syukujitsu.csv").read_bytes().decode("cp932")))
hol = set(pd.to_datetime(sy.iloc[:, 0], format="%Y/%m/%d"))
md = d.index.month * 100 + d.index.day
d["dow"] = d.index.dayofweek
d["holiday"] = (d.index.isin(hol) | (md >= 1229) | (md <= 103)).astype(int)
d["fy"] = d.index.year - (d.index.month <= 3).astype(int)
d["month"] = d.index.month
d.index.name = "date"
d = d[d.hours == 24]
d.reset_index().assign(date=lambda x: x.date.dt.strftime("%Y-%m-%d")).to_csv(ROOT / "data" / "daily.csv", index=False, float_format="%.4f")
print(len(d), int(d[["temp_fukuoka", "temp_kagoshima"]].isna().sum().sum()))
