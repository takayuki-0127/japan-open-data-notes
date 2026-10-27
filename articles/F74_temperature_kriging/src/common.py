import numpy as np, pandas as pd, warnings
from scipy.spatial import cKDTree
from pykrige.ok import OrdinaryKriging
import lightgbm as lgb
from sklearn.linear_model import LinearRegression
warnings.filterwarnings('ignore')
LAT0, LON0 = 36.0, 137.0
def xy(df):
    x = (df['lon'].values - LON0) * np.cos(np.radians(LAT0)) * 111.32
    y = (df['lat'].values - LAT0) * 110.57
    return x, y
def idw(xt, yt, vt, xp, yp, p=2, k=12):
    tr = cKDTree(np.c_[xt, yt]); d, i = tr.query(np.c_[xp, yp], k=k)
    d = np.maximum(d, 1e-6); w = 1/d**p
    return (w*vt[i]).sum(1)/w.sum(1)
def ok(xt, yt, vt, xp, yp, model='spherical', nlags=20):
    m = OrdinaryKriging(xt, yt, vt, variogram_model=model, nlags=nlags, verbose=False, enable_plotting=False)
    z, s2 = m.execute('points', xp, yp, backend='C', n_closest_points=40)
    return np.asarray(z), np.sqrt(np.maximum(np.asarray(s2), 0)), m
def feats(df):
    x, y = xy(df)
    return np.c_[df['lat'].values, df['lon'].values, df['alt'].values/100, x, y]
def lin(tr, te, target):
    X = tr[['lat','lon']].assign(alt=tr.alt/100).values; Xp = te[['lat','lon']].assign(alt=te.alt/100).values
    m = LinearRegression().fit(X, tr[target].values)
    return m.predict(Xp), m
def rk(tr, te, target, model='spherical'):
    pl, m = lin(tr, te, target)
    res = tr[target].values - m.predict(tr[['lat','lon']].assign(alt=tr.alt/100).values)
    xt, yt = xy(tr); xp, yp = xy(te)
    zr, s, _ = ok(xt, yt, res, xp, yp, model)
    return pl + zr, s
def gbm(tr, te, target, seed=0):
    m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=10, subsample=0.8, subsample_freq=1, colsample_bytree=1.0, random_state=seed, verbose=-1)
    m.fit(feats(tr), tr[target].values)
    return m.predict(feats(te))
def gbm_xy(tr, te, target, seed=0):
    m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=10, subsample=0.8, subsample_freq=1, random_state=seed, verbose=-1)
    f = lambda d: feats(d)[:, [0,1,3,4]]
    m.fit(f(tr), tr[target].values); return m.predict(f(te))
METHODS = ['IDW','OK','線形回帰','RK','LightGBM']
def predict_all(tr, te, target, model='spherical', p=2, k=12, seed=0):
    xt, yt = xy(tr); xp, yp = xy(te); v = tr[target].values
    out = {}
    out['IDW'] = idw(xt, yt, v, xp, yp, p, k)
    z, s, _ = ok(xt, yt, v, xp, yp, model); out['OK'] = z; out['OK_sd'] = s
    out['線形回帰'], _ = lin(tr, te, target)
    z, s = rk(tr, te, target, model); out['RK'] = z; out['RK_sd'] = s
    out['LightGBM'] = gbm(tr, te, target, seed)
    return out
