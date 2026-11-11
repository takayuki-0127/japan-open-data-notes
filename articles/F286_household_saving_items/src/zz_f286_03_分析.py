"""F286 分析：支出の変化を 量・物価指数・切り替え に分ける（2020→2025年、二人以上の世帯）。
入力：data/kakei43_long.csv（02 の出力）、data/cpi_items_annual.csv、data/items_panel_f113.csv（いずれも写し）
出力：results/ 以下
"""
import os, json, unicodedata
import numpy as np, pandas as pd

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
os.makedirs('results', exist_ok=True)
N = lambda s: unicodedata.normalize('NFKC', str(s))

d = pd.read_csv('data/kakei43_long.csv', dtype={'code': str})
cpi = pd.read_csv('data/cpi_items_annual.csv').set_index('year')
f113 = pd.read_csv('data/items_panel_f113.csv')

# ---- 対象の品目：購入数量が両年ある個別の品目（集計の行と、2025年に中身が変わった発泡酒は除く）
q = d[d['var'] == 'q']
wq = q[q.grp == 'avg'].pivot_table(index='code', columns='year', values='val', aggfunc='first').dropna()
names20 = q[q.year == 2020].groupby('code').name.first()
names25 = q[q.year == 2025].groupby('code').name.first()
items = [c for c in wq.index
         if c not in ('00000', '3X7') and '-' not in c and ',' not in c
         and (('.' not in c) or c in ('1.1.1', '3.1'))]
BIG = d[d.year == 2020].groupby('code').big.first()
def big(c):
    return BIG.get(c, 'その他')
def _old_big(c):
    if c == '3.1': return '光熱'
    if c.startswith('3X'): return '食料'
    try:
        v = int(c.split('.')[0][:3]) if '.' not in c else int(c.split('.')[0])
    except ValueError:
        return 'その他'
    if c == '1.1.1': return '食料'
    if v < 400: return '食料'
    if 400 <= v < 450: return '住居'
    if 450 <= v < 550: return '家具・家事'
    if 550 <= v < 700: return '被服'
    return 'その他'

# ---- 物価指数との対応
cpicols = {N(c.split('|')[0]): c for c in cpi.columns if not c.split('|')[1].startswith('0')}
MANUAL = {  # 家計調査の品目名 -> 物価指数の品目（複数は対数の平均）
    '米': ['うるち米Ａ', 'うるち米Ｂ'], '牛肉': ['牛肉（国産品）', '牛肉（輸入品）'],
    '豚肉': ['豚肉（国産品）', '豚肉（輸入品）'], 'チーズ': ['チーズ（国産品）', 'チーズ（輸入品）'],
    '即席麺': ['カップ麺'], 'パスタ': ['スパゲッティ'], 'かつお節・削り節': ['かつお節'],
    'マヨネーズ・マヨネーズ風調味料': ['マヨネーズ'], 'ぶどう': ['ぶどうＡ', 'ぶどうＢ'],
    'ワイン': ['ワイン（国産品）', 'ワイン（輸入品）'], 'コーヒー': ['インスタントコーヒー', 'コーヒー豆'],
    '生うどん・そば': ['ゆでうどん'], 'チューハイ・カクテル': ['チューハイ'],
}
def cpi_dln(name, strict=False):
    n = N(name)
    if n in cpicols:
        s = cpi[cpicols[n]]
        return np.log(s[2025] / s[2020]), 'exact'
    if strict or name not in MANUAL:
        return np.nan, None
    v = []
    for m in MANUAL[name]:
        k = cpicols.get(N(m))
        if k is not None:
            v.append(np.log(cpi[k][2025] / cpi[k][2020]))
    return (np.mean(v), 'manual') if v else (np.nan, None)

