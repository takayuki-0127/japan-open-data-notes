"""02 整形：令和7年国勢調査（人口等基本集計・原数値）の3つの表を、分析に使う形にする。

入力：data/raw/f120_census2025_raw.json（01_取得.md の手順で e-Stat の Excel をブラウザで読み、必要な部分を CSV の文字列にしたもの）
  t2_7 … 第2-7表 男女・年齢（5歳階級）別人口－市区町村（2000年（平成12年）市区町村含む）。国籍総数・男女総数の行だけ
  t1_2 … 第1-2表 人口・2020年の人口（組替）・面積など－市区町村（人口集中地区）
  t4_3 … 第4-3表 男女・年齢（5歳階級）・配偶関係別人口（15歳以上）－全国・都道府県の行だけ
出力：
  data/old_units_2025.csv … 2000年の市町村（3,252）ごとの2025年の人口
  data/did_2025.csv       … 市区町村ごとの人口集中地区（DID）の2025年の人口・面積と2020年の人口
  data/marital_2025.csv   … 全国の男女・5歳階級別の未婚・不詳の人数
"""
import io
import json

import numpy as np
import pandas as pd

from common import DATA, RAW

raw = json.load(open(RAW / "f120_census2025_raw.json", encoding="utf-8"))

# ---------------------------------------------------------------- 第2-7表：2000年の市町村ごとの2025年人口
t = pd.read_csv(io.StringIO(raw["t2_7"]), header=None, dtype=str)
t = t.rename(columns={0: "kind", 1: "pref2000", 2: "code2000", 3: "flag2000", 4: "pref2025", 5: "code2025", 6: "name", 7: "pop2025"})
t["pop2025"] = pd.to_numeric(t.pop2025, errors="coerce")
# kind：a 都道府県 / 1 政令市 / 0 区 / 2 市 / 3 町村 / 9（旧：○○）＝2000年の市町村
# flag2000 が "2000" の行は「2000年の市町村としても使える行」。合併でできた今の市町村の行は flag2000 が空で、その下に「（旧：○○）」の行が並ぶ
old_rows = t[(t.kind != "a") & (t.flag2000 == "2000")].copy()
old_rows["old_name"] = old_rows.name.str.replace(r"^\d{4}_", "", regex=True).str.replace(r"^（旧：(.*)）$", r"\1", regex=True)
dup = old_rows[old_rows.code2000.duplicated(keep=False)]
print("2つの今の市町村にまたがる2000年の市町村（分割編入）：", dup[["code2000", "old_name", "code2025", "pop2025"]].values.tolist())
old_rows = old_rows.sort_values("pop2025", ascending=False)
o = old_rows.groupby("code2000").agg(old_name=("old_name", "first"), code2025=("code2025", "first"),
                                      pop2025=("pop2025", "sum"), kind=("kind", "first")).reset_index()

old = pd.read_csv(DATA / "f94_old_units_2000.csv", dtype={"code": str})
m = old.merge(o, left_on="code", right_on="code2000", how="left")
miss = m[m.pop2025.isna()]
print("2000年の市町村", len(old), "2025年の値がない", len(miss))
if len(miss):
    print(miss[["code", "name", "type"]].head(20).to_string())
nat = t[(t.kind == "a")].pop2025.sum()
print("都道府県の合計（2025）", int(nat), " 旧市町村の合計", int(m.pop2025.sum()))
m[["code", "name", "type", "pop2000", "pop1995", "area", "old_name", "code2025", "pop2025"]].to_csv(DATA / "old_units_2025.csv", index=False)

# ---------------------------------------------------------------- 第1-2表：人口集中地区（市区町村ごとの合計）
d = pd.read_csv(io.StringIO(raw["t1_2"]), header=None, dtype=str, skiprows=6)
d = d.rename(columns={0: "kind", 1: "pref", 2: "name", 3: "did", 4: "pop2025", 7: "pop2020", 11: "area2025"})
d = d[d.did == "DID00_総数"].copy()
d["code5"] = d.name.str[:5]
for c in ["pop2025", "pop2020", "area2025"]:
    d[c] = pd.to_numeric(d[c], errors="coerce")
d = d[d.kind.isin(["1", "2", "3", "0"])]
d[["code5", "kind", "name", "pop2025", "pop2020", "area2025"]].to_csv(DATA / "did_2025.csv", index=False)
print("DID のある市区町村（2025）", int(d.pop2025.notna().sum()))

# ---------------------------------------------------------------- 第4-3表：全国の配偶関係
mr = pd.read_csv(io.StringIO(raw["t4_3"]), header=None, dtype=str, skiprows=2)
ages = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
        "65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95-99", "100+"]
mr = mr[(mr[1] == "00_全国") & (mr[3] == "0_国籍総数") & (mr[4].isin(["1_男", "2_女"]))]
rows = []
for _, r in mr.iterrows():
    for i, a in enumerate(ages):
        rows.append(dict(sex={"1_男": "男", "2_女": "女"}[r[4]], status=r[5], age=a, n=float(r[7 + i])))
x = pd.DataFrame(rows).pivot_table(index=["sex", "age"], columns="status", values="n").reset_index()
x.columns = ["sex", "age", "total", "unmarried", "married", "widowed", "divorced", "unknown"]
x["unmarried_pct"] = x.unmarried / (x.total - x.unknown) * 100          # 不詳を分母から除く（人口統計資料集と同じ扱い）
x["unmarried_pct_incl_unknown"] = x.unmarried / x.total * 100           # 頑健性：不詳を分母に含める
x["unknown_pct"] = x.unknown / x.total * 100
x.to_csv(DATA / "marital_2025.csv", index=False)
print(x[x.age.isin(["25-29", "30-34", "45-49", "50-54"])].round(1).to_string())

# ---------------------------------------------------------------- 不詳補完値（参考表）第4-3表：2020年（遡及）と2025年の全国
hk = json.load(open(RAW / "f120_census_hokan_marital.json", encoding="utf-8"))
rows = []
for key, yr in [("t4_3_hokan2020", 2020), ("t4_3_hokan2025", 2025)]:
    h = pd.read_csv(io.StringIO(hk[key]), header=None, dtype=str, skiprows=2)
    h = h[(h[3] == "0_国籍総数") & (h[4].isin(["1_男", "2_女"]))]
    for _, r in h.iterrows():
        for i, a in enumerate(ages):
            rows.append(dict(year=yr, sex={"1_男": "男", "2_女": "女"}[r[4]], status=r[5], age=a, n=pd.to_numeric(r[7 + i], errors="coerce")))
h = pd.DataFrame(rows).pivot_table(index=["year", "sex", "age"], columns="status", values="n").reset_index()
print("不詳補完値の配偶関係の区分：", [c for c in h.columns if c not in ("year", "sex", "age")])
h["unmarried_pct"] = h["1_未婚"] / h["0_総数"] * 100
h[["year", "sex", "age", "0_総数", "1_未婚", "unmarried_pct"]].to_csv(DATA / "marital_hokan_2020_2025.csv", index=False)
print(h[h.age.isin(["30-34", "45-49", "50-54"])][["year", "sex", "age", "unmarried_pct"]].round(1).to_string())
