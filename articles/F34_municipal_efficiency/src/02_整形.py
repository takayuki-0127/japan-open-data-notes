"""02 整形：SSDSE-A-2026（主分析）と、社会・人口統計体系の2015年（年を変えた頑健性）から、
市区町村ごとの「入力（歳出・職員数）」と「出力（人口・高齢者・子ども・面積・施設）」の表を作る。"""
import csv, json, re
import numpy as np, pandas as pd
from common import RAW, DATA, group_of

# ---------- 主分析：SSDSE-A-2026 ----------
rows = list(csv.reader(open(RAW / "SSDSE-A-2026.csv", encoding="cp932")))
codes, years, names = rows[0], rows[1], rows[2]
df = pd.DataFrame(rows[3:], columns=codes)
df = df.rename(columns={"SSDSE-A-2026": "code", "Prefecture": "pref", "Municipality": "muni"})
df["code"] = df["code"].str[1:]
num = [c for c in df.columns if c not in ("code", "pref", "muni")]
df[num] = df[num].apply(pd.to_numeric, errors="coerce")

m = pd.DataFrame({
    "code": df["code"], "pref": df["pref"], "muni": df["muni"],
    # 入力
    "spend": (df["D3203"] - df["D320311"]) / 1e3,     # 歳出決算総額 − 災害復旧費（2022年度、百万円）
    "spend_all": df["D3203"] / 1e3,                    # 災害復旧費を含む
    "staff": df["D1202"],                              # 一般行政部門職員数（2024年）
    # 出力（需要の量）
    "pop": df["A1101"], "pop65": df["A1303"], "pop14": df["A1301"],
    "habitable_ha": df["B1103"],                       # 可住地面積（ha）
    "pupils": df["E2501"] + df["E3501"] + df["E3905"] + df["E3906"],   # 小中・義務教育学校の児童生徒数（2024年）
    "nursery": df["J250302"],                          # 保育所等数（2023年）
    "library": df["G1401"], "kominkan": df["G1201"],   # 図書館数・公民館数（2021年）
    # 2段階目の説明に使う
    "area_ha": df["B1101"], "keijo": df["D2203"],      # 経常収支比率（2022年度）
})
m["density"] = m["pop"] / (m["habitable_ha"] / 100)    # 可住地1km²あたり人口
m["aged"] = m["pop65"] / m["pop"] * 100
m["group"] = m["pop"].apply(group_of)
m["tokyo23"] = m["code"].str.startswith("131") & (m["code"].astype(int) < 13200)

# 財政力指数（2020年度）は社会・人口統計体系から
js = json.load(open(RAW / "ssds_municipal_2005_2020.json", encoding="utf-8"))


def ssds_table(key):
    t = js[key]
    head = [re.sub(r"_.*", "", h) for h in t[0]]
    d = pd.DataFrame(t[1:], columns=["region"] + head[1:])
    d["code"] = d["region"].str[:5]
    for c in head[1:]:
        d[c] = pd.to_numeric(d[c].str.replace(",", ""), errors="coerce")
    return d.drop(columns="region")


fz = ssds_table("2020b2")[["code", "D2201"]].rename(columns={"D2201": "zaiseiryoku"})
m = m.merge(fz, on="code", how="left")
m.to_csv(DATA / "municipal_2022.csv", index=False, encoding="utf-8")
print("主分析", len(m), "市区町村、欠測：", m[["spend", "staff", "pupils", "nursery", "zaiseiryoku"]].isna().sum().to_dict())
print(m.groupby("group")["code"].count())

# ---------- 年を変えた頑健性：2015年 ----------
a = ssds_table("2015b1")[["code", "A1101", "B1103", "J2503"]]
b = ssds_table("2015b2")[["code", "A1301", "A1303", "D3203"]]
p = a.merge(b, on="code")
p = p[p["code"].isin(m["code"])]      # 政令市の区を除き、2022年と同じ単位にそろえる
p = p.rename(columns={"A1101": "pop", "B1103": "habitable_ha", "J2503": "nursery",
                      "A1301": "pop14", "A1303": "pop65", "D3203": "spend_all"})
p["spend_all"] = p["spend_all"] / 1e3
p["group"] = p["pop"].apply(group_of)
p.to_csv(DATA / "municipal_2015.csv", index=False, encoding="utf-8")
print("2015年", len(p), "市区町村、欠測：", p.isna().sum()[p.isna().sum() > 0].to_dict())
