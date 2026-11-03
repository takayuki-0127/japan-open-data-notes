"""03 分析: 普及曲線（Bass・ロジスティック・ゴンペルツ）の当てはめと地域差。乱数は使わない（ブートストラップは seed=134）。"""
import numpy as np, pandas as pd, json, warnings
from scipy.optimize import curve_fit
from scipy import stats
warnings.filterwarnings('ignore')
rng = np.random.default_rng(134)
df = pd.read_csv('data/fit_pref_long.csv')
df = df[df.pref != '合計']
PREFS = list(dict.fromkeys(df[df.date == '2026-03'].pref))
assert len(PREFS) == 47, len(PREFS)
def tyear(d): y, m = map(int, d.split('-')); return y + m / 12 - 2012.5   # 2012年7月1日（制度開始）=0
df['t'] = df.date.map(tyear)
REGION = {}
for p in PREFS[:1]: REGION[p] = '北海道'
for p in PREFS[1:7]: REGION[p] = '東北'
for p in PREFS[7:14]: REGION[p] = '関東'
for p in PREFS[14:23]: REGION[p] = '中部'
for p in PREFS[23:30]: REGION[p] = '近畿'
for p in PREFS[30:35]: REGION[p] = '中国'
for p in PREFS[35:39]: REGION[p] = '四国'
for p in PREFS[39:47]: REGION[p] = '九州・沖縄'

# 共変量
e = pd.read_csv('/mnt/user-data/uploads/Downloads/SSDSE-E-2026.csv', encoding='cp932', header=None, skiprows=3)
e = e[[1, 2, 13, 19, 23, 70, 73]]; e.columns = ['pref', 'pop', 'hh', 'habitable_km2', 'inc_pc', 'houses', 'detached']
e = e[e.pref.isin(PREFS)].set_index('pref').astype(float)
e['habitable_km2'] = e['habitable_km2'] / 100  # SSDSE は ha
sun = pd.read_csv('/mnt/user-data/outputs/mono/articles/198_sunshine_rank/data/sunshine_annual.csv')
sun = sun[(sun.year >= 2012) & (sun.year <= 2024) & (sun.flag.isna())].groupby('pref').sunshine_h.mean()
FULL = {(p[:-1] if p != '北海道' else p): p for p in PREFS}
sun.index = [FULL[x] for x in sun.index]
cov = e.join(sun.rename('sunshine_h'))
cov['detached_share'] = cov.detached / cov.houses
cov['region'] = [REGION[p] for p in cov.index]
cov.to_csv('data/covariates.csv')

def bass(t, m, p, q):
    E = np.exp(-(p + q) * t); return m * (1 - E) / (1 + (q / p) * E)
def logistic(t, K, r, t0): return K / (1 + np.exp(-r * (t - t0)))
def gompertz(t, K, b, c): return K * np.exp(-b * np.exp(-c * t))
MODELS = {'Bass': bass, 'ロジスティック': logistic, 'ゴンペルツ': gompertz}

def fit(name, t, y, kmax):
    ymax = y.max()
    try:
        if name == 'Bass':
            p0 = [ymax * 1.5, 0.01, 0.3]; bd = ([ymax, 1e-5, 1e-4], [kmax, 1.0, 3.0])
        elif name == 'ロジスティック':
            p0 = [ymax * 1.5, 0.4, 5]; bd = ([ymax, 1e-3, -10], [kmax, 5.0, 60])
        else:
            p0 = [ymax * 1.5, 3, 0.2]; bd = ([ymax, 1e-3, 1e-3], [kmax, 100, 5])
        par, _ = curve_fit(MODELS[name], t, y, p0=p0, bounds=bd, maxfev=40000)
        pred = MODELS[name](t, *par); sse = ((y - pred) ** 2).sum(); n = len(y)
        return dict(par=par, sse=sse, aic=n * np.log(sse / n + 1e-12) + 6, K=par[0], K_at_bound=bool(par[0] > 0.98 * kmax))
    except Exception as ex:
        return None

def tq(model, par, q):
    """フィットした曲線が K の q 倍に届く時点（年, 2012.5基準）"""
    tt = np.linspace(0, 80, 80001); v = MODELS[model](tt, *par) / par[0]
    i = np.searchsorted(v, q); return tt[i] if i < len(tt) else np.nan

SERIES = {'res_cnt_new': '住宅用太陽光（10kW未満）の件数', 'big_kw_new': '事業用太陽光（10kW以上）の容量', 'wind_kw_new': '風力の容量'}
def panel(series, prefs=None, start=None, anchor=True, end=None):
    d = df[df.series == series]
    if start: d = d[d.t >= start]
    if end: d = d[d.t <= end]
    return d

