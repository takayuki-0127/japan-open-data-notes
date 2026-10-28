# 03_分析：品目別の価格と数量から、いくつもの式で物価指数を作って比べる
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, __import__('os').path.dirname(__file__))
from common import *
rng = np.random.default_rng(113)
d_all = load_panel(); years = list(range(2005, 2025))
# 本体：2005〜2024年の全年がそろう品目（電気代が入る2005年から。固定基準と連鎖を同じ品目で比べる）
_pp, _ = wide(d_all); BAL = _pp.dropna(subset=years).index
d = d_all[d_all.code.isin(BAL)]
FORM = ['L', 'P', 'F', 'T', 'GL', 'J', 'C', 'D']

def all_indices(dd, yrs=None):
    yrs = yrs or years
    p, q = wide(dd)
    full = p.dropna(subset=yrs).index      # 全期間そろう品目（固定基準用）
    pf, qf = p.loc[full], q.loc[full]
    out = {}
    for k in FORM:
        out['fix_' + k] = fixed(pf, qf, yrs[0], yrs, k)
        out['chain_' + k] = chain(p, q, yrs, k)
    out['lowe5'] = lowe_rebased(pf, qf, yrs, bases=(2005, 2010, 2015, 2020))
    return pd.DataFrame(out), len(full), p.shape[0]

res = {}
# 1) 本体：食料＋光熱
main, nfull, nall = all_indices(d)
main.to_csv(P('results/index_main.csv'))
res['n_items_all'] = nall; res['n_items_full'] = nfull

def ann(s, a, b):  # 年率
    return (s[b] / s[a]) ** (1 / (b - a)) - 1

summ = []
for c in main.columns:
    summ.append(dict(index=c, cum_05_24=main[c][2024] / main[c][2005] - 1, ann_05_24=ann(main[c], 2005, 2024),
                     cum_20_24=main[c][2024] / main[c][2020] - 1, ann_20_24=ann(main[c], 2020, 2024),
                     yoy_2023=main[c][2023] / main[c][2022] - 1))
summ = pd.DataFrame(summ); summ.to_csv(P('results/summary_main.csv'), index=False)
print(summ.round(4).to_string())

# 2) 1年ごとの比較（連鎖の年ごとの伸び）
p, q = wide(d)
yy = []
for a, b in zip(years[:-1], years[1:]):
    r = bilateral(p[a], p[b], q[a], q[b]); r['year'] = b; yy.append(r)
yy = pd.DataFrame(yy).set_index('year')
for k in FORM: yy[k] = yy[k] - 1
yy['bias_L_F'] = yy['L'] - yy['F']; yy['bias_L_T'] = yy['L'] - yy['T']
# 価格の上がり方と数量の変わり方の相関（支出ウエイトつき）：負なら「高くなったものを減らした」
cor = []
for a, b in zip(years[:-1], years[1:]):
    m = p[a].notna() & p[b].notna()
    lp = np.log(p[b][m] / p[a][m]); lq = np.log(q[b][m] / q[a][m]); w = (p[a][m] * q[a][m]); w = w / w.sum()
    lpc = lp - (w * lp).sum(); lqc = lq - (w * lq).sum()
    cor.append(((w * lpc * lqc).sum() / np.sqrt((w * lpc ** 2).sum() * (w * lqc ** 2).sum()),
                np.sqrt((w * lpc ** 2).sum())))
yy['corr_dp_dq'] = [c[0] for c in cor]; yy['sd_dlogp'] = [c[1] for c in cor]
yy.to_csv(P('results/yearly_formulas.csv'))
print(yy[['L', 'P', 'F', 'T', 'J', 'C', 'bias_L_F', 'corr_dp_dq', 'sd_dlogp', 'n']].round(4).to_string())
res['bias_mean_LF_pt'] = float(yy.bias_L_F.mean() * 100)
res['bias_mean_LF_pt_2006_2019'] = float(yy.loc[2006:2019].bias_L_F.mean() * 100)
res['bias_mean_LF_pt_2020_2024'] = float(yy.loc[2021:2024].bias_L_F.mean() * 100)
res['corr_bias_sd'] = float(np.corrcoef(yy.bias_L_F, yy.sd_dlogp ** 2)[0, 1])
res['share_negative_corr'] = float((yy.corr_dp_dq < 0).mean())

