"""エージェントベースのモデル（人口と店の需要のシミュレーション）。

1つの町を 10×10 の区画に分け、区画ごとに住民がいる。住民は自分の区画から近い店ほど
よく使い（距離で減る重み exp(-d/λ)）、町の外（郊外の大型店・通販など）にも一定の重み W_out
で流れる。店は年間の売上（住民の支出の合計）が自分の固定費 F を K 年続けて下回ると閉じる。
店主の引退などで毎年 q の割合が閉じ、（閉店の数 × 倍率）の出店候補が人口に比例した場所に現れ、
見込み売上が固定費を上回れば出店する。

単位：住民1人あたりの年間の町内での買い物を 1 とする（売上は「何人分の支出か」）。
"""
from dataclasses import dataclass, replace

import numpy as np

G = 10  # 区画は G×G


@dataclass(frozen=True)
class Params:
    lam: float = 1.5        # 距離の減り方（km）。λ km 離れると重みが 1/e
    w_out0: float = 0.25    # 町の外への重み（最初の年の町内の重みに対する比。0.25 なら支出の20%が町の外）
    g_out: float = 0.0      # 町の外への重みの年あたりの伸び（対数）
    margin_lo: float = 0.6  # 最初の年の「固定費 ÷ 売上」の下限（上限は 1）
    k_exit: int = 2         # 何年続けて赤字なら閉じるか
    q_churn: float = 0.02   # 引退などで閉じる割合（年）と、同じ数の出店候補
    rho: float = 0.3        # 人口の集まり方（町の一辺に対する割合。小さいほど中心に集まる）
    periphery: float = 0.0  # 人口減が周辺ほど速い度合い（0 なら一様に減る）
    entry_mult: float = 1.0 # 出店候補の多さ（閉店の割合 q に対する倍率）。実データに合わせて校正する


def town_geometry(area_km2, rho):
    L = float(np.clip(np.sqrt(max(area_km2, 1.0)), 1.0, 40.0))
    xs = (np.arange(G) + 0.5) / G * L
    cx, cy = np.meshgrid(xs, xs)
    cx, cy = cx.ravel(), cy.ravel()
    r = np.hypot(cx - L / 2, cy - L / 2)
    w = np.exp(-r / (rho * L))
    return L, cx, cy, r / (L / 2 * np.sqrt(2)), w / w.sum()


def shares(dist, lam, w_out):
    """dist: 区画 × 店 の距離。区画ごとの店への支出の割合と、町の外への割合。"""
    if dist.shape[1] == 0:
        return np.zeros_like(dist), np.ones(dist.shape[0])
    ww = np.exp(-dist / lam)
    den = ww.sum(1, keepdims=True) + w_out
    return ww / den, (w_out / den[:, 0])


def simulate(pop_path, area_km2, n_stores0, p: Params, rng, record_access=False):
    """pop_path: 年ごとの人口（最初の年＝店の数を合わせる年）。

    町の外への重みは、区画ごとに「最初の年の町内の店への重みの合計 × w_out0」とする
    （最初の年は、どの区画でも支出の w_out0/(1+w_out0) が町の外へ流れる）。店が減って
    町内の重みが小さくなると、その区画の住民はより多くを町の外で買う。
    返り値：年ごとの店の数、町の外に流れた支出の割合、（record_access なら）
    いちばん近い店まで 1km・2km を超える住民の割合。
    """
    L, cx, cy, rr, w0 = town_geometry(area_km2, p.rho)
    cell = L / G
    T = len(pop_path)
    n0 = int(max(n_stores0, 0))
    c = rng.choice(G * G, size=n0, p=w0)
    sx = cx[c] + (rng.random(n0) - 0.5) * cell
    sy = cy[c] + (rng.random(n0) - 0.5) * cell

    def wmat(xx, yy):
        return np.exp(-np.hypot(cx[:, None] - xx[None, :], cy[:, None] - yy[None, :]) / p.lam)

    def cell_pop(t):
        frac_decl = 1 - pop_path[t] / pop_path[0]
        w = w0 * np.exp(-p.periphery * frac_decl * rr * 4)
        return pop_path[t] * w / w.sum()

    W = wmat(sx, sy)
    base_in = W.sum(1) if n0 else np.ones(G * G)
    base_in = np.maximum(base_in, np.exp(-L / p.lam))
    P0 = cell_pop(0)
    out0 = p.w_out0 * base_in
    den = W.sum(1) + out0
    R0 = (P0[:, None] * W / den[:, None]).sum(0)
    F = R0 * rng.uniform(p.margin_lo, 1.0, size=n0)
    ratio_pool = (F / np.maximum(R0, 1e-12)) if n0 else np.array([0.8])
    bad = np.zeros(n0, dtype=int)
    n_hist, leak_hist, acc1, acc2 = [n0], [float((P0 * out0 / den).sum() / P0.sum())], [], []

    def access(Pc, xx, yy):
        if len(xx) == 0:
            return 1.0, 1.0
        dmin = np.hypot(cx[:, None] - xx[None, :], cy[:, None] - yy[None, :]).min(1)
        return float(Pc[dmin > 1.0].sum() / Pc.sum()), float(Pc[dmin > 2.0].sum() / Pc.sum())

    if record_access:
        a1, a2 = access(P0, sx, sy); acc1.append(a1); acc2.append(a2)
    for t in range(1, T):
        out = out0 * np.exp(p.g_out * t)
        Pc = cell_pop(t)
        n = len(sx)
        if n:
            W = wmat(sx, sy)
            den = W.sum(1) + out
            R = (Pc[:, None] * W / den[:, None]).sum(0)
            bad = np.where(R < F, bad + 1, 0)
            keep = (bad < p.k_exit) & (rng.random(n) > p.q_churn)
            sx, sy, F, bad = sx[keep], sy[keep], F[keep], bad[keep]
        insum = wmat(sx, sy).sum(1) if len(sx) else np.zeros(G * G)
        # 出店候補：数は（前の年の店の数）× q、場所は人口に比例
        n_cand = rng.poisson(p.entry_mult * p.q_churn * max(n, 1) + 0.05)
        Fmed = np.median(F) if len(F) else (np.median(R0) * 0.8 if n0 else 1.0)
        for _ in range(n_cand):
            cc = rng.choice(G * G, p=Pc / Pc.sum())
            nx = cx[cc] + (rng.random() - 0.5) * cell
            ny = cy[cc] + (rng.random() - 0.5) * cell
            e = np.exp(-np.hypot(cx - nx, cy - ny) / p.lam)
            Rn = float((Pc * e / (insum + e + out)).sum())
            Fn = Fmed * rng.choice(ratio_pool) / np.mean(ratio_pool)
            if Rn >= Fn:
                sx, sy = np.append(sx, nx), np.append(sy, ny)
                F, bad = np.append(F, Fn), np.append(bad, 0)
                insum = insum + e
        n_hist.append(len(sx))
        leak_hist.append(float((Pc * out / (insum + out)).sum() / Pc.sum()))
        if record_access:
            a1, a2 = access(Pc, sx, sy); acc1.append(a1); acc2.append(a2)
    res = {"n": np.array(n_hist), "leak": np.array(leak_hist)}
    if record_access:
        res["acc1"], res["acc2"] = np.array(acc1), np.array(acc2)
    return res


def pop_path_loglinear(p0, p1, years):
    t = np.arange(years + 1) / years
    return p0 * (p1 / p0) ** t


BASE = Params()


def variant(**kw):
    return replace(BASE, **kw)