rows = []
for s in SERIES:
    for p in PREFS + ['全国']:
        d = df[(df.series == s)] if p == '全国' else df[(df.series == s) & (df.pref == p)]
        if p == '全国': d = d.groupby('t', as_index=False).value.sum()
        d = d.sort_values('t'); t = np.r_[0.0, d.t.values]; y = np.r_[0.0, d.value.values]
        if y.max() <= 0: continue
        for mname in MODELS:
            r = fit(mname, t, y, kmax=y.max() * 20)
            if not r: rows.append(dict(series=s, pref=p, model=mname, ok=False)); continue
            K = r['K']; rows.append(dict(series=s, pref=p, model=mname, ok=True, K=K, K_ratio=K / y.max(), K_at_bound=r['K_at_bound'],
                     aic=r['aic'], rmse_pct=np.sqrt(r['sse'] / len(y)) / y.max() * 100,
                     t10=tq(mname, r['par'], .1) + 2012.5, t50=tq(mname, r['par'], .5) + 2012.5, t90=tq(mname, r['par'], .9) + 2012.5,
                     p1=r['par'][1], p2=r['par'][2], last=y.max()))
fits = pd.DataFrame(rows); fits.to_csv('results/fits_all.csv', index=False)

# 観測ベースの速さ（モデルに頼らない）：2026年3月の水準の半分に届いた時点（線形補間, 起点0）
def obs_t(series, frac=0.5, prefs=PREFS):
    out = {}
    for p in prefs:
        d = df[(df.series == series) & (df.pref == p)].sort_values('t')
        t = np.r_[0.0, d.t.values]; y = np.r_[0.0, d.value.values]; tgt = y[-1] * frac
        out[p] = np.interp(tgt, np.maximum.accumulate(y), t) + 2012.5
    return pd.Series(out)

res = {}
nat = fits[fits.pref == '全国'][['series', 'model', 'K_ratio', 'K_at_bound', 'aic', 'rmse_pct', 't10', 't50', 't90']]
res['national_fits'] = nat.round(3).to_dict('records')

# 都道府県のフィット要約（Bass を主に）
summ = {}
for s in SERIES:
    f = fits[(fits.series == s) & (fits.pref.isin(PREFS)) & fits.ok]
    by = {}
    for m in MODELS:
        g = f[f.model == m]
        by[m] = dict(n=len(g), K_at_bound=int(g.K_at_bound.sum()), median_rmse_pct=round(g.rmse_pct.median(), 2),
                     t50_median=round(g.t50.median(), 2), t50_iqr=[round(g.t50.quantile(.25), 2), round(g.t50.quantile(.75), 2)],
                     dur10_90_median=round((g.t90 - g.t10).median(), 2), K_ratio_median=round(g.K_ratio.median(), 2))
    best = f.loc[f.groupby('pref').aic.idxmin()].model.value_counts().to_dict()
    by['AIC最小のモデル'] = best
    summ[s] = by
res['pref_fit_summary'] = summ

# 予測の検証：2023年3月までで当てはめ、2023年6月〜2026年3月（12四半期）を予測
val = []
for s in SERIES:
    for p in PREFS:
        d = df[(df.series == s) & (df.pref == p)].sort_values('t')
        tr = d[d.date <= '2023-03']; te = d[d.date > '2023-03']
        t = np.r_[0.0, tr.t.values]; y = np.r_[0.0, tr.value.values]
        if y.max() <= 0 or te.value.iloc[-1] <= 0: continue
        for m in MODELS:
            r = fit(m, t, y, kmax=y.max() * 20)
            if not r: continue
            pr = MODELS[m](te.t.values, *r['par'])
            val.append(dict(series=s, pref=p, model=m, ape_last=abs(pr[-1] - te.value.iloc[-1]) / te.value.iloc[-1] * 100,
                            under=bool(pr[-1] < te.value.iloc[-1])))
        # 素朴な比較：直近2年の平均の伸びをそのまま延ばす
        last8 = tr.tail(9); slope = (last8.value.iloc[-1] - last8.value.iloc[0]) / (last8.t.iloc[-1] - last8.t.iloc[0])
        pr = tr.value.iloc[-1] + slope * (te.t.iloc[-1] - tr.t.iloc[-1])
        val.append(dict(series=s, pref=p, model='直線（直近2年の伸び）', ape_last=abs(pr - te.value.iloc[-1]) / te.value.iloc[-1] * 100, under=bool(pr < te.value.iloc[-1])))
val = pd.DataFrame(val); val.to_csv('results/validation.csv', index=False)
res['validation_mape_2026_03'] = val.groupby(['series', 'model']).agg(median_ape=('ape_last', 'median'), share_under=('under', 'mean')).round(3).reset_index().to_dict('records')

