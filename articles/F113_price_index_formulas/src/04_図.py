# 04_図
import sys, os, json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, os.path.dirname(__file__)); from common import P
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in f.replace(' ', '') or 'NotoSansCJK' in os.path.basename(f): font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
C = dict(L='#c0392b', P='#2471a3', F='#1e8449', chainF='#117a65', lowe='#7d3c98', J='#b9770e', C='#6e2c00', D='#566573', T='#148f77', GL='#7f8c8d')
m = pd.read_csv(P('results/index_main.csv'), index_col=0) * 100
# 図1
fig, ax = plt.subplots(figsize=(8, 4.8))
for k, lab, c, ls in [('fix_L', 'ラスパイレス（2005年の数量で固定）', C['L'], '-'), ('lowe5', '5年ごとに基準を改めるラスパイレス（CPIに近い作り方）', C['lowe'], '--'),
                       ('fix_F', 'フィッシャー（2005年と各年の平均的な形）', C['F'], '-'), ('chain_F', '連鎖フィッシャー（毎年つなぐ）', C['chainF'], ':'),
                       ('fix_P', 'パーシェ（各年の数量）', C['P'], '-')]:
    ax.plot(m.index, m[k], ls, color=c, lw=2, label=lab)
ax.set_title('同じ126品目の価格と数量でも、式によって2024年の水準が変わる（2005年＝100）', fontsize=11)
ax.set_xticks(range(2005, 2025, 3)); ax.set_ylabel('指数（2005年＝100）'); ax.legend(fontsize=8, frameon=False, loc='upper left'); ax.grid(alpha=.3)
for k, c in [('fix_L', C['L']), ('fix_P', C['P'])]:
    ax.annotate(f"{m[k].iloc[-1]:.1f}", (m.index[-1], m[k].iloc[-1]), xytext=(4, 0), textcoords='offset points', color=c, fontsize=9, va='center')
ax.text(0.99, 0.02, '家計調査（二人以上の世帯）の食料・光熱126品目の平均価格と購入数量から計算', transform=ax.transAxes, ha='right', fontsize=7, color='gray')
fig.tight_layout(); fig.savefig(P('figures/fig1_index_paths.png'), dpi=150); plt.close()
# 図2
g = pd.read_csv(P('results/gap_by_horizon.csv'), index_col=0)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(g.h, g.L_minus_P_pt, 'o-', color=C['L'], label='ラスパイレス − パーシェ（基準を2005年に固定）')
ax.plot(g.h, g.fixL_minus_chainF_pt, 's-', color='#e59866', label='ラスパイレス（固定） − 連鎖フィッシャー')
ax.plot(g.h, g.lowe5_minus_chainF_pt, 'd--', color=C['lowe'], label='5年ごとに改めるラスパイレス − 連鎖フィッシャー')
ax.axhline(0, color='k', lw=.8); ax.set_xlabel('基準年（2005年）からの年数'); ax.set_ylabel('指数の差（ポイント、2005年＝100）')
ax.set_title('固定した数量のずれは、基準年から離れるほど広がる。5年ごとに改めると半分以下に', fontsize=11)
ax.set_xticks(range(0, 20, 2)); ax.legend(fontsize=8.5, frameon=False); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(P('figures/fig2_gap_horizon.png'), dpi=150); plt.close()
# 図3
y = pd.read_csv(P('results/yearly_formulas.csv'), index_col=0)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.6), sharex=True, gridspec_kw=dict(height_ratios=[1.3, 1]))
a1.bar(y.index, y.bias_L_F * 100, color=[C['L'] if v > 0 else C['P'] for v in y.bias_L_F], width=.7)
a1.axhline(0, color='k', lw=.8); a1.set_ylabel('前年比の差（ポイント）')
a1.set_title('1年ごとの前年比：ラスパイレス − フィッシャー（連鎖）。平均0.05ポイント、最大は2010年の0.22', fontsize=10.5)
for yr in [2010, 2023]:
    a1.annotate(f"{y.bias_L_F[yr]*100:.2f}", (yr, y.bias_L_F[yr] * 100), xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8)
