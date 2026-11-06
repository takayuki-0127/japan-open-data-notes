"""03 分析：A 品目別の寄与、B 世帯の区分別の物価、C 値上げと購入数量（価格弾力性）。
出力：results/*.csv, results/main.json
"""
import os, json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(H, 'data')
R = os.path.join(H, 'results')
os.makedirs(R, exist_ok=True)
rng = np.random.default_rng(209)
OUT = {}

# ---------------- A 品目別の寄与 ----------------
meta = pd.read_csv(os.path.join(D, 'cpi_items_meta.csv'), dtype={'code': str})
ann = pd.read_csv(os.path.join(D, 'cpi_items_annual.csv'), index_col=0)
mon = pd.read_csv(os.path.join(D, 'cpi_items_monthly.csv.gz'), index_col=0, dtype={'ym': str})
mon.index = mon.index.astype(str)
meta['key'] = meta['name'] + '|' + meta['code']
TOP = ['食料', '住居', '光熱・水道', '家具・家事用品', '被服及び履物', '保健医療', '交通・通信', '教育', '教養娯楽', '諸雑費']
MID = ['穀類', '魚介類', '肉類', '乳卵類', '野菜・海藻', '果物', '油脂・調味料', '菓子類', '調理食品', '飲料', '酒類', '外食',
       '家賃', '設備修繕・維持', '電気代', 'ガス代', '他の光熱', '上下水道料', '家庭用耐久財', '室内装備品', '寝具類', '家事雑貨',
       '家事用消耗品', '家事サービス', '衣料', '和服', '洋服', 'シャツ・セーター・下着類', '履物類', '他の被服', '被服関連サービス',
       '医薬品・健康保持用摂取品', '保健医療用品・器具', '保健医療サービス', '交通', '自動車等関係費', '通信', '授業料等',
       '教科書・学習参考教材', '補習教育', '教養娯楽用耐久財', '教養娯楽用品', '書籍・他の印刷物', '教養娯楽サービス',
       '理美容サービス', '理美容用品', '身の回り用品', 'たばこ', '他の諸雑費']
top = mid = None
recs = []
for _, m in meta.iterrows():
    if m['name'] == '生鮮食品':  # ここから先は再掲の集計なので止める
        break
    if m['code'].startswith('0'):
        if m['name'] in TOP:
            top, mid = m['name'], None
        if m['name'] in MID:
            mid = m['name']
        continue
    recs.append({'key': m['key'], 'item': m['name'], 'code': m['code'], 'w': m['weight'], 'top': top, 'mid': mid})
items = pd.DataFrame(recs)
W = meta.loc[meta.name == '総合', 'weight'].iloc[0]
OUT['A_item_count'] = int(len(items))
OUT['A_item_weight_share'] = float(items.w.sum() / W)
tot = meta.loc[meta.name == '総合', 'key'].iloc[0]


def contrib(base, end, idx):
    i0 = idx.loc[base, items.key].values
    i1 = idx.loc[end, items.key].values
    T0 = idx.loc[base, tot]
    c = items.w.values * (i1 - i0) / (W * T0) * 100
    out = items.copy()
    out['i0'], out['i1'], out['pp'] = i0, i1, c
    out['chg_pct'] = (i1 / i0 - 1) * 100
    actual = (idx.loc[end, tot] / T0 - 1) * 100
    return out, actual


