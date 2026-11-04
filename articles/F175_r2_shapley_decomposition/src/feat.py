"""特徴量（予測する日 D の前日 D−1 の夜に、D の24時間分を出す設定）

- 需要は D−1 の23時まで分かっている → 24時間前・168時間前（1週間前）の同じ時刻の値を使える
- 気温は D の日平均・最高・最低を使う（本来は予報値。実測で代用しているので、運用より良く出る）
"""
import numpy as np
import pandas as pd


def special_flags(dates):
    m, d = dates.dt.month, dates.dt.day
    nenmatsu = ((m == 12) & (d >= 29)) | ((m == 1) & (d <= 3))
    obon = (m == 8) & (d >= 13) & (d <= 16)
    gw = ((m == 4) & (d >= 29)) | ((m == 5) & (d <= 5))
    return nenmatsu.astype(int), obon.astype(int), gw.astype(int)


def make_features(df, tmean_shift=None):
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    if tmean_shift is not None:  # 気温の予報誤差を足す（頑健性）
        for c in ("temp_mean", "temp_max", "temp_min"):
            d[c] = d[c] + d["date"].map(tmean_shift).fillna(0).values
    d["dow"] = d.index.dayofweek
    d["daytype"] = np.where((d["holiday"] == 1) | (d["dow"] == 6), 2, np.where(d["dow"] == 5, 1, 0))
    d["nenmatsu"], d["obon"], d["gw"] = special_flags(d["date"])
    doy = d.index.dayofyear
    d["doy_sin"], d["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    d["month"] = d.index.month
    d["year"] = d.index.year + (d.index.dayofyear / 366)
    d["cdd"] = (d["temp_mean"] - 22).clip(lower=0)
    d["hdd"] = (16 - d["temp_mean"]).clip(lower=0)
    d["cdd_max"] = (d["temp_max"] - 28).clip(lower=0)
    d["lag24"] = d["demand"].shift(24)
    d["lag168"] = d["demand"].shift(168)
    daily = d["demand"].resample("D").mean()
    d["prevday_mean"] = d["date"].map(daily.shift(1))
    dt = d["temp_mean"].resample("D").first()
    d["temp_prev"] = d["date"].map(dt.shift(1))
    d["temp_change"] = d["temp_mean"] - d["temp_prev"]
    d["lag24_daytype"] = d["daytype"].shift(24)
    return d


LGB_FEATS = ["hour", "dow", "daytype", "holiday", "nenmatsu", "obon", "gw", "doy_sin", "doy_cos", "month", "year",
             "temp_mean", "temp_max", "temp_min", "humid_mean", "cdd", "hdd", "cdd_max", "temp_change",
             "lag24", "lag168", "prevday_mean", "lag24_daytype"]
LAG_FEATS = ["lag24", "lag168", "prevday_mean", "lag24_daytype"]
TEMP_FEATS = ["temp_mean", "temp_max", "temp_min", "humid_mean", "cdd", "hdd", "cdd_max", "temp_change"]


def ridge_matrix(d):
    """線形回帰用：時刻×曜日区分のダミー、時刻帯×冷暖房度日、ラグ"""
    X = pd.get_dummies(d["hour"].astype(str) + "_" + d["daytype"].astype(str), prefix="hd", dtype=float)
    blk = pd.cut(d["hour"], [-1, 5, 11, 17, 23], labels=["n", "m", "a", "e"]).astype(str)
    for b in ["n", "m", "a", "e"]:
        on = (blk == b).astype(float)
        for c in ("cdd", "hdd", "cdd_max"):
            X[f"{c}_{b}"] = on * d[c]
            X[f"{c}2_{b}"] = on * d[c] ** 2
    for c in ("nenmatsu", "obon", "gw", "doy_sin", "doy_cos", "year", "humid_mean", "temp_change"):
        X[c] = d[c]
    X["lag24"] = d["lag24"] * (d["daytype"] == d["lag24_daytype"])
    X["lag24_diff_type"] = d["lag24"] * (d["daytype"] != d["lag24_daytype"])
    X["lag168"] = d["lag168"]
    X["prevday_mean"] = d["prevday_mean"]
    return X
