"""04 図：6枚（figures/）"""
import json, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

R = ROOT / 'results'; F = ROOT / 'figures'
d = make_data(); d = d[d[Y] > 0]; d['欠測'] = d[FOCUS].isna().astype(int)
pat = pd.read_csv(R / 'missing_by_pop.csv'); comp = pd.read_csv(R / 'missing_compare.csv', index_col=0)
cm = pd.read_csv(R / 'coef_methods.csv'); imp = pd.read_csv(R / 'imputed_values.csv')
sim = pd.read_csv(R / 'sim_summary.csv'); rate = pd.read_csv(R / 'sim_rate_summary.csv')
rob = pd.read_csv(R / 'robustness.csv'); S = json.load(open(R / 'summary.json', encoding='utf-8'))
METH = ['完全ケース', '平均で埋める', '回帰で1回埋める', '多重代入（結果も使う）', '多重代入（結果を使わない）']
COL = {'完全ケース': '#555555', '平均で埋める': '#d9822b', '回帰で1回埋める': '#c9a227',
       '多重代入（結果も使う）': '#2b6cb0', '多重代入（結果を使わない）': '#8fb3dc'}

# 1 どんな町で欠けるか
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={'width_ratios': [1, 1.15]})
ax = axes[0]
ax.bar(pat['人口区分'], pat['欠測の割合'] * 100, color='#9fbfe0')
for i, r in pat.iterrows():
    ax.text(i, r['欠測の割合'] * 100 + 2, f"{r['欠測の割合']*100:.0f}%\n({r['市区町村']})", ha='center', fontsize=8.5)
ax.set_ylim(0, 118); ax.set_ylabel('持ち家率が欠けている割合（%）'); ax.set_xlabel('人口（2015年）')
ax.set_title('持ち家率（住宅・土地統計調査 2013年）は、小さい町村で欠ける', fontsize=11)
ax.tick_params(axis='x', labelsize=8.5)
ax = axes[1]
std = d[[Y] + XFULL].std()
z = ((comp['値がない'] - comp['値がある']) / std.reindex(comp.index)).dropna()
z = z.reindex([Y] + XFULL)
ax.barh(range(len(z))[::-1], z.values, color=['#2b6cb0' if v > 0 else '#d9822b' for v in z.values])
ax.set_yticks(range(len(z))[::-1]); ax.set_yticklabels(z.index, fontsize=9)
ax.axvline(0, color='#333', lw=0.7)
ax.set_xlabel('値がない町 − 値がある町（標準偏差の単位）')
ax.set_title('欠けている町は、高齢化が進み、農業が多く、人口密度が低い', fontsize=11)
fig.tight_layout(); fig.savefig(F / 'f41_missing.png', dpi=150); plt.close(fig)

# 2 欠けている町の持ち家率を埋めた値（人口との関係）
fig, ax = plt.subplots(figsize=(8.6, 5))
obs = d[d['欠測'] == 0]
ax.scatter(np.log10(obs['人口']), obs['持ち家率'], s=7, color='#555555', alpha=0.5, label=f'値がある町（{len(obs):,}）')
mis = d[d['欠測'] == 1]
one = imp[imp.set == 0]
ax.scatter(np.log10(mis['人口'].values), one['持ち家率'].values, s=7, color='#2b6cb0', alpha=0.6,
           label=f'値がない町に埋めた値（{len(mis):,}、20組のうち1組目）')
ax.axhline(100, color='#c33', lw=0.8, ls='--'); ax.text(2.3, 101, '100%', color='#c33', fontsize=8.5)
ax.set_xticks([2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6]); ax.set_xticklabels(['300', '1千', '3千', '1万', '3万', '10万', '30万', '100万'])
ax.set_xlabel('人口（2015年、対数目盛）'); ax.set_ylabel('持ち家率（%）')
ax.set_title('値がない町は人口1.5万人未満に集中。埋めた値は、ほぼ「外挿」になる', fontsize=11)
ax.legend(fontsize=9, loc='upper right')
fig.tight_layout(); fig.savefig(F / 'f41_imputed.png', dpi=150); plt.close(fig)

# 3 実データで、扱い方ごとの係数
fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
for ax, v in zip(axes, ['持ち家率', '65歳以上の割合', '第1次産業の割合']):
    s = cm[cm['var'] == v].set_index('method').reindex(METH)
    y = np.arange(len(METH))[::-1]
    ax.errorbar(s['coef'], y, xerr=[s['coef'] - s['lo'], s['hi'] - s['coef']], fmt='none', ecolor='#999', capsize=3)
    ax.scatter(s['coef'], y, c=[COL[m] for m in METH], s=45, zorder=3)
    ax.axvline(0, color='#333', lw=0.6)
    ax.set_title(f'{v}（10ポイントあたり）', fontsize=11)
    ax.set_xlabel('子ども女性比の差（女性1,000人あたり）')
