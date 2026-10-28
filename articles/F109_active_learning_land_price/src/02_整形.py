"""F109 整形：シミュレーションで使う行列（LightGBM 用の表、k-means 用の標準化した数値、空間ブロック）と、データの概要"""
import numpy as np, pandas as pd, json
from common import load, NUM, CAT, DATA, RES
d = load()
Z = d[NUM].copy()
Z = Z.fillna(Z.median())
Z = (Z - Z.mean()) / Z.std()
np.save(DATA / "z_numeric.npy", Z.values.astype("float32"))
summ = dict(n=len(d), n_pref=int(d["pref"].nunique()), n_block20=int(d["block20"].nunique()),
            price_median=float(d["price"].median()), log_sd=float(d["y"].std()),
            share_by_class=d["land_use_class"].value_counts(normalize=True).round(4).to_dict())
json.dump(summ, open(RES / "data_summary.json", "w"), ensure_ascii=False, indent=1)
print(summ)