A, actual = contrib(2020, 2025, ann)
A = A.sort_values('pp', ascending=False)
A.to_csv(os.path.join(R, 'A_item_contrib_2020_2025.csv'), index=False)
OUT['A_total_pct_2020_2025'] = float(actual)
OUT['A_sum_items_pp'] = float(A.pp.sum())
pos = A[A.pp > 0].pp
cum = A.pp.cumsum() / A.pp.sum()
OUT['A_top10_share'] = float(A.pp.head(10).sum() / A.pp.sum())
OUT['A_top20_share'] = float(A.pp.head(20).sum() / A.pp.sum())
OUT['A_n_items_for_50pct'] = int((cum < 0.5).sum() + 1)
OUT['A_n_items_for_80pct'] = int((cum < 0.8).sum() + 1)
OUT['A_n_items_negative'] = int((A.pp < 0).sum())
OUT['A_items_negative_pp'] = float(A[A.pp < 0].pp.sum())
OUT['A_top15'] = A.head(15)[['item', 'top', 'mid', 'chg_pct', 'pp']].round(3).values.tolist()
OUT['A_bottom5'] = A.tail(5)[['item', 'top', 'mid', 'chg_pct', 'pp']].round(3).values.tolist()
bytop = A.groupby('top').pp.sum().sort_values(ascending=False)
bymid = A.groupby('mid').pp.sum().sort_values(ascending=False)
bytop.to_csv(os.path.join(R, 'A_by_top_2020_2025.csv'))
bymid.to_csv(os.path.join(R, 'A_by_mid_2020_2025.csv'))
OUT['A_by_top'] = bytop.round(3).to_dict()
OUT['A_by_mid_top10'] = bymid.head(10).round(3).to_dict()
# 期間を変える（頑健性）
rob = []
for b, e in [(2020, 2025), (2021, 2025), (2020, 2024), (2022, 2025)]:
    x, act = contrib(b, e, ann)
    x = x.sort_values('pp', ascending=False)
    c2 = x.pp.cumsum() / x.pp.sum()
    rob.append({'period': f'{b}-{e}', 'total_pct': act, 'top10_share': x.pp.head(10).sum() / x.pp.sum(),
                'n50': int((c2 < .5).sum() + 1), 'food_share': x[x.top == '食料'].pp.sum() / x.pp.sum(),
                'energy_share': x[x.mid.isin(['電気代', 'ガス代', '他の光熱'])].pp.sum() / x.pp.sum(),
                'top3': '・'.join(x.item.head(3))})
# 月次：2026年1〜9月平均 vs 2021年1〜9月平均
m9 = mon[mon.index.str[4:].astype(int) <= 9].copy()
m9['y'] = m9.index.str[:4].astype(int)
a9 = m9.groupby('y').mean(numeric_only=True)
x, act = contrib(2021, 2026, a9)
x = x.sort_values('pp', ascending=False)
c2 = x.pp.cumsum() / x.pp.sum()
rob.append({'period': '2021-2026(1-9月)', 'total_pct': act, 'top10_share': x.pp.head(10).sum() / x.pp.sum(),
            'n50': int((c2 < .5).sum() + 1), 'food_share': x[x.top == '食料'].pp.sum() / x.pp.sum(),
            'energy_share': x[x.mid.isin(['電気代', 'ガス代', '他の光熱'])].pp.sum() / x.pp.sum(), 'top3': '・'.join(x.item.head(3))})
rob = pd.DataFrame(rob)
rob.to_csv(os.path.join(R, 'A_robust_periods.csv'), index=False)
OUT['A_robust_periods'] = rob.round(3).to_dict(orient='records')

# 財・サービス（公表の分類）
gm = pd.read_csv(os.path.join(D, 'cpi_gs_meta.csv'), dtype={'code': str})
ga = pd.read_csv(os.path.join(D, 'cpi_gs_annual.csv'), index_col=0)
gmo = pd.read_csv(os.path.join(D, 'cpi_gs_monthly.csv'), index_col=0, dtype={'ym': str})
gmo.index = gmo.index.astype(str)
gm['key'] = gm['name'] + '|' + gm['code']


def gkey(name, nth=0):
    return gm[gm.name == name].key.iloc[nth]


