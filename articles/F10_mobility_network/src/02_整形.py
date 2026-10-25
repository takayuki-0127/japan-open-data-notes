"""移動と通勤の行列を作る。"""
import io, csv, json, re
import numpy as np
import pandas as pd
import geopandas as gpd
from common import RAW, DATA

PREF = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県",
        "新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県",
        "奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県",
        "熊本県","大分県","宮崎県","鹿児島県","沖縄県"]

def num(c):
    c = c.strip().replace(",", "")
    return 0 if c in ("", "－", "-", "…", "x", "X") else int(float(c))

raw = json.load(open(RAW / "f10_migration_raw.json", encoding="utf-8"))
mats = {}
# 1990・2000・2010：長期時系列 第11表（日本人の移動。行＝移動前、列＝移動後）
for y in ["1990", "2000", "2010"]:
    rows = list(csv.reader(io.StringIO(raw[y]["Sheet1"])))
    hdr = rows[4]
    cols = {j: int(c) for j, c in enumerate(hdr) if re.fullmatch(r"\d\d", c.strip())}
    M = np.zeros((47, 47), int); seen = set(); tot = {}
    for r in rows[5:]:
        c = r[0].strip()
        if re.fullmatch(r"\d\d", c) and 1 <= int(c) <= 47 and int(c) not in seen:
            o = int(c); seen.add(o); tot[o] = num(r[3])
            for j, d in cols.items():
                if 1 <= d <= 47:
                    M[o - 1, d - 1] = num(r[j])
    assert len(seen) == 47 and all(M[o - 1].sum() == tot[o] for o in tot), y
    mats[y] = M
# 2025：年報 表2（行＝移動前、列＝移動後）。1990〜2010 とそろえるため日本人移動者を使う。移動者（外国人を含む）も別に保存
rows = list(csv.reader(io.StringIO(raw["2025"]["a002"])))
names = rows[4]; kind = rows[5]
colmap = {j: PREF.index(n) for j, n in enumerate(names) if n in PREF and kind[j] == "総数"}
for label, key in [("日本人移動者", "2025"), ("移動者", "2025all")]:
    M = np.zeros((47, 47), int)
    for r in rows[7:]:
        if len(r) > 6 and r[2] == label and r[6] in PREF:
            o = PREF.index(r[6])
            for j, d in colmap.items():
                M[o, d] = num(r[j])
    np.fill_diagonal(M, 0)
    mats[key] = M
for k, M in mats.items():
    pd.DataFrame(M, index=PREF, columns=PREF).to_csv(DATA / f"migration_{k}.csv")
    print("migration", k, M.sum())

# 都道府県の人口（SSDSE-B：2012年を 2010年の近似に、2023年を 2025年の近似に使う）
b = pd.read_csv(RAW / "SSDSE-B-2026.csv", encoding="cp932", skiprows=1)
b = b[["年度", "都道府県", "総人口", "日本人人口"]]
pop = b[b["年度"].isin([2012, 2023])].pivot(index="都道府県", columns="年度", values="日本人人口").reindex(PREF)
pop.columns = ["jp2012", "jp2023"]
pop.to_csv(DATA / "pref_pop.csv")

# 境界：都道府県の形と重心
g = gpd.read_file(RAW / "N03-21_210101.json")
g = g[g["N03_001"].isin(PREF)]
pref_g = g.dissolve(by="N03_001").reindex(PREF)
pref_g = pref_g.set_crs(4326, allow_override=True)
cent = pref_g.to_crs(6677).representative_point().to_crs(4326)
pd.DataFrame({"pref": PREF, "lon": cent.x.values, "lat": cent.y.values}).to_csv(DATA / "pref_xy.csv", index=False)
pref_g[["geometry"]].reset_index().to_file(DATA / "pref.geojson", driver="GeoJSON")

# 通勤：1都3県の市区町村（政令市は区、東京は特別区）の間の 15歳以上就業者
t = open(RAW / "f10_commute.csv", encoding="utf-8").read()
body, nm = t.split("#NAMES\n")
df = pd.read_csv(io.StringIO(body), dtype=str)
df["workers15"] = df["workers15"].astype(int)
name = dict(l.split(",", 1) for l in nm.strip().split("\n"))
agg = {"11000","12000","13000","14000","11100","12100","13100","14100","14130","14150"}
def fine(c):
    return c[:2] in ("11", "12", "13", "14") and c not in agg and not c.endswith("000")
od = df[(df["src"] != "all") & (df["cat"] == "02") & df["res_code"].map(fine) & df["work_code"].map(fine)]
od = od[od["res_code"] != od["work_code"]][["res_code", "work_code", "workers15"]]
od.columns = ["res", "work", "n"]
od.to_csv(DATA / "commute_od.csv", index=False)
resw = df[(df["src"] != "all") & (df["cat"] == "0") & df["res_code"].map(fine)][["res_code", "workers15"]]
selfw = df[(df["src"] != "all") & (df["cat"] == "01") & df["res_code"].map(fine)][["res_code", "workers15"]]
mun = resw.merge(selfw, on="res_code", suffixes=("_all", "_self")).rename(columns={"res_code": "code"})
mun["name"] = mun["code"].map(name)
mun.to_csv(DATA / "commute_municipalities.csv", index=False)
print("commute", len(od), od["n"].sum(), len(mun), mun["workers15_all"].sum())
