# 使い方：python src/02_分析.py <この記事のフォルダ> <articles フォルダ>
import sys, json, numpy as np, pandas as pd
W = sys.argv[1]; A = sys.argv[2] if len(sys.argv) > 2 else '..'  # articles フォルダ（F03_land_price_ml を含む）
rng = np.random.default_rng(207)
out = {}
h = pd.read_csv(f'{W}/data/price_hist_1996_2026.csv.gz', dtype={'use': str, 'code': str})
c = pd.read_csv(f'{W}/data/chg_2007_2026.csv.gz', dtype=str)
fe = pd.read_csv(f'{A}/F03_land_price_ml/data/features.csv', dtype={'code': str})
st = pd.read_csv(f'{A}/F03_land_price_ml/data/stations.csv', dtype={'group': str})
h['pref'] = h.code.str[:2].astype(int)
TOK = {11, 12, 13, 14}; OSA = {26, 27, 28, 29}; NAG = {23, 24}
h['area'] = np.where(h.pref.isin(TOK), '東京圏', np.where(h.pref.isin(OSA), '大阪圏', np.where(h.pref.isin(NAG), '名古屋圏', '地方圏')))
h['kind'] = np.where(h.use == '000', '住宅地', np.where(h.use == '005', '商業地', 'その他'))

# ---------- A: 20-year change ----------
def cont(row_cols, start):
    cols = [f'c{y}' for y in range(start + 1, 2027)]
    return c[cols].apply(lambda s: s.str[0]).eq('1').all(axis=1)
c['cont2006'] = cont(None, 2006); c['cont2011'] = cont(None, 2011); c['cont2016'] = cont(None, 2016)
d = h.merge(c[['code', 'cont2006', 'cont2011', 'cont2016']], on='code')
def chg(s, start):
    m = d[f'cont{start}'] & (d[f'p{start}'] > 0)
    x = d[m].copy(); x['dl'] = np.log(x.p2026 / x[f'p{start}'])
    return x
A20 = chg(d, 2006)
out['A_n'] = int(len(A20)); out['A_share_up'] = float((A20.dl > 0).mean()); out['A_median_pct'] = float(np.expm1(A20.dl.median()) * 100)
out['A_by_area'] = A20.groupby('area').dl.agg(lambda s: [len(s), float((s > 0).mean()), float(np.expm1(s.median()) * 100)]).to_dict()
out['A_by_kind'] = A20[A20.kind != 'その他'].groupby('kind').dl.agg(lambda s: [len(s), float((s > 0).mean()), float(np.expm1(s.median()) * 100)]).to_dict()
out['A_by_area_kind'] = {f'{a}_{k}': [len(g), float((g.dl > 0).mean()), float(np.expm1(g.dl.median()) * 100)] for (a, k), g in A20[A20.kind != 'その他'].groupby(['area', 'kind'])}
# two decades
for s in (2011, 2016):
    x = chg(d, s); out[f'A_from{s}'] = [int(len(x)), float((x.dl > 0).mean()), float(np.expm1(x.dl.median()) * 100)]
x = A20.copy(); x['d1'] = np.log(x.p2016 / x.p2006); x['d2'] = np.log(x.p2026 / x.p2016)
out['A_decades'] = {'2006_16_up': float((x.d1 > 0).mean()), '2016_26_up': float((x.d2 > 0).mean()), 'corr_d1_d2': float(np.corrcoef(x.d1, x.d2)[0, 1]),
                    'both_up': float(((x.d1 > 0) & (x.d2 > 0)).mean()), 'down_then_up': float(((x.d1 <= 0) & (x.d2 > 0)).mean())}
