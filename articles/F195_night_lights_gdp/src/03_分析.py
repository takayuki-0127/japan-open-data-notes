# -*- coding: utf-8 -*-
"""夜間光で県内総生産をどこまで説明・予測できるか。
入力: data/panel.csv（02_整形.py）
出力: results/*.csv, results/summary.json
"""
import json, os
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '..', 'data'); R = os.path.join(HERE, '..', 'results')
os.makedirs(R, exist_ok=True)
rng = np.random.default_rng(195)

P = pd.read_csv(os.path.join(D, 'panel.csv'))
raw = pd.read_csv(os.path.join(D, 'raw', 'ntl_adm2_annual_jpn.csv.gz'))

# ---- 光の加工の別案（ADM2 から作り直す）----
# 画素数 = 合計 / 平均。暗い単位を除く = 平均 0.5 未満の ADM2 を 0 とする（弱い光をノイズとみなす）、中央値ベース = 中央値 × 画素数
raw['npix'] = raw['ntl_sum'] / raw['ntl_mean'].replace(0, np.nan)
raw['bgsub'] = np.where(raw['ntl_mean'] >= 0.5, raw['ntl_sum'], 0.0)
raw['medbase'] = (raw['ntl_median'] * raw['npix']).fillna(0)
src = open(os.path.join(HERE, '02_整形.py'), encoding='utf-8').read()
KUN = eval(src[src.index('KUNREI = {') + 9: src.index('}', src.index('KUNREI = {')) + 1])
raw['pref'] = raw['NAM_1'].map(KUN)
alt = raw.groupby(['pref', 'year'])[['bgsub', 'medbase', 'npix']].sum().reset_index().rename(columns={'year': 'fy'})
P = P.merge(alt, on=['pref', 'fy'], how='left')
P['light_nogf10'] = P['ntl_nogf_10km_sum']

E = P[P.edition == 2022].copy()      # 主な分析：令和4年度版（47都道府県そろう。令和5年度版は5県が未公表）
YM = int(E.fy.max())
for c in ['gdp_real', 'gdp_nom', 'pop', 'workers', 'ntl_sum', 'bgsub', 'medbase', 'light_nogf10', 'area_km2']:
    E['l_' + c] = np.log(E[c])
E['l_dens'] = np.log(E['pop'] / E['area_km2'])

out = {}

# ---- 1. 断面：年ごとの R2 と弾力性 ----
rows = []
for y, g in E.groupby('fy'):
    for lab, f in [('光だけ', 'l_gdp_real ~ l_ntl_sum'), ('人口だけ', 'l_gdp_real ~ l_pop'),
                   ('光＋人口', 'l_gdp_real ~ l_ntl_sum + l_pop'), ('就業者だけ', 'l_gdp_real ~ l_workers')]:
        m = smf.ols(f, g).fit(cov_type='HC3')
        rows.append(dict(fy=y, model=lab, r2=m.rsquared, b_light=m.params.get('l_ntl_sum', np.nan),
                         se_light=m.bse.get('l_ntl_sum', np.nan), p_light=m.pvalues.get('l_ntl_sum', np.nan)))
cs = pd.DataFrame(rows); cs.to_csv(os.path.join(R, 'cross_section_by_year.csv'), index=False)
out['csYM'] = cs[cs.fy == YM].set_index('model')[['r2', 'b_light', 'se_light', 'p_light']].round(4).to_dict('index')
out['cs_r2_light_range'] = [round(cs[cs.model == '光だけ'].r2.min(), 3), round(cs[cs.model == '光だけ'].r2.max(), 3)]
out['cs_b_light_range'] = [round(cs[cs.model == '光だけ'].b_light.min(), 3), round(cs[cs.model == '光だけ'].b_light.max(), 3)]

# ---- 2. 予測：1県ずつ抜いて当てる（2023年度）----
g = E[E.fy == YM].reset_index(drop=True)
def loo(formula, d):
    pred = np.empty(len(d))
    for i in range(len(d)):
        m = smf.ols(formula, d.drop(i)).fit(); pred[i] = m.predict(d.iloc[[i]]).iloc[0]
    return pred