axes[0].set_yticks(np.arange(len(METH))[::-1])
axes[0].set_yticklabels([f"{m}（{int(cm[(cm.method == m)].n.iloc[0]):,}）" for m in METH], fontsize=9)
fig.suptitle('同じデータでも、欠測の扱い方で係数は変わる（点と95%区間、かっこ内は使った町の数）', fontsize=12)
fig.tight_layout(); fig.savefig(F / 'f41_methods.png', dpi=150); plt.close(fig)

# 4 わざと欠かせた実験：偏りとカバー率
KINDS = ['MCAR', 'MAR（結果で欠ける）', 'MAR（人口で欠ける）', 'MNAR（持ち家率で欠ける）']
KL = ['でたらめに欠ける\n（MCAR）', '子どもが多い町ほど\n欠ける（MAR）', '小さい町ほど\n欠ける（MAR）', '持ち家率が高い町ほど\n欠ける（MNAR）']
fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
w = 0.16
for j, m in enumerate(METH):
    s = sim[sim.method == m].set_index('kind').reindex(KINDS)
    x = np.arange(len(KINDS)) + (j - 2) * w
    axes[0].bar(x, s['偏り'], w, color=COL[m], label=m)
    axes[0].errorbar(x, s['偏り'], yerr=s['標準偏差'], fmt='none', ecolor='#333', lw=0.8, capsize=2)
    axes[1].bar(x, s['RMSE'], w, color=COL[m])
axes[0].axhline(0, color='#333', lw=0.7)
axes[0].set_xticks(range(len(KINDS))); axes[0].set_xticklabels(KL, fontsize=9)
axes[0].set_ylabel('偏り（推定の平均 − 真の値）'); axes[0].set_title(f'持ち家率の係数の偏り（真の値 {S["truth_full_owner_per10"]:.1f}、線は推定のばらつき）', fontsize=11)
axes[0].legend(fontsize=8.5, loc='upper left')
axes[1].set_xticks(range(len(KINDS))); axes[1].set_xticklabels(KL, fontsize=9)
axes[1].set_ylabel('RMSE（偏りとばらつきを合わせた外れ方）')
axes[1].set_title('真の値からの外れ方（小さいほどよい）', fontsize=11)
fig.suptitle(f'値がそろっている{S["n"] - S["n_missing"]:,}の町で、35%をわざと欠かせて比べた（各100回）', fontsize=12)
fig.tight_layout(); fig.savefig(F / 'f41_sim.png', dpi=150); plt.close(fig)

# 5 欠測率を変える（小さい町ほど欠ける場合）
fig, ax = plt.subplots(figsize=(7.6, 4.6))
for m in ['完全ケース', '多重代入（結果も使う）']:
    s = rate[rate.method == m]
    ax.plot(s['rate'] * 100, s['偏り'], 'o-', color=COL[m], label=f'{m}：偏り')
    ax.fill_between(s['rate'] * 100, s['偏り'] - s['標準偏差'], s['偏り'] + s['標準偏差'], color=COL[m], alpha=0.15)
ax.axhline(0, color='#333', lw=0.7)
ax.set_xlabel('欠けている割合（%）'); ax.set_ylabel('持ち家率の係数の偏り（帯は推定のばらつき）')
ax.set_title('小さい町ほど欠ける場合、欠測が増えるほど偏りもばらつきも大きくなる', fontsize=11)
ax.legend(fontsize=9)
fig.tight_layout(); fig.savefig(F / 'f41_rate.png', dpi=150); plt.close(fig)

# 6 頑健性（実データの持ち家率の係数）
r = rob[rob['var'] == FOCUS].reset_index(drop=True)
base = cm[(cm['var'] == FOCUS)].set_index('method')
rows = [('完全ケース（基本）', base.loc['完全ケース']), ('多重代入（基本、m=20）', base.loc['多重代入（結果も使う）'])] + \
       [(s.setting, s) for _, s in r.iterrows()]
fig, ax = plt.subplots(figsize=(8.8, 5.6))
y = np.arange(len(rows))[::-1]
for yy, (lab, s) in zip(y, rows):
    c = '#555555' if '完全ケース' in lab else ('#d9822b' if 'マッチング' in lab else '#2b6cb0')
    ax.errorbar(s['coef'], yy, xerr=[[s['coef'] - s['lo']], [s['hi'] - s['coef']]], fmt='o', color=c, capsize=3, ms=5)
ax.set_yticks(y); ax.set_yticklabels([f"{lab}（{int(s['n']):,}）" for lab, s in rows], fontsize=9)
ax.axvline(0, color='#333', lw=0.6)
ax.set_xlabel('持ち家率10ポイントあたりの子ども女性比の差')
ax.set_title('結果も使って埋めれば、設定を変えても多重代入は −8〜−10。完全ケースは −6〜−7', fontsize=11)
fig.tight_layout(); fig.savefig(F / 'f41_robust.png', dpi=150); plt.close(fig)
print('figures done')
