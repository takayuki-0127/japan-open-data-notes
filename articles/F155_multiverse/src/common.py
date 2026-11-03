"""共通：パス・図の設定・推定の部品（F155 マルチバース分析）"""
import itertools
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"
RES = ROOT / "results"
for p in (FIG, RES):
    p.mkdir(parents=True, exist_ok=True)
SEED = 20261103

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False

# 都道府県コード → 地方（8区分）
REGION = {}
for c in range(1, 48):
    REGION[c] = ("北海道" if c == 1 else "東北" if c <= 7 else "関東" if c <= 14 else "中部" if c <= 23
                 else "近畿" if c <= 30 else "中国" if c <= 35 else "四国" if c <= 39 else "九州・沖縄")
HIT3 = {3, 4, 7}  # 岩手・宮城・福島


def wls_resid(X, Y, w):
    """重み w で Y（n×m）を X に回帰した残差（FWL 用）。X は n×k"""
    sw = np.sqrt(w)[:, None]
    Q, _ = np.linalg.qr(X * sw)
    Ys = Y * sw
    R = Ys - Q @ (Q.T @ Ys)
    return R / sw  # 元の尺度の残差（重みをかけ直して使う）


def fwl_beta_cluster(yt, dt, w, groups, k_total):
    """FWL で残差化した y・d から係数と、クラスタ頑健（CR1）な標準誤差。
    yt・dt は残差化済み（n,）、k_total は全体の説明変数の数（自由度の補正用）"""
    sxx = np.sum(w * dt * dt)
    b = np.sum(w * dt * yt) / sxx
    e = yt - b * dt
    s = pd.Series(w * dt * e).groupby(groups).sum().values
    G = len(s); n = len(yt)
    c = G / (G - 1) * (n - 1) / max(n - k_total, 1)
    se = np.sqrt(c * np.sum(s ** 2)) / sxx
    return b, se, G


def ols_hc1(X, y, w=None, j=1):
    """（重み付き）最小二乗。X の j 列目の係数と HC1 標準誤差"""
    n, k = X.shape
    w = np.ones(n) if w is None else w
    sw = np.sqrt(w)
    Xs, ys = X * sw[:, None], y * sw
    XtX = Xs.T @ Xs
    inv = np.linalg.pinv(XtX)
    beta = inv @ (Xs.T @ ys)
    e = ys - Xs @ beta
    meat = (Xs * (e ** 2)[:, None]).T @ Xs
    V = inv @ meat @ inv * n / (n - k)
    return beta[j], np.sqrt(V[j, j])


def ols_beta(X, y, w=None, j=1):
    """係数だけ（ブートストラップ用に速く）"""
    if w is not None:
        sw = np.sqrt(w)
        X, y = X * sw[:, None], y * sw
    XtX = X.T @ X
    return np.linalg.solve(XtX + 1e-10 * np.eye(len(XtX)), X.T @ y)[j]


def shapley_r2(est, dims):
    """推定値のばらつきを、選択肢（次元）ごとに分ける（各次元のダミーで回帰した R² のシャープレイ値）"""
    est = np.asarray(est, float)
    tss = np.sum((est - est.mean()) ** 2)
    names = list(dims.keys())
    cache = {}

    def r2(sub):
        key = tuple(sorted(sub))
        if key in cache:
            return cache[key]
        if not sub:
            cache[key] = 0.0
            return 0.0
        Z = [np.ones(len(est))]
        for nm in sub:
            dmy = pd.get_dummies(pd.Series(dims[nm]).astype(str), drop_first=True).astype(float).values
            Z.append(dmy)
        Z = np.column_stack(Z)
        coef, *_ = np.linalg.lstsq(Z, est, rcond=None)
        v = 1 - np.sum((est - Z @ coef) ** 2) / tss
        cache[key] = v
        return v

    from math import factorial
    m = len(names)
    out = {}
    for nm in names:
        others = [x for x in names if x != nm]
        val = 0.0
        for r in range(len(others) + 1):
            for sub in itertools.combinations(others, r):
                wgt = factorial(r) * factorial(m - r - 1) / factorial(m)
                val += wgt * (r2(list(sub) + [nm]) - r2(list(sub)))
        out[nm] = val
    out["全部の組み合わせ（交互作用なし）"] = r2(names)
    return out


def summarize(est, lo, hi, w=None):
    est, lo, hi = map(lambda a: np.asarray(a, float), (est, lo, hi))
    w = np.ones(len(est)) if w is None else np.asarray(w, float)
    w = w / w.sum()
    o = np.argsort(est)
    cw = np.cumsum(w[o])

    def q(p):
        return float(est[o][np.searchsorted(cw, p)])
    return dict(n=int(len(est)), median=q(0.5), p05=q(0.05), p25=q(0.25), p75=q(0.75), p95=q(0.95),
                mean=float(np.sum(w * est)), min=float(est.min()), max=float(est.max()),
                share_pos=float(np.sum(w * (est > 0))),
                share_sig_pos=float(np.sum(w * (lo > 0))), share_sig_neg=float(np.sum(w * (hi < 0))))
