# 都道府県の共変量：人口密度（総人口÷可住地面積）、鉄道の乗降客数（人口千人あたり）、65歳以上割合
# 入力：SSDSE-E-2026.csv（統計センター）、F03 の stations.csv（国土数値情報 S12 2024）と features.csv（地価公示の地点、都道府県コード付き）
# 駅の都道府県は、最寄りの地価公示地点の都道府県で割り当てる（近似）
import sys, pandas as pd, numpy as np
from scipy.spatial import cKDTree
ssdse_e, stations, features, out = sys.argv[1:5]
e = pd.read_csv(ssdse_e, encoding="cp932", header=None)
cols = e.iloc[0].tolist(); body = e.iloc[3:].copy(); body.columns = cols
body = body[body["SSDSE-E-2026"] != "R00000"]
pref = body["Prefecture"].str.replace(r"(都|府|県)$", "", regex=True)
df = pd.DataFrame({"pref": pref.values,
                   "pop2024": body["A1101"].astype(float).values,
                   "habitable_km2": body["B1103"].astype(float).values / 100,  # ha→km2
                   "pop65": body["A1303"].astype(float).values})
df["density_hab"] = df.pop2024 / df.habitable_km2
df["share65"] = df.pop65 / df.pop2024
st = pd.read_csv(stations, dtype={"group": str})
st["pass"] = st.pass2024.where(st.pass2024 > 0, st.pass2016)  # 2024年が0（未掲載）の駅は2016年の値で補う
ft = pd.read_csv(features, usecols=["pref", "lat", "lon"], dtype={"pref": str})
tree = cKDTree(np.c_[ft.lat.values, ft.lon.values * np.cos(np.radians(36))])
_, idx = tree.query(np.c_[st.lat.values, st.lon.values * np.cos(np.radians(36))])
st["pcode"] = ft.pref.values[idx]
codes = {f"{i+1:02d}": p for i, p in enumerate("北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 長崎 熊本 大分 宮崎 鹿児島 沖縄".split())}
st["pref"] = st.pcode.map(codes)
agg = st.groupby("pref").agg(rail_pass=("pass", "sum"), n_station=("name", "size")).reset_index()
df = df.merge(agg, on="pref", how="left").fillna({"rail_pass": 0, "n_station": 0})
df["rail_per1000"] = df.rail_pass / df.pop2024 * 1000
df.to_csv(out, index=False, encoding="utf-8")
print(df.sort_values("density_hab").head(3)); print(df[["density_hab", "rail_per1000"]].corr(method="spearman"))
