"""02 整形：搬送人員と気温を「都道府県×日」の表にまとめる → data/panel.csv

- 気温は各都道府県の県庁所在地（埼玉は熊谷、滋賀は彦根）の気象台の値で代表させる
- WBGT の近似：最高気温と日平均の湿度から、オーストラリア気象局の簡易式
  WBGT ≈ 0.567×T + 0.393×e + 3.94（e は水蒸気圧 hPa）。日射と風を含まないので、環境省の WBGT とは一致しない
"""
import numpy as np
import pandas as pd
from common import RAW, DATA, block

hs = pd.read_csv(RAW / "heatstroke_daily_2015_2025.csv", parse_dates=["date"])
w = pd.read_csv(RAW / "jma_daily_2015_2025.csv", parse_dates=["date"])
for c in ["tmean", "tmax", "tmin", "rh"]:
    w[c] = pd.to_numeric(w[c], errors="coerce")
# 欠測は同じ地点の前後の日で線形補間（ごく少数）
w = w.sort_values(["pref", "date"])
nmiss = int(w[["tmax", "tmean", "rh"]].isna().sum().sum())
w[["tmean", "tmax", "tmin", "rh"]] = w.groupby("pref")[["tmean", "tmax", "tmin", "rh"]].transform(lambda s: s.interpolate(limit=3))
e = w.rh / 100 * 6.105 * np.exp(17.27 * w.tmax / (237.7 + w.tmax))
w["wbgt"] = (0.567 * w.tmax + 0.393 * e + 3.94).round(2)

df = w.merge(hs, on=["pref", "date"], how="left")
df["block"] = df.pref.map(block)
df.to_csv(DATA / "panel.csv", index=False)
print(df.shape, "気象の欠測（補間前）:", nmiss, "搬送の行:", df.total.notna().sum())
