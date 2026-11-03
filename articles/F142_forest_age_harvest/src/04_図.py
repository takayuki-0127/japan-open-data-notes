import pandas as pd, numpy as np, json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
B = Path(__file__).resolve().parents[1]; R = B / 'results'; F = B / 'figures'; F.mkdir(exist_ok=True)
f = pd.read_csv(B / 'data' / 'forest_age_class.csv'); res = json.load(open(R / 'summary.json'))
C1, C2, C3, C4 = '#2a6f97', '#c97b2b', '#6a994e', '#9b9b9b'
lab = [f'{k}' for k in range(1, 19)] + ['19+']
t = f[(f.kind == 'area_ha') & (f.species == '人工林計') & (f.pref == '全国')].pivot(index='age_class', columns='year', values='value')

# 図1 齢級別面積 2007 と 2022
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(1, 20); w = 0.4
ax.bar(x - w/2, t[2007] / 1e4, w, color=C4, label='2007年3月末')
ax.bar(x + w/2, t[2022] / 1e4, w, color=C1, label='2022年3月末')
ax.axvspan(10.5, 19.6, color=C2, alpha=0.08); ax.text(15, 160, '11齢級以上（51年生以上）', color=C2, ha='center', fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=9); ax.set_xlabel('齢級（1齢級＝1〜5年生、11齢級＝51〜55年生）')
ax.set_ylabel('面積（万ha）'); ax.set_title('人工林の齢級別の面積：山が15年で3つ右へ動いた', loc='left', fontsize=13)
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(F / 'fig1_age_class_area.png', dpi=150); plt.close()

# 図2 11齢級以上の割合（樹種別）と見通し
fig, ax = plt.subplots(figsize=(8.5, 4.8))
yrs = [2007, 2012, 2017, 2022]
for sp, c in [('人工林計', C1), ('スギ', C3), ('ヒノキ', C2), ('カラマツ', '#7b5ea7')]:
    v = [res['share_mature'][f'{sp}|11'][str(y)] * 100 for y in yrs]
    ax.plot(yrs, v, marker='o', color=c, lw=2.2 if sp == '人工林計' else 1.5, label=sp)
    off = {'カラマツ': 4.5, 'スギ': 2.5, '人工林計': -2.5}.get(sp, 0)
    ax.text(2022.4, v[-1] + off, f'{sp} {v[-1]:.0f}%', color=c, va='center', fontsize=9)
pj = res['projection_share_ge11']
ax.plot([2022, 2027, 2032, 2037], [pj[k] * 100 for k in ['2022', '2027', '2032', '2037']], ls='--', color=C1, lw=1.5)
ax.text(2037, pj['2037'] * 100 + 3, f"見通し {pj['2037']*100:.0f}%\n（2017→22年の\n減り方が続く場合）", color=C1, fontsize=8.5, ha='center')
ax.set_ylim(0, 100); ax.set_xlim(2005, 2041); ax.set_ylabel('人工林の面積に占める割合（%）')
ax.set_title('51年生以上（11齢級以上）の割合：2007年の21%から2022年は64%に', loc='left', fontsize=13)
ax.legend(frameon=False, loc='upper left', fontsize=9); fig.tight_layout(); fig.savefig(F / 'fig2_share_mature.png', dpi=150); plt.close()

# 図3 コホートの残り方
cb = pd.read_csv(R / 'cohort_ratio_planted.csv')
fig, ax = plt.subplots(figsize=(8.5, 4.8))
for per, c in [('2007-2012', C4), ('2012-2017', C2), ('2017-2022', C1)]:
    g = cb[(cb.period == per) & (cb.k >= 2)]
    ax.plot(g.k, g.ratio * 100, marker='o', ms=4, color=c, label=per.replace('-', '→') + '年')
