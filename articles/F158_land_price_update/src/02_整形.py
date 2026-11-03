"""地点の特徴量（F03）と 2017〜2026 年の価格を結合し、地点表と年×地点の長い表を作る"""
import numpy as np, pandas as pd
from common import RAW, DATA, YEARS

# 地点の特徴量は F03 と同じ（リポジトリの articles/F03_land_price_ml/data/features.csv）
F03 = RAW / "F03_features.csv"
if not F03.exists():
    F03 = RAW.parents[2] / "F03_land_price_ml" / "data" / "features.csv"
f = pd.read_csv(F03, dtype={"code": str, "muni": str, "pref": str})
h = pd.read_csv(RAW / "l01_price_history.csv", dtype=str)
# 属性移動：1文字目は選定状況、2〜14文字目のどれかが 1 なら、その年に地点の属性（地積・用途・駅距離など）が変わった
chg = np.column_stack([h[f"chg{y}"].str[1:].str.contains("1").values for y in YEARS])
h["attr_changed"] = chg.any(axis=1).astype(int)
pts = f.drop(columns=["price", "price_2016"]).merge(h[["code", "attr_changed"]], on="code")
pts.to_csv(DATA / "points.csv", index=False)
rows = []
for y in YEARS:
    p = pd.to_numeric(h[f"p{y}"])
    ok = (h["bits"].str[y - 1983] == "1") & (p > 0)
    rows.append(pd.DataFrame({"code": h.loc[ok, "code"], "year": y, "price": p[ok].astype(int)}))
panel = pd.concat(rows)
panel.to_csv(DATA / "panel.csv", index=False)
print(len(pts), len(panel), pts["attr_changed"].mean().round(3))
print(panel.groupby("year").size().to_dict())