# 3) 品目を項目ごとに再標本化（ブートストラップ）して、年平均の差 L−F（連鎖）の区間
codes = p.index.values; B = 500; bs = []
for _ in range(B):
    s = rng.choice(codes, len(codes), replace=True)
    pb, qb = p.loc[s].reset_index(drop=True), q.loc[s].reset_index(drop=True)
    diffs = [bilateral(pb[a], pb[b], qb[a], qb[b]) for a, b in zip(years[:-1], years[1:])]
    bs.append(np.mean([x['L'] - x['F'] for x in diffs]) * 100)
res['bias_LF_boot_ci'] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]

# 4) 頑健性：品目の範囲
sets = {
    '食料＋光熱（本体、2005〜2024年にそろう品目）': d,
    '途中で加わった品目も入れる（連鎖のみ意味あり）': d_all,
    '食料だけ': d[d.group != '光熱'],
    '「他の〜」を除く': d[~d.name.str.startswith('他の')],
    '生鮮（魚介・野菜・果物）を除く': d[~d.group.isin(FRESH)],
    '支出の大きい30品目': d[d.code.isin(d[d.year == 2020].nlargest(30, 'exp').code)],
}
rob = []
for nm, dd in sets.items():
    ix, nf, na = all_indices(dd)
    pp, qq = wide(dd)
    pp = pp.loc[pp.dropna(subset=years).index] if nm != '途中で加わった品目も入れる（連鎖のみ意味あり）' else pp; qq = qq.loc[pp.index]
    b = np.mean([bilateral(pp[a], pp[c], qq[a], qq[c])['L'] - bilateral(pp[a], pp[c], qq[a], qq[c])['F'] for a, c in zip(years[:-1], years[1:])]) * 100
    rob.append(dict(set=nm, n=na, n_full=nf, chainL=ix.chain_L[2024] - 1, chainF=ix.chain_F[2024] - 1,
                    fixL=ix.fix_L[2024] - 1, fixP=ix.fix_P[2024] - 1, fixF=ix.fix_F[2024] - 1, lowe5=ix.lowe5[2024] - 1,
                    chainJ=ix.chain_J[2024] - 1, chainC=ix.chain_C[2024] - 1,
                    chainL_20_24=ix.chain_L[2024] / ix.chain_L[2020] - 1, chainF_20_24=ix.chain_F[2024] / ix.chain_F[2020] - 1,
                    bias_LF_pt_per_year=b))
# 2002年から（電気代を除く、2002〜2024年にそろう品目）
y02 = list(range(2002, 2025))
p02, q02 = wide(d_all); keep = p02.dropna(subset=y02).index; p02, q02 = p02.loc[keep], q02.loc[keep]
d02 = d_all[d_all.code.isin(keep)]
ix, nf, na = all_indices(d02, y02)
b02 = np.mean([bilateral(p02[a], p02[c], q02[a], q02[c])['L'] - bilateral(p02[a], p02[c], q02[a], q02[c])['F'] for a, c in zip(y02[:-1], y02[1:])]) * 100
rob.append(dict(set='2002〜2024年（電気代なし）', n=na, n_full=nf, chainL=ix.chain_L[2024] - 1, chainF=ix.chain_F[2024] - 1, fixL=ix.fix_L[2024] - 1,
                fixP=ix.fix_P[2024] - 1, fixF=ix.fix_F[2024] - 1, lowe5=lowe_rebased(p02, q02, y02, bases=(2002, 2005, 2010, 2015, 2020))[2024] - 1,
                chainJ=ix.chain_J[2024] - 1, chainC=ix.chain_C[2024] - 1, chainL_20_24=ix.chain_L[2024] / ix.chain_L[2020] - 1,
                chainF_20_24=ix.chain_F[2024] / ix.chain_F[2020] - 1, bias_LF_pt_per_year=b02))
rob = pd.DataFrame(rob); rob.to_csv(P('results/robust_items.csv'), index=False); print(rob.round(4).to_string())

# 5) 頑健性：基準年（ウエイトの年）を変えて、2020→2024 の上がり方を測る（ロウ指数）
p_all, q_all = wide(d)
bb = []
for base in [2005, 2010, 2015, 2019, 2020, 2022, 2024]:
    m = p_all[[base, 2020, 2024]].notna().all(axis=1)
    pw, qw = p_all[m], q_all[m]
    lowe = (pw[2024] * qw[base]).sum() / (pw[2020] * qw[base]).sum() - 1
    bb.append(dict(weight_year=base, n=int(m.sum()), rise_2020_2024=lowe))
