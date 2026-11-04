"""共通：欠測の作り方、埋め方、推定したい値（6つ）、ルービンのルール。"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parents[1]
RES = BASE / "results"
FIG = BASE / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
(BASE / "data" / "raw").mkdir(parents=True, exist_ok=True)
SEED = 20261104

COLS = ["logpop", "aging", "logdens", "births", "single", "logtax", "unemp", "tert"]
MISS = ["logtax", "unemp", "tert"]  # 欠かす3つ
IDX = {c: i for i, c in enumerate(COLS)}
UNEMP_CUT = 5.0  # 「失業率5%以上の割合」に使う境目


def load():
    return pd.read_csv(BASE / "data" / "muni.csv")[COLS].to_numpy(float)


# ---------------------------------------------------------------- 推定したい値
EST = ["mean_tax", "p90_tax", "sd_unemp", "share_unemp5", "corr_unemp_tert", "coef_tert"]
EST_JA = {
    "mean_tax": "1人あたり地方税の平均（千円）",
    "p90_tax": "1人あたり地方税の90%点（千円）",
    "sd_unemp": "失業率の標準偏差（ポイント）",
    "share_unemp5": "失業率5%以上の市区町村の割合（%）",
    "corr_unemp_tert": "失業率と第3次産業の割合の相関",
    "coef_tert": "第3次産業の割合1ポイントあたりの地方税の差（%）",
}
HAS_SE = ["mean_tax", "share_unemp5", "corr_unemp_tert", "coef_tert"]


def ols_hc1(y, X):
    X = np.column_stack([np.ones(len(y)), X])
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    n, k = X.shape
    meat = (X * e[:, None] ** 2).T @ X
    V = XtX_inv @ meat @ XtX_inv * n / (n - k)
    return b, np.sqrt(np.diag(V))


def estimates(D, coef_model="log"):
    """完全な（埋めた）データ D から6つの値と、使える場合は標準誤差を返す。
    推定量はすべて「変換後の尺度」で SE を持つ（相関は Fisher z）。"""
    tax = np.exp(D[:, IDX["logtax"]])
    un = D[:, IDX["unemp"]]
    te = D[:, IDX["tert"]]
    n = len(D)
    q, se = {}, {}
    q["mean_tax"] = tax.mean()
    se["mean_tax"] = tax.std(ddof=1) / np.sqrt(n)
    q["p90_tax"] = np.quantile(tax, 0.9)
    q["sd_unemp"] = un.std(ddof=1)
    p = (un >= UNEMP_CUT).mean()
    q["share_unemp5"] = 100 * p
    se["share_unemp5"] = 100 * np.sqrt(max(p * (1 - p), 1e-12) / n)
    r = np.corrcoef(un, te)[0, 1]
    q["corr_unemp_tert"] = np.arctanh(np.clip(r, -0.999999, 0.999999))  # z 尺度
    se["corr_unemp_tert"] = 1 / np.sqrt(n - 3)
    yv = D[:, IDX["logtax"]] if coef_model == "log" else tax
    X = np.column_stack([te, D[:, IDX["aging"]], D[:, IDX["logdens"]], un])
    b, s = ols_hc1(yv, X)
    scale = 100 if coef_model == "log" else 1
    q["coef_tert"] = scale * b[1]
    se["coef_tert"] = scale * s[1]
    return q, se


def available_case(Dm, coef_model="log"):
    """値がある市区町村だけで計算する（値ごとに使える行を使う。回帰と相関は全部そろった行）。"""
    M = np.isnan(Dm)
    q, se = {}, {}
    t_ok = ~M[:, IDX["logtax"]]
    u_ok = ~M[:, IDX["unemp"]]
    tax = np.exp(Dm[t_ok, IDX["logtax"]])
    q["mean_tax"] = tax.mean()
    se["mean_tax"] = tax.std(ddof=1) / np.sqrt(len(tax))
    q["p90_tax"] = np.quantile(tax, 0.9)
    un = Dm[u_ok, IDX["unemp"]]
    q["sd_unemp"] = un.std(ddof=1)
    p = (un >= UNEMP_CUT).mean()
    q["share_unemp5"] = 100 * p
    se["share_unemp5"] = 100 * np.sqrt(max(p * (1 - p), 1e-12) / len(un))
    ut = u_ok & ~M[:, IDX["tert"]]
    r = np.corrcoef(Dm[ut, IDX["unemp"]], Dm[ut, IDX["tert"]])[0, 1]
    q["corr_unemp_tert"] = np.arctanh(r)
    se["corr_unemp_tert"] = 1 / np.sqrt(ut.sum() - 3)
    allok = ~M[:, [IDX[c] for c in MISS]].any(axis=1)
    sub = Dm[allok]
    yv = sub[:, IDX["logtax"]] if coef_model == "log" else np.exp(sub[:, IDX["logtax"]])
    X = np.column_stack([sub[:, IDX["tert"]], sub[:, IDX["aging"]], sub[:, IDX["logdens"]], sub[:, IDX["unemp"]]])
    b, s = ols_hc1(yv, X)
    scale = 100 if coef_model == "log" else 1
    q["coef_tert"], se["coef_tert"] = scale * b[1], scale * s[1]
    return q, se


def rubin(qs, ses):
    """ルービンのルール。qs, ses は m 個の dict。戻り値：点推定・SE・自由度・fmi（SEのある値だけ）。"""
    m = len(qs)
    out = {}
    for k in qs[0]:
        Q = np.array([x[k] for x in qs])
        qbar = Q.mean()
        if k in ses[0]:
            U = np.mean([x[k] ** 2 for x in ses])
            B = Q.var(ddof=1) if m > 1 else 0.0
            T = U + (1 + 1 / m) * B
            r = (1 + 1 / m) * B / U if U > 0 else 0
            df = (m - 1) * (1 + 1 / r) ** 2 if r > 0 else 1e6
            fmi = (r + 2 / (df + 3)) / (r + 1)
            out[k] = (qbar, np.sqrt(T), df, fmi)
        else:
            out[k] = (qbar, np.nan, np.nan, np.nan)
    return out


# ---------------------------------------------------------------- 欠測の作り方
def make_missing(D, mech, rate, rng, strength=1.5):
    """MISS の3列を、それぞれ割合 rate で欠かす（列ごとに独立に判定）。
    mcar：でたらめ／mar：人口が小さいほど欠ける／mnar：その値自体が大きいほど欠ける。
    strength は1標準偏差あたりのロジットの傾き。"""
    Dm = D.copy()
    n = len(D)
    for c in MISS:
        if mech == "mcar":
            z = np.zeros(n)
        elif mech == "mar":
            v = D[:, IDX["logpop"]]
            z = -strength * (v - v.mean()) / v.std()
        elif mech == "mnar":
            v = D[:, IDX[c]]
            z = strength * (v - v.mean()) / v.std()
        else:
            raise ValueError(mech)
        # 平均の欠測率が rate になるよう切片を二分法で合わせる
        lo, hi = -20, 20
        for _ in range(60):
            a = (lo + hi) / 2
            if (1 / (1 + np.exp(-(a + z)))).mean() > rate:
                hi = a
            else:
                lo = a
        pr = 1 / (1 + np.exp(-(a + z)))
        Dm[rng.random(n) < pr, IDX[c]] = np.nan
    return Dm


# ---------------------------------------------------------------- 埋め方
def _bayes_draw(Xo, yo, rng):
    Xo1 = np.column_stack([np.ones(len(yo)), Xo])
    XtX_inv = np.linalg.pinv(Xo1.T @ Xo1)
    bhat = XtX_inv @ Xo1.T @ yo
    resid = yo - Xo1 @ bhat
    dfree = len(yo) - Xo1.shape[1]
    s2 = resid @ resid / rng.chisquare(dfree)
    L = np.linalg.cholesky(XtX_inv * s2 + 1e-12 * np.eye(len(bhat)))
    bstar = bhat + L @ rng.standard_normal(len(bhat))
    return bhat, bstar, np.sqrt(s2)


def mice(Dm, m, rng, method="pmm", iters=10, k=5, use=None):
    """連鎖方程式による多重代入（m 本の鎖を別々に回す）。method は 'norm'（正規分布から引く）か 'pmm'（予測平均マッチング）。
    use：埋めるときに使う列（既定は全列）。戻り値は m 個の完全データ。"""
    M = np.isnan(Dm)
    targets = [IDX[c] for c in MISS if M[:, IDX[c]].any()]
    use = list(range(Dm.shape[1])) if use is None else [IDX[c] for c in use]
    outs = []
    for _ in range(m):
        D = Dm.copy()
        for j in targets:  # 初期値：観測値からでたらめに引く
            obs = D[~M[:, j], j]
            D[M[:, j], j] = rng.choice(obs, M[:, j].sum())
        for _ in range(iters):
            for j in targets:
                pred = [c for c in use if c != j]
                o, mi = ~M[:, j], M[:, j]
                Xo, Xm, yo = D[o][:, pred], D[mi][:, pred], D[o, j]
                bhat, bstar, s = _bayes_draw(Xo, yo, rng)
                Xm1 = np.column_stack([np.ones(mi.sum()), Xm])
                if method == "norm":
                    D[mi, j] = Xm1 @ bstar + s * rng.standard_normal(mi.sum())
                else:
                    yh_o = np.column_stack([np.ones(o.sum()), Xo]) @ bhat
                    yh_m = Xm1 @ bstar
                    # 予測値の近い k 件から1件を引く（並べ替えて前後 k 件ずつの候補だけを比べる）
                    order = np.argsort(yh_o)
                    ys = yh_o[order]
                    pos = np.searchsorted(ys, yh_m)
                    cand = np.clip(pos[:, None] + np.arange(-k, k)[None, :], 0, len(ys) - 1)
                    dist = np.abs(ys[cand] - yh_m[:, None])
                    dist[:, 1:][cand[:, 1:] == cand[:, :-1]] = np.inf  # 端で重なった候補を除く
                    nn = np.take_along_axis(cand, np.argsort(dist, axis=1)[:, :k], axis=1)
                    pick = nn[np.arange(len(nn)), rng.integers(0, k, len(nn))]
                    D[mi, j] = yo[order[pick]]
        outs.append(D)
    return outs


def mice_strat(Dm, m, rng, method="pmm", strata=5, **kw):
    """人口（欠かさない列）の大きさで strata 個のグループに分け、グループごとに別々に多重代入する。
    すべての関係が町の大きさで変わってよい、という柔らかい埋め方。"""
    lp = Dm[:, IDX["logpop"]]
    g = np.searchsorted(np.quantile(lp, np.linspace(0, 1, strata + 1)[1:-1]), lp, side="right")
    outs = [Dm.copy() for _ in range(m)]
    for k in range(strata):
        sel = g == k
        parts = mice(Dm[sel], m, rng, method=method, **kw)
        for D, P in zip(outs, parts):
            D[sel] = P
    return outs


def fill_mean(Dm):
    D = Dm.copy()
    for c in MISS:
        j = IDX[c]
        D[np.isnan(D[:, j]), j] = np.nanmean(D[:, j])
    return D


def fill_regression(Dm, rng):
    """回帰の予測値で1回だけ埋める（ばらつきを足さない）。連鎖方程式で10回回す。"""
    M = np.isnan(Dm)
    D = fill_mean(Dm)
    for _ in range(10):
        for c in MISS:
            j = IDX[c]
            if not M[:, j].any():
                continue
            pred = [i for i in range(D.shape[1]) if i != j]
            o, mi = ~M[:, j], M[:, j]
            X1 = np.column_stack([np.ones(o.sum()), D[o][:, pred]])
            b = np.linalg.lstsq(X1, D[o, j], rcond=None)[0]
            D[mi, j] = np.column_stack([np.ones(mi.sum()), D[mi][:, pred]]) @ b
    return D


def fill_knn(Dm, k=5):
    from sklearn.impute import KNNImputer
    mu, sd = np.nanmean(Dm, 0), np.nanstd(Dm, 0)
    Z = KNNImputer(n_neighbors=k).fit_transform((Dm - mu) / sd)
    return Z * sd + mu


def fill_forest(Dm, seed):
    from sklearn.ensemble import ExtraTreesRegressor
    from sklearn.experimental import enable_iterative_imputer  # noqa: F401
    from sklearn.impute import IterativeImputer
    imp = IterativeImputer(estimator=ExtraTreesRegressor(n_estimators=40, min_samples_leaf=3, random_state=seed, n_jobs=1),
                           max_iter=5, random_state=seed)
    return imp.fit_transform(Dm)


def ci_cover(q, se, df, truth):
    t = stats.t.ppf(0.975, df) if np.isfinite(df) and df < 1e5 else 1.959964
    return (q - t * se <= truth) & (truth <= q + t * se), 2 * t * se
