"""3つのデータを「地域×年×指標」の長い表にそろえる。
どの指標も「大きいほど良い」向きにそろえた列 good を作る（失業率は符号を反転）。"""
import pandas as pd
import numpy as np
from common import RAW, DATA

rows = []
p = pd.read_csv(RAW / "f01_pref_panel.csv")
for col, name, sign in [("unemp_rate", "完全失業率", -1), ("emp_rate", "就業率", 1), ("jor", "有効求人倍率", 1)]:
    d = p[["code", "year", col]].rename(columns={col: "value"})
    d["indicator"] = name
    d["sign"] = sign
    rows.append(d)

t = pd.read_csv(RAW / "f44_tfr_pref.csv")
t = t[(t.pref != "全国") & (t.year >= 1972)].copy()
codes = p.drop_duplicates("code")[["code", "pref"]]
t = t.merge(codes, on="pref", how="left")
assert t.code.notna().all(), "都道府県名の対応に失敗"
t = t.rename(columns={"tfr": "value"})[["code", "year", "value"]]
t["indicator"] = "合計特殊出生率"
t["sign"] = 1
rows.append(t)

pref = pd.concat(rows, ignore_index=True)
pref["good"] = pref["value"] * pref["sign"]
pref.to_csv(DATA / "pref_long.csv", index=False)
print(pref.groupby("indicator").agg(n=("value", "size"), y0=("year", "min"), y1=("year", "max"), regions=("code", "nunique")))

s = pd.read_csv(RAW / "f19_screening_muni.csv", dtype={"code": str})
s = s[s.n_colon > 0].copy()
s["rate"] = s.y_colon / s.n_colon * 100
s = s[["code", "year", "n_colon", "y_colon", "rate", "pop"]]
s.to_csv(DATA / "muni_screening.csv", index=False)
print("市区町村の検診:", s.code.nunique(), "団体", sorted(s.year.unique()))
