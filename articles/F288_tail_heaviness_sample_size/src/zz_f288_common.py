"""F288 共通：本当の分布から超過額を作る関数と、4つの分布の最尤推定（ベクトル化）。"""
import numpy as np

LN2 = np.log(2.0)

# ---------- 本当の分布（中央値を1にそろえる） ----------
DISTS = {
    "exp":     ("指数", 0.0),
    "weib0.6": ("ワイブル 形0.6", 0.0),
    "ln1.0":   ("対数正規 σ=1.0", 0.0),
    "ln1.5":   ("対数正規 σ=1.5", 0.0),
    "gpd0.2":  ("GPD ξ=0.2", 0.2),
    "gpd0.4":  ("GPD ξ=0.4", 0.4),
    "gpd0.5":  ("GPD ξ=0.5", 0.5),
    "gpd0.6":  ("GPD ξ=0.6", 0.6),
    "gpd0.8":  ("GPD ξ=0.8", 0.8),
}
TRUE_MODEL = {"exp": "exp", "weib0.6": "weib", "ln1.0": "lnorm", "ln1.5": "lnorm",
              "gpd0.2": "gpd", "gpd0.4": "gpd", "gpd0.5": "gpd", "gpd0.6": "gpd", "gpd0.8": "gpd"}


def draw(dist, size, rng):
    u = rng.random(size)
    if dist == "exp":
        return -np.log1p(-u) / LN2
    if dist.startswith("weib"):
        k = float(dist[4:])
        lam = 1.0 / LN2 ** (1.0 / k)
        return lam * (-np.log1p(-u)) ** (1.0 / k)
    if dist.startswith("ln"):
        s = float(dist[2:])
        from scipy.special import ndtri
        return np.exp(s * ndtri(u))
    if dist.startswith("gpd"):
        xi = float(dist[3:])
        sig = xi / (2.0 ** xi - 1.0)
        return sig / xi * ((1.0 - u) ** (-xi) - 1.0)
    raise ValueError(dist)


def draw_ln_exceed(sigma, q, size, rng):
    """対数正規 σ の損害のうち、q 分位点 u を超えたものの超過額 X−u（R4）。"""
    from scipy.special import ndtri
    u0 = np.exp(sigma * ndtri(q))
    p = q + (1.0 - q) * rng.random(size)
    x = np.exp(sigma * ndtri(p))
    y = x - u0
    return y / np.median(np.exp(sigma * ndtri(q + (1 - q) * 0.5)) - u0)  # 尺度はそろえるだけ（形には影響しない）


# ---------- 当てはめ（行ごとに1つの標本、Y: reps×n） ----------
def fit_exp(Y):
    n = Y.shape[1]
    m = Y.mean(1)
    return -n * np.log(m) - n  # 対数尤度


def fit_lnorm(Y):
    n = Y.shape[1]
    L = np.log(Y)
    mu = L.mean(1)
    s = L.std(1)
    ll = -L.sum(1) - n * np.log(s) - 0.5 * n * np.log(2 * np.pi) - 0.5 * n
    return ll


def fit_weib(Y, iters=70):
    n = Y.shape[1]
    L = np.log(Y)
    mL = L.mean(1)
    lo = np.full(Y.shape[0], np.log(0.02))
    hi = np.full(Y.shape[0], np.log(50.0))
    Ls = L - L.max(1, keepdims=True)  # 桁あふれを防ぐ
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        k = np.exp(mid)
        w = np.exp(k[:, None] * Ls)
        g = (w * L).sum(1) / w.sum(1) - 1.0 / k - mL
        hi = np.where(g > 0, mid, hi)
        lo = np.where(g > 0, lo, mid)
    k = np.exp(0.5 * (lo + hi))
    lam = (np.mean(Y ** k[:, None], 1)) ** (1.0 / k)
    z = Y / lam[:, None]
    ll = n * np.log(k) - n * k * np.log(lam) + (k - 1)[:, None].squeeze() * L.sum(1) - (z ** k[:, None]).sum(1)
    return ll, k


