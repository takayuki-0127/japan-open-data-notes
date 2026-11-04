"""共通：データの読み込み、層の作り方、配分、分散の式。"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RES = BASE / "results"
FIG = BASE / "figures"
for d in (DATA / "raw", RES, FIG):
    d.mkdir(parents=True, exist_ok=True)
SEED = 20261105

# 推定したい値（全国の合計。aging_mean だけは市区町村の単純平均）
Y = {
    "households": ("A7101", "世帯数"),
    "employees": ("C2208", "従業者数（民営）"),
    "elderly": ("A1303", "65歳以上人口"),
    "births": ("A4101", "出生数"),
    "farms": ("C310201", "農家数（販売農家）"),
    "aging_mean": (None, "高齢化率の単純平均"),
}
Y_ORDER = list(Y)

# 地方区分（都道府県コード → 8地方）
REGION = {}
for p in range(1, 48):
    if p == 1:
        r = "北海道"
    elif p <= 7:
        r = "東北"
    elif p <= 14:
        r = "関東"
    elif p <= 23:
        r = "中部"
    elif p <= 30:
        r = "近畿"
    elif p <= 35:
        r = "中国"
    elif p <= 39:
        r = "四国"
    else:
        r = "九州・沖縄"
    REGION[p] = r


def load():
    """data/frame.csv：1行＝市区町村。y_*（今の値）と x_*（前回の値）。"""
    return pd.read_csv(DATA / "frame.csv")


# ---------------------------------------------------------------- 層の作り方
def strata_quantile(x, H):
    """前回の人口の対数で、件数がほぼ同じ H 層に分ける。"""
    r = pd.Series(np.log1p(x)).rank(method="first").to_numpy()
    return np.minimum((r - 1) * H // len(x), H - 1).astype(int)


def strata_cumsqrtf(x, H, bins=200):
    """Dalenius–Hodges の累積√f 法（前回の人口の対数の度数で境目を決める）。"""
    lx = np.log1p(x)
    cnt, edges = np.histogram(lx, bins=bins)
    c = np.cumsum(np.sqrt(cnt))
    cuts = [edges[np.searchsorted(c, c[-1] * k / H) + 1] for k in range(1, H)]
    return np.searchsorted(np.array(cuts), lx, side="right").astype(int)


def strata_region(pref):
    names = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
    return np.array([names.index(REGION[p]) for p in pref])


# ---------------------------------------------------------------- 配分
def _round_alloc(target, Nh, n, nmin=2):
    """実数の配分を、合計 n・各層 nmin 以上 Nh 以下の整数に丸める（全数の層を先に確定）。"""
    Nh = np.asarray(Nh)
    H = len(Nh)
    nh = np.zeros(H, int)
    fixed = np.zeros(H, bool)
    w = np.asarray(target, float).copy()
    rest = n
    for _ in range(H + 1):
        free = ~fixed
        if w[free].sum() <= 0:
            share = np.where(free, Nh, 0) / Nh[free].sum() * rest
        else:
            share = np.where(free, w, 0) / w[free].sum() * rest
        over = free & (share >= Nh)
        if not over.any():
            break
        nh[over] = Nh[over]
        fixed |= over
        rest = n - nh[fixed].sum()
    free = ~fixed
    base = np.floor(share).astype(int)
    base = np.where(free, np.clip(base, np.minimum(nmin, Nh), Nh), nh)
    base = np.minimum(base, Nh)
    # 合計を n に合わせる（端数の大きい順に足す／小さい順に引く）
    frac = np.where(free, share - np.floor(share), -1)
    while base.sum() < n:
        cand = np.where(free & (base < Nh), frac, -np.inf)
        k = int(np.argmax(cand))
        base[k] += 1
        frac[k] = -0.5
    while base.sum() > n:
        cand = np.where(free & (base > np.minimum(nmin, Nh)), frac, np.inf)
        k = int(np.argmin(cand))
        base[k] -= 1
        frac[k] = 2
    return base


def allocate(h, n, kind, s=None):
    """kind: prop（比例）, equal（等配分）, neyman（N_h S_h に比例。s は層ごとの標準偏差）。"""
    H = h.max() + 1
    Nh = np.bincount(h, minlength=H)
    if kind == "prop":
        t = Nh.astype(float)
    elif kind == "equal":
        t = np.ones(H)
    elif kind == "neyman":
        t = Nh * np.asarray(s, float)
    else:
        raise ValueError(kind)
    return _round_alloc(t, Nh, n)


def strat_sd(v, h):
    H = h.max() + 1
    return np.array([np.std(v[h == k], ddof=1) if (h == k).sum() > 1 else 0.0 for k in range(H)])


def var_total(y, h, nh):
    """層別の単純無作為抽出で、合計の推定量の分散（式で厳密に）。"""
    H = h.max() + 1
    Nh = np.bincount(h, minlength=H)
    S2 = strat_sd(y, h) ** 2
    return float(np.sum(Nh**2 * (1 - nh / Nh) * S2 / nh))


def var_srs(y, n):
    N = len(y)
    return float(N**2 * (1 - n / N) * np.var(y, ddof=1) / n)
