# F173 04 図（03_分析.py のあとに実行）
import os, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False})
A = Path(__file__).resolve().parents[1]; R = A / 'results'; FG = A / 'figures'; FG.mkdir(exist_ok=True)
C1, C2, CG = '#1f4e79', '#b5482b', '#9aa5b1'

prof = pd.read_csv(R / 'profile_1994_2024.csv')
pv = pd.read_csv(R / 'profile_vs_published_1994_2024.csv')

# 図1：1994年と2024年の累積分布（2024年の価格）。横の矢印が「同じ順位の世帯の位置がどれだけ動いたか」
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.plot(prof.q1994, prof.u * 100, color=C1, lw=2.2, label='1994年の所得（2024年の価格に直す）')
ax.plot(prof.q2024, prof.u * 100, color=C2, lw=2.2, label='2024年の所得')
ax.fill_betweenx(prof.u * 100, prof.q2024, prof.q1994, color=CG, alpha=.25, lw=0, label='2本の間の面積 ＝ W1（178.8万円）')
for u in [.1, .3, .5, .7, .9]:
    a = np.interp(u, prof.u, prof.q1994); b = np.interp(u, prof.u, prof.q2024)
    ax.annotate('', xy=(b, u * 100), xytext=(a, u * 100), arrowprops=dict(arrowstyle='->', color='k', lw=1))
    ax.text(a + 12, u * 100 + 1.8, f'{b - a:+.0f}', fontsize=8.5)
ax.set_xlim(0, 2000); ax.set_ylim(0, 100)
ax.set_xlabel('世帯の所得（万円、2024年の価格）'); ax.set_ylabel('下からの順位（％）')
ax.legend(frameon=False, fontsize=9, loc='lower right')
ax.set_title('図1　1994年→2024年：どの順位の世帯の位置も、左（少ない側）へ動いた', loc='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig1_cdf_transport.png', dpi=160); plt.close(fig)

# 図2：順位ごとの動き（万円と％）。公表の五分位値・中央値どうしの差も重ねる
fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.2))
u = prof.u * 100; m = (prof.u > 0.005) & (prof.u < 0.97); m2 = (prof.u > 0.05) & (prof.u < 0.97)
axs[0].plot(u[m], prof['diff'][m], color=C2, lw=2)
axs[0].scatter(pv.u.dropna() * 100, pv.published_diff_real.dropna().iloc[:5], color='k', s=22, zorder=3, label='公表の分位点どうしの差')
axs[0].axhline(0, color='k', lw=.6); axs[0].axhline(pv.estimated_diff_real.iloc[-1], color=CG, ls='--', lw=1)
axs[0].text(55, pv.estimated_diff_real.iloc[-1] - 40, '平均の差（推定）−178万円', fontsize=8.5, color='#555')
axs[0].set_xlabel('下からの順位（％、〜97%）'); axs[0].set_ylabel('2024年 − 1994年（万円）'); axs[0].legend(frameon=False, fontsize=8.5, loc='lower left')
axs[0].set_title('万円で見ると、上の順位ほど大きく下がった', fontsize=10.5, loc='left')
pct = (prof.q2024 / prof.q1994 - 1) * 100
axs[1].plot(u[m2], pct[m2], color=C1, lw=2); axs[1].axhline(0, color='k', lw=.6)
axs[1].set_xlabel('下からの順位（％、5〜97%）'); axs[1].set_ylabel('変化率（％）'); axs[1].set_ylim(-45, 5); axs[1].set_xlim(0, 100)
axs[1].set_title('％で見ると、どの順位もおおむね2〜3割', fontsize=10.5, loc='left')
fig.suptitle('図2　1994年→2024年、同じ順位どうしの所得の差（2024年の価格）', x=0.01, ha='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig2_quantile_diff.png', dpi=160); plt.close(fig)

# 図3：741組すべてで、W1 と「平均の差」の関係（実質）
ap = pd.read_csv(R / 'all_pairs.csv'); g = ap[ap.price == 'real']
fig, ax = plt.subplots(figsize=(7.6, 5))
sc = ax.scatter(g.abs_dmean, g.W1, c=g.minor_share * 100, cmap='viridis', s=12, vmin=0, vmax=50)
lim = max(g.W1.max(), g.abs_dmean.max()) * 1.03
ax.plot([0, lim], [0, lim], color='k', lw=.8, ls='--'); ax.text(lim * .62, lim * .55, 'W1 ＝ 平均の差（分位点関数が交わらない）', fontsize=8.5, rotation=33)
cb = fig.colorbar(sc, ax=ax); cb.set_label('逆向きに動いた部分の割合（W1 のうち、％）')
ax.set_xlabel('平均の差の大きさ（万円）'); ax.set_ylabel('W1（万円）'); ax.set_xlim(0, lim); ax.set_ylim(0, lim)
ax.set_title('図3　39年から2年を選ぶ741組：W1 が平均の差を上回るのは、平均がほとんど変わらない組だけ', loc='left', fontsize=10.5)
fig.tight_layout(); fig.savefig(FG / 'fig3_w1_vs_mean.png', dpi=160); plt.close(fig)

