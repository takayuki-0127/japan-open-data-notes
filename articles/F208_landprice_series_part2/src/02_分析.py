# 使い方：python src/02_分析.py <この記事のフォルダ> <articles フォルダ>
# A：マンションの価格（F182 の取引データ）と地価（F207 の地価公示の履歴）の市区町村×年の動き
# B：地価の予測を毎年更新したとき、どこで外れやすいか（F158 のパネル、F03 の特徴量）
import sys, json, numpy as np, pandas as pd
W = sys.argv[1]; A = sys.argv[2] if len(sys.argv) > 2 else '..'
SEED = 208; rng = np.random.default_rng(SEED)
out = {}
TOK = {11, 12, 13, 14}; OSA = {26, 27, 28, 29}; NAG = {23, 24}
def area_of(pref):
    pref = np.asarray(pref).astype(int)
    return np.where(np.isin(pref, list(TOK)), '東京圏', np.where(np.isin(pref, list(OSA)), '大阪圏', np.where(np.isin(pref, list(NAG)), '名古屋圏', '地方圏')))

# ================= A: condo vs land =================
c = pd.read_csv(f'{A}/F182_condo_depreciation_curve/data/condo_clean.csv.gz', dtype={'muni': str})
c = c[c.struct.isin(['RC', 'SRC'])].copy()
c['lp'] = np.log(c.ppm2)
c['ageb'] = pd.cut(c.age, [-1, 9, 19, 29, 60], labels=['築0〜9年', '築10〜19年', '築20〜29年', '築30年以上']).astype(str)
c['g'] = c.muni + '_' + c.year.astype(str)
# hedonic: log ppm2 on age dummies(1yr), log area, walk, SRC, renov, with muni×year FE (within transform)
X = pd.get_dummies(c.age.clip(0, 50).astype(int), prefix='a', drop_first=True, dtype=float)
X['larea'] = np.log(c.area); X['walk'] = c.walk; X['src'] = (c.struct == 'SRC').astype(float); X['renov'] = c.renov.astype(float)
Xd = X - X.groupby(c.g.values).transform('mean'); yd = c.lp - c.groupby('g').lp.transform('mean')
beta, *_ = np.linalg.lstsq(Xd.values, yd.values, rcond=None)
c['adj'] = c.lp - X.values @ beta  # quality-adjusted log price

def condo_index(df, minn):
    g = df.groupby(['muni', 'year']).agg(ci=('adj', 'mean'), n=('adj', 'size')).reset_index()
    return g[g.n >= minn]

h = pd.read_csv(f'{A}/F207_landprice_series_part1/data/price_hist_1996_2026.csv.gz', dtype={'use': str, 'code': str})
ch = pd.read_csv(f'{A}/F207_landprice_series_part1/data/chg_2007_2026.csv.gz', dtype=str)
h = h.merge(ch, on='code'); h['muni'] = h.code.str[:5]
def land_changes(use):
    rows = []
    hh = h[h.use.isin(use)]
    for y in range(2015, 2027):
        ok = (hh[f'p{y}'] > 0) & (hh[f'p{y-1}'] > 0) & hh[f'c{y}'].str[0].eq('1')
        x = hh[ok]
        rows.append(pd.DataFrame({'muni': x.muni, 'year': y, 'dl': np.log(x[f'p{y}'] / x[f'p{y-1}'])}))
    r = pd.concat(rows)
    return r.groupby(['muni', 'year']).agg(dland=('dl', 'mean'), nl=('dl', 'size')).reset_index()

def panel(use=('000',), minn=20, df=None, lag=1, area=None):
    ci = condo_index(c if df is None else df, minn).sort_values(['muni', 'year'])
    ci['dcondo'] = ci.groupby('muni').ci.diff(); ci['yprev'] = ci.groupby('muni').year.shift()
    ci = ci[ci.year - ci.yprev == 1]
    L = land_changes(list(use))
    # 地価公示は1月1日時点。lag=1：y 年の取引と y+1 年1月の公示（y 年中の動き）を合わせる
    L = L.assign(year=L.year - lag)
    m = ci.merge(L, on=['muni', 'year'])
    m['pref'] = m.muni.str[:2].astype(int); m['area'] = area_of(m.pref)
    if area: m = m[m.area == area]
    return m

