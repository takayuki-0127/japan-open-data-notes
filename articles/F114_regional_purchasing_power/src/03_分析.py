# 03_分析：名目の所得を地域の物価で割ると、都道府県の差はどれだけ縮むか
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from common import P, CATS, TEN, area
rng = np.random.default_rng(114)
reg = pd.read_csv(P('data/regional_index_long.csv'), dtype={'code': str})
idx = reg[reg.table == 'index']; wgt = reg[reg.table == 'weight']
pref_idx = idx[idx.level == '都道府県'].copy(); pref_idx['pref'] = pref_idx.pref.astype(int)
inc = pd.read_csv(P('data/income_per_taxpayer.csv'))
kp = pd.read_csv(P('data/income_per_capita_kenmin.csv'))
S = {}

# 0) 総合を10大費目から作り直せるか（全国のウエイト／その地域のウエイト）
val = []
for y in sorted(idx.year.unique()):
    I = pref_idx[pref_idx.year == y].set_index('code')
    W = wgt[(wgt.year == y)].set_index('code')
    wn = W.loc['00000', TEN].astype(float); wn = wn / wn.sum()
    rn = (I[TEN] * wn).sum(axis=1)
    wr = W.loc[I.index, TEN].astype(float); wr = wr.div(wr.sum(axis=1), axis=0)
    rr = (I[TEN] * wr).sum(axis=1)
    val.append(dict(year=y, mae_national_w=float((rn - I['総合']).abs().mean()), mae_own_w=float((rr - I['総合']).abs().mean()),
                    max_national_w=float((rn - I['総合']).abs().max())))
val = pd.DataFrame(val); val.to_csv(P('results/check_rebuild_total.csv'), index=False)
S['rebuild'] = val.mean(numeric_only=True).round(3).to_dict()
print('総合の作り直し（平均絶対誤差）\n', val.round(3).to_string(index=False))

def stats(nom, price, w=None):
    """nom: 名目所得、price: 地域差指数（全国=100）。47都道府県の対数のばらつきと、物価に吸収される割合"""
    ln, lp = np.log(nom), np.log(price / 100)
    lr = ln - lp
    if w is None: w = np.ones(len(ln))
    w = np.asarray(w, float) / np.sum(w)
    sd = lambda x: np.sqrt(np.sum(w * (x - np.sum(w * x)) ** 2))
    cov = np.sum(w * (ln - np.sum(w * ln)) * (lp - np.sum(w * lp)))
    beta = cov / sd(ln) ** 2
    return dict(sd_nom=sd(ln), sd_real=sd(lr), shrink=1 - sd(lr) / sd(ln), beta=beta,
                maxmin_nom=float(np.exp(ln.max() - ln.min())), maxmin_real=float(np.exp(lr.max() - lr.min())),
                rho=float(pd.Series(ln).rank().corr(pd.Series(lr).rank())))

def boot_ci(nom, price, B=2000):
    n = len(nom); out = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        st = stats(nom[i], price[i]); out.append((st['shrink'], st['beta']))
    out = np.array(out)
    return np.percentile(out[:, 0], [2.5, 97.5]), np.percentile(out[:, 1], [2.5, 97.5])

def panel(y_inc, y_price=None, col='総合'):
    y_price = y_price or y_inc
    a = inc[inc.year == y_inc].drop_duplicates('pref').set_index('pref')
    b = pref_idx[pref_idx.year == y_price].set_index('pref')
    d = pd.DataFrame({'inc': a.inc_tp, 'price': b[col], 'price_xr': b['家賃を除く総合'], 'housing': b['住居']}).dropna()
    d['taxpayers'] = a.taxpayers if 'taxpayers' in a else np.nan
    return d

