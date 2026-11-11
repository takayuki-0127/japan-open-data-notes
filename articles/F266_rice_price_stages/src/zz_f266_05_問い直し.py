# 05 問い直し（結果を見た後で足した）：上がるときに広がった1kgあたりの取り分は、元の値段が下がった後に戻ったか
import pandas as pd, numpy as np, json, os
import statsmodels.api as sm
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
o = pd.read_csv(os.path.join(B, 'data', 'processed', 'stages_main.csv'), index_col=0, parse_dates=True)
R = os.path.join(B, 'results')
# 店頭は1か月遅れて動く（H2）ので、店頭 t と 相対取引価格 t−1 を組にした取り分も作る
o['aitai_l1'] = o['aitai_kg'].shift(1)
o['margin_l1'] = o['retail_kg'] - o['aitai_l1']
x = o.loc['2010-10':].dropna(subset=['retail_kg', 'aitai_l1'])
sd = x.loc['2015':'2023', 'margin_l1'].std(); mu = x.loc['2015':'2023', 'margin_l1'].mean()
pk = x.loc['2025', 'retail_kg'].idxmax()
res = {'margin_l1_2015_23_mean': mu, 'margin_l1_2015_23_sd': sd,
       'margin_l1_2023': x.loc['2023', 'margin_l1'].mean(), 'margin_l1_peak': x.loc[pk, 'margin_l1'], 'peak_month': str(pk.date()),
       'margin_l1_last': x['margin_l1'].iloc[-1], 'last_month': str(x.index[-1].date()),
       'margin_l1_2026_mean': x.loc['2026', 'margin_l1'].mean(),
       'margin_l1_max': x['margin_l1'].max(), 'margin_l1_max_month': str(x['margin_l1'].idxmax().date()),
       'margin_l1_2025_mean': x.loc['2025', 'margin_l1'].mean(), 'margin_l1_2024_mean': x.loc['2024', 'margin_l1'].mean()}
# 上り・下りの局面：相対取引価格（精米換算）の山の月（2025年の最大）で分ける
ap = o.loc['2025', 'aitai_kg'].idxmax()
up = x.loc['2024-01':ap]; dn = x.loc[ap:]
for lab, z in [('up', up), ('down', dn)]:
    res[f'{lab}_d_aitai'] = z['aitai_l1'].iloc[-1] - z['aitai_l1'].iloc[0]
    res[f'{lab}_d_retail'] = z['retail_kg'].iloc[-1] - z['retail_kg'].iloc[0]
    res[f'{lab}_from'] = str(z.index[0].date()); res[f'{lab}_to'] = str(z.index[-1].date())
    res[f'{lab}_passthrough_yen'] = res[f'{lab}_d_retail'] / res[f'{lab}_d_aitai']
res['aitai_peak_month'] = str(ap.date())
# 円の前月差の回帰：Δ店頭_t = a + b+ Δ相対+_{t−1} + b− Δ相対−_{t−1}（2010-10〜、年産の切り替え月も含む）
d = pd.DataFrame({'dr': x['retail_kg'].diff(), 'da': x['aitai_l1'].diff()}).dropna()
d['da_up'] = d['da'].clip(lower=0); d['da_dn'] = d['da'].clip(upper=0)
m = sm.OLS(d['dr'], sm.add_constant(d[['da_up', 'da_dn']])).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
res['reg_b_up'] = m.params['da_up']; res['reg_b_dn'] = m.params['da_dn']
res['reg_se_up'] = m.bse['da_up']; res['reg_se_dn'] = m.bse['da_dn']
res['reg_p_equal'] = float(m.t_test('da_up - da_dn = 0').pvalue); res['reg_n'] = int(m.nobs)
# 累積（0〜3か月後）で見た場合
L = []
for k in range(0, 4): L.append(x['aitai_kg'].diff().shift(k).rename(f'l{k}'))
dd = pd.concat([x['retail_kg'].diff().rename('dr')] + L, axis=1).dropna()
up_ = dd[[f'l{k}' for k in range(4)]].clip(lower=0).add_suffix('_up'); dn_ = dd[[f'l{k}' for k in range(4)]].clip(upper=0).add_suffix('_dn')
m2 = sm.OLS(dd['dr'], sm.add_constant(pd.concat([up_, dn_], axis=1))).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
res['cum_up_0_3'] = float(m2.params[[c for c in m2.params.index if c.endswith('_up')]].sum())
res['cum_dn_0_3'] = float(m2.params[[c for c in m2.params.index if c.endswith('_dn')]].sum())
w = np.zeros(len(m2.params)); idx = list(m2.params.index)
for c in idx:
    if c.endswith('_up'): w[idx.index(c)] = 1
    if c.endswith('_dn'): w[idx.index(c)] = -1
res['cum_p_equal'] = float(m2.t_test(w).pvalue)
x[['retail_kg', 'aitai_kg', 'aitai_l1', 'margin_l1']].to_csv(os.path.join(R, 'reask_margin_l1.csv'))
json.dump(res, open(os.path.join(R, 'reask.json'), 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(res, ensure_ascii=False, indent=0, default=lambda v: round(float(v), 3)))
