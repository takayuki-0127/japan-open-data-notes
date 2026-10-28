# F115 04 図
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
from pathlib import Path
from common import *
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False})
A = Path(__file__).resolve().parents[1]; R = A / 'results'; FG = A / 'figures'; FG.mkdir(exist_ok=True)
bins = pd.read_csv(A / 'data' / 'bins_long.csv'); pub = pd.read_csv(A / 'data' / 'published.csv').set_index('year')
summ = pd.read_csv(R / 'error_summary.csv'); est = pd.read_csv(R / 'estimates_long.csv')
C = {'lognorm': '#9aa5b1', 'gamma': '#c9b37e', 'singh_maddala': '#5b8db8', 'dagum': '#8fb3d9', 'gb2': '#1f4e79',
     'uniform_pareto': '#d98c3f', 'pchip_pareto': '#b5482b', 'midpoint': '#6b9e5e'}
ORDER = ['lognorm', 'gamma', 'singh_maddala', 'dagum', 'gb2', 'midpoint', 'uniform_pareto', 'pchip_pareto']

# 図1：2024年の階級別の割合（密度）と、当てはめた分布
d = bins[bins.year == 2024]; cuts = SCHEMES['S25']; sh = coarsen(d.lo, d.share, cuts)
fig, ax = plt.subplots(figsize=(8, 4.6))
c = np.asarray(cuts, float); w = np.diff(c)
ax.bar(c[:-1], sh[:-1] / w * 100, width=w, align='edge', color='#dfe5ec', edgecolor='#9aa5b1', lw=.6, label='公表の割合（100万円あたりに直す）')
x = np.linspace(1, 2500, 1500)
for m, fn in [('lognorm', lambda: fit_param(cuts, sh, 'lognorm')[0]), ('gb2', lambda: fit_param(cuts, sh, 'gb2', [])[0]), ('pchip_pareto', lambda: fit_pchip_pareto(cuts, sh)[0])]:
    dd = fn(); f = np.gradient(dd.cdf(x), x) * 100 * 100
    ax.plot(x, f, color=C[m], lw=2, label=FAMILY_LABEL[m])
ax.axvline(pub.at[2024, 'median'], color='k', ls=':', lw=1); ax.text(pub.at[2024, 'median'] + 15, ax.get_ylim()[1] * .92, f"公表の中央値 {pub.at[2024, 'median']:.0f}万円", fontsize=9)
ax.set_xlabel('世帯の所得（万円、2024年）'); ax.set_ylabel('世帯の割合（％／100万円）'); ax.set_xlim(0, 2500)
ax.text(2010, ax.get_ylim()[1] * .2, '2,000万円以上 1.6%\n（幅が決まらない）', fontsize=8.5, color='#555')
ax.legend(frameon=False, fontsize=9); ax.set_title('図1　公表されているのは50万円刻みの割合だけ（2024年の所得）', loc='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig1_bins_2024.png', dpi=160); plt.close(fig)

# 図2：公表の25階級からの推定と公表値の差（39年の平均絶対誤差）
T = [('p20', '下から\n20%の値'), ('median', '中央値'), ('p80', '下から\n80%の値'), ('mean', '平均'), ('qmean1', '下位20%\nの平均'), ('qmean5', '上位20%\nの平均')]
s = summ[summ.scheme == 'S25'].pivot(index='method', columns='target', values='mae_pct').loc[ORDER]
fig, ax = plt.subplots(figsize=(8.4, 4.6))
M = s[[t for t, _ in T]].values
im = ax.imshow(np.minimum(M, 10), cmap='Reds', vmin=0, vmax=10, aspect='auto')
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, f'{M[i, j]:.1f}', ha='center', va='center', fontsize=9.5, color='white' if M[i, j] > 6 else 'black')
ax.set_xticks(range(len(T)), [l for _, l in T]); ax.set_yticks(range(len(ORDER)), [FAMILY_LABEL[m] for m in ORDER])
ax.set_title('図2　公表の25階級から推定した値と公表値のずれ（％、1985〜2024年の39年の平均）', loc='left', fontsize=11)
ax.tick_params(length=0); [sp.set_visible(False) for sp in ax.spines.values()]
fig.colorbar(im, ax=ax, shrink=.8, label='平均絶対誤差（％、10以上は同じ色）')
fig.tight_layout(); fig.savefig(FG / 'fig2_error_heatmap_S25.png', dpi=160); plt.close(fig)

# 図3：階級を粗くすると（中央値・平均・上位20%の平均）
SC = ['S25', 'S14', 'S8', 'S5', 'S3']; lab = ['25階級', '14階級', '8階級', '5階級', '3階級']
fig, axs = plt.subplots(1, 3, figsize=(10.5, 4.2), sharey=False)
for ax, (t, tl) in zip(axs, [('median', '中央値'), ('mean', '平均'), ('qmean5', '上位20%の平均')]):
    for m in ['lognorm', 'singh_maddala', 'gb2', 'midpoint', 'pchip_pareto']:
        v = [summ[(summ.scheme == sc) & (summ.method == m) & (summ.target == t)].mae_pct.iloc[0] for sc in SC]
        ax.plot(range(len(SC)), v, marker='o', color=C[m], lw=2, label=FAMILY_LABEL[m])
    ax.set_yscale('log'); ax.set_xticks(range(len(SC)), lab, fontsize=9); ax.set_title(tl, fontsize=11)
    ax.set_ylim(0.3, 300); ax.axhline(1, color='#999', lw=.6, ls=':')
