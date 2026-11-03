# 雨の日が月の小売販売額をどれだけ動かすか：前年同月差どうしの回帰（全国の時系列）と、地域パネル（月の固定効果）
import warnings; warnings.filterwarnings('ignore')
import pandas as pd, numpy as np, pathlib, json, statsmodels.formula.api as smf, calendar, datetime as dt, jpholiday
A = pathlib.Path(__file__).resolve().parents[1]; R = A/'results'
np.random.seed(135)
ret = pd.read_csv(A/'data/retail_monthly.csv'); wm = pd.read_csv(A/'data/weather_monthly.csv')

# ---- 暦：月の土日祝の日数（前年同月との差を統制） ----
def offdays(ym):
    y, m = map(int, ym.split('-'))
    return sum(1 for d in range(1, calendar.monthrange(y, m)[1]+1)
               if dt.date(y, m, d).weekday() >= 5 or jpholiday.is_holiday(dt.date(y, m, d)))
yms = sorted(set(ret.ym) | set(wm.ym))
cal = pd.DataFrame({'ym': yms}); cal['off'] = cal.ym.map(offdays)
cal['ndays'] = cal.ym.map(lambda s: calendar.monthrange(*map(int, s.split('-')))[1])

def lag12(ym):
    y, m = map(int, ym.split('-')); return f'{y-1}-{m:02d}'

# ---- 気象：地点ごとの前年同月差、全国は9地点の平均 ----
W = wm.copy()
W['ptot_log'] = np.log1p(W.ptot)
vars_ = ['rain1', 'rain10', 'ptot_log', 'tmean', 'rain1_off', 'rain1_wd']
W['ym_l'] = W.ym.map(lag12)
W = W.merge(W[['地点', 'ym'] + vars_].rename(columns={'ym': 'ym_l', **{v: v+'_l' for v in vars_}}), on=['地点', 'ym_l'], how='left')
for v in vars_: W['d_'+v] = W[v] - W[v+'_l']
W['d_t2'] = W.tmean**2 - W.tmean_l**2
nat_w = W.groupby('ym')[[c for c in W if c.startswith('d_')] + vars_].mean().reset_index()

# ---- 売上：前年同月比（対数差×100）。百貨店・スーパーは既存店の伸び率も ----
def g12(df):
    df = df.sort_values('ym').copy(); s = df.set_index('ym').値
    df['g'] = [100*(np.log(s[y]) - np.log(s[lag12(y)])) if lag12(y) in s.index and s[lag12(y)] > 0 else np.nan for y in df.ym]
    return df

nat = []
for (gy, it, kd), df in ret[ret.地域 == '全国'].groupby(['業態', '品目', '指標']):
    if kd == '既存店':
        df = df.assign(g=100*np.log1p(df.値/100))      # 伸び率(%)を対数差に
    else:
        df = g12(df)
    nat.append(df)
nat = pd.concat(nat)

# 期間・ダミー
TAX = ['2014-03', '2014-04', '2015-03', '2015-04', '2019-09', '2019-10', '2020-09', '2020-10']
COVID = lambda ym: '2020-02' <= ym <= '2023-05'
def prep(df, w):
    d = df.merge(w, on='ym').merge(cal, on='ym')
    d['d_off'] = d.off - d.ym.map(lag12).map(cal.set_index('ym').off)
    d['d_ndays'] = d.ndays - d.ym.map(lag12).map(cal.set_index('ym').ndays)
    for t in TAX: d['tax_'+t.replace('-', '')] = (d.ym == t).astype(int)
    d['covid'] = d.ym.map(COVID); d['m'] = d.ym.str[5:7]
    d['season'] = d.m.map(lambda m: {'06': '梅雨', '07': '梅雨', '08': '夏', '09': '夏', '12': '冬', '01': '冬', '02': '冬'}.get(m, '春秋'))
    return d[(d.ym >= '2014-01') & (d.ym <= '2026-08')].dropna(subset=['g', 'd_rain1'])
TAXF = ' + '.join('tax_'+t.replace('-', '') for t in TAX)

MAIN = [('百貨店', '合計', '既存店'), ('スーパー', '合計', '既存店'), ('コンビニ', '商品販売額', '販売額'),
        ('ドラッグストア', '商品販売額', '販売額'), ('ホームセンター', '商品販売額', '販売額'), ('家電大型専門店', '商品販売額', '販売額')]
