"""共有フレイル（グループごとの共通の倍率 z）つきの区分化指数モデル。

閉鎖のハザード  λ_ij(t) = z_g · λ0(t) · exp(x β)
λ0 は経過年ごとの階段関数（＝Cox と同じく形を決めない）。z_g の分布は
- ガンマ（平均1・分散θ）：周辺尤度が閉じた形で書ける
- 対数正規（log z ~ N(0, σ²)）：ガウス–エルミート求積で積分
セル（グループ×種別×地域区分×設立年×経過年）の事象数とリスク年から最尤推定する。
"""
import numpy as np, pandas as pd
from scipy.special import gammaln, digamma
from scipy.optimize import minimize


def design(cells, cov=("kindj", "area", "cohort"), fe=None):
    X = [pd.get_dummies(cells["k"], prefix="k", dtype=float)]           # 基準ハザード（切片なし）
    ref = {"kindj": "株式会社", "area": "その他の市町村", "cohort": 2018}
    for c in cov:
        dm = pd.get_dummies(cells[c], prefix=c, dtype=float)
        r = f"{c}_{ref[c]}"
        dm = dm.drop(columns=r if r in dm.columns else dm.columns[0])
        X.append(dm)
    if fe is not None:
        dm = pd.get_dummies(cells[fe], prefix=fe, dtype=float)
        X.append(dm.iloc[:, 1:])
    X = pd.concat(X, axis=1)
    return X


class Fit:
    pass


def _prep(cells, group, ev, cov, fe):
    X = design(cells, cov, fe)
    g, gidx = np.unique(cells[group].to_numpy(), return_inverse=True)
    return X, X.to_numpy(), cells[ev].to_numpy(float), np.log(cells["expo"].to_numpy()), g, gidx


def _num_hess(f, x, h=1e-4):
    n = len(x); H = np.zeros((n, n))
    for i in range(n):
        e = np.zeros(n); e[i] = h
        H[i] = (f(x + e) - f(x - e)) / (2 * h)
    return (H + H.T) / 2


def fit_poisson(cells, ev="ev_all", cov=("kindj", "area", "cohort"), fe=None, group="prefn"):
    """フレイルなし（独立と仮定）。SE は通常のものと、グループで束ねた頑健 SE。"""
    X, Xm, d, off, g, gidx = _prep(cells, group, ev, cov, fe)
    b = np.zeros(Xm.shape[1]); b[:11] = np.log(d.sum() / np.exp(off).sum())
    for _ in range(60):
        mu = np.exp(Xm @ b + off)
        grad = Xm.T @ (d - mu); I = (Xm * mu[:, None]).T @ Xm
        step = np.linalg.solve(I + 1e-9 * np.eye(len(b)), grad)
        step = step * min(1.0, 3.0 / max(np.abs(step).max(), 1e-12)); b += step
        if np.abs(step).max() < 1e-9: break
    mu = np.exp(Xm @ b + off); I = (Xm * mu[:, None]).T @ Xm; Iinv = np.linalg.inv(I)
    U = np.zeros((len(g), len(b)))
    np.add.at(U, gidx, Xm * (d - mu)[:, None])
    Vr = Iinv @ (U.T @ U) * len(g) / (len(g) - 1) @ Iinv
    f = Fit(); f.names = list(X.columns); f.beta = b; f.se = np.sqrt(np.diag(Iinv)); f.se_robust = np.sqrt(np.diag(Vr))
    f.loglik = float(np.sum(d * np.log(mu) - mu)); f.theta = 0.0; f.groups = g
    D = np.bincount(gidx, d); Hh = np.bincount(gidx, mu); f.D = D; f.H = Hh
    return f


def fit_gamma(cells, ev="ev_all", cov=("kindj", "area", "cohort"), fe=None, group="prefn", start=None):
    X, Xm, d, off, g, gidx = _prep(cells, group, ev, cov, fe)
    D = np.bincount(gidx, d)
    p = Xm.shape[1]

    def nll(par, grad=True):
        b, phi = par[:p], par[p]; th = np.exp(phi); a = 1 / th
        eta = Xm @ b + off; mu = np.exp(eta)
        H = np.bincount(gidx, mu, minlength=len(g))
        ll = np.sum(d * eta) + np.sum(gammaln(D + a) - gammaln(a) + D * phi - (D + a) * np.log1p(th * H))
        if not grad: return -ll
        w = (1 + th * D) / (1 + th * H)
        gb = Xm.T @ (d - w[gidx] * mu)
        dth = np.sum(-(digamma(D + a) - digamma(a)) / th**2 + D / th + np.log1p(th * H) / th**2 - (D + a) * H / (1 + th * H))
        return -ll, -np.r_[gb, th * dth]

    if start is None:
        f0 = fit_poisson(cells, ev, cov, fe, group); start = np.r_[f0.beta, np.log(0.02)]
    best = None
    for phi0 in ([start[-1]] + [np.log(0.002), np.log(0.1)]):
        x0 = np.r_[start[:p], phi0]
        r = minimize(nll, x0, jac=True, method="L-BFGS-B", bounds=[(None, None)] * p + [(-14, 3)],
                     options=dict(maxiter=5000, ftol=1e-13, gtol=1e-7))
        if best is None or r.fun < best.fun: best = r
    r = best
    Hs = _num_hess(lambda x: nll(x)[1], r.x)
    try: cov_ = np.linalg.inv(Hs); se = np.sqrt(np.abs(np.diag(cov_)))
    except Exception: se = np.full(len(r.x), np.nan)
    b, th = r.x[:p], np.exp(r.x[p])
    mu = np.exp(Xm @ b + off); H = np.bincount(gidx, mu, minlength=len(g))
    f = Fit(); f.names = list(X.columns); f.beta = b; f.se = se[:p]; f.theta = th; f.se_logtheta = se[p]
    f.loglik = -r.fun - np.sum(d * off) + np.sum(d * off)  # 比較用（定数込みで fit_poisson と同じ基準）
    # fit_poisson の loglik は Σ d log μ − μ。ガンマの周辺尤度も同じ基準になるよう、-Σ log Γ 等の定数は両方とも落としている
    f.groups = g; f.D = D; f.H = H
    f.post = (D + 1 / th) / (1 / th + H)            # z の事後平均（経験ベイズ）
    f.raw = D / H                                    # 縮める前の「実績÷期待」
    f.converged = r.success
    return f


