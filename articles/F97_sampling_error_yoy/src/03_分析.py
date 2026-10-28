"""前年比・前月比が標本誤差の範囲を超えているかを調べる。"""
import json
import numpy as np, pandas as pd
from scipy.stats import norm
from common import DATA, RES, CATS
np.random.seed(42)
Z95, Z90 = norm.ppf(0.975), norm.ppf(0.95)
se10 = pd.read_csv(DATA/'kakei_se_10cat.csv'); sem = pd.read_csv(DATA/'kakei_se_monthly.csv')
se18 = pd.read_csv(DATA/'kakei_se_items_2018.csv'); ser = pd.read_csv(DATA/'kakei_se_region.csv')
km = pd.read_csv(DATA/'kakei_monthly.csv'); ka = pd.read_csv(DATA/'kakei_annual.csv')
lfs = pd.read_csv(DATA/'lfs_se_by_size.csv'); ur = pd.read_csv(DATA/'lfs_urate_sa.csv')
out = {}
def sed(s1, s2=None, rho=0.0):
    s2 = s1 if s2 is None else s2
    return np.sqrt(s1**2 + s2**2 - 2*rho*s1*s2)
# ---- 1. 標準誤差率（年平均）を4年の平均で
se_ann = se10.groupby('item')[['two','single','single_m','single_f']].mean()
out['se_annual_two'] = se_ann.two.round(2).to_dict()
se_m_total = sem.se.mean(); out['se_month_total_mean'] = round(se_m_total,3)
out['se_month_total_range'] = [float(sem.se.min()), float(sem.se.max())]
ratio_m_a = se_m_total / se_ann.loc['消費支出','two']; out['ratio_month_to_annual'] = round(ratio_m_a,2)
# ---- 2. 見つけられる最小の変化（95%・独立、検出力80%も）
rows = []
def add(series, kind, s, note=''):
    rows.append(dict(series=series, kind=kind, se=s, thr95=Z95*sed(s), thr90=Z90*sed(s), mdc80=(Z95+norm.ppf(0.8))*sed(s), note=note))
for c in CATS: add(c, '二人以上・年', se_ann.loc[c,'two'])
add('消費支出', '二人以上・月', se_m_total)
for c in ['食料','光熱・水道','教養娯楽','交通・通信','住居']: add(c, '二人以上・月（推計）', se_ann.loc[c,'two']*np.sqrt(12), '年の標準誤差率×√12')
for c in ['消費支出']: add('消費支出', '単身・年', se_ann.loc[c,'single']); add('消費支出','単身男性・年',se_ann.loc[c,'single_m']); add('消費支出','単身女性・年',se_ann.loc[c,'single_f'])
for r, g in ser.groupby('region'):
    add('消費支出', f'地方・年（{r}）', g.se.mean())
for _, r in se18.iterrows(): add(r['item'], '品目・年（2018年の表）', r['se_2018'])
mdc = pd.DataFrame(rows); mdc.to_csv(RES/'mdc_table.csv', index=False)
# ---- 3. 月の実質前年同月比（消費支出、公表値）の判定
t = km[km.item=='消費支出'].dropna(subset=['real']).copy()
t['ym'] = pd.to_datetime(t.date)
thr_m = Z95*sed(se_m_total)
t['sig'] = t.real.abs() > thr_m
out['monthly_total'] = dict(n=int(len(t)), period=[t.date.min(), t.date.max()], thr95=round(thr_m,2),
    share_sig=round(t.sig.mean(),3), share_abs_le1=round((t.real.abs()<=1).mean(),3),
    share_sig_2015_2026=round(t[t.ym>='2015-01-01'].sig.mean(),3))
# 月ごとの実際の標準誤差率が両方分かる月（2023〜2025年）
mm = sem.copy(); mm['date'] = mm.year.astype(str)+'-'+mm.month.map('{:02d}'.format)
mm['prev'] = (mm.year-1).astype(str)+'-'+mm.month.map('{:02d}'.format)
mm = mm.merge(mm[['date','se']].rename(columns={'date':'prev','se':'se_prev'}), on='prev')
mm = mm.merge(t[['date','real','nom']], on='date')
mm['thr'] = Z95*np.sqrt(mm.se**2+mm.se_prev**2); mm['sig'] = mm.real.abs() > mm.thr
mm.to_csv(RES/'monthly_exact_se_2023_2025.csv', index=False)
out['monthly_exact'] = dict(n=int(len(mm)), thr_range=[round(mm.thr.min(),2), round(mm.thr.max(),2)], n_sig=int(mm.sig.sum()),
    sig_months=mm.loc[mm.sig,'date'].tolist(), real_range=[float(mm.real.min()), float(mm.real.max())])