GS = {  # 財とサービスの内訳（重複しない組み合わせ）
    '生鮮商品': gkey('生鮮商品'), '他の農水畜産物': gkey('他の農水畜産物'), '食料工業製品': gkey('食料工業製品'),
    '石油製品': gkey('石油製品'), '電気・都市ガス・水道': gkey('電気・都市ガス・水道'), '繊維製品': gkey('繊維製品'),
    '他の工業製品': gkey('他の工業製品'), '出版物': gkey('出版物'),
    '公共サービス': gkey('公共サービス'), '外食': gkey('外食', 0), '民営家賃': gkey('民営家賃'),
    '持家の帰属家賃': gkey('持家の帰属家賃'), '他のサービス': gkey('他のサービス'),
}
wmap = dict(zip(gm.key, gm.weight))
Wg = wmap[gkey('総合')]
OUT['GS_weight_sum_share'] = float(sum(wmap[k] for k in GS.values()) / Wg)
T = gkey('総合')
gsc = {n: wmap[k] * (ga.loc[2025, k] - ga.loc[2020, k]) / (Wg * ga.loc[2020, T]) * 100 for n, k in GS.items()}
OUT['GS_contrib_2020_2025'] = {k: round(v, 3) for k, v in gsc.items()}
OUT['GS_goods_pp'] = float(sum(v for k, v in gsc.items() if k in list(GS)[:8]))
OUT['GS_services_pp'] = float(sum(v for k, v in gsc.items() if k in list(GS)[8:]))
OUT['GS_goods_pct'] = float((ga.loc[2025, gkey('財')] / ga.loc[2020, gkey('財')] - 1) * 100)
OUT['GS_services_pct'] = float((ga.loc[2025, gkey('サービス')] / ga.loc[2020, gkey('サービス')] - 1) * 100)
OUT['GS_goods_weight'] = float(wmap[gkey('財')] / Wg)
# 月次の前年比の寄与（2021年1月〜）
rows = []
idx = list(gmo.index)
for ym in idx:
    if ym < '202101':
        continue
    prev = str(int(ym[:4]) - 1) + ym[4:]
    if prev not in gmo.index:
        continue
    rec = {'ym': ym, 'total_yoy': (gmo.loc[ym, T] / gmo.loc[prev, T] - 1) * 100}
    for n, k in GS.items():
        rec[n] = wmap[k] * (gmo.loc[ym, k] - gmo.loc[prev, k]) / (Wg * gmo.loc[prev, T]) * 100
    rows.append(rec)
gsm = pd.DataFrame(rows)
gsm.to_csv(os.path.join(R, 'A_gs_monthly_yoy_contrib.csv'), index=False)
gsm['goods'] = gsm[list(GS)[:8]].sum(axis=1)
gsm['services'] = gsm[list(GS)[8:]].sum(axis=1)
last = gsm.iloc[-1]
OUT['GS_latest'] = {'ym': last.ym, 'total_yoy': round(last.total_yoy, 2), 'goods_pp': round(last.goods, 2), 'services_pp': round(last.services, 2)}
peak = gsm.loc[gsm.total_yoy.idxmax()]
OUT['GS_peak'] = {'ym': peak.ym, 'total_yoy': round(peak.total_yoy, 2), 'goods_pp': round(peak.goods, 2), 'services_pp': round(peak.services, 2)}
ser_share = gsm.groupby(gsm.ym.str[:4]).apply(lambda g: g.services.sum() / g.total_yoy.sum())
OUT['GS_services_share_by_year'] = ser_share.round(3).to_dict()

# ---------------- B 世帯の区分別の物価 ----------------
hw = pd.read_csv(os.path.join(D, 'hh_weights.csv'))
cpi_key = {m: meta[meta.name == m].key.iloc[0] for m in hw.cpi.dropna().unique() if m}
LAB = {('q5', 'g0'): '平均', ('q5', 'g1'): '第Ⅰ五分位', ('q5', 'g2'): '第Ⅱ五分位', ('q5', 'g3'): '第Ⅲ五分位',
       ('q5', 'g4'): '第Ⅳ五分位', ('q5', 'g5'): '第Ⅴ五分位',
       ('age', 'g0'): '平均', ('age', 'g1'): '29歳以下', ('age', 'g2'): '30〜39歳', ('age', 'g3'): '40〜49歳',
       ('age', 'g4'): '50〜59歳', ('age', 'g5'): '60〜69歳', ('age', 'g6'): '70歳以上'}


