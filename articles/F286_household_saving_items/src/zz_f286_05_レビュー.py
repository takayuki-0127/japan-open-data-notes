"""F286 独立レビューを受けた追加の計算（区間・ビールを除く・物価指数で値上がりを決めた問い直し・同じ系列の比較など）。
入力：results/（03 の出力）、data/cpi_items_annual.csv、data/items_panel_f113.csv
出力：results/D_review.json
"""
import os, json, unicodedata
import numpy as np, pandas as pd

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
N = lambda s: unicodedata.normalize('NFKC', str(s))
R = json.load(open('results/main.json'))
A = pd.read_csv('results/A_items_avg.csv', dtype={'code': str})
B = pd.read_csv('results/B_items_by_quintile.csv', dtype={'code': str})
C = pd.read_csv('results/C_reask_food_trend.csv')
cpi = pd.read_csv('data/cpi_items_annual.csv').set_index('year')
f = pd.read_csv('data/items_panel_f113.csv'); f['nm'] = f.name.map(N)
fq = f.pivot_table(index='nm', columns='year', values='q')
rng = np.random.default_rng(286)
NB = 5000
out = {}

def wm(x, w):
    return float((x * w).sum() / w.sum())

def wcorr(x, y, w):
    w = w / w.sum(); mx = (x * w).sum(); my = (y * w).sum()
    return float(((x - mx) * (y - my) * w).sum() / np.sqrt(((x - mx) ** 2 * w).sum() * ((y - my) ** 2 * w).sum()))

def reask_stats(t, hi):
    return dict(n=len(t), n_hi=int(hi.sum()), n_lo=int((~hi).sum()), excess=wm(t.excess, t.w),
                hi=wm(t.excess[hi], t.w[hi]), lo=wm(t.excess[~hi], t.w[~hi]),
                gap=wm(t.excess[hi], t.w[hi]) - wm(t.excess[~hi], t.w[~hi]), corr=wcorr(t.x, t.excess, t.w))

def boot(t, thr):
    keys = ['excess', 'gap', 'corr']; bs = {k: [] for k in keys}
    for _ in range(NB):
        s = t.iloc[rng.integers(0, len(t), len(t))]
        hi = s.x >= thr
        if hi.sum() == 0 or (~hi).sum() == 0:
            continue
        r = reask_stats(s, hi)
        for k in keys:
            bs[k].append(r[k])
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in bs.items()}

thr = np.log(1.10)
# 1) 問い直し（平均価格で値上がりを決めた、本文の版）
t = C.copy(); t['x'] = t.dlprice
hi = t.x >= thr
out['reask_avgprice'] = reask_stats(t, hi)
out['reask_avgprice']['ci95_item_bootstrap'] = boot(t, thr)
lo = t[~hi]
beer = lo[lo.nm == 'ビール']
out['reask_avgprice']['beer'] = dict(excess=float(beer.excess.iloc[0]), share_of_lo_weight=float(beer.w.iloc[0] / lo.w.sum()),
                                     dlprice=float(beer.dlprice.iloc[0]))
lo_nb = lo[lo.nm != 'ビール']
out['reask_avgprice']['lo_ex_beer'] = wm(lo_nb.excess, lo_nb.w)
out['reask_avgprice']['gap_ex_beer'] = out['reask_avgprice']['hi'] - out['reask_avgprice']['lo_ex_beer']
out['reask_avgprice']['lo_items'] = lo.sort_values('w', ascending=False)[['nm', 'excess', 'dlprice', 'w']].round(4).to_dict('records')

# 2) 問い直し（物価指数 2019→2024 で値上がりを決めた版）
cpicols = {N(c.split('|')[0]): c for c in cpi.columns if not c.split('|')[1].startswith('0')}
MANUAL = {'米': ['うるち米Ａ', 'うるち米Ｂ'], '牛肉': ['牛肉（国産品）', '牛肉（輸入品）'],
          '豚肉': ['豚肉（国産品）', '豚肉（輸入品）'], 'チーズ': ['チーズ（国産品）', 'チーズ（輸入品）'],
          '即席麺': ['カップ麺'], 'パスタ': ['スパゲッティ'], 'かつお節・削り節': ['かつお節'],
          'マヨネーズ・マヨネーズ風調味料': ['マヨネーズ'], 'ぶどう': ['ぶどうＡ', 'ぶどうＢ'],
          'ワイン': ['ワイン（国産品）', 'ワイン（輸入品）'], 'コーヒー': ['インスタントコーヒー', 'コーヒー豆'],
          '生うどん・そば': ['ゆでうどん'], 'チューハイ・カクテル': ['チューハイ']}
MN = {N(k): v for k, v in MANUAL.items()}
def cpi1924(n):
    if n in cpicols:
        s = cpi[cpicols[n]]
        return np.log(s[2024] / s[2019]) if pd.notna(s.get(2019)) and pd.notna(s.get(2024)) else np.nan
    if n in MN:
        v = [np.log(cpi[cpicols[N(m)]][2024] / cpi[cpicols[N(m)]][2019]) for m in MN[n] if N(m) in cpicols]
        v = [x for x in v if pd.notna(x)]
        return float(np.mean(v)) if v else np.nan
    return np.nan
