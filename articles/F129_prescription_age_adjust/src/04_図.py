# F129 04 図
import json, pathlib
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in f.replace(' ', '') or 'NotoSansCJKjp' in f: font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.unicode_minus'] = False
B = pathlib.Path(__file__).resolve().parent.parent; R = B / 'results'; F = B / 'figures'; F.mkdir(exist_ok=True)
S = json.load(open(R / 'summary.json'))
m = pd.read_csv(R / 'sr_main_214_2024.csv', dtype={'pref': str})
C1, C2, C3, G = '#2b6cb0', '#dd6b20', '#2f855a', '#718096'

# 図1 年齢構成から見込まれる比 と 実際の比
fig, ax = plt.subplots(figsize=(7.2, 5.6))
ax.scatter(m.age_ratio, m.crude, s=40, color=C1, label='実際の処方量（人口1人あたり、全国＝1）', zorder=3)
lim = [0.7, 1.45]; ax.plot(lim, lim, color=G, lw=1, ls='--', label='年齢構成どおりなら、この線の上')
ax.set_xlim(lim); ax.set_ylim(0.65, 1.45)
ax.set_xlabel('年齢・性の構成だけから見込まれる処方量（全国＝1）'); ax.set_ylabel('実際の処方量（全国＝1）')
ax.set_title('血圧降下剤（外来、2024年度）：47都道府県\n年齢構成で、県の差の約3分の2（対数の分散で{:.0%}）が説明された'.format(S['main']['share_explained']), fontsize=11)
ax.legend(loc='upper left', fontsize=9); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(F / 'fig1_expected_vs_crude.png', dpi=150); plt.close()

# 図2 ファンネルプロット
tau = S['main_funnel']['tau']
fig, ax = plt.subplots(figsize=(7.2, 5.6))
x = m.E.values; ax.scatter(x / 1e8, m.SR, s=36, color=C1, zorder=3, label='都道府県（年齢調整後の比）')
xs = np.linspace(x.min() * .8, x.max() * 1.05, 300); s = 1 / np.sqrt(xs)
for z, ls, lab in ((1.96, '--', '95%'), (3.09, '-', '99.8%')):
    ax.plot(xs / 1e8, 1 + z * np.sqrt(s ** 2 + tau ** 2), color=C2, ls=ls, lw=1.3, label=f'過分散を入れた管理限界 {lab}')
    ax.plot(xs / 1e8, 1 - z * np.sqrt(s ** 2 + tau ** 2), color=C2, ls=ls, lw=1.3)
    ax.plot(xs / 1e8, 1 + z * s, color=G, ls=ls, lw=1); ax.plot(xs / 1e8, 1 - z * s, color=G, ls=ls, lw=1)
ax.plot([], [], color=G, label='錠数をそのまま件数とみなした限界（ほぼ1の線に重なる）')
ax.axhline(1, color='k', lw=.6); ax.set_xscale('log')
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
ax.xaxis.set_major_locator(FixedLocator([0.3, 0.5, 1, 2, 3, 5, 8])); ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{v:g}'))
ax.set_xlabel('年齢構成から見込まれる処方量（億錠、対数目盛）'); ax.set_ylabel('年齢調整後の比（全国＝1）')
f = S['main_funnel']
ax.set_title(f'ファンネルプロット：錠数をそのまま使うと{f["poisson_out95"]}県すべてが外れ、\n県どうしのばらつき（τ={tau:.3f}）を入れると95%の外は{f["re_out95"]}県、99.8%の外は{f["re_out998"]}県', fontsize=11)
ax.legend(fontsize=8, loc='upper right'); ax.grid(alpha=.3, which='both')
fig.tight_layout(); fig.savefig(F / 'fig2_funnel.png', dpi=150); plt.close()