A20.to_csv(f'{W}/results/A_change_2006_2026.csv.gz', index=False, columns=['code', 'lon', 'lat', 'pref', 'area', 'kind', 'p2006', 'p2016', 'p2026', 'dl'])
# features of rising points
F = A20.merge(fe[['code', 'dist_metro', 'dist_nearest_st', 'log_pass_1km', 'log_pass_nearest', 'log_muni_pop', 'muni_pop_change', 'far', 'land_use_class']], on='code')
F = F[F.kind != 'その他'].dropna()
F['log_dist_metro'] = np.log1p(F.dist_metro); F['log_dist_st'] = np.log1p(F.dist_nearest_st / 1000)
F['commercial'] = (F.kind == '商業地').astype(int)
import statsmodels.api as sm
Xc = ['log_dist_metro', 'log_dist_st', 'log_pass_1km', 'log_muni_pop', 'muni_pop_change', 'commercial']
Z = F[Xc].copy(); Z = (Z - Z.mean()) / Z.std()
mod = sm.OLS(F.dl.values, sm.add_constant(Z.values)).fit(cov_type='cluster', cov_kwds={'groups': F.code.str[:5].values})
out['A_reg'] = {k: [float(mod.params[i + 1]), float(mod.bse[i + 1])] for i, k in enumerate(Xc)}; out['A_reg_r2'] = float(mod.rsquared); out['A_reg_n'] = int(len(F))
# binned: distance to metro center x
F['dm_bin'] = pd.cut(F.dist_metro, [0, 10, 20, 40, 80, 2000], labels=['〜10km', '10〜20km', '20〜40km', '40〜80km', '80km〜'])
F['pc_bin'] = pd.cut(F.muni_pop_change, [-100, -5, -2, 0, 2, 100], labels=['−5%未満', '−5〜−2%', '−2〜0%', '0〜+2%', '+2%以上'])
out['A_bin_dm'] = F.groupby('dm_bin', observed=True).dl.agg(lambda s: [len(s), float((s > 0).mean()), float(np.expm1(s.median()) * 100)]).to_dict()
out['A_bin_pc'] = F.groupby('pc_bin', observed=True).dl.agg(lambda s: [len(s), float((s > 0).mean()), float(np.expm1(s.median()) * 100)]).to_dict()
F[['code', 'kind', 'area', 'dl', 'dist_metro', 'muni_pop_change', 'dm_bin', 'pc_bin']].to_csv(f'{W}/results/A_features.csv.gz', index=False)

# ---------- B: explain vs predict (2026 levels) ----------
import lightgbm as lgb
B = fe.copy(); B = B[B.price > 0]
B['y'] = np.log(B.price); B['log_dist_metro'] = np.log1p(B.dist_metro); B['log_dist_st'] = np.log1p(B.dist_nearest_st / 1000)
B['commercial'] = (B.land_use_class == '商業地').astype(int); B['far'] = B.far.fillna(B.far.median())
num = ['log_dist_st', 'log_dist_metro', 'log_pass_1km', 'log_pass_nearest', 'log_muni_pop', 'log_muni_density', 'muni_pop_change', 'far', 'coverage', 'log_acreage', 'road_width', 'commercial', 'lat', 'lon']
B = B.dropna(subset=num + ['y', 'block20']).reset_index(drop=True)
blocks = B.block20.unique(); rng.shuffle(blocks); fold_of = {b: i % 5 for i, b in enumerate(blocks)}; B['fold'] = B.block20.map(fold_of)
Brand = rng.integers(0, 5, len(B))
specs = {
    'OLS_基本': ['log_dist_st', 'log_dist_metro', 'log_pass_1km', 'far', 'log_acreage', 'road_width', 'commercial'],
    'OLS_市区町村の人口も': ['log_dist_st', 'log_dist_metro', 'log_pass_1km', 'far', 'log_acreage', 'road_width', 'commercial', 'log_muni_pop', 'log_muni_density', 'muni_pop_change'],
}
def ols_fit(tr, cols, fe_muni=False):
    X = tr[cols].values
    if fe_muni:
        dm = pd.get_dummies(tr.muni.astype(str), drop_first=True, dtype=float); X = np.column_stack([X, dm.values])
    return sm.OLS(tr.y.values, sm.add_constant(X, has_constant='add')).fit()
def cv_err(predict_fn, fold):
    P = np.full(len(B), np.nan)
    for k in range(5):
        tr = B[fold != k]; te = B[fold == k]; P[(fold == k)] = predict_fn(tr, te)
    e = np.abs(np.exp(P - B.y.values) - 1); return float(np.median(e)), float((e <= .2).mean()), P
res = {}
for nm, cols in specs.items():
    f = lambda tr, te, cols=cols: ols_fit(tr, cols).predict(sm.add_constant(te[cols].values, has_constant='add'))
    res[nm] = {'block': cv_err(f, B.fold.values)[:2], 'random': cv_err(f, Brand)[:2]}
prm = dict(objective='regression', learning_rate=0.1, num_leaves=63, n_estimators=300, max_bin=63, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, random_state=207, n_jobs=2)
def lgb_fn(tr, te):
    m = lgb.LGBMRegressor(**prm).fit(tr[num], tr.y); return m.predict(te[num])