def fe_slope(m, y='dcondo', x='dland'):
    """年の固定効果つき、取引数で重みづけした回帰の傾きと、市区町村クラスターのブートストラップ区間"""
    def est(d):
        dy = d[y] - d.groupby('year')[y].transform('mean'); dx = d[x] - d.groupby('year')[x].transform('mean')
        w = d.n
        return float((w * dx * dy).sum() / (w * dx * dx).sum())
    b = est(m)
    mun = m.muni.unique(); g = {k: v for k, v in m.groupby('muni')}
    bs = []
    for _ in range(300):
        s = rng.choice(mun, len(mun))
        bs.append(est(pd.concat([g[k] for k in s])))
    return [b, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), int(len(m)), int(m.muni.nunique())]

def pooled_slope(m):
    """年の固定効果なし（全国の動きも含む）"""
    w = m.n; dx = m.dland - np.average(m.dland, weights=w); dy = m.dcondo - np.average(m.dcondo, weights=w)
    return float((w * dx * dy).sum() / (w * dx * dx).sum())

M = panel()
out['A_hedonic_beta'] = {k: float(v) for k, v in zip(X.columns, beta) if not k.startswith('a_')}
out['A_n_condo'] = int(len(c))
out['A_panel'] = [int(len(M)), int(M.muni.nunique())]
out['A_slope_main'] = fe_slope(M)
out['A_slope_pooled'] = pooled_slope(M)
out['A_corr_main'] = float(np.corrcoef(M.dcondo, M.dland)[0, 1])
# lag comparison
out['A_slope_by_lag'] = {}
for lag in [0, 1, 2]:
    out['A_slope_by_lag'][str(lag)] = fe_slope(panel(lag=lag))
# by age band
out['A_slope_by_age'] = {}
for ab in ['築0〜9年', '築10〜19年', '築20〜29年', '築30年以上']:
    out['A_slope_by_age'][ab] = fe_slope(panel(df=c[c.ageb == ab], minn=10))
# robustness
out['A_rob'] = {
    '主（住宅地・20件以上・公示は翌年1月）': out['A_slope_main'],
    '商業地の地価': fe_slope(panel(use=('005',))),
    '住宅地＋商業地': fe_slope(panel(use=('000', '005'))),
    '取引50件以上の市区町村×年': fe_slope(panel(minn=50)),
    '東京圏だけ': fe_slope(panel(area='東京圏')),
    '東京圏以外': fe_slope(M[M.area != '東京圏']),
    '2020年以降だけ': fe_slope(M[M.year >= 2020]),
}
# national chained index: weighted mean of muni changes each year (balanced pairs)
nat = M.groupby('year')[['dcondo','dland','n']].apply(lambda d: pd.Series({'condo': np.average(d.dcondo, weights=d.n), 'land': np.average(d.dland, weights=d.n)})).reset_index()
nat['condo_idx'] = 100 * np.exp(nat.condo.cumsum()); nat['land_idx'] = 100 * np.exp(nat.land.cumsum())
nat.to_csv(f'{W}/results/A_national_index.csv', index=False)
out['A_nat_2025'] = [float(nat.condo_idx.iloc[-1]), float(nat.land_idx.iloc[-1]), int(nat.year.iloc[0] - 1), int(nat.year.iloc[-1])]
# by age band national
natb = {}
for ab in ['築0〜9年', '築10〜19年', '築20〜29年', '築30年以上']:
    mb = panel(df=c[c.ageb == ab], minn=10)
    nb = mb.groupby('year')[['dcondo','n']].apply(lambda d: np.average(d.dcondo, weights=d.n))
    natb[ab] = (100 * np.exp(nb.cumsum())).round(2).to_dict()