# 図3 院外処方だけで見ると
c = pd.read_csv(R / 'sr_214_compare.csv', dtype={'pref': str}).set_index('pref')
o = pd.read_csv(R / 'outshare_214_2024.csv', dtype={'pref': str}).set_index('pref').out_share
fig, axs = plt.subplots(1, 2, figsize=(10, 4.6))
axs[0].scatter(o.reindex(c.index) * 100, c.SR2024_out, color=C2, s=30, label='院外処方だけ')
axs[0].scatter(o.reindex(c.index) * 100, c.SR2024_total, color=C1, s=30, label='院外＋院内')
axs[0].set_xlabel('外来の処方のうち院外処方の割合（%、錠数）'); axs[0].set_ylabel('年齢調整後の比（全国＝1）')
axs[0].set_title('院外だけで数えると、院外の割合が高い県ほど多く見える\n（相関 院外だけ {:.2f} → 院外＋院内 {:.2f}）'.format(S['corr_outonly_sr_vs_outshare'], S['corr_total_sr_vs_outshare']), fontsize=10)
axs[0].legend(fontsize=9); axs[0].grid(alpha=.3)
rb = {r['check']: r for r in S['robustness']}
k1 = '主：2024年度・外来（院外＋院内）・錠とカプセルの数・性と年齢'; k2 = '院外処方だけ（2024年度）'
vals = [rb[k2]['share_explained'], rb[k1]['share_explained']]
axs[1].bar(['院外処方だけ', '院外＋院内'], [v * 100 for v in vals], color=[C2, C1])
for i, v in enumerate(vals): axs[1].text(i, v * 100 + 1.5, f'{v:.0%}', ha='center')
axs[1].set_ylim(0, 80); axs[1].set_ylabel('年齢構成で説明された県の差（%）')
axs[1].set_title('数え方で「年齢で説明できる割合」が変わる', fontsize=10)
fig.tight_layout(); fig.savefig(F / 'fig3_outpatient_share.png', dpi=150); plt.close()

# 図4 薬効分類ごと
cl = pd.read_csv(R / 'by_class_2024.csv').sort_values('share_explained')
fig, ax = plt.subplots(figsize=(8, 7.4))
col = [C1 if c == 214 else (G if v < 0.5 else C3) for c, v in zip(cl.cls, cl.share_explained)]
ax.barh(cl.cname, cl.share_explained * 100, color=col)
ax.axvline(50, color='k', lw=.6, ls='--'); ax.axvline(0, color='k', lw=.6)
ax.set_xlabel('年齢構成で説明された県の差（%、外来・錠とカプセルの数、2024年度）')
ax.set_title('処方量の多い25の薬効分類：年齢で半分以上説明できたのは{}分類\n（中央値 {:.0%}。マイナスは、調整するとかえって差が広がったもの）'.format(S['by_class']['n_share_over_half'], S['by_class']['median_share']), fontsize=10.5)
ax.tick_params(axis='y', labelsize=8.5); ax.grid(alpha=.3, axis='x')
fig.tight_layout(); fig.savefig(F / 'fig4_by_class.png', dpi=150); plt.close()

# 図5 頑健性
r = pd.DataFrame(S['robustness'])
lab = ['主（院外＋院内、錠数、\n性と年齢、2024年度）', '薬剤費で数える', '年齢だけで調整', '秘匿を500とみなす', '院外だけ（2024年度）', '院外だけ（2023年度）']
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={'width_ratios': [1.4, 1]})
y = np.arange(len(r))[::-1]
axs[0].barh(y - .18, r.share_explained * 100, .36, color=C1, label='年齢で説明された割合（%）')
axs[0].barh(y + .18, r.sr_cv * 100, .36, color=C2, label='調整後に残った差（変動係数、%）')
axs[0].set_yticks(y); axs[0].set_yticklabels(lab, fontsize=8.5); axs[0].legend(fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2); axs[0].grid(alpha=.3, axis='x')
axs[0].set_title('頑健性：院外だけに絞ると説明できる割合が下がる', fontsize=10)
axs[1].scatter(c.SR2023_out, c.SR2024_out, color=C1, s=28)
axs[1].plot([.6, 1.6], [.6, 1.6], color=G, ls='--', lw=1)
axs[1].set_xlabel('2023年度（第10回）'); axs[1].set_ylabel('2024年度（第11回）')
axs[1].set_title('院外処方の調整後の比：年度をまたいだ相関 {:.3f}'.format(S['main_sr_corr_2023_2024_outonly']), fontsize=10); axs[1].grid(alpha=.3)
fig.tight_layout(); fig.savefig(F / 'fig5_robustness.png', dpi=150); plt.close()
print('figs ok')
