"""04 図：figures/ に PNG を6枚（図5は 05 の問い直しの結果を使う）"""
import os, json, numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); R = os.path.join(B, 'results'); F = os.path.join(B, 'figures')
os.makedirs(F, exist_ok=True)
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f or 'NotoSansCJKjp-Regular' in f: fm.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#52514e', 'xtick.color': '#52514e', 'ytick.color': '#52514e', 'axes.grid': True,
                     'grid.color': '#e6e5e0', 'grid.linewidth': .8, 'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'savefig.dpi': 160})
INK2 = '#52514e'; BLUE, GREEN, ORANGE, PINK, GOLD = '#2a78d6', '#1baf7a', '#eb6834', '#e87ba4', '#eda100'
o = pd.read_csv(os.path.join(B, 'data', 'processed', 'stages_main.csv'), index_col=0, parse_dates=True)
p = pd.read_csv(os.path.join(B, 'data', 'processed', 'monthly_panel.csv'), index_col=0, parse_dates=True)
M = json.load(open(os.path.join(R, 'main.json'))); Q = json.load(open(os.path.join(R, 'reask.json')))
xc = pd.read_csv(os.path.join(R, 'xcorr.csv'), index_col=0); rob = pd.read_csv(os.path.join(R, 'robustness.csv'), index_col=0)
def save(fig, n): fig.savefig(os.path.join(F, n), bbox_inches='tight'); plt.close(fig)
def crop_lines(ax, a='2015', b='2026'):
    for y in range(int(a), int(b) + 1): ax.axvline(pd.Timestamp(f'{y}-09-01'), color='#d8d6cf', lw=.6, zorder=0)
# 図1 3つの段階の値段（2023年平均=100）
z = o.loc['2015':].copy(); cpi = p['cpi_rice_a']
fig, ax = plt.subplots(figsize=(9, 4.8))
for c, lab, col in [('aitai_kg', '産地→卸（相対取引価格・全銘柄平均）', ORANGE), ('cgpi', '卸・精米（企業物価指数 精米）', GREEN), ('retail_kg', '店頭（東京都区部 コシヒカリ5kg）', BLUE)]:
    s = z[c] / z.loc['2023', c].mean() * 100; ax.plot(s.index, s, color=col, lw=2, label=lab)
s = cpi.loc['2015':] / cpi.loc['2023'].mean() * 100; ax.plot(s.index, s, color=BLUE, lw=1, ls='--', label='店頭（全国 消費者物価 うるち米A）')
crop_lines(ax); ax.set_ylabel('2023年平均＝100'); ax.set_title('米の値段を3つの段階で見る（月次、2015年1月〜2026年10月）', loc='left', fontsize=12)
ax.legend(frameon=False, fontsize=9, loc='upper left'); ax.text(pd.Timestamp('2015-09-15'), ax.get_ylim()[1] * .55, '細い縦線＝9月\n（新しい年産の\n取引が始まる月）', fontsize=8, color=INK2)
save(fig, 'fig1_three_stages.png')
# 図2 店頭1kgの中身（円/kg）
z = o.loc['2015':'2026-09']
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.fill_between(z.index, 0, z['aitai_kg'], color=ORANGE, alpha=.55, lw=0, label='元の米の値段（相対取引価格を精米1kgに直したもの）')
ax.fill_between(z.index, z['aitai_kg'], z['retail_kg'], color=BLUE, alpha=.35, lw=0, label='その上に乗る分（店頭−元の米の値段）')
ax.plot(z.index, z['retail_kg'], color=BLUE, lw=1.8, label='店頭（東京都区部、円/kg）')
crop_lines(ax); ax.set_ylabel('円／精米1kg（税込み）'); ax.legend(frameon=False, fontsize=9, loc='upper left')
ax.set_title('店頭の1kgの値段を「元の米」と「その上に乗る分」に分ける', loc='left', fontsize=12)
for t, off in [('2023-07-01', (-110, 40)), (M['main']['retail_peak_month'], (-230, -70))]:
    r = o.loc[t]; ax.annotate(f"{pd.Timestamp(t):%Y年%-m月}\n上に乗る分 {r['margin_kg']:.0f}円", (pd.Timestamp(t), r['retail_kg']), xytext=off, textcoords='offset points', fontsize=8.5, color=INK2, arrowprops=dict(arrowstyle='-', color=INK2, lw=.6))
save(fig, 'fig2_retail_split.png')
# 図3 どの段階が先に動くか（前月比の相互相関）
fig, axs = plt.subplots(1, 3, figsize=(10, 3.8), sharey=True)
for ax, c, t in zip(axs, ['cgpi_vs_aitai', 'tokyo_vs_cgpi', 'tokyo_vs_aitai'], ['卸・精米 と 産地→卸', '店頭 と 卸・精米', '店頭 と 産地→卸']):
    s = xc[c]; ax.bar(s.index, s.values, color=[BLUE if k == s.idxmax() else '#b9c7d8' for k in s.index], width=.75)
    ax.set_title(t, fontsize=10.5); ax.set_xlabel('ずれ（か月）'); ax.axhline(0, color=INK2, lw=.6)