# 地域差：住宅用は一戸建1000戸あたり件数、事業用は可住地1km²あたりkW、風力は全国シェア
last = df[df.date == '2026-03'].pivot(index='pref', columns='series', values='value').loc[PREFS]
mid = df[df.date == '2017-06'].pivot(index='pref', columns='series', values='value').loc[PREFS]
cov2 = cov.loc[PREFS].copy()
cov2['res_per1000det'] = last.res_cnt_new / cov2.detached * 1000
cov2['res_per1000det_2017'] = mid.res_cnt_new / cov2.detached * 1000
cov2['res_pace'] = (last.res_cnt_new - mid.res_cnt_new) / cov2.detached * 1000 / (2026.25 - 2017.5)  # 年あたり
cov2['res_mig_per1000det'] = df[(df.date == '2026-03') & (df.series == 'res_cnt_mig')].set_index('pref').value.loc[PREFS] / cov2.detached * 1000
cov2['big_kw_per_km2'] = last.big_kw_new / cov2.habitable_km2
cov2['big_share_by2017'] = mid.big_kw_new / last.big_kw_new
cov2['wind_kw'] = last.wind_kw_new
cov2['t50obs_res'] = obs_t('res_cnt_new'); cov2['t50obs_big'] = obs_t('big_kw_new'); cov2['t50obs_wind'] = obs_t('wind_kw_new')
fb = fits[(fits.model == 'Bass') & fits.pref.isin(PREFS)].set_index(['series', 'pref'])
for s, nm in [('res_cnt_new', 'res'), ('big_kw_new', 'big'), ('wind_kw_new', 'wind')]:
    g = fb.loc[s].reindex(PREFS)
    cov2[f'bass_t50_{nm}'] = g.t50; cov2[f'bass_q_{nm}'] = g.p2; cov2[f'bass_p_{nm}'] = g.p1; cov2[f'bass_Kbound_{nm}'] = g.K_at_bound
cov2.to_csv('results/pref_metrics.csv')

def spear(a, b):
    m = cov2[[a, b]].dropna(); r, pv = stats.spearmanr(m[a], m[b]); return dict(rho=round(r, 3), p=round(pv, 4), n=len(m))
corr = {}
for y in ['res_per1000det', 'res_pace', 'res_per1000det_2017', 't50obs_res', 'big_kw_per_km2', 't50obs_big', 'big_share_by2017']:
    corr[y] = {x: spear(y, x) for x in ['sunshine_h', 'detached_share', 'inc_pc', 'res_mig_per1000det']}
res['spearman'] = corr
# 地方ブロック
reg = cov2.groupby('region').apply(lambda g: pd.Series(dict(
    res_per1000det=g.res_cnt_new_sum if False else (last.loc[g.index].res_cnt_new.sum() / g.detached.sum() * 1000),
    res_per1000det_2017=(mid.loc[g.index].res_cnt_new.sum() / g.detached.sum() * 1000),
    big_kw_per_km2=last.loc[g.index].big_kw_new.sum() / g.habitable_km2.sum(),
    big_share_by2017=mid.loc[g.index].big_kw_new.sum() / last.loc[g.index].big_kw_new.sum(),
    wind_share=last.loc[g.index].wind_kw_new.sum() / last.wind_kw_new.sum(),
    wind_share_2017=mid.loc[g.index].wind_kw_new.sum() / mid.wind_kw_new.sum(),
    t50obs_res_med=g.t50obs_res.median(), t50obs_big_med=g.t50obs_big.median(), t50obs_wind_med=g.t50obs_wind.median(),
    sunshine=g.sunshine_h.mean(), n=len(g))))
order = ['北海道', '東北', '関東', '中部', '近畿', '中国', '四国', '九州・沖縄']
reg = reg.loc[order]; reg.round(3).to_csv('results/region_metrics.csv')
res['region'] = reg.round(3).reset_index().to_dict('records')
# 広がりの集中：風力の上位5県シェア、事業用太陽光の上位5県シェア
def topshare(col, k=5):
    v = last[col].sort_values(ascending=False); return round(v.head(k).sum() / v.sum(), 3)
res['top5_share'] = {s: topshare(s) for s in SERIES}
res['top5_share_2017'] = {s: round(mid[s].sort_values(ascending=False).head(5).sum() / mid[s].sum(), 3) for s in SERIES}
res['gini'] = {}
for s in SERIES:
    v = np.sort((last[s] / cov2.habitable_km2).values); n = len(v); res['gini'][s] = round((2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * v.sum()), 3)
