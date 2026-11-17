"""data/raw の住宅・土地統計調査の表から、太陽光の発電機器のある住宅数の表を作る。ネットにはつながない。
出力：data/timeseries.csv（年・地域・所有の関係・総数・太陽光あり・なし）、data/tatekata.csv（年・建て方）、data/jiki.csv（所有の関係・建築の時期）"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
WS = re.compile(r"[\s　]+")


def norm(s):
    return WS.sub("", str(s)) if str(s) != "nan" else ""


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return np.nan


# ---- 時系列 第19表 ----------------------------------------------------------------------------------
YEARS = [2003, 2008, 2013, 2018, 2023]
rows = []
for sheet, tenure in [("総数", "総数"), ("持ち家", "持ち家"), ("借家", "借家")]:
    v = pd.read_excel(RAW / "jutaku_timeseries_t19_2003_2023.xlsx", sheet_name=sheet, header=None, dtype=str)
    h9 = [norm(s) for s in v.iloc[9].tolist()]
    sol = [j for j, s in enumerate(h9) if s.startswith("太陽光を利用した発電機器")][0]
    yr = [norm(s) for s in v.iloc[14].tolist()]
    tot_cols = [j for j in range(sol) if yr[j] in [str(y) for y in YEARS]][:5]   # 総数の5列
    yes_cols = [sol + k for k in range(5)]
    no_cols = [sol + 5 + k for k in range(5)]
    assert [yr[j] for j in yes_cols] == [str(y) for y in YEARS] and [yr[j] for j in no_cols] == [str(y) for y in YEARS]
    for i in range(15, len(v)):
        name = ""
        for j in range(0, 4):
            s = norm(v.iat[i, j])
            if s and not re.match(r"^[A-Za-z0-9]", s):
                name = s
                break
        if not name or np.isnan(num(v.iat[i, tot_cols[0]])):
            continue
        for k, y in enumerate(YEARS):
            rows.append({"year": y, "area": name, "tenure": tenure, "total": num(v.iat[i, tot_cols[k]]),
                         "solar_yes": num(v.iat[i, yes_cols[k]]), "solar_no": num(v.iat[i, no_cols[k]])})
ts = pd.DataFrame(rows)
ts.to_csv(ROOT / "data" / "timeseries.csv", index=False)

# ---- 建て方（各回の全国の表） ----------------------------------------------------------------------------
out = []
for y, fn in [(2008, "jutaku_2008_tatekata.xls"), (2013, "jutaku_2013_tatekata.xls"), (2018, "jutaku_2018_tatekata.xls"), (2023, "jutaku_2023_tatekata.xlsx")]:
    v = pd.read_excel(RAW / fn, header=None, dtype=str)
    N = v.map(norm)
    hdr = [(i, j) for i in range(20) for j in range(v.shape[1]) if N.iat[i, j].startswith("太陽光を利用した発電")][0]
    sol = hdr[1]
    tot = [j for i in range(20) for j in range(v.shape[1]) if N.iat[i, j] == "総数"][0]
    got = {}
    for i in range(hdr[0] + 1, len(v)):
        for j in range(0, min(15, v.shape[1])):
            lab = N.iat[i, j]
            if lab in ("住宅総数", "一戸建", "長屋建", "共同住宅") and lab not in got and not np.isnan(num(v.iat[i, tot])):
                got[lab] = (num(v.iat[i, tot]), num(v.iat[i, sol]), num(v.iat[i, sol + 1]))
        if len(got) == 4:
            break
    for lab, (t, s, n) in got.items():
        out.append({"year": y, "type": lab, "total": t, "solar_yes": s, "solar_no": n})
pd.DataFrame(out).to_csv(ROOT / "data" / "tatekata.csv", index=False)

# ---- 建築の時期（令和5年、全国） -------------------------------------------------------------------------
v = pd.read_excel(RAW / "jutaku_2023_jiki.xlsx", header=None, dtype=str)
hdr = [norm(s) for s in v.iloc[6].tolist()]
c_tot = hdr.index("00_総数")
c_yes = [j for j, s in enumerate(hdr) if s.startswith("21_太陽光")][0]
c_no = [j for j, s in enumerate(hdr) if s.startswith("22_太陽光")][0]
d = v.iloc[9:].copy()
d = d[(d[1] == "00000_全国") & (d[2] == "0_総数")]
jk = pd.DataFrame({"tenure": d[3].str.split("_").str[1], "period": d[4].str.split("_", n=1).str[1],
                   "total": d[c_tot].map(num), "solar_yes": d[c_yes].map(num), "solar_no": d[c_no].map(num)})
jk.to_csv(ROOT / "data" / "jiki.csv", index=False)
print(ts.area.nunique(), len(ts), len(out), len(jk), sorted(jk.tenure.unique()))
