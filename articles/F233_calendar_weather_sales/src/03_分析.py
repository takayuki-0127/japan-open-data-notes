"""03 分析：前年同月比を、カレンダー（曜日・祝日・連休・うるう年）と天気（気温・雨）と消費税に分解する"""
import pandas as pd, numpy as np, statsmodels.api as sm, json, itertools, math
from pathlib import Path
B = Path(__file__).resolve().parents[1]; R = B/'results'; R.mkdir(exist_ok=True)
rng = np.random.default_rng(233)
s = pd.read_csv(B/'data/sales_monthly.csv'); cal = pd.read_csv(B/'data/calendar_monthly.csv')
w = pd.read_csv(B/'data/weather_national.csv')
G = ['百貨店','スーパー','コンビニ','ドラッグストア','ホームセンター','家電大型専門店']

def ym_shift(ym, k):
    p = pd.Period(ym, 'M') + k; return str(p)

cal = cal.set_index('ym'); w = w.set_index('ym')
def d12(df, cols):
    out = {}
    for ym in df.index:
        p = ym_shift(ym, -12)
        if p in df.index: out[ym] = df.loc[ym, cols].values - df.loc[p, cols].values
    return pd.DataFrame(out, index=cols).T
calc = ['n_sat','n_sun','n_hol_wd','n_renkyu','n_days'] + [f'dow{k}' for k in range(7)]
dc = d12(cal, calc).add_prefix('d_')
wcols = ['tmean','rain1','tmean_3c','rain1_3c']
dw = d12(w, wcols).add_prefix('d_')
mon = pd.Series({ym:int(ym[5:]) for ym in dw.index})
dw['d_temp_summer'] = dw.d_tmean*mon.isin([6,7,8,9]).astype(float)
dw['d_temp_winter'] = dw.d_tmean*mon.isin([12,1,2]).astype(float)
dw['d_temp_other'] = dw.d_tmean - dw.d_temp_summer - dw.d_temp_winter
dw['d3_temp_summer'] = dw.d_tmean_3c*mon.isin([6,7,8,9]).astype(float)
dw['d3_temp_winter'] = dw.d_tmean_3c*mon.isin([12,1,2]).astype(float)
dw['d3_temp_other'] = dw.d_tmean_3c - dw.d3_temp_summer - dw.d3_temp_winter

TAX = {'2014-03':'tax_pre14','2014-04':'tax_post14','2015-03':'tax_pre14b','2015-04':'tax_post14b',
       '2019-09':'tax_pre19','2019-10':'tax_post19','2020-09':'tax_pre19b','2020-10':'tax_post19b'}
def ydf(g):
    x = s[s.業態==g].set_index('ym').値
    if s[s.業態==g].指標.iloc[0]=='既存店':
        y = 100*np.log(x/100)
    else:
        y = pd.Series({ym:100*np.log(x[ym]/x[ym_shift(ym,-12)]) for ym in x.index if ym_shift(ym,-12) in x.index})
    return y.rename('y')
def covid(ym): return '2020-02'<=ym<='2023-05'

CAL = ['d_n_sat','d_n_sun','d_n_hol_wd','d_n_renkyu','d_n_days']
WEA = ['d_temp_summer','d_temp_winter','d_temp_other','d_rain1']
WEA3 = ['d3_temp_summer','d3_temp_winter','d3_temp_other','d_rain1_3c']
DOW = ['d_dow1','d_dow2','d_dow3','d_dow4','d_dow5','d_dow6','d_n_hol_wd','d_n_renkyu']  # 月曜が基準（日数の差は d_dow の合計で吸収）

def panel(g, start='2013-01', end='2026-08', drop_covid=True):
    y = ydf(g); d = pd.concat([y, dc, dw], axis=1, join='inner')
    for k,v in TAX.items(): d[v] = (d.index==k).astype(float)
    # 2014・2019の駆け込みと反動は、1年後の比較月で符号が逆になる
    d['tax14'] = d.tax_pre14 - d.tax_pre14b; d['tax14r'] = d.tax_post14 - d.tax_post14b
    d['tax19'] = d.tax_pre19 - d.tax_pre19b; d['tax19r'] = d.tax_post19 - d.tax_post19b
    d = d[(d.index>=start)&(d.index<=end)]
    if drop_covid: d = d[~d.index.map(covid)]
    return d.dropna(subset=['y'])
TAXV = ['tax14','tax14r','tax19','tax19r']

def fit(d, cols):
    cols = [c for c in cols if d[c].abs().sum()>0]
    X = sm.add_constant(d[cols]); m = sm.OLS(d.y, X).fit(cov_type='HAC', cov_kwds={'maxlags':12})
    return m, cols
