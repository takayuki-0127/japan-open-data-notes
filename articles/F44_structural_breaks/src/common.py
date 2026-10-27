"""共通の設定（パス・フォント・乱数の種）と、構造変化の推定の関数"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110


# ---------- 区間ごとの線形トレンド（水準と傾きの両方が折れ目で変わる）の最小二乗 ----------
def seg_ssr(y, t, dummies=None):
    """y = a + b*t (+ ダミー) を当てはめた残差平方和"""
    X = np.column_stack([np.ones_like(t), t] + ([] if dummies is None else [dummies]))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    return float(r @ r)


def ssr_matrix(y, t, h, dummy=None):
    """すべての区間 [i, j]（長さ h 以上）の残差平方和の表"""
    n = len(y)
    S = np.full((n, n), np.inf)
    for i in range(n):
        for j in range(i + h - 1, n):
            d = None
            if dummy is not None:
                d = dummy[i:j + 1]
                if d.sum() == 0 or d.sum() == len(d):
                    d = None
            S[i, j] = seg_ssr(y[i:j + 1], t[i:j + 1], d)
    return S


def bai_perron(y, t, h, max_m=5, dummy=None):
    """動的計画法で、折れ目の数 m ごとに残差平方和が最小になる位置を求める（Bai–Perron 2003）。
    返り値：{m: (ssr, [折れ目の位置（その区間の最後の添字）])}"""
    n = len(y)
    S = ssr_matrix(y, t, h, dummy)
    out = {0: (S[0, n - 1], [])}
    # cost[m][j] = 0..j を m+1 区間に分けた最小 SSR
    cost = [S[0].copy()]
    arg = [None]
    for m in range(1, max_m + 1):
        c = np.full(n, np.inf)
        a = np.full(n, -1)
        for j in range((m + 1) * h - 1, n):
            best, bk = np.inf, -1
            for k in range(m * h - 1, j - h + 1):
                v = cost[m - 1][k] + S[k + 1, j]
                if v < best:
                    best, bk = v, k
            c[j], a[j] = best, bk
        cost.append(c)
        arg.append(a)
        if not np.isfinite(c[n - 1]):
            break
        # 折れ目をたどる
        bks, j = [], n - 1
        for mm in range(m, 0, -1):
            k = int(arg[mm][j])
            bks.append(k)
            j = k
        out[m] = (c[n - 1], sorted(bks))
    return out


def info_criteria(res, n, k_per_seg=2, extra=0):
    """BIC と LWZ（Liu–Wu–Zidek）で折れ目の数を選ぶ"""
    rows = []
    for m, (ssr, bks) in res.items():
        p = (m + 1) * k_per_seg + m + extra  # 係数＋折れ目の位置
        bic = n * np.log(ssr / n) + p * np.log(n)
        lwz = n * np.log(ssr / (n - p)) + p * 0.299 * np.log(n) ** 2.1
        rows.append(dict(m=m, ssr=ssr, bic=bic, lwz=lwz, breaks=bks))
    return pd.DataFrame(rows)


def fit_segments(y, t, bks, dummy=None):
    """折れ目で区切った各区間の切片・傾き・当てはめ値"""
    edges = [-1] + list(bks) + [len(y) - 1]
    fitted = np.empty_like(y)
    segs = []
    for a, b in zip(edges[:-1], edges[1:]):
        ys, ts = y[a + 1:b + 1], t[a + 1:b + 1]
        cols = [np.ones_like(ts), ts]
        d = None
        if dummy is not None:
            d = dummy[a + 1:b + 1]
            if 0 < d.sum() < len(d):
                cols.append(d)
        X = np.column_stack(cols)
        beta, *_ = np.linalg.lstsq(X, ys, rcond=None)
        fitted[a + 1:b + 1] = X @ beta
        segs.append(dict(start=int(ts[0]), end=int(ts[-1]), slope=float(beta[1])))
    return fitted, segs
