"""04 図：figures/ に PNG を6枚（図5は 05 の問い直しの結果を使う）。"""
import os, importlib.util, numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
B = os.path.join(os.path.dirname(__file__), '..'); R = os.path.join(B, 'results'); F = os.path.join(B, 'figures')
os.makedirs(F, exist_ok=True)
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f or 'NotoSansCJKjp-Regular' in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#52514e', 'xtick.color': '#52514e', 'ytick.color': '#52514e', 'axes.grid': True,
                     'grid.color': '#e6e5e0', 'grid.linewidth': .8, 'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'savefig.dpi': 160})
INK2 = '#52514e'; BLUE, GREEN, ORANGE, PINK, GOLD = '#2a78d6', '#1baf7a', '#eb6834', '#e87ba4', '#eda100'
spec = importlib.util.spec_from_file_location('a', os.path.join(os.path.dirname(__file__), 'zz_f263_03_分析.py'))
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
FULL = (110 / 108 - 1) * 100
M = a.METHODS; SH = ['M1 前後比較', 'M2 前年同月比の差', 'M3 中断時系列', 'M4 軽減税率と差の差', 'M5 非課税と差の差', 'M6 合成対照']
real = pd.read_csv(os.path.join(R, 'B_real_vs_band.csv')); bd = pd.read_csv(os.path.join(R, 'B_bands.csv'))
def save(fig, n): fig.savefig(os.path.join(F, n), bbox_inches='tight'); plt.close(fig)

# 図1 群の指数
T, C8, CN = a.sets()
g = {'標準税率（10%に上がった）': a.group(T), '軽減税率（8%のまま）': a.group(C8), '非課税': a.group(CN)}
x = pd.to_datetime([y + '01' for y in a.YM])
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.axvspan(pd.Timestamp('2017-01-01'), pd.Timestamp('2019-09-30'), color='#eef3fb', lw=0)
ax.axvspan(pd.Timestamp('2022-01-01'), pd.Timestamp('2026-09-30'), color='#fbf1ea', lw=0)
for (lab, s), c in zip(g.items(), [ORANGE, GREEN, BLUE]):
    v = s - s.loc['201909']; ax.plot(x, v.values, color=c, lw=1.8, label=lab)
ax.axvline(pd.Timestamp('2019-10-01'), color=INK2, lw=1, ls='--')
ax.text(pd.Timestamp('2019-11-15'), ax.get_ylim()[1] * .92, '2019年10月\n税率引き上げ', fontsize=9, color=INK2)
ax.text(pd.Timestamp('2017-02-01'), ax.get_ylim()[0] * .9 + .5, '落ち着いた期間\n（プラセボ）', fontsize=9, color=BLUE)
ax.text(pd.Timestamp('2022-02-01'), ax.get_ylim()[1] * .55, '荒れた期間\n（プラセボ）', fontsize=9, color=ORANGE)
ax.set_ylabel('2019年9月との差（100×対数、約%）'); ax.legend(loc='upper left', fontsize=9, frameon=False)
ax.set_title('消費者物価：税の区分ごとの品目の指数（2020年のウエイトで集計）', fontsize=12, loc='left')
save(fig, 'fig1_group_indices.png')

# 図2 本番の推定と偶然の幅
r = real[(real.variant == 'main') & (real.h == 3)].set_index('method').loc[M]
fig, ax = plt.subplots(figsize=(9, 4.6)); yy = np.arange(len(M))[::-1]
for i, m in enumerate(M):
    ax.plot([r.loc[m, 'p5'], r.loc[m, 'p95']], [yy[i]] * 2, color='#c9d6ea', lw=9, solid_capstyle='butt')
    ax.plot(r.loc[m, 'est'], yy[i], 'o', color=ORANGE, ms=9)
    ax.text(r.loc[m, 'est'] + .08, yy[i] + .18, f"{r.loc[m, 'est']:+.2f}", fontsize=10, color=ORANGE)
ax.axvline(0, color=INK2, lw=.8); ax.axvline(100 * np.log(110 / 108), color=INK2, lw=1, ls='--')
ax.text(100 * np.log(110 / 108) + .05, yy[-1] - .55, '全部転嫁の目安 1.83\n（%で+1.85%）', fontsize=9, color=INK2)
ax.set_yticks(yy); ax.set_yticklabels(SH); ax.set_ylim(-.9, len(M) - .4)
ax.set_xlabel('標準税率の品目の値段の上がり方（2019年10〜12月、対照との差、100×対数）')
ax.set_title('対照の置き方で +0.7〜+1.6 に分かれた（帯＝何もない月の5〜95%点）', fontsize=12, loc='left')
save(fig, 'fig2_estimates_by_control.png')

# 図3 偶然の幅：落ち着いた期間と荒れた期間
b = bd[(bd.variant == 'main') & (bd.h == 3)].pivot(index='method', columns='kind', values='half90').loc[M]
fig, ax = plt.subplots(figsize=(9, 4.4)); xx = np.arange(len(M))
ax.bar(xx - .2, b['落ち着いた期間'], .38, color=BLUE, label='落ち着いた期間（2017年1月〜2019年7月）')
ax.bar(xx + .2, b['荒れた期間'], .38, color=ORANGE, label='荒れた期間（2022年1月〜2026年7月）')
for i, m in enumerate(M):
    ax.text(i - .2, b.loc[m, '落ち着いた期間'] + .04, f"{b.loc[m, '落ち着いた期間']:.2f}", ha='center', fontsize=9)
    ax.text(i + .2, b.loc[m, '荒れた期間'] + .04, f"{b.loc[m, '荒れた期間']:.2f}", ha='center', fontsize=9)