L = {}
for lab, f in [('光だけ', 'l_gdp_real ~ l_ntl_sum'), ('人口だけ', 'l_gdp_real ~ l_pop'), ('光＋人口', 'l_gdp_real ~ l_ntl_sum + l_pop'),
               ('光＋人口密度', 'l_gdp_real ~ l_ntl_sum + l_dens')]:
    pr = loo(f, g); err = np.exp(g['l_gdp_real'] - pr) - 1
    L[lab] = dict(mape=float(np.mean(np.abs(err))), med_ape=float(np.median(np.abs(err))),
                  within20=int((np.abs(err) <= 0.2).sum()), max_ape=float(np.max(np.abs(err))))
    if lab == '光だけ':
        g['pred_light'] = pr; g['err_light'] = err
out['loo2022'] = {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in L.items()}
# 外れ方：光の割に生産が大きい／小さい県の特徴（名前の一覧は出さず、相関で見る）
g['dens'] = g['pop'] / g['area_km2']; g['light_pc'] = g['ntl_sum'] / g['pop']
g['gdp_pc'] = g['gdp_real'] / g['pop']
rc = {}
for c, lab in [('l_dens', '人口密度（対数）'), ('top10_share', '光の集中度（上位10%の単位の割合）'), ('light_pc', '1人あたりの光')]:
    rho, pv = stats.spearmanr(g['err_light'], g[c]); rc[lab] = dict(rho=round(float(rho), 3), p=round(float(pv), 4))
out['resid_corr'] = rc
out['tokyo_err'] = round(float(g.loc[g.pref == 13, 'err_light'].iloc[0]), 3)
out['n_over20_pos'] = int((g.err_light > 0.2).sum()); out['n_over20_neg'] = int((g.err_light < -0.2).sum())
g[['pref', 'name', 'region', 'gdp_real', 'ntl_sum', 'pop', 'dens', 'pred_light', 'err_light', 'top10_share']].to_csv(
    os.path.join(R, 'loo_2022.csv'), index=False)
# 東京を除いた断面
gx = g[g.pref != 13]; mx = smf.ols('l_gdp_real ~ l_ntl_sum', gx).fit()
out['cs_excl_tokyo'] = dict(r2=round(mx.rsquared, 4), b=round(mx.params['l_ntl_sum'], 4))

# ---- 3. 変化：同じ県の中で、光が増えた年に生産も増えたか ----
fe = smf.ols('l_gdp_real ~ l_ntl_sum + C(pref) + C(fy)', E).fit(cov_type='cluster', cov_kwds={'groups': E['pref']})
out['fe_twoway'] = dict(b=round(fe.params['l_ntl_sum'], 4), se=round(fe.bse['l_ntl_sum'], 4), p=round(fe.pvalues['l_ntl_sum'], 4))
fe1 = smf.ols('l_gdp_real ~ l_ntl_sum + C(pref)', E).fit(cov_type='cluster', cov_kwds={'groups': E['pref']})
out['fe_pref_only'] = dict(b=round(fe1.params['l_ntl_sum'], 4), se=round(fe1.bse['l_ntl_sum'], 4), p=round(fe1.pvalues['l_ntl_sum'], 4))
# 長い差：2012→2023（コロナ前 2012→2019 も）
def longdiff(y0, y1, light='ntl_sum'):
    a = E[E.fy == y0].set_index('pref'); b = E[E.fy == y1].set_index('pref')
    dl = np.log(b[light] / a[light]); dg = np.log(b['gdp_real'] / a['gdp_real'])
    rho, pv = stats.spearmanr(dl, dg); m = smf.ols('dg ~ dl', pd.DataFrame(dict(dl=dl, dg=dg))).fit(cov_type='HC3')
    return dict(rho=round(float(rho), 3), p=round(float(pv), 4), b=round(m.params['dl'], 3), se=round(m.bse['dl'], 3), r2=round(m.rsquared, 3),
                mean_dl=round(float(dl.mean()), 4), mean_dg=round(float(dg.mean()), 4)), pd.DataFrame(dict(dl=dl, dg=dg))
