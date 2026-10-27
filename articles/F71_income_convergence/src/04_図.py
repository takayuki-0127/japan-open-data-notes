import numpy as np, pandas as pd, pathlib, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in fm.findSystemFonts():
    if 'NotoSansCJK' in f or 'NotoSansJP' in f: fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.unicode_minus'] = False
H = pathlib.Path(__file__).resolve().parents[1]; R = H/'results'; F = H/'figures'
p = pd.read_csv(H/'data/panel_rel_income.csv'); C1, C2, C3, C4 = '#1f5f8b', '#d1495b', '#7a7a7a', '#e39b36'
# 1 σ
s = pd.read_csv(R/'sigma_by_year.csv', index_col=0)
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(s.index, s['sd46_沖縄除く'], color=C1, lw=2.2, label='46都道府県（沖縄を除く、単純）')
ax.plot(s.index, s['sd46_東京除く'], color=C2, lw=2.2, label='東京・沖縄を除く45道府県')
ax.plot(s.index, s['sd47_人口重み'], color=C3, lw=1.6, ls='--', label='47都道府県・人口で重み（1975年度〜）')
ax.plot(s.index, s['sd46_段差を消さない'], color=C4, lw=1.2, ls=':', label='46都道府県・基準改定の段差を消さずにつないだ場合')
for y, t in [(1961, '1961'), (1975, '1975'), (2020, '2020')]:
    ax.axvline(y, color='#bbb', lw=0.8, zorder=0)
ax.set_ylabel('1人当たり県民所得（対数）の県の間の標準偏差'); ax.set_xlabel('年度')
ax.set_title('σ収束：県の間の所得の散らばり（1955〜2022年度）', loc='left', fontsize=13)
ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(F/'f71_sigma.png', dpi=150); plt.close()
# 2 β 散布図
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
for ax, (a, b) in zip(axs, [(1955, 1975), (2007, 2022)]):
    x = p[p.year == a].set_index('code')['r']; yb = p[p.year == b].set_index('code')['r']
    d = pd.concat([x.rename('r0'), yb.rename('r1')], axis=1).dropna(); d['g'] = (d.r1-d.r0)/(b-a)*100
    tk = d.index == 13
    ax.scatter(d.r0[~tk], d.g[~tk], color=C1, s=28, alpha=.8)
    ax.scatter(d.r0[tk], d.g[tk], color=C2, s=50); ax.annotate('東京', (d.r0[tk].iloc[0], d.g[tk].iloc[0]), xytext=(4, 4), textcoords='offset points', color=C2)
    k, c = np.polyfit(d.r0, d.g, 1); xx = np.linspace(d.r0.min(), d.r0.max(), 10); ax.plot(xx, k*xx+c, color=C3, lw=1.5)
    ax.axhline(0, color='#999', lw=.8); ax.axvline(0, color='#999', lw=.8)
    ax.set_title(f'{a}→{b}年度（傾き {k/100:+.4f}／年）', loc='left', fontsize=12)
    ax.set_xlabel(f'{a}年度の相対所得（全県の対数平均との差）'); ax.grid(alpha=.3)
axs[0].set_ylabel('相対所得の変化（%ポイント／年）')
fig.suptitle('β収束：初めに低かった県ほど伸びたか', x=0.01, ha='left', fontsize=13); fig.tight_layout(); fig.savefig(F/'f71_beta.png', dpi=150); plt.close()
# 3 移動β
r = pd.read_csv(R/'rolling_beta_10y.csv')
fig, ax = plt.subplots(figsize=(9, 4.6))
m = (r.始まり+r.終わり)/2
ax.fill_between(m, r.下, r.上, color=C1, alpha=.18); ax.plot(m, r.beta, color=C1, lw=2)
ax.axhline(0, color='#555', lw=1)
ax.set_xlabel('10年間の期間の中央の年度'); ax.set_ylabel('β（年率、95%区間）')
ax.set_title('10年ごとのβ：マイナスなら「低い県ほど伸びた」', loc='left', fontsize=13); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(F/'f71_rolling_beta.png', dpi=150); plt.close()
# 4 東京と分布
piv = p.pivot(index='year', columns='code', values='r')
ex = piv.drop(columns=[13, 47])
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.fill_between(piv.index, ex.quantile(.1, axis=1), ex.quantile(.9, axis=1), color=C1, alpha=.18, label='東京・沖縄を除く県の10〜90%点')
ax.plot(piv.index, ex.median(axis=1), color=C1, lw=1.5, label='同・中央値')
ax.plot(piv.index, piv[13], color=C2, lw=2.2, label='東京都（基準改定の段差を消してつないだ値）')
pn = p.pivot(index='year', columns='code', values='r_naive')
ax.plot(pn.index, pn[13], color=C2, lw=1.2, ls=':', label='東京都（段差を消さずにつないだ値）')
ax.set_ylabel('相対所得（全県の対数平均との差）'); ax.set_xlabel('年度'); ax.grid(alpha=.3)
ax.set_title('東京の位置はほぼ横ばい、ほかの県の幅は縮んだ', loc='left', fontsize=13); ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(F/'f71_tokyo_band.png', dpi=150); plt.close()
# 5 動学パネル
t = pd.read_csv(R/'dynamic_panel.csv')
sets = ['基本（1955〜2020、5年ごと）', '東京を除く', '1975〜2020（47県）', '3年ごと（1955〜2020）', '操作変数のラグ 3:5（AR(2)対策）', '基準改定の段差を消さない']
meth = [('OLS', C3), ('FE', C4), ('差分GMM', C2), ('systemGMM', C1)]
fig, ax = plt.subplots(figsize=(10, 5))
for i, sname in enumerate(sets):
    row = t[t.設定 == sname].iloc[0]
    for j, (mname, col) in enumerate(meth):
        y = i + (j-1.5)*0.18; v = row[mname]; se = row[mname+'_se']
        ax.errorbar(v, y, xerr=1.96*se, fmt='o', color=col, ms=6, capsize=2, label=mname.replace('FE', '固定効果').replace('systemGMM', 'system GMM') if i == 0 else None)
ax.set_yticks(range(len(sets))); ax.set_yticklabels([s.replace('（AR(2)対策）', '') for s in sets]); ax.invert_yaxis()
ax.axvline(1, color='#999', lw=.8); ax.set_xlabel('ρ（5年前の相対所得の係数。1に近いほど差が残る）')
ax.set_title('動学パネル：手法で ρ は0.71〜0.95と揺れた', loc='left', fontsize=13); ax.legend(frameon=False, fontsize=9, loc='lower left'); ax.grid(alpha=.3, axis='x')
fig.tight_layout(); fig.savefig(F/'f71_dynamic_panel.png', dpi=150); plt.close()
print('ok')
