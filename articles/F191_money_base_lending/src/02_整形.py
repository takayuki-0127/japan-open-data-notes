"""長い形の CSV を月×系列の表にし、M2 を1本につなぐ。
M2：2003年4月以降は新しい M2（平残）、それより前は旧 M2+CD（平残）の前年比でさかのぼってつなぐ。
単位：億円（平均残高。loan_dom_end などは月末残高）。
"""
import numpy as np, pandas as pd
from common import RAW, DATA, SERIES

raw = pd.read_csv(RAW / "boj_raw.csv", dtype={"date": str})
raw = raw[raw.value.astype(str) != "null"].copy()
raw["value"] = raw.value.astype(float)
name = {c: n for d in SERIES.values() for c, n in d.items()}
raw["s"] = raw.code.map(name)
raw["month"] = pd.to_datetime(raw.date, format="%Y%m")
w = raw.pivot_table(index="month", columns="s", values="value").sort_index()
# M2 を1本に：2003/04 以降は新 M2、それより前は旧 M2+CD の動きで遡る
m2 = w["m2_new"].copy()
base = pd.Timestamp("2003-04-01")
ratio = w.loc[base, "m2_new"] / w.loc[base, "m2cd_old"]
old = w["m2cd_old"] * ratio
m2 = m2.where(m2.index >= base, old)
w["m2"] = m2
# つなぎ目の確認：重なる2004/04〜2008/04 の前年比の差
yo_new = np.log(w.m2_new).diff(12); yo_old = np.log(w.m2cd_old).diff(12)
ov = (yo_new - yo_old).loc["2004-04":"2008-04"]
print("M2 つなぎ：重なり期間の前年比の差（%pt） 平均", round(ov.mean() * 100, 2), "最大", round(ov.abs().max() * 100, 2))
w.index = w.index.strftime("%Y-%m")
w.round(0).to_csv(DATA / "monthly.csv")
print(w.notna().sum().to_string())
