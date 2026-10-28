"""区間打ち切りの道具：調査の作り方、Turnbull 推定（EM）、端点・中点での代入 KM、パラメトリック、区分指数の比例ハザード"""
import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy import stats

D0 = pd.Timestamp("2015-01-01")
END = (pd.Timestamp("2026-09-30") - D0).days
YR = 365.25
MON = YR / 12
J = 132          # 月のビン数（0〜132か月）。それより先は「その先」のビン

def surveys_calendar(k, month=9, day=30):
    """暦の上で k 年おきの調査（最後は必ず 2026-09-30）。month/day で調査日をずらす"""
    last = (pd.Timestamp(2026, month, day) - D0).days
    if last > END:
        last = (pd.Timestamp(2025, month, day) - D0).days
    u = []
    t = last
    while t > 0:
        u.append(t); t = int(round(t - k * YR))
    u = sorted(set(u + [END]))
    return np.array(u)

def observe(df, k=None, scheme="calendar", month=9, day=30):
    """真の閉鎖日から、調査で見える区間 (L, R]（日数・開始からの経過）を作る。
    k=None はそのまま（正確な日付）。scheme='calendar' は暦の調査日、'anniv' は設立から k 年ごと＋最後に 2026-09-30。
    k='once' は 2026-09-30 の1回だけ（current status）。"""
    s, e, ev = df.s.values, df.e.values, df.event.values
    if k is None:
        T = (e - s).astype(float)
        return np.where(ev == 1, T, T), np.where(ev == 1, T, np.inf)
    if scheme == "anniv":
        step = k * YR
        # 閉鎖日 e の直前の調査（設立から step ごと）と直後の調査
        jlo = np.floor((e - s) / step)
        last_before = s + jlo * step
        last_before = np.where(last_before >= e, s + (jlo - 1) * step, last_before)
        last_before = np.maximum(last_before, s)
        nxt = s + (np.floor((e - s) / step) + 1) * step
        nxt = np.where(s + np.floor((e - s) / step) * step == e, e, nxt)
        nxt = np.minimum(nxt, END)
        L = last_before - s
        R = np.where(ev == 1, nxt - s, np.inf)
        L = np.where((ev == 0) & (e == END), END - s, L)
        return L.astype(float), R.astype(float)
    U = np.array([END]) if k == "once" else surveys_calendar(k, month, day)
    i_lo = np.searchsorted(U, e, side="left") - 1          # e より前の最後の調査
    prev = np.where(i_lo >= 0, U[np.clip(i_lo, 0, None)], -10**9)
    L = np.maximum(prev, s) - s
    i_hi = np.searchsorted(U, e, side="left")              # e 以後の最初の調査
    R = np.where(ev == 1, U[np.clip(i_hi, 0, len(U) - 1)] - s, np.inf)
    L = np.where((ev == 0) & (e == END), END - s, L)       # 最後まで残った法人は最後の調査で生存を確認
    return L.astype(float), R.astype(float)

def to_months(L, R):
    Lm = np.floor(L / MON).astype(int)
    Rm = np.where(np.isinf(R), -1, np.ceil(R / MON)).astype(int)
    Rm = np.where((Rm >= 0) & (Rm <= Lm), Lm + 1, Rm)
    Lm = np.minimum(Lm, J); Rm = np.where(Rm > J, J, Rm)
    return Lm, Rm

def turnbull(Lm, Rm, w=None, tol=1e-10, maxit=50000):
    """月のビン (j-1, j] (j=1..J) と「その先」(J+1) の上の質量を EM で推定。S(t) を 0..J か月で返す"""
    if w is None: w = np.ones(len(Lm))
    g = pd.DataFrame({"L": Lm, "R": Rm, "w": w}).groupby(["L", "R"]).w.sum().reset_index()
    nb = J + 1
    A = np.zeros((len(g), nb), dtype=bool)
    for i, (l, r) in enumerate(zip(g.L.values, g.R.values)):
        A[i, l: (nb if r < 0 else r)] = True     # ビン index b は (b, b+1] か月
    n = g.w.values.astype(float); N = n.sum()
    p = np.full(nb, 1.0 / nb)
    ll_old = -np.inf
    Af = A.astype(float)
    for it in range(maxit):
        den = Af @ p
        ll = (n * np.log(den)).sum()
        p = p * (Af.T @ (n / den)) / N
        if ll - ll_old < tol * abs(ll) and it > 50:
            break
        ll_old = ll
    S = 1 - np.concatenate([[0], np.cumsum(p[:J])])
    return S, it

def km_months(Tm, ev, w=None):
    """月単位の KM。イベントは月 m（= (m-1, m] に起きた）、打ち切りは月 m で生存確認。S を 0..J か月で返す"""
    if w is None: w = np.ones(len(Tm))
    Tm = np.clip(np.asarray(Tm, int), 0, J)
    Tm = np.where(ev == 1, np.maximum(Tm, 1), Tm)
    d = np.bincount(Tm[ev == 1], weights=w[ev == 1], minlength=J + 1)
    c = np.bincount(Tm[ev == 0], weights=w[ev == 0], minlength=J + 1)
    atrisk = (d + c)[::-1].cumsum()[::-1]
    h = np.where(atrisk > 0, d / np.maximum(atrisk, 1e-12), 0)
    h[0] = 0
    return np.cumprod(1 - h)

