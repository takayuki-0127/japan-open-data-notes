"""47都道府県の求人倍率の月次変化を「全国・地方・県」に分ける（階層型の動的因子モデル）"""
import json, warnings
import numpy as np, pandas as pd
from pathlib import Path
from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from sklearn.metrics import adjusted_rand_score, silhouette_score
warnings.filterwarnings('ignore')
np.random.seed(151)
B = Path(__file__).resolve().parents[1]; RS = B/'results'; RS.mkdir(exist_ok=True)
rd = lambda k: pd.read_csv(B/f'data/{k}_sa.csv', index_col=0)
o, s = rd('offers'), rd('seekers')
P = [c for c in o.columns if c != '全国']
R7 = [('北海道・東北', 0, 7), ('関東', 7, 14), ('中部', 14, 23), ('近畿', 23, 30), ('中国', 30, 35), ('四国', 35, 39), ('九州・沖縄', 39, 47)]
R10 = [('北海道・東北', 0, 7), ('北関東', 7, 10), ('南関東', 10, 14), ('北陸・甲信越', 14, 20), ('東海', 20, 24), ('近畿', 24, 30),
       ('中国', 30, 35), ('四国', 35, 39), ('北九州', 39, 43), ('南九州・沖縄', 43, 47)]
mk = lambda R: {P[i]: g for g, a, b in R for i in range(a, b)}
REG7, REG10 = mk(R7), mk(R10)
# 県庁所在地の緯度経度（おおよそ）
LL = [(43.06,141.35),(40.82,140.74),(39.70,141.15),(38.27,140.87),(39.72,140.10),(38.24,140.36),(37.75,140.47),(36.34,140.45),(36.57,139.88),(36.39,139.06),
      (35.86,139.65),(35.61,140.12),(35.69,139.69),(35.45,139.64),(37.90,139.02),(36.70,137.21),(36.59,136.63),(36.07,136.22),(35.66,138.57),(36.65,138.18),
      (35.39,136.72),(34.98,138.38),(35.18,136.91),(34.73,136.51),(35.00,135.87),(35.02,135.76),(34.69,135.52),(34.69,135.18),(34.69,135.83),(34.23,135.17),
      (35.50,134.24),(35.47,133.05),(34.66,133.93),(34.40,132.46),(34.19,131.47),(34.07,134.56),(34.34,134.04),(33.84,132.77),(33.56,133.53),(33.61,130.42),
      (33.25,130.30),(32.74,129.87),(32.79,130.74),(33.24,131.61),(31.91,131.42),(31.56,130.56),(26.21,127.68)]

def panel(kind='m1', start='1990-02', end='2026-09', src='own', drop_covid=False):
    if src == 'own': L = np.log(o[P] / s[P])
    elif src == 'pub': L = np.log(rd('ratio')[P])
    elif src == 'new': L = np.log(rd('new_ratio')[P])
    elif src == 'offers': L = np.log(o[P])
    elif src == 'w_offers': L = np.log(rd('w_offers')[P])
    lag = {'m1': 1, 'm3': 3, 'm12': 12}[kind]
    X = 100 * L.diff(lag)
    X.index = pd.PeriodIndex(X.index, freq='M'); X = X.loc[start:end]
    if drop_covid: X.loc['2020-03':'2022-03'] = np.nan
    return X

def n_factors(X):
    Z = ((X - X.mean()) / X.std()).dropna().values; T, N = Z.shape
    ev = np.linalg.eigvalsh(Z.T @ Z / T)[::-1]
    ic = [np.log((ev[k:].sum()) / N) + k * (N + T) / (N * T) * np.log(min(N, T)) for k in range(0, 9)]
    return {'share': (ev[:8] / ev.sum()).round(4).tolist(), 'ER': (ev[:7] / ev[1:8]).round(2).tolist(),
            'k_ER': int(np.argmax(ev[:7] / ev[1:8]) + 1), 'k_ICp2': int(np.argmin(ic))}

