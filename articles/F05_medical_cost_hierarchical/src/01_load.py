"""01 取得・結合：市区町村×年度のパネル（data/panel.csv）を作る
元データ（data/raw/）
- iryohi_muni_r03_r05.csv：医療費の地域差分析 基礎データの「市区町村別データ」シート（30＝市町村国保、31＝後期高齢者医療）を、
  令和3〜5年度の Excel から列を絞って CSV にしたもの（idx_* が年齢調整後の地域差指数、cost_* が1人当たり実績医療費）
- census2020_muni.csv：令和2年国勢調査の市区町村別人口・人口増減率・人口密度
- beds_per100k_2025.csv / aged65_share_2023.csv：都道府県別の人口10万対病床数（医療施設調査）と65歳以上人口割合
"""
import numpy as np, pandas as pd
from common import RAW, DATA, YEARS, short

d = pd.read_csv(RAW / "iryohi_muni_r03_r05.csv")
d["fy"] = d["year"].map(YEARS)
c = pd.read_csv(RAW / "census2020_muni.csv")
c = c.dropna(subset=["pop2020"])
c["code"] = pd.to_numeric(c["code2020"], errors="coerce")
c = c[c["code"].notna() & (c["code"] % 1000 != 0)]
c = c[["code", "pop2020", "chg_rate", "density"]].drop_duplicates("code").astype({"code": int})
# 浜松市は2024年に区を再編（22138〜22140）。区の人口が国勢調査にないので、市全体の値で代用
hm = c[c["code"] == 22130]
for k in (22138, 22139, 22140):
    c = pd.concat([c, hm.assign(code=k)])
d = d.merge(c, on="code", how="left")
miss = d[d["pop2020"].isna()][["code", "pref", "muni"]].drop_duplicates()
print("人口が結合できない市区町村:", len(miss)); print(miss.to_string(index=False))
d = d.dropna(subset=["pop2020", "idx_total"])
# 政令指定都市は「区」と「市の合計」の両方の行があるので、市の合計の行を落として区を単位にする
names = set(d["muni"])
wards = [n for n in names if n.endswith("区") and "市" in n]
cities = {n.split("市")[0] + "市" for n in wards}
city = set(d.loc[d["muni"].isin(cities), "code"])
print("落とした政令市の合計行:", sorted(city))
d = d[~d["code"].isin(city)].copy()
for col in ["pop2020", "chg_rate", "density"]:
    d[col] = pd.to_numeric(d[col], errors="coerce")
beds = pd.read_csv(RAW / "beds_per100k_2025.csv")[["pref", "total"]].rename(columns={"total": "beds_per100k"})
age = pd.read_csv(RAW / "aged65_share_2023.csv")
d["pref_s"] = d["pref"].map(short)
d = d.merge(beds, left_on="pref_s", right_on="pref", how="left", suffixes=("", "_b")).drop(columns="pref_b")
d = d.merge(age, left_on="pref_s", right_on="pref", how="left", suffixes=("", "_a")).drop(columns="pref_a")
assert d["beds_per100k"].notna().all() and d["aged65_share_2023"].notna().all()
d.to_csv(DATA / "panel.csv", index=False)
print(d.groupby(["scheme", "fy"]).size())
