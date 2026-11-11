"""F261 トレンド（潜在 GDP）の出し方。03_分析.py と 05_問い直し.py で共通に使う。"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.filters.bk_filter import bkfilter
from statsmodels.tsa.filters.cf_filter import cffilter
from statsmodels.tsa.filters.hp_filter import hpfilter

warnings.filterwarnings("ignore")
BREAKS = ["2008Q1", "2020Q1"]  # 折れ線トレンドの区切り（事前に固定）


def tr_hp(l, lam=1600):
    _, t = hpfilter(l, lamb=lam)
    return np.asarray(t)


def tr_bk(l):
    c = bkfilter(l, 6, 32, 12)
    t = np.full(len(l), np.nan)
    t[12:len(l) - 12] = l[12:len(l) - 12] - np.asarray(c).ravel()
    return t


def tr_cf(l):
    c, _ = cffilter(l, 6, 32, drift=True)
    return l - np.asarray(c)


def tr_ham(l, h=8, p=4):
    n = len(l)
    t = np.full(n, np.nan)
    X, Y, idx = [], [], []
    for s in range(p - 1, n - h):
        X.append([1.0] + [l[s - j] for j in range(p)])
        Y.append(l[s + h])
        idx.append(s + h)
    X, Y = np.array(X), np.array(Y)
    b = np.linalg.lstsq(X, Y, rcond=None)[0]
    t[idx] = X @ b
    return t


def tr_uc(l):
    m = sm.tsa.UnobservedComponents(l, level="smooth trend", autoregressive=2)
    r = m.fit(disp=False, maxiter=500, method="lbfgs")
    return np.asarray(r.smoothed_state[0])


def tr_lin(l, quarters):
    n = len(l)
    tt = np.arange(n, dtype=float)
    cols = [np.ones(n), tt]
    for b in BREAKS:
        if b in quarters:
            k = quarters.index(b)
            cols.append(np.maximum(tt - k, 0))
    X = np.column_stack(cols)
    beta = np.linalg.lstsq(X, l, rcond=None)[0]
    return X @ beta


def stat_trends(l, quarters, lam=1600, ham_h=8):
    return {
        "HP1600" if lam == 1600 else f"HP{lam}": tr_hp(l, lam),
        "BK": tr_bk(l),
        "CF": tr_cf(l),
        "HAM": tr_ham(l, h=ham_h),
        "UC": tr_uc(l),
        "LIN": tr_lin(l, quarters),
    }


def yoy(t):
    t = np.asarray(t, dtype=float)
    out = np.full(len(t), np.nan)
    out[4:] = 100 * (np.exp(t[4:] - t[:-4]) - 1)
    return out


def qoq_ann4(t):
    """前期比年率の4期平均（頑健性3）"""
    t = np.asarray(t, dtype=float)
    a = np.full(len(t), np.nan)
    a[1:] = 100 * (np.exp(4 * (t[1:] - t[:-1])) - 1)
    return pd.Series(a).rolling(4).mean().values


