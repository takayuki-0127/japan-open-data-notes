"""03 分析：市区町村の1人あたり所得の格差を、タイル指数で「県の間」と「県の中」に分ける"""
import numpy as np, pandas as pd, json
from common import ROOT, YEARS, SEED, METRO, theil_T, theil_L, gini, decompose

p = pd.read_csv(ROOT / 'data/panel.csv', dtype={'code': str})
R = ROOT / 'results'
out = {}


def frame(df, ycol='inc_tp', wcol='C120120'):
    d = df[[ycol, wcol, 'pref', 'pref_name', 'block', 'code', 'name', 'tokyo23']].dropna().copy()
    d = d.rename(columns={ycol: 'y', wcol: 'w'})
    d = d[(d.y > 0) & (d.w > 0) & np.isfinite(d.y)]
    d['metro'] = np.where(d.pref.isin(METRO), '大都市圏', 'それ以外')
    d['t23'] = np.where(d.tokyo23, '東京23区', 'それ以外')
    return d


def gini_decomp(d, group):
    """ジニ係数の分解：グループ内・グループ間（グループ平均で計算）・重なり（残り）"""
    G = gini(d.y, d.w)
    W = d.w.sum(); Y = (d.w * d.y).sum(); within = 0; gm = []
    for g, x in d.groupby(group):
        pg = x.w.sum() / W; sg = (x.w * x.y).sum() / Y
        within += pg * sg * gini(x.y, x.w)
        gm.append(((x.w * x.y).sum() / x.w.sum(), x.w.sum()))
    gm = np.array(gm)
    between = gini(gm[:, 0], gm[:, 1])
    return {'gini': G, 'within': within, 'between': between, 'overlap': G - within - between}


# 1) 格差の指標の推移（納税者で重みづけ）と、単純な市区町村の数での計算
rows = []
for y in YEARS:
    d = frame(p[p.year == y])
    q = np.quantile(d.y, [0.1, 0.5, 0.9])
    wq = lambda a: np.interp(a, np.cumsum(d.sort_values('y').w) / d.w.sum(), d.sort_values('y').y)
    rows.append({'year': y, 'mean': (d.w * d.y).sum() / d.w.sum(), 'gini_w': gini(d.y, d.w), 'T_w': theil_T(d.y, d.w),
                 'L_w': theil_L(d.y, d.w), 'gini_u': gini(d.y, np.ones(len(d))), 'T_u': theil_T(d.y, np.ones(len(d))),
                 'p90p10_w': wq(0.9) / wq(0.1), 'p90p10_u': q[2] / q[0], 'median_u': q[1], 'max': d.y.max(),
                 'max_name': d.loc[d.y.idxmax(), 'name'], 'n': len(d)})
ind = pd.DataFrame(rows); ind.to_csv(R / 'indicators.csv', index=False, encoding='utf-8')
print(ind.round(4).to_string())

# 2) 分解：県・地方ブロック・大都市圏・東京23区
dec = []
for y in YEARS:
    d = frame(p[p.year == y])
    for grp, lab in [('pref', '都道府県（47）'), ('block', '地方ブロック（8）'), ('metro', '大都市圏かどうか（2）'), ('t23', '東京23区かどうか（2）')]:
        for k in ['T', 'L']:
            r, _ = decompose(d, grp, kind=k)
            dec.append({'year': y, 'group': lab, 'index': k, **r})
dec = pd.DataFrame(dec); dec.to_csv(R / 'decomposition.csv', index=False, encoding='utf-8')
print(dec[dec['index'] == 'T'].round(4).to_string())

# 3) 県ごとの「県の中」の格差と寄与（2005・2020）
pc = []
for y in [2005, 2020]:
    d = frame(p[p.year == y])
    r, g = decompose(d, 'pref_name', kind='T')
    g['year'] = y; g['contrib_share'] = g.within_contrib / r['total']
    pc.append(g)
pc = pd.concat(pc); pc.to_csv(R / 'pref_within.csv', index=False, encoding='utf-8')
w = pc.pivot(index='group', columns='year', values=['inner', 'contrib_share', 'mu'])
print(w.sort_values(('contrib_share', 2020), ascending=False).head(10).round(4))