res['LightGBM'] = {'block': cv_err(lgb_fn, B.fold.values)[:2], 'random': cv_err(lgb_fn, Brand)[:2]}
out['B_cv'] = res; out['B_n'] = int(len(B))
# station-distance "effect" across specs (in-sample, full data)
eff = {}
for nm, cols in specs.items():
    m = ols_fit(B, cols); i = cols.index('log_dist_st') + 1; eff[nm] = [float(m.params[i]), float(m.bse[i])]
# OLS with municipality fixed effects (within-municipality comparison)
cols = specs['OLS_基本']; m = ols_fit(B, cols, fe_muni=True); eff['OLS_市区町村の固定効果'] = [float(m.params[1]), float(m.bse[1])]
P_fe = None
# with lat/lon
cols2 = specs['OLS_市区町村の人口も'] + ['lat', 'lon']; m = ols_fit(B, cols2); eff['OLS_緯度経度も'] = [float(m.params[1]), float(m.bse[1])]
# LightGBM: average effect of moving log_dist_st by +1 (≈ distance 0→1.7km etc.) via finite difference over data
mfull = lgb.LGBMRegressor(**prm).fit(B[num], B.y)
X1 = B[num].copy(); X0 = B[num].copy(); X1['log_dist_st'] = X1.log_dist_st + 0.1
eff['LightGBM_平均の差分'] = [float(((mfull.predict(X1) - mfull.predict(X0)) / 0.1).mean()), None]
# PDP-like curve
grid = np.linspace(B.log_dist_st.quantile(.02), B.log_dist_st.quantile(.98), 25)
samp = B.sample(3000, random_state=207)
pdp = []
for g in grid:
    Xg = samp[num].copy(); Xg['log_dist_st'] = g; pdp.append(float(mfull.predict(Xg).mean()))
out['B_eff'] = eff; out['B_pdp'] = [list(map(float, grid)), pdp]
# per-region LightGBM effect (heterogeneity) by area
B['pref2'] = B.code.str[:2].astype(int)
B['area'] = np.where(B.pref2.isin(TOK), '東京圏', np.where(B.pref2.isin(OSA), '大阪圏', np.where(B.pref2.isin(NAG), '名古屋圏', '地方圏')))
dd = (mfull.predict(X1) - mfull.predict(X0)) / 0.1
out['B_eff_area'] = {a: float(dd[B.area.values == a].mean()) for a in ['東京圏', '大阪圏', '名古屋圏', '地方圏']}
out['B_eff_area_ols'] = {}
for a in ['東京圏', '大阪圏', '名古屋圏', '地方圏']:
    mm = ols_fit(B[B.area == a], specs['OLS_基本']); out['B_eff_area_ols'][a] = [float(mm.params[1]), float(mm.bse[1])]
# robustness: residential only
Rr = B[B.commercial == 0]
mm = ols_fit(Rr, specs['OLS_基本']); out['B_eff_resid_ols'] = [float(mm.params[1]), float(mm.bse[1])]
mr = lgb.LGBMRegressor(**prm).fit(Rr[num], Rr.y); X1r = Rr[num].copy(); X0r = Rr[num].copy(); X1r['log_dist_st'] += 0.1
out['B_eff_resid_lgb'] = float(((mr.predict(X1r) - mr.predict(X0r)) / 0.1).mean())

# ---------- C: new stations DiD ----------
ns = pd.read_csv(f'{W}/data/stations_new.csv')
rows = []
for _, r in ns.iterrows():
    m = st[(st.name == r['name']) & ((st.lat - r.lat_hint).abs() < 0.05)]
    if len(m) == 0: print('MISS', r['name']); continue
    rows.append(dict(name=r['name'], lon=float(m.lon.iloc[0]), lat=float(m.lat.iloc[0]), first_post=int(r.first_post), line=r.line))
NS = pd.DataFrame(rows); NS.to_csv(f'{W}/results/C_new_stations_matched.csv', index=False)
newset = set(NS.name)
other = st[~st.name.isin(newset)][['lon', 'lat']].values
def km(lon1, lat1, lon2, lat2):
    R = 6371.0; p1 = np.radians(lat1); p2 = np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))