# 全国の値
natv = df.groupby(['series', 'date']).value.sum().unstack(0)
res['national_levels'] = natv.loc[['2014-04', '2017-03', '2017-06', '2020-03', '2023-03', '2026-03'], list(SERIES) + ['res_cnt_mig']].round(0).to_dict('index')
# 年あたりの増え方（全国）
natv['t'] = natv.index.map(tyear)
yr = natv[natv.index.str.endswith('-03')]
res['national_annual_adds_FY'] = (yr[list(SERIES)].diff().dropna().round(0)).to_dict('index')

# 頑健性1：曲線の形（3モデルの t50 の都道府県順位の一致）
rob = {}
for s in SERIES:
    f = fits[(fits.series == s) & fits.pref.isin(PREFS) & fits.ok].pivot(index='pref', columns='model', values='t50').reindex(PREFS)
    rob[s] = {f'{a}×{b}': round(stats.spearmanr(f[a], f[b], nan_policy='omit')[0], 3) for a, b in [('Bass', 'ロジスティック'), ('Bass', 'ゴンペルツ'), ('ロジスティック', 'ゴンペルツ')]}
    rob[s]['観測t50×Bass t50'] = round(stats.spearmanr(cov2[f"t50obs_{ {'res_cnt_new':'res','big_kw_new':'big','wind_kw_new':'wind'}[s]}"], f['Bass'].reindex(PREFS), nan_policy='omit')[0], 3)
res['robust_shape_rank_corr'] = rob
# 頑健性2：期間（2017年6月以降だけで当てはめ。起点の0を使わない）
rows2 = []
for s in SERIES:
    for p in PREFS + ['全国']:
        d = df[(df.series == s)] if p == '全国' else df[(df.series == s) & (df.pref == p)]
        if p == '全国': d = d.groupby('t', as_index=False).value.sum()
        d = d[d.t >= tyear('2017-06')].sort_values('t'); t = d.t.values; y = d.value.values
        if y.max() <= 0: continue
        r = fit('ロジスティック', t, y, kmax=y.max() * 20)
        if r: rows2.append(dict(series=s, pref=p, K_ratio=r['K'] / y.max(), K_at_bound=r['K_at_bound'], t50=tq('ロジスティック', r['par'], .5) + 2012.5))
f2 = pd.DataFrame(rows2)
res['robust_period_2017on_logistic'] = {s: dict(national=f2[(f2.series == s) & (f2.pref == '全国')].round(3).to_dict('records'),
                                               K_at_bound=int(f2[(f2.series == s) & (f2.pref != '全国')].K_at_bound.sum()),
                                               t50_median=round(f2[(f2.series == s) & (f2.pref != '全国')].t50.median(), 2)) for s in SERIES}
# 頑健性3：電源の単位（住宅用を件数ではなく容量で）
for s2 in ['res_kw_new']:
    v = obs_t(s2); rob['res_kw_vs_cnt_t50obs'] = round(stats.spearmanr(v, cov2.t50obs_res)[0], 3)
    res['spearman']['t50obs_res_kw'] = {x: spear('t50obs_res', x) for x in ['sunshine_h']}
    cov2['t50obs_reskw'] = v
    res['spearman']['t50obs_reskw'] = {x: spear('t50obs_reskw', x) for x in ['sunshine_h', 'detached_share', 'inc_pc']}
# 頑健性4：ブートストラップで日照との相関の区間
bs = {}
for y in ['res_per1000det', 'res_pace', 'big_kw_per_km2', 't50obs_big']:
    m = cov2[[y, 'sunshine_h']].dropna().values; vals = []
    for _ in range(2000):
        i = rng.integers(0, len(m), len(m)); vals.append(stats.spearmanr(m[i, 0], m[i, 1])[0])
    bs[y] = [round(np.percentile(vals, 2.5), 3), round(np.percentile(vals, 97.5), 3)]
res['bootstrap_ci_spearman_sunshine'] = bs
# 頑健性5：重回帰（住宅用の普及度 ~ 日照 + 一戸建率 + 所得、標準化係数）
import statsmodels.api as sm
for y in ['res_per1000det', 'res_pace']:
    X = cov2[['sunshine_h', 'detached_share', 'inc_pc']].apply(lambda c: (c - c.mean()) / c.std())
    mdl = sm.OLS((cov2[y] - cov2[y].mean()) / cov2[y].std(), sm.add_constant(X), missing='drop').fit(cov_type='HC1')
    res[f'ols_{y}'] = dict(coef=mdl.params.round(3).to_dict(), ci=mdl.conf_int().round(3).values.tolist(), r2=round(mdl.rsquared, 3))
res['robustness_rank_corr'] = rob
res['data_points'] = sorted(df.date.unique().tolist())
json.dump(res, open('results/results.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: res[k] for k in ['national_fits', 'pref_fit_summary', 'validation_mape_2026_03']}, ensure_ascii=False, indent=0, default=float)[:6000])
