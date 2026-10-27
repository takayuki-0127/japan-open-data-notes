# 頑健性：バリオグラムのモデル、IDW の設定、離島を除く、日最高・日最低、乱数の種、LightGBM から標高を外す
import numpy as np, pandas as pd, json, sys
from pathlib import Path
from sklearn.model_selection import KFold, GroupKFold
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *
B = Path(__file__).resolve().parents[1]; R = B/'results'
d = pd.read_csv(B/'data/normals_mean_temp.csv', dtype={'id':str}).reset_index(drop=True)
x, y = xy(d); d['block'] = (np.floor(x/100)).astype(int)*1000 + np.floor(y/100).astype(int)
def split(df, scheme, seed=0):
    if scheme == 'point': return list(KFold(10, shuffle=True, random_state=seed).split(df))
    return list(GroupKFold(10).split(df, groups=df['block']))
def rmse(a, b): return float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
out = []
def run(name, df, target, fn, scheme):
    p = np.full(len(df), np.nan)
    for tr, te in split(df, scheme): p[te] = fn(df.iloc[tr], df.iloc[te], target)
    out.append(dict(setting=name, scheme=scheme, target=target, rmse=rmse(p, df[target]))); print(out[-1], flush=True)
def okf(model): 
    def f(tr, te, t):
        xt, yt = xy(tr); xp, yp = xy(te); return ok(xt, yt, tr[t].values, xp, yp, model)[0]
    return f
def rkf(model): return lambda tr, te, t: rk(tr, te, t, model)[0]
def idwf(p, k):
    def f(tr, te, t):
        xt, yt = xy(tr); xp, yp = xy(te); return idw(xt, yt, tr[t].values, xp, yp, p, k)
    return f
for sch in ['point', 'block']:
    for mdl in ['spherical', 'exponential', 'gaussian']:
        run(f'OK_{mdl}', d, 'annual', okf(mdl), sch); run(f'RK_{mdl}', d, 'annual', rkf(mdl), sch)
    for p, k in [(1, 12), (2, 6), (3, 12), (2, 30)]: run(f'IDW_p{p}_k{k}', d, 'annual', idwf(p, k), sch)
    run('LightGBM_標高なし', d, 'annual', lambda tr, te, t: gbm_xy(tr, te, t), sch)
    # 最も近い観測点が50km以上離れている地点（離島など）を除く
    tr_ = cKDTree(np.c_[x, y]); dd, _ = tr_.query(np.c_[x, y], k=2); d2 = d[dd[:,1] < 50].reset_index(drop=True)
    for nm, fn in [('IDW', idwf(2, 12)), ('OK', okf('spherical')), ('RK', rkf('spherical')), ('LightGBM', lambda tr, te, t: gbm(tr, te, t))]:
        run(f'離島除く_{nm}', d2, 'annual', fn, sch)
# 日最高・日最低の平年値（年）
lg = pd.read_csv(B/'data/normals_temp_long.csv', dtype={'id':str})
for el in ['max', 'min']:
    e = lg[lg.elem==el][['id','annual']].rename(columns={'annual':'t_'+el})
    d3 = d.merge(e, on='id').dropna(subset=['t_'+el]).reset_index(drop=True)
    for sch in ['point', 'block']:
        for nm, fn in [('IDW', idwf(2, 12)), ('OK', okf('spherical')), ('RK', rkf('spherical')), ('LightGBM', lambda tr, te, t: gbm(tr, te, t))]:
            run(f'日{"最高" if el=="max" else "最低"}_{nm}', d3, 't_'+el, fn, sch)
# 乱数の種（点の分け方）
for s in [1, 2, 3]:
    for nm, fn in [('OK', okf('spherical')), ('RK', rkf('spherical')), ('LightGBM', lambda tr, te, t: gbm(tr, te, t, s))]:
        p = np.full(len(d), np.nan)
        for tr, te in split(d, 'point', s): p[te] = fn(d.iloc[tr], d.iloc[te], 'annual')
        out.append(dict(setting=f'種{s}_{nm}', scheme='point', target='annual', rmse=rmse(p, d.annual))); print(out[-1], flush=True)
pd.DataFrame(out).to_csv(R/'robustness.csv', index=False)