out['A_nat_by_age'] = natb
# cumulative muni-level change 2016->2024 (condo years) for scatter
ci = condo_index(c, 20)
w = ci.pivot(index='muni', columns='year', values='ci')
cum = (w[2024] - w[2016]).dropna().rename('dcondo').to_frame()
hh = h[h.use == '000'].copy()
ok = (hh.p2017 > 0) & (hh.p2025 > 0) & hh[[f'c{y}' for y in range(2018, 2026)]].apply(lambda s: s.str[0]).eq('1').all(axis=1)
lc = hh[ok].assign(dl=lambda d: np.log(d.p2025 / d.p2017)).groupby('muni').dl.agg(['mean', 'size'])
cum = cum.join(lc.rename(columns={'mean': 'dland', 'size': 'nl'}), how='inner')
cum = cum[cum.nl >= 3]
cum['n'] = ci[ci.year.between(2016, 2024)].groupby('muni').n.sum().reindex(cum.index)
cum['area'] = area_of(cum.index.str[:2])
cum.reset_index().to_csv(f'{W}/results/A_muni_cumulative.csv', index=False)
X1 = np.c_[np.ones(len(cum)), cum.dland]; b1 = np.linalg.lstsq(X1 * np.sqrt(cum.n.values)[:, None], cum.dcondo * np.sqrt(cum.n.values), rcond=None)[0]
out['A_cum'] = {'n_muni': int(len(cum)), 'slope': float(b1[1]), 'intercept': float(b1[0]), 'corr': float(np.corrcoef(cum.dcondo, cum.dland)[0, 1]),
                'share_condo_gt_land': float((cum.dcondo > cum.dland).mean()),
                'median_condo_pct': float(np.expm1(cum.dcondo.median()) * 100), 'median_land_pct': float(np.expm1(cum.dland.median()) * 100)}
M.to_csv(f'{W}/results/A_panel_muni_year.csv.gz', index=False)

# ================= B: yearly-updated forecast misses =================
import lightgbm as lgb
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import Ridge
fe = pd.read_csv(f'{A}/F03_land_price_ml/data/features.csv', dtype={'code': str, 'muni': str})
P = pd.read_csv(f'{A}/F158_land_price_update/data/panel.csv', dtype={'code': str})
NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage", "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
       "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km", "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
FEAT = NUM + CAT
pts = fe.set_index('code')
for k in CAT: pts[k] = pts[k].astype('category')
PARAMS = dict(objective="regression", learning_rate=0.1, num_leaves=63, min_child_samples=20, max_bin=63, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.8, reg_lambda=1.0, n_estimators=300, random_state=SEED, verbose=-1, n_jobs=2)
def make_folds(kind):
    r2 = np.random.default_rng(SEED)  # 分け方は毎回同じ
    if kind == 'random':
        return pd.Series(r2.permutation(len(pts)) % 5, index=pts.index)
    u = pts.block20.unique(); perm = dict(zip(u, r2.permutation(len(u))))
    f = np.zeros(len(pts), int)
    for i, (_, te) in enumerate(GroupKFold(5).split(pts, groups=pts.block20.map(perm))): f[te] = i
    return pd.Series(f, index=pts.index)
P = P[P.code.isin(pts.index)].copy(); P['y'] = np.log(P.price)
wide = P.pivot(index='code', columns='year', values='y')

def ridge_fit_predict(Xtr, ytr, Xte):
    med = Xtr[NUM].median()
    def z(Xa, fit=None):
        A_ = Xa[NUM].fillna(med).copy(); A_['dist_station'] = np.log(A_['dist_station'] + 50)
        D = pd.get_dummies(Xa[CAT].astype(str), dtype=float)
        return A_, D
    Atr, Dtr = z(Xtr); mu, sd = Atr.mean(), Atr.std().replace(0, 1)
    Ate, Dte = z(Xte); Dte = Dte.reindex(columns=Dtr.columns, fill_value=0.0)
    Ztr = np.hstack([((Atr - mu) / sd).values, Dtr.values]); Zte = np.hstack([((Ate - mu) / sd).values, Dte.values])
    return Ridge(alpha=1.0).fit(Ztr, ytr).predict(Zte)