# 4) 2005→2020 の変化の内訳
a = dec[(dec.group == '都道府県（47）') & (dec['index'] == 'T')].set_index('year')
chg = {'total': a.loc[2020, 'total'] - a.loc[2005, 'total'], 'between': a.loc[2020, 'between'] - a.loc[2005, 'between'],
       'within': a.loc[2020, 'within'] - a.loc[2005, 'within']}
pw = w['contrib_share'].copy(); tot = a['total']
pw = pc.pivot(index='group', columns='year', values='within_contrib'); pw['diff'] = pw[2020] - pw[2005]
chg['within_by_pref_top'] = pw.sort_values('diff', ascending=False).head(5)['diff'].round(5).to_dict()
chg['within_by_pref_bottom'] = pw.sort_values('diff').head(3)['diff'].round(5).to_dict()
out['change_2005_2020'] = chg; print(chg)

# 5) でたらめに47グループに分けたときの「間」の割合（同じ大きさのグループ、500回）
rng = np.random.default_rng(SEED); base = {}
for y in [2005, 2020]:
    d = frame(p[p.year == y]); sizes = d.groupby('pref').size().values; sh = []
    for _ in range(500):
        lab = np.repeat(np.arange(47), sizes); rng.shuffle(lab); d['rg'] = lab
        sh.append(decompose(d, 'rg', kind='T')[0]['between_share'])
    base[y] = {'mean': float(np.mean(sh)), 'p95': float(np.quantile(sh, 0.95)), 'max': float(np.max(sh))}
out['random_groups'] = base; print('random', base)

# 6) 頑健性（2005・2020、県で分けた T の「間」の割合と全体）
def rob(name, df, ycol='inc_tp', wcol='C120120', kind='T', unw=False):
    res = {}
    for y in [2005, 2020]:
        d = frame(df[df.year == y], ycol, wcol)
        if unw: d['w'] = 1.0
        r, _ = decompose(d, 'pref', kind=kind)
        res[y] = r
    return {'setting': name, 'total_2005': res[2005]['total'], 'total_2020': res[2020]['total'],
            'between_share_2005': res[2005]['between_share'], 'between_share_2020': res[2020]['between_share'],
            'within_2005': res[2005]['within'], 'within_2020': res[2020]['within']}

rb = [rob('基本（納税者1人あたり・納税者の重み・T）', p),
      rob('平均対数偏差（L）', p, kind='L'),
      rob('人口1人あたり・人口の重み', p, 'inc_pc', 'A1101'),
      rob('重みなし（市区町村を1つずつ）', p, unw=True),
      rob('東京都を除く', p[p.pref != 13]),
      rob('東京23区を除く', p[~p.tokyo23]),
      rob('所得の上位10市区町村を除く（各年）',
          p[~p.set_index(['year', 'code']).index.isin(
              p.sort_values('inc_tp', ascending=False).groupby('year').head(10).set_index(['year', 'code']).index)]),
      rob('人口1万人未満の町村を除く', p[(p.A1101.isna()) | (p.A1101 >= 1e4)])]
rb = pd.DataFrame(rb); rb.to_csv(R / 'robustness.csv', index=False, encoding='utf-8'); print(rb.round(4).to_string())

# 7) ジニ係数の分解（県）
gd = []
for y in YEARS:
    d = frame(p[p.year == y]); gd.append({'year': y, **gini_decomp(d, 'pref')})
gd = pd.DataFrame(gd); gd.to_csv(R / 'gini_decomposition.csv', index=False, encoding='utf-8'); print(gd.round(4))

# 8) 東京23区のうち所得の高い区の影響：東京都の中の格差のうち23区の中の分
d = frame(p[(p.year == 2020) & (p.pref == 13)]); r, g = decompose(d, 't23', kind='T')
out['tokyo_inner_2020'] = {**r, 'groups': g[['group', 'mu', 'share', 'inner']].round(4).to_dict('records')}
d = frame(p[(p.year == 2005) & (p.pref == 13)]); r, g = decompose(d, 't23', kind='T')
out['tokyo_inner_2005'] = {**r, 'groups': g[['group', 'mu', 'share', 'inner']].round(4).to_dict('records')}
top = p[p.year.isin([2005, 2020])].sort_values('inc_tp', ascending=False).groupby('year').head(5)[['year', 'name', 'inc_tp']]
out['top5'] = top.round(1).to_dict('records')
json.dump(out, open(R / 'summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, default=float)[:3000])
