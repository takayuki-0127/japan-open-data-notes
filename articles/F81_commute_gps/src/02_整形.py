"""02 整形：分析用の表を作る"""
import numpy as np, pandas as pd
from common import ROOT, T, Y, X

def load(name):
    d = pd.read_csv(ROOT / "data/raw" / name, dtype={"code": str, "pref": str})
    d = d[(d["pop"] > 0)].copy()
    d = d.replace([np.inf, -np.inf], np.nan)
    d["ward"] = d["income_from_city"].fillna(0).eq(1).astype(int)   # 政令市の区（所得は市の値）
    d["tokyo23"] = d["code"].str[:2].eq("13") & d["code"].str[2:].astype(int).lt(200)
    keep = ["code", "name", "pref", "pop", "ward", "tokyo23", Y, T, "unmarried"] + X
    return d[keep].dropna(subset=[Y, T, "unmarried"] + X)

for src, out in [("f20_municipal_2018_22.csv", "analysis_2018_22.csv"),
                 ("f20_municipal_2013_17.csv", "analysis_2013_17.csv")]:
    d = load(src)
    d.to_csv(ROOT / "data" / out, index=False)
    print(out, d.shape)