out['ld_2012_2022'], ld = longdiff(2012, YM); ld.to_csv(os.path.join(R, 'longdiff_2012_2022.csv'))
out['ld_2012_2019'], _ = longdiff(2012, 2019)
out['ld_2019_2022'], _ = longdiff(2019, YM)
# 全国の合計
nat = E.groupby('fy')[['ntl_sum', 'gdp_real', 'gdp_nom', 'pop']].sum()
idx = nat / nat.iloc[0] * 100; idx.to_csv(os.path.join(R, 'national_index.csv'))
out['nat_2012_2022'] = {c: round(float(idx[c].iloc[-1]), 1) for c in idx.columns}
dn = np.log(nat).diff().dropna(); rho, pv = stats.pearsonr(dn['ntl_sum'], dn['gdp_real'])
out['nat_yoy_corr'] = dict(r=round(float(rho), 3), p=round(float(pv), 4), n=int(len(dn)))
dx = dn.drop([2020, 2021]); r2_, p2_ = stats.pearsonr(dx['ntl_sum'], dx['gdp_real'])
out['nat_yoy_corr_ex2020_21'] = dict(r=round(float(r2_), 3), p=round(float(p2_), 4), n=int(len(dx)))
out['nat_2020'] = {c: round(float((nat[c].loc[2020] / nat[c].loc[2019] - 1) * 100), 2) for c in ['ntl_sum', 'gdp_real']}

# ---- 4. 頑健性 ----
rob = []
# (a) 光の加工
for lab, col in [('合計（基本）', 'ntl_sum'), ('ガス燃焼10km以内を除く', 'light_nogf10'), ('暗い単位（平均0.5未満）を除く', 'bgsub'), ('中央値×画素数', 'medbase')]:
    d = E.copy(); d['lx'] = np.log(d[col].clip(lower=1e-9))
    m = smf.ols('l_gdp_real ~ lx', d[d.fy == YM]).fit()
    f = smf.ols('l_gdp_real ~ lx + C(pref) + C(fy)', d).fit(cov_type='cluster', cov_kwds={'groups': d['pref']})
    rob.append(dict(group='光の加工', variant=lab, r2_last=m.rsquared, b_last=m.params['lx'], b_fe=f.params['lx'], p_fe=f.pvalues['lx']))
# (b) 目的変数・年の版
for lab, ed, y in [('実質（令和4年度版・基本）', 2022, 'gdp_real'), ('名目（令和4年度版）', 2022, 'gdp_nom'), ('実質（令和5年度版・42県・2023年度まで）', 2023, 'gdp_real')]:
    d = P[(P.edition == ed) & P[y].notna()].copy(); d['ly'] = np.log(d[y]); d['lx'] = np.log(d['ntl_sum'])
    yy = d.fy.max(); m = smf.ols('ly ~ lx', d[d.fy == yy]).fit()
    f = smf.ols('ly ~ lx + C(pref) + C(fy)', d).fit(cov_type='cluster', cov_kwds={'groups': d['pref']})
    rob.append(dict(group='生産の指標・版', variant=lab, r2_last=m.rsquared, b_last=m.params['lx'], b_fe=f.params['lx'], p_fe=f.pvalues['lx']))
# (c) 地域の単位：8地方にまとめる
d = E.groupby(['region', 'fy'])[['gdp_real', 'ntl_sum']].sum().reset_index()
d['ly'] = np.log(d.gdp_real); d['lx'] = np.log(d.ntl_sum)
m = smf.ols('ly ~ lx', d[d.fy == YM]).fit()
f = smf.ols('ly ~ lx + C(region) + C(fy)', d).fit(cov_type='cluster', cov_kwds={'groups': d['region']})
rob.append(dict(group='地域の単位', variant='8地方', r2_last=m.rsquared, b_last=m.params['lx'], b_fe=f.params['lx'], p_fe=f.pvalues['lx']))
rob.append(dict(group='地域の単位', variant='47都道府県（基本）', r2_last=out['csYM']['光だけ']['r2'], b_last=out['csYM']['光だけ']['b_light'],
                b_fe=out['fe_twoway']['b'], p_fe=out['fe_twoway']['p']))