# 傾向からのばらつきと標本誤差の比較（13か月中心移動平均からの残差）
t = t.set_index('ym').sort_index()
ex = t.index.to_series().between('2014-01-01','2015-06-30') | t.index.to_series().between('2019-06-01','2021-12-31')
s = t.real.copy(); ma = s.rolling(13, center=True).mean(); resid = (s - ma)[~ex].dropna()
out['resid_sd_vs_noise'] = dict(resid_sd=round(resid.std(),2), noise_sd=round(sed(se_m_total)*np.sqrt(1-1/13),2), n=int(len(resid)))
t[['real','nom','sig']].assign(ma13=ma).to_csv(RES/'monthly_total_yoy.csv')
# ---- 4. 年の前年比（11費目、2001〜2025年、2018・2019年を除く）
def annual_test(rho=0.0, z=Z95, se_src='mean'):
    r = []
    for c in CATS:
        s = se_ann.loc[c,'two'] if se_src=='mean' else (se18.set_index('item').se_2018[c] if se_src=='2018' else se10[(se10.year==int(se_src))&(se10.item==c)].two.iloc[0])
        g = ka[(ka.item==c)&ka.yoy.notna()]
        for _, x in g.iterrows():
            r.append(dict(item=c, year=int(x.year), yoy=x.yoy, se=s, thr=z*sed(s, rho=rho), sig=abs(x.yoy) > z*sed(s, rho=rho)))
    return pd.DataFrame(r)
an = annual_test(); an.to_csv(RES/'annual_10cat_tests.csv', index=False)
by = an.groupby('item').agg(n=('sig','size'), share_sig=('sig','mean'), thr=('thr','first'), med_abs=('yoy', lambda v: v.abs().median()))
by.to_csv(RES/'annual_10cat_summary.csv'); out['annual_10cat'] = by.round(3).to_dict(orient='index')
tot = an[an.item=='消費支出']; out['annual_total_years_not_sig'] = tot.loc[~tot.sig, ['year','yoy']].round(2).values.tolist()
# 30品目（2018年の表）
r = []
for _, x in se18.iterrows():
    g = ka[(ka.item==x['item'])&ka.yoy.notna()]
    thr = Z95*sed(x.se_2018)
    r.append(dict(item=x['item'], se=x.se_2018, thr=thr, n=len(g), share_sig=(g.yoy.abs()>thr).mean(), med_abs=g.yoy.abs().median()))
it30 = pd.DataFrame(r); it30.to_csv(RES/'annual_30items_summary.csv', index=False)
out['items30_share_sig_overall'] = round(float((it30.share_sig*it30.n).sum()/it30.n.sum()),3)
# 月の品目（推計の標準誤差率）
r = []
for _, x in se18.iterrows():
    g = km[(km.item==x['item'])].dropna(subset=['real'])
    thr = Z95*sed(x.se_2018*np.sqrt(12))
    r.append(dict(item=x['item'], se_month=x.se_2018*np.sqrt(12), thr=thr, n=len(g), share_sig=(g.real.abs()>thr).mean()))
im = pd.DataFrame(r); im.to_csv(RES/'monthly_items_summary.csv', index=False)
# ---- 5. 「+1%」は本当に増えたか：真の変化が0より大きい確からしさ（平らな事前分布のおおまかな目安）
p = {}
for lab, s in [('年・消費支出', se_ann.loc['消費支出','two']), ('月・消費支出', se_m_total), ('年・単身', se_ann.loc['消費支出','single']),
               ('年・地方（平均）', ser[ser.region!='全国'].se.mean()), ('年・教育', se_ann.loc['教育','two'])]:
    p[lab] = {f'{v:+.0f}%': round(float(norm.cdf(v/sed(s))),3) for v in [0.5,1,2,3,5]}
