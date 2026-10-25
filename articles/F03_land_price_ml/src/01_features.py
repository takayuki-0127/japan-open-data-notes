"""地価公示（L01）の各地点に特徴量をつける → data/features.csv
前年の価格は使わない（地点の属性・周辺の駅・市区町村の人口だけで説明する）"""
import json
import numpy as np, pandas as pd
from sklearn.neighbors import BallTree
from common import L01_GEOJSON, S12_GEOJSON, RAW, DATA, RES

R = 6371.0
# --- 地価公示 ---
g = json.load(open(L01_GEOJSON, encoding="utf-8"))
rows = []
for f in g["features"]:
    p = f["properties"]; lon, lat = f["geometry"]["coordinates"]
    rows.append(dict(
        code=f'{p["L01_001"]}-{p["L01_002"]}-{p["L01_003"]}', muni=p["L01_001"], pref=p["L01_001"][:2],
        land_use_class={"000": "住宅地", "003": "宅地見込地", "005": "商業地", "007": "準工業地", "009": "工業地",
                        "010": "調整区域内宅地", "013": "調整区域内の林地"}.get(p["L01_002"], "その他"),
        price=p["L01_008"], price_2016=p["L01_095"], city=p["L01_024"], address=p["L01_025"],
        acreage=p["L01_027"], gas=p["L01_032"], water=p["L01_033"], sewage=p["L01_034"],
        irregular=int(p["L01_035"] != "_"), frontage_ratio=p["L01_036"], depth_ratio=p["L01_037"],
        floors=p["L01_038"], basement=p["L01_039"], road_type=p["L01_040"], road_width=p["L01_042"],
        station_square=int(p["L01_049"] == "駅前広場接面"), station=p["L01_048"], dist_station=p["L01_050"],
        use_district=p["L01_051"], fire_area=p["L01_052"], planning_area=p["L01_053"],
        coverage=p["L01_057"], far=p["L01_058"], lat=lat, lon=lon))
d = pd.DataFrame(rows)
d["road_type"] = d["road_type"].replace({"都道": "都道府県道", "府道": "都道府県道", "道道": "都道府県道", "県道": "都道府県道",
                                         "区道": "市区町村道", "市道": "市区町村道", "町道": "市区町村道", "村道": "市区町村道"})
d.loc[~d["road_type"].isin(["市区町村道", "都道府県道", "国道", "私道"]), "road_type"] = "その他"
d["log_acreage"] = np.log(d["acreage"].clip(lower=1))
# 駅距離 0 は「駅に近接」「駅前広場に接する」地点（354地点）。0m のまま使う
for c in ["frontage_ratio", "depth_ratio", "road_width", "coverage", "far", "floors", "basement"]:
    d.loc[d[c] < 0, c] = np.nan

# --- 駅別乗降客数（同じ駅グループをまとめ、線の中点を駅の位置とする） ---
s = json.load(open(S12_GEOJSON, encoding="utf-8"))
st = []
for f in s["features"]:
    p = f["properties"]; c = np.array(f["geometry"]["coordinates"])
    st.append(dict(group=p["S12_001g"], name=p["S12_001"], lon=c[:, 0].mean(), lat=c[:, 1].mean(),
                   pass2024=p["S12_061"] or 0, pass2016=p["S12_029"] or 0))
st = pd.DataFrame(st)
stg = st.groupby("group").agg(name=("name", "first"), lon=("lon", "mean"), lat=("lat", "mean"),
                              pass2024=("pass2024", "sum"), pass2016=("pass2016", "sum")).reset_index()
stg.to_csv(DATA / "stations.csv", index=False)
tree = BallTree(np.radians(stg[["lat", "lon"]].values), metric="haversine")
X = np.radians(d[["lat", "lon"]].values)
dist, idx = tree.query(X, k=1)
d["dist_nearest_st"] = dist[:, 0] * R * 1000
d["log_pass_nearest"] = np.log1p(stg["pass2024"].values[idx[:, 0]])
for km in (1, 3, 10):
    ind = tree.query_radius(X, r=km / R)
    d[f"log_pass_{km}km"] = np.log1p([stg["pass2024"].values[i].sum() for i in ind])
# 三大都市の中心（東京駅・大阪駅・名古屋駅）までの最短距離
metro = np.radians([[35.6812, 139.7671], [34.7025, 135.4959], [35.1709, 136.8815]])
mt = BallTree(metro, metric="haversine")
d["dist_metro"] = mt.query(X, k=1)[0][:, 0] * R

# --- 市区町村の人口（令和2年国勢調査、令和2年10月の境域） ---
c = pd.read_csv(RAW / "census2020_muni.csv", dtype=str)
c = c[~c["name"].str.contains("旧：")].drop_duplicates("code2020")
c = c[["code2020", "pop2020", "chg_rate", "area_km2", "density"]].rename(columns={"code2020": "muni"})
for k in ["pop2020", "chg_rate", "area_km2", "density"]:
    c[k] = pd.to_numeric(c[k], errors="coerce")
# 浜松市は2024年に区を再編（22138〜22140）。令和2年の区に対応しないため市全体（22130）の値を使う
d["muni_census"] = d["muni"].where(~d["muni"].isin(["22138", "22139", "22140"]), "22130")
d = d.merge(c.rename(columns={"muni": "muni_census"}), on="muni_census", how="left")
miss = d["pop2020"].isna()
print("国勢調査と結合できなかった地点:", miss.sum(), d.loc[miss, "muni"].unique()[:20])
d["log_muni_density"] = np.log(d["density"]); d["log_muni_pop"] = np.log(d["pop2020"]); d["muni_pop_change"] = d["chg_rate"]
# 20km 四方のブロック（空間ブロックCV用、緯度経度をおおよそ 20km に区切る）
d["block20"] = (np.floor(d["lat"] / 0.18)).astype(int).astype(str) + "_" + (np.floor(d["lon"] / 0.22)).astype(int).astype(str)
# 住所と、対数などに変換済みの元の列は落として保存（ファイルを小さくするため）
d.drop(columns=["address", "acreage", "pop2020", "chg_rate", "density", "area_km2"]).to_csv(DATA / "features.csv", index=False)
print(d.shape, d["land_use_class"].value_counts().to_dict())

