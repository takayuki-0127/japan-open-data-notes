"""03 分析：都道府県（46、1955〜2022年度）と市区町村（2005〜2020年度）の所得順位の遷移行列、移動性の指標、定常分布"""
import json, numpy as np, pandas as pd
from scipy.stats import spearmanr
from common import ROOT, SEED, rank_class, level_class, transition, ergodic, mobility, lr_homogeneity
OUT = ROOT / 'results'; OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)
pref = pd.read_csv(ROOT / 'data/pref_panel.csv')
pref47 = pd.read_csv(ROOT / 'data/pref47_panel.csv')
muni = pd.read_csv(ROOT / 'data/muni_panel.csv', dtype={'code': str})
res = {}

def wide(df, val='r', key='code'):
    return df.pivot(index=key, columns='year', values=val)

def pairs(W, step, k, start_lo=None, start_hi=None, mode='rank', cuts=None):
    """W（行＝地域、列＝年）から、start→start+step の区分の組をすべて集める"""
    years = [int(c) for c in W.columns]
    A, B, S = [], [], []
    for t in years:
        if t + step not in years: continue
        if start_lo is not None and t < start_lo: continue
        if start_hi is not None and t > start_hi: continue
        x, y = W[t].to_numpy(), W[t + step].to_numpy()
        ok = ~np.isnan(x) & ~np.isnan(y)
        if mode == 'rank':
            a, b = rank_class(x[ok], k), rank_class(y[ok], k)
        else:
            a, b = level_class(np.exp(x[ok]), cuts), level_class(np.exp(y[ok]), cuts)
        A += list(a); B += list(b); S += [t] * len(a)
    return np.array(A), np.array(B), np.array(S)

def boot_mob(W, step, k, lo, hi, nb=500):
    """地域を復元抽出するブートストラップで Shorrocks の M の区間"""
    idx = np.arange(len(W)); out = []
    for _ in range(nb):
        s = rng.choice(idx, len(idx), replace=True)
        Wb = W.iloc[s].reset_index(drop=True)
        a, b, _ = pairs(Wb, step, k, lo, hi)
        _, P = transition(a, b, k)
        if np.isnan(P).any(): continue
        out.append(mobility(P)['shorrocks'])
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]

Wp = wide(pref); Wpn = wide(pref, 'r_naive'); Wp47 = wide(pref47)
K, STEP = 5, 5
periods = [(1955, 1974, '1955〜79'), (1975, 1994, '1975〜99'), (1995, 2017, '1995〜2022')]

# ---- 1. 都道府県：5年遷移（5分位）全期間と期間別
a, b, s = pairs(Wp, STEP, K)
n_all, P_all = transition(a, b, K)
res['pref_all'] = {'P': P_all.round(3).tolist(), 'n': int(n_all.sum()), **mobility(P_all, STEP)}
cnts = []
res['pref_period'] = {}
for lo, hi, lab in periods:
    a, b, _ = pairs(Wp, STEP, K, lo, hi)
    n, P = transition(a, b, K); cnts.append(n)
    res['pref_period'][lab] = {'P': P.round(3).tolist(), 'n': int(n.sum()), **mobility(P, STEP),
                               'shorrocks_ci': boot_mob(Wp, STEP, K, lo, hi)}
res['pref_homogeneity'] = dict(zip(['lr', 'df', 'p'], lr_homogeneity(cnts)))

# ---- 2. 順位の相関：t と t+h（h＝1〜40年）
def rankcorr(W, hs):
    years = [int(c) for c in W.columns]; out = {}
    for h in hs:
        v = [spearmanr(W[t], W[t + h], nan_policy='omit').statistic for t in years if t + h in years]
        out[h] = float(np.mean(v)) if v else np.nan
    return out
res['pref_rankcorr'] = rankcorr(Wp, range(1, 61))
res['pref_rankcorr_naive'] = rankcorr(Wpn, [5, 10, 20, 40])

# 上位・下位のとどまり方（1955→2022、1975→2022、2000→2022）
def stay_top(W, t0, t1, m):
    r0, r1 = W[t0].rank(ascending=False), W[t1].rank(ascending=False)
    top = set(r0[r0 <= m].index) & set(r1[r1 <= m].index)
    r0b, r1b = W[t0].rank(), W[t1].rank()
    bot = set(r0b[r0b <= m].index) & set(r1b[r1b <= m].index)
    return len(top), len(bot)
