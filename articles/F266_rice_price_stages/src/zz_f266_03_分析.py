# 03 分析：PLAN.md の H1〜H4 と頑健性
import pandas as pd, numpy as np, json, os
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
df = pd.read_csv(os.path.join(B, 'data', 'processed', 'monthly_panel.csv'), index_col=0, parse_dates=True)
R = os.path.join(B, 'results'); os.makedirs(R, exist_ok=True)
def build(d, yld=0.90, aitai='aitai_all', retail='tokyo', tax=False):
    o = pd.DataFrame(index=d.index)
    o['aitai_kg'] = d[aitai] / 60 / yld
    if retail == 'tokyo':
        o['retail_kg'] = d['tokyo_koshi_5kg'] / 5
    else:  # 全国CPI（うるち米A）を、2023年平均の東京の円/kgにそろえる
        base = (d['tokyo_koshi_5kg'] / 5).loc['2023'].mean() / d['cpi_rice_a'].loc['2023'].mean()
        o['retail_kg'] = d['cpi_rice_a'] * base
    if tax: o = o / 1.08
    o['margin_kg'] = o['retail_kg'] - o['aitai_kg']; o['ratio'] = o['retail_kg'] / o['aitai_kg']
    o['cgpi'] = d['cgpi_seimai']
    return o
def evaluate(o, base=('2023-01', '2023-12')):
    b = o.loc[base[0]:base[1]].mean()
    p25 = o.loc['2025']
    pk = p25['retail_kg'].idxmax()                      # 店頭の2025年の山の月
    last = o[['aitai_kg', 'retail_kg']].dropna().index.max()  # 両方そろう最新月
    res = {'base_retail_kg': b['retail_kg'], 'base_aitai_kg': b['aitai_kg'], 'base_margin_kg': b['margin_kg'], 'base_ratio': b['ratio'],
           'retail_peak_month': str(pk.date()), 'last_month': str(last.date())}
    for lab, t in [('peak', pk), ('last', last)]:
        r = o.loc[t]; dr = r['retail_kg'] - b['retail_kg']; da = r['aitai_kg'] - b['aitai_kg']
        res.update({f'{lab}_retail_kg': r['retail_kg'], f'{lab}_aitai_kg': r['aitai_kg'], f'{lab}_margin_kg': r['margin_kg'], f'{lab}_ratio': r['ratio'],
                    f'{lab}_d_retail': dr, f'{lab}_d_aitai': da, f'{lab}_share_aitai': da / dr if dr != 0 else np.nan})
    a25 = p25.mean(); dr = a25['retail_kg'] - b['retail_kg']; da = a25['aitai_kg'] - b['aitai_kg']
    res.update({'y2025_share_aitai': da / dr, 'y2025_d_retail': dr, 'y2025_d_aitai': da, 'y2025_ratio': a25['ratio'], 'y2025_margin_kg': a25['margin_kg']})
    res['avg1523_ratio'] = o.loc['2015':'2023', 'ratio'].mean(); res['avg1523_margin_kg'] = o.loc['2015':'2023', 'margin_kg'].mean()
    # H4：各系列の2025年の山（月次の最大）の基準比
    bc = o.loc[base[0]:base[1], 'cgpi'].mean()
    res['rise_aitai_pct'] = (o.loc['2025', 'aitai_kg'].max() / b['aitai_kg'] - 1) * 100
    res['rise_cgpi_pct'] = (o.loc['2025', 'cgpi'].max() / bc - 1) * 100
    res['rise_retail_pct'] = (o.loc['2025', 'retail_kg'].max() / b['retail_kg'] - 1) * 100
    res['rise25avg_aitai_pct'] = (o.loc['2025', 'aitai_kg'].mean() / b['aitai_kg'] - 1) * 100
    res['rise25avg_cgpi_pct'] = (o.loc['2025', 'cgpi'].mean() / bc - 1) * 100
    res['rise25avg_retail_pct'] = (o.loc['2025', 'retail_kg'].mean() / b['retail_kg'] - 1) * 100
    return res
def xcorr(x, y, K=6, start='2010-10', end=None, drop_sep=False):
    """corr(Δlog y_t, Δlog x_{t-k}); k>0 = y（店頭）が x より k か月遅れる。drop_sep=True は x の9月（年産の切り替え）の変化を除く"""
    dx = np.log(x).diff(); dy = np.log(y).diff()
    if drop_sep: dx[dx.index.month == 9] = np.nan
    out = {}
    for k in range(-K, K + 1):
        z = pd.concat([dy, dx.shift(k)], axis=1).loc[start:end].dropna()
        out[k] = z.corr().iat[0, 1] if len(z) > 24 else np.nan
    return pd.Series(out)
main = build(df); RES = {'main': evaluate(main)}
xc = pd.DataFrame({'tokyo_vs_aitai': xcorr(main['aitai_kg'], main['retail_kg']),
                   'cpi_vs_aitai': xcorr(main['aitai_kg'], build(df, retail='cpi')['retail_kg'], start='2015-02'),
                   'cgpi_vs_aitai': xcorr(main['aitai_kg'], main['cgpi']),
                   'tokyo_vs_cgpi': xcorr(main['cgpi'], main['retail_kg']),
                   'tokyo_vs_aitai_pre2024': xcorr(main['aitai_kg'], main['retail_kg'], end='2023-12'),
                   'tokyo_vs_aitai_noSep': xcorr(main['aitai_kg'], main['retail_kg'], drop_sep=True)})  # 結果を見た後で足した確認
xc.index.name = 'lag'; xc.to_csv(os.path.join(R, 'xcorr.csv'))
RES['xcorr_best_lag'] = {c: int(xc[c].idxmax()) for c in xc.columns}; RES['xcorr_best_r'] = {c: float(xc[c].max()) for c in xc.columns}
# 頑健性
rob = {}
for lab, kw, base in [('yield088', dict(yld=0.88), None), ('yield092', dict(yld=0.92), None), ('cpi_national', dict(retail='cpi'), None),
                      ('tax_excl', dict(tax=True), None), ('niigata_koshi', dict(aitai='aitai_niigata_koshi'), None),
                      ('base_2022_23', {}, ('2022-01', '2023-12'))]:
    o = build(df, **kw); rob[lab] = evaluate(o, base) if base else evaluate(o)
RES['robust'] = rob
# 判定
m = RES['main']
RES['verdict'] = {'H1_share_peak>=0.70': bool(m['peak_share_aitai'] >= 0.70), 'H2_lag>=1': bool(RES['xcorr_best_lag']['tokyo_vs_aitai'] >= 1),
                  'H3_peak_ratio<avg1523': bool(m['peak_ratio'] < m['avg1523_ratio']),
                  'H4_aitai>=cgpi>=retail': bool(m['rise_aitai_pct'] >= m['rise_cgpi_pct'] >= m['rise_retail_pct'])}
main.to_csv(os.path.join(B, 'data', 'processed', 'stages_main.csv'))
json.dump(RES, open(os.path.join(R, 'main.json'), 'w'), ensure_ascii=False, indent=1, default=float)
pd.DataFrame({k: v for k, v in rob.items()}).T.to_csv(os.path.join(R, 'robustness.csv'))
print(json.dumps(RES['main'], ensure_ascii=False, indent=0, default=lambda v: round(float(v), 3)))
print(xc.round(3).to_string()); print(RES['verdict'])
print(pd.DataFrame(rob).T[['peak_share_aitai', 'last_share_aitai', 'y2025_share_aitai', 'peak_ratio', 'avg1523_ratio', 'rise_aitai_pct', 'rise_cgpi_pct', 'rise_retail_pct']].round(3).to_string())
