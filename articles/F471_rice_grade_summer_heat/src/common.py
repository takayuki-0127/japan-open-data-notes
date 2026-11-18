"""共通の関数（固定効果の回帰など）。"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

SEED = 20261116
REG7 = {"北海道": "北海道・東北", "東北": "北海道・東北", "関東": "関東", "北陸": "北陸", "東海": "東海",
        "近畿": "近畿", "中国四国": "中国四国", "九州": "九州", "沖縄": "九州"}
REG_ORDER = ["北海道・東北", "関東", "北陸", "東海", "近畿", "中国四国", "九州"]
SMALL = ["東京", "神奈川", "山梨", "大阪", "和歌山", "沖縄"]


def design(d, xcols, trend=True, year_fe=False):
    X = d[xcols].astype(float).copy()
    if trend and not year_fe:
        X["trend"] = d["year"] - 2015
    P = pd.get_dummies(d["pref"], prefix="p", dtype=float)
    X = pd.concat([X, P], axis=1)
    if year_fe:
        Y = pd.get_dummies(d["year"], prefix="y", dtype=float, drop_first=True)
        X = pd.concat([X, Y], axis=1)
    return X


def fe_ols(d, xcols, y="r1", trend=True, year_fe=False, weights=None, cluster="year"):
    d = d.reset_index(drop=True)
    X = design(d, xcols, trend, year_fe)
    if weights is None:
        m = sm.OLS(d[y].astype(float), X)
    else:
        m = sm.WLS(d[y].astype(float), X, weights=d[weights].astype(float))
    groups = pd.factorize(d[cluster], sort=True)[0]
    r = m.fit(cov_type="cluster", cov_kwds={"groups": groups})
    return r


def coef(r, name):
    ci = r.conf_int().loc[name]
    return dict(b=float(r.params[name]), se=float(r.bse[name]), lo=float(ci[0]), hi=float(ci[1]), n=int(r.nobs))
