"""ベースライン：線形回帰（ヘドニック）。log(価格) を特徴量の線形和で説明"""
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from common import load, NUM, CAT, RES
from cvlib import oof, score

NUM_LIN = [c for c in NUM if c not in ("lat", "lon")]   # 線形では緯度経度は意味を持ちにくいので外す


def design(tr, te):
    X = []
    for part in (tr, te):
        x = part[NUM_LIN].copy()
        for c in NUM_LIN:
            x[c + "_na"] = x[c].isna().astype(int)
            x[c] = x[c].fillna(tr[c].median())
        x["log_dist_station"] = np.log(x["dist_station"] + 50)  # 0m（駅に近接）があるので 50m 足す
        X.append(pd.concat([x, pd.get_dummies(part[CAT].astype(str), dtype=float)], axis=1))
    X[1] = X[1].reindex(columns=X[0].columns, fill_value=0)
    mu, sd = X[0].mean(), X[0].std().replace(0, 1)
    return (X[0] - mu) / sd, (X[1] - mu) / sd


def fit_predict(tr, te):
    a, b = design(tr, te)
    return Ridge(alpha=1.0).fit(a, tr["y"]).predict(b)


if __name__ == "__main__":
    d = load()
    out = []
    for kind in ("random", "pref", "block20"):
        p = oof(d, fit_predict, kind)
        out.append(dict(model="線形回帰", cv=kind, **score(d["y"].values, p)))
        d[f"lin_{kind}"] = p
    r = pd.DataFrame(out); print(r.round(3))
    r.to_csv(RES / "baseline_linear.csv", index=False)
    d[["code", "y", "lin_random", "lin_pref", "lin_block20"]].to_csv(RES / "oof_linear.csv", index=False)
