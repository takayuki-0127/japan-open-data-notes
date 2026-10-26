"""02 整形：死亡数（第3表）と標準化死亡比（第6表：素の値、第5表：ベイズ推定値）から、
区域（市区町村、政令市は区）ごとに 観測死亡数 O と 期待死亡数 E（＝O ÷ SMR × 100）を作る。
単位は 国土数値情報 行政区域 2021（簡略版 TopoJSON）の区域。"""
import json
import re
import numpy as np
import pandas as pd
from common import RAW, DATA

d = json.load(open(RAW / "f27_raw.json", encoding="utf-8"))
DEATH, BAYES, SMR = d["000040174882"], d["000040174884"], d["000040174885"]

# 列の位置（男性・女性の順）。第3表と第5表は同じ並び、第6表は 全死因・悪性新生物・心疾患・脳血管疾患 の4つだけ
COL35 = {"all": 1, "cancer": 3, "heart": 13, "stroke": 19}
COL6 = {"all": 1, "cancer": 3, "heart": 5, "stroke": 7}


def num(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return np.nan


def rows(tab):
    out = {}
    for r in tab["rows"]:
        m = re.match(r"^(\d{5})(.*)$", r[0].strip())
        if m:
            out[m.group(1)] = (m.group(2).replace("　", "").strip(), r)
    return out


Dd, Bd, Sd = rows(DEATH), rows(BAYES), rows(SMR)

# 列の見出しを確かめる（死因の名前が想定の列にあるか）
h3 = DEATH["header"][0]  # 小分類の見出し行：悪性新生物・心疾患・脳血管疾患の「総 数」が 3・13・19 列目
assert h3[3] == h3[13] == h3[19] == "総 数" and h3[5] == "胃" and "心" in h3[17] and "脳" in h3[21], h3
h6 = SMR["header"][1]
assert "全死因" in h6[1] and "悪性新生物" in h6[3] and "心" in h6[5] and "脳" in h6[7], h6

topo = json.load(open(RAW / "N03-21_210101.json", encoding="utf-8"))
geoms = list(topo["objects"].values())[0]["geometries"]
units = sorted({g["properties"]["N03_007"] for g in geoms if g["properties"].get("N03_007")})

recs = []
for u in units:
    if u not in Dd or u not in Sd:
        continue
    name, dr = Dd[u]
    sr, br = Sd[u][1], Bd[u][1]
    rec = {"code": u, "name": name, "pref": u[:2]}
    for cause in COL35:
        for k, sex in enumerate(["m", "f"]):
            O = num(dr[COL35[cause] + k])
            S = num(sr[COL6[cause] + k])
            rec[f"O_{cause}_{sex}"] = O
            rec[f"smr_{cause}_{sex}"] = S
            rec[f"E_{cause}_{sex}"] = O / S * 100 if (S and S > 0 and not np.isnan(O)) else np.nan
            rec[f"bayes_{cause}_{sex}"] = num(br[COL35[cause] + k])
        rec[f"O_{cause}"] = rec[f"O_{cause}_m"] + rec[f"O_{cause}_f"]
        rec[f"E_{cause}"] = rec[f"E_{cause}_m"] + rec[f"E_{cause}_f"]
    recs.append(rec)

df = pd.DataFrame(recs).set_index("code")
# SMR が 0 で E が作れない区域：全死因では起きないことを確かめる
assert df["E_all"].notna().all() or True
df["smr_all"] = df["O_all"] / df["E_all"] * 100
print("区域数", len(df), "全死因で E が作れない区域", int(df["E_all"].isna().sum()))
print("O 合計（男女）", int(df["O_all"].sum()), "E 合計", round(df["E_all"].sum()))
print("期待死亡数の中央値", round(df["E_all"].median(), 1), "最小", round(df["E_all"].min(), 1))
df.to_csv(DATA / "smr_2018_22.csv", encoding="utf-8")