axs[0].set_ylabel('公表値とのずれ（％、39年の平均、対数目盛り）'); axs[0].legend(frameon=False, fontsize=8.5, loc='upper left')
fig.suptitle('図3　階級を粗くすると、どの方法がどれだけ外れるか', x=0.01, ha='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig3_coarsening.png', dpi=160); plt.close(fig)

# 図4：確かめられる「上位20%の所得の割合」と、確かめられない「ジニ係数」（公表の25階級、年ごと）
e = est[est.scheme == 'S25']; yrs = sorted(e.year.unique())
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2))
ax = axs[0]; ax.plot(pub.index, pub.qshare5 * 100, color='k', lw=2.4, label='公表（五分位階級の平均から）')
for m in ['lognorm', 'gb2', 'pchip_pareto']:
    v = e[e.method == m].set_index('year').qshare5 * 100; ax.plot(v.index, v.values, color=C[m], lw=1.6, label=FAMILY_LABEL[m])
ax.set_title('上位20%の世帯が受け取る所得の割合（％）', fontsize=10.5); ax.legend(frameon=False, fontsize=8.5)
ax = axs[1]
g = e.pivot(index='year', columns='method', values='gini')
ax.fill_between(g.index, g.min(axis=1), g.max(axis=1), color='#e8d5cf', label='8つの方法の幅')
for m in ['lognorm', 'gb2', 'pchip_pareto']: ax.plot(g.index, g[m], color=C[m], lw=1.6, label=FAMILY_LABEL[m])
ax.set_title('ジニ係数（公表値がなく、答え合わせできない）', fontsize=10.5); ax.legend(frameon=False, fontsize=8.5)
for a in axs: a.set_xlabel('所得の年')
fig.suptitle('図4　答え合わせできる指標と、できない指標', x=0.01, ha='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig4_share_gini_years.png', dpi=160); plt.close(fig)

# 図5：シミュレーション（答えの分かっている分布から5,000世帯を抜き出し、0.1%単位に四捨五入）
if not (R / 'sim_summary.csv').exists(): raise SystemExit('sim なし')
sim = pd.read_csv(R / 'sim_summary.csv'); s5 = sim[sim.n == 5000]
fig, axs = plt.subplots(1, 2, figsize=(10.8, 5.0))
ax = axs[0]
for i, sc in enumerate(['S25', 'S8', 'S5']):
    v = s5[(s5.truth == 'mix3') & (s5.scheme == sc)].set_index('method').loc[ORDER]
    ax.barh(np.arange(len(ORDER)) + (i - 1) * .27, v.gini_err_bias, height=.26, xerr=v.gini_err_rmse,
            color=['#1f4e79', '#5b8db8', '#a9c4e0'][i], error_kw=dict(lw=.7, capsize=0, ecolor='#555'), label=SCHEME_LABEL[sc].split('（')[0])
ax.axvline(0, color='k', lw=.8); ax.set_yticks(range(len(ORDER)), [FAMILY_LABEL[m] for m in ORDER]); ax.invert_yaxis()
ax.set_xlim(-0.03, 0.07); ax.set_title('ジニ係数のずれ（答え 0.407、混合分布）', fontsize=10.5); ax.legend(frameon=False, fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=3)
ax = axs[1]
for i, (tn, tl) in enumerate([('mix3', '答え＝対数正規3つの混合（上位1% 5.3%）'), ('gb2', '答え＝GB2（上位1% 4.7%）')]):
    v = s5[(s5.truth == tn) & (s5.scheme == 'S25')].set_index('method').loc[ORDER]
    ax.barh(np.arange(len(ORDER)) + (i - .5) * .38, v.top1_err_bias * 100, height=.36, xerr=v.top1_err_rmse * 100,
            color=['#b5482b', '#e3a48a'][i], error_kw=dict(lw=.7, capsize=0, ecolor='#555'), label=tl)
ax.axvline(0, color='k', lw=.8); ax.set_yticks(range(len(ORDER)), [''] * len(ORDER)); ax.invert_yaxis()
ax.set_title('上位1%の所得の割合のずれ（ポイント、公表の25階級）', fontsize=10.5); ax.legend(frameon=False, fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=1)
fig.suptitle('図5　答えが分かっている分布で試すと（棒＝平均のずれ、線＝ずれの二乗平均の平方根。混合60回・GB2 40回）', x=0.01, ha='left', fontsize=11)
fig.tight_layout(); fig.savefig(FG / 'fig5_simulation.png', dpi=160); plt.close(fig)
print('ok')