ax.axhline(100 * np.log(110 / 108), color=INK2, lw=1, ls='--'); ax.text(5.45, 1.88, '1.83', fontsize=9, color=INK2)
ax.set_xticks(xx); ax.set_xticklabels([s.replace(' ', '\n', 1) for s in SH], fontsize=9)
ax.set_ylabel('何もない月に出る数字の90%の幅の半分（ポイント）'); ax.legend(fontsize=9, frameon=False, loc='upper left')
ax.set_title('何もない月でも、これだけの「効果」が出る（3か月平均）', fontsize=12, loc='left')
save(fig, 'fig3_placebo_bands.png')

# 図4 頑健性
V = ['main', 'P36', 'エネルギーを除くT', '軽減の対照から生鮮を除く', '単純平均']
VL = ['基本（前24か月）', '前36か月', '標準税率からエネルギーを除く', '軽減税率の対照から生鮮を除く', '品目の単純平均']
cols = [INK2, BLUE, ORANGE, GREEN, PINK]
fig, ax = plt.subplots(figsize=(9, 4.8))
for j, (v, lab, c) in enumerate(zip(V, VL, cols)):
    rr = real[(real.variant == v) & (real.h == 3)].set_index('method').loc[M]
    ax.scatter(rr.est.values, yy + (2 - j) * .13, color=c, s=30, label=lab, zorder=3)
ax.axvline(100 * np.log(110 / 108), color=INK2, lw=1, ls='--'); ax.axvline(0, color=INK2, lw=.8)
ax.set_yticks(yy); ax.set_yticklabels(SH); ax.legend(fontsize=8.5, frameon=False, loc='upper left', bbox_to_anchor=(1.01, 1.0))
ax.set_xlabel('2019年10〜12月の推定（100×対数）'); ax.set_title('条件を変えると、推定は +0.6〜+2.6 の間で動く（前12か月を除く）', fontsize=12, loc='left')
save(fig, 'fig4_robustness.png')

# 図5 問い直し：品目ごと
d = pd.read_csv(os.path.join(R, 'D_item_estimates.csv'), dtype={'code': str})
d1 = d[d.method == 'M2']
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw={'width_ratios': [1.25, 1]})
ax = axs[0]; bins = np.arange(-6, 8.01, .5)
ax.hist(d1.est.clip(-6, 8), bins=bins, color=BLUE, alpha=.85)
ax.axvline(100 * np.log(110 / 108), color=ORANGE, lw=1.4, ls='--'); ax.axvline(0, color=INK2, lw=.8)
ax.text(100 * np.log(110 / 108) + .15, ax.get_ylim()[1] * .9, '全部転嫁 1.83', color=ORANGE, fontsize=9)
ax.set_xlabel('品目ごとの推定（M2 前年同月比の差、100×対数）'); ax.set_ylabel('品目の数（335品目）')
ax.set_title('品目ごとに見ると、真ん中は全部転嫁の近く', fontsize=11, loc='left')
ax = axs[1]
s = pd.read_csv(os.path.join(R, 'D_item_summary.csv')); s = s[s.method == 'M2'].set_index('cat')
order = ['全部転嫁と合う（ゼロとは合わない）', '両方と合う（区別できない）', 'ゼロと合う（全部転嫁とは合わない）', 'その間', '上回る', '下回る']
lab = ['全部転嫁と合う', '区別できない', 'ゼロと合う', '間（どちらとも合わない）', '全部転嫁を上回る', 'ゼロを下回る']
vals = [s.w_share.get(o, 0) * 100 for o in order]; ns = [int(s.n.get(o, 0)) for o in order]
ax.barh(np.arange(len(order))[::-1], vals, color=[GREEN, '#bdbcb6', BLUE, GOLD, ORANGE, PINK])
for i, (v, n) in enumerate(zip(vals, ns)):
    ax.text(v + .5, len(order) - 1 - i, f'{v:.0f}%（{n}品目）', va='center', fontsize=9)
ax.set_yticks(np.arange(len(order))[::-1]); ax.set_yticklabels(lab, fontsize=9); ax.set_xlim(0, 45)
ax.set_xlabel('標準税率の品目のウエイトに占める割合（%）'); ax.set_title('各品目の「何もない月」の幅と比べると', fontsize=11, loc='left')
save(fig, 'fig5_reask_items.png')

# 図6 期間の長さ h と偶然の幅（落ち着いた期間）
bb = bd[(bd.variant == 'main') & (bd.kind == '落ち着いた期間')]
fig, ax = plt.subplots(figsize=(9, 4.4))
for m, sh, c in zip(M, SH, [INK2, BLUE, GOLD, GREEN, PINK, ORANGE]):
    q = bb[bb.method == m].sort_values('h'); ax.plot(q.h, q.half90, 'o-', color=c, label=sh)
ax.set_xticks([1, 3, 6, 12]); ax.set_xlabel('施策のあと何か月の平均で見るか'); ax.set_ylabel('90%の幅の半分（ポイント）')
ax.legend(fontsize=8.5, frameon=False, ncol=2); ax.set_title('落ち着いた期間の偶然の幅：見る期間を変えると', fontsize=12, loc='left')
save(fig, 'fig6_band_by_horizon.png')
print('ok')
