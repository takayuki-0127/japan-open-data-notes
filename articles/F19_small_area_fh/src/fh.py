"""Fay–Herriot モデル（REML）の最小限の実装。
  θ̂_i = x_i'β + u_i + e_i,  u_i ~ N(0, A),  e_i ~ N(0, D_i)（D_i は既知）
"""
import numpy as np
from scipy.optimize import minimize_scalar


def _parts(A, y, X, D):
    V = A + D
    W = 1.0 / V
    XtWX = X.T @ (X * W[:, None])
    beta = np.linalg.solve(XtWX, X.T @ (W * y))
    r = y - X @ beta
    return V, W, XtWX, beta, r


def reml_negll(logA, y, X, D):
    A = np.exp(logA)
    V, W, XtWX, beta, r = _parts(A, y, X, D)
    sign, logdet = np.linalg.slogdet(XtWX)
    return 0.5 * (np.sum(np.log(V)) + logdet + np.sum(W * r * r))


def fit(y, X, D):
    y, X, D = np.asarray(y, float), np.asarray(X, float), np.asarray(D, float)
    res = minimize_scalar(reml_negll, bounds=(np.log(1e-8), np.log(10 * np.var(y) + 1e-8)),
                          args=(y, X, D), method="bounded")
    A = float(np.exp(res.x))
    V, W, XtWX, beta, r = _parts(A, y, X, D)
    gamma = A / (A + D)
    synth = X @ beta
    eb = gamma * y + (1 - gamma) * synth
    # Prasad–Rao 型の MSE の近似（g1 + g2。g3 は省略）
    g1 = gamma * D
    inv = np.linalg.inv(XtWX)
    g2 = (1 - gamma) ** 2 * np.einsum("ij,jk,ik->i", X, inv, X)
    return dict(A=A, beta=beta, gamma=gamma, synth=synth, eb=eb, mse=g1 + g2)
