"""05 問い直し：品目ごとに見ると、全部転嫁した品目はどれだけあったか（＋頑健性5：品目ごとの推定の中央値）
入力：data/item_class.csv, data/item_logidx.csv.gz
出力：results/D_item_estimates.csv, results/D_item_summary.csv, results/D_item_median.csv
"""
import os, numpy as np, pandas as pd, importlib.util
B = os.path.join(os.path.dirname(__file__), '..'); R = os.path.join(B, 'results')
spec = importlib.util.spec_from_file_location('a', os.path.join(os.path.dirname(__file__), 'zz_f263_03_分析.py'))
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
it, L, pos, YM = a.it, a.L, a.pos, a.YM
FULL = 100 * np.log(110 / 108)
T, C8, CN = a.sets()
yC8, yCN = a.group(C8).values, a.group(CN).values
k0, h, P = pos['201910'], 3, 24
ks = list(range(max(pos['201701'], P, 15), pos['201910'] - h + 1))   # 落ち着いた期間のプラセボ
rows = []
for c in T:
    y = L[c].values
    f = {'M1': lambda k: a.m1(y, k, h), 'M2': lambda k: a.m2(y, k, h), 'M3': lambda k: a.m3(y, k, h, P),
         'M4': lambda k: a.m1(y - yC8, k, h), 'M5': lambda k: a.m1(y - yCN, k, h)}
    for m, fn in f.items():
        est = fn(k0); pl = np.array([fn(k) for k in ks])
        p5, p95 = np.percentile(pl, 5), np.percentile(pl, 95)
        rows.append(dict(code=c, name=it.loc[c, 'name'], weight=it.loc[c, 'weight'], energy=it.loc[c, 'energy'], fresh=it.loc[c, 'fresh'],
                         method=m, est=est, p5=p5, p95=p95, zero_ok=p5 <= est <= p95, full_ok=p5 <= est - FULL <= p95))
d = pd.DataFrame(rows); d.to_csv(os.path.join(R, 'D_item_estimates.csv'), index=False)

def cat(r):
    if r.full_ok and not r.zero_ok: return '全部転嫁と合う（ゼロとは合わない）'
    if r.zero_ok and not r.full_ok: return 'ゼロと合う（全部転嫁とは合わない）'
    if r.zero_ok and r.full_ok: return '両方と合う（区別できない）'
    return '上回る' if r.est - FULL > r.p95 else ('下回る' if r.est < r.p5 else 'その間')
d['cat'] = d.apply(cat, axis=1)
s = d.groupby(['method', 'cat']).agg(n=('code', 'size'), w=('weight', 'sum')).reset_index()
s['w_share'] = s.w / d[d.method == 'M1'].weight.sum()
s.to_csv(os.path.join(R, 'D_item_summary.csv'), index=False)
med = d.groupby('method').agg(median=('est', 'median'), wmean=('est', lambda x: np.average(x, weights=d.loc[x.index, 'weight'])),
                              q25=('est', lambda x: x.quantile(.25)), q75=('est', lambda x: x.quantile(.75)),
                              med_halfband=('p95', lambda x: np.median((x - d.loc[x.index, 'p5']) / 2))).reset_index()
med.to_csv(os.path.join(R, 'D_item_median.csv'), index=False)
pd.set_option('display.width', 200)
print(med.round(3).to_string()); print(s.round(3).to_string())
