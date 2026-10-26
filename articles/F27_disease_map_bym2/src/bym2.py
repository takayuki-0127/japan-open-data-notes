"""BYM2 モデル（Riebler ら 2016）を PyMC で書く。
log θ_i = α + Xβ + σ ( √(ρ/s) φ_i + √(1−ρ) ε_i )
  φ：ICAR（隣の区域の平均に引っぱられる空間効果、和が0）、ε：区域ごとの独立な効果
  s：ICAR の分散の幾何平均（隣接の形によらず σ を「全体のばらつき」として読めるようにする尺度合わせ）
O_i ~ Poisson(E_i θ_i)"""
import numpy as np
import pymc as pm
import pytensor.tensor as pt
from scipy.sparse.csgraph import connected_components


def connect(A, P):
    """隣接行列 A（0/1）が1つにつながるよう、離れた塊どうしを最も近い区域の組で結ぶ。結んだ数を返す。"""
    A = A.copy()
    added = 0
    while True:
        k, lab = connected_components(A, directed=False)
        if k == 1:
            return A, added
        big = np.bincount(lab).argmax()
        ins, out = np.where(lab == big)[0], np.where(lab != big)[0]
        # いちばん大きい塊と、それ以外のいちばん近い組
        d = np.hypot(P[out, None, 0] - P[None, ins, 0], P[out, None, 1] - P[None, ins, 1])
        i, j = np.unravel_index(np.argmin(d), d.shape)
        # その区域が属する塊を1本で結ぶ
        a, b = out[i], ins[j]
        A[a, b] = A[b, a] = 1
        added += 1


def scale_factor(A):
    """ICAR の精度行列 Q = D − A の一般化逆行列の対角の幾何平均。"""
    Q = np.diag(A.sum(1)) - A
    n = len(A)
    # 和が0の制約をつけた逆行列：Q + 11ᵀ/n の逆から 11ᵀ/n を引く
    one = np.ones((n, n)) / n
    V = np.linalg.inv(Q + one) - one
    return float(np.exp(np.mean(np.log(np.diag(V)))))


def fit(O, E, A, X=None, prior="pc", draws=1000, tune=1500, chains=4, seed=27):
    n = len(O)
    s = scale_factor(A)
    logE = np.log(E)
    with pm.Model() as m:
        alpha = pm.Normal("alpha", 0, 1)
        if prior == "pc":
            # PC 事前分布：P(σ > 1) = 0.01、ρ は Beta(0.5, 0.5)
            sigma = pm.Exponential("sigma", lam=-np.log(0.01) / 1.0)
            rho = pm.Beta("rho", 0.5, 0.5)
        else:
            # 頑健性：より広い事前分布
            sigma = pm.HalfNormal("sigma", 1.0)
            rho = pm.Uniform("rho", 0, 1)
        phi = pm.ICAR("phi", W=A)
        eps = pm.Normal("eps", 0, 1, shape=n)
        u = sigma * (pt.sqrt(rho / s) * phi + pt.sqrt(1 - rho) * eps)
        eta = alpha + u
        if X is not None:
            beta = pm.Normal("beta", 0, 1, shape=X.shape[1])
            eta = eta + pt.dot(X, beta)
        pm.Deterministic("theta", pt.exp(eta))
        pm.Deterministic("spatial", sigma * pt.sqrt(rho / s) * phi)
        pm.Deterministic("iid", sigma * pt.sqrt(1 - rho) * eps)
        pm.Poisson("O", mu=np.asarray(E) * pt.exp(eta), observed=np.asarray(O).astype(int))
        idata = pm.sample(draws=draws, tune=tune, chains=chains, random_seed=seed,
                          nuts_sampler="nutpie", progressbar=False)
    return idata, s