# 1) 本体：2024年（課税対象所得÷納税義務者、地域差指数 2024年）
d = panel(2024)
d['real'] = d.inc / (d.price / 100); d['real_xr'] = d.inc / (d.price_xr / 100)
d['area'] = [area(i) for i in d.index]
nat = d.inc.median()
main = stats(d.inc.values, d.price.values); main_xr = stats(d.inc.values, d.price_xr.values)
ci_s, ci_b = boot_ci(d.inc.values, d.price.values)
main.update(shrink_ci=list(np.round(ci_s, 3)), beta_ci=list(np.round(ci_b, 3)))
S['main_2024'] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}
S['main_2024_ex_rent'] = {k: round(v, 4) for k, v in main_xr.items()}
# 東京都と他の46の中央値との比
oth = d.drop(13)
tok = dict(nom_ratio=d.inc[13] / oth.inc.median(), real_ratio=d.real[13] / oth.real.median(), real_xr_ratio=d.real_xr[13] / oth.real_xr.median(),
           price=d.price[13], price_xr=d.price_xr[13], housing=d.housing[13])
S['tokyo_2024'] = {k: round(float(v), 3) for k, v in tok.items()}
# 圏域の平均（納税義務者は2024年の値がないので2020年の人数で重み付け）
w20 = inc[(inc.year == 2020) & (inc.src == '市区町村の合計')].set_index('pref').taxpayers
d['w'] = w20
ar = d.groupby('area').apply(lambda g: pd.Series({'n': len(g), 'nom': np.average(g.inc, weights=g.w), 'price': np.average(g.price, weights=g.w),
                                                  'price_xr': np.average(g.price_xr, weights=g.w), 'real': np.average(g.real, weights=g.w),
                                                  'real_xr': np.average(g.real_xr, weights=g.w)}))
base_nom = np.average(d.inc, weights=d.w); base_real = np.average(d.real, weights=d.w); base_xr = np.average(d.real_xr, weights=d.w)
ar['nom_rel'] = ar.nom / base_nom; ar['real_rel'] = ar.real / base_real; ar['real_xr_rel'] = ar.real_xr / base_xr
ar.round(4).to_csv(P('results/area_2024.csv'))
S['area_2024'] = ar[['n', 'nom_rel', 'price', 'real_rel', 'price_xr', 'real_xr_rel']].round(3).to_dict(orient='index')
print(ar.round(3).to_string())
# 順位の動き
d['rank_nom'] = d.inc.rank(ascending=False); d['rank_real'] = d.real.rank(ascending=False); d['rank_xr'] = d.real_xr.rank(ascending=False)
mv = (d.rank_nom - d.rank_real).abs()
S['rank_2024'] = dict(moved5=int((mv >= 5).sum()), moved10=int((mv >= 10).sum()), max_move=int(mv.max()), median_move=float(mv.median()),
                      tokyo_rank_nom=int(d.rank_nom[13]), tokyo_rank_real=int(d.rank_real[13]), tokyo_rank_xr=int(d.rank_xr[13]))
d.round(4).to_csv(P('results/pref_2024.csv'))
# 所得の差を物価が打ち消す割合：所得が10%高い県は物価が何%高いか
S['elasticity_note'] = '所得（対数）に対する地域差指数（対数）の傾き＝beta'

# 2) 年を変える（課税対象所得の年 × 同じ年の地域差指数）
rows = []
for y in [2013, 2015, 2017, 2020, 2024]:
    dd = panel(y)
    for col in ['総合', '家賃を除く総合']:
        p = dd.price if col == '総合' else dd.price_xr
        st = stats(dd.inc.values, p.values); st.update(year=y, price=col, tokyo_nom=float(dd.inc[13] / dd.drop(13).inc.median()),
                                                     tokyo_real=float((dd.inc / p)[13] / (dd.inc / p).drop(13).median()))
        rows.append(st)
yr = pd.DataFrame(rows); yr.round(4).to_csv(P('results/by_year_taxable.csv'), index=False)
print(yr.round(3).to_string(index=False))
S['by_year'] = yr.round(3).to_dict(orient='records')

