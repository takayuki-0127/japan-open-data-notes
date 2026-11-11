"""07 独立レビューの指摘の検算（結果を見たあとに足したもの）。
出力：results/E_review_checks.json
"""
import os, json, importlib.util, numpy as np, pandas as pd
B = os.path.join(os.path.dirname(__file__), '..'); R = os.path.join(B, 'results')
spec = importlib.util.spec_from_file_location('a', os.path.join(os.path.dirname(__file__), 'zz_f263_03_分析.py'))
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
it, L, pos, YM = a.it, a.L, a.pos, a.YM
FULL = 100 * np.log(110 / 108); k0, h, P = pos['201910'], 3, 24
T, C8, CN = a.sets()
yT, yC8, yCN = a.group(T).values, a.group(C8).values, a.group(CN).values
donors = list(it.index[it.tax.isin(['軽減', '非課税'])]); Dn = L[donors].values
out = {}
calm = list(range(max(pos['201701'], P, 15), k0 - h + 1))
def band(fn, ks):
    v = np.array([fn(k) for k in ks]); return float(np.percentile(v, 5)), float(np.percentile(v, 95))

# 4. 非課税・軽減税率の群の動き（M1、2019年10〜12月）と、非課税から4品目を除いた M5
out['C8_own_M1'] = a.m1(yC8, k0, h); out['CN_own_M1'] = a.m1(yCN, k0, h)
cn_items = {it.loc[c, 'name']: a.m1(L[c].values, k0, h) for c in CN}
out['CN_items_M1'] = {k: round(v, 3) for k, v in cn_items.items()}
drop = ['介護料', '傷害保険料', '火災・地震保険料', '診療代']
CN2 = [c for c in CN if it.loc[c, 'name'] not in drop]
yCN2 = a.group(CN2).values
out['M5_excl4'] = a.m1(yT - yCN2, k0, h); out['M5_excl4_band'] = band(lambda k: a.m1(yT - yCN2, k, h), calm)
out['CN2_own_M1'] = a.m1(yCN2, k0, h)

# 6. プラセボの始まりを誤っていた2018年4月にした場合
old = list(range(pos['201804'], k0 - h + 1))
fns = [lambda k: a.m1(yT, k, h), lambda k: a.m2(yT, k, h), lambda k: a.m3(yT, k, h, P), lambda k: a.m1(yT - yC8, k, h),
       lambda k: a.m1(yT - yCN, k, h), lambda k: a.m6(yT, Dn, k, h, P)[0]]
ob = [band(f, old) for f in fns]; hw = [(q - p) / 2 for p, q in ob]
est = [f(k0) for f in fns]
out['old_window'] = dict(n=len(old), bands=[[round(p, 3), round(q, 3)] for p, q in ob], half=[round(x, 3) for x in hw],
                         M3_outside=bool(not (ob[2][0] <= est[2] <= ob[2][1])), H1_ratio=round(np.mean(hw[:3]) / np.mean(hw[3:]), 3))

# 7. 合成対照の当てはまりと月ごとの差
e6, w = a.m6(yT, Dn, k0, h, P)
pre = slice(k0 - P, k0); post = slice(k0, k0 + 12)
yt = yT[pre] - yT[pre].mean(); synth_pre = (Dn[pre] - Dn[pre].mean(axis=0)) @ w
gap_post = (yT[post] - yT[pre].mean()) - (Dn[post] - Dn[pre].mean(axis=0)) @ w
out['M6'] = dict(n_donors=len(donors), n_weighted=int((w > 1e-4).sum()), pre_rmse=float(np.sqrt(np.mean((yt - synth_pre) ** 2))),
                 pre_sd_T=float(yt.std(ddof=0)), gaps_by_month=[round(x, 3) for x in gap_post[:3]], est=e6)

# 9. 全部転嫁と合うか（推定−目安 が帯の中か）
calm_b = [band(f, calm) for f in fns]
out['full_consistent'] = {m: bool(p <= e - FULL <= q) for m, e, (p, q) in zip(a.METHODS, est, calm_b)}
out['zero_consistent'] = {m: bool(p <= e <= q) for m, e, (p, q) in zip(a.METHODS, est, calm_b)}
out['calm_p5_p95'] = {m: [round(p, 2), round(q, 2)] for m, (p, q) in zip(a.METHODS, calm_b)}
out['est'] = {m: round(e, 3) for m, e in zip(a.METHODS, est)}

# 10. 目安を%（1.85）で比べた場合の H3
out['H3_M1_minus_1.85'] = est[0] - 1.85; out['H3_M1_minus_log'] = est[0] - FULL

# 5. 不足の分け方（M1 と M2）
d = pd.read_csv(os.path.join(R, 'D_item_estimates.csv'), dtype={'code': str})
for m in ['M1', 'M2']:
    x = d[d.method == m]; W = x.weight.sum(); gap = (x.est - FULL) * x.weight / W
    out[f'shortfall_{m}'] = dict(total=float(gap.sum()), energy=float(gap[x.energy].sum()),
                                 energy_items=sorted(x[x.energy].name.tolist()))

# 11. ピザ（配達）を軽減税率に移した場合
it2 = it.copy(); it2.loc[it2.name == 'ピザ（配達）', 'tax'] = '軽減'
T2 = list(it2.index[it2.tax == '標準']); C82 = list(it2.index[it2.tax == '軽減']); D2 = list(it2.index[it2.tax.isin(['軽減', '非課税'])])
w_ = lambda cs: it2.loc[cs, 'weight']
g = lambda cs: (100 * np.log((a.I[cs] * w_(cs).values).sum(axis=1) / w_(cs).sum())).values
yT2, yC82 = g(T2), g(C82)
out['pizza_reduced'] = {m: round(v, 3) for m, v in zip(a.METHODS, [a.m1(yT2, k0, h), a.m2(yT2, k0, h), a.m3(yT2, k0, h, P), a.m1(yT2 - yC82, k0, h), a.m1(yT2 - yCN, k0, h), a.m6(yT2, L[D2].values, k0, h, P)[0]])}
out['pizza_weight_share_T'] = float(it.loc[it.name == 'ピザ（配達）', 'weight'].sum() / it.loc[T, 'weight'].sum())
json.dump(out, open(os.path.join(R, 'E_review_checks.json'), 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