GH_X, GH_W = np.polynomial.hermite.hermgauss(20)


def _ln_group(D, H, s):
    """適応型ガウス–エルミート：各グループの事後の山の位置と幅に節点を合わせる。
    log ∫ exp(D u − e^u H) N(u; 0, s²) du と、u・e^u の事後平均を返す。"""
    u = np.log((D + 0.5) / (H + 1e-300)) * (H * s**2) / (1 + H * s**2)  # 初期値
    for _ in range(50):
        g1 = D - np.exp(u) * H - u / s**2
        g2 = -np.exp(u) * H - 1 / s**2
        st = np.clip(g1 / g2, -2, 2); u = u - st
        if np.abs(st).max() < 1e-10: break
    sc = 1 / np.sqrt(np.exp(u) * H + 1 / s**2)
    U = u[:, None] + np.sqrt(2) * sc[:, None] * GH_X[None]
    hU = D[:, None] * U - np.exp(U) * H[:, None] - U**2 / (2 * s**2)
    L = hU + GH_X[None] ** 2 + np.log(GH_W)[None] + np.log(np.sqrt(2) * sc)[:, None] - np.log(np.sqrt(2 * np.pi) * s)
    m = L.max(1, keepdims=True); P = np.exp(L - m); S = P.sum(1)
    post = P / S[:, None]
    return np.log(S) + m[:, 0], (post * U).sum(1), (post * np.exp(U)).sum(1)


def fit_lognormal(cells, ev="ev_all", cov=("kindj", "area", "cohort"), fe=None, group="prefn", start=None):
    X, Xm, d, off, g, gidx = _prep(cells, group, ev, cov, fe)
    D = np.bincount(gidx, d); p = Xm.shape[1]

    def nll(par):
        b, s = par[:p], np.exp(par[p])
        eta = Xm @ b + off; mu = np.exp(eta); H = np.bincount(gidx, mu, minlength=len(g))
        lg, Eu, Ez = _ln_group(D, H, s)
        return -(np.sum(d * eta) + lg.sum()), Xm, mu, Ez

    def nll_full(par):
        v, _, mu, Ez = nll(par)
        gb = Xm.T @ (d - Ez[gidx] * mu)
        h = 1e-5; e = np.zeros_like(par); e[-1] = h
        gs = (nll(par + e)[0] - nll(par - e)[0]) / (2 * h)
        return v, -np.r_[gb, -gs]

    if start is None:
        f0 = fit_poisson(cells, ev, cov, fe, group); start = np.r_[f0.beta, np.log(0.15)]
    r = minimize(nll_full, start, jac=True, method="L-BFGS-B", bounds=[(None, None)] * p + [(-8, 1.5)],
                 options=dict(maxiter=5000, ftol=1e-14, gtol=1e-7))
    Hs = _num_hess(lambda x: nll_full(x)[1], r.x)
    try: se = np.sqrt(np.abs(np.diag(np.linalg.inv(Hs))))
    except Exception: se = np.full(len(r.x), np.nan)
    b, s = r.x[:p], np.exp(r.x[p])
    mu = np.exp(Xm @ b + off); H = np.bincount(gidx, mu, minlength=len(g))
    lg, Eu, Ez = _ln_group(D, H, s)
    f = Fit(); f.names = list(X.columns); f.beta = b; f.se = se[:p]; f.sigma = s; f.se_logsigma = se[p]
    f.loglik = -r.fun; f.groups = g; f.D = D; f.H = H; f.post_u = Eu; f.post_z = Ez; f.converged = r.success
    return f


def coef_table(f, keys):
    out = {}
    for k in keys:
        if k in f.names:
            i = f.names.index(k); out[k] = (np.exp(f.beta[i]), np.exp(f.beta[i] - 1.96 * f.se[i]), np.exp(f.beta[i] + 1.96 * f.se[i]))
    return out
