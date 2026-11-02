"""F123 本体：3つのデータ × 4つのモデル × 分け方（ランダム・ブロックの大きさ・都道府県・緩衝帯）で交差検証"""
import sys, time, json
import numpy as np, pandas as pd
import lightgbm as lgb
from scipy.spatial import cKDTree
from sklearn.linear_model import RidgeCV, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsRegressor
from common import load, folds, RES, SEED

LGB = dict(objective="regression", learning_rate=0.05, num_leaves=31, min_child_samples=20, subsample=0.8,
           subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1, n_jobs=2)
NEST = {"地価": 600, "出生率": 400, "気温": 400}

def fit_predict(model, tr, te, feats, name):
    if model == "LightGBM（特徴量＋座標）":
        cols = feats + ["xk", "yk"]
        m = lgb.LGBMRegressor(n_estimators=NEST[name], random_state=SEED, **LGB).fit(tr[cols], tr["y"])
        return m.predict(te[cols])
    if model == "LightGBM（特徴量だけ）":
        if name == "気温":   # 気温は特徴量が標高だけなので、標高だけの木
            cols = feats
        else:
            cols = feats
        m = lgb.LGBMRegressor(n_estimators=NEST[name], random_state=SEED, **LGB).fit(tr[cols], tr["y"])
        return m.predict(te[cols])
    if model == "線形回帰":
        cols = feats + (["xk", "yk"] if name == "気温" else [])
        med = tr[cols].median()   # 欠けている値は学習側の中央値で埋める（地価の一部の項目）
        Xtr, Xte = tr[cols].fillna(med), te[cols].fillna(med)
        sc = StandardScaler().fit(Xtr)
        m = RidgeCV(alphas=np.logspace(-3, 3, 13)).fit(sc.transform(Xtr), tr["y"])
        return m.predict(sc.transform(Xte))
    if model == "近くの地点の平均（座標だけ）":
        m = KNeighborsRegressor(n_neighbors=10, weights="distance").fit(tr[["xk", "yk"]], tr["y"])
        return m.predict(te[["xk", "yk"]])
    raise ValueError(model)

MODELS = ["LightGBM（特徴量＋座標）", "LightGBM（特徴量だけ）", "線形回帰", "近くの地点の平均（座標だけ）"]

def run(d, feats, name, fold, model, buffer=0.0):
    pred = np.full(len(d), np.nan)
    nn_dist = np.full(len(d), np.nan)
    for k in np.unique(fold):
        te = fold == k; trm = ~te
        tr_idx = np.where(trm)[0]
        if buffer > 0:   # テストの地点から buffer km 以内の学習地点を外す
            tt = cKDTree(d.loc[te, ["xk", "yk"]].values)
            dist, _ = tt.query(d.loc[trm, ["xk", "yk"]].values, k=1)
            tr_idx = tr_idx[dist > buffer]
        tr = d.iloc[tr_idx]
        pred[te] = fit_predict(model, tr, d[te], feats, name)
        dist2, _ = cKDTree(tr[["xk", "yk"]].values).query(d.loc[te, ["xk", "yk"]].values, k=1)
        nn_dist[te] = dist2
    y = d["y"].values
    r = y - pred
    out = dict(rmse=float(np.sqrt(np.mean(r ** 2))), mae=float(np.mean(np.abs(r))),
               r2=float(1 - np.sum(r ** 2) / np.sum((y - y.mean()) ** 2)),
               nn_km_median=float(np.median(nn_dist)))
    if name == "地価":
        out["med_ape"] = float(np.median(np.abs(np.exp(r) - 1)))   # 予測÷実際 の外れの中央値
    return out, pred

if __name__ == "__main__":
    names = sys.argv[1:] or ["気温", "出生率", "地価"]
    SIZES = {"地価": [5, 10, 20, 50, 100], "出生率": [10, 20, 50, 100, 200], "気温": [20, 50, 100, 200]}
    BUF_SIZE = {"地価": 20, "出生率": 50, "気温": 100}
    BUFS = {"地価": [5, 10, 20], "出生率": [10, 25, 50], "気温": [25, 50, 100]}
    SEEDS = [SEED, SEED + 1, SEED + 2]
    for name in names:
        d, feats = load(name)
        rows, oof = [], {"y": d["y"].values}
        t0 = time.time()
        part = RES / f"cv_{name}_part.csv"
        done = pd.read_csv(part) if part.exists() else pd.DataFrame()
        if len(done): rows = done.to_dict("records")
        for model in MODELS:
            if len(done) and model in set(done["model"]):
                print("skip", name, model, flush=True); continue
            for s in SEEDS:
                sch = [("random", None, 0.0)] + [("block", z, 0.0) for z in SIZES[name]]
                if s == SEED:
                    sch += [("pref", None, 0.0)] + [("block", BUF_SIZE[name], b) for b in BUFS[name]]
                for kind, size, buf in sch:
                    if kind == "pref" and s != SEED:
                        continue
                    f = folds(d, kind, seed=s, size=size)
                    res, p = run(d, feats, name, f, model, buf)
                    rows.append(dict(dataset=name, model=model, scheme=kind, size_km=size, buffer_km=buf, seed=s, n=len(d), **res))
                    if s == SEED and buf == 0 and (kind == "random" or size == BUF_SIZE[name]):
                        oof[f"{model}|{kind}{size or ''}"] = p
                    print(name, model, kind, size, buf, s, {k: round(v, 3) for k, v in res.items()}, f"{time.time()-t0:.0f}s", flush=True)
            pd.DataFrame(rows).to_csv(part, index=False)
            pd.DataFrame(oof).to_csv(RES / f"oof_{name}_{MODELS.index(model)}.csv.gz", index=False, compression="gzip")
        pd.DataFrame(rows).to_csv(RES / f"cv_{name}.csv", index=False)
        o = pd.DataFrame(oof); o["xk"], o["yk"] = d["xk"], d["yk"]
        o.to_csv(RES / f"oof_{name}.csv.gz", index=False, compression="gzip")
