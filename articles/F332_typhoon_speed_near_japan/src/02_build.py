"""02 整形：ベストトラックを、6時間ごとの区間（2点の間の動き）の表にする"""
import io, pathlib, zipfile
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
R = 6371.0


def parse():
    t = zipfile.ZipFile(RAW / "bst_all.zip").read("bst_all.txt").decode("ascii")
    rows, sid = [], None
    for l in t.splitlines():
        f = l.split()
        if not f:
            continue
        if f[0] == "66666":
            sid = f[1]
            continue
        yy, mm, dd, hh = int(l[0:2]), int(l[2:4]), int(l[4:6]), int(l[6:8])
        year = 1900 + yy if yy >= 51 else 2000 + yy
        grade = int(f[2]); lat = int(f[3]) / 10; lon = int(f[4]) / 10; pres = int(f[5])
        rows.append((sid, year, mm, dd, hh, grade, lat, lon, pres))
    d = pd.DataFrame(rows, columns=["sid", "year", "month", "day", "hour", "grade", "lat", "lon", "pres"])
    d["time"] = pd.to_datetime(dict(year=d.year, month=d.month, day=d.day, hour=d.hour))
    return d


def main():
    d = parse()
    ty = d.groupby("sid").grade.apply(lambda g: ((g >= 3) & (g <= 5)).any() | (g == 9).any())
    d = d[d.sid.map(ty)]
    d = d[d.hour.isin([0, 6, 12, 18])].sort_values(["sid", "time"]).copy()
    g = d.groupby("sid")
    n = pd.DataFrame({"sid": d.sid, "t0": d.time, "lat0": d.lat, "lon0": d.lon, "grade0": d.grade, "pres0": d.pres,
                      "t1": g.time.shift(-1), "lat1": g.lat.shift(-1), "lon1": g.lon.shift(-1), "grade1": g.grade.shift(-1)})
    n = n.dropna(subset=["t1"]).copy()
    n["t1"] = pd.to_datetime(n.t1)
    n = n[(n.t1 - n.t0).dt.total_seconds() == 6 * 3600].copy()
    p0, p1 = np.radians(n.lat0), np.radians(n.lat1)
    dl = np.radians(n.lon1 - n.lon0)
    a = np.sin((p1 - p0) / 2) ** 2 + np.cos(p0) * np.cos(p1) * np.sin(dl / 2) ** 2
    n["km"] = 2 * R * np.arcsin(np.sqrt(a))
    n["speed"] = n.km / 6.0
    n["latm"] = (n.lat0 + n.lat1) / 2
    n["lonm"] = (n.lon0 + n.lon1) / 2
    n["year"] = n.t0.dt.year
    n["month"] = n.t0.dt.month
    n["extra"] = ((n.grade0 == 6) | (n.grade1 == 6)).astype(int)
    n = n.drop(columns=["t1"]).round(4)
    n["t0"] = n.t0.dt.strftime("%Y-%m-%d %H")
    n.to_csv(ROOT / "data" / "segments.csv", index=False)
    print(len(n), n.sid.nunique(), n.year.min(), n.year.max())


if __name__ == "__main__":
    main()
