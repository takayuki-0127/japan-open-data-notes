"""03b 答えが分かっている人工データ：x1 だけが効き、x2 は x1 と相関するだけ（効果0）。相関を強めると各手法は x2 をどう扱うか"""
import numpy as np, pandas as pd
import lightgbm as lgb
from common import RES, SEED, METHODS
from interp import all_importances

rows = []
for rho in [0.0, 0.5, 0.8, 0.9, 0.95, 0.99]:
    for rep in range(8):
        rng = np.random.default_rng(SEED + rep)
        n = 6000
        x1 = rng.normal(size=n)
        x2 = rho * x1 + np.sqrt(1 - rho ** 2) * rng.normal(size=n)
        x3, x4 = rng.normal(size=n), rng.normal(size=n)
        y = x1 + 0.5 * x3 + 0.5 * rng.normal(size=n)
        X = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4})
        tr = np.arange(n) < 4000
        m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=31, random_state=SEED + rep,
                              verbose=-1, n_jobs=2).fit(X[tr], y[tr])
        imp, _ = all_importances(m, X[~tr], y[~tr], n_shap=2000, n_curve=1000, n_repeats=5, seed=rep)
        for k in METHODS:
            s = imp[k] / imp[k].sum()
            rows.append(dict(rho=rho, rep=rep, method=k, x1=s["x1"], x2=s["x2"], x3=s["x3"], x4=s["x4"],
                             x1_raw=imp.loc["x1", k], x2_raw=imp.loc["x2", k]))
    print(rho, flush=True)
d = pd.DataFrame(rows)
d.to_csv(RES / "simulation.csv", index=False)
print(d.groupby(["rho", "method"])[["x1", "x2", "x3", "x4"]].mean().round(3).to_string())