out['prob_increase'] = p
# ---- 6. 労働力調査：完全失業率の前月差
L = np.log(lfs.size_man.values); Lm = np.log(lfs.se_rate_month.values); La = np.log(lfs.se_rate_annual.values)
LF = 6900  # 労働力人口（万人）のおおよその値。2025年平均は7,004万人、1990年代後半〜2010年代は6,500〜6,900万人程度
def se_rate_pt(u, monthly=True):
    size = u/100*LF
    sr = np.exp(np.interp(np.log(size), L[::-1], (Lm if monthly else La)[::-1]))
    return u*sr/100
ur['month'] = pd.to_datetime(ur.month); ur = ur.set_index('month')
ur['se'] = se_rate_pt(ur.urate.values); ur['d1'] = ur.urate.diff().round(1); ur['d12'] = ur.urate.diff(12).round(1)
out['lfs_se_pt'] = dict(at_2_5=round(float(se_rate_pt(np.array([2.5]))[0]),3), at_5_0=round(float(se_rate_pt(np.array([5.0]))[0]),3), median=round(ur.se.median(),3))
res_l = {}
for rho in [0, 0.25, 0.5]:
    thr = Z95*ur.se*np.sqrt(2*(1-rho))
    d = ur.d1.dropna(); th = thr.loc[d.index]
    res_l[str(rho)] = dict(thr_median=round(float(th.median()),3), share_sig=round(float((d.abs()>th).mean()),3),
        share_sig_among_pm01=round(float(((d.abs()>th)&(d.abs().round(1)==0.1)).sum()/max(1,(d.abs().round(1)==0.1).sum())),3),
        share_sig_d12=round(float((ur.d12.dropna().abs() > thr.loc[ur.d12.dropna().index]).mean()),3))
out['lfs'] = res_l
dist = ur.d1.dropna().value_counts().sort_index(); out['lfs_d1_dist'] = {f'{k:+.1f}': int(v) for k, v in dist.items()}
ur.to_csv(RES/'lfs_urate_changes.csv')
# ---- 7. 頑健性
rb = []
for rho in [0, 0.1, 0.2]:
    a = annual_test(rho=rho); rb.append(dict(check='年の相関ρ', setting=f'ρ={rho}', share_sig=a.sig.mean(), share_sig_total=a[a.item=='消費支出'].sig.mean()))
for lab, z in [('95%', Z95), ('90%', Z90)]:
    a = annual_test(z=z); rb.append(dict(check='信頼水準（年）', setting=lab, share_sig=a.sig.mean(), share_sig_total=a[a.item=='消費支出'].sig.mean()))
    rb.append(dict(check='信頼水準（月・消費支出）', setting=lab, share_sig=(t.real.abs() > z*sed(se_m_total)).mean(), share_sig_total=np.nan))
for src in ['2022','2025','2018']:
    a = annual_test(se_src=src); rb.append(dict(check='標準誤差の出どころ（年）', setting=src+'年の表', share_sig=a.sig.mean(), share_sig_total=a[a.item=='消費支出'].sig.mean()))
for lab, s in [('平均1.42%', se_m_total), ('最小1.1%', 1.1), ('最大1.7%', 1.7)]:
    rb.append(dict(check='月の標準誤差率', setting=lab, share_sig=(t.real.abs() > Z95*sed(s)).mean(), share_sig_total=np.nan))
rb.append(dict(check='特別な月を除く（月・消費支出）', setting='消費税・コロナの時期を除く', share_sig=(t.real[~ex].abs() > thr_m).mean(), share_sig_total=np.nan))
rb.append(dict(check='名目と実質（月・消費支出）', setting='名目', share_sig=(t.nom.abs() > thr_m).mean(), share_sig_total=np.nan))
for lab, k in [('√12倍', np.sqrt(12)), (f'実際の比{ratio_m_a:.2f}倍', ratio_m_a)]:
    sh = []
    for _, x in se18.iterrows():
        g = km[(km.item==x['item'])].dropna(subset=['real']); sh.append((g.real.abs() > Z95*sed(x.se_2018*k)).values)
    rb.append(dict(check='品目の月の標準誤差率の推計', setting=lab, share_sig=np.concatenate(sh).mean(), share_sig_total=np.nan))
rb = pd.DataFrame(rb); rb.to_csv(RES/'robustness.csv', index=False)
out['robustness'] = rb.round(3).to_dict(orient='records')
out['annual_overall_share_sig'] = round(float(an.sig.mean()),3)
out['monthly_items_share_sig_overall'] = round(float((im.share_sig*im.n).sum()/im.n.sum()),3)
json.dump(out, open(RES/'summary_main.json','w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:9000])