t2 = C.copy(); t2['x'] = t2.nm.map(cpi1924); t2 = t2[t2.x.notna()].copy(); t2['w'] = t2.w / t2.w.sum()
hi2 = t2.x >= thr
out['reask_cpi'] = reask_stats(t2, hi2)
out['reask_cpi']['ci95_item_bootstrap'] = boot(t2, thr)

# 3) 同じ系列（F113）での 2020→2024 と 2019→2024（食料121品目、2019年の支出で重み）
idx = {int(k): v for k, v in R['reask']['food_q_index_vs2019'].items()}
out['same_series'] = dict(dl_2019_2024=idx[2024], dl_2020_2024=idx[2024] - idx[2020], peak_2020=idx[2020],
                          peak_share=idx[2020] / (idx[2020] - idx[2024]), ratio=(idx[2020] - idx[2024]) / (-idx[2024]))
# 頑健性 R3（124品目・2020年の重み）と §6（121品目・2019年の重み）
out['R3_vs_s6'] = dict(R3_n=R['robustness']['R3_2019_2024']['n'], R3=R['robustness']['R3_2019_2024']['wmean_dlq_1924'],
                       s6_n=R['reask']['n'], s6=R['reask']['wmean_act'])

# 4) 五分位Ⅰの切り替えと品目数、食料の H1 の差（対数）
q = R['H5']['by_quintile']
out['quintile'] = {g: dict(n=q[g]['n'], dlq=q[g]['wmean_dlq'], mix=q[g]['wmean_mix']) for g in q}
fo = R['robustness']['R6_food_only']
out['food_h1'] = dict(n_hi=fo['n_hi'], n_lo=fo['n_lo'], hi=fo['wmean_dlq_hi'], lo=fo['wmean_dlq_lo'], gap_log=fo['gap_hi_lo'])
out['R4_median_gap_log'] = R['robustness']['R4_unweighted']['median_gap_hi_lo']

# 5) 手で対応した13品目、名前一致だけの切り替え
man = A[A.cpimap == 'manual']
out['manual_items'] = man[['name', 'dlcpi', 'mix']].round(4).to_dict('records')
out['n_exact'] = int((A.cpimap == 'exact').sum()); out['n_manual'] = len(man)
out['R5_exact_mix'] = R['robustness']['R5_exact_only']['wmean_mix']; out['H2_mix'] = R['H2']['wmean_mix']

# 6) 図2の表に出していない大分類の重み、§2 で H1 の各群にいる大きい品目
bb = pd.DataFrame(R['by_big'])
shown = ['食料', '光熱・水道', '交通・通信', '住居']
out['other_big_weight'] = float(bb[~bb.big.isin(shown)].w.sum())
out['big_items'] = A.sort_values('w', ascending=False).head(6)[['name', 'w', 'dlq', 'dlcpi']].round(4).to_dict('records')

# 7) 問い直しの全体の量の減り（−8.0%）の区間（品目の再抽出）
bs = []
for _ in range(NB):
    s = C.iloc[rng.integers(0, len(C), len(C))]
    bs.append(wm(s.act, s.w))
out['reask_act_ci'] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]

json.dump(out, open('results/D_review.json', 'w'), ensure_ascii=False, indent=1, default=float)
pc = lambda v: round((np.exp(v) - 1) * 100, 1)
ra, rc = out['reask_avgprice'], out['reask_cpi']
print('avgprice', {k: round(v * 100, 1) if isinstance(v, float) else v for k, v in ra.items() if k not in ('lo_items', 'beer', 'ci95_item_bootstrap')})
print(' ci', {k: [round(x * 100, 1) if k != 'corr' else round(x, 2) for x in v] for k, v in ra['ci95_item_bootstrap'].items()}, 'beer', ra['beer'])
print('cpi', {k: round(v * 100, 1) if isinstance(v, float) else v for k, v in rc.items() if k != 'ci95_item_bootstrap'})
print(' ci', {k: [round(x * 100, 1) if k != 'corr' else round(x, 2) for x in v] for k, v in rc['ci95_item_bootstrap'].items()})
print('same', {k: round(v, 4) for k, v in out['same_series'].items()}, pc(out['same_series']['dl_2020_2024']))
print('R3vs6', out['R3_vs_s6'])
print('quint', out['quintile']); print('food', out['food_h1'], 'R4', out['R4_median_gap_log'])
print('manual', out['n_exact'], out['n_manual'], [m['name'] for m in out['manual_items']], out['R5_exact_mix'], out['H2_mix'])
print('other', out['other_big_weight'], out['big_items']); print('actci', out['reask_act_ci'])
print('lo items', ra['lo_items'])
