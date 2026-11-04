# 博物館・美術館の入館者はコロナ前に戻ったか：3年ごとの社会教育調査で、コロナ前の傾向と比べる
import os, json
import numpy as np, pandas as pd
import statsmodels.api as sm
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '..', 'data'); R = os.path.join(HERE, '..', 'results')
os.makedirs(R, exist_ok=True)
rng = np.random.default_rng(194)

vis = pd.read_csv(os.path.join(D, 'national_visitors_by_type.csv'))
fac = pd.read_csv(os.path.join(D, 'national_facilities_by_type_derived.csv'))
use = pd.read_csv(os.path.join(D, 'national_users_by_facility.csv'))
pref = pd.read_csv(os.path.join(D, 'pref_visitors_museum_similar.csv'))
rail = pd.read_csv(os.path.join(D, 'rail_fiscal_year.csv'))
TYPES = ['総合', '科学', '歴史', '美術', '野外', '動物園', '植物園', '動植物園', '水族館']

def trend_cf(years, values, fit_years, target_years, log=True):
    """fit_years の点で 対数(値)=a+b*年度 を当てはめ、target_years の予測と95%予測区間を返す"""
    s = pd.Series(values, index=years)
    y = np.log(s.loc[fit_years].values) if log else s.loc[fit_years].values
    X = sm.add_constant(np.array(fit_years, float))
    m = sm.OLS(y, X).fit()
    Xt = sm.add_constant(np.array(target_years, float), has_constant='add')
    pr = m.get_prediction(Xt).summary_frame(alpha=0.05)
    f = np.exp if log else (lambda v: v)
    return dict(pred=f(pr['mean'].values), lo=f(pr['obs_ci_lower'].values), hi=f(pr['obs_ci_upper'].values),
                slope_pct=(np.exp(m.params[1]) - 1) * 100 if log else m.params[1], r2=m.rsquared, n=len(fit_years))

BASES = {
    '主：1998〜2017年度の傾向': dict(fit=[1998, 2001, 2004, 2007, 2010, 2014, 2017], trend=True),
    '2007〜2017年度の傾向': dict(fit=[2007, 2010, 2014, 2017], trend=True),
    '1989〜2017年度の傾向': dict(fit=[1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2014, 2017], trend=True),
    '傾向なし：2017年度そのもの': dict(fit=[2017], trend=False),
    '傾向なし：2014・2017年度の平均': dict(fit=[2014, 2017], trend=False),
}

def recovery(series, base):
    """series: 年度→値。base の取り方で 2020・2023年度の回復率（実績÷基準）を返す"""
    b = BASES[base]
    yrs = list(series.index)
    if b['trend']:
        cf = trend_cf(yrs, series.values, b['fit'], [2020, 2023])
        pred, lo, hi, slope = cf['pred'], cf['lo'], cf['hi'], cf['slope_pct']
    else:
        m = series.loc[b['fit']].mean()
        pred = np.array([m, m]); lo = hi = np.array([np.nan, np.nan]); slope = np.nan
    act = series.loc[[2020, 2023]].values
    return dict(rec2020=act[0] / pred[0], rec2023=act[1] / pred[1],
                rec2023_lo=act[1] / hi[1] if b['trend'] else np.nan, rec2023_hi=act[1] / lo[1] if b['trend'] else np.nan,
                base2023=pred[1], slope_pct_per_fy=slope)

MAIN = '主：1998〜2017年度の傾向'
out = {}

# 1) 全国（博物館＋類似施設）と、種類別
rows = []
for col in ['合計'] + TYPES:
    s = vis.set_index('fy')[col]
    r = recovery(s, MAIN)
    rows.append(dict(series=col, fy2017=s[2017], fy2020=s[2020], fy2023=s[2023],
                     vs2017_2020=s[2020] / s[2017], vs2017_2023=s[2023] / s[2017], **r))
by_type = pd.DataFrame(rows)
by_type.to_csv(os.path.join(R, 'recovery_by_type.csv'), index=False)