ax.axhline(100, color='k', lw=0.7)
ax.set_xticks(range(2, 19)); ax.set_xticklabels([f'{k}→{k+1}' if k < 18 else '18・19+→19+' for k in range(2, 19)], rotation=60, fontsize=8)
ax.text(2, 81, '1→2齢級は、植えたあとに面積が登録される時期のずれで100%を大きく超えるため省いた', fontsize=8, color='#555')
ax.set_ylim(80, 110); ax.set_xlabel('齢級の移り変わり（5年で1つ上がる）'); ax.set_ylabel('5年後に残った面積の割合（%）')
ax.set_title('同じ世代の森林の5年後：若い世代はほぼ100%、主伐期の世代は少しずつ減る', loc='left', fontsize=12)
ax.legend(frameon=False, fontsize=9); fig.tight_layout(); fig.savefig(F / 'fig3_cohort_ratio.png', dpi=150); plt.close()

# 図4 蓄積の増えと伐採（全国の人工林、年あたり）
sv = pd.DataFrame(res['stock_vs_harvest'])
fig, ax = plt.subplots(figsize=(8.5, 4.8))
xs = np.arange(len(sv))
ax.bar(xs, sv.d_stock_per_yr / 1e3, color=C3, label='蓄積の増え（森林に残った分）')
ax.bar(xs, sv.harvest_standing_per_yr / 1e3, bottom=sv.d_stock_per_yr / 1e3, color=C2, label='伐採（針葉樹の素材生産量÷0.7）')
for i, r in sv.iterrows():
    ax.text(i, (r.gross_growth_per_yr) / 1e3 + 2, f"伐った割合 {r.harvest_share*100:.0f}%", ha='center', fontsize=10)
ax.set_xticks(xs); ax.set_xticklabels([p.replace('-', '→') + '年' for p in sv.period])
ax.set_ylabel('百万m3／年'); ax.set_ylim(0, 120)
ax.set_title('人工林で1年に増えた木の量のうち、伐った割合は21%から37%に', loc='left', fontsize=13)
ax.legend(frameon=False, fontsize=9, loc='upper right'); fig.tight_layout(); fig.savefig(F / 'fig4_stock_vs_harvest.png', dpi=150); plt.close()

# 図5 地方別の伐った割合と、都道府県の散布図（名前は出さない）
pf = pd.read_csv(R / 'prefecture_stock_harvest.csv', index_col=0)
rg = pd.read_csv(R / 'region_stock_harvest.csv', index_col=0).sort_values('harvest_share')
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw=dict(width_ratios=[1, 1.15]))
ax = axs[0]; ax.barh(rg.index, rg.harvest_share * 100, color=C1)
for i, v in enumerate(rg.harvest_share * 100): ax.text(v + 1, i, f'{v:.0f}%', va='center', fontsize=9)
ax.set_xlim(0, 65); ax.set_xlabel('伐った割合（%）'); ax.set_title('地方別（2017→22年の蓄積の増えと2019年の伐採）', loc='left', fontsize=10.5)
ax = axs[1]; q = pf[pf.harvest_share > 0]
ax.scatter(q.share_ge11 * 100, q.harvest_share * 100, s=np.sqrt(q.stock_2022) / 3, color=C2, alpha=0.6, edgecolor='w')
rho = res['pref_rho_mature_vs_harvestshare']
ax.set_xlabel('人工林のうち51年生以上の割合（%、2022年）'); ax.set_ylabel('伐った割合（%）')
ax.set_title(f"都道府県（円の大きさ＝蓄積）　順位相関 {rho['rho']:.2f}（95%区間 {rho['ci'][0]:.2f}〜{rho['ci'][1]:.2f}）", loc='left', fontsize=10)
fig.suptitle('伐った割合は地方で2〜5割と違い、51年生以上が多い県ほど伐っているわけではなかった', x=0.01, ha='left', fontsize=12.5)
fig.tight_layout(); fig.savefig(F / 'fig5_region_pref.png', dpi=150); plt.close()
print('ok')