# (d) 1人あたり同士（人口の大きさを除く）
d = E.copy(); d['ly'] = np.log(d.gdp_real / d['pop']); d['lx'] = np.log(d.ntl_sum / d['pop'])
m = smf.ols('ly ~ lx', d[d.fy == YM]).fit()
rob.append(dict(group='1人あたり', variant='1人あたり生産 ~ 1人あたり光', r2_last=m.rsquared, b_last=m.params['lx'], b_fe=np.nan, p_fe=np.nan))
d['lxa'] = np.log(d.ntl_sum / d.area_km2); d['lya'] = np.log(d.gdp_real / d.area_km2)
m = smf.ols('lya ~ lxa', d[d.fy == YM]).fit()
rob.append(dict(group='1人あたり', variant='面積あたり生産 ~ 面積あたり光', r2_last=m.rsquared, b_last=m.params['lxa'], b_fe=np.nan, p_fe=np.nan))
# (e) 東京を除く
rob.append(dict(group='標本', variant='東京を除く46', r2_last=out['cs_excl_tokyo']['r2'], b_last=out['cs_excl_tokyo']['b'], b_fe=np.nan, p_fe=np.nan))
d = E[E.pref != 13]; f = smf.ols('l_gdp_real ~ l_ntl_sum + C(pref) + C(fy)', d).fit(cov_type='cluster', cov_kwds={'groups': d['pref']})
rob[-1]['b_fe'] = f.params['l_ntl_sum']; rob[-1]['p_fe'] = f.pvalues['l_ntl_sum']
# (f) コロナ期（2020〜2021年度）を除く
d = E[~E.fy.isin([2020, 2021])]; f = smf.ols('l_gdp_real ~ l_ntl_sum + C(pref) + C(fy)', d).fit(cov_type='cluster', cov_kwds={'groups': d['pref']})
rob.append(dict(group='期間', variant='2020・2021年度を除く', r2_last=np.nan, b_last=np.nan, b_fe=f.params['l_ntl_sum'], p_fe=f.pvalues['l_ntl_sum']))
d = E[E.fy <= 2019]; f = smf.ols('l_gdp_real ~ l_ntl_sum + C(pref) + C(fy)', d).fit(cov_type='cluster', cov_kwds={'groups': d['pref']})
rob.append(dict(group='期間', variant='2012〜2019年度だけ', r2_last=np.nan, b_last=np.nan, b_fe=f.params['l_ntl_sum'], p_fe=f.pvalues['l_ntl_sum']))
# (g) 1年ずらす（光の年を1つ前・後に）
for sh, lab in [(1, '光を1年前に'), (-1, '光を1年後に')]:
    a = E[['pref', 'fy', 'l_ntl_sum']].copy(); a['fy'] = a['fy'] + sh
    d = E.drop(columns='l_ntl_sum').merge(a, on=['pref', 'fy'])
    f = smf.ols('l_gdp_real ~ l_ntl_sum + C(pref) + C(fy)', d).fit(cov_type='cluster', cov_kwds={'groups': d['pref']})
    rob.append(dict(group='時点', variant=lab, r2_last=np.nan, b_last=np.nan, b_fe=f.params['l_ntl_sum'], p_fe=f.pvalues['l_ntl_sum']))
rob = pd.DataFrame(rob); rob.to_csv(os.path.join(R, 'robustness.csv'), index=False)
out['rob'] = rob.round(4).to_dict('records')

# ---- 5. 並べ替え：同じ県内の変化の関係は偶然の幅を超えるか ----
# 県ごとに光の年の並びを入れ替える（県と年の効果は残す）
def fe_b(d):
    y = d['l_gdp_real'] - d.groupby('pref')['l_gdp_real'].transform('mean') - d.groupby('fy')['l_gdp_real'].transform('mean') + d['l_gdp_real'].mean()
    x = d['l_ntl_sum'] - d.groupby('pref')['l_ntl_sum'].transform('mean') - d.groupby('fy')['l_ntl_sum'].transform('mean') + d['l_ntl_sum'].mean()
    return float((x * y).sum() / (x * x).sum())
b0 = fe_b(E); null = []
for _ in range(2000):
    d = E.copy(); d['l_ntl_sum'] = d.groupby('pref')['l_ntl_sum'].transform(lambda s: rng.permutation(s.values)); null.append(fe_b(d))
null = np.array(null)
out['perm_fe'] = dict(b=round(b0, 4), p_two=round(float(np.mean(np.abs(null) >= abs(b0))), 4), q025=round(float(np.quantile(null, .025)), 4), q975=round(float(np.quantile(null, .975)), 4))

# ---- 6. 検出力の目安：今の残差の大きさで、真の弾力性 0.1/0.3 がどれだけ見分けられるか ----
res = fe.resid; sx = (E['l_ntl_sum'] - E.groupby('pref')['l_ntl_sum'].transform('mean') - E.groupby('fy')['l_ntl_sum'].transform('mean') + E['l_ntl_sum'].mean())
se_naive = float(np.sqrt(res.var() / (sx ** 2).sum()))
out['fe_se_naive'] = round(se_naive, 4); out['fe_se_cluster'] = out['fe_twoway']['se']
out['mde80'] = round(2.8 * out['fe_twoway']['se'], 3)
out['within_sd'] = dict(light=round(float(sx.std()), 4))

json.dump(out, open(os.path.join(R, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
