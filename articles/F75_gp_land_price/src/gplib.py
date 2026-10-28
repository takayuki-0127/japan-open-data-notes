"""ガウス過程・比較モデル・CV の分け方（02〜04 で共通）"""
import numpy as np, pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor as GPR
from sklearn.gaussian_process.kernels import ConstantKernel as C, Matern, RBF, RationalQuadratic, WhiteKernel
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, GroupKFold
from sklearn.neighbors import KNeighborsRegressor
import lightgbm as lgb
from common import SEED, COV, NUM_LGB, CAT_LGB, LGB_PARAMS

N_HYPER = 1000   # ハイパーパラメータの推定に使う学習データの点数（計算を軽くするため）
MAXITER = 60     # L-BFGS-B の反復の上限（計算を軽くするため）


def _opt(obj_func, initial_theta, bounds):
    from scipy.optimize import minimize
    r = minimize(obj_func, initial_theta, method="L-BFGS-B", jac=True, bounds=bounds,
                 options={"maxiter": MAXITER})
    return r.x, r.fun


def kernel(name="matern15", dims=2):
    ls = np.ones(dims) * (5.0 if dims == 2 else 1.0) if dims > 2 else 5.0
    b = (0.05, 500.0)
    base = {"matern05": Matern(ls, b, nu=0.5), "matern15": Matern(ls, b, nu=1.5),
            "matern25": Matern(ls, b, nu=2.5), "rbf": RBF(ls, b),
            "rq": RationalQuadratic(length_scale=5.0, alpha=1.0, length_scale_bounds=b)}[name]
    return C(1.0, (1e-3, 1e2)) * base + WhiteKernel(0.05, (1e-5, 1e1))


def gp_fit_predict(Xtr, ytr, Xte, kern, seed=SEED, n_hyper=N_HYPER):
    """部分標本でハイパーパラメータを推定 → 学習データ全部で条件付けて予測（平均と標準偏差）"""
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(Xtr), min(n_hyper, len(Xtr)), replace=False)
    g = GPR(kern, normalize_y=True, n_restarts_optimizer=0, random_state=seed, optimizer=_opt).fit(Xtr[idx], ytr[idx])
    g2 = GPR(g.kernel_, normalize_y=True, optimizer=None).fit(Xtr, ytr)
    mu, sd = [], []
    for i in range(0, len(Xte), 2000):
        m, s = g2.predict(Xte[i:i + 2000], return_std=True)
        mu.append(m); sd.append(s)
    return np.concatenate(mu), np.concatenate(sd), g.kernel_


def zfit(tr, te, cols):
    m, s = tr[cols].mean(), tr[cols].std().replace(0, 1)
    return ((tr[cols] - m) / s).fillna(0).values, ((te[cols] - m) / s).fillna(0).values


def model_fit_predict(name, tr, te, kern_name="matern15", n_hyper=N_HYPER):
    """戻り値：予測（対数）、標準偏差（なければ None）、推定したカーネル（なければ None）"""
    ytr = tr["y"].values
    XY_tr, XY_te = tr[["x_km", "y_km"]].values, te[["x_km", "y_km"]].values
    if name == "knn10":
        m = KNeighborsRegressor(10, weights="distance").fit(XY_tr, ytr)
        return m.predict(XY_te), None, None
    if name == "gp_map":
        return gp_fit_predict(XY_tr, ytr, XY_te, kernel(kern_name), n_hyper=n_hyper)
    if name == "ridge":
        a, b = zfit(tr, te, COV)
        return Ridge(1.0).fit(a, ytr).predict(b), None, None
    if name == "rk":  # 回帰クリギング：共変量の回帰 + 残差を地図のガウス過程で補間
        a, b = zfit(tr, te, COV)
        r = Ridge(1.0).fit(a, ytr)
        mu, sd, k = gp_fit_predict(XY_tr, ytr - r.predict(a), XY_te, kernel(kern_name), n_hyper=n_hyper)
        return r.predict(b) + mu, sd, k
    if name == "gp_ard":  # 座標と共変量のすべてに長さスケールを持たせたガウス過程
        cols = ["x_km", "y_km"] + COV
        a, b = zfit(tr, te, cols)
        return gp_fit_predict(a, ytr, b, kernel(kern_name, dims=len(cols)), n_hyper=n_hyper)
    if name == "lgbm":
        cols = NUM_LGB + CAT_LGB
        A, B = tr[cols].copy(), te[cols].copy()
        for c in CAT_LGB:
            cat = pd.Categorical(pd.concat([A[c], B[c]]).astype(str))
            A[c] = pd.Categorical(A[c].astype(str), categories=cat.categories)
            B[c] = pd.Categorical(B[c].astype(str), categories=cat.categories)
        m = lgb.LGBMRegressor(**LGB_PARAMS).fit(A, ytr)
        return m.predict(B), None, None
    raise ValueError(name)


def splits(d, kind, k=5):
    if kind == "random":
        return list(KFold(k, shuffle=True, random_state=SEED).split(d))
    g = d[kind]
    rng = np.random.default_rng(SEED)
    u = g.unique(); perm = dict(zip(u, rng.permutation(len(u))))
    return list(GroupKFold(k).split(d, groups=g.map(perm)))


def oof(d, name, kind, **kw):
    p = np.full(len(d), np.nan); s = np.full(len(d), np.nan); ks = []
    for tr, te in splits(d, kind):
        mu, sd, k = model_fit_predict(name, d.iloc[tr], d.iloc[te], **kw)
        p[te] = mu
        if sd is not None:
            s[te] = sd
        ks.append(str(k))
    return p, (s if not np.isnan(s).all() else None), ks