# 2) 基準の取り方（頑健性1）
rob = []
s = vis.set_index('fy')['合計']
for b in BASES:
    r = recovery(s, b); rob.append(dict(base=b, **r))
# 鉄道（F136 と同じ統計）も同じ年度で
rs = rail[rail.unit == '全国'].set_index('fy')
rail_rows = []
for col in ['total', 'teikigai', 'teiki']:
    x = rs[col]
    rail_rows.append(dict(series=col, vs2017_2020=x[2020] / x[2017], vs2017_2023=x[2023] / x[2017], vs2017_2025=x[2025] / x[2017],
                          vs2019_2023=x[2023] / x[2019]))
rail_nat = pd.DataFrame(rail_rows)
# 鉄道の傾向（2014〜2018年度、年度ごとの点）で 2023年度の基準を作る
for col in ['total', 'teikigai']:
    x = rs[col]
    cf = trend_cf(list(x.index), x.values, [2014, 2015, 2016, 2017, 2018], [2020, 2023])
    rail_nat.loc[rail_nat.series == col, 'rec2023_trend'] = x[2023] / cf['pred'][1]
    rail_nat.loc[rail_nat.series == col, 'slope_pct_per_fy'] = cf['slope_pct']
rail_nat.to_csv(os.path.join(R, 'rail_fiscal_comparison.csv'), index=False)

# 頑健性2：1館あたり（施設数の変化を除く）
fs = fac.set_index('fy')['合計']
per_hall = (vis.set_index('fy')['合計'] * 1000 / fs)
r_ph = recovery(per_hall, MAIN)
rob.append(dict(base='1館あたり（主の基準）', **r_ph))
rob.append(dict(base='1館あたり：2017年度比', rec2020=per_hall[2020] / per_hall[2017], rec2023=per_hall[2023] / per_hall[2017]))
pd.DataFrame(rob).to_csv(os.path.join(R, 'robustness_baseline.csv'), index=False)

# 3) 博物館と類似施設、ほかの社会教育施設（利用者数）
u = use.set_index('fy')
fac_rows = []
for col in ['公民館', '図書館', '博物館', '博物館類似施設', '青少年教育施設', '女性教育施設', '社会体育施設', '民間体育施設', '生涯学習センター']:
    x = u[col]
    fac_rows.append(dict(facility=col, fy2017=x[2017], fy2020=x[2020], fy2023=x[2023],
                         vs2017_2020=x[2020] / x[2017], vs2017_2023=x[2023] / x[2017],
                         vs2014_2017=x[2017] / x[2014] if not np.isnan(x[2014]) else np.nan))
other = pd.DataFrame(fac_rows)
other.to_csv(os.path.join(R, 'other_facilities.csv'), index=False)

# 4) 特別展とそれ以外（全国、博物館・類似施設）
p = pref[pref.pref == '全国'].copy()
p['regular'] = p.visitors - p.special
sp = p.pivot(index='kind', columns='fy', values=['visitors', 'special', 'regular', 'halls'])
sp_rows = []
for kind in ['博物館', '博物館類似施設']:
    for v in ['visitors', 'special', 'regular', 'halls']:
        sp_rows.append(dict(kind=kind, var=v, fy2017=sp.loc[kind, (v, 2017)], fy2020=sp.loc[kind, (v, 2020)], fy2023=sp.loc[kind, (v, 2023)],
                            vs2017_2023=sp.loc[kind, (v, 2023)] / sp.loc[kind, (v, 2017)]))
special = pd.DataFrame(sp_rows)
special.to_csv(os.path.join(R, 'special_exhibitions.csv'), index=False)

