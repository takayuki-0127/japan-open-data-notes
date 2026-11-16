"""data/raw から、夏ごとの表（data/summer.csv）を作る。"""
import os, re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data")
Y0, Y1 = 1949, 2025

STATIONS = [("網走", 47409, "北日本"), ("根室", 47420, "北日本"), ("寿都", 47421, "北日本"), ("山形", 47588, "北日本"),
            ("石巻", 47592, "北日本"), ("伏木", 47606, "東日本"), ("飯田", 47637, "東日本"), ("銚子", 47648, "東日本"),
            ("境", 47742, "西日本"), ("浜田", 47755, "西日本"), ("彦根", 47761, "西日本"), ("宮崎", 47830, "西日本"),
            ("多度津", 47890, "西日本"), ("名瀬", 47909, "沖縄・奄美"), ("石垣島", 47918, "沖縄・奄美")]
REGIONS = ["北日本", "東日本", "西日本", "沖縄・奄美"]

# ---- NINO.3 の基準値との差（月） ------------------------------------------------------------------------
txt = re.sub(r"<[^>]+>", " ", open(os.path.join(RAW, "nino3idx.html"), encoding="utf-8").read())
n3 = {}
for ln in txt.splitlines():
    m = re.match(r"^\s*(\d{4})((?:\s+-?\d+\.\d)+)\s*$", ln)
    if m:
        vals = [float(v) for v in m.group(2).split()]
        n3[int(m.group(1))] = vals + [np.nan] * (12 - len(vals))
n3 = pd.DataFrame.from_dict(n3, orient="index", columns=[f"m{i}" for i in range(1, 13)])
n3.index.name = "year"
n3.to_csv(os.path.join(OUT, "nino3_monthly.csv"), float_format="%.1f")

# ---- 発生期間の表 -----------------------------------------------------------------------------------
h = open(os.path.join(RAW, "elnino_table.html"), encoding="utf-8").read()
SEAS = {"春": 1, "夏": 2, "秋": 3, "冬": 4}


def parse_season(t):
    """「1951年夏」→(1951,2)、「1951/52年冬」→(1951,4)（12〜2月の冬は始まりの年で数える）。"""
    m = re.match(r"(\d{4})(?:/(\d{2}))?年([春夏秋冬])", t)
    y, s = int(m.group(1)), SEAS[m.group(3)]
    if s == 4 and m.group(2) is None:
        y -= 1  # 「1953年冬」のような書き方は、前の年の12月からの冬
    return y * 4 + s


events = []
for color, period in re.findall(r'BACKGROUND-COLOR:\s*(#\w+)"?>([^<]+)</TD>', h, flags=re.I):
    period = period.strip()
    if "～" not in period:
        continue
    a, b = period.split("～")
    kind = {"#fff0f0": "elnino", "#eeffff": "lanina"}[color.lower()]
    events.append({"kind": kind, "period": period, "start": parse_season(a), "end": parse_season(b)})
ev = pd.DataFrame(events)
ev.to_csv(os.path.join(OUT, "events.csv"), index=False)


def in_event(year, season, kind):
    k = year * 4 + season
    return bool(((ev["kind"] == kind) & (ev["start"] <= k) & (ev["end"] >= k)).any())


# ---- 夏の気温 -------------------------------------------------------------------------------------
jp = pd.read_csv(os.path.join(RAW, "ssn_jpn.csv"), encoding="cp932")
jp.columns = ["year", "djf", "mam", "jja", "son"]
jp = jp.set_index("year")


def etrn(block):
    html = open(os.path.join(RAW, f"etrn_m_{block}.html"), encoding="utf-8").read()
    out = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.split(r"<t[dh][^>]*>", tr)[1:]]
        if len(cells) >= 13 and re.fullmatch(r"\d{4}", cells[0]):
            vals = []
            for c in cells[1:13]:
                c2 = c.replace(")", "").replace("]", "").strip()
                vals.append(np.nan if (c.endswith("]") or not re.fullmatch(r"-?\d+(\.\d+)?", c2)) else float(c2))
            out[int(cells[0])] = vals
    return pd.DataFrame.from_dict(out, orient="index", columns=[f"m{i}" for i in range(1, 13)])


rows = []
for name, block, reg in STATIONS:
    t = etrn(block).loc[Y0:Y1]
    for y, r in t.iterrows():
        rows.append({"station": name, "region": reg, "year": y, "t6": r["m6"], "t7": r["m7"], "t8": r["m8"]})
stm = pd.DataFrame(rows)
stm["jja"] = stm[["t6", "t7", "t8"]].mean(axis=1, skipna=False)
stm.to_csv(os.path.join(OUT, "station_summer.csv"), index=False, float_format="%.2f")
# 地点ごとに 1991〜2020年の平均からの差 → 地方の平均（地点の数が欠けた年は除く）
for c in ("t6", "t7", "t8", "jja"):
    base = stm[(stm.year >= 1991) & (stm.year <= 2020)].groupby("station")[c].mean()
    stm[c + "_anom"] = stm[c] - stm["station"].map(base)
reg_tab = {}
for reg in REGIONS:
    d = stm[stm.region == reg]
    nst = d["station"].nunique()
    for c in ("jja", "t6", "t7", "t8"):
        g = d.groupby("year")[c + "_anom"]
        reg_tab[f"{reg}_{c}"] = g.mean().where(g.count() == nst)

s = pd.DataFrame(index=pd.Index(range(Y0, Y1 + 1), name="year"))
s["jp_jja"] = jp["jja"].reindex(s.index)
for k, v in reg_tab.items():
    s[k] = v.reindex(s.index)
s["nino3_jja"] = n3.loc[Y0:Y1, ["m6", "m7", "m8"]].mean(axis=1)
s["nino3_prev_djf"] = [np.nanmean([n3.loc[y - 1, "m12"], n3.loc[y, "m1"], n3.loc[y, "m2"]]) if y - 1 in n3.index else np.nan
                       for y in s.index]
s["elnino_summer"] = [int(in_event(y, 2, "elnino")) for y in s.index]
s["lanina_summer"] = [int(in_event(y, 2, "lanina")) for y in s.index]
s["elnino_prev_winter"] = [int(in_event(y - 1, 4, "elnino")) for y in s.index]
assert not (s["elnino_summer"] & s["lanina_summer"]).any()
s.to_csv(os.path.join(OUT, "summer.csv"), float_format="%.3f")
print(s.shape, "events", len(ev), "el", int(s.elnino_summer.sum()), "la", int(s.lanina_summer.sum()))
