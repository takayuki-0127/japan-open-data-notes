"""02 整形：資料不足（ ]）・欠測（×）・2026年（年の途中）を除き、数値にする"""
import pandas as pd
from common import RAW, DATA

d = pd.read_csv(RAW / "jma_annual_a2.csv", dtype=str, encoding="utf-8-sig")
d["year"] = d["year"].astype(int)
cols = ["tmean", "tmax_mean", "tmax_abs", "d25", "d30", "d35"]
bad = d[cols].apply(lambda s: s.fillna("×").str.contains(r"\]|×|\)")).any(axis=1)
d = d[~bad & (d.year <= 2025)].copy()
for c in cols: d[c] = pd.to_numeric(d[c])
d = d.drop(columns="tmax_date")
d.to_csv(DATA / "annual_clean.csv", index=False, encoding="utf-8")
print(len(d), "行", d.station.nunique(), "地点", d.year.min(), "〜", d.year.max(), "除いた行", int(bad.sum()))