ITEMS = [('百貨店', '衣料品', '既存店'), ('百貨店', '身の回り品', '既存店'), ('百貨店', '飲食料品', '既存店'),
         ('スーパー', '衣料品', '既存店'), ('スーパー', '飲食料品', '既存店'), ('スーパー', '家庭用品', '既存店'),
         ('コンビニ', 'FF・日配食品', '販売額'), ('コンビニ', '加工食品', '販売額'), ('コンビニ', '非食品', '販売額')]

def fit(d, rain='d_rain1', extra='', excl_covid=True):
    x = d[~d.covid] if excl_covid else d.assign()
    f = f'g ~ {rain} + d_tmean + d_t2 + d_off + d_ndays + {TAXF}{extra}' + (' + covid' if not excl_covid else '')
    r = smf.ols(f, x).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    return r, len(x)

def row(name, r, n, term):
    b, se = r.params[term], r.bse[term]
    return dict(系列=name, 係数=b, 下限=b-1.96*se, 上限=b+1.96*se, p=r.pvalues[term], n=n)

out = {}
def series(gy, it, kd):
    return nat[(nat.業態 == gy) & (nat.品目.str.startswith(it)) & (nat.指標 == kd)]

# 1) 業態ごとの主結果
rows = []; keep = []
for gy, it, kd in MAIN:
    d = prep(series(gy, it, kd), nat_w); r, n = fit(d); rows.append(row(f'{gy}', r, n, 'd_rain1'))
    # 図1用：他の変数を除いた残差どうし（FWL）
    x = d[~d.covid].copy(); ctrl = f'd_tmean + d_t2 + d_off + d_ndays + {TAXF}'
    x['res_g'] = smf.ols('g ~ ' + ctrl, x).fit().resid; x['res_rain'] = smf.ols('d_rain1 ~ ' + ctrl, x).fit().resid
    keep.append(x[['ym', 'g', 'd_rain1', 'res_g', 'res_rain']].assign(業態=gy))
pd.concat(keep).to_csv(A/'data/national_prepped.csv', index=False)
main = pd.DataFrame(rows); main.to_csv(R/'main_by_format.csv', index=False); out['main'] = main
# 2) 品目
rows = []
for gy, it, kd in ITEMS:
    s = series(gy, it, kd)
    if s.empty: continue
    d = prep(s, nat_w); r, n = fit(d); rows.append(row(f'{gy}・{it}', r, n, 'd_rain1'))
items = pd.DataFrame(rows); items.to_csv(R/'items.csv', index=False); out['items'] = items
# 3) 土日祝の雨と平日の雨
rows = []
for gy, it, kd in MAIN:
    d = prep(series(gy, it, kd), nat_w)
    x = d[~d.covid]
    r = smf.ols(f'g ~ d_rain1_off + d_rain1_wd + d_tmean + d_t2 + d_off + d_ndays + {TAXF}', x).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    for t, lab in [('d_rain1_off', '土日祝の雨'), ('d_rain1_wd', '平日の雨')]:
        rows.append({**row(gy, r, len(x), t), '雨の曜日': lab})
offwd = pd.DataFrame(rows); offwd.to_csv(R/'offday_vs_weekday.csv', index=False); out['offwd'] = offwd
# 4) 季節ごと（雨×季節の交差項）
rows = []
for gy, it, kd in MAIN:
    d = prep(series(gy, it, kd), nat_w); x = d[~d.covid].copy()
    for s in ['梅雨', '夏', '冬', '春秋']: x['rs_'+s] = x.d_rain1*(x.season == s)
    r = smf.ols(f'g ~ rs_梅雨 + rs_夏 + rs_冬 + rs_春秋 + d_tmean + d_t2 + d_off + d_ndays + {TAXF}', x).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    for s in ['梅雨', '夏', '冬', '春秋']: rows.append({**row(gy, r, len(x), 'rs_'+s), '季節': s})
season = pd.DataFrame(rows); season.to_csv(R/'season.csv', index=False); out['season'] = season