def hdfm(X, REG, order=1):
    fac = {p: ['全国', REG[p]] for p in P}
    m = DynamicFactorMQ(X, factors=fac, factor_orders=order, idiosyncratic_ar1=True, standardize=True)
    r = m.fit(maxiter=500, disp=False)
    F = r.factors.smoothed
    Z = (X - X.mean()) / X.std()
    rows = []
    for p in P:
        z = Z[p]; ok = z.notna()
        cn = r.params[f'loading.全国->{p}'] * F['全国']; cr = r.params[f'loading.{REG[p]}->{p}'] * F[REG[p]]
        v = z[ok].var()
        both = np.linalg.lstsq(np.c_[cn[ok], cr[ok], np.ones(ok.sum())], z[ok], rcond=None)[0]
        fit = np.c_[cn[ok], cr[ok], np.ones(ok.sum())] @ both
        r2 = 1 - ((z[ok] - fit) ** 2).sum() / ((z[ok] - z[ok].mean()) ** 2).sum()
        sn = np.corrcoef(cn[ok], z[ok])[0, 1] ** 2
        rows.append({'pref': p, 'region': REG[p], 'national': sn, 'regional': max(r2 - sn, 0), 'idio': 1 - r2,
                     'load_nat': r.params[f'loading.全国->{p}']})
    return pd.DataFrame(rows), F, r

def summ(D):
    return {'nat_med': round(D.national.median(), 3), 'reg_med': round(D.regional.median(), 3), 'idio_med': round(D.idio.median(), 3),
            'nat_mean': round(D.national.mean(), 3), 'reg_mean': round(D.regional.mean(), 3),
            'nat_min': round(D.national.min(), 3), 'nat_max': round(D.national.max(), 3)}

def resid_after_national(X):
    Z = ((X - X.mean()) / X.std()).dropna()
    u, sv, vt = np.linalg.svd(Z.values, full_matrices=False)
    f = u[:, 0] * sv[0]
    E = Z.values - np.outer(f, vt[0])
    return pd.DataFrame(E, index=Z.index, columns=Z.columns)

def cluster(E, REG, ks=range(2, 13), method='average'):
    C = np.corrcoef(E.values.T); Dm = 1 - C; np.fill_diagonal(Dm, 0)
    Lk = linkage(squareform(Dm, checks=False), method)
    lab_true = pd.Series(REG)[E.columns].astype('category').cat.codes.values
    out = []
    for k in ks:
        lab = fcluster(Lk, k, 'maxclust')
        sil = silhouette_score(Dm, lab, metric='precomputed') if len(set(lab)) > 1 else np.nan
        out.append({'k': k, 'silhouette': round(sil, 4), 'ARI_vs_7': round(adjusted_rand_score(lab_true, lab), 3), 'labels': lab.tolist()})
    # 同じ地方 / 違う地方の残差相関
    same = np.array([[REG[a] == REG[b] for b in E.columns] for a in E.columns]); iu = np.triu_indices(len(P), 1)
    return out, C, {'within': round(C[iu][same[iu]].mean(), 3), 'between': round(C[iu][~same[iu]].mean(), 3)}

def dist_km():
    la = np.radians([a for a, b in LL]); lo = np.radians([b for a, b in LL])
    d = np.sin((la[:, None] - la[None]) / 2) ** 2 + np.cos(la[:, None]) * np.cos(la[None]) * np.sin((lo[:, None] - lo[None]) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(d))

res = {}
X = panel()
res['n'] = {'T': X.shape[0], 'N': X.shape[1], 'start': str(X.index[0]), 'end': str(X.index[-1])}
res['nfac_m1'] = n_factors(X); res['nfac_m3'] = n_factors(panel('m3')); res['nfac_m12'] = n_factors(panel('m12'))
D, F, fitres = hdfm(X, REG7)
D.to_csv(RS/'decomp_main.csv', index=False); F.to_csv(RS/'factors_main.csv')
res['main'] = summ(D)
res['main_by_region'] = D.groupby('region')[['national', 'regional', 'idio']].median().round(3).to_dict('index')
# 残差の相関と分け方
E = resid_after_national(X)
cl, C, wb = cluster(E, REG7)
res['cluster'] = [{k: v for k, v in c.items() if k != 'labels'} for c in cl]; res['within_between'] = wb
best = max(cl, key=lambda c: c['silhouette']); res['cluster_best_k'] = best['k']
pd.DataFrame({'pref': P, 'region7': [REG7[p] for p in P], **{f'k{c["k"]}': c['labels'] for c in cl}}).to_csv(RS/'clusters.csv', index=False)
pd.DataFrame(C, index=P, columns=P).round(4).to_csv(RS/'resid_corr.csv')
Dk = dist_km(); iu = np.triu_indices(47, 1)
bins = [0, 100, 200, 300, 500, 800, 3000]
dd = pd.DataFrame({'km': Dk[iu], 'corr': C[iu]}); dd['bin'] = pd.cut(dd.km, bins)
res['corr_by_distance'] = {str(k): round(v, 3) for k, v in dd.groupby('bin', observed=True)['corr'].mean().items()}
dd.to_csv(RS/'corr_distance_pairs.csv', index=False)
# 最も残差相関が高い相手が同じ地方か
best_same = np.mean([REG7[P[i]] == REG7[P[np.argsort(C[i])[-2]]] for i in range(47)])
best_d = np.array([Dk[i, np.argsort(C[i])[-2]] for i in range(47)])
res['top_partner_same_region'] = round(best_same, 3); res['top_partner_km_median'] = round(float(np.median(best_d)), 0)
# 時期ごとの同調（10年の窓、1年ずつずらす）：第1主成分の割合
roll = []
Xa = panel(start='1980-02')
for y in range(1980, 2017):
    w = Xa.loc[f'{y}-02':f'{y+10}-01'].dropna()
    Z = (w - w.mean()) / w.std(); ev = np.linalg.eigvalsh(np.corrcoef(Z.values.T))[::-1]
    roll.append({'window': f'{y}-{y+9}', 'mid': y + 5, 'pc1_share': round(ev[0] / ev.sum(), 4), 'pc2_share': round(ev[1] / ev.sum(), 4)})