def r2(d, cols):
    if not cols: return 0.0
    cols = [c for c in cols if d[c].abs().sum()>0]
    return sm.OLS(d.y, sm.add_constant(d[cols])).fit().rsquared

res = {}; coef_rows = []; dec_rows = []; contrib_rows = []
for g in G:
    d = panel(g)
    m, cols = fit(d, CAL+WEA+TAXV)
    for c in CAL+WEA:
        if c in m.params: coef_rows.append(dict(業態=g, 変数=c, 係数=m.params[c], lo=m.conf_int().loc[c,0], hi=m.conf_int().loc[c,1], p=m.pvalues[c], n=int(m.nobs)))
    # Shapley R2（3グループ）
    groups = {'カレンダー':CAL, '天気':WEA, '消費税':TAXV}
    sh = {k:0.0 for k in groups}; names = list(groups)
    for k in names:
        others = [o for o in names if o!=k]
        for r_ in range(len(others)+1):
            for S in itertools.combinations(others, r_):
                wgt = math.factorial(len(S))*math.factorial(len(names)-len(S)-1)/math.factorial(len(names))
                base = sum((groups[o] for o in S), [])
                sh[k] += wgt*(r2(d, base+groups[k]) - r2(d, base))
    dec_rows.append(dict(業態=g, **{f'R2_{k}':v for k,v in sh.items()}, R2_計=m.rsquared, sd_y=d.y.std(), n=int(m.nobs)))
    # 月ごとの寄与（カレンダー・天気）
    cc = d[[c for c in CAL if c in m.params]].mul(m.params[[c for c in CAL if c in m.params]]).sum(1)
    wc = d[[c for c in WEA if c in m.params]].mul(m.params[[c for c in WEA if c in m.params]]).sum(1)
    t = pd.DataFrame({'業態':g,'y':d.y,'カレンダー寄与':cc,'天気寄与':wc}); t['調整後']=t.y-t.カレンダー寄与-t.天気寄与
    contrib_rows.append(t.reset_index().rename(columns={'index':'ym'}))
    res[g] = dict(n=int(m.nobs), r2=m.rsquared,
                  abs_cal_med=float(cc.abs().median()), abs_cal_p90=float(cc.abs().quantile(.9)),
                  abs_wea_med=float(wc.abs().median()), abs_wea_p90=float(wc.abs().quantile(.9)),
                  share_cal_gt1=float((cc.abs()>1).mean()), share_cw_gt1=float(((cc+wc).abs()>1).mean()))
coef = pd.DataFrame(coef_rows); coef.to_csv(R/'A_coef_main.csv', index=False)
dec = pd.DataFrame(dec_rows); dec.to_csv(R/'B_r2_decomposition.csv', index=False)
contrib = pd.concat(contrib_rows); contrib.to_csv(R/'C_monthly_contrib.csv', index=False)

# 頑健性1：2013〜2019年だけで推定 → 2023-06〜2026-08 に当てはめ（期間外の検証）
oos = []
for g in G:
    dtr = panel(g, end='2019-12'); dte = panel(g, start='2023-06')
    m, cols = fit(dtr, CAL+WEA+TAXV)
    Xte = sm.add_constant(dte[cols], has_constant='add')[m.params.index]
    cw = [c for c in CAL+WEA if c in m.params]
    pred_cw = dte[cw].mul(m.params[cw]).sum(1)
    raw = dte.y - dte.y.mean(); adj = (dte.y - pred_cw); adj = adj - adj.mean()
    oos.append(dict(業態=g, n_test=len(dte), sd_raw=raw.std(), sd_adj=adj.std(), 減少率=1-adj.std()/raw.std()))
oos = pd.DataFrame(oos); oos.to_csv(R/'D_out_of_sample.csv', index=False)