res['pref_top_bottom_stay'] = {f'{t0}->{t1}_top{m}': stay_top(Wp, t0, t1, m)
                               for t0, t1 in [(1955, 2022), (1975, 2022), (2000, 2022), (2015, 2022)] for m in [5, 10]}
# 順位の幅（67年で）
rk = Wp.rank(ascending=False)
res['pref_rank_range'] = {'median': float((rk.max(1) - rk.min(1)).median()),
                          'max': float((rk.max(1) - rk.min(1)).max()),
                          'tokyo_ranks': sorted(set(rk.loc[13].astype(int).tolist()))}

# ---- 3. 定常分布（水準の区分：相対所得の境目）
CUTS = [0.85, 0.95, 1.05, 1.15]
res['ergodic'] = {}
for lo, hi, lab in periods + [(1955, 2017, '全期間')]:
    a, b, _ = pairs(Wp, STEP, 5, lo, hi, mode='level', cuts=CUTS)
    n, P = transition(a, b, 5)
    P2 = np.where(np.isnan(P), np.eye(5), P)
    pi = ergodic(P2)
    end = hi + STEP
    cur = np.bincount(level_class(np.exp(Wp[end].dropna()), CUTS), minlength=5) / Wp[end].notna().sum()
    start = np.bincount(level_class(np.exp(Wp[lo].dropna()), CUTS), minlength=5) / Wp[lo].notna().sum()
    res['ergodic'][lab] = {'start_year': lo, 'start': start.round(3).tolist(), 'end_year': end,
                           'end': cur.round(3).tolist(), 'ergodic': pi.round(3).tolist(), 'n': int(n.sum())}

# ---- 4. 市区町村：5年遷移（5分位・10分位）
Wm = wide(muni)
mp = {}
for (t0, t1) in [(2005, 2010), (2010, 2015), (2015, 2020)]:
    sub = Wm[[t0, t1]].dropna()
    for k in [5, 10]:
        n, P = transition(rank_class(sub[t0].to_numpy(), k), rank_class(sub[t1].to_numpy(), k), k)
        mp[f'{t0}->{t1}_k{k}'] = {'P': P.round(3).tolist() if k == 5 else None, 'n': int(n.sum()), **mobility(P, 5)}
res['muni'] = mp
res['muni_rankcorr'] = {f'{t0}->{t1}': float(spearmanr(Wm[t0], Wm[t1], nan_policy='omit').statistic)
                        for t0, t1 in [(2005, 2010), (2010, 2015), (2015, 2020), (2005, 2020), (2005, 2017), (2017, 2020)]}
# 規模別（2015年の納税者数で3つに分け、2015→20 の5分位の「とどまる割合」）
tp = muni[muni.year == 2015].set_index('code').taxpayers
sub = Wm[[2015, 2020]].dropna().join(tp)
sub['size'] = pd.qcut(sub.taxpayers, 3, labels=['小', '中', '大'])
a, b = rank_class(sub[2015].to_numpy(), 5), rank_class(sub[2020].to_numpy(), 5)
sub['stay'] = (a == b); sub['move2'] = np.abs(a - b) >= 2
res['muni_by_size'] = sub.groupby('size', observed=True)[['stay', 'move2']].mean().round(3).to_dict()
# 県内の市区町村と県の比較：同じ2005→2020 の15年で、県（46）の順位相関
res['pref_rankcorr_2005_2020'] = float(spearmanr(Wp[2005], Wp[2020]).statistic)

# ---- 5. 頑健性
rob = []
for k in [3, 4, 5, 6]:
    a, b, _ = pairs(Wp, STEP, k); _, P = transition(a, b, k)
    rob.append({'設定': f'都道府県 {k}区分・5年', **mobility(P, STEP)})
for st in [1, 10, 20]:
    a, b, _ = pairs(Wp, st, K); _, P = transition(a, b, K)
    rob.append({'設定': f'都道府県 5区分・{st}年', **mobility(P, st)})
