"""F280 04 図：6枚。"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in f and ('Regular' in f or 'Medium' in f):
        font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['svg.hashsalt'] = 'f280'
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '..', 'data', 'processed'); R = os.path.join(HERE, '..', 'results'); F = os.path.join(HERE, '..', 'figures')
os.makedirs(F, exist_ok=True)
J = json.load(open(os.path.join(R, 'main.json')))
LAB = {'age': '年齢構成', 'in_r': '入院・受診率', 'in_d': '入院・1件当たり日数', 'in_p': '入院・1日当たり',
       'out_r': '入院外・受診率', 'out_d': '入院外・1件当たり日数', 'out_p': '入院外・1日当たり', 'oth': 'その他の種類'}
COL = {'age': '#7a7a7a', 'r': '#4C72B0', 'd': '#55A868', 'p': '#C44E52', 'oth': '#B8A04A'}
META = dict(Software=None)

def save(fig, name):
    fig.savefig(os.path.join(F, name), dpi=150, bbox_inches='tight', metadata=META)
    plt.close(fig)

# 図1：2013→2023年度の分解（千円）
m = J['main']; c = m['contrib']
keys = ['age', 'in_r', 'in_d', 'in_p', 'out_r', 'out_d', 'out_p', 'oth']
vals = [c[k] for k in keys]
cols = [COL['age'], COL['r'], COL['d'], COL['p'], COL['r'], COL['d'], COL['p'], COL['oth']]
fig, ax = plt.subplots(figsize=(8, 4.6))
y = np.arange(len(keys))[::-1]
ax.barh(y, vals, color=cols)
for yi, v in zip(y, vals):
    ax.text(v + (0.8 if v >= 0 else -0.8), yi, f'{v:+.1f}', va='center', ha='left' if v >= 0 else 'right', fontsize=9)
ax.set_yticks(y); ax.set_yticklabels([LAB[k] for k in keys])
ax.axvline(0, color='k', lw=0.8)
ax.set_xlabel('1人当たり医療費の増加への寄与（千円）')
ax.set_title(f"1人当たり医療費は2013→2023年度に{m['C0']/10:.1f}万円→{m['C1']/10:.1f}万円（+{m['growth_pct']:.1f}%）\n増加{m['dC']:.1f}千円の内訳（年ごとにLMDIで分けて足した値）", fontsize=11)
ax.set_xlim(min(vals) - 8, max(vals) + 8)
save(fig, 'fig1_decomposition_2013_2023.png')

# 図2：年ごとの寄与（%ポイント）
yr = pd.read_csv(os.path.join(R, 'A_yearly_contrib.csv'))
C = {int(k): v for k, v in J['C_by_year'].items()}
yr['C0'] = yr.fy.map(lambda y: C[y - 1])
grp = {'年齢構成': ['age'], '受診率': ['in_r', 'out_r'], '1件当たり日数': ['in_d', 'out_d'], '1日当たり医療費': ['in_p', 'out_p'], 'その他の種類': ['oth']}
gc = [COL['age'], COL['r'], COL['d'], COL['p'], COL['oth']]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
pos = np.zeros(len(yr)); neg = np.zeros(len(yr))
for (g, ks), col in zip(grp.items(), gc):
    v = (yr[ks].sum(axis=1) / yr.C0 * 100).values
    ax.bar(yr.fy, np.where(v > 0, v, 0), bottom=pos, color=col, label=g)
    ax.bar(yr.fy, np.where(v < 0, v, 0), bottom=neg, color=col)
    pos += np.where(v > 0, v, 0); neg += np.where(v < 0, v, 0)
tot = yr[keys].sum(axis=1) / yr.C0 * 100
ax.plot(yr.fy, tot, 'k-o', ms=4, label='1人当たり医療費の伸び')
ax.set_ylim(neg.min() - 0.5, pos.max() + 0.5)
ax.axhline(0, color='k', lw=0.8)
ax.set_xticks(yr.fy); ax.set_xticklabels([f'{y}' for y in yr.fy], fontsize=9)
ax.set_ylabel('前年度比への寄与（%ポイント）'); ax.set_xlabel('年度')
ax.set_title('年ごとの伸びの内訳：1日当たり医療費が押し上げ、受診率と日数が押し下げる年が多い', fontsize=11)
ax.legend(fontsize=8, ncol=6, loc='upper center', bbox_to_anchor=(0.5, -0.13))
save(fig, 'fig2_yearly_contrib.png')

# 図3・4：年齢別の三要素（2013と2023年度）
t = pd.read_csv(os.path.join(R, 'C_age_2013_2023.csv'))
ages = list(dict.fromkeys(t.age))
x = np.arange(len(ages))
for k, title, name in [('in', '入院', 'fig3_age_inpatient.png'), ('out', '入院外（調剤を含む）', 'fig4_age_outpatient.png')]:
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, v, lab in zip(axs, ['r', 'd', 'p'], ['受診率（件/人・年）', '1件当たり日数（日）', '1日当たり医療費（千円）']):
        for fy, st in [(2013, '--'), (2023, '-')]:
            s = t[t.fy == fy].set_index('age').reindex(ages)
            ax.plot(x, s[f'{k}_{v}'], st, marker='o', ms=3, label=f'{fy}年度')
        ax.set_title(lab, fontsize=10); ax.set_xticks(x[::2]); ax.set_xticklabels(ages[::2], rotation=60, fontsize=7)
        ax.set_xlabel('年齢（5歳階級）', fontsize=8)
    axs[0].legend(fontsize=8)
    fig.suptitle(f'年齢別の三要素：{title}（2013年度と2023年度）', fontsize=11)
    fig.tight_layout()
    save(fig, name)

# 図5：1日当たり・1件当たり・1人当たり日数の累積と、診療報酬改定等の累積
b = pd.read_csv(os.path.join(R, 'B_daily_cost_vs_revision.csv'))
ra = J['reask']
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot([2013] + list(b.fy), [0] + list(b.p_growth_logpct.cumsum()), 'o-', color=COL['p'], label=f"1日当たり医療費（年齢をそろえた、+{J['H4']['p_growth_logpct']:.1f}）")
ax.plot([2013] + list(b.fy), [0] + list(b.revision_pct.cumsum()), 's--', color='k', label=f"診療報酬改定等の累積（{J['H4']['revision_sum_pct']:.1f}）")
ax.scatter([2023], [ra['per_case']], marker='D', s=60, color='#8172B2', zorder=5, label=f"1件当たり医療費（日数×1日当たり、+{ra['per_case']:.1f}）")
ax.scatter([2023], [ra['days_per_person']], marker='v', s=60, color=COL['d'], zorder=5, label=f"1人当たり受診日数（{ra['days_per_person']:.1f}）")
ax.axhline(0, color='gray', lw=0.6)
ax.set_xlabel('年度'); ax.set_ylabel('2013年度からの累積（対数×100、改定は%の和）')
ax.set_title(f"1日当たり医療費は改定の累積を{J['H4']['gap']:.0f}ポイント上回るが、\n日数が減った分を差し引いた1件当たりでは差は約{ra['per_case_gap']:.0f}ポイント", fontsize=11)
ax.legend(fontsize=8, loc='lower left')
save(fig, 'fig5_daily_cost_vs_revision.png')

# 図6：頑健性
rob = J['robustness']
rows = [('主（2013→2023、LMDI）', m['share_age'], m['share_p_in_within']),
        ('R1 終わり2019年度', rob['R1_end2019']['share_age'], rob['R1_end2019']['share_p_in_within']),
        ('R2 2時点シャープレイ', rob['R2_shapley']['share_age'], rob['R2_shapley']['share_p_in_within']),
        ('R3 10歳階級', rob['R3_10yr']['share_age'], rob['R3_10yr']['share_p_in_within']),
        ('R4b 始め2011年度', rob['R4b_start2011']['share_age'], rob['R4b_start2011']['share_p_in_within']),
        ('R7 終わり2022年度', rob['R7_end2022']['share_age'], rob['R7_end2022']['share_p_in_within'])]
fig, axs = plt.subplots(1, 2, figsize=(10, 4.0), sharey=True)
yy = np.arange(len(rows))[::-1]
axs[0].scatter([r[1] * 100 for r in rows], yy, color=COL['age'], zorder=3)
lo, md, hi = rob['R6_rounding']['share_age']
axs[0].plot([lo * 100, hi * 100], [yy[0], yy[0]], color=COL['age'], lw=6, alpha=0.3)
axs[0].axvline(40, color='r', ls='--', lw=1); axs[0].text(40.3, yy[0] + 0.25, 'H1の基準40%', color='r', fontsize=8)
axs[0].set_xlabel('年齢構成の寄与（伸びに占める%）')
axs[1].scatter([r[2] * 100 for r in rows], yy, color=COL['p'], zorder=3)
lo, md, hi = rob['R6_rounding']['share_p']
axs[1].plot([lo * 100, hi * 100], [yy[0], yy[0]], color=COL['p'], lw=6, alpha=0.3)
axs[1].axvline(100, color='r', ls='--', lw=1); axs[1].text(103, yy[0] + 0.25, 'H2の基準100%', color='r', fontsize=8)
axs[1].set_xlabel('年齢ごとの変化に占める1日当たりの寄与（%）')
axs[0].set_yticks(yy); axs[0].set_yticklabels([r[0] for r in rows], fontsize=9)
sa = [r[1] * 100 for r in rows]
fig.suptitle(f'頑健性：年齢構成の寄与は{min(sa):.0f}〜{max(sa):.0f}%でどれも基準の40%以上。1日当たりの寄与はどの条件でも100%を大きく超える\n（帯は公表値の丸めの幅で値をずらした1,000回の95%範囲）', fontsize=10)
fig.tight_layout()
save(fig, 'fig6_robustness.png')
print('ok')