# 3) 所得の物差しを変える：1人当たり県民所得（年度）× 地域差指数（同じ年）
rows = []
for y in range(2013, 2024):
    a = kp[kp.year == y].set_index('pref'); b = pref_idx[pref_idx.year == y].set_index('pref')
    dd = pd.DataFrame({'inc': a.inc_pc, 'price': b['総合'], 'xr': b['家賃を除く総合']}).dropna()
    if len(dd) < 40: continue
    st = stats(dd.inc.values, dd.price.values); st2 = stats(dd.inc.values, dd.xr.values)
    rows.append(dict(year=y, n=len(dd), shrink=st['shrink'], beta=st['beta'], shrink_xr=st2['shrink'], beta_xr=st2['beta'],
                     tokyo_nom=float(dd.inc[13] / dd.drop(13).inc.median()), tokyo_real=float((dd.inc / dd.price)[13] / (dd.inc / dd.price).drop(13).median())))
kpr = pd.DataFrame(rows); kpr.round(4).to_csv(P('results/by_year_kenmin.csv'), index=False)
print(kpr.round(3).to_string(index=False))
S['kenmin'] = dict(shrink_range=[round(kpr.shrink.min(), 3), round(kpr.shrink.max(), 3)], beta_range=[round(kpr.beta.min(), 3), round(kpr.beta.max(), 3)],
                   tokyo_nom_range=[round(kpr.tokyo_nom.min(), 3), round(kpr.tokyo_nom.max(), 3)], tokyo_real_range=[round(kpr.tokyo_real.min(), 3), round(kpr.tokyo_real.max(), 3)])

# 4) 世帯の型で物価の重みを変える（2024年）：10大費目の指数を、家計調査の支出の割合で平均し直す
hh = pd.read_csv(P('data/household_spending_2024.csv'), index_col=0)
I24 = pref_idx[pref_idx.year == 2024].set_index('pref')
W24 = wgt[(wgt.year == 2024) & (wgt.code == '00000')][TEN].iloc[0].astype(float)
types = {'公式のウエイト（全国）': W24, '総世帯（平均）': hh.loc['総世帯', TEN], '持家（総世帯）': hh.loc['総世帯の持家', TEN],
         '民営借家（総世帯）': hh.loc['総世帯の民営借家', TEN], '単身（平均）': hh.loc['単身_平均', TEN], '単身・民営借家': hh.loc['単身_民営借家', TEN],
         '勤労者・民営借家': hh.loc['勤労者世帯の民営借家', TEN]}
rows = []; prices = {}
for nm, w in types.items():
    w = w.astype(float) / w.sum()
    p = (I24[TEN] * w).sum(axis=1); prices[nm] = p
    st = stats(d.inc.loc[p.index].values, p.values)
    rows.append(dict(type=nm, housing_share=float(w['住居']), shrink=st['shrink'], beta=st['beta'], price_tokyo=float(p[13]),
                     price_sd=float(p.std()), price_min=float(p.min()), price_max=float(p.max()),
                     tokyo_real=float((d.inc / p)[13] / (d.inc / p).drop(13).median())))
ht = pd.DataFrame(rows); ht.round(4).to_csv(P('results/household_types_2024.csv'), index=False)
pd.DataFrame(prices).round(2).to_csv(P('results/household_price_2024.csv'))
print(ht.round(3).to_string(index=False))
S['household'] = ht.round(3).to_dict(orient='records')

# 5) 重み付け：納税義務者数で重み付け（2020年、人数のある年）
dd = panel(2020); st = stats(dd.inc.values, dd.price.values, w=dd.taxpayers.values)
S['weighted_2020'] = {k: round(v, 4) for k, v in st.items()}
S['unweighted_2020'] = {k: round(v, 4) for k, v in stats(dd.inc.values, dd.price.values).items()}

