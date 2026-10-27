"""社会・人口統計体系の表を、市区町村×年の分析用の表にする"""
import json, numpy as np, pandas as pd
from common import RAW, DATA

IND = {"C220832":"農業，林業","C220833":"漁業","C220835":"鉱業","C220836":"建設業","C220837":"製造業",
       "C220838":"電気・ガス・水道","C220839":"情報通信業","C220840":"運輸・郵便","C220841":"卸売・小売",
       "C220844":"金融・保険","C220845":"不動産・物品賃貸","C220846":"学術研究・専門サービス",
       "C220847":"宿泊・飲食","C220848":"生活関連・娯楽","C220849":"教育・学習支援","C220850":"医療・福祉",
       "C220851":"複合サービス","C220852":"その他サービス"}

def tab(rows):
    h = rows[0][1:]
    out = []
    for r in rows[1:]:
        code, name = r[0].split("_", 1)
        vals = [np.nan if v in ("", "-", "…", "x", "X", "***") else float(v.replace(",", "")) for v in r[1:]]
        out.append([code, name] + vals)
    return pd.DataFrame(out, columns=["code", "name"] + h)

raw = json.load(open(RAW / "f46_ssds_raw.json", encoding="utf-8"))

# 単位：政令市は市全体、東京23区は区ごと（政令市の区と「特別区部」は落とす）
base = tab(raw["P2015"])[["code", "name"]]
seirei = [c for c in base.code if c[2:] in ("100", "130", "140", "150") and c[:2] != "13"]
ward = set()
for c in seirei:
    for k in range(1, 30):
        ward.add(f"{int(c)+k:05d}")
keep = base[~base.code.isin(ward) & (base.code != "13100")].code
print("units", len(keep), "designated cities", len(seirei))

def emp(y):
    d = tab(raw[f"E{y}"]).set_index("code")
    return d.loc[d.index.isin(keep)]

E = {y: emp(y) for y in (2014, 2016, 2021)}
mig = []
for y in range(2009, 2025):
    d = tab(raw[f"M{y}"]).set_index("code")
    d = d.loc[d.index.isin(keep)]
    d["net"] = d["A5101"] - d["A5102"]
    mig.append(d[["net"]].rename(columns={"net": y}))
M = pd.concat(mig, axis=1)
P = {}
for y in (2005, 2010, 2015, 2020):
    d = tab(raw[f"P{y}"]).set_index("code")
    P[y] = d.loc[d.index.isin(keep)]

df = pd.DataFrame(index=keep.values)
df["name"] = base.set_index("code").loc[keep, "name"].values
df["pref"] = [c[:2] for c in df.index]
for y in (2005, 2010, 2015, 2020):
    df[f"pop{y}"] = P[y]["A1101"]
df["old15"] = P[2015]["A1303"] / P[2015]["A1101"]
df["work15"] = P[2015]["A1302"] / P[2015]["A1101"]
for y in (2014, 2016, 2021):
    df[f"emp{y}"] = E[y]["C2208"]
    for k in IND:
        df[f"{k}_{y}"] = E[y][k]
for y in range(2009, 2025):
    df[f"net{y}"] = M[y]
df.index.name = "code"
df.to_csv(DATA / "panel_municipal.csv", encoding="utf-8")
pd.Series(IND).rename("industry").to_csv(DATA / "industries.csv", encoding="utf-8")
print(df.shape, df[["emp2016", "emp2021", "net2016", "pop2015"]].describe().T)
print("missing industries 2016:", int(df[[f"{k}_2016" for k in IND]].isna().sum().sum()))
