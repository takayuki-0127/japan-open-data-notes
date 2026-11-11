"""F295 共通：架空の4つのリスクの周辺分布と、コピュラの乱数。
すべて架空・説明のための値（実在の会社・規制の数値ではない）。
"""
import numpy as np
from scipy import stats

Q = 0.995           # 必要資本の確率水準（VaR99.5）
TARGET = 100.0      # 単独の必要資本（VaR99.5 − 平均）をそろえる大きさ（億円）
MARG_N = 2_000_000  # 周辺分布を作る年数（経験分布の分位点に使う）
MODULES = ["自然災害", "死亡", "市場", "オペレーショナル"]


def raw_marginal(k, n, rng, xi_cat=0.5):
    """尺度をそろえる前の、モジュール k の1年の損失を n 年分つくる。"""
    if k == 0:  # 自然災害：Poisson(2) 件 × (10 + GPD 超過額)
        cnt = rng.poisson(2.0, n)
        tot = cnt.sum()
        sev = 10.0 + stats.genpareto.rvs(xi_cat, scale=10.0, size=tot, random_state=rng)
        out = np.zeros(n)
        idx = np.repeat(np.arange(n), cnt)
        np.add.at(out, idx, sev)
        return out
    if k == 1:  # 死亡：対数正規の上振れ（平均を引く）
        x = rng.lognormal(0.0, 0.35, n)
        return x - np.exp(0.35 ** 2 / 2)
    if k == 2:  # 市場：自由度4の t
        return rng.standard_t(4, n)
    if k == 3:  # オペレーショナル：Poisson(0.5) 件 × 対数正規(σ=1.5)
        cnt = rng.poisson(0.5, n)
        tot = cnt.sum()
        sev = rng.lognormal(np.log(20.0), 1.5, tot)
        out = np.zeros(n)
        idx = np.repeat(np.arange(n), cnt)
        np.add.at(out, idx, sev)
        return out
    raise ValueError(k)


def capital(x, q=Q):
    """必要資本 = VaR_q − 平均"""
    return np.quantile(x, q) - x.mean()


def tvar_capital(x, q=Q):
    v = np.quantile(x, q)
    return x[x >= v].mean() - x.mean()


def build_marginals(seed=2951, xi_cat=0.5, scale_override=None, n=MARG_N):
    """4つの周辺分布（尺度をそろえた経験分布）を返す。各列は昇順に並べた n 個の値。"""
    rng = np.random.default_rng(seed)
    cols, scales = [], []
    for k in range(4):
        x = raw_marginal(k, n, rng, xi_cat)
        s = TARGET / capital(x)
        if scale_override is not None:
            s *= scale_override[k]
        cols.append(np.sort(x * s))
        scales.append(s)
    return np.column_stack(cols), np.array(scales)


def to_losses(U, marg):
    """一様乱数 U (n×4) を、経験分布の分位点で損失に直す。"""
    m = marg.shape[0]
    idx = np.minimum((U * m).astype(np.int64), m - 1)
    return np.column_stack([marg[idx[:, k], k] for k in range(marg.shape[1])])


def equicorr(rho, d=4):
    return np.full((d, d), rho) + np.eye(d) * (1 - rho)


def u_gauss(n, R, rng):
    L = np.linalg.cholesky(R)
    z = rng.standard_normal((n, R.shape[0])) @ L.T
    return stats.norm.cdf(z)


def u_t(n, R, nu, rng):
    L = np.linalg.cholesky(R)
    z = rng.standard_normal((n, R.shape[0])) @ L.T
    w = rng.chisquare(nu, n) / nu
    t = z / np.sqrt(w)[:, None]
    return stats.t.cdf(t, nu)


def tau_from_rho(rho):
    return 2 / np.pi * np.arcsin(rho)


def u_gumbel(n, d, tau, rng):
    """グンベル（上の裾が一緒に動く）。Marshall–Olkin：正の安定分布を使う。"""
    theta = 1.0 / (1.0 - tau)
    a = 1.0 / theta
    if a >= 1.0:
        return rng.random((n, d))
    th = rng.uniform(-np.pi / 2, np.pi / 2, n)
    w = rng.exponential(1.0, n)
    # Kanter / Chambers–Mallows–Stuck：ラプラス変換が exp(-t^a) になる正の安定分布（数値で確認済み）
    v = (np.sin(a * (th + np.pi / 2)) / np.cos(th) ** (1 / a)
         * (np.cos(th - a * (th + np.pi / 2)) / w) ** ((1 - a) / a))
    e = rng.exponential(1.0, (n, d))
    return np.exp(-(e / v[:, None]) ** a)


def u_clayton_survival(n, d, tau, rng):
    """裏返したクレイトン（上の裾が一緒に動く）。"""
    theta = 2 * tau / (1 - tau)
    v = rng.gamma(1 / theta, 1.0, n)
    e = rng.exponential(1.0, (n, d))
    u = (1 + e / v[:, None]) ** (-1 / theta)
    return 1.0 - u


def u_indep(n, d, rng):
    return rng.random((n, d))


def u_comon(n, d, rng):
    u = rng.random(n)
    return np.repeat(u[:, None], d, axis=1)


def sample_U(kind, n, rng, rho=0.25, nu=4, R=None, d=4):
    if R is None:
        R = equicorr(rho, d)
    tau = tau_from_rho(R[np.triu_indices(d, 1)].mean())
    if kind == "独立":
        return u_indep(n, d, rng)
    if kind == "ガウス":
        return u_gauss(n, R, rng)
    if kind == "t":
        return u_t(n, R, nu, rng)
    if kind == "グンベル":
        return u_gumbel(n, d, tau, rng)
    if kind == "裏返しクレイトン":
        return u_clayton_survival(n, d, tau, rng)
    if kind == "共単調":
        return u_comon(n, d, rng)
    raise ValueError(kind)


def measures(X, q=Q):
    """X (n×4) から、単独・合計の必要資本（VaR・TVaR）と分散効果を返す。"""
    S = X.sum(1)
    sv = np.array([capital(X[:, k], q) for k in range(X.shape[1])])
    st = np.array([tvar_capital(X[:, k], q) for k in range(X.shape[1])])
    av, at = capital(S, q), tvar_capital(S, q)
    return dict(sa_var=sv.sum(), agg_var=av, db_var=1 - av / sv.sum(),
                sa_tvar=st.sum(), agg_tvar=at, db_tvar=1 - at / st.sum())


def formula_db(s, R):
    s = np.asarray(s, float)
    return 1 - np.sqrt(s @ R @ s) / s.sum()


def kendall_check(U, m=20000):
    return stats.kendalltau(U[:m, 0], U[:m, 1]).statistic
