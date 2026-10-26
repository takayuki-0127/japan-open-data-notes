"""03 人口集中地区（DID）の人口・面積を市町村ごとに足し上げる（2005・2010・2015・2020年）。
- 国土数値情報 A16 の属性表は、1つの DID が複数の図形に分かれると同じ行がくり返されるので、(市区町村コード, DID番号) で重複を除く
- 2010・2015・2020 年はその年のファイルの値、2005 年は 2010 年ファイルの「前回」の値を使う（前回値 −99999＝前回は DID なし→0）
- 政令市の区は市にまとめる。市町村の範囲は 2026 年の市町村（SSDSE-A の地域コード）にそろえる
出力：data/did_muni.csv"""
import json
import numpy as np, pandas as pd
from common import RAW, DATA

ss = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", skiprows=2, dtype=str)
codes = set(ss["地域コード"].str[1:])
desig = sorted(c for c in codes if c[2:] in ("100", "130", "140", "150") and c[:2] != "13")   # 政令市（市全体のコード）

def to_city(c):
    if c in codes: return c
    p = [d for d in desig if d[:2] == c[:2] and 0 < int(c[2:]) - int(d[2:]) < 30]
    if p: return max(p)
    return {"43201": "43100",   # 熊本市（2012年に政令市）
            "03305": "03216", "04423": "04216", "11445": "11246", "17344": "17212", "23304": "23238", "40305": "40231",  # 町村から市になってコードが変わった
            "11226": "11203", "23481": "23213"}.get(c)   # 鳩ヶ谷市→川口市、一色町→西尾市（2011年の合併）

D = json.load(open(RAW / "did_ksj_A16.json"))
recs, lost = [], {}
for y, v in D.items():
    df = pd.DataFrame(v["rows"], columns=v["f"])
    for c in ["A16_004", "A16_005", "A16_006", "A16_007", "A16_008"]:
        df[c] = pd.to_numeric(df[c])
    df = df.drop_duplicates(["A16_002", "A16_004"])
    df["city"] = df.A16_002.map(to_city)
    lost[y] = sorted(df[df.city.isna()].A16_003.unique())
    df = df[df.city.notna()]
    yr = 2000 + int(y)
    g = df.groupby("city").agg(pop=("A16_005", "sum"), area=("A16_006", "sum"), n_did=("A16_004", "count"))
    g["year"] = yr; recs.append(g.reset_index())
    if y == "10":   # 2005年は前回の値
        df["pp"] = df.A16_007.clip(lower=0); df["pa"] = df.A16_008.clip(lower=0)
        g = df.groupby("city").agg(pop=("pp", "sum"), area=("pa", "sum"))
        g["n_did"] = df[df.A16_007 > 0].groupby("city").size()
        g["year"] = 2005; recs.append(g.reset_index())
print("2026年の市町村に対応しないコード：", lost)
long = pd.concat(recs)
long = long[long["pop"] > 0]
w = long.pivot_table(index="city", columns="year", values=["pop", "area", "n_did"])
w.columns = [f"{a}{b}" for a, b in w.columns]
w = w.reset_index().rename(columns={"city": "code5"})
w["code"] = "R" + w.code5
for y in (2005, 2010, 2015, 2020):
    w[f"dens{y}"] = w[f"pop{y}"] / w[f"area{y}"]   # 人/km²
nm = ss.set_index(ss["地域コード"])[["都道府県", "市区町村", "総人口"]]
w = w.join(nm, on="code")
w.to_csv(DATA / "did_muni.csv", index=False, encoding="utf-8-sig")
print("DID のある市町村：", {y: int(w[f"pop{y}"].notna().sum()) for y in (2005, 2010, 2015, 2020)})
print("全国の DID 人口（万人）：", {y: round(w[f"pop{y}"].sum() / 1e4) for y in (2005, 2010, 2015, 2020)})
print("4時点すべてにある市町村：", int(w[[f"pop{y}" for y in (2005, 2010, 2015, 2020)]].notna().all(axis=1).sum()))