pd.DataFrame(roll).to_csv(RS/'rolling_pc1.csv', index=False); res['rolling'] = roll
# 全国の因子と鉱工業生産
iip = pd.read_csv(B/'data/raw/iip_mining_manufacturing.csv'); iip.index = pd.PeriodIndex(iip.ym.astype(str), freq='M')
g = np.log(iip.prod_sa.fillna(iip.prod_sa_c)).diff() * 100
fn = F['全国'] * np.sign(D.load_nat.mean())
nat = (100 * np.log(o['全国'] / s['全国']).diff()); nat.index = pd.PeriodIndex(nat.index, freq='M')
cc = {}
for lag in range(-6, 7):
    a = pd.concat([fn, g.shift(lag)], axis=1).dropna(); cc[lag] = round(a.corr().iloc[0, 1], 3)
res['factor_vs_iip_lag'] = cc  # lag>0: 鉱工業がlagか月前
a3 = pd.concat([fn.rolling(3).mean(), g.rolling(3).mean()], axis=1).dropna(); res['factor_vs_iip_3m'] = round(a3.corr().iloc[0, 1], 3)
a = pd.concat([fn, nat], axis=1).dropna(); res['factor_vs_national_ratio'] = round(a.corr().iloc[0, 1], 3)
pd.concat([fn.rename('national_factor'), g.rename('iip_dlog'), nat.rename('national_ratio_dlog')], axis=1).loc['1990-02':].to_csv(RS/'national_factor_iip.csv')
# 頑健性
rob = {}
def run(name, X, REG=REG7, order=1):
    Dx, _, _ = hdfm(X, REG, order); rob[name] = summ(Dx); print(name, rob[name], flush=True)
run('基本（月次の変化、7地方、AR1）', X)
run('因子のAR次数を2', X, order=2)
run('10地方に分ける', X, REG10)
run('3か月の変化', panel('m3'))
run('公表の求人倍率（0.01倍に丸め）', panel(src='pub'))
run('新規求人倍率', panel(src='new'))
run('有効求人数だけ（受理地、2005年3月〜）', panel(src='offers', start='2005-03'))
run('有効求人数だけ（就業地、2005年3月〜）', panel(src='w_offers', start='2005-03'))
run('1990〜2007年', panel(end='2007-12'))
run('2008〜2026年', panel(start='2008-01'))
run('コロナ期（2020年3月〜22年3月）を除く', panel(drop_covid=True))
res['robust'] = rob
# 分け方の頑健性：3か月の変化・ward法
cl3, _, wb3 = cluster(resid_after_national(panel('m3')), REG7); cw, _, _ = cluster(E, REG7, method='ward')
res['cluster_m3'] = [{k: v for k, v in c.items() if k != 'labels'} for c in cl3]; res['within_between_m3'] = wb3
res['cluster_ward'] = [{k: v for k, v in c.items() if k != 'labels'} for c in cw]
json.dump(res, open(RS/'summary.json', 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k not in ('rolling',)}, ensure_ascii=False, default=str)[:6000])
