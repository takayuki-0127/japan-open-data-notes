"""F03 の特徴量（地価公示2026年・25,565地点）から3大都市圏を取り出し、km 座標と空間ブロックを付ける"""
import numpy as np, pandas as pd
from common import DATA, AREAS, to_km

src = DATA / "raw" / "F03_features.csv"   # F03 の data/features.csv をそのまま置いたもの
d = pd.read_csv(src, dtype={"code": str, "muni": str, "pref": str})
rows = []
for area, prefs in AREAS.items():
    s = d[d["pref"].isin(prefs)].copy()
    s["area"] = area
    s["x_km"], s["y_km"] = to_km(s["lat"].values, s["lon"].values, area)
    for size in (5, 10, 20):
        s[f"blk{size}"] = (np.floor(s["x_km"] / size).astype(int).astype(str) + "_" +
                           np.floor(s["y_km"] / size).astype(int).astype(str))
    rows.append(s)
out = pd.concat(rows, ignore_index=True)
keep = ["code", "muni", "pref", "area", "land_use_class", "price", "lat", "lon", "x_km", "y_km",
        "blk5", "blk10", "blk20"] + [c for c in d.columns if c not in
        ("code", "muni", "pref", "land_use_class", "price", "lat", "lon", "block20", "city", "station", "price_2016",
         "muni_census")]
out = out[list(dict.fromkeys(keep))]
out.to_csv(DATA / "features_metro.csv", index=False)
print(out.groupby(["area", "land_use_class"]).size().unstack(fill_value=0))