# 5) 頑健性：降水の指標・期間・重み
rows = []
w_big = W[W.地点.isin(['東京', '名古屋', '大阪'])].groupby('ym')[[c for c in W if c.startswith('d_')]].mean().reset_index()
for gy, it, kd in MAIN:
    s = series(gy, it, kd); base = prep(s, nat_w)
    r, n = fit(base); rows.append({**row(gy, r, n, 'd_rain1'), '条件': '基本（1mm以上の日数）'})
    r, n = fit(base, 'd_rain10'); rows.append({**row(gy, r, n, 'd_rain10'), '条件': '10mm以上の日数'})
    r, n = fit(base, 'd_ptot_log'); b = row(gy, r, n, 'd_ptot_log'); rows.append({**b, '条件': '月の降水量（対数）'})
    r, n = fit(base, excl_covid=False); rows.append({**row(gy, r, n, 'd_rain1'), '条件': 'コロナ期を含める'})
    r, n = fit(base[base.ym >= '2016-01']); rows.append({**row(gy, r, n, 'd_rain1'), '条件': '2016年以降'})
    r, n = fit(prep(s, w_big)); rows.append({**row(gy, r, n, 'd_rain1'), '条件': '三大都市の雨だけ'})
    x = base[~base.covid]; rr = smf.ols(f'g ~ d_rain1 + d_off + d_ndays + {TAXF}', x).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    rows.append({**row(gy, rr, len(x), 'd_rain1'), '条件': '気温を入れない'})
rob = pd.DataFrame(rows); rob.to_csv(R/'robustness_national.csv', index=False); out['rob'] = rob

# 6) 地域パネル：前年同月比 ~ 地域の雨の日数の差 + 月の固定効果（全国共通の動き・暦・コロナ・税を吸収）
reg = ret[(ret.地域 != '全国')].copy()
pan = []
for (gy, rg), df in reg.groupby(['業態', '地域']):
    pan.append(g12(df))
pan = pd.concat(pan).merge(W[['地域', 'ym', 'd_rain1', 'd_rain10', 'd_ptot_log', 'd_tmean', 'd_t2', 'd_rain1_off', 'd_rain1_wd']], on=['地域', 'ym'])
pan = pan[(pan.ym >= '2014-01') & (pan.ym <= '2026-08')].dropna(subset=['g', 'd_rain1'])
# 地域区分が途中で変わる系列（ホームセンターの九州・沖縄）は除く
pan = pan[~((pan.業態 == 'ホームセンター') & pan.地域.isin(['九州', '沖縄']))]
pan.to_csv(A/'data/panel_region.csv', index=False)
rows = []
for gy, d in pan.groupby('業態'):
    for cond, x, rain in [('基本', d, 'd_rain1'), ('コロナ期を除く', d[~d.ym.map(COVID)], 'd_rain1'),
                          ('10mm以上の日数', d, 'd_rain10'), ('沖縄を除く', d[d.地域 != '沖縄'], 'd_rain1')]:
        r = smf.ols(f'g ~ {rain} + d_tmean + d_t2 + C(ym) + C(地域)', x).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(x.ym)[0]})
        rows.append({**row(gy, r, len(x), rain), '条件': cond, '地域数': x.地域.nunique()})
    # 地域でクラスター（少数クラスターなので参考）
    r = smf.ols('g ~ d_rain1 + d_tmean + d_t2 + C(ym) + C(地域)', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.地域)[0]})
    rows.append({**row(gy, r, len(d), 'd_rain1'), '条件': '地域でクラスター（参考）', '地域数': d.地域.nunique()})
    x = d.copy(); r = smf.ols('g ~ d_rain1_off + d_rain1_wd + d_tmean + d_t2 + C(ym) + C(地域)', x).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(x.ym)[0]})
    for t, lab in [('d_rain1_off', '土日祝の雨'), ('d_rain1_wd', '平日の雨')]:
        rows.append({**row(gy, r, len(x), t), '条件': lab, '地域数': x.地域.nunique()})
panel = pd.DataFrame(rows); panel.to_csv(R/'panel_region.csv', index=False); out['panel'] = panel

# 記述：雨の日数の前年差の大きさ
desc = dict(
    sd_d_rain1_nat=float(prep(series('百貨店', '合計', '既存店'), nat_w).query('~covid').d_rain1.std()),
    sd_d_rain1_station=float(W[(W.ym >= '2014-01') & (W.ym <= '2026-08')].d_rain1.std()),
    mean_rain1_nat=float(nat_w[(nat_w.ym >= '2014-01')].rain1.mean()),
    corr_rain1_ptot=float(W[['d_rain1', 'd_ptot_log']].corr().iloc[0, 1]),
    corr_rain1_tmean=float(W[['d_rain1', 'd_tmean']].corr().iloc[0, 1]),
)
json.dump(desc, open(R/'describe.json', 'w'), ensure_ascii=False, indent=1)
pd.set_option('display.width', 200)
for k, v in out.items(): print('==', k); print(v.round(3).to_string())
print(desc)
