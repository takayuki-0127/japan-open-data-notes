"""問い直し（結果を見てから足した）：灯油の値段が大きく動いた年（2009年・2016年の安い年、2022年からの高い年）に、
買う量はどれだけ動いたのか。2008〜2025年の前年比で、値段の変化と量の変化の関係（弾力性の目安）を見る。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
N = pd.read_csv(R / "kerosene_national_2007_2025.csv", index_col="year")
d = pd.DataFrame({"dlog_price": np.log(N.price).diff(), "dlog_qty": np.log(N.qty).diff()}).dropna()
k = np.polyfit(d.dlog_price, d.dlog_qty, 1)
r = float(np.corrcoef(d.dlog_price, d.dlog_qty)[0, 1])
trend = float(d.dlog_qty.mean())
d.to_csv(R / "requestion_price_qty_yoy.csv", float_format="%.5f")
out = {"slope": round(float(k[0]), 3), "intercept_pct": round(float(k[1]) * 100, 2), "corr": round(r, 3), "n": int(len(d)),
       "mean_qty_change_pct": round(trend * 100, 2),
       "y2009": {"price_pct": round(float(N.loc[2009, "price"] / N.loc[2008, "price"] - 1) * 100, 1), "qty_pct": round(float(N.loc[2009, "qty"] / N.loc[2008, "qty"] - 1) * 100, 1)},
       "y2016": {"price_pct": round(float(N.loc[2016, "price"] / N.loc[2015, "price"] - 1) * 100, 1), "qty_pct": round(float(N.loc[2016, "qty"] / N.loc[2015, "qty"] - 1) * 100, 1)},
       "y2022": {"price_pct": round(float(N.loc[2022, "price"] / N.loc[2021, "price"] - 1) * 100, 1), "qty_pct": round(float(N.loc[2022, "qty"] / N.loc[2021, "qty"] - 1) * 100, 1)}}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
