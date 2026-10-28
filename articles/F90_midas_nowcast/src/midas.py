"""MIDAS 回帰・ブリッジ方程式・AR の共通部分（疑似リアルタイムのデータの切り出しは F18 と同じ）"""
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.special import betaln
from statsmodels.tsa.ar_model import AutoReg
from common import DATA, LAG

warnings.filterwarnings("ignore")


def load():
    p = pd.read_csv(DATA / "panel_monthly.csv", index_col="month")
    p.index = pd.PeriodIndex(p.index, freq="M")
    g = pd.read_csv(DATA / "gdp_quarterly.csv", index_col="quarter")["gdp_qoq"]
    g.index = pd.PeriodIndex(g.index, freq="Q")
    return p, g


def vintage(p, g, V, cols):
    """月末 V の時点で手に入るデータだけを残す（F18 の vintage と同じ規則）"""
    V = pd.Period(V, "M")
    z = p[cols].copy()
    for c in cols:
        z.loc[z.index > V - LAG[c], c] = np.nan
    z = z.loc[:V]
    rel = g.index.asfreq("M", how="end") + 2  # 1次速報はその四半期の最後の月の2か月後
    return z, g[rel <= V]


# ---------- ラグの重み ----------
def w_almon(th, K):
    k = np.arange(K, dtype=float)
    e = th[0] * k + th[1] * k ** 2
    e = e - e.max()
    w = np.exp(e)
    return w / w.sum()


def w_beta(th, K):
    """beta ラグ（第1パラメータ=1 に固定、第2パラメータだけ推定：単調に減る〜平ら）"""
    eps = 1e-6
    x = (np.arange(K) + 0.5) / K
    b = np.exp(th[0])  # >0
    a = 1.0
    lw = (a - 1) * np.log(x + eps) + (b - 1) * np.log(1 - x + eps) - betaln(a, b)
    w = np.exp(lw - lw.max())
    return w / w.sum()


def build_xy(x, y, d, K, gap):
    """四半期 s ごとに、月次 x の「s の最後の月 − d」から K か月さかのぼった値と、y の gap 期前を並べる。
    d：その四半期の最後の月から、手に入る最後の月までの距離（0=最後の月まで出ている、2=1か月目だけ等）"""
    rows, ys, idx = [], [], []
    for s in y.index:
        anchor = s.asfreq("M", how="end") - d
        lagm = [anchor - k for k in range(K)]
        if lagm[-1] < x.index.min() or anchor > x.index.max():
            continue
        xv = x.reindex(lagm).values
        ylag = y.get(s - gap, np.nan) if gap > 0 else np.nan
        rows.append(np.r_[xv, ylag])
        ys.append(y.get(s, np.nan))
        idx.append(s)
    X = np.array(rows)
    return X, np.array(ys), idx


def fit_predict_midas(x, yhist, target_q, d, gap, K=6, weight="almon", use_ar=True):
    """1つの月次系列による MIDAS 回帰で target_q を予測する（直接予測、d と gap ごとに推定）"""
    # 学習データ
    X, Y, idx = build_xy(x, yhist, d, K, gap)
    ok = ~np.isnan(Y) & ~np.isnan(X[:, :K]).any(1)
    if use_ar:
        ok &= ~np.isnan(X[:, K])
    X, Y = X[ok], Y[ok]
    if len(Y) < 20:
        return np.nan, None
    # 予測に使う行
    Xt, _, it = build_xy(x, pd.Series({target_q: np.nan}, dtype=float).combine_first(yhist), d, K, gap)
    row = Xt[it.index(target_q)] if target_q in it else None
    if row is None or np.isnan(row[:K]).any():
        return np.nan, None
    if use_ar and np.isnan(row[K]):
        return np.nan, None
    # 標準化（学習データの平均・標準偏差）
    mu, sd = np.nanmean(X[:, :K]), np.nanstd(X[:, :K]) or 1.0
    Xs, rs = (X[:, :K] - mu) / sd, (row[:K] - mu) / sd
    ar_col, ar_t = (X[:, K], row[K]) if use_ar else (np.zeros(len(Y)), 0.0)
    if weight == "umidas":
        A = np.column_stack([np.ones(len(Y)), Xs] + ([ar_col] if use_ar else []))
        beta, *_ = np.linalg.lstsq(A, Y, rcond=None)
        at = np.r_[1.0, rs, [ar_t] if use_ar else []]
        return float(at @ beta), dict(w=beta[1:K + 1] / (np.abs(beta[1:K + 1]).sum() or 1))
    wf = w_almon if weight == "almon" else w_beta
    nth = 2 if weight == "almon" else 1

    def resid(par):
        a, b, c = par[0], par[1], par[2]
        w = wf(par[3:], K)
        return a + b * (Xs @ w) + c * ar_col - Y

    best = None
    starts = ([[0, 0], [-0.3, 0], [0.2, -0.05]] if weight == "almon" else [[0.0], [1.0], [2.0]])
    lb = [-np.inf, -np.inf, -np.inf] + ([-2, -0.5] if weight == "almon" else [-3])
    ub = [np.inf, np.inf, np.inf] + ([2, 0.5] if weight == "almon" else [4])
    for st in starts:
        r = least_squares(resid, np.r_[np.mean(Y), 0.1, 0.0, st], bounds=(lb, ub))
        if best is None or r.cost < best.cost:
            best = r
    par = best.x
    w = wf(par[3:], K)
    pred = par[0] + par[1] * (rs @ w) + par[2] * ar_t
    return float(pred), dict(w=w, b=par[1], c=par[2])


def fit_predict_bridge(x, yhist, target_q, gap, use_ar=True):
    """ブリッジ方程式：足りない月を月次の AR(2) で埋めて四半期平均にし、GDP に回帰する"""
    xs = x.dropna()
    if len(xs) < 36:
        return np.nan
    end_m = target_q.asfreq("M", how="end")
    last = xs.index.max()
    if last < end_m:
        h = (end_m - last).n
        m = AutoReg(xs.values, lags=2, trend="c").fit()
        f = m.forecast(h)
        xs = pd.concat([xs, pd.Series(f, index=pd.period_range(last + 1, end_m, freq="M"))])
    q = xs.copy()
    q.index = q.index.asfreq("Q")
    cnt = q.groupby(level=0).count()
    xq = q.groupby(level=0).mean()[cnt == 3]
    df = pd.DataFrame({"y": yhist, "x": xq})
    df["ylag"] = yhist.shift(gap) if gap > 0 else np.nan
    train = df.dropna(subset=["y", "x"] + (["ylag"] if use_ar else []))
    if len(train) < 20 or target_q not in xq.index:
        return np.nan
    A = np.column_stack([np.ones(len(train)), train.x] + ([train.ylag] if use_ar else []))
    beta, *_ = np.linalg.lstsq(A, train.y.values, rcond=None)
    yl = yhist.get(target_q - gap, np.nan)
    if use_ar and np.isnan(yl):
        return np.nan
    at = np.r_[1.0, xq[target_q]] if not use_ar else np.r_[1.0, xq[target_q], yl]
    return float(at @ beta)


def ar_nowcast(gv, target_q):
    y = gv.dropna()
    h = (target_q - y.index.max()).n
    m = AutoReg(y.values, lags=1, trend="c").fit()
    return float(m.forecast(h)[-1]), h
