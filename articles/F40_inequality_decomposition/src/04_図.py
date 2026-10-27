"""04 図：5枚"""
import numpy as np, pandas as pd, json
import matplotlib.pyplot as plt
from common import ROOT, YEARS

R = ROOT / 'results'; F = ROOT / 'figures'
ind = pd.read_csv(R / 'indicators.csv'); dec = pd.read_csv(R / 'decomposition.csv')
pw = pd.read_csv(R / 'pref_within.csv'); rb = pd.read_csv(R / 'robustness.csv')
sm = json.load(open(R / 'summary.json', encoding='utf-8'))
p = pd.read_csv(ROOT / 'data/panel.csv', dtype={'code': str})
C1, C2, C3, G = '#2a6f97', '#e07a5f', '#81b29a', '#888888'

# 1) 分布と指標の推移
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
for y, c in [(2005, G), (2020, C1)]:
    v = p[p.year == y].inc_tp
    ax[0].hist(v, bins=np.arange(150, 1200, 15), histtype='step', lw=1.8, color=c, label=f'{y}年度')
ax[0].set_yscale('log'); ax[0].set_xlabel('納税者1人あたり課税対象所得（万円）'); ax[0].set_ylabel('市区町村の数（対数目盛）')
ax[0].set_title('市区町村の所得の分布'); ax[0].legend()
ax[0].annotate('東京都港区\n1,163万円（2020）', xy=(1163, 1), xytext=(820, 30), arrowprops=dict(arrowstyle='->', color=C1), fontsize=9)
b = ind.set_index('year')
ax[1].plot(YEARS, b.T_w / b.T_w.iloc[0] * 100, 'o-', c=C1, label='タイル指数（納税者の重み）')
ax[1].plot(YEARS, b.gini_w / b.gini_w.iloc[0] * 100, 's-', c=C2, label='ジニ係数（納税者の重み）')
ax[1].plot(YEARS, b.T_u / b.T_u.iloc[0] * 100, 'o--', c=C1, alpha=.5, label='タイル指数（重みなし）')
ax[1].plot(YEARS, b.p90p10_u / b.p90p10_u.iloc[0] * 100, 'd--', c=G, label='上位10%点÷下位10%点（重みなし）')
ax[1].axhline(100, c='k', lw=.5); ax[1].set_ylabel('2005年度＝100'); ax[1].set_title('格差の指標の推移'); ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(F / 'f40_trend.png', dpi=150); plt.close()

# 2) 分解：県の間と県の中
d = dec[(dec.group == '都道府県（47）') & (dec['index'] == 'T')].set_index('year')
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
x = np.arange(len(YEARS))
ax[0].bar(x, d.between * 1000, color=C1, label='県の間')
ax[0].bar(x, d.within * 1000, bottom=d.between * 1000, color=C2, label='県の中')
for i, y in enumerate(YEARS):
    ax[0].text(i, d.loc[y, 'total'] * 1000 + .3, f"県の間 {d.loc[y,'between_share']*100:.0f}%", ha='center', fontsize=9)
ax[0].set_xticks(x, [f'{y}' for y in YEARS]); ax[0].set_ylabel('タイル指数 ×1000'); ax[0].set_title('格差を「県の間」と「県の中」に分ける'); ax[0].legend()
for lab, c, m in [('都道府県（47）', C1, 'o'), ('地方ブロック（8）', C3, 's'), ('大都市圏かどうか（2）', C2, 'd'), ('東京23区かどうか（2）', G, '^')]:
    e = dec[(dec.group == lab) & (dec['index'] == 'T')]
    ax[1].plot(e.year, e.between_share * 100, marker=m, c=c, label=lab)
rg = sm['random_groups']
ax[1].fill_between([2005, 2020], [rg['2005']['mean'] * 100] * 2, [rg['2020']['p95'] * 100] * 2, color='#ddd', label='でたらめに47に分けた場合（平均〜95%点）')
ax[1].set_ylabel('「間」の割合（%）'); ax[1].set_ylim(0, 85); ax[1].set_title('分け方ごとの「間」の割合'); ax[1].legend(fontsize=8, loc='upper right')
fig.tight_layout(); fig.savefig(F / 'f40_decomp.png', dpi=150); plt.close()

# 3) 県ごとの「県の中」の寄与
w = pw.pivot(index='group', columns='year', values='contrib_share').sort_values(2020, ascending=False).head(12)
fig, ax = plt.subplots(figsize=(8, 5))
yy = np.arange(len(w))[::-1]
ax.barh(yy + .2, w[2005] * 100, .4, color=G, label='2005年度'); ax.barh(yy - .2, w[2020] * 100, .4, color=C1, label='2020年度')
ax.set_yticks(yy, w.index); ax.set_xlabel('全国の格差（タイル指数）に占める、その県の「県の中」の分（%）')
ax.set_title('「県の中」の格差の多くは東京都の中にある'); ax.legend()
fig.tight_layout(); fig.savefig(F / 'f40_pref_within.png', dpi=150); plt.close()

# 4) 15年の増加の内訳
chg = sm['change_2005_2020']; tk = chg['within_by_pref_top']['東京都']
parts = [('県の間', chg['between']), ('東京都の中', tk), ('ほかの46道府県の中', chg['within'] - tk)]
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.bar([q[0] for q in parts], [q[1] * 1000 for q in parts], color=[C1, C2, C3])
for i, q in enumerate(parts):
    ax.text(i, q[1] * 1000 + .05, f"{q[1]*1000:.2f}\n（増加の{q[1]/chg['total']*100:.0f}%）", ha='center', fontsize=10)
ax.set_ylabel('タイル指数の増加 ×1000'); ax.set_title(f"2005→2020年度に格差が増えた分（全体 {chg['total']*1000:.2f}）の内訳")
ax.set_ylim(0, max(q[1] for q in parts) * 1000 * 1.3)
fig.tight_layout(); fig.savefig(F / 'f40_change.png', dpi=150); plt.close()

# 5) 頑健性
fig, ax = plt.subplots(figsize=(9, 5.2))
yy = np.arange(len(rb))[::-1]
ax.barh(yy + .2, rb.between_share_2005 * 100, .4, color=G, label='2005年度')
ax.barh(yy - .2, rb.between_share_2020 * 100, .4, color=C1, label='2020年度')
ax.axvspan(rg['2020']['mean'] * 100, rg['2020']['p95'] * 100, color='#e6e6e6', zorder=0, label='でたらめに47に分けた場合（2020、平均〜95%点）')
ax.set_yticks(yy, rb.setting); ax.set_xlabel('「県の間」の割合（%）'); ax.set_title('設定を変えても、県の間の割合は下がっていた'); ax.set_xlim(0, 75); ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.4, -0.12), ncol=3)
fig.tight_layout(); fig.savefig(F / 'f40_robust.png', dpi=150); plt.close()
print('ok')