def km_days(Td, ev, grid_years):
    df = pd.DataFrame({"t": Td.astype(int), "e": ev})
    g = df.groupby("t").e.agg(["size", "sum"]).sort_index()
    atrisk = g["size"][::-1].cumsum()[::-1]
    S = np.cumprod(1 - g["sum"] / atrisk).values
    idx = np.searchsorted(g.index.values, np.round(np.asarray(grid_years) * YR), side="right") - 1
    return np.where(idx >= 0, S[np.clip(idx, 0, None)], 1.0)

# ---- パラメトリック（区間打ち切りの尤度） ----
def _surv(dist, th, t):
    t = np.asarray(t, float)
    if dist == "weibull":
        lam, k = np.exp(th[0]), np.exp(th[1]); return np.exp(-(t / lam) ** k)
    if dist == "loglogistic":
        a, b = np.exp(th[0]), np.exp(th[1]); return 1 / (1 + (t / a) ** b)
    if dist == "lognormal":
        mu, sg = th[0], np.exp(th[1])
        with np.errstate(divide="ignore"):
            return stats.norm.sf((np.log(np.maximum(t, 1e-12)) - mu) / sg)
    raise ValueError(dist)

def fit_param(dist, Lm, Rm, w=None):
    if w is None: w = np.ones(len(Lm))
    g = pd.DataFrame({"L": Lm, "R": Rm, "w": w}).groupby(["L", "R"]).w.sum().reset_index()
    L = g.L.values / 12.0; R = np.where(g.R.values < 0, np.inf, g.R.values / 12.0); n = g.w.values
    rc = np.isinf(R)
    def nll(th):
        SL = np.where(L > 0, _surv(dist, th, L), 1.0)
        SR = np.where(rc, 0.0, _surv(dist, th, np.where(rc, 1.0, R)))
        pr = np.clip(SL - SR, 1e-300, None)
        return -(n * np.log(pr)).sum()
    best = None
    for x0 in ([np.log(60), np.log(1.0)], [np.log(30), np.log(0.8)], [5.0, np.log(2.0)]):
        r = minimize(nll, x0, method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-6, "maxiter": 5000})
        if best is None or r.fun < best.fun: best = r
    S = _surv(dist, best.x, np.arange(J + 1) / 12.0); S[0] = 1.0
    return S, best

# ---- 区分指数（1年ごとの基準ハザード）の比例ハザード ----
CUTS = np.arange(0, 11) * 1.0          # 0,1,...,10 年。10年より先は最後の区間

def _H0(t, loglam):
    lam = np.exp(loglam)
    t = np.asarray(t, float)[:, None]
    lo = CUTS[None, :]; hi = np.concatenate([CUTS[1:], [np.inf]])[None, :]
    return (np.clip(np.minimum(t, hi) - lo, 0, None) * lam[None, :]).sum(1)

def _h0(t, loglam):
    idx = np.clip(np.searchsorted(CUTS, t, side="right") - 1, 0, len(CUTS) - 1)
    return np.exp(loglam[idx])

def fit_ph(L, R, X, n, exact=None):
    """L,R は年。R=inf は右打ち切り。exact=True の行は L=R=T の正確なイベント。X は (n, p)。
    返り値：係数・標準誤差（数値ヘッセ行列から）"""
    L = np.asarray(L, float); R = np.asarray(R, float); X = np.asarray(X, float); n = np.asarray(n, float)
    if exact is None: exact = np.zeros(len(L), bool)
    rc = np.isinf(R) & ~exact
    iv = ~rc & ~exact
    HL = None
    nk = len(CUTS); p = X.shape[1]
    def nll(th):
        ll0, b = th[:nk], th[nk:]
        eta = X @ b; r = np.exp(eta)
        HLv = _H0(L, ll0) * r
        out = np.zeros(len(L))
        out[rc] = -HLv[rc]
        if exact.any():
            out[exact] = np.log(_h0(L[exact], ll0)) + eta[exact] - HLv[exact]
        if iv.any():
            HR_ = _H0(R[iv], ll0) * r[iv]
            out[iv] = -HLv[iv] + np.log(np.clip(-np.expm1(-(HR_ - HLv[iv])), 1e-300, None))
        return -(n * out).sum()
    x0 = np.concatenate([np.full(nk, np.log(0.01)), np.zeros(p)])
    r = minimize(nll, x0, method="L-BFGS-B")
    r = minimize(nll, r.x, method="BFGS", options={"gtol": 1e-6})
    # 数値ヘッセ行列（係数部分）
    th = r.x; k = len(th); eps = 1e-4
    Hm = np.zeros((k, k))
    f0 = nll(th)
    for i in range(k):
        for j in range(i, k):
            ei = np.zeros(k); ej = np.zeros(k); ei[i] = eps; ej[j] = eps
            v = (nll(th + ei + ej) - nll(th + ei - ej) - nll(th - ei + ej) + nll(th - ei - ej)) / (4 * eps * eps)
            Hm[i, j] = Hm[j, i] = v
    cov = np.linalg.pinv(Hm)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    return th[nk:], se[nk:], th[:nk]