def hh_index(wyear, base, end, idxtab=ann, drop=()):
    out = []
    sub = hw[(hw.year == wyear) & (hw.kcode != 'total') & (~hw.cpi.isin(drop))]
    for (tab, g), x in sub.groupby(['tab', 'group']):
        s = x.groupby('cpi').yen.sum()
        s = s / s.sum()
        rel = np.array([idxtab.loc[end, cpi_key[c]] / idxtab.loc[base, cpi_key[c]] for c in s.index])
        out.append({'tab': tab, 'group': g, 'label': LAB[(tab, g)], 'wyear': wyear, 'base': base, 'end': end, 'drop': '・'.join(drop),
                    'pct': (np.dot(s.values, rel) - 1) * 100})
    return pd.DataFrame(out)


B = pd.concat([hh_index(2020, 2020, 2025), hh_index(2025, 2020, 2025), hh_index(2020, 2021, 2025),
               hh_index(2020, 2021, 2026, a9), hh_index(2020, 2020, 2025, drop=('通信',)), hh_index(2020, 2020, 2025, drop=('電気代', 'ガス代', '他の光熱'))])
B['variant'] = B.apply(lambda r: f"重み{r.wyear}・{r.base}→{r.end}" + (f"・{r['drop']}を除く" if r['drop'] else ''), axis=1)
OUT['B_variants'] = {v: {f'{r.tab}:{r.label}': round(r.pct, 2) for r in x.itertuples()} for v, x in B.groupby('variant')}
B.to_csv(os.path.join(R, 'B_household_inflation.csv'), index=False)
main = B[(B.wyear == 2020) & (B.base == 2020) & (B.end == 2025) & (B['drop'] == '')]
OUT['B_main'] = {f"{r.tab}:{r.label}": round(r.pct, 2) for r in main.itertuples()}
cpi_ex = meta[meta.name == '持家の帰属家賃を除く総合'].key.iloc[0]
OUT['B_check_cpi_ex_imputed_rent_2020_2025'] = float((ann.loc[2025, cpi_ex] / ann.loc[2020, cpi_ex] - 1) * 100)
OUT['B_check_cpi_total_2020_2025'] = float(actual)
# 年ごとの道のり
path = []
for e in range(2021, 2026):
    t = hh_index(2020, 2020, e)
    t['year'] = e
    path.append(t)
path = pd.concat(path)
path.to_csv(os.path.join(R, 'B_path_2020w.csv'), index=False)


def gapdec(tab, ga_, gb, wyear=2020, base=2020, end=2025):
    sub = hw[(hw.year == wyear) & (hw.kcode != 'total') & (hw.tab == tab)]
    sa = sub[sub.group == ga_].groupby('cpi').yen.sum(); sa /= sa.sum()
    sb = sub[sub.group == gb].groupby('cpi').yen.sum(); sb /= sb.sum()
    cats = sa.index.union(sb.index)
    rel = pd.Series({c: ann.loc[end, cpi_key[c]] / ann.loc[base, cpi_key[c]] - 1 for c in cats})
    d = (sa.reindex(cats, fill_value=0) - sb.reindex(cats, fill_value=0)) * rel * 100
    return d.sort_values()