a2.bar(y.index, y.corr_dp_dq, color=['#5d6d7e' if v < 0 else '#e67e22' for v in y.corr_dp_dq], width=.7)
a2.axhline(0, color='k', lw=.8); a2.set_ylabel('相関'); a2.set_ylim(-.8, .5); a2.set_xticks(range(2006, 2025, 2))
a2.set_title('価格の上がり方と数量の増え方の相関（支出ウエイトつき）：19年中17年で負＝高くなった品目を減らした', fontsize=10)
fig.tight_layout(); fig.savefig(P('figures/fig3_yearly_bias.png'), dpi=150); plt.close()
# 図4
s = pd.read_csv(P('results/summary_main.csv')).set_index('index')
lab = dict(L='ラスパイレス', P='パーシェ', F='フィッシャー', T='トルンクビスト', GL='幾何ラスパイレス', D='ダット（平均価格の比）', J='ジェボンズ（比の幾何平均）', C='カーリ（比の算術平均）')
ks = ['P', 'GL', 'T', 'F', 'L', 'D', 'J', 'C']
fig, ax = plt.subplots(figsize=(8, 4.6))
yy = np.arange(len(ks))
ax.barh(yy - .2, [s.loc['fix_' + k, 'cum_05_24'] * 100 for k in ks], .38, color='#aab7b8', label='2005年を基準に固定')
ax.barh(yy + .2, [s.loc['chain_' + k, 'cum_05_24'] * 100 for k in ks], .38, color=[C.get(k, '#555') for k in ks], label='毎年つなぐ（連鎖）')
for i, k in enumerate(ks):
    ax.text(s.loc['chain_' + k, 'cum_05_24'] * 100 + .3, i + .2, f"{s.loc['chain_' + k, 'cum_05_24']*100:.1f}", va='center', fontsize=8)
    ax.text(s.loc['fix_' + k, 'cum_05_24'] * 100 + .3, i - .2, f"{s.loc['fix_' + k, 'cum_05_24']*100:.1f}", va='center', fontsize=8, color='gray')
ax.set_yticks(yy); ax.set_yticklabels([lab[k] for k in ks], fontsize=9); ax.axhline(4.5, color='k', lw=.6, ls=':')
ax.text(46, 4.75, '↑ 支出ウエイトなし', fontsize=8, ha='right'); ax.text(46, 4.2, '↓ 支出ウエイトあり', fontsize=8, ha='right', va='top')
ax.set_xlabel('2005→2024年の上昇率（%）'); ax.set_xlim(25, 50)
ax.set_title('支出ウエイトのある式どうしの差は最大4ポイント、ウエイトなしの式はフィッシャーより4〜12ポイント高い', fontsize=10.5)
ax.legend(fontsize=8, frameon=False, loc='lower right')
fig.tight_layout(); fig.savefig(P('figures/fig4_formulas.png'), dpi=150); plt.close()
# 図5
r = pd.read_csv(P('results/robust_items.csv')); w = pd.read_csv(P('results/robust_weight_year.csv'))
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 4.3), gridspec_kw=dict(width_ratios=[1.35, 1]))
short = {'食料＋光熱（本体、2005〜2024年にそろう品目）': '本体（126品目）', '途中で加わった品目も入れる（連鎖のみ意味あり）': '途中で加わった品目も入れる',
         '食料だけ': '食料だけ', '「他の〜」を除く': '「他の〜」を除く', '生鮮（魚介・野菜・果物）を除く': '生鮮を除く（50品目）',
         '支出の大きい30品目': '支出の大きい30品目', '2002〜2024年（電気代なし）': '2002年から（電気代なし）'}
yy = np.arange(len(r))
a1.barh(yy, r.bias_LF_pt_per_year, color=['#c0392b' if i == 0 else '#e6b0aa' for i in range(len(r))])
a1.set_yticks(yy); a1.set_yticklabels([short[x] for x in r.set], fontsize=8.5); a1.invert_yaxis()
for i, v in enumerate(r.bias_LF_pt_per_year): a1.text(v + .002, i, f'{v:.3f}', va='center', fontsize=8)
a1.set_xlabel('前年比の差の年平均（ポイント）'); a1.set_title('品目の範囲を変えたときの\nラスパイレス − フィッシャー（連鎖）', fontsize=10)
a2.plot(w.weight_year, w.rise_2020_2024 * 100, 'o-', color=C['lowe'], label='数量をその年で固定（ロウ指数）')
a2.axhline(w.fisher_2020_2024.iloc[0] * 100, color=C['F'], ls='--', label='フィッシャー（2020年と2024年）')
a2.set_xlabel('数量（ウエイト）を取る年'); a2.set_ylabel('2020→2024年の上昇率（%）'); a2.legend(fontsize=8, frameon=False)
a2.set_title('ウエイトの年が古いほど、\n2020→2024年の上昇は大きく出る', fontsize=10); a2.grid(alpha=.3)
fig.tight_layout(); fig.savefig(P('figures/fig5_robustness.png'), dpi=150); plt.close()
print('ok')
