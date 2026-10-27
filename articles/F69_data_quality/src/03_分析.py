"""F69 公的データの「見えにくい欠点」：0 と欠測と秘匿の見分け方
5つの統計表に、同じ点検ルール（R1〜R6）を当てて、何が見つかるかを数える。

R1 記号の検出      ：数値でないセル（-、…、/ など）を数え、どの行・列に集まるかを見る
R2 0 と記号の併存  ：同じ列に 0 と記号の両方があるか（両方あれば、記号は 0 ではない可能性が高い）
R3 合計の一致      ：内訳の合計＝総数 が成り立つか（記号を 0 とみなす／欠測とみなす の2通り）
R4 桁ずれ          ：前の時点からの比が極端（既定 3倍以上・3分の1以下）なセル
R5 単位の妥当範囲  ：単位から計算した値（1人あたり所得など）が、ありうる範囲に入るか
R6 再計算との一致  ：公表されている率を、公表されている実数から計算し直して一致するか
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import *

RES.mkdir(exist_ok=True)
summary = []          # 表×ルール の点検結果
def add(table, rule, checked, flagged, note):
    summary.append(dict(table=table, rule=rule, checked=int(checked), flagged=int(flagged),
                        share=(flagged / checked if checked else np.nan), note=note))

# =============================================================== T1 社会・人口統計体系（市区町村）
s = load_ssds()
T1 = 'T1 社会・人口統計体系（市区町村）'
dash = s[s.raw == '-']
add(T1, 'R1 記号', len(s), len(dash), "記号は '-' の1種類だけ")
# どの項目・年に集まるか
by_item = (dash.groupby(['item', 'label', 'year']).size().rename('n_dash').reset_index()
           .sort_values('n_dash', ascending=False))
by_item.to_csv(RES / 't1_dash_by_item.csv', index=False)
# '-' の市区町村の規模（2020年の総人口）
pop20 = s[(s.year == 2020) & (s.item == 'A1101')].set_index('code').value
ward = s.drop_duplicates('code').set_index('code').name.str.contains('区$') & ~s.drop_duplicates('code').set_index('code').name.str.contains('東京都')
nopop = set(zip(s[(s.item == 'A1101') & (s.raw == '-')].year, s[(s.item == 'A1101') & (s.raw == '-')].code))
dash = dash.assign(noarea=[(y, c) in nopop for y, c in zip(dash.year, dash.code)])
groups = {
    'その時点に区域がない（同じ年の総人口も -）': dash.noarea,
    '住宅・土地統計の対象外（H、2008・2013年）': ~dash.noarea & dash.item.str.startswith('H'),
    '政令市の区など（所得・財政 C・D、2010年以降）': ~dash.noarea & dash.item.str[0].isin(['C', 'D']) & (dash.year >= 2010),
}
groups['それ以外'] = ~(groups[list(groups)[0]] | groups[list(groups)[1]] | groups[list(groups)[2]])
rows = []
for g, m in groups.items():
    codes = dash[m].code.unique()
    rows.append(dict(group=g, cells=int(m.sum()), munis=len(codes),
                     pop_median_2020=float(pop20.reindex(codes).median()),
                     ward_share=float(ward.reindex(codes).mean())))
rows.append(dict(group='（参考）全市区町村', cells=0, munis=int(pop20.notna().sum()),
                 pop_median_2020=float(pop20.median()), ward_share=float(ward.reindex(pop20.index).mean())))
t1_groups = pd.DataFrame(rows); t1_groups.to_csv(RES / 't1_dash_groups.csv', index=False)

# R2：同じ項目×年に 0 と '-' が両方あるか
zz = s.assign(is0=s.value == 0, isd=s.raw == '-').groupby(['item', 'label', 'year'])[['is0', 'isd']].sum()
both = zz[(zz.is0 > 0) & (zz.isd > 0)]
add(T1, 'R2 0と記号の併存', len(zz), len(both), '0 と - が同じ列にある項目×年')
zz.reset_index().to_csv(RES / 't1_zero_vs_dash.csv', index=False)

# R3：男＋女＝総人口、年齢3区分の合計と総人口（差は年齢不詳）
w = s.pivot_table(index=['year', 'code'], columns='item', values='value', aggfunc='first')
chk = w[['A1101', 'A110101', 'A110102']].dropna()
r3a = (chk.A1101 - chk.A110101 - chk.A110102)
add(T1, 'R3 合計（男＋女＝総数）', len(r3a), (r3a != 0).sum(), '一致しない市区町村×年')
age = w[['A1101', 'A1301', 'A1302', 'A1303']].dropna()
gap = age.A1101 - age.A1301 - age.A1302 - age.A1303
gap_share = gap / age.A1101
add(T1, 'R3 合計（年齢3区分＝総数）', len(gap), (gap != 0).sum(), '差＝年齢不詳。総数側が大きい')
t1_agegap = gap_share.groupby(level='year').describe(percentiles=[.5, .9, .99])
t1_agegap.to_csv(RES / 't1_age_unknown_share.csv')
pd.DataFrame({'gap': gap, 'gap_share': gap_share}).reset_index().to_csv(RES / 't1_age_unknown_by_muni.csv', index=False)

# R4：総人口の前回比（5年ごと）
popw = w['A1101'].unstack(0)[[2005, 2010, 2015, 2020]]
rat = pd.concat({f'{a}→{b}': popw[b] / popw[a] for a, b in [(2005, 2010), (2010, 2015), (2015, 2020)]}, axis=1)
jumps = []
for th in [1.5, 2, 3, 5, 10]:
    f = ((rat >= th) | (rat <= 1 / th)).sum().sum()
    jumps.append(dict(threshold=th, flagged=int(f), checked=int(rat.notna().sum().sum())))
t1_jumps = pd.DataFrame(jumps); t1_jumps.to_csv(RES / 't1_population_jumps.csv', index=False)
flag3 = rat[(rat >= 3) | (rat <= 1 / 3)].stack().rename('ratio').reset_index()
flag3.columns = ['code', 'period', 'ratio']
flag3['name'] = flag3.code.map(s.drop_duplicates('code').set_index('code').name)
flag3.to_csv(RES / 't1_population_jumps_3x.csv', index=False)
add(T1, 'R4 桁ずれ（総人口の前回比 3倍・3分の1）', rat.notna().sum().sum(), len(flag3),
    '見つかったのは原発事故後の避難指示区域の町村')

# R5：単位の妥当範囲（課税対象所得【千円】÷納税義務者【人】＝1人あたり所得【千円】）
inc = (w['C120110'] / w['C120120']).dropna()
bad = inc[(inc < 1000) | (inc > 20000)]
add(T1, 'R5 単位（1人あたり所得 100万〜2,000万円）', len(inc), len(bad), '範囲外の市区町村×年')
t1_inc = inc.groupby(level='year').describe()
t1_inc.to_csv(RES / 't1_income_per_taxpayer.csv')
# 単位を読み違えた場合（千円を円とみなす）
t1_unit_demo = pd.DataFrame({'読み方': ['正しい（千円）', '円と読み違えた'],
                             '1人あたり所得の中央値': [inc.median() * 1000, inc.median()]})
t1_unit_demo.to_csv(RES / 't1_unit_misread.csv', index=False)

# '-' を 0 とみなすと、どれだけずれるか（持ち家率と財政力指数）
def share_mean(year, num, den, dash_as_zero):
    a = w.loc[year][num]; b = w.loc[year][den]
    if dash_as_zero:
        a = a.fillna(0); b = b.fillna(0)
        r = (a / b).replace([np.inf, -np.inf], np.nan)
    else:
        r = a / b
    return r.mean(), r.notna().sum()
demo = []
for y in [2008, 2013]:
    m_na, n_na = share_mean(y, 'H1310', 'H1101', False)
    demo.append(dict(item=f'持ち家率 {y}年', 欠測として扱う=m_na, n_欠測=n_na,
                     note='分母も - なので 0 とみなしても計算できない'))
fz = w.loc[2020]['D2201']
demo.append(dict(item='財政力指数 2020年', 欠測として扱う=fz.mean(), n_欠測=int(fz.notna().sum()),
                 ゼロとして扱う=fz.fillna(0).mean(), n_ゼロ=int(fz.fillna(0).notna().sum())))
pd.DataFrame(demo).to_csv(RES / 't1_dash_as_zero_demo.csv', index=False)

# =============================================================== T2 家計調査（長期時系列）
k = load_kakei()
T2 = 'T2 家計調査（二人以上の世帯、月次）'
kv = k.copy()
add(T2, 'R1 記号', len(kv), (kv.value.isna()).sum(), "記号は '-'（増減率の表だけ）")
t2_sym = kv.assign(isna=kv.value.isna()).groupby('kind').isna.agg(['sum', 'count'])
t2_sym.to_csv(RES / 't2_symbols_by_table.csv')
# 記号の位置：先頭の続き／途中／最後
def runs(g):
    na = g.sort_values(['year', 'month']).value.isna().to_numpy()
    if not na.any():
        return pd.Series(dict(lead=0, inner=0, trail=0, all_na=False))
    n = len(na); first = np.argmax(~na) if (~na).any() else n
    last = n - np.argmax(~na[::-1]) if (~na).any() else 0
    lead = first; trail = n - last if (~na).any() else 0
    inner = na[first:last].sum() if (~na).any() else 0
    return pd.Series(dict(lead=lead, inner=inner, trail=trail, all_na=not (~na).any()))
t2_runs = kv[kv.kind != '支出金額'].groupby(['kind', 'item']).apply(runs)
t2_pos = t2_runs.groupby('kind')[['lead', 'inner', 'trail']].sum()
t2_pos['all_na_items'] = t2_runs.groupby('kind').all_na.sum()
t2_pos['items'] = t2_runs.groupby('kind').size()
t2_pos.to_csv(RES / 't2_dash_position.csv')
t2_runs.reset_index().to_csv(RES / 't2_dash_runs_by_item.csv', index=False)
# R6：名目増減率を支出金額から計算し直す（前年同月比）
amt = k[k.kind == '支出金額'].pivot_table(index=['row', 'item'], columns=['year', 'month'], values='value')
nom = k[k.kind == '名目増減率'].pivot_table(index=['row', 'item'], columns=['year', 'month'], values='value')
cols = [c for c in amt.columns if (c[0] - 1, c[1]) in amt.columns]
calc = pd.DataFrame({c: (amt[c] / amt[(c[0] - 1, c[1])] - 1) * 100 for c in cols})
calc.columns = pd.MultiIndex.from_tuples(cols)
common_cols = [c for c in cols if c in nom.columns]
diff = (nom[common_cols] - calc[common_cols]).stack([0, 1]).rename('diff').reset_index()
diff.columns = ['row', 'item', 'year', 'month', 'diff']
diff = diff.dropna()
diff['absdiff'] = diff['diff'].abs()
t2_recalc = diff.groupby('year').absdiff.agg(['count', 'median', lambda x: (x > 0.15).mean()])
t2_recalc.columns = ['n', 'median_absdiff', 'share_over_0.15']
t2_recalc.to_csv(RES / 't2_recalc_by_year.csv')
add(T2, 'R6 再計算（名目増減率）', len(diff), (diff.absdiff > 0.15).sum(),
    '公表の増減率と、実額からの計算の差が 0.15pt 超')
# R4：支出金額の前年同月比が極端
yo = calc.stack([0, 1]).rename('yoy').dropna()
add(T2, 'R4 桁ずれ（前年同月比 3倍・3分の1）', len(yo), ((yo >= 200) | (yo <= -66.7)).sum(), '品目の支出の急変')
big = k[(k.raw.str.contains(',', na=False)) & (k.kind != '支出金額')]
big[['kind', 'item', 'year', 'month', 'raw']].to_csv(RES / 't2_comma_in_rate.csv', index=False)

# =============================================================== T3 感染症発生動向調査（IDWR）
i = load_idwr()
T3 = 'T3 感染症発生動向調査（インフルエンザ定点、週次）'
i['rep'] = i.reports.map(to_num); i['per'] = i.per_sentinel.map(to_num)
i['rep_sym'] = i.reports.map(sym); i['per_sym'] = i.per_sentinel.map(sym)
add(T3, 'R1 記号', 2 * len(i), i.rep_sym.notna().sum() + i.per_sym.notna().sum(), "記号は '-' と '…'")
lit0 = int((i.rep == 0).sum())
add(T3, 'R2 0と記号の併存', len(i), lit0, "報告数が数字の 0 のセル（'-' と同じ列に 0 があるか）")
# R3：都道府県の合計＝総数（'-' を 0 とみなす／欠測とみなす）
pref = i[i.pref != '総数']; tot = i[i.pref == '総数'].set_index('wk').rep.fillna(0)  # 総数の '-' も 0 とみなす
s0 = pref.groupby('wk').rep.apply(lambda x: x.fillna(0).sum())
sn = pref.groupby('wk').rep.apply(lambda x: x.sum(min_count=len(x)))
tot_na = i[i.pref == '総数'].set_index('wk').rep
t3_sum = pd.DataFrame({'total': tot, 'sum_dash0': s0, 'sum_dashNA': sn})
t3_sum['ok_dash0'] = t3_sum.total == t3_sum.sum_dash0
t3_sum['ok_dashNA'] = tot_na.reindex(t3_sum.index) == t3_sum.sum_dashNA
t3_sum.to_csv(RES / 't3_sum_check.csv')
add(T3, 'R3 合計（47都道府県＝総数）', len(t3_sum), (~t3_sum.ok_dash0).sum(), "'-' を 0 とみなしても合わない週")
weeks_with_dash = pref.groupby('wk').rep_sym.apply(lambda x: (x == '-').any())
t3_sumtab = pd.DataFrame({
    '集計': ["'-' を 0 とみなす", "'-' を欠測とみなす"],
    '一致した週': [int(t3_sum.ok_dash0.sum()), int(t3_sum.ok_dashNA.sum())],
    '全週': [len(t3_sum)] * 2,
    "'-' を含む週": [int(weeks_with_dash.sum())] * 2})
t3_sumtab.to_csv(RES / 't3_sum_summary.csv', index=False)
# '…' の行
i[i.rep_sym == '…'][['file', 'week', 'pref', 'reports', 'per_sentinel']].to_csv(RES / 't3_ellipsis_rows.csv', index=False)
# '-' を欠測とみなすと平均がどれだけずれるか（シーズン×都道府県の平均）
i['year'] = i.wk.str[:4].astype(int); i['w'] = i.wk.str[5:7].astype(int)
i['season'] = np.where(i.w >= 36, i.year, i.year - 1)
pp = i[(i.pref != '総数') & (i.season.between(2012, 2025)) & ~i.season.isin([2020, 2021])]
m0 = pp.groupby('season').per.apply(lambda x: x.fillna(0).mean())
mn = pp.groupby('season').per.mean()
t3_demo = pd.DataFrame({'dash_as_0': m0, 'dash_as_NA': mn}); t3_demo['ratio'] = t3_demo.dash_as_NA / t3_demo.dash_as_0
t3_demo.to_csv(RES / 't3_mean_dash_demo.csv')

# =============================================================== T4 人口動態保健所・市区町村別統計
v = load_vital()
T4 = 'T4 人口動態保健所・市区町村別統計（2018〜22年）'
vv = v[v.raw != '']          # 表の右端の空の列は除く
add(T4, 'R1 記号', len(vv), (vv.raw == '…').sum(), "記号は '…' だけ（'-' も 0 もない）")
t4_tab = vv.assign(el=vv.raw == '…', zero=vv.value == 0).groupby('table').agg(
    cells=('raw', 'size'), ellipsis=('el', 'sum'), zeros=('zero', 'sum'),
    min_value=('value', 'min'))
t4_tab.to_csv(RES / 't4_symbols_by_table.csv')
add(T4, 'R2 0と記号の併存', len(vv), int((vv.value == 0).sum()), "数字の 0 は1つもない（0 も '…' で表されている可能性）")
# 行ごとの '…' の数：全部 '…' の行（＝その地域の値がまるごとない）と一部だけの行
d3 = vv[vv.table == '死亡数（第3表）']
per_row = d3.groupby(['area', 'kind']).raw.apply(lambda x: (x == '…').sum()).rename('n_el').reset_index()
ncol = d3.groupby('area').size().max()
per_row['type'] = np.select([per_row.n_el == 0, per_row.n_el == ncol], ['なし', '全部'], '一部')
t4_rows = per_row.groupby(['kind', 'type']).size().unstack(fill_value=0)
t4_rows.to_csv(RES / 't4_rows_by_type.csv')
per_row.to_csv(RES / 't4_ellipsis_by_area.csv', index=False)
# 死亡数の大きさと '…' の関係：その行の総数（男女計）が小さい地域ほど '…' が多いか
tot_d = d3[d3.col.isin([0, 1])].groupby('area').value.sum(min_count=1)
per_row['total_deaths'] = per_row.area.map(tot_d)
m = per_row[(per_row.kind == 'muni') & per_row.total_deaths.notna()]
m['size'] = pd.cut(m.total_deaths, [0, 500, 2000, 10000, 1e9], labels=['500人未満', '500〜2,000人', '2,000〜1万人', '1万人以上'])
t4_size = m.groupby('size', observed=True).n_el.agg(['count', 'mean', lambda x: (x > 0).mean()])
t4_size.columns = ['areas', 'mean_ellipsis_per_row', 'share_rows_with_ellipsis']
t4_size.to_csv(RES / 't4_ellipsis_by_size.csv')

# =============================================================== T5 国勢調査 2020（就業状態、都道府県×男女×各歳）
c = load_census()
T5 = 'T5 国勢調査2020 就業状態等基本集計（都道府県×男女×各歳）'
num = {col: c[col].map(to_num) for col in CENSUS_COLS}
cn = pd.DataFrame(num); cn[['area', 'sex', 'age']] = c[['area', 'sex', 'age']]
nd = sum(c[col].map(sym).eq('-').sum() for col in CENSUS_COLS)
add(T5, 'R1 記号', c[CENSUS_COLS].size, nd, "記号は '-' だけ")
add(T5, 'R2 0と記号の併存', c[CENSUS_COLS].size, int(sum((cn[col] == 0).sum() for col in CENSUS_COLS)),
    "数字の 0 のセル（'-' と同じ列に 0 があるか）")
ident = {
    '総数＝労働力＋非労働力＋不詳': ('総数', ['労働力人口', '非労働力人口', '不詳']),
    '労働力＝就業者＋完全失業者': ('労働力人口', ['就業者', '完全失業者']),
    '就業者＝主に仕事＋家事のほか＋通学のかたわら＋休業者': ('就業者', ['主に仕事', '家事のほか仕事', '通学のかたわら仕事', '休業者']),
    '非労働力＝家事＋通学＋その他': ('非労働力人口', ['家事', '通学', 'その他']),
}
r5 = []
has_dash = c[CENSUS_COLS].apply(lambda col: col.map(sym).eq('-')).any(axis=1)
for nm, (lhs, rhs) in ident.items():
    for mode in ['dash0', 'dashNA']:
        L = cn[lhs] if mode == 'dashNA' else cn[lhs].fillna(0)
        R = cn[rhs].sum(axis=1, min_count=len(rhs)) if mode == 'dashNA' else cn[rhs].fillna(0).sum(axis=1)
        ok = (L - R).abs() < 0.5
        ev = L.notna() & R.notna()
        r5.append(dict(identity=nm, mode=mode, evaluable=int(ev.sum()), ok=int((ok & ev).sum()),
                       rows_with_dash_evaluable=int((ev & has_dash).sum()),
                       rows_with_dash_ok=int((ok & ev & has_dash).sum())))
t5_ident = pd.DataFrame(r5); t5_ident.to_csv(RES / 't5_identity_check.csv', index=False)
n_ok0 = t5_ident[t5_ident['mode'] == 'dash0'].ok.sum(); n_ev0 = t5_ident[t5_ident['mode'] == 'dash0'].evaluable.sum()
add(T5, 'R3 合計（4つの恒等式）', n_ev0, n_ev0 - n_ok0, "'-' を 0 とみなして合わないもの")
# 男＋女＝総数
key = ['area', 'age']
pv = cn.pivot_table(index=key, columns='sex', values='総数', aggfunc='first')
sx = (pv['0_総数'] - pv['1_男'].fillna(0) - pv['2_女'].fillna(0)).abs() < 0.5
add(T5, 'R3 合計（男＋女＝総数）', len(sx), (~sx).sum(), '一致しない都道府県×年齢')
# R6：労働力率＝労働力人口÷（総数−不詳）
lr = 100 * cn['労働力人口'].fillna(0) / (cn['総数'] - cn['不詳'].fillna(0))
d_lr = (lr - cn['労働力率']).abs()
add(T5, 'R6 再計算（労働力率）', int(d_lr.notna().sum()), int((d_lr > 0.001).sum()), '公表の労働力率と、実数からの計算の差が 0.001pt 超')
d_lr2 = (100 * cn['労働力人口'].fillna(0) / cn['総数'] - cn['労働力率']).abs()
t5_lr = pd.DataFrame({'計算のしかた': ['分母から不詳を除く（公表の定義）', '分母に不詳を含める'],
                      '一致（差0.001pt以内）': [int((d_lr <= 0.001).sum()), int((d_lr2 <= 0.001).sum())],
                      '差の中央値（pt）': [float(d_lr.median()), float(d_lr2.median())],
                      '件数': [int(d_lr.notna().sum()), int(d_lr2.notna().sum())]})
t5_lr.to_csv(RES / 't5_lfpr_recalc.csv', index=False)
# '-' が出る場所：どの列・年齢
dpos = pd.DataFrame({col: c[col].map(sym).eq('-') for col in CENSUS_COLS[:-1]})
t5_where = dpos.sum().rename('n_dash'); t5_where.to_csv(RES / 't5_dash_by_column.csv')
agegrp = c.age.str.extract(r'_(\d+)')[0].astype(float)
t5_age = dpos.any(axis=1).groupby(pd.cut(agegrp, [14, 19, 29, 59, 69, 79, 89, 120])).mean()
t5_age.to_csv(RES / 't5_dash_by_age.csv')

# =============================================================== まとめ
summ = pd.DataFrame(summary)
summ.to_csv(RES / 'rulebook_summary.csv', index=False)
print(summ.to_string())
print(t1_groups.to_string()); print(t1_jumps.to_string()); print(flag3.head(20).to_string())
print(t1_agegap.to_string()); print(t1_inc.to_string()); print(pd.read_csv(RES / 't1_dash_as_zero_demo.csv').to_string())
print(t2_sym.to_string()); print(t2_pos.to_string()); print(t2_recalc.to_string()); print(big.head().to_string())
print(t3_sumtab.to_string()); print(t3_demo.to_string()); 
print(t4_tab.to_string()); print(t4_rows.to_string()); print(t4_size.to_string())
print(t5_ident.to_string()); print(t5_lr.to_string()); print(t5_where.to_string()); print(t5_age.to_string())

# =============================================================== 頑健性
rob = []
# 1) 桁ずれの閾値を変える（総人口の前回比）：見つかる区域が避難指示区域以外に広がるか
fuku = {'07542', '07543', '07544', '07545', '07546', '07547', '07548', '07564', '07308', '07211', '07212'}
for th in [1.25, 1.5, 2, 3, 5, 10]:
    f = rat[(rat >= th) | (rat <= 1 / th)].stack()
    codes = set(f.index.get_level_values(0))
    rob.append(dict(check='T1 桁ずれの閾値', setting=f'{th}倍', flagged=len(f), note=f'区域 {len(codes)}、うち福島の避難指示区域以外 {len(codes - fuku)}'))
# 2) 名目増減率の再計算：許す差を変える
for tol in [0.05, 0.1, 0.15, 0.5]:
    rob.append(dict(check='T2 再計算の許容差', setting=f'{tol}pt', flagged=int((diff.absdiff > tol).sum()), note=f'全 {len(diff)} セル'))
# 3) 感染症：定点の定義が変わった 2025年14週の前後で分ける
i2 = t3_sum.copy(); i2['after'] = i2.index >= '2025-14'
for a, g in i2.groupby('after'):
    rob.append(dict(check='T3 合計＝総数（定義変更の前後）', setting='2025年14週以降' if a else '2025年13週まで',
                    flagged=int((~g.ok_dash0).sum()), note=f'全 {len(g)} 週'))
# 4) 人口動態：SMR の表（第6表）の '…' も小さい地域に集まるか
d6 = vv[vv.table == 'SMR（第6表）']
el6 = d6.groupby('area').raw.apply(lambda x: (x == '…').any())
sz = el6.index.map(tot_d)
bins = pd.cut(pd.Series(sz, index=el6.index), [0, 500, 2000, 10000, 1e9])
for b, g in el6.groupby(bins, observed=True):
    rob.append(dict(check="T4 SMR表の '…' がある行", setting=str(b), flagged=int(g.sum()), note=f'全 {len(g)} 行'))
# 5) 国勢調査：許す差を 0 から 1 人に広げても結果は同じか
for tol in [0.5, 1.5]:
    L = cn['総数']; R = cn[['労働力人口', '非労働力人口', '不詳']].fillna(0).sum(axis=1)
    rob.append(dict(check='T5 総数＝内訳（許容差）', setting=f'{tol}人', flagged=int(((L - R).abs() >= tol).sum()), note='全 13,248 行'))
robdf = pd.DataFrame(rob); robdf.to_csv(RES / 'robustness.csv', index=False)
print(robdf.to_string())
