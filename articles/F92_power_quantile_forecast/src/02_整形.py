"""02 整形：翌日のピーク需要を予測するための特徴量を作る

前日の夜に、翌日 D の1日のピーク（最大需要、MW）を予測する設定。
- 需要：D−1 のピーク、D−7 のピーク（どちらも D−1 の夜には分かっている）
- 気温：D の日平均・最高・最低（本来は予報値。実測で代用しているので運用より良く出る）
"""
import numpy as np
import pandas as pd
from common import RAW, DATA


def build(name):
    d = pd.read_csv(RAW / name, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    d = d.set_index("date").asfreq("D").reset_index()
    d["peak"] = d["peak_mw"]
    d["lag1"] = d["peak"].shift(1)
    d["lag7"] = d["peak"].shift(7)
    d["dow"] = d.date.dt.dayofweek
    md = d.date.dt.month * 100 + d.date.dt.day
    d["holiday"] = d["holiday"].fillna(0)
    d["offday"] = ((d.dow >= 5) | (d.holiday == 1)).astype(int)
    d["sat"] = (d.dow == 5).astype(int)
    d["obon"] = ((md >= 810) & (md <= 820)).astype(int)
    d["nenmatsu"] = ((md >= 1228) | (md <= 104)).astype(int)
    d["gw"] = ((md >= 429) & (md <= 506)).astype(int)
    d["lag1_off"] = d["offday"].shift(1)
    doy = d.date.dt.dayofyear
    d["doy_sin"], d["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    d["trend"] = (d.date - pd.Timestamp("2016-01-01")).dt.days / 365.25
    d["cdd"] = (d.temp_mean - 22).clip(lower=0)
    d["hdd"] = (14 - d.temp_mean).clip(lower=0)
    d["cddmax"] = (d.temp_max - 30).clip(lower=0)
    d["temp_change"] = d.temp_mean - d.temp_mean.shift(1)
    d["month"] = d.date.dt.month
    d["season"] = np.select([d.month.isin([7, 8, 9]), d.month.isin([12, 1, 2])], ["夏（7〜9月）", "冬（12〜2月）"], "その他")
    return d.dropna(subset=["peak", "lag1", "lag7", "temp_mean", "temp_change", "lag1_off"])


if __name__ == "__main__":
    for src, out in [("daily_tokyo.csv", "tokyo.csv"), ("daily_kansai.csv", "kansai.csv")]:
        d = build(src)
        d.to_csv(DATA / out, index=False)
        print(out, len(d), d.date.min().date(), d.date.max().date(), int(d.peak.mean()))
