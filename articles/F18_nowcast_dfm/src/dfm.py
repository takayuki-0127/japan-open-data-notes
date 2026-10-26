"""ダイナミックファクターモデル（月次＋四半期）とナウキャストの共通部分"""
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ
from statsmodels.tsa.ar_model import AutoReg
from common import DATA, SERIES

warnings.filterwarnings("ignore")
LAG = {s[0]: s[4] for s in SERIES}


def load():
    p = pd.read_csv(DATA / "monthly_panel.csv", parse_dates=["month"], index_col="month")
    p.index = p.index.to_period("M")
    g = pd.read_csv(DATA / "gdp_q.csv", parse_dates=["month"], index_col="month")["gdp_qoq"]
    g.index = g.index.to_period("M").asfreq("Q")
    return p, g


def vintage(p, g, V, cols, mask=None):
    """V（月末時点）で手に入るデータだけを残す。p は月次、g は四半期（前期比）"""
    V = pd.Period(V, "M")
    z = p[cols].copy()
    for c in cols:
        z.loc[z.index > V - LAG[c], c] = np.nan
    if mask is not None:
        z.loc[mask[0]:mask[1], :] = np.nan
    z = z.loc[:V]
    gv = g.copy()
    # 四半期 q の GDP（1次速報）は q の最後の月の2か月後の半ばに出る → その月末から使える
    rel = (gv.index.asfreq("M", how="end") + 2)
    gv = gv[rel <= V]
    return z, gv


def fit_nowcast(z, gv, target_q, k=1, factor_orders=2, maxiter=300):
    """target_q の GDP 前期比を推定する。データの標準化はその時点のデータだけで行う"""
    tq = pd.Period(target_q, "Q")
    end_m = tq.asfreq("M", how="end")
    idx = pd.period_range(z.index.min(), max(end_m, z.index.max()), freq="M")
    z = z.reindex(idx)
    mu, sd = z.mean(), z.std()
    zz = (z - mu) / sd
    gq_idx = pd.period_range(gv.index.min(), tq, freq="Q")
    gg = gv.reindex(gq_idx)
    gm, gs = gg.mean(), gg.std()
    gz = ((gg - gm) / gs).to_frame("GDP")
    # 月次の開始より前の四半期は落とす
    gz = gz[gz.index.asfreq("M", how="start") >= zz.index.min()]
    if k == 1:
        factors = 1
    else:
        factors = k
    mod = DynamicFactorMQ(zz, endog_quarterly=gz, factors=factors, factor_orders=factor_orders,
                          idiosyncratic_ar1=True, standardize=False)
    res = mod.fit(disp=False, maxiter=maxiter)
    pred = res.get_prediction(information_set="smoothed").predicted_mean
    v = pred.loc[end_m, "GDP"] * gs + gm
    return float(v), res


def ar_nowcast(gv, target_q, p=1):
    """AR(p) で target_q の前期比を予測（手に入る最後の四半期から何期先か）"""
    tq = pd.Period(target_q, "Q")
    y = gv.dropna()
    h = (tq - y.index.max()).n
    m = AutoReg(y.values, lags=p, trend="c").fit()
    f = m.forecast(h)
    return float(f[-1]), h


def mean_nowcast(gv):
    return float(gv.dropna().mean())
