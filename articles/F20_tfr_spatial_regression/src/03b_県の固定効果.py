"""03b 追加の確認：都道府県ダミーを入れた OLS で、残差の空間的な偏りがどこまで消えるか"""
import json
import numpy as np
import pandas as pd
import spreg
from esda.moran import Moran
from common import RES
import importlib
m = importlib.import_module("03_分析")

df = m.sample("2018_22", m.X_MAIN)
w, P, _ = m.weights(list(df.index), "queen")
Z = m.zscore(df, m.X_MAIN)
D = pd.get_dummies(df["pref"], prefix="p", drop_first=True).astype(float)
X = np.c_[Z.values, D.values]
y = df[["tfr"]].values
ols = spreg.OLS(y, X)
mi = Moran(ols.u.flatten(), w, permutations=999)
err = spreg.ML_Error(y, X, w=w)
out = {"n": len(df), "r2": float(ols.r2), "beta": ols.betas.flatten()[1:7].tolist(), "se": np.sqrt(np.diag(ols.vm))[1:7].tolist(),
       "moran_resid": [float(mi.I), float(mi.p_sim)], "sem_lambda": float(err.lam),
       "sem_beta": err.betas.flatten()[1:7].tolist(), "sem_se": np.sqrt(np.diag(err.vm))[1:7].tolist()}
r = json.load(open(RES / "results.json", encoding="utf-8"))
r["pref_fe"] = out
json.dump(r, open(RES / "results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