def panel(grp):
    rows = []
    for c in items:
        g = d[(d.code == c) & (d.grp == grp)]
        get = lambda var, y: g[(g['var'] == var) & (g.year == y)].val.iloc[0]
        try:
            e0, e1, q0, q1, p0, p1 = (get('exp', 2020), get('exp', 2025), get('q', 2020), get('q', 2025),
                                       get('p', 2020), get('p', 2025))
        except IndexError:
            continue
        if not (e0 > 0 and e1 > 0 and q0 > 0 and q1 > 0 and p0 > 0 and p1 > 0):
            continue
        dc, how = cpi_dln(names20[c])
        rows.append(dict(code=c, name=names20[c], name25=names25.get(c, ''), big=big(c), grp=grp,
                         exp20=e0, exp25=e1, dlexp=np.log(e1 / e0), dlq=np.log(q1 / q0),
                         dlp=np.log(p1 / p0), dlcpi=dc, cpimap=how))
    t = pd.DataFrame(rows)
    t['mix'] = t.dlp - t.dlcpi
    t['w'] = t.exp20 / t.exp20.sum()
    return t

P = {g: panel(g) for g in ['avg', 'q1', 'q2', 'q3', 'q4', 'q5']}
A = P['avg']

# ---- 前からの流れ（F113：2015→2020年の量）と 2019 起点
f = f113.copy(); f['nm'] = f.name.map(N)
fq = f.pivot_table(index='nm', columns='year', values='q')
A['nm'] = A.name.map(N)
A['dlq_pre'] = A.nm.map(lambda n: np.log(fq.loc[n, 2020] / fq.loc[n, 2015]) if n in fq.index and fq.loc[n, [2015, 2020]].notna().all() else np.nan)
A['dlq_1924'] = A.nm.map(lambda n: np.log(fq.loc[n, 2024] / fq.loc[n, 2019]) if n in fq.index and fq.loc[n, [2019, 2024]].notna().all() else np.nan)

def wmean(x, w):
    m = x.notna() & w.notna()
    return float((x[m] * w[m]).sum() / w[m].sum()) if m.any() else np.nan

res = {}
def h1(t, label):
    out = dict(n=len(t), wmean_dlq=wmean(t.dlq, t.w))
    hi = t[t.dlcpi >= np.log(1.10)]; lo = t[t.dlcpi < np.log(1.10)]
    out.update(n_hi=len(hi), n_lo=len(lo), wmean_dlq_hi=wmean(hi.dlq, hi.w), wmean_dlq_lo=wmean(lo.dlq, lo.w))
    out['gap_hi_lo'] = out['wmean_dlq_hi'] - out['wmean_dlq_lo']
    out['verdict'] = '支持' if (out['wmean_dlq'] <= -0.03 and out['gap_hi_lo'] <= -0.03) else '外れ'
    return out

res['H1'] = h1(A, 'all')
m = A.dlcpi.notna()
res['H2'] = dict(n_mapped=int(m.sum()), n_exact=int((A.cpimap == 'exact').sum()),
                 wmean_mix=wmean(A.mix[m], A.w[m]), median_mix=float(A.mix[m].median()),
                 wmean_dlcpi=wmean(A.dlcpi[m], A.w[m]), wmean_dlp=wmean(A.dlp[m], A.w[m]))
res['H2']['verdict'] = '支持' if res['H2']['wmean_mix'] <= -0.02 else '外れ'
A['qcontrib'] = A.w * A.dlq
neg = A[A.qcontrib < 0].sort_values('qcontrib')
res['H3'] = dict(n_neg=len(neg), total_neg=float(neg.qcontrib.sum()), top10_share=float(neg.qcontrib.head(10).sum() / neg.qcontrib.sum()),
                 top10=neg.head(10)[['name', 'big', 'dlq', 'w', 'qcontrib']].round(4).to_dict('records'))
