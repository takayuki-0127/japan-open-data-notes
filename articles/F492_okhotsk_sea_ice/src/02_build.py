"""data/raw から、海氷期ごとの表（data/season.csv）と地点の初終日（data/stations.csv）を作る。"""
import datetime as dt, os, re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data")

# ---- 半旬ごとの海氷域面積 ----------------------------------------------------------------------------
lines = open(os.path.join(RAW, "okhotsk_alldata.txt"), encoding="utf-8").read().splitlines()
head = lines[1].split()
cols = head[1:]
rows = []
for ln in lines[2:]:
    t = ln.split()
    if len(t) != len(head):
        continue
    rows.append([int(t[0][:4]) + 1] + [float(v) for v in t[1:]])
a = pd.DataFrame(rows, columns=["season"] + cols).set_index("season")
a = a.replace(-99.99, np.nan)
DEC_MAY = [c for c in cols if c[:2] in ("12", "01", "02", "03", "04", "05")]
assert len(DEC_MAY) == 36
JAN_APR = [c for c in cols if c[:2] in ("01", "02", "03", "04")]
FEB_MAR = [c for c in cols if c[:2] in ("02", "03")]
APR_MAY = [c for c in cols if c[:2] in ("04", "05")]
DEC_JAN = [c for c in cols if c[:2] in ("12", "01")]
s = pd.DataFrame(index=a.index)
s["max_dec_may"] = a[DEC_MAY].max(axis=1)
s["acc_dec_may"] = a[DEC_MAY].sum(axis=1, min_count=36)
s["acc_jan_apr"] = a[JAN_APR].sum(axis=1, min_count=24)
s["mean_dec_jan"] = a[DEC_JAN].mean(axis=1)
s["mean_feb_mar"] = a[FEB_MAR].mean(axis=1)
s["mean_apr_may"] = a[APR_MAY].mean(axis=1)
# 最大の時期（12月1日からの日数）
def day_of(col, season):
    m, d = int(col[:2]), int(col[3:])
    y = season - 1 if m >= 10 else season
    return (dt.date(y, m, d) - dt.date(season - 1, 12, 1)).days
s["max_day_from_dec1"] = [day_of(a.loc[y, DEC_MAY].idxmax(), y) for y in a.index]

lt = pd.read_csv(os.path.join(RAW, "longterm_okhotsk_latest.txt"), sep=r"\s+", skiprows=1, header=None,
                 names=["season_label", "max_official"])
lt["season"] = lt["season_label"].str[:4].astype(int) + 1
s = s.join(lt.set_index("season")["max_official"])

# ---- 網走の気温 -------------------------------------------------------------------------------------
html = open(os.path.join(RAW, "etrn_monthly_temp_47409.html"), encoding="utf-8").read()
temps = {}
for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S):
    parts = re.split(r"<t[dh][^>]*>", tr)[1:]
    cells = [re.sub(r"<[^>]+>", "", c).strip() for c in parts]
    if len(cells) >= 13 and re.fullmatch(r"\d{4}", cells[0]):
        vals = []
        for c in cells[1:13]:
            c2 = c.replace(")", "").replace("]", "").strip()
            # 「]」（資料不足値）は使わない
            vals.append(np.nan if (c.endswith("]") or c2 in ("", "×", "///", "#")) else float(c2))
        temps[int(cells[0])] = vals
tm = pd.DataFrame.from_dict(temps, orient="index", columns=[f"m{i}" for i in range(1, 13)])
tm.index.name = "year"
tm.to_csv(os.path.join(OUT, "abashiri_monthly_temp.csv"), float_format="%.1f")
# 海氷期 Y の冬：前の年の12月と、その年の1〜3月
prevdec = tm["m12"].shift(1)
w = pd.DataFrame(index=tm.index)
w["t_jan_mar"] = tm[["m1", "m2", "m3"]].mean(axis=1, skipna=False)
w["t_dec_feb"] = pd.concat([prevdec, tm["m1"], tm["m2"]], axis=1).mean(axis=1, skipna=False)
w["t_feb_mar"] = tm[["m2", "m3"]].mean(axis=1, skipna=False)
s = s.join(w, how="left")
s.index.name = "season"
s.to_csv(os.path.join(OUT, "season.csv"), float_format="%.3f")

# ---- 沿岸の初終日 -------------------------------------------------------------------------------------
NAMES = {"wakkanai": "稚内", "omu": "雄武", "monbetsu": "紋別", "abashiri": "網走", "nemuro": "根室", "kushiro": "釧路"}


def doy(tok, season):
    """「1.24」→ 1月1日からの日数（12月なら負）。「----」は現象なし（None）、空は値なし（nan）。"""
    tok = tok.strip()
    if tok == "":
        return np.nan, False
    if set(tok) == {"-"}:
        return np.nan, True
    m, d = tok.split(".")
    m, d = int(m), int(d)
    y = season - 1 if m >= 10 else season
    return float((dt.date(y, m, d) - dt.date(season, 1, 1)).days), False


recs = []
for key, jp in NAMES.items():
    for ln in open(os.path.join(RAW, f"station_{key}.txt"), encoding="utf-8").read().splitlines():
        if not re.match(r"^\d{4}", ln):
            continue
        ln = ln.ljust(51)
        y = int(ln[0:4])
        first, none_f = doy(ln[4:13], y)
        last, _ = doy(ln[13:22], y)
        per = ln[22:31].strip()
        shore, none_s = doy(ln[31:44], y)
        open_, _ = doy(ln[44:51], y)
        recs.append({"station": key, "name": jp, "season": y, "first": first, "no_ice": int(none_f),
                     "last": last, "period": float(per) if per not in ("",) else np.nan,
                     "shore_first": shore, "no_shore": int(none_s), "sea_open": open_})
st = pd.DataFrame(recs)
st.to_csv(os.path.join(OUT, "stations.csv"), index=False, float_format="%.0f")
print("season", s.shape, "stations", st.shape)
