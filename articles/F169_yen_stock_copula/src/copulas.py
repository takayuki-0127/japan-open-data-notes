"""2変数コピュラの対数尤度（擬似観測値 u, v ∈ (0,1)）。"""
import numpy as np
import sympy as sp
from scipy import stats, optimize, special

def ll_gauss(p, u, v):
    r = np.tanh(p[0]); x, y = stats.norm.ppf(u), stats.norm.ppf(v)
    return np.sum(-0.5 * np.log(1 - r**2) - (r**2 * (x**2 + y**2) - 2 * r * x * y) / (2 * (1 - r**2)))

def ll_t(p, u, v):
    r = np.tanh(p[0]); nu = 2 + np.exp(p[1]); x, y = stats.t.ppf(u, nu), stats.t.ppf(v, nu)
    lg = special.gammaln
    c = (lg((nu + 2) / 2) + lg(nu / 2) - 2 * lg((nu + 1) / 2) - 0.5 * np.log(1 - r**2)
         - (nu + 2) / 2 * np.log1p((x**2 + y**2 - 2 * r * x * y) / (nu * (1 - r**2)))
         + (nu + 1) / 2 * (np.log1p(x**2 / nu) + np.log1p(y**2 / nu)))
    return np.sum(c)

def _clayton(th, u, v):
    return np.log1p(th) - (1 + th) * (np.log(u) + np.log(v)) - (2 + 1 / th) * np.log(u**-th + v**-th - 1)

def ll_clayton(p, u, v): return np.sum(_clayton(np.exp(p[0]), u, v))
def ll_sclayton(p, u, v): return np.sum(_clayton(np.exp(p[0]), 1 - u, 1 - v))

def _gumbel(th, u, v):
    a, b = -np.log(u), -np.log(v); s = a**th + b**th; A = s**(1 / th)
    return (-A + (th - 1) * (np.log(a) + np.log(b)) - np.log(u) - np.log(v)
            + (1 / th - 2) * np.log(s) + np.log(A + th - 1))

def ll_gumbel(p, u, v): return np.sum(_gumbel(1 + np.exp(p[0]), u, v))
def ll_sgumbel(p, u, v): return np.sum(_gumbel(1 + np.exp(p[0]), 1 - u, 1 - v))

def ll_frank(p, u, v):
    th = p[0]
    if abs(th) < 1e-6: return 0.0
    num = th * (1 - np.exp(-th)) * np.exp(-th * (u + v))
    den = ((1 - np.exp(-th)) - (1 - np.exp(-th * u)) * (1 - np.exp(-th * v)))**2
    return np.sum(np.log(np.abs(num)) - np.log(den))

# 対称化 Joe-Clayton（Patton 2006）：上と下の裾の依存を別々に推定できる
_u, _v, _k, _g = sp.symbols("u v k g", positive=True)
_jc = 1 - (1 - ((1 - (1 - _u)**_k)**(-_g) + (1 - (1 - _v)**_k)**(-_g) - 1)**(-1 / _g))**(1 / _k)
_jcd = sp.lambdify((_u, _v, _k, _g), sp.diff(_jc, _u, _v), "numpy")

def _jc_dens(u, v, lu, ll):
    k = 1 / np.log2(2 - lu); g = -1 / np.log2(ll)
    return _jcd(u, v, k, g)

def ll_sjc(p, u, v):
    lu, ll = special.expit(p[0]) * 0.99, special.expit(p[1]) * 0.99
    lu, ll = max(lu, 1e-4), max(ll, 1e-4)
    d = 0.5 * (_jc_dens(u, v, lu, ll) + _jc_dens(1 - u, 1 - v, ll, lu))
    if not np.all(np.isfinite(d)) or np.any(d <= 0): return -1e12
    return np.sum(np.log(d))

FAMILIES = {
    "ガウス": (ll_gauss, [0.3]), "t": (ll_t, [0.3, 1.0]), "クレイトン（下の裾）": (ll_clayton, [-0.5]),
    "クレイトン回転（上の裾）": (ll_sclayton, [-0.5]), "ガンベル（上の裾）": (ll_gumbel, [-1.5]),
    "ガンベル回転（下の裾）": (ll_sgumbel, [-1.5]), "フランク（裾なし）": (ll_frank, [2.0]),
    "対称化ジョー・クレイトン": (ll_sjc, [-1.5, -1.5]),
}

def tails(name, p):
    """推定値から上の裾 λU・下の裾 λL を返す。"""
    if name == "ガウス": return 0.0, 0.0
    if name == "t":
        r = np.tanh(p[0]); nu = 2 + np.exp(p[1])
        l = 2 * stats.t.cdf(-np.sqrt((nu + 1) * (1 - r) / (1 + r)), nu + 1); return l, l
    if name.startswith("クレイトン（"): return 0.0, 2 ** (-1 / np.exp(p[0]))
    if name.startswith("クレイトン回転"): return 2 ** (-1 / np.exp(p[0])), 0.0
    if name.startswith("ガンベル（"): return 2 - 2 ** (1 / (1 + np.exp(p[0]))), 0.0
    if name.startswith("ガンベル回転"): return 0.0, 2 - 2 ** (1 / (1 + np.exp(p[0])))
    if name.startswith("フランク"): return 0.0, 0.0
    if name.startswith("対称化"):
        return max(special.expit(p[0]) * 0.99, 1e-4), max(special.expit(p[1]) * 0.99, 1e-4)

def fit_all(u, v):
    out = []
    for name, (f, x0) in FAMILIES.items():
        best = None
        for s in (0, 1):
            x = np.array(x0) + s * 0.7
            r = optimize.minimize(lambda q: -f(q, u, v), x, method="Nelder-Mead",
                                  options={"xatol": 1e-5, "fatol": 1e-6, "maxiter": 4000})
            if best is None or r.fun < best.fun: best = r
        k = len(x0); ll = -best.fun; lu, lL = tails(name, best.x)
        out.append(dict(family=name, k=k, loglik=ll, aic=2 * k - 2 * ll, lambda_upper=lu, lambda_lower=lL,
                        params=";".join(f"{z:.4f}" for z in best.x)))
    return out
