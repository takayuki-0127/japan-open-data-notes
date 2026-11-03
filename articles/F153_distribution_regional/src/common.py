"""共通：階級別の度数から分位関数を作る、Wasserstein 距離とその分解"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

ROOT = Path(__file__).resolve().parents[1]
P = np.linspace(0.005, 0.995, 199)          # 分位点の格子（上下0.5%は使わない）
YG = np.linspace(0, 2000, 8001)              # 0〜2,000万円の格子（0.25万円刻み）
SIZE_N = {"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5, "p6": 6, "p7plus": 7.5}


def load(year=None):
    df = pd.read_csv(ROOT / "data/households_long.csv", dtype={"code": str, "inc_code": str})
    df = df[~df.inc_code.isin(["00", "99"])].copy()   # 総数と不詳を除く（不詳は除いて割り直す）
    if year is not None:
        df = df[df.year == year]
    return df


def bins_of(df_one):
    """1つの分布（lo, hi, households）→ 境目と累積割合"""
    g = df_one.groupby(["lo"], as_index=False).agg(hi=("hi", "first"), n=("households", "sum")).sort_values("lo")
    n = g.n.to_numpy(float)
    edges = list(g.lo.to_numpy(float)) + [np.inf]
    cdf = np.concatenate([[0], np.cumsum(n) / n.sum()])
    return np.array(edges), cdf


def quantiles(edges, cdf, method="pchip", p=P, tail_cap=None):
    """分位関数 Q(p)。method：pchip（累積分布を単調スプラインでつなぐ）／uniform（階級の中で一様）。
    最後の開いた階級はパレート（α は最後の2つの境目の生存割合から）。tail_cap を与えると上の裾を一様（上限 tail_cap）にする"""
    e = edges[:-1]                      # 有限の境目（0, …, 2000）
    c = cdf[:-1]
    s1, s2 = 1 - c[-2], 1 - c[-1]       # S(1500), S(2000)
    alpha = np.log(s1 / s2) / np.log(e[-1] / e[-2]) if s2 > 0 and s1 > s2 else 2.0
    out = np.empty_like(p)
    lo_mask = p <= c[-1]
    if method == "pchip":
        f = PchipInterpolator(e, c)
        Fy = f(YG)
        Fy = np.maximum.accumulate(np.clip(Fy, 0, 1))
        out[lo_mask] = np.interp(p[lo_mask], Fy, YG)
    else:
        out[lo_mask] = np.interp(p[lo_mask], c, e)
    pu = p[~lo_mask]
    if tail_cap is None:
        out[~lo_mask] = e[-1] * ((1 - pu) / s2) ** (-1 / alpha)
    else:
        out[~lo_mask] = e[-1] + (pu - c[-1]) / s2 * (tail_cap - e[-1])
    return out, alpha


def w2_decomp(q1, q2):
    """1次元の 2-Wasserstein 距離の2乗を、位置・広がり・形に分ける（分位点の格子で計算）。
    W² = (μ1−μ2)² + (σ1−σ2)² + 2σ1σ2(1−ρ)"""
    m1, m2 = q1.mean(), q2.mean()
    s1, s2 = q1.std(), q2.std()
    rho = np.corrcoef(q1, q2)[0, 1]
    loc = (m1 - m2) ** 2
    scale = (s1 - s2) ** 2
    shape = 2 * s1 * s2 * (1 - rho)
    w2sq = np.mean((q1 - q2) ** 2)
    return dict(w2=np.sqrt(w2sq), w2sq=w2sq, loc=loc, scale=scale, shape=shape, check=loc + scale + shape - w2sq)


def mix_quantiles(df_cells, weights, by, method="pchip", p=P):
    """セル（by の値）ごとの分布を weights（by → 割合）で混ぜた分布の分位関数（DFL 型の入れ替え）"""
    Fy = np.zeros_like(YG)
    tail = 0.0
    alphas = []
    for key, w in weights.items():
        if w <= 0:
            continue
        sub = df_cells[df_cells[by] == key]
        if sub.households.sum() <= 0:
            continue
        e, c = bins_of(sub)
        if method == "pchip":
            f = PchipInterpolator(e[:-1], c[:-1])
            F = np.maximum.accumulate(np.clip(f(YG), 0, 1))
        else:
            F = np.interp(YG, e[:-1], c[:-1])
        Fy += w * F
        alphas.append((w, 1 - c[-3], 1 - c[-2]))
    # 含めたセルの重みで割り直す
    wsum = sum(w for w, _, _ in alphas)
    Fy = Fy / wsum
    # 上の裾：混ぜた生存割合からパレート
    s1 = sum(w * a for w, a, _ in alphas) / wsum; s2 = sum(w * b for w, _, b in alphas) / wsum
    alpha = np.log(s1 / s2) / np.log(2000 / 1500) if s2 > 0 and s1 > s2 else 2.0
    Fy = np.maximum.accumulate(Fy)
    out = np.empty_like(p)
    cmax = Fy[-1]
    lo = p <= cmax
    out[lo] = np.interp(p[lo], Fy, YG)
    out[~lo] = 2000 * ((1 - p[~lo]) / s2) ** (-1 / alpha)
    return out
