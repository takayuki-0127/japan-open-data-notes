"""長期記憶の推定に使う関数（GPH・局所Whittle・ARFIMA の Whittle 推定・DFA・R/S・シミュレーション）"""
import numpy as np
from scipy.optimize import minimize_scalar, minimize


def periodogram(x):
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    f = np.fft.fft(x)
    m = (n - 1) // 2
    lam = 2 * np.pi * np.arange(1, m + 1) / n
    I = np.abs(f[1:m + 1]) ** 2 / (2 * np.pi * n)
    return lam, I


def gph(x, power=0.6):
    """Geweke–Porter-Hudak の対数ピリオドグラム回帰。d と標準誤差（π/√(24m)）"""
    lam, I = periodogram(x)
    m = int(len(x) ** power)
    X = np.log(4 * np.sin(lam[:m] / 2) ** 2)
    y = np.log(I[:m])
    b = np.polyfit(X, y, 1)[0]
    return -b, np.pi / np.sqrt(24 * m)


def local_whittle(x, power=0.6):
    """Robinson (1995) の局所Whittle。d と標準誤差（1/(2√m)）"""
    lam, I = periodogram(x)
    m = int(len(x) ** power)
    lam, I = lam[:m], I[:m]

    def R(d):
        return np.log(np.mean(lam ** (2 * d) * I)) - 2 * d * np.mean(np.log(lam))
    r = minimize_scalar(R, bounds=(-0.49, 1.49), method="bounded")
    return r.x, 1 / (2 * np.sqrt(m))


def _spec_arfima(lam, d, phi):
    s = np.abs(2 * np.sin(lam / 2)) ** (-2 * d)
    for k, p in enumerate(phi, 1):
        pass
    ar = np.ones_like(lam, dtype=complex)
    for k, p in enumerate(phi, 1):
        ar = ar - p * np.exp(-1j * k * lam)
    return s / np.abs(ar) ** 2


def whittle_arfima(x, p=1):
    """ARFIMA(p,d,0) を全周波数の Whittle 尤度で推定。d, phi, 目的関数の値"""
    lam, I = periodogram(x)

    def obj(th):
        d, phi = th[0], th[1:]
        g = _spec_arfima(lam, d, phi)
        s2 = np.mean(I / g)
        return np.log(s2) + np.mean(np.log(g))
    best = None
    for d0 in (0.0, 0.2, 0.4):
        th0 = np.r_[d0, np.zeros(p)]
        bnds = [(-0.49, 0.99)] + [(-0.95, 0.95)] * p
        r = minimize(obj, th0, bounds=bnds, method="L-BFGS-B")
        if best is None or r.fun < best.fun:
            best = r
    n = len(lam)
    bic = 2 * n * best.fun + (p + 1) * np.log(n)
    return best.x[0], best.x[1:], bic


def dfa(x, order=1, smin=10, nscale=20):
    """DFA（トレンド除去変動解析）。傾き α（= H、d = α − 0.5）"""
    x = np.asarray(x, float)
    y = np.cumsum(x - x.mean())
    n = len(y)
    scales = np.unique(np.logspace(np.log10(smin), np.log10(n // 4), nscale).astype(int))
    F = []
    for s in scales:
        k = n // s
        seg = y[:k * s].reshape(k, s)
        t = np.arange(s)
        V = np.vander(t, order + 1)
        coef, *_ = np.linalg.lstsq(V, seg.T, rcond=None)
        resid = seg.T - V @ coef
        F.append(np.sqrt(np.mean(resid ** 2)))
    a = np.polyfit(np.log(scales), np.log(F), 1)[0]
    return a, scales, np.array(F)


def rs_hurst(x, smin=10, nscale=20):
    """古典的な R/S 解析によるハースト指数"""
    x = np.asarray(x, float)
    n = len(x)
    scales = np.unique(np.logspace(np.log10(smin), np.log10(n // 2), nscale).astype(int))
    RS = []
    for s in scales:
        k = n // s
        seg = x[:k * s].reshape(k, s)
        z = np.cumsum(seg - seg.mean(1, keepdims=True), 1)
        R = z.max(1) - z.min(1)
        S = seg.std(1)
        ok = S > 0
        RS.append(np.mean(R[ok] / S[ok]))
    return np.polyfit(np.log(scales), np.log(RS), 1)[0]


def arfima_sim(n, d, phi=0.0, rng=None, burn=2000, trunc=5000):
    """ARFIMA(1,d,0) を MA(∞) の打ち切りで生成"""
    rng = np.random.default_rng() if rng is None else rng
    K = trunc
    psi = np.ones(K)
    for k in range(1, K):
        psi[k] = psi[k - 1] * (k - 1 + d) / k
    e = rng.standard_normal(n + burn + K)
    u = np.convolve(e, psi, mode="valid")[: n + burn]
    if phi != 0:
        y = np.empty_like(u)
        y[0] = u[0]
        for t in range(1, len(u)):
            y[t] = phi * y[t - 1] + u[t]
        u = y
    return u[burn:]


def impulse(d, phi, H):
    """ARFIMA(p,d,0) の衝撃応答（1単位の衝撃が h 期後に残る量）"""
    psi = np.ones(H + 1)
    for k in range(1, H + 1):
        psi[k] = psi[k - 1] * (k - 1 + d) / k
    phi = np.atleast_1d(phi)
    out = np.zeros(H + 1)
    for t in range(H + 1):
        out[t] = psi[t] + sum(phi[j] * out[t - j - 1] for j in range(len(phi)) if t - j - 1 >= 0)
    return out


def all_estimates(x):
    """主な推定量をまとめて返す（d の単位にそろえる）"""
    r = {}
    for pw in (0.5, 0.6, 0.7, 0.8):
        r[f"gph_{pw}"], r[f"gph_{pw}_se"] = gph(x, pw)
        r[f"lw_{pw}"], r[f"lw_{pw}_se"] = local_whittle(x, pw)
    best = None
    for p in range(0, 4):
        d, phi, bic = whittle_arfima(x, p)
        if best is None or bic < best[2]:
            best = (d, phi, bic, p)
    r["arfima_d"], r["arfima_p"] = best[0], best[3]
    r["arfima_phi"] = ";".join(f"{v:.3f}" for v in best[1])
    r["dfa_d"] = dfa(x)[0] - 0.5
    r["rs_d"] = rs_hurst(x) - 0.5
    return r