# 5) 地方（運輸局の区分。沖縄は1県だけになるので九州とまとめて9区分）：博物館＋類似施設の 2023/2017 と、鉄道の同じ比
pref['region'] = pref.region.replace({'九州': '九州・沖縄', '沖縄': '九州・沖縄'})
rail.loc[rail.unit.isin(['九州', '沖縄']), 'unit'] = '九州・沖縄'
rail = rail.groupby(['unit', 'fy'], as_index=False)[['teiki', 'teikigai', 'total']].sum()
q = pref[pref.pref != '全国'].groupby(['region', 'fy'])[['visitors', 'halls']].sum().reset_index()
qr = q.pivot(index='region', columns='fy', values='visitors')
qh = q.pivot(index='region', columns='fy', values='halls')
reg = pd.DataFrame({'visitors2017': qr[2017], 'visitors2020': qr[2020], 'visitors2023': qr[2023],
                    'vs2017_2020': qr[2020] / qr[2017], 'vs2017_2023': qr[2023] / qr[2017],
                    'perhall_vs2017_2023': (qr[2023] / qh[2023]) / (qr[2017] / qh[2017])})
# 博物館だけ・類似施設だけ
for kind, tag in [('博物館', 'mus'), ('博物館類似施設', 'sim')]:
    qq = pref[(pref.pref != '全国') & (pref.kind == kind)].groupby(['region', 'fy']).visitors.sum().unstack()
    reg[f'{tag}_vs2017_2023'] = qq[2023] / qq[2017]
rr = rail[rail.unit.isin(reg.index)].pivot(index='unit', columns='fy', values=['total', 'teikigai'])
reg['rail_total_vs2017_2023'] = rr[('total', 2023)] / rr[('total', 2017)]
reg['rail_teikigai_vs2017_2023'] = rr[('teikigai', 2023)] / rr[('teikigai', 2017)]
reg['share2017'] = reg.visitors2017 / reg.visitors2017.sum()
order = ['北海道', '東北', '関東', '北陸信越', '中部', '近畿', '中国', '四国', '九州・沖縄']
reg = reg.loc[order]
reg.to_csv(os.path.join(R, 'recovery_by_region.csv'))
from scipy.stats import spearmanr
rho_t, p_t = spearmanr(reg.vs2017_2023, reg.rail_teikigai_vs2017_2023)
rho_a, p_a = spearmanr(reg.vs2017_2023, reg.rail_total_vs2017_2023)
# 都道府県（47）の 2023/2017 の分布（順位は出さない）
pp = pref[(pref.pref != '全国')].groupby(['pref', 'fy']).visitors.sum().unstack()
ratio47 = pp[2023] / pp[2017]
# 頑健性：関東を除く全国
exk = q[q.region != '関東'].groupby('fy').visitors.sum()

# 6) 2023年度の不足を種類に分ける（2017年度比で、どの種類の減少が大きいか）
gap = (by_type.set_index('series').fy2017 - by_type.set_index('series').fy2023)[TYPES]
gap_share = (gap / gap.sum())

out.update(dict(
    total=by_type[by_type.series == '合計'].iloc[0].to_dict(),
    rail=rail_nat.to_dict('records'),
    per_hall=dict(r_ph, per2017=per_hall[2017], per2023=per_hall[2023], halls2017=fs[2017], halls2023=fs[2023]),
    spearman_region_vs_rail_teikigai=[rho_t, p_t], spearman_region_vs_rail_total=[rho_a, p_a],
    pref47=dict(median=float(ratio47.median()), q10=float(ratio47.quantile(.1)), q90=float(ratio47.quantile(.9)),
                n_ge_100=int((ratio47 >= 1).sum()), n_lt_80=int((ratio47 < .8).sum())),
    ex_kanto=dict(vs2017_2023=exk[2023] / exk[2017]),
    gap_share=gap_share.to_dict(),
))
json.dump(out, open(os.path.join(R, 'summary.json'), 'w'), ensure_ascii=False, indent=1, default=float)

pd.set_option('display.width', 200)
print(by_type.round(3).to_string())
print(pd.DataFrame(rob).round(3).to_string())
print(rail_nat.round(3).to_string())
print(other.round(3).to_string())
print(special.round(3).to_string())
print(reg.round(3).to_string())
print(json.dumps({k: out[k] for k in ['per_hall', 'spearman_region_vs_rail_teikigai', 'spearman_region_vs_rail_total', 'pref47', 'ex_kanto', 'gap_share']}, ensure_ascii=False, default=float, indent=0))