res['H3']['verdict'] = '支持' if res['H3']['top10_share'] >= 0.5 else '外れ'
big10 = A[A.dlq <= -0.105]
bp = big10[big10.dlq_pre.notna()]
res['H4'] = dict(n_cut10=len(big10), n_with_pre=len(bp), share_pre_negative=float((bp.dlq_pre < 0).mean()) if len(bp) else np.nan)
res['H4']['verdict'] = '支持' if res['H4']['share_pre_negative'] >= 0.5 else '外れ'
A['saving'] = (A.dlq <= -0.105) & ((A.dlq - A.dlq_pre) <= -0.05)
res['saving_items'] = A[A.saving].sort_values('qcontrib')[['name', 'big', 'dlq', 'dlq_pre', 'dlcpi', 'mix', 'w']].round(3).to_dict('records')
# H5 収入五分位
qq = {}
for g in ['q1', 'q2', 'q3', 'q4', 'q5']:
    t = P[g]
    qq[g] = dict(n=len(t), wmean_dlq=wmean(t.dlq, t.w), wmean_mix=wmean(t.mix[t.dlcpi.notna()], t.w[t.dlcpi.notna()]))
res['H5'] = dict(by_quintile=qq, gap_I_V=qq['q1']['wmean_dlq'] - qq['q5']['wmean_dlq'])
res['H5']['verdict'] = '支持' if res['H5']['gap_I_V'] <= -0.03 else '外れ'

# ---- 大分類別
gb = []
for b, t in A.groupby('big'):
    mm = t.dlcpi.notna()
    gb.append(dict(big=b, n=len(t), w=float(t.w.sum()), wmean_dlexp=wmean(t.dlexp, t.w), wmean_dlq=wmean(t.dlq, t.w),
                   wmean_dlp=wmean(t.dlp, t.w), wmean_dlcpi=wmean(t.dlcpi[mm], t.w[mm]), wmean_mix=wmean(t.mix[mm], t.w[mm])))
res['by_big'] = gb

# ---- 頑健性
hs = d[(d.name == '世帯人員') & (d['var'] == 'exp')].pivot_table(index='grp', columns='year', values='val')
dl_hh = float(np.log(hs.loc['avg', 2025] / hs.loc['avg', 2020]))
R = {}
R['R1_per_person'] = dict(dl_hh=dl_hh, wmean_dlq=res['H1']['wmean_dlq'] - dl_hh,
                          gap_I_V=(qq['q1']['wmean_dlq'] - np.log(hs.loc['q1', 2025] / hs.loc['q1', 2020])) - (qq['q5']['wmean_dlq'] - np.log(hs.loc['q5', 2025] / hs.loc['q5', 2020])))
nr = A[A.name != '米'].copy(); nr['w'] = nr.exp20 / nr.exp20.sum()
R['R2_no_rice'] = h1(nr, 'norice'); mm = nr.dlcpi.notna(); R['R2_no_rice']['wmean_mix'] = wmean(nr.mix[mm], nr.w[mm])
b = A[A.dlq_1924.notna()].copy(); b['w'] = b.exp20 / b.exp20.sum()
R['R3_2019_2024'] = dict(n=len(b), wmean_dlq_1924=wmean(b.dlq_1924, b.w), wmean_dlq_2025same=wmean(b.dlq, b.w))
R['R4_unweighted'] = dict(median_dlq=float(A.dlq.median()), median_mix=float(A.mix.median()),
                          median_gap_hi_lo=float(A[A.dlcpi >= np.log(1.1)].dlq.median() - A[A.dlcpi < np.log(1.1)].dlq.median()))
ex = A[A.cpimap == 'exact']
R['R5_exact_only'] = dict(n=len(ex), wmean_mix=wmean(ex.mix, ex.w))
fo = A[A.big == '食料'].copy(); fo['w'] = fo.exp20 / fo.exp20.sum()
R['R6_food_only'] = h1(fo, 'food'); mm = fo.dlcpi.notna(); R['R6_food_only']['wmean_mix'] = wmean(fo.mix[mm], fo.w[mm])
fo2 = A[A.big == '食料'].copy(); fo2['w'] = fo2.exp20 / fo2.exp20.sum()
R['R6_food_only']['per_person_wmean_dlq'] = R['R6_food_only']['wmean_dlq'] - dl_hh
res['robustness'] = R

