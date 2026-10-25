"""LightGBM をランダムCVと空間ブロックCV（都道府県・20km四方）で評価。頑健性もここで"""
import numpy as np, pandas as pd
import lightgbm as lgb
from common import load, NUM, CAT, RES, SEED
from cvlib import oof, score

PARAMS = dict(objective="regression", learning_rate=0.03, num_leaves=63, min_child_samples=20,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, n_estimators=1500,
              random_state=SEED, verbose=-1)


def make(features):
    def fp(tr, te):
        m = lgb.LGBMRegressor(**PARAMS).fit(tr[features], tr["y"])
        return m.predict(te[features])
    return fp


if __name__ == "__main__":
    d = load()
    FEAT = NUM + CAT
    rows, keep = [], {}
    for kind in ("random", "pref", "block20"):
        p = oof(d, make(FEAT), kind)
        keep[kind] = p
        rows.append(dict(model="LightGBM", setting="基本", cv=kind, n=len(d), **score(d["y"].values, p)))
        print(rows[-1])
    pd.DataFrame({"code": d["code"], "y": d["y"], **{f"lgb_{k}": v for k, v in keep.items()}}).to_csv(RES / "oof_lgbm.csv", index=False)
    # 頑健性
    variants = {
        "緯度・経度なし": [f for f in FEAT if f not in ("lat", "lon")],
        "用途地域なし": [f for f in FEAT if f != "use_district"],
        "乗降客数・人口なし（地点の属性だけ）": [f for f in FEAT if not (f.startswith("log_pass") or f.startswith("log_muni") or f in ("muni_pop_change", "dist_metro", "lat", "lon"))],
    }
    for name, fs in variants.items():
        for kind in ("random", "block20"):
            p = oof(d, make(fs), kind)
            rows.append(dict(model="LightGBM", setting=name, cv=kind, n=len(d), **score(d["y"].values, p))); print(rows[-1])
    for cls in ("住宅地", "商業地"):
        s = d[d["land_use_class"] == cls].reset_index(drop=True)
        for kind in ("random", "block20"):
            p = oof(s, make(FEAT), kind)
            rows.append(dict(model="LightGBM", setting=f"{cls}だけで学習", cv=kind, n=len(s), **score(s["y"].values, p))); print(rows[-1])
    d16 = load(2016).reset_index(drop=True)
    for kind in ("random", "block20"):
        p = oof(d16, make(FEAT), kind)
        rows.append(dict(model="LightGBM", setting="2016年の価格（属性は2026年）", cv=kind, n=len(d16), **score(d16["y"].values, p))); print(rows[-1])
    pd.DataFrame(rows).to_csv(RES / "cv_lgbm.csv", index=False)
