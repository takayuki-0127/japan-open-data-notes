"""共通の関数：パスの設定、県と年の固定効果つき回帰、県でクラスターした標準誤差、wild cluster bootstrap。"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"
for d in (DATA, RES, FIG):
    d.mkdir(exist_ok=True)
SEED = 20261114


def design(df, regs, unit="code", time="year"):
    """回帰の行列（定数・県ダミー・年ダミー・説明変数）を作る。説明変数は先頭の列に置く。"""
    U = pd.get_dummies(df[unit], prefix="u", drop_first=True, dtype=float)
    T = pd.get_dummies(df[time], prefix="t", drop_first=True, dtype=float)
    X = pd.concat([df[regs].astype(float).reset_index(drop=True), U.reset_index(drop=True),
                   T.reset_index(drop=True)], axis=1)
    X.insert(len(regs), "const", 1.0)
    return X


def ols_cluster(y, X, groups):
    """OLS と、県でクラスターした分散（小標本補正つき、Stata と同じ）。"""
    y, Xv = np.asarray(y, float), np.asarray(X, float)
    XtXi = np.linalg.pinv(Xv.T @ Xv)
    b = XtXi @ Xv.T @ y
    e = y - Xv @ b
    g = np.asarray(groups)
    G = len(np.unique(g))
    n, k = Xv.shape
    meat = np.zeros((k, k))
    for gg in np.unique(g):
        s = Xv[g == gg].T @ e[g == gg]
        meat += np.outer(s, s)
    c = G / (G - 1) * (n - 1) / (n - k)
    V = c * XtXi @ meat @ XtXi
    return b, V, e


def fe_reg(df, y, regs, unit="code", time="year"):
    """固定効果つき回帰。説明変数の係数・標準誤差・分散行列を返す。"""
    d = df.dropna(subset=[y] + regs).reset_index(drop=True)
    X = design(d, regs, unit, time)
    b, V, _ = ols_cluster(d[y], X, d[unit])
    k = len(regs)
    return {"b": b[:k], "V": V[:k, :k], "se": np.sqrt(np.diag(V)[:k]), "n": len(d), "G": d[unit].nunique()}


def wild_cluster_p(df, y, reg, controls=(), unit="code", time="year", B=9999, weights="rademacher", seed=SEED):
    """帰無仮説（係数=0）で制約した wild cluster bootstrap の p 値（t 統計量で比べる、両側）。"""
    d = df.dropna(subset=[y, reg] + list(controls)).reset_index(drop=True)
    X = np.asarray(design(d, [reg] + list(controls), unit, time), float)
    yv = d[y].to_numpy(float)
    g = d[unit].to_numpy()
    b, V, _ = ols_cluster(yv, X, g)
    t0 = b[0] / np.sqrt(V[0, 0])
    Xr = X[:, 1:]
    br = np.linalg.pinv(Xr.T @ Xr) @ Xr.T @ yv
    fit_r, er = Xr @ br, yv - Xr @ br
    groups, inv = np.unique(g, return_inverse=True)
    G = len(groups)
    rng = np.random.default_rng(seed)
    if weights == "rademacher":
        W = rng.choice([-1.0, 1.0], size=(B, G))
    else:  # Webb の6点
        pts = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])
        W = rng.choice(pts, size=(B, G))
    XtXi = np.linalg.pinv(X.T @ X)
    A = XtXi @ X.T                       # b = A y
    n, k = X.shape
    c = G / (G - 1) * (n - 1) / (n - k)
    a0 = A[0]                             # 処置の係数だけ使う
    ts = np.empty(B)
    # 処置の係数の分散は、残差を県ごとに足したものから計算できる：var = c * sum_g (a0_g · e_g)^2
    for i in range(B):
        ys = fit_r + er * W[i, inv]
        bs = A @ ys
        es = ys - X @ bs
        sg = np.bincount(inv, weights=a0 * es, minlength=G)
        ts[i] = bs[0] / np.sqrt(c * np.sum(sg ** 2))
    return float(np.mean(np.abs(ts) >= abs(t0))), float(t0)


def save_json(obj, name):
    def conv(o):
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))
    (RES / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=conv), encoding="utf-8")


def r(x, k=4):
    return float(np.round(x, k))