axs[0].set_ylabel('前月比の相関（2010年10月〜）')
fig.suptitle('どの段階が先に動くか（ずれがプラス＝左に書いた段階が遅れて動く）', x=.01, y=1.03, ha='left', fontsize=12)
fig.tight_layout()
save(fig, 'fig3_lead_lag.png')
# 図4 頑健性：上がり幅のうち元の米の値段の分（H1）と倍率（H3）
lab = {'main': '基本', 'yield088': '歩留まり0.88', 'yield092': '歩留まり0.92', 'cpi_national': '店頭を全国CPIに', 'tax_excl': '消費税を除く', 'niigata_koshi': '新潟コシヒカリで比べる', 'base_2022_23': '基準を2022〜23年に'}
t = pd.concat([pd.DataFrame([M['main']], index=['main']), rob])
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
ax = axs[0]; y = np.arange(len(t))[::-1]
ax.barh(y, t['peak_share_aitai'] * 100, color=ORANGE, alpha=.8, height=.35, label='店頭の山の月（2025年11月）')
ax.barh(y - .38, t['y2025_share_aitai'] * 100, color=GOLD, alpha=.8, height=.35, label='2025年の平均')
ax.axvline(70, color=INK2, ls='--', lw=1); ax.text(69, y[-1] - .9, '仮説の線 70%', fontsize=8.5, color=INK2, ha='right')
ax.set_yticks(y - .19); ax.set_yticklabels([lab[i] for i in t.index]); ax.set_xlabel('店頭の上がり幅のうち、元の米の値段の分（%）'); ax.legend(frameon=False, fontsize=8.5, loc='upper center', bbox_to_anchor=(.45, -.14), ncol=2)
ax = axs[1]
ax.scatter(t['avg1523_ratio'], y, color='#9a9890', label='2015〜2023年の平均', zorder=3); ax.scatter(t['peak_ratio'], y, color=BLUE, label='店頭の山の月', zorder=3)
for yy, a_, b_ in zip(y, t['avg1523_ratio'], t['peak_ratio']): ax.plot([a_, b_], [yy, yy], color='#c9c7bf', lw=1.5, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([]); ax.set_xlabel('倍率（店頭 ÷ 元の米の値段）'); ax.legend(frameon=False, fontsize=8.5, loc='upper center', bbox_to_anchor=(.5, -.14), ncol=2)
fig.suptitle('条件を変えて確かめる：上に乗る分の円は増え、倍率は縮んだ', x=.01, ha='left', fontsize=12)
save(fig, 'fig4_robustness.png')
# 図5 問い直し：上に乗る分（店頭 t − 元の米 t−1）は戻ったか
z = pd.read_csv(os.path.join(R, 'reask_margin_l1.csv'), index_col=0, parse_dates=True).loc['2015':]
mu, sd = Q['margin_l1_2015_23_mean'], Q['margin_l1_2015_23_sd']
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.axhspan(mu - 2 * sd, mu + 2 * sd, color='#e6e5e0', label='2015〜2023年の平均±2標準偏差')
ax.plot(z.index, z['margin_l1'], color=BLUE, lw=1.8, label='上に乗る分（店頭の月 − 前月の元の米の値段）')
crop_lines(ax); ax.set_ylabel('円／精米1kg'); ax.legend(frameon=False, fontsize=9, loc='upper left')
for t_, k, off in [(Q['margin_l1_max_month'], 'margin_l1_max', (-150, -5)), (Q['last_month'], 'margin_l1_last', (-150, 25))]:
    ax.annotate(f"{pd.Timestamp(t_):%Y年%-m月} {Q[k]:.0f}円", (pd.Timestamp(t_), Q[k]), xytext=off, textcoords='offset points', fontsize=8.5, color=INK2, arrowprops=dict(arrowstyle='-', color=INK2, lw=.6))
ax.text(pd.Timestamp('2016-01-01'), mu + 2 * sd + 8, f'2015〜2023年の平均 {mu:.0f}円', fontsize=8.5, color=INK2)
ax.set_title('もう一度問う：値上がりで広がった「上に乗る分」は、元の値段が下がった後に戻ったか', loc='left', fontsize=11.5)
save(fig, 'fig5_reask_margin.png')
# 図6 2024〜2026年を月ごとに
z = o.loc['2023-07':'2026-10']
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(z.index, z['retail_kg'], color=BLUE, lw=2, marker='o', ms=3, label='店頭（東京都区部、円/kg）')
ax.plot(z.index, z['aitai_kg'], color=ORANGE, lw=2, marker='o', ms=3, drawstyle='steps-post', label='元の米の値段（相対取引価格の精米換算、円/kg）')
crop_lines(ax, '2023', '2026'); ax.set_ylabel('円／精米1kg（税込み）'); ax.legend(frameon=False, fontsize=9, loc='upper left')
ax.axvspan(pd.Timestamp('2024-06-01'), pd.Timestamp('2024-08-31'), color=GOLD, alpha=.15)
ax.annotate('2024年6〜8月：店頭が先に上がり、\n元の米の値段はまだほぼ横ばい', (pd.Timestamp('2024-07-15'), 560), xytext=(pd.Timestamp('2023-07-15'), 760), fontsize=8.5, color=INK2, arrowprops=dict(arrowstyle='-', color=INK2, lw=.6))
ax.set_title('2024〜2026年を月ごとに：9月に新しい年産の値段へ段差で切り替わる', loc='left', fontsize=12)
save(fig, 'fig6_monthly_2024_26.png')
print(sorted(os.listdir(F)))