P = d[['code', 'lon', 'lat', 'pref', 'kind'] + [f'p{y}' for y in range(1996, 2027)]].copy()
# distance to nearest other station (excluding new ones)
from scipy.spatial import cKDTree
lat0 = 36.0
def xy(lon, lat): return np.column_stack([np.radians(lon) * 6371 * np.cos(np.radians(lat0)), np.radians(lat) * 6371])
tree = cKDTree(xy(other[:, 0], other[:, 1]))
P['d_other'] = tree.query(xy(P.lon.values, P.lat.values))[0]
def build(r_in=1.0, r_ctl=(1.5, 4.0), need_far_other=1.0, win=5, exclude=None):
    recs = []
    for _, s in NS.iterrows():
        if exclude and s.line in exclude: continue
        dist = km(P.lon.values, P.lat.values, s.lon, s.lat)
        tr = (dist <= r_in) & (P.d_other.values > need_far_other)
        ct = (dist >= r_ctl[0]) & (dist <= r_ctl[1])
        for g, msk in ((1, tr), (0, ct)):
            sub = P[msk]
            for _, q in sub.iterrows():
                for k in range(-win, win + 1):
                    y = s.first_post + k
                    if y < 1996 or y > 2026: continue
                    v = q[f'p{y}']
                    if v and v > 0: recs.append((s['name'], q.code, g, k, y, np.log(v)))
    D = pd.DataFrame(recs, columns=['st', 'code', 'treat', 'k', 'year', 'lp'])
    # keep points observed at k=-1 and at least one post
    ok = D[D.k == -1].set_index(['st', 'code']).index
    D = D.set_index(['st', 'code']).loc[lambda x: x.index.isin(ok)].reset_index()
    base = D[D.k == -1][['st', 'code', 'lp']].rename(columns={'lp': 'lp0'})
    D = D.merge(base, on=['st', 'code']); D['dlp'] = D.lp - D.lp0
    return D
def es(D):
    g = D.groupby(['st', 'k', 'treat']).dlp.mean().unstack('treat')
    g = g.reindex(columns=[0, 1]).dropna(); g['diff'] = g[1] - g[0]
    return g.reset_index()
def did(D, post=(1, 5)):
    g = es(D); x = g[(g.k >= post[0]) & (g.k <= post[1])].groupby('st')['diff'].mean()
    pre = g[(g.k >= -5) & (g.k <= -2)].groupby('st')['diff'].mean()
    sts = x.index.values; vals = x.values
    bs = [rng.choice(vals, len(vals)).mean() for _ in range(2000)]
    pb = [rng.choice(pre.values, len(pre)).mean() for _ in range(2000)] if len(pre) else [np.nan]
    return dict(n_st=int(len(sts)), est=float(vals.mean()), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                pre=float(pre.mean()) if len(pre) else None, pre_lo=float(np.nanpercentile(pb, 2.5)), pre_hi=float(np.nanpercentile(pb, 97.5)))
D0 = build(); D0.to_csv(f'{W}/results/C_panel_main.csv.gz', index=False)
E = es(D0); evt = E.groupby('k')['diff'].agg(['mean', 'count']).reset_index()
bsk = {}
for k, gk in E.groupby('k'):
    v = gk['diff'].values; b = [rng.choice(v, len(v)).mean() for _ in range(1000)]; bsk[int(k)] = [float(v.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), int(len(v))]
out['C_event'] = bsk
out['C_main'] = did(D0)
out['C_n_points'] = {'treat': int(D0[D0.treat == 1][['st', 'code']].drop_duplicates().shape[0]), 'ctrl': int(D0[D0.treat == 0][['st', 'code']].drop_duplicates().shape[0])}
rob = {}
rob['半径0.5km'] = did(build(r_in=0.5, need_far_other=0.5))
rob['他の駅の条件なし'] = did(build(need_far_other=0.0))
rob['比較を1〜2km'] = did(build(r_ctl=(1.0, 2.0)))
rob['比較を2〜5km'] = did(build(r_ctl=(2.0, 5.0)))
rob['TXを除く'] = did(build(exclude={'つくばエクスプレス'}))
rob['新幹線を除く'] = did(build(exclude={'九州新幹線', '北陸新幹線', '西九州新幹線'}))
# placebo: shift opening 5 years earlier
NS_orig = NS.copy(); NS['first_post'] = NS.first_post - 5; rob['開業を5年前にずらす（偽の開業）'] = did(build()); NS = NS_orig
# per line
D0['line'] = D0.st.map(dict(zip(NS.name, NS.line)))
lines = {}
for ln, g in D0.groupby('line'):
    e = es(g); x = e[(e.k >= 1) & (e.k <= 5)].groupby('st')['diff'].mean()
    if len(x): lines[ln] = [int(len(x)), float(x.mean()), int(g[g.treat == 1][['st', 'code']].drop_duplicates().shape[0])]
out['C_rob'] = rob; out['C_lines'] = lines
# anticipation: k=-3..-1 vs -5 ... computed from event dict
json.dump(out, open(f'{W}/results/main.json', 'w'), ensure_ascii=False, indent=1, default=str)
print('ok')
