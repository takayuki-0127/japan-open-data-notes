"""03c シミュレーションのサンプルの大きさを変える（学習 500・2000・20000 件、相関 0.9 と 0.99）"""
import numpy as np, pandas as pd
import lightgbm as lgb
from common import RES, SEED, METHODS
from interp import all_importances

rows = []
for ntr in [500, 2000, 20000]:
    for rho in [0.0, 0.9, 0.99]:
        for rep in range(8):
            rng = np.random.default_rng(SEED + 100 + rep)
            n = ntr + 2000
            x1 = rng.normal(size=n)
            x2 = rho * x1 + np.sqrt(1 - rho ** 2) * rng.normal(size=n)
            x3, x4 = rng.normal(size=n), rng.normal(size=n)
            y = x1 + 0.5 * x3 + 0.5 * rng.normal(size=n)
            X = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4})
            tr = np.arange(n) < ntr
            m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=10,
                                  random_state=SEED + rep, verbose=-1, n_jobs=2).fit(X[tr], y[tr])
            imp, _ = all_importances(m, X[~tr], y[~tr], n_shap=2000, n_curve=1000, n_repeats=5, seed=rep)
            for k in METHODS:
                s = imp[k] / imp[k].sum()
                rows.append(dict(n_train=ntr, rho=rho, rep=rep, method=k, x1=s["x1"], x2=s["x2"], x3=s["x3"], x4=s["x4"]))
        print(ntr, rho, flush=True)
d = pd.DataFrame(rows)
d.to_csv(RES / "simulation_n.csv", index=False)
print(d.groupby(["n_train", "rho", "method"])[["x1", "x2", "x4"]].mean().round(3).to_string())