# 頑健性2：天気を東京・名古屋・大阪の3都市に
# 頑健性3：曜日を7つの曜日の数の差で表す
# 頑健性4：年を1年ずつ抜く
# 頑健性5：コロナ期を含める（2020-02〜2023-05 も入れる）
rob = []
key = ['d_n_sat','d_n_sun','d_n_hol_wd','d_temp_summer','d_rain1']
for g in G:
    d = panel(g)
    m0,_ = fit(d, CAL+WEA+TAXV)
    d3 = d.copy()
    m3,_ = fit(d3, CAL+WEA3+TAXV)
    mdw,_ = fit(d, DOW+['d_n_days']+WEA+TAXV)
    mc,_ = fit(panel(g, drop_covid=False), CAL+WEA+TAXV)
    loo = {k:[] for k in key}
    for yr in sorted(set(i[:4] for i in d.index)):
        mm,_ = fit(d[~d.index.str.startswith(yr)], CAL+WEA+TAXV)
        for k in key:
            if k in mm.params: loo[k].append(mm.params[k])
    for k in key:
        rob.append(dict(業態=g, 変数=k, 主=m0.params.get(k,np.nan),
            三都市=m3.params.get(k.replace('d_temp','d3_temp').replace('d_rain1','d_rain1_3c'),np.nan) if k.startswith(('d_temp','d_rain')) else m0.params.get(k,np.nan),
            曜日7分類=(mdw.params.get('d_dow5',np.nan) if k=='d_n_sat' else mdw.params.get('d_dow6',np.nan) if k=='d_n_sun' else mdw.params.get(k,np.nan)),
            コロナ期込み=mc.params.get(k,np.nan),
            一年抜き_min=min(loo[k]) if loo[k] else np.nan, 一年抜き_max=max(loo[k]) if loo[k] else np.nan))
    # 並べ替え：天気を年ごとにシャッフルしても天気の R2 は出るか
rob = pd.DataFrame(rob); rob.to_csv(R/'E_robustness.csv', index=False)
perm = []
for g in G:
    d = panel(g); base = r2(d, CAL+TAXV); real = r2(d, CAL+WEA+TAXV)-base
    sims = []
    for _ in range(500):
        dd = d.copy(); idx = rng.permutation(len(dd)); dd[WEA] = dd[WEA].values[idx]
        sims.append(r2(dd, CAL+WEA+TAXV)-base)
    perm.append(dict(業態=g, 天気の追加R2=real, 並べ替え95点=np.quantile(sims,.95), p=(np.array(sims)>=real).mean()))
perm = pd.DataFrame(perm); perm.to_csv(R/'F_weather_permutation.csv', index=False)

json.dump(dict(per_group=res), open(R/'main.json','w'), ensure_ascii=False, indent=1, default=float)
pd.set_option('display.width',200)
print(coef.round(3).to_string()); print(dec.round(3).to_string()); print(oos.round(3).to_string())
print(rob.round(3).to_string()); print(perm.round(3).to_string()); print(json.dumps(res, ensure_ascii=False, indent=0, default=float)[:1500])

# 追加1：消費税の前後の月を除いた「ふだんの月」での分解
dec2 = []
for g in G:
    d = panel(g); d = d[(d[TAXV].abs().sum(1)==0)]
    sh = {}
    rc = r2(d, CAL); rw = r2(d, WEA); rcw = r2(d, CAL+WEA)
    sh['カレンダー'] = 0.5*(rc + (rcw-rw)); sh['天気'] = 0.5*(rw + (rcw-rc))
    dec2.append(dict(業態=g, **{f'R2_{k}':v for k,v in sh.items()}, R2_計=rcw, sd_y=d.y.std(), n=len(d)))
dec2 = pd.DataFrame(dec2); dec2.to_csv(R/'B2_r2_normal_months.csv', index=False); print(dec2.round(3).to_string())

# 追加2：来年（2026-09〜2027-12）の月ごとに、カレンダーだけで前年比が何%動くか（係数は主の推定）
calf = pd.read_csv(B/'data/calendar_monthly.csv').set_index('ym')
dcf = d12(calf, calc).add_prefix('d_')
fut = dcf[(dcf.index>='2026-09')&(dcf.index<='2027-12')]
rows = []
for g in G:
    m,_ = fit(panel(g), CAL+WEA+TAXV)
    cc = fut[CAL].mul(m.params[CAL]).sum(1)
    for ym,v in cc.items(): rows.append(dict(ym=ym, 業態=g, カレンダー寄与=v))
fut_t = pd.DataFrame(rows); fut_t = fut_t.merge(fut[CAL].reset_index().rename(columns={'index':'ym'}), on='ym')
fut_t.to_csv(R/'G_calendar_effect_2026_2027.csv', index=False)
print(fut_t.pivot(index='ym', columns='業態', values='カレンダー寄与').round(2).to_string())

# 追加3：架空の販促の例（架空の小売チェーン「みどり屋」。売上の動きはスーパーの全国の値で代用）
c = contrib[(contrib.業態=='スーパー')&(contrib.ym>='2024-01')].copy(); c['cw']=c.カレンダー寄与+c.天気寄与
ex = c.loc[c.cw.abs().idxmax()] if False else c.iloc[c.cw.abs().values.argmax()]
print('例', ex.to_dict())
json.dump(dict(per_group=res, example=ex.to_dict()), open(R/'main.json','w'), ensure_ascii=False, indent=1, default=float)