# 6) 都市（都道府県庁所在市・政令市）：2020年の地域差指数（総合）と課税対象所得
ci = pd.read_csv(P('data/city_income_2020.csv'), dtype={'ccode': str})
cidx = idx[(idx.year == 2020) & (idx.level == '都市')][['code', 'name', '総合']]
cc = cidx.merge(ci, left_on='code', right_on='ccode', how='inner').dropna(subset=['総合', 'inc_tp'])
stc = stats(cc.inc_tp.values, cc['総合'].values)
S['city_2020'] = {k: round(v, 4) for k, v in stc.items()}; S['city_2020']['n'] = len(cc)
cc.to_csv(P('results/city_2020.csv'), index=False)
print('都市', len(cc), {k: round(v, 3) for k, v in stc.items()})

# 7) 物価の地域差そのものの推移（47都道府県の標準偏差）
tr = pref_idx.groupby('year').agg(sd_total=('総合', 'std'), sd_xr=('家賃を除く総合', 'std'), sd_housing=('住居', 'std'),
                                  max_total=('総合', 'max'), min_total=('総合', 'min'), tokyo=('総合', lambda s: np.nan))
tr['tokyo'] = pref_idx[pref_idx.pref == 13].set_index('year')['総合']
tr['tokyo_xr'] = pref_idx[pref_idx.pref == 13].set_index('year')['家賃を除く総合']
tr.round(3).to_csv(P('results/price_dispersion_trend.csv'))
print(tr.round(2).to_string())
S['trend'] = dict(sd_total_2013=round(tr.sd_total[2013], 3), sd_total_2025=round(tr.sd_total[2025], 3),
                  sd_xr_2013=round(tr.sd_xr[2013], 3), sd_xr_2025=round(tr.sd_xr[2025], 3),
                  tokyo_2013=tr.tokyo[2013], tokyo_2025=tr.tokyo[2025])
# 8) 住居（家賃）の差が、物価の差のうちどれだけか（2024年、全国ウエイトで寄与を分解）
wn = W24 / W24.sum()
contrib = (I24[TEN] - 100).mul(wn, axis=1)
tot = contrib.sum(axis=1)
share = contrib.apply(lambda c: np.cov(c, tot)[0, 1] / tot.var())
S['variance_share_2024'] = share.round(3).to_dict()
# 所得の差を打ち消す部分のうち、住居の寄与
lp_h = np.log(1 + contrib['住居'] / 100)
S['beta_housing_part'] = round(float(np.cov(lp_h, np.log(d.inc.loc[I24.index]))[0, 1] / np.log(d.inc.loc[I24.index]).var()), 4)
json.dump(S, open(P('results/summary.json'), 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: S[k] for k in ['main_2024', 'main_2024_ex_rent', 'tokyo_2024', 'rank_2024', 'weighted_2020', 'unweighted_2020', 'variance_share_2024', 'beta_housing_part', 'kenmin']}, ensure_ascii=False, indent=0, default=float))

# 9) 住居の重みを0〜40%に動かす（ほかの費目は全国のウエイトの比のまま）
oth = W24.drop('住居') / W24.drop('住居').sum()
rows = []
for s in np.round(np.arange(0, 0.401, 0.02), 2):
    w = pd.concat([oth * (1 - s), pd.Series({'住居': s})])[TEN]
    p = (I24[TEN] * w).sum(axis=1)
    st = stats(d.inc.loc[p.index].values, p.values)
    rows.append(dict(housing_share=s, shrink=st['shrink'], beta=st['beta'], tokyo_price=float(p[13]),
                     tokyo_real=float((d.inc / p)[13] / (d.inc / p).drop(13).median())))
sw = pd.DataFrame(rows); sw.round(4).to_csv(P('results/housing_weight_sweep.csv'), index=False)
S['sweep'] = sw.iloc[[0, 5, 10, 15, 20]].round(3).to_dict(orient='records')
json.dump(S, open(P('results/summary.json'), 'w'), ensure_ascii=False, indent=1, default=float)
print(sw.round(3).to_string(index=False))
