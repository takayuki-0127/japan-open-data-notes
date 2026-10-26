"""福井市の500mメッシュ人口と消防署の位置をそろえ、需要点と候補地を作る。

入力（data/raw/）
- f23_mesh500_2020_5336_5436.csv：国勢調査2020 500mメッシュ「人口及び世帯」（e-Stat 統計地理情報システム T001141、1次メッシュ 5336・5436）から必要な列だけ抜いたもの
- f23_firestations_p17_2012_fukui.json：国土数値情報 消防署データ P17（平成24年＝2012年、福井県）の点データ
- N03-21_210101.json：行政区域（国土数値情報 2021 をもとにした簡略版 TopoJSON、smartnews-smri/japan-topography、CC BY 4.0）
出力（data/）
- demand.csv：福井市内で人口のあるメッシュ（中心点・人口・65歳以上・75歳以上）
- candidates.csv：候補地（今の消防署の場所＋1kmごとの格子から選んだ地点）
"""
import json
import urllib.request

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from common import RAW, DATA

CITY = "18201"  # 福井市

dst = RAW / "N03-21_210101.json"
if not dst.exists():
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/"
        "data/municipality/topojson/s0010/N03-21_210101.json", dst)
g = gpd.read_file(dst)
city = g[g["N03_007"].astype(str).str.zfill(5) == CITY].dissolve()
poly = city.geometry.iloc[0]
city.to_file(DATA / "city.geojson", driver="GeoJSON")


def mesh_center(code):
    """4次メッシュ（500m、9桁）の中心の緯度経度"""
    s = str(code)
    p, u = int(s[0:2]), int(s[2:4])
    q, v = int(s[4]), int(s[5])
    r, w = int(s[6]), int(s[7])
    m = int(s[8])
    lat = p / 1.5 + q * (5 / 60) + r * (30 / 3600)
    lon = u + 100 + v * (7.5 / 60) + w * (45 / 3600)
    dlat, dlon = 15 / 3600, 22.5 / 3600  # 500m メッシュの大きさ
    lat += dlat * (1 if m in (3, 4) else 0)
    lon += dlon * (1 if m in (2, 4) else 0)
    return lat + dlat / 2, lon + dlon / 2


mesh = pd.read_csv(RAW / "f23_mesh500_2020_5336_5436.csv", dtype={"KEY_CODE": str})
for c in ["pop", "pop65", "pop75", "hh"]:
    mesh[c] = pd.to_numeric(mesh[c], errors="coerce")
# 秘匿の合算先（HTKSAKI）があるメッシュは、合算先に値が入っている。値が空のものは0とみなす
mesh[["pop", "pop65", "pop75", "hh"]] = mesh[["pop", "pop65", "pop75", "hh"]].fillna(0)
ll = mesh["KEY_CODE"].map(mesh_center)
mesh["lat"] = [a for a, b in ll]
mesh["lon"] = [b for a, b in ll]
inside = [poly.contains(Point(x, y)) for x, y in zip(mesh["lon"], mesh["lat"])]
dem = mesh[np.array(inside) & (mesh["pop"] > 0)].copy()
dem = dem.rename(columns={"KEY_CODE": "mesh"})[["mesh", "lat", "lon", "pop", "pop65", "pop75", "hh"]]
dem = dem.reset_index(drop=True)
dem.to_csv(DATA / "demand.csv", index=False)

# 今の消防署（2012年）。同じ場所（消防局と東消防署）は1か所にまとめる
fs = pd.DataFrame(json.load(open(RAW / "f23_firestations_p17_2012_fukui.json", encoding="utf-8")))
fs = fs[fs["P17_002"] == CITY].rename(columns={"P17_001": "name", "P17_003": "kind", "P17_004": "address"})
fs["lat"], fs["lon"] = fs["lat"].astype(float), fs["lon"].astype(float)
fs["key"] = (fs["lat"].round(3).astype(str) + "_" + fs["lon"].round(3).astype(str))
fs = fs.sort_values("kind").drop_duplicates("key")
cur = pd.DataFrame({"cand": ["S%02d" % i for i in range(len(fs))], "name": fs["name"].values,
                    "lat": fs["lat"].values, "lon": fs["lon"].values, "type": "station"})

# 格子の候補地：3次メッシュ（1km）ごとに、いちばん人口の多い500mメッシュの中心を1つ選ぶ
dem["m3"] = dem["mesh"].str[:8]
grid = dem.sort_values("pop", ascending=False).drop_duplicates("m3")
gridc = pd.DataFrame({"cand": ["G%03d" % i for i in range(len(grid))], "name": grid["mesh"].values,
                      "lat": grid["lat"].values, "lon": grid["lon"].values, "type": "grid"})
cand = pd.concat([cur, gridc], ignore_index=True)
cand.to_csv(DATA / "candidates.csv", index=False)
dem.drop(columns="m3").to_csv(DATA / "demand.csv", index=False)

print("demand cells", len(dem), "pop", int(dem["pop"].sum()), "65+", int(dem["pop65"].sum()))
print("stations", len(cur), "grid cands", len(gridc))
