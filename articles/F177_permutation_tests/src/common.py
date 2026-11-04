"""F177 共通：パス・乱数の種・並べ替え検定の関数"""
from pathlib import Path
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW, DATA, RES, FIG = ROOT / "data/raw", ROOT / "data", ROOT / "results", ROOT / "figures"
SEED = 177


def welch(a, b):
    """Welch の t 統計量と両側 p 値"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    t = (a.mean() - b.mean()) / np.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    return t, 2 * stats.t.sf(abs(t), df)


def student(a, b):
    r = stats.ttest_ind(a, b, equal_var=True)
    return r.statistic, r.pvalue


def stat_matrix(X, G, kind):
    """X: (N,) の値、G: (B,N) の真偽（True=グループ1）。各行の検定統計量を返す"""
    X = np.asarray(X, float)
    n1 = G.sum(1)
    n0 = G.shape[1] - n1
    if kind == "mean":
        s1 = (G * X).sum(1); s0 = X.sum() - s1
        return s1 / n1 - s0 / n0
    if kind == "t":
        s1 = (G * X).sum(1); s0 = X.sum() - s1
        q1 = (G * X ** 2).sum(1); q0 = (X ** 2).sum() - q1
        m1, m0 = s1 / n1, s0 / n0
        v1 = (q1 - n1 * m1 ** 2) / (n1 - 1); v0 = (q0 - n0 * m0 ** 2) / (n0 - 1)
        return (m1 - m0) / np.sqrt(v1 / n1 + v0 / n0)
    if kind == "rank":
        R = stats.rankdata(X)
        return (G * R).sum(1)
    if kind in ("median", "trim"):
        out = np.empty(G.shape[0])
        for i, g in enumerate(G):
            a, b = X[g], X[~g]
            if kind == "median":
                out[i] = np.median(a) - np.median(b)
            else:
                out[i] = stats.trim_mean(a, 0.2) - stats.trim_mean(b, 0.2)
        return out
    raise ValueError(kind)


def random_splits(N, k, B, rng):
    """N 個から k 個を選ぶ分け方を B 通り（真偽の行列）"""
    G = np.zeros((B, N), bool)
    idx = np.argsort(rng.random((B, N)), axis=1)[:, :k]
    np.put_along_axis(G, idx, True, axis=1)
    return G


def perm_p(obs, null, center=None):
    """両側の並べ替え p 値。(数 + 1) / (B + 1)。center があれば |T−center| で比べる"""
    null = np.asarray(null, float)
    if center is None:
        return (np.sum(np.abs(null) >= abs(obs) - 1e-12) + 1) / (len(null) + 1)
    return (np.sum(np.abs(null - center) >= abs(obs - center) - 1e-12) + 1) / (len(null) + 1)
