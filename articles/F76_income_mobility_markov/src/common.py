"""共通：パス・フォント・遷移行列と移動性の指標"""
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261028
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False
C1, C2, C3, G = '#2a6f97', '#e07a5f', '#81b29a', '#888888'


def rank_class(x, k):
    """各年の順位で k 区分に分ける（0＝いちばん低い、k−1＝いちばん高い）。同順位は平均順位"""
    r = pd.Series(x).rank(method='average').to_numpy()
    n = len(r)
    return np.minimum((np.floor((r - 0.5) * k / n)).astype(int), k - 1)


def level_class(rel, cuts):
    """相対所得（平均＝1）を、決めた境目で区分に分ける"""
    return np.searchsorted(np.asarray(cuts), np.asarray(rel), side='right')


def transition(a, b, k):
    """区分 a→b の件数と遷移行列（行で割合）。件数0の行は NaN"""
    n = np.zeros((k, k))
    for i, j in zip(a, b):
        n[int(i), int(j)] += 1
    with np.errstate(invalid='ignore', divide='ignore'):
        p = n / n.sum(1, keepdims=True)
    return n, p


def ergodic(P):
    """定常分布（P の固有値1の左固有ベクトル）"""
    w, v = np.linalg.eig(P.T)
    i = np.argmin(np.abs(w - 1))
    x = np.real(v[:, i]); x = x / x.sum()
    return x


def mobility(P, step=1):
    """移動性の指標：Shorrocks の M、とどまる割合（行の平均）、第2固有値と混ざり合う半減期（年）"""
    k = P.shape[0]
    M = (k - np.trace(P)) / (k - 1)
    ev = np.sort(np.abs(np.linalg.eigvals(P)))[::-1]
    l2 = ev[1] if len(ev) > 1 else np.nan
    hl = (np.log(0.5) / np.log(l2)) * step if 0 < l2 < 1 else np.inf
    return {'shorrocks': float(M), 'stay': float(np.trace(P) / k), 'lambda2': float(l2), 'halflife_years': float(hl)}


def lr_homogeneity(counts_list):
    """期間ごとの遷移行列が同じか（Anderson–Goodman の尤度比検定）。返り値：統計量、自由度、p値"""
    from scipy.stats import chi2
    tot = sum(counts_list)
    with np.errstate(invalid='ignore', divide='ignore'):
        Ptot = tot / tot.sum(1, keepdims=True)
    lr = 0.0; df = 0
    for n in counts_list:
        with np.errstate(invalid='ignore', divide='ignore'):
            P = n / n.sum(1, keepdims=True)
        m = (n > 0)
        lr += 2 * np.sum(n[m] * np.log(P[m] / Ptot[m]))
    for i in range(tot.shape[0]):
        nz_rows = sum(1 for n in counts_list if n[i].sum() > 0)
        df += (nz_rows - 1) * (int((tot[i] > 0).sum()) - 1)
    return float(lr), int(df), float(chi2.sf(lr, df)) if df > 0 else np.nan