fisher_ref = bilateral(p_all[2020], p_all[2024], q_all[2020], q_all[2024])['F'] - 1
bb = pd.DataFrame(bb); bb['fisher_2020_2024'] = fisher_ref; bb.to_csv(P('results/robust_weight_year.csv'), index=False)
print(bb.round(4).to_string())

# 6) 公表の CPI（類別）との照合：同じ類のなかで 連鎖フィッシャー と CPI の年平均の伸び
cpi = pd.read_csv(P('data/raw/cpi_chubunrui_f12.csv.gz'), dtype=str)
cpi = cpi[cpi['類・品目'].str.fullmatch(r'\d{6}')].copy()
cpi['year'] = cpi['類・品目'].str[:4].astype(int)
grp_map = {'穀類': '穀類', '魚介類': '魚介類', '肉類': '肉類', '乳卵類': '乳卵類', '野菜・海藻': '野菜・海藻', '果物': '果物',
           '油脂・調味料': '油脂・調味料', '飲料': '飲料', '酒類': '酒類', '光熱': 'エネルギー'}
cv = []
for g, col in grp_map.items():
    dd = d[d.group == g]
    if len(dd) == 0: continue
    ix, _, na = all_indices(dd)
    row = dict(group=g, n=na, chainF_ann=ann(ix.chain_F, 2005, 2024), chainL_ann=ann(ix.chain_L, 2005, 2024), fixL_ann=ann(ix.fix_L, 2005, 2024))
    if col:
        a = cpi.groupby('year')[col].apply(lambda s: pd.to_numeric(s, errors='coerce').mean())
        row['cpi_ann'] = ann(a, 2005, 2024)
    cv.append(row)
# 食料全体
ix, _, _ = all_indices(d[d.group != '光熱'])
a = cpi.groupby('year')['食料'].apply(lambda s: pd.to_numeric(s, errors='coerce').mean())
cv.append(dict(group='食料（参考：CPIは外食・調理食品・菓子も含む）', n=d[d.group != '光熱'].code.nunique(), chainF_ann=ann(ix.chain_F, 2005, 2024),
               chainL_ann=ann(ix.chain_L, 2005, 2024), fixL_ann=ann(ix.fix_L, 2005, 2024), cpi_ann=ann(a, 2005, 2024)))
cv = pd.DataFrame(cv); cv.to_csv(P('results/check_vs_cpi.csv'), index=False); print(cv.round(4).to_string())
res['corr_group_cpi'] = float(cv.dropna().iloc[:-1][['chainF_ann', 'cpi_ann']].corr().iloc[0, 1])

# 7) 2002 年の数量で固定したときの品目の寄与：ラスパイレスがフィッシャーより高くなる分を、どの品目が作ったか（2002→2024）
pf, qf = wide(d)
L = (pf[2024] * qf[2005]).sum() / (pf[2005] * qf[2005]).sum(); Pa = (pf[2024] * qf[2024]).sum() / (pf[2005] * qf[2024]).sum()
contrib = pd.DataFrame({'name': d.drop_duplicates('code').set_index('code').name.reindex(pf.index),
                        'price_ratio': pf[2024] / pf[2005], 'qty_ratio': qf[2024] / qf[2005],
                        'share2005': pf[2005] * qf[2005] / (pf[2005] * qf[2005]).sum(),
                        'share2024': pf[2024] * qf[2024] / (pf[2024] * qf[2024]).sum()})
contrib.sort_values('share2005', ascending=False).to_csv(P('results/items_2005_2024.csv'))
res['fixL_05_24'] = float(L - 1); res['fixP_05_24'] = float(Pa - 1)
# 固定基準のずれ（L−P）は基準年から離れるほど広がるか
gap = pd.DataFrame({'h': [y - 2005 for y in years], 'L_minus_P_pt': (main.fix_L - main.fix_P).values * 100, 'L_minus_F_pt': (main.fix_L - main.fix_F).values * 100,
                    'lowe5_minus_chainF_pt': (main.lowe5 - main.chain_F).values * 100, 'fixL_minus_chainF_pt': (main.fix_L - main.chain_F).values * 100}, index=years)
gap.to_csv(P('results/gap_by_horizon.csv')); print(gap.round(2).to_string())
json.dump(res, open(P('results/summary.json'), 'w'), ensure_ascii=False, indent=1); print(res)
