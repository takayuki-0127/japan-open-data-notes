"""02 整形：47都道府県のCSVを読み、普通の住宅の取引だけを残して data/condo_clean.csv.gz に書く"""
import zipfile, io
import numpy as np, pandas as pd
from common import RAW, RAW_ZIP, CLEAN, RES, walk_min

cols = ["種類", "市区町村コード", "都道府県名", "市区町村名", "最寄駅：距離（分）", "取引価格（総額）", "面積（㎡）", "建築年",
        "建物の構造", "用途", "取引時期", "改装", "取引の事情等"]
with zipfile.ZipFile(RAW / RAW_ZIP) as z:
    d = pd.concat([pd.read_csv(io.BytesIO(z.read(n)), encoding="cp932", usecols=cols, low_memory=False)
                   for n in sorted(z.namelist()) if n.endswith(".csv")], ignore_index=True)
log = [("元データ（中古マンション等・取引価格情報）", len(d))]
d = d[d["種類"] == "中古マンション等"]
d = d[d["取引の事情等"].isna()]; log.append(("取引の事情等（競売・関係者間など）がないもの", len(d)))
d = d[d["用途"].isna() | (d["用途"] == "住宅")]; log.append(("用途が住宅（または空欄）", len(d)))
yq = d["取引時期"].str.extract(r"(\d{4})年第(\d)四半期")
d["year"] = yq[0].astype(int); d["yq"] = yq[0] + "Q" + yq[1]
d["built"] = pd.to_numeric(d["建築年"].astype(str).str.extract(r"(\d{4})年")[0], errors="coerce")
d["age"] = d.year - d.built
d["area"] = pd.to_numeric(d["面積（㎡）"].astype(str).str.replace(",", ""), errors="coerce")
d["walk"] = d["最寄駅：距離（分）"].map(walk_min)
d["price"] = pd.to_numeric(d["取引価格（総額）"], errors="coerce")
d["ppm2"] = d.price / d.area / 10000
s = d["建物の構造"].astype(str)
d["struct"] = np.where(s.str.startswith("ＳＲＣ"), "SRC", np.where(s.str.startswith("ＲＣ"), "RC", "その他"))
d["renov"] = (d["改装"] == "改装済み").astype(int)
d = d.dropna(subset=["age", "area", "walk", "ppm2"]); log.append(("築年・面積・駅距離・価格がそろうもの", len(d)))
d = d[(d.age >= 0) & (d.age <= 60) & (d.area >= 15) & (d.area <= 200)]; log.append(("築0〜60年・15〜200㎡", len(d)))
# ㎡単価の極端な値は、都道府県ごとに上下0.5%を除く
q = d.groupby("都道府県名").ppm2.quantile([0.005, 0.995]).unstack()
lo, hi = d["都道府県名"].map(q[0.005]), d["都道府県名"].map(q[0.995])
d = d[(d.ppm2 >= lo) & (d.ppm2 <= hi)]; log.append(("都道府県ごとに㎡単価の上下0.5%を除く", len(d)))
out = pd.DataFrame({"pref": d["都道府県名"], "muni": d["市区町村コード"].astype(int).astype(str).str.zfill(5), "yq": d.yq, "year": d.year,
                    "age": d.age.astype(int), "built": d.built.astype(int), "area": d.area, "walk": d.walk, "ppm2": d.ppm2.round(3),
                    "struct": d.struct, "renov": d.renov})
out.to_csv(CLEAN, index=False, compression="gzip")
pd.DataFrame(log, columns=["段階", "件数"]).to_csv(RES / "sample_log.csv", index=False)
print(pd.DataFrame(log)); print(CLEAN, len(out))
