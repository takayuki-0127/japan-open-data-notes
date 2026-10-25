"""CV の分け方と評価（02・03 で共通）"""
import numpy as np, pandas as pd
from sklearn.model_selection import KFold, GroupKFold
from common import SEED


def splits(d, kind, k=5):
    if kind == "random":
        return list(KFold(k, shuffle=True, random_state=SEED).split(d))
    groups = d["pref"] if kind == "pref" else d["block20"]
    # グループの並びをランダムにしてから GroupKFold（件数がほぼ均等になる）
    rng = np.random.default_rng(SEED)
    u = groups.unique(); perm = dict(zip(u, rng.permutation(len(u))))
    return list(GroupKFold(k).split(d, groups=groups.map(perm)))


def score(y, p):
    e = p - y
    ape = np.abs(np.exp(p) / np.exp(y) - 1)
    return dict(r2=1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum(), rmse_log=np.sqrt((e ** 2).mean()),
                median_ape=np.median(ape), within20=(ape <= 0.2).mean())


def oof(d, fit_predict, kind):
    p = np.full(len(d), np.nan)
    for tr, te in splits(d, kind):
        p[te] = fit_predict(d.iloc[tr], d.iloc[te])
    return p