def run_yearly(fold_kind='block20', model='lgbm', years=range(2018, 2027)):
    fo = make_folds(fold_kind); rows = []
    for T in years:
        cur = wide[T].dropna(); prev = wide[T - 1].dropna()
        for k in range(5):
            tr = prev.index[fo.reindex(prev.index).values != k]
            te = cur.index[fo.reindex(cur.index).values == k]
            Xtr, Xte = pts.loc[tr, FEAT], pts.loc[te, FEAT]
            if model == 'lgbm':
                p = lgb.LGBMRegressor(**PARAMS).fit(Xtr, prev.loc[tr]).predict(Xte)
            else:
                p = ridge_fit_predict(Xtr, prev.loc[tr].values, Xte)
            # 学習側の地点で測った T-1→T の全国の変化（中央値）は使わない：毎年更新は「T-1 年の公示で学習して T を当てる」
            rows.append(pd.DataFrame({'code': te, 'year': T, 'pred': p, 'y': cur.loc[te].values}))
    r = pd.concat(rows); r['e'] = r.pred - r.y  # log の外れ（＋は予測が高い）
    return r

import os
if os.path.exists(f'{W}/results/B_oof_yearly.csv.gz'):
    R = pd.read_csv(f'{W}/results/B_oof_yearly.csv.gz', dtype={'code': str})  # 2回目以降は保存した予測を使う（同じ種で作ったもの）
else:
    R = run_yearly(); R.to_csv(f'{W}/results/B_oof_yearly.csv.gz', index=False)
def stats(e):
    a = np.abs(np.expm1(e))
    return {'n': int(len(e)), 'mape_med': float(np.median(a) * 100), 'within20': float((a <= .2).mean()), 'bias_med': float(np.expm1(np.median(e)) * 100)}
out['B_overall'] = stats(R.e)
out['B_by_year'] = {int(y): stats(g.e) for y, g in R.groupby('year')}
# point-level average signed miss over years
pt = R.groupby('code').agg(e_mean=('e', 'mean'), e_abs=('e', lambda s: np.abs(np.expm1(s)).mean()), ny=('e', 'size')).join(pts[['lon', 'lat', 'muni', 'land_use_class', 'dist_metro', 'muni_pop_change', 'log_pass_1km']])
pt['pref'] = pt.index.str[:2].astype(int); pt['area'] = area_of(pt.pref)
A20 = pd.read_csv(f'{A}/F207_landprice_series_part1/results/A_change_2006_2026.csv.gz', dtype={'code': str}).set_index('code')
pt = pt.join(A20[['dl']].rename(columns={'dl': 'dl20'}))
# price level (2017) and own change 2017->2026
pt = pt.join((wide[2026] - wide[2017]).rename('d10')).join(wide[2017].rename('y2017'))
pt.reset_index().to_csv(f'{W}/results/B_point_miss.csv.gz', index=False)
# persistence: corr of e_T and e_{T-1} for same point
ew = R.pivot(index='code', columns='year', values='e')
pers = [float(ew[[y - 1, y]].dropna().corr().iloc[0, 1]) for y in range(2019, 2027)]
out['B_persistence_by_year'] = dict(zip(range(2019, 2027), pers))
out['B_persistence_mean'] = float(np.mean(pers))
# share of variance of errors that is a stable point component (between-point var of mean / total var), balanced points
bal = ew.dropna()
out['B_stable_share'] = float(bal.mean(axis=1).var() / bal.stack().var())
out['B_n_balanced'] = int(len(bal))
# where misses: by groups (signed bias & abs), using point means
def grp(col, bins=None, labels=None):
    s = pt[col] if bins is None else pd.cut(pt[col], bins, labels=labels)
    g = pt.groupby(s, observed=True)
    return {str(k): [int(len(v)), float(np.expm1(v.e_mean.median()) * 100), float(v.e_abs.median() * 100)] for k, v in g}