a, b, _ = pairs(Wpn, STEP, K); _, P = transition(a, b, K)
rob.append({'設定': '都道府県 段差を消さない系列', **mobility(P, STEP)})
a, b, _ = pairs(Wp47, STEP, K); _, P = transition(a, b, K)
rob.append({'設定': '47都道府県（1975年度〜）', **mobility(P, STEP)})
a, b, _ = pairs(Wp.drop(index=13), STEP, K); _, P = transition(a, b, K)
rob.append({'設定': '東京を除く45道府県', **mobility(P, STEP)})
a, b, _ = pairs(Wp, STEP, K, 1975, 2017); _, P = transition(a, b, K)
rob.append({'設定': '都道府県 1975年度〜', **mobility(P, STEP)})
for key in ['2005->2010_k5', '2010->2015_k5', '2015->2020_k5']:
    rob.append({'設定': f'市区町村 {key.replace("_k5","")}', **{k: mp[key][k] for k in ['shorrocks', 'stay', 'lambda2', 'halflife_years']}})
# 市区町村：人口1万人以上だけ
big = muni[(muni.year == 2015) & (muni['pop'] >= 10000)].code
sb = Wm.loc[Wm.index.isin(big), [2015, 2020]].dropna()
_, P = transition(rank_class(sb[2015].to_numpy(), 5), rank_class(sb[2020].to_numpy(), 5), 5)
rob.append({'設定': '市区町村 2015→2020（人口1万人以上）', **mobility(P, 5)})
pd.DataFrame(rob).round(3).to_csv(OUT / 'robustness.csv', index=False)
res['robustness'] = pd.DataFrame(rob).round(3).to_dict('records')

# 期間別・5分位の行列を CSV に
rows = []
for lab, d in [('全期間', res['pref_all'])] + list(res['pref_period'].items()):
    for i, row in enumerate(d['P']):
        rows.append({'期間': lab, '出発の区分': i + 1, **{f'到着{j+1}': v for j, v in enumerate(row)}})
pd.DataFrame(rows).to_csv(OUT / 'transition_pref_5q_5y.csv', index=False)
json.dump(res, open(OUT / 'summary.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: res[k] for k in ['pref_all', 'pref_homogeneity', 'pref_top_bottom_stay', 'pref_rank_range', 'muni_rankcorr', 'muni_by_size', 'pref_rankcorr_2005_2020']}, ensure_ascii=False, default=float))
for lab, d in res['pref_period'].items(): print(lab, {k: d[k] for k in ['shorrocks', 'stay', 'lambda2', 'halflife_years', 'shorrocks_ci', 'n']})
for lab, d in res['ergodic'].items(): print(lab, d)
for key, d in mp.items(): print(key, {k: d[k] for k in ['shorrocks', 'stay', 'n']})
print({h: round(res['pref_rankcorr'][h], 3) for h in [1, 5, 10, 20, 30, 40, 50, 60]}, res['pref_rankcorr_naive'])
print(pd.DataFrame(rob).round(3).to_string())

# ---- 6. マルコフ性の確認：1年の行列を5回かけたもの vs 実際の5年の行列
a, b, _ = pairs(Wp, 1, K); _, P1 = transition(a, b, K)
P1_5 = np.linalg.matrix_power(P1, 5)
res['markov_check'] = {'P1^5_stay': float(np.trace(P1_5) / K), 'P5_stay': res['pref_all']['stay'],
                       'P1^5_shorrocks': mobility(P1_5)['shorrocks'], 'P5_shorrocks': res['pref_all']['shorrocks'],
                       'P1^20_stay': float(np.trace(np.linalg.matrix_power(P1, 20)) / K)}
a, b, _ = pairs(Wp, 20, K); _, P20 = transition(a, b, K)
res['markov_check']['P20_stay'] = float(np.trace(P20) / K)
# 期間の違いの検定：重ならない5年ごとの組だけ（1955,1960,…）
cnts2 = []
for lo, hi, lab in periods:
    A, B = [], []
    for t in range(lo, hi + 1, 5):
        if t + 5 > 2022: continue
        x, y = Wp[t].to_numpy(), Wp[t + 5].to_numpy(); ok = ~np.isnan(x) & ~np.isnan(y)
        A += list(rank_class(x[ok], K)); B += list(rank_class(y[ok], K))
    n, _ = transition(np.array(A), np.array(B), K); cnts2.append(n)
res['pref_homogeneity_nonoverlap'] = dict(zip(['lr', 'df', 'p'], lr_homogeneity(cnts2)))
json.dump(res, open(OUT / 'summary.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(res['markov_check'], res['pref_homogeneity_nonoverlap'])
