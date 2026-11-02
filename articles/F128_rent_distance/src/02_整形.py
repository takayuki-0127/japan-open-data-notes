"""02 整形：住宅・土地統計調査の表を、分析用の CSV にする"""
import csv
import io
import json
import numpy as np
import pandas as pd
from common import DATA, num, xy_to_lonlat, haversine, CENTERS, CENTERS_WIDE

raw = json.load(open(DATA / "raw" / "f128_hlts_rent.json", encoding="utf-8"))


def rows(key):
    return list(csv.reader(io.StringIO(raw[key])))


# --- 1) 距離帯ごとの 1畳当たり家賃（建築の時期別）2023・2018 ---
def band_table(key, year, off):
    out = []
    for r in rows(key):
        if len(r) < off + 10:
            continue
        reg, age = r[off], r[off + 1] if off == 1 else r[off + 2]
        if not reg[:5].isdigit() or "_" not in age:
            continue
        v = [num(x) for x in (r[off + 2:off + 11] if off == 1 else r[off + 3:off + 12])]
        out.append(dict(year=year, region=reg, age=age, total=v[0], private=v[4], wood=v[5], nonwood=v[6], public=v[2], ur=v[3]))
    return pd.DataFrame(out)


b23 = band_table("d23", 2023, 1)
b18 = band_table("d18", 2018, 5)
band = pd.concat([b23, b18], ignore_index=True)
band["metro"] = band.region.str.extract(r"_(東京|名古屋|大阪)")[0]
km = band.region.str.extract(r"(\d+)～(\d+)km")
band["band_lo"], band["band_hi"] = km[0].astype(float), km[1].astype(float)
band.to_csv(DATA / "band_rent_by_age.csv", index=False)
print("距離帯の表", band.shape, band.region.nunique())


# --- 2) 市区町村の 延べ面積1m2当たり家賃（所有の関係別）2023・2018 ---
def muni_table(key, year, off):
    out = []
    for r in rows(key):
        if len(r) < (17 if off == 1 else 22):
            continue
        reg, ten = r[off], r[off + 1] if off == 1 else r[off + 2]
        if not reg[:5].isdigit():
            continue
        vals = r[off + 2:] if off == 1 else r[off + 3:]
        v = [num(x) for x in vals]
        out.append(dict(year=year, code=reg[:5], name=reg[6:], tenure=ten, n=v[0], n_unknown=v[11],
                        rent_m2_incl0=v[12], rent_m2=v[13], n_6000plus=v[10], n_0yen=v[1]))
    return pd.DataFrame(out)


m23 = muni_table("m23", 2023, 1)
m18 = muni_table("m18", 2018, 5)
muni = pd.concat([m23, m18], ignore_index=True)
muni["tenure"] = muni.tenure.str.replace(r"^\d+_", "", regex=True)
muni.to_csv(DATA / "muni_rent_m2_long.csv", index=False)
print("市区町村の表", muni.shape, muni.groupby("year").code.nunique().to_dict())

# --- 3) 市区町村の 最寄り駅までの距離別 主世帯数（2023、世帯の型＝総数）---
st = []
for r in rows("s23"):
    if len(r) < 18 or not r[1][:5].isdigit() or r[2] != "00_総数":
        continue
    v = [num(x) for x in r[3:18]]
    tot = v[0]
    st.append(dict(code=r[1][:5], hh=tot, st200=v[1], st500=v[2], st1000=v[3], st2000=v[4], st2000plus=v[9]))
st = pd.DataFrame(st)
st["share_st500"] = (st.st200 + st.st500) / st.hh
st["share_st1000"] = (st.st200 + st.st500 + st.st1000) / st.hh
st["share_st2000plus"] = st.st2000plus / st.hh
st.to_csv(DATA / "muni_station_access_2023.csv", index=False)
print("駅までの距離の表", st.shape)

# --- 4) 位置・所得など（F107 と同じ市区町村の表）と結合 ---
nd = pd.read_csv(DATA / "raw" / "municipal_nodes_F107.csv", dtype={"code": str, "pref": str})
nd["lon"], nd["lat"] = xy_to_lonlat(nd.x_km, nd.y_km)
for nm, (lo, la) in CENTERS_WIDE.items():
    nd[f"d_{nm}"] = haversine(nd.lon, nd.lat, lo, la)
d3 = nd[[f"d_{k}" for k in CENTERS]]
nd["dist3"] = d3.min(axis=1)
nd["metro3"] = d3.idxmin(axis=1).str[2:]
dw = nd[[f"d_{k}" for k in CENTERS_WIDE]]
nd["distW"] = dw.min(axis=1)
nd["metroW"] = dw.idxmin(axis=1).str[2:]
keep = ["code", "name", "pref", "pop", "income", "density", "aged", "owner", "floor", "lon", "lat",
        "d_東京", "d_名古屋", "d_大阪", "dist3", "metro3", "distW", "metroW"]
nd = nd[keep]

# 政令市は「区」で比べる。表に市全体の行（例 01100）もあるが、区の行を使う
priv = muni[muni.tenure == "民営借家"].pivot_table(index="code", columns="year", values=["rent_m2", "n", "rent_m2_incl0"])
priv.columns = [f"{a}_{b}" for a, b in priv.columns]
allt = muni[muni.tenure == "総数"].pivot_table(index="code", columns="year", values="rent_m2")
allt.columns = [f"rent_m2_all_{c}" for c in allt.columns]
df = nd.merge(priv.reset_index(), on="code", how="inner").merge(allt.reset_index(), on="code", how="left")
df = df.merge(st[["code", "share_st500", "share_st1000", "share_st2000plus"]], on="code", how="left")
df.to_csv(DATA / "muni_analysis.csv", index=False)
print("結合後", df.shape, "民営借家の家賃がある 2023:", df.rent_m2_2023.notna().sum(), "2018:", df.rent_m2_2018.notna().sum())
print(df[["rent_m2_2023", "dist3", "distW", "share_st1000"]].describe().round(2))