gq = gapdec('q5', 'g1', 'g5')
ga_ = gapdec('age', 'g6', 'g1')
gq.to_csv(os.path.join(R, 'B_gap_q1_minus_q5.csv'))
ga_.to_csv(os.path.join(R, 'B_gap_age70_minus_u29.csv'))
OUT['B_gap_q1_q5_total'] = float(gq.sum())
OUT['B_gap_q1_q5_top'] = gq.sort_values(ascending=False).head(5).round(3).to_dict()
OUT['B_gap_q1_q5_bottom'] = gq.head(5).round(3).to_dict()
OUT['B_gap_age_total'] = float(ga_.sum())
OUT['B_gap_age_top'] = ga_.sort_values(ascending=False).head(5).round(3).to_dict()
OUT['B_gap_age_bottom'] = ga_.head(5).round(3).to_dict()
# 円に直す（2025年の消費支出 × 差）
cons25 = hw[(hw.year == 2025) & (hw.kcode == 'total')].set_index(['tab', 'group']).yen
OUT['B_yen_extra'] = {}
for (tab, g), lab in LAB.items():
    r = main[(main.tab == tab) & (main.group == g)]
    if len(r):
        mapped_share = hw[(hw.year == 2020) & (hw.tab == tab) & (hw.group == g) & (hw.kcode != 'total')].yen.sum() / \
            hw[(hw.year == 2020) & (hw.tab == tab) & (hw.group == g) & (hw.kcode == 'total')].yen.sum()
        OUT['B_yen_extra'][f'{tab}:{lab}'] = round(float(cons25[(tab, g)]) * mapped_share * (1 - 1 / (1 + r.pct.iloc[0] / 100)))
# 食料の割合（エンゲル係数に近いもの）と物価の関係
fshare = []
for (tab, g), x in hw[(hw.year == 2020) & (hw.kcode != 'total')].groupby(['tab', 'group']):
    food = x[x.kcode.str.match(r'^1\.\d+$')].yen.sum()
    en = x[x.kcode.isin(['3.1', '3.2', '3.3'])].yen.sum()
    allm = x.yen.sum()
    r = main[(main.tab == tab) & (main.group == g)].pct.iloc[0]
    fshare.append({'tab': tab, 'label': LAB[(tab, g)], 'food_share': food / allm, 'energy_share': en / allm, 'pct': r})
fshare = pd.DataFrame(fshare)
fshare.to_csv(os.path.join(R, 'B_food_energy_share.csv'), index=False)
OUT['B_corr_foodshare_pct'] = float(np.corrcoef(fshare.food_share, fshare.pct)[0, 1])

# ---------------- C 値上げと購入数量 ----------------
p = pd.read_csv(os.path.join(D, 'items_panel_f113.csv'), dtype={'code': str})
p['name'] = p.code.map({'430': '電気代', '432': 'プロパンガス', '433': '灯油'}).fillna(p.name).str.replace(r'\d\)$', '', regex=True)
p = p.sort_values(['code', 'year'])
p['lp'] = np.log(p.price)
p['lq'] = np.log(p.q)
p['dlp'] = p.groupby('code').lp.diff()
p['dlq'] = p.groupby('code').lq.diff()
p['wlag'] = p.groupby('code').exp.shift()
full = p.groupby('code').year.transform('count') == p.year.nunique()
d = p.dropna(subset=['dlp', 'dlq'])
d = d[np.isfinite(d.dlp) & np.isfinite(d.dlq)]
d['energy'] = d.group.eq('光熱')
d['period'] = np.where(d.year >= 2021, 'p2021_24', np.where(d.year <= 2019, 'p2003_19', 'y2020'))
OUT['C_items'] = int(d.code.nunique())
OUT['C_years'] = [int(d.year.min()), int(d.year.max())]


def fe(df, w=True, label=''):
    m = smf.wls('dlq ~ dlp + C(year)', data=df, weights=df.wlag if w else np.ones(len(df))).fit(
        cov_type='cluster', cov_kwds={'groups': df.code})
    return {'label': label, 'b': m.params['dlp'], 'lo': m.conf_int().loc['dlp', 0], 'hi': m.conf_int().loc['dlp', 1],
            'n': int(m.nobs), 'items': int(df.code.nunique())}