# 図4：前の年からの動きを、距離の種類ごとに（最大を1にそろえる）。標本の揺れの目安を重ねる
seq = pd.read_csv(R / 'consecutive_years.csv'); nz = pd.read_csv(R / 'noise_floor.csv').set_index('households')
fig, axs = plt.subplots(2, 1, figsize=(10, 5.8), sharex=True)
x = seq.y2
axs[0].bar(x, seq.W1, color=C2, width=.7)
for h, ls in [(2000, ':'), (5000, '--')]:
    axs[0].axhline(nz.loc[h, 'W1_mean'], color='k', lw=1, ls=ls)
    axs[0].text(2025.6, nz.loc[h, 'W1_mean'], f'{h:,}世帯の標本なら\n動いていなくても出る大きさ', fontsize=7.5, va='center')
axs[0].set_ylabel('W1（万円）'); axs[0].set_title('W1（移した量×距離）：前の年からの動き', loc='left', fontsize=10.5)
axs[1].plot(x, seq.TV_bins / seq.TV_bins.max(), color=C1, marker='o', ms=3, lw=1.4, label='全変動距離（階級の割合の差だけ）')
axs[1].plot(x, seq.KS / seq.KS.max(), color='#6b9e5e', marker='s', ms=3, lw=1.2, label='KS（累積分布の差の最大）')
axs[1].plot(x, seq.W1 / seq.W1.max(), color=C2, lw=1.2, ls='--', label='W1')
axs[1].set_ylabel('最大を1にそろえた値'); axs[1].legend(frameon=False, fontsize=8.5, ncol=3, loc='upper center')
axs[1].set_xlabel('比べた年（前の年との比較。2019年の所得は調査がなく、2018→2020 を1組として比べた）')
fig.suptitle('図4　「どの年に大きく動いたか」は、距離の種類で入れ替わる（実質）', x=0.01, ha='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig4_consecutive.png', dpi=160); plt.close(fig)

# 図5：頑健性（1994→2024 の W1 と W2）
rb = pd.read_csv(R / 'robustness_1994_2024.csv')
lab = {'pchip': '単調スプライン＋パレート（主）', 'uniform': '階級内一様＋パレート', 'gb2': 'GB2 を当てはめる', 'midpoint': '階級の中央の値',
       'cap2000': '2,000万円以上を全員2,000万円', 'cap3000': '2,000万円以上を全員3,000万円', 'S14': '14階級にまとめる', 'S8': '8階級にまとめる',
       'S5': '5階級にまとめる', 'S21top1000': '1,000万円以上をひとまとめ', 'cpi_all': '物価を「総合」で調整', 'u<0.99': '上位1%を除いて測る'}
rb = rb.iloc[::-1]
fig, axs = plt.subplots(1, 2, figsize=(9.6, 5), sharey=True)
yy = np.arange(len(rb))
axs[0].barh(yy, rb.W1, color=C2); axs[0].set_yticks(yy); axs[0].set_yticklabels([lab[v] for v in rb.variant], fontsize=9)
for i, v in enumerate(rb.W1): axs[0].text(v + 3, i, f'{v:.0f}', va='center', fontsize=8.5)
axs[0].set_xlabel('W1（万円）'); axs[0].set_title('W1：階級を粗くしすぎなければ166〜182万円', loc='left', fontsize=10.5)
axs[1].barh(yy, rb.W2.fillna(0), color=C1)
for i, v in enumerate(rb.W2): axs[1].text((0 if np.isnan(v) else v) + 5, i, '—' if np.isnan(v) else f'{v:.0f}', va='center', fontsize=8.5)
axs[1].set_xlabel('W2（万円）'); axs[1].set_title('W2：上の裾の扱いで大きく動く', loc='left', fontsize=10.5)
fig.suptitle('図5　1994年→2024年の距離は、階級の扱いを変えてもどこまで同じか', x=0.01, ha='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig5_robustness.png', dpi=160); plt.close(fig)
print('ok')