# ---- 問い直し（結果を見た後に追加）：コロナの年をはさまずに、前からの流れを引くと量の減りは残るか（食料・F113）
f['nm'] = f.name.map(N)
fq2 = f.pivot_table(index='nm', columns='year', values='q'); fe = f.pivot_table(index='nm', columns='year', values='exp')
fpi = f.pivot_table(index='nm', columns='year', values='price')
food_nm = set(A[A.big == '食料'].nm)
ok = [n for n in fq2.index if n in food_nm and fq2.loc[n, [2014, 2019, 2024]].notna().all() and (fq2.loc[n, [2014, 2019, 2024]] > 0).all()]
rq = pd.DataFrame(dict(nm=ok,
    act=[np.log(fq2.loc[n, 2024] / fq2.loc[n, 2019]) for n in ok],
    trend=[np.log(fq2.loc[n, 2019] / fq2.loc[n, 2014]) for n in ok],
    act_pre=[np.log(fq2.loc[n, 2019] / fq2.loc[n, 2014]) for n in ok],
    pre2=[np.log(fq2.loc[n, 2014] / fq2.loc[n, 2009]) if pd.notna(fq2.loc[n].get(2009)) and fq2.loc[n, 2009] > 0 else np.nan for n in ok],
    dlprice=[np.log(fpi.loc[n, 2024] / fpi.loc[n, 2019]) for n in ok],
    w=[fe.loc[n, 2019] for n in ok]))
rq['w'] = rq.w / rq.w.sum(); rq['excess'] = rq.act - rq.trend
rq['excess_pre'] = rq.act_pre - rq.pre2  # 比べる：2014→2019 の流れからの外れ（2009→2014 を流れとして）
hi = rq.dlprice >= np.log(1.10)
res['reask'] = dict(n=len(rq), wmean_act=wmean(rq.act, rq.w), wmean_trend=wmean(rq.trend, rq.w), wmean_excess=wmean(rq.excess, rq.w),
                    share_excess_neg=float((rq.excess < 0).mean()), wmean_excess_pre=wmean(rq.excess_pre, rq.w),
                    wmean_excess_hi=wmean(rq.excess[hi], rq.w[hi]), wmean_excess_lo=wmean(rq.excess[~hi], rq.w[~hi]),
                    n_hi=int(hi.sum()), n_lo=int((~hi).sum()),
                    corr_dlprice_excess_w=float(np.cov(rq.dlprice, rq.excess, aweights=rq.w)[0, 1] / np.sqrt(float(np.cov(rq.dlprice, aweights=rq.w)) * float(np.cov(rq.excess, aweights=rq.w)))))
# 年ごとの食料の量（重みつき、2019=0）
yrs = list(range(2014, 2025)); ser = []
for y in yrs:
    ser.append(wmean(pd.Series([np.log(fq2.loc[n, y] / fq2.loc[n, 2019]) for n in ok]), rq.w))
res['reask']['food_q_index_vs2019'] = dict(zip(yrs, ser))
rq.to_csv('results/C_reask_food_trend.csv', index=False)
res['hh_size'] = hs.to_dict()

json.dump(res, open('results/main.json', 'w'), ensure_ascii=False, indent=1, default=float)
A.drop(columns=['nm']).to_csv('results/A_items_avg.csv', index=False)
pd.concat(P.values()).to_csv('results/B_items_by_quintile.csv', index=False)
print(json.dumps({k: (v if k in ('H1', 'H2', 'H4', 'H5') else None) for k, v in res.items() if k in ('H1', 'H2', 'H4', 'H5')}, ensure_ascii=False, indent=1, default=float))
print('H3', res['H3']['top10_share'], res['H3']['verdict'])
print(pd.DataFrame(gb).round(3).to_string())
print(json.dumps(R, ensure_ascii=False, indent=1, default=float)); print(json.dumps(res['reask'], ensure_ascii=False, indent=1, default=float))