out['B_by_area'] = grp('area')
out['B_by_use'] = grp('land_use_class')
pt['price_dec'] = pd.qcut(pt.y2017, 10, labels=[f'{i}' for i in range(1, 11)])
out['B_by_price_decile'] = grp('price_dec')
pt['d10_dec'] = pd.qcut(pt.d10, 10, labels=[f'{i}' for i in range(1, 11)])
out['B_by_own_change_decile'] = grp('d10_dec')
out['B_by_popchg'] = grp('muni_pop_change', [-100, -5, -2, 0, 2, 100], ['−5%未満', '−5〜−2%', '−2〜0%', '0〜+2%', '+2%以上'])
# correlation of point-mean signed error with own 10-year change
okp = pt.dropna(subset=['d10'])
out['B_corr_emean_d10'] = float(np.corrcoef(okp.e_mean, okp.d10)[0, 1])
# regression to the mean in price: slope of e_mean on standardized y2017
q = pt.dropna(subset=['y2017']); z = (q.y2017 - q.y2017.mean()) / q.y2017.std(); out['B_slope_e_on_price_sd'] = float(np.polyfit(z, q.e_mean, 1)[0])
# year-specific: are misses explained by own last-year change (momentum)? for points with history
mom = []
for T in range(2019, 2027):
    r = R[R.year == T].set_index('code')
    d1 = (wide[T - 1] - wide[T - 2]).reindex(r.index); d0 = (wide[T] - wide[T - 1]).reindex(r.index)
    ok = d1.notna() & d0.notna()
    mom.append([T, float(np.corrcoef(r.e[ok], d0[ok])[0, 1]), float(np.corrcoef(r.e[ok], d1[ok])[0, 1])])
out['B_corr_e_with_change'] = mom  # [year, corr(e, change T-1→T), corr(e, change T-2→T-1)]
# simple fix: carry over the national median change of training points T-1→T (unknown at forecast time) vs prior year's median change (known)
fix = []
fo = make_folds('block20')
for T in range(2019, 2027):
    r = R[R.year == T].copy(); r['fold'] = fo.reindex(r.code).values
    for k in range(5):
        trc = fo.index[fo.values != k]
        w2 = wide.reindex(trc)
        known = float(np.nanmedian(w2[T - 1] - w2[T - 2]))
        r.loc[r.fold == k, 'pred_known'] = r.loc[r.fold == k, 'pred'] + known
    fix.append(r)
F = pd.concat(fix)
out['B_fix_trend'] = {'before': stats(F.e), 'after_add_last_year_trend': stats(F.pred_known - F.y)}
# robustness: random folds, ridge, residential only, years halves
Rr = run_yearly('random'); Rg = run_yearly(model='ridge')
out['B_rob'] = {
    '主（LightGBM・20km四方で分割）': stats(R.e),
    '地点でランダムに分割': stats(Rr.e),
    'リッジ回帰': stats(Rg.e),
    '住宅地だけ（主の結果から）': stats(R[R.code.map(pts.land_use_class.astype(str)) == '住宅地'].e),
    '2018〜2021年': stats(R[R.year <= 2021].e), '2022〜2026年': stats(R[R.year >= 2022].e),
}
for nm, rr in [('random', Rr), ('ridge', Rg)]:
    ew2 = rr.pivot(index='code', columns='year', values='e')
    out[f'B_persistence_{nm}'] = float(np.mean([ew2[[y - 1, y]].dropna().corr().iloc[0, 1] for y in range(2019, 2027)]))
    p2 = rr.groupby('code').e.mean()
    out[f'B_area_bias_{nm}'] = {a: float(np.expm1(p2.reindex(pt.index[pt.area == a]).median()) * 100) for a in ['東京圏', '大阪圏', '名古屋圏', '地方圏']}
json.dump(out, open(f'{W}/results/main.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:6000])