def _gpd_prof(Y, theta):
    """θ（行ごと）での GPD のプロファイル対数尤度と ξ。"""
    n = Y.shape[1]
    s = np.log1p(theta[:, None] * Y).sum(1) / n  # = ξ
    with np.errstate(divide="ignore", invalid="ignore"):
        ll = n * (np.log(np.abs(theta)) - np.log(np.abs(s)) - 1.0 - s)
    ll = np.where(np.isfinite(ll), ll, -np.inf)
    return ll, s


def fit_gpd(Y):
    """GPD の最尤推定（θ=ξ/σ の格子探索＋細かい格子）。指数（θ→0）も候補に入れる。
    ξ<−1 では尤度が上に有界でなく最尤推定が存在しないため、θ の下限を −0.999/最大値 に置いた。下限に張り付いた回は at_bound=True。"""
    ymax = Y.max(1)
    tg = np.concatenate([-np.logspace(np.log10(0.999), -4, 120), np.logspace(-4, 6, 280)])
    best_ll = np.full(Y.shape[0], -np.inf)
    best_t = np.zeros(Y.shape[0])
    lls = np.empty((Y.shape[0], tg.size))
    for j, t in enumerate(tg):
        ll, _ = _gpd_prof(Y, t / ymax)
        lls[:, j] = ll
    jb = lls.argmax(1)
    # 細かい格子で詰める
    jl = np.clip(jb - 1, 0, tg.size - 1)
    jh = np.clip(jb + 1, 0, tg.size - 1)
    tl, th = tg[jl], tg[jh]
    fine = np.linspace(0, 1, 41)
    for f in fine:
        t = tl + (th - tl) * f
        t = np.where(np.abs(t) < 1e-9, 1e-9, t)
        ll, _ = _gpd_prof(Y, t / ymax)
        upd = ll > best_ll
        best_ll = np.where(upd, ll, best_ll)
        best_t = np.where(upd, t, best_t)
    ll, xi = _gpd_prof(Y, best_t / ymax)
    at_bound = best_t <= tg[0] + 1e-12  # θ が下限（−0.999/最大値）に張り付いた＝ξ<−1 で最尤推定が存在しない側
    llexp = fit_exp(Y)
    use_exp = llexp >= ll
    ll = np.where(use_exp, llexp, ll)
    xi = np.where(use_exp, 0.0, xi)
    at_bound = at_bound & ~use_exp
    return ll, xi, at_bound


def pwm_xi(Y):
    """確率加重モーメント法（Hosking & Wallis 1987）の ξ。"""
    n = Y.shape[1]
    S = np.sort(Y, 1)
    p = (np.arange(1, n + 1) - 0.35) / n
    a0 = S.mean(1)
    a1 = (S * (1 - p)).mean(1)
    k = a0 / (a0 - 2 * a1) - 2.0
    return -k


def fit_all(Y):
    n = Y.shape[1]
    le = fit_exp(Y)
    lw, kw = fit_weib(Y)
    ll_ = fit_lnorm(Y)
    lg, xi, bnd = fit_gpd(Y)
    aic = np.vstack([2 * 1 - 2 * le, 2 * 2 - 2 * lw, 2 * 2 - 2 * ll_, 2 * 2 - 2 * lg]).T
    bic = np.vstack([np.log(n) * 1 - 2 * le, np.log(n) * 2 - 2 * lw, np.log(n) * 2 - 2 * ll_, np.log(n) * 2 - 2 * lg]).T
    names = np.array(["exp", "weib", "lnorm", "gpd"])
    lr = np.where(xi > 0, 2 * (lg - le), 0.0)
    return {
        "xi_mle": xi, "xi_pwm": pwm_xi(Y), "lr": lr, "weib_k": kw,
        "pick_aic": names[aic.argmin(1)], "pick_bic": names[bic.argmin(1)],
        "gpd_bound": bnd,
        "aic_exp": aic[:, 0], "aic_weib": aic[:, 1], "aic_lnorm": aic[:, 2], "aic_gpd": aic[:, 3],
    }
