"""02 整形：SSDSE-A から、母集団の代わりにする市区町村の表 data/frame.csv を作る。

- 今の値（y_*）：2026年版（国勢調査2020・経済センサス2021・人口動態2023・農林業センサス2019）
- 前回の値（x_*）：2021年版（国勢調査2015・経済センサス2016・人口動態2019・農林業センサス2014）
- 人口0の町（2026年版で1）を除く。前回の値が0・欠測の町は、前回の値を0として最小の層に入れる。
市区町村名は出力しない（地域コードと都道府県コードだけ）。
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
CODES = {"pop": "A1101", "households": "A7101", "employees": "C2208", "elderly": "A1303",
         "births": "A4101", "farms": "C310201"}


def read(year):
    raw = pd.read_csv(RAW / f"SSDSE-A-{year}.csv", encoding="cp932", header=None, dtype=str)
    codes = raw.iloc[0].tolist()
    body = raw.iloc[3:].reset_index(drop=True)
    body.columns = codes
    out = pd.DataFrame({"area_code": body.iloc[:, 0].values})
    for k, c in CODES.items():
        out[k] = pd.to_numeric(body[c].str.replace(",", ""), errors="coerce").values
    return out


cur = read("2026")
pri = read("2021")
df = cur.rename(columns={k: f"y_{k}" for k in CODES}).merge(
    pri.rename(columns={k: f"x_{k}" for k in CODES}), on="area_code", how="left")
df.insert(1, "pref", df["area_code"].str[1:3].astype(int))
df = df[df["y_pop"] > 0].reset_index(drop=True)
for k in CODES:
    df[f"x_{k}"] = df[f"x_{k}"].fillna(0)
df["y_aging_mean"] = df["y_elderly"] / df["y_pop"] * 100
df["x_aging_mean"] = np.where(df["x_pop"] > 0, df["x_elderly"] / df["x_pop"].where(df["x_pop"] > 0) * 100, np.nan)
df["x_aging_mean"] = df["x_aging_mean"].fillna(df["x_aging_mean"].median())
df.to_csv(BASE / "data" / "frame.csv", index=False)
print(df.shape, "前回の人口が0：", int((df["x_pop"] == 0).sum()))
print(df.describe().T[["mean", "50%", "max"]].round(1))
