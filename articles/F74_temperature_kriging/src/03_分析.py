# 交差検証で、IDW・通常クリギング（OK）・線形回帰（緯度・経度・標高）・回帰クリギング（RK）・LightGBM を比べる
import numpy as np, pandas as pd, json, sys
from pathlib import Path
from sklearn.model_selection import KFold, GroupKFold
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *
B = Path(__file__).resolve().parents[1]; R = B/'results'
d = pd.read_csv(B/'data/normals_mean_temp.csv', dtype={'id':str}).reset_index(drop=True)
TARGETS = {'annual':'年平均','m1':'1月','m4':'4月','m8':'8月','m10':'10月'}
def cv(df, target, scheme, model='spherical', p=2, k=12, seed=0, nf=10):
    if scheme == 'point': spl = KFold(nf, shuffle=True, random_state=seed).split(df)
    else:
        g = df['area'] if scheme == 'area' else df['block']
        spl = GroupKFold(nf).split(df, groups=g)
    pred = {m: np.full(len(df), np.nan) for m in METHODS + ['OK_sd','RK_sd']}
    for tr_i, te_i in spl:
        o = predict_all(df.iloc[tr_i], df.iloc[te_i], target, model, p, k, seed)
        for m, v in o.items(): pred[m][te_i] = v
    return pd.DataFrame(pred)
def metrics(df, P, target):
    y = df[target].values; out = {}
    for m in METHODS:
        e = P[m].values - y
        out[m] = dict(rmse=float(np.sqrt(np.mean(e**2))), mae=float(np.mean(np.abs(e))), bias=float(np.mean(e)))
    return out
# 1) 本体：年平均・各月 × 点で分ける／地域（予報区の番号）で分ける
x, y = xy(d)
d['block'] = (np.floor(x/100)).astype(int)*1000 + np.floor(y/100).astype(int)   # 100km 四方
res = []; keep = {}
for t, lab in TARGETS.items():
    for sch in ['point', 'area', 'block']:
        P = cv(d, t, sch); keep[(t, sch)] = P
        for m, v in metrics(d, P, t).items(): res.append(dict(target=t, label=lab, scheme=sch, method=m, **v))
    print(t, 'done', flush=True)
res = pd.DataFrame(res); res.to_csv(R/'cv_metrics.csv', index=False)
print(res[res.target=='annual'].pivot(index='method', columns='scheme', values='rmse').round(3))
# 2) 年平均・点の CV の予測を保存（標高帯別の誤差、区間の当たり方）
P = keep[('annual','point')].copy(); P['id'] = d['id']; P['obs'] = d['annual']; P['alt'] = d['alt']; P['lat']=d['lat']; P['lon']=d['lon']; P['area']=d['area']
P.to_csv(R/'cv_pred_annual_point.csv', index=False)
Pa = keep[('annual','area')].copy(); Pa['id']=d['id']; Pa['obs']=d['annual']; Pa['alt']=d['alt']; Pa.to_csv(R/'cv_pred_annual_area.csv', index=False)
bins = [-10, 50, 200, 500, 1000, 4000]; lab = ['50m未満','50〜200m','200〜500m','500〜1000m','1000m以上']
P['altbin'] = pd.cut(P['alt'], bins, labels=lab)
eb = []
for b, g in P.groupby('altbin', observed=True):
    r = dict(altbin=b, n=len(g))
    for m in METHODS: r[m] = float(np.sqrt(np.mean((g[m]-g['obs'])**2)))
    eb.append(r)
eb = pd.DataFrame(eb); eb.to_csv(R/'rmse_by_altitude.csv', index=False); print(eb.round(2))
cover = {}
for sch, PP in [('point', keep[('annual','point')]), ('area', keep[('annual','area')])]:
    for m in ['OK','RK']:
        z = (PP[m] - d['annual'])/PP[m+'_sd']
        cover[f'{sch}_{m}'] = dict(within95=float(np.mean(np.abs(z) <= 1.96)), within68=float(np.mean(np.abs(z) <= 1.0)), sd_median=float(PP[m+'_sd'].median()))
# 3) 標高の効き方（逓減率）
from sklearn.linear_model import LinearRegression
lr = {}
for t in TARGETS:
    m = LinearRegression().fit(d[['lat','lon']].assign(alt=d.alt/100).values, d[t].values)
    lr[t] = dict(lat=float(m.coef_[0]), lon=float(m.coef_[1]), per100m=float(m.coef_[2]), r2=float(m.score(d[['lat','lon']].assign(alt=d.alt/100).values, d[t].values)))
# 4) 経験バリオグラム（年平均の生の値と、回帰の残差）
from pykrige.ok import OrdinaryKriging
vg = {}
m_lin = LinearRegression().fit(d[['lat','lon']].assign(alt=d.alt/100).values, d['annual'].values)
resid = d['annual'].values - m_lin.predict(d[['lat','lon']].assign(alt=d.alt/100).values)
for nm, v in [('raw', d['annual'].values), ('resid', resid)]:
    for mdl in ['spherical','exponential','gaussian']:
        o = OrdinaryKriging(x, y, v, variogram_model=mdl, nlags=25, verbose=False)
        vg[f'{nm}_{mdl}'] = dict(params=[float(p) for p in o.variogram_model_parameters], lags=[float(a) for a in o.lags], semivar=[float(a) for a in o.semivariance])
json.dump(vg, open(R/'variogram.json','w'), ensure_ascii=False)
# 近い2点の差：最近傍の距離
tr = cKDTree(np.c_[x, y]); dd, _ = tr.query(np.c_[x, y], k=2)
summ = dict(n=len(d), nn_km_median=float(np.median(dd[:,1])), nn_km_p90=float(np.percentile(dd[:,1],90)), cover=cover, lapse=lr,
            alt_median=float(d.alt.median()), alt_ge500=int((d.alt>=500).sum()), resid_sd=float(resid.std()), raw_sd=float(d.annual.std()))
json.dump(summ, open(R/'summary.json','w'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1)[:2500])
# 5) 富士山頂（標高3,775m、ほかの地点より2,400m以上高い）を除いた RMSE（予測はそのまま、評価だけ除く）
rows = []
for sch, PP in [('point', keep[('annual','point')]), ('area', keep[('annual','area')]), ('block', keep[('annual','block')])]:
    k = d['alt'] < 3000
    for m in METHODS:
        e = PP[m] - d['annual']; rows.append(dict(scheme=sch, method=m, rmse_all=float(np.sqrt((e**2).mean())), rmse_no_fuji=float(np.sqrt((e[k]**2).mean())), err_fuji=float(e[~k].iloc[0])))
pd.DataFrame(rows).to_csv(R/'rmse_excluding_fuji.csv', index=False)
