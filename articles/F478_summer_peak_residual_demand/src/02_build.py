"""data/raw の CSV を、夏（7〜9月）の1時間値の長い表にする。
- 1時間値（2016〜2023年度）：DATE_TIME はその1時間の始まり。単位 MWh（＝その1時間の平均 MW）。
- 30分値（2024年以降）：単位 MW平均。関西は TIME が30分の始まり、九州は30分の終わり。
  30分の始まりの時刻にそろえ、1時間ごとに平均する（＝その1時間の MWh）。
列は見出しの文字（エリア需要、太陽光の実績・抑制量、風力の実績・抑制量）で決める。"""
import pathlib, io
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
COLS = ["demand", "pv", "pv_cut", "wind", "wind_cut"]


def text(p):
    return p.read_bytes().decode("cp932").replace("\r\n", "\n").replace("\r", "\n")


def read_hourly(p):
    lines = text(p).split("\n")
    hi = next(i for i, l in enumerate(lines) if l.startswith("DATE_TIME"))  # 先頭に注記の行がある年がある
    top, head = lines[hi - 1].split(","), lines[hi].split(",")
    names = []
    for g, h in zip(top, head):
        h = h.split("〔")[0]
        names.append(f"{g}{h}" if g else h)
    df = pd.read_csv(io.StringIO("\n".join(lines[hi + 1:])), header=None, names=names)
    df = df.dropna(subset=["DATE_TIME"])
    out = pd.DataFrame({"dt": pd.to_datetime(df["DATE_TIME"], format="%Y/%m/%d %H:%M"),
                        "demand": df["エリア需要"], "pv": df["太陽光実績"], "pv_cut": df["太陽光抑制量"],
                        "wind": df["風力実績"], "wind_cut": df["風力抑制量"]})
    return out


def read_30min(p, time_is_end):
    lines = text(p).split("\n")
    hi = next(i for i, l in enumerate(lines) if l.startswith("DATE,TIME"))
    df = pd.read_csv(io.StringIO("\n".join(lines[hi:])))
    df = df.dropna(subset=["DATE"])
    ds = df["DATE"].astype(str)
    base = pd.to_datetime(ds, format="%Y/%m/%d") if ds.str.contains("/").all() else pd.to_datetime(ds, format="%Y%m%d")
    hm = df["TIME"].astype(str).str.split(":", expand=True)
    mins = hm[0].astype("int64") * 60 + hm[1].astype("int64") - (30 if time_is_end else 0)
    start = base + pd.to_timedelta(mins, unit="min")
    out = pd.DataFrame({"dt": start.dt.floor("h"), "demand": df["エリア需要"], "pv": df["太陽光発電実績"],
                        "pv_cut": df["太陽光出力制御量"], "wind": df["風力発電実績"], "wind_cut": df["風力出力制御量"]})
    for c in COLS:
        out[c] = pd.to_numeric(out[c]).astype(float)
    cnt = out.groupby("dt").size()
    assert (cnt == 2).all(), (p.name, cnt[cnt != 2].head())
    return out.groupby("dt", sort=True)[COLS].mean().reset_index()


def main():
    parts = []
    for area, pat_h, pat_m, end in [("関西", "kansai_area_jyukyu_jisseki_*.csv", "kansai_eria_jukyu_*_06.csv", False),
                                    ("九州", "kyushu_area_jyukyu_jisseki_*_2Q.csv", "kyushu_eria_jukyu_*_09.csv", True)]:
        h = pd.concat([read_hourly(p) for p in sorted(RAW.glob(pat_h))])
        m = pd.concat([read_30min(p, end) for p in sorted(RAW.glob(pat_m))])
        d = pd.concat([h[h.dt < "2024-04-01"], m]).sort_values("dt")
        d = d[d.dt.dt.month.isin([7, 8, 9])].copy()
        d["area"] = area
        assert d.dt.is_unique, area
        parts.append(d)
    d = pd.concat(parts)
    for c in COLS:
        d[c] = pd.to_numeric(d[c]).astype(float)
    sy = pd.read_csv(io.StringIO(text(RAW / "syukujitsu.csv")))
    hol = set(pd.to_datetime(sy.iloc[:, 0], format="%Y/%m/%d").dt.date)
    d["date"] = d.dt.dt.date
    d["year"] = d.dt.dt.year
    d["hour"] = d.dt.dt.hour
    md = d.dt.dt.month * 100 + d.dt.dt.day
    d["weekday"] = (d.dt.dt.dayofweek < 5) & (~d.date.isin(hol)) & ~((md >= 813) & (md <= 816))
    d["dt"] = d.dt.dt.strftime("%Y-%m-%d %H:%M")
    d = d[["area", "dt", "year", "hour", "weekday"] + COLS]
    d.to_csv(DATA / "summer_hourly.csv", index=False, float_format="%.1f")
    print(d.groupby(["area", "year"]).size().unstack())


if __name__ == "__main__":
    main()