CL = []
CL.append(fe(d, True, '全期間（2003〜24年）'))
CL.append(fe(d[d.period == 'p2003_19'], True, '2003〜19年'))
CL.append(fe(d[d.period == 'p2021_24'], True, '2021〜24年'))
CL.append(fe(d, False, '全期間・重みなし'))
CL.append(fe(d[~d.energy], True, '全期間・エネルギーを除く'))
for g, x in d.groupby('group'):
    if x.code.nunique() >= 5:
        CL.append(fe(x, True, f'群:{g}'))
# 2年の差でも
p2 = p.copy()
p2['dlp'] = p2.groupby('code').lp.diff(2)
p2['dlq'] = p2.groupby('code').lq.diff(2)
p2['wlag'] = p2.groupby('code').exp.shift(2)
d2 = p2.dropna(subset=['dlp', 'dlq', 'wlag'])
d2 = d2[(d2.year % 2 == 0)]
CL.append(fe(d2, True, '2年の差（偶数年）'))
CL = pd.DataFrame(CL)
CL.to_csv(os.path.join(R, 'C_elasticity.csv'), index=False)
OUT['C_elasticity'] = CL.round(3).to_dict(orient='records')

# 長い差：2020→2024（品目の横断）
lp = p.pivot(index='code', columns='year', values='lp')
lq = p.pivot(index='code', columns='year', values='lq')
ex = p.pivot(index='code', columns='year', values='exp')
nm = p.drop_duplicates('code').set_index('code')[['name', 'group']]
L = pd.DataFrame({'dlp': lp[2024] - lp[2020], 'dlq': lq[2024] - lq[2020], 'w': ex[2020]}).dropna()
L = L.join(nm)
L['dlp_rel'] = L.dlp - np.average(L.dlp, weights=L.w)
m = smf.wls('dlq ~ dlp', data=L, weights=L.w).fit(cov_type='HC1')
OUT['C_long_2020_2024'] = {'b': m.params['dlp'], 'lo': m.conf_int().loc['dlp', 0], 'hi': m.conf_int().loc['dlp', 1], 'n': int(m.nobs),
                           'corr_w': float(np.corrcoef(L.dlp, L.dlq)[0, 1])}
perm = []
for _ in range(2000):
    s = L.dlq.sample(frac=1, random_state=int(rng.integers(1e9))).values
    perm.append(smf.wls('y ~ dlp', data=L.assign(y=s), weights=L.w).fit().params['dlp'])
perm = np.array(perm)
OUT['C_long_perm_p'] = float((np.abs(perm) >= abs(m.params['dlp'])).mean())
L.sort_values('dlp', ascending=False).to_csv(os.path.join(R, 'C_long_diff_2020_2024.csv'))
L['chg_p'] = (np.exp(L.dlp) - 1) * 100
L['chg_q'] = (np.exp(L.dlq) - 1) * 100
OUT['C_top_price_risers'] = L.sort_values('dlp', ascending=False).head(10)[['name', 'chg_p', 'chg_q']].round(1).values.tolist()
OUT['C_biggest_q_drop'] = L.sort_values('dlq').head(10)[['name', 'chg_p', 'chg_q']].round(1).values.tolist()
hi = L[L.chg_p >= L.chg_p.quantile(0.75)]
lo_ = L[L.chg_p <= L.chg_p.quantile(0.25)]
OUT['C_q_change_top_quartile_price'] = float(np.average(hi.chg_q, weights=hi.w))
OUT['C_q_change_bottom_quartile_price'] = float(np.average(lo_.chg_q, weights=lo_.w))
OUT['C_exp_change_total_pct'] = float((np.exp(L.dlp + L.dlq) * L.w).sum() / L.w.sum() * 100 - 100)
OUT['C_price_change_wavg'] = float((np.exp(L.dlp) * L.w).sum() / L.w.sum() * 100 - 100)
OUT['C_qty_change_wavg'] = float((np.exp(L.dlq) * L.w).sum() / L.w.sum() * 100 - 100)

json.dump(OUT, open(os.path.join(R, 'main.json'), 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(OUT, ensure_ascii=False, indent=1, default=float)[:6000])
