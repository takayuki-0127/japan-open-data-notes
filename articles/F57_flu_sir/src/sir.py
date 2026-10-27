"""SIR／SEIR モデルのシミュレーションと当てはめ（週次の定点当たり報告数に合わせる）。

割合で書いた SIR は、S(0)=s0 のとき「β×s0」だけが形を決める（s0 と報告率は見分けられない）。
そこで S(0)=1 とし、Reff0＝β/γ×s0（シーズン初めの実効再生産数）を推定する。
報告数 y_週 ＝ c × その週の新しい感染（割合）。c には報告率・受診率・s0 がまとめて入る。
"""
import numpy as np
from scipy.optimize import least_squares

DT = 0.5          # シミュレーションの刻み（日）
NDAYS = 371       # 第36週の木曜の3.5日前から53週分


def holiday_mask(season_start, ndays=NDAYS, dt=DT, days=(12, 27, 1, 7)):
    """年末年始（既定：12/27〜1/7）を1、それ以外を0。0日目＝第36週の月曜。"""
    import pandas as pd
    t0 = pd.Timestamp.fromisocalendar(season_start, 36, 1)
    t = t0 + pd.to_timedelta(np.arange(0, ndays, dt), unit="D")
    m1, d1, m2, d2 = days
    a = ((t.month == m1) & (t.day >= d1)) | ((t.month == m2) & (t.day <= d2))
    return a.astype(float)


def simulate(params, hol, D=3.0, L=0.0, nweek=53):
    """params: list of strains [(Reff0, log10 I0)], h（休みの間の β の倍率）。週ごとの新しい感染（割合）を返す。"""
    strains, h = params
    g = 1.0 / D
    n = len(hol)
    inc = np.zeros(n)
    for R, lI0 in strains:
        b = R * g
        S, E, I = 1.0, 0.0, 10 ** lI0
        sig = 1.0 / L if L > 0 else None
        for k in range(n):
            bb = b * (h if hol[k] > 0 else 1.0)
            new = bb * S * I * DT
            if new > S: new = S
            S -= new
            if sig:
                ei = sig * E * DT
                E += new - ei
                I += ei - g * I * DT
            else:
                I += new - g * I * DT
            inc[k] += new
    per_week = int(round(7 / DT))
    w = inc[: nweek * per_week].reshape(nweek, per_week).sum(1)
    return w


def fit(y, hol, nstrain=1, use_h=True, D=3.0, L=0.0, off=0.3, mask=None, starts=None, seed=0):
    """y：第36週から並べた週次の定点当たり報告数（nweek 本、欠けは nan）。"""
    nweek = len(y)
    obs = np.log(np.asarray(y) + off)
    ok = ~np.isnan(obs) if mask is None else (mask & ~np.isnan(obs))
    rng = np.random.default_rng(seed)

    def unpack(p):
        i = 0; st = []
        for _ in range(nstrain):
            st.append((p[i], p[i + 1])); i += 2
        h = p[i] if use_h else 1.0
        if use_h: i += 1
        lc, b = p[i], p[i + 1]
        return st, h, lc, b

    def resid(p):
        st, h, lc, b = unpack(p)
        w = simulate((st, h), hol, D=D, L=L, nweek=nweek)
        pred = np.log(np.exp(lc) * w + b + off)
        return (pred - obs)[ok]

    lo, hi = [], []
    for _ in range(nstrain):
        lo += [1.0, -14.0]; hi += [4.0, -2.0]
    if use_h: lo.append(0.2); hi.append(1.5)
    lo += [0.0, 0.0]; hi += [18.0, 5.0]
    best = None
    ntry = starts or 8
    for t in range(ntry):
        p0 = []
        for j in range(nstrain):
            p0 += [rng.uniform(1.1, 2.0), rng.uniform(-11, -4)]
        if use_h: p0.append(rng.uniform(0.6, 1.0))
        p0 += [rng.uniform(6, 12), rng.uniform(0.1, 1.0)]
        try:
            r = least_squares(resid, p0, bounds=(lo, hi), x_scale="jac", max_nfev=400)
        except Exception:
            continue
        if best is None or r.cost < best.cost:
            best = r
    st, h, lc, b = unpack(best.x)
    w = simulate((st, h), hol, D=D, L=L, nweek=nweek)
    pred = np.exp(lc) * w + b
    n = ok.sum(); k = len(best.x)
    rss = 2 * best.cost
    aic = n * np.log(rss / n) + 2 * k
    return dict(strains=st, h=h, logc=lc, base=b, pred=pred, rss=rss, n=int(n), k=k, aic=aic,
                rmse=float(np.sqrt(rss / n)))


def final_size(R):
    """一山の SIR の最終規模（感受性者のうち感染する割合）z = 1 - exp(-R z)。"""
    if R <= 1: return 0.0
    z = 0.8
    for _ in range(200):
        z = 1 - np.exp(-R * z)
    return z


def rt_from_growth(y, mean=3.0, sd=1.5):
    """週ごとの増加率から R を出す（世代時間をガンマ分布と仮定、Wallinga–Lipsitch）。"""
    y = np.asarray(y, float)
    r = np.log(y[1:] / y[:-1]) / 7.0
    k = (mean / sd) ** 2; th = sd ** 2 / mean
    return (1 + r * th) ** k
