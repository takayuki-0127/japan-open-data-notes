# -*- coding: utf-8 -*-
"""図を作る。入力: data/panel.csv, results/*.csv  出力: figures/*.png"""
import json, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '..', 'data'); R = os.path.join(HERE, '..', 'results'); F = os.path.join(HERE, '..', 'figures')
os.makedirs(F, exist_ok=True)
for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
C1, C2, C3, C4 = '#2b6cb0', '#dd6b20', '#38a169', '#718096'

P = pd.read_csv(os.path.join(D, 'panel.csv')); E = P[P.edition == 2022]; YM = int(E.fy.max())
S = json.load(open(os.path.join(R, 'summary.json'), encoding='utf-8'))

# 図1：光の合計と県内総生産（断面）
g = E[E.fy == YM]
fig, ax = plt.subplots(figsize=(7.2, 5.2))
x = np.log10(g.ntl_sum); y = np.log10(g.gdp_real / 1e6)
ax.scatter(x, y, s=28, color=C1, alpha=.8)
b, a = np.polyfit(x, y, 1); xs = np.linspace(x.min(), x.max(), 10); ax.plot(xs, a + b * xs, color=C4, lw=1)
t = g[g.pref == 13]; ax.annotate('東京都', (np.log10(t.ntl_sum.iloc[0]), np.log10(t.gdp_real.iloc[0] / 1e6)), xytext=(-60, -4), textcoords='offset points', fontsize=10)
ax.set_xlabel('夜間光の合計（対数目盛、log10）'); ax.set_ylabel('県内総生産・実質（兆円、log10）')
ax.set_title(f'{YM}年度：光の合計で県内総生産の差の{S["csYM"]["光だけ"]["r2"]*100:.0f}%を説明（47都道府県）', fontsize=11)
fig.text(0.01, 0.01, '出典：NASA Black Marble（世界銀行 Space2Stats の ADM2 集計）、内閣府「県民経済計算」（令和4年度版）', fontsize=7, color='#555')
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(os.path.join(F, 'f195_01_scatter.png'), dpi=150); plt.close(fig)

# 図2：水準と1人あたりの説明力
rob = pd.DataFrame(S['rob'])
vals = [('光だけ（水準）', S['csYM']['光だけ']['r2'], C1), ('人口だけ（水準）', S['csYM']['人口だけ']['r2'], C4),
        ('光＋人口（水準）', S['csYM']['光＋人口']['r2'], C3),
        ('1人あたり光→1人あたり生産', float(rob[rob.variant.str.startswith('1人あたり生産')].r2_last.iloc[0]), C2)]
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.barh([v[0] for v in vals][::-1], [v[1] for v in vals][::-1], color=[v[2] for v in vals][::-1])
for i, v in enumerate(vals[::-1]):
    ax.text(v[1] + 0.01, i, f'{v[1]:.2f}', va='center', fontsize=10)
ax.set_xlim(0, 1.08); ax.set_xlabel('決定係数 R²（' + str(YM) + '年度、47都道府県）')
ax.set_title('高い R² の大半は「県の大きさ」。1人あたりにすると光ではほぼ説明できない', fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(F, 'f195_02_r2.png'), dpi=150); plt.close(fig)

# 図3：1県ずつ抜いた予測の外れ（名前は東京のみ）
L = pd.read_csv(os.path.join(R, 'loo_2022.csv'))
fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.2))
axs[0].hist(L.err_light * 100, bins=np.arange(-60, 190, 10), color=C1, alpha=.85)
axs[0].axvline(0, color=C4, lw=1); axs[0].set_xlabel('予測の外れ（実際÷予測−1、%）'); axs[0].set_ylabel('都道府県の数')
axs[0].set_title(f'光だけの予測：外れの中央値 {S["loo2022"]["光だけ"]["med_ape"]*100:.0f}%', fontsize=10.5)
axs[0].annotate('東京都 +174%', (170, 1), xytext=(95, 6), arrowprops=dict(arrowstyle='->', color=C4), fontsize=9)
lp = L.ntl_sum / L['pop'] * 1000
axs[1].scatter(np.log10(lp), L.err_light * 100, s=22, color=C2, alpha=.8)
axs[1].axhline(0, color=C4, lw=1); axs[1].set_xlabel('1,000人あたりの光（log10）'); axs[1].set_ylabel('予測の外れ（%）')
axs[1].set_title(f'人口の割に明るい県ほど、生産は予測より小さい（順位相関 {S["resid_corr"]["1人あたりの光"]["rho"]:.2f}）', fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(F, 'f195_03_loo.png'), dpi=150); plt.close(fig)

# 図4：全国の合計の動き
N = pd.read_csv(os.path.join(R, 'national_index.csv'))
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.plot(N.fy, N.ntl_sum, marker='o', color=C1, label='夜間光の合計（暦年）')
ax.plot(N.fy, N.gdp_real, marker='s', color=C2, label='県内総生産・実質の合計（年度）')
ax.plot(N.fy, N['pop'], color=C4, ls='--', label='人口')
ax.axhline(100, color='#ccc', lw=.8); ax.set_ylabel('2012年＝100'); ax.legend(frameon=False, fontsize=9)
ax.set_title(f'全国では前年比の相関 {S["nat_yoy_corr"]["r"]:.2f}（10年分）。2020年は光 {S["nat_2020"]["ntl_sum"]:+.1f}%・生産 {S["nat_2020"]["gdp_real"]:+.1f}%', fontsize=10.5)
fig.tight_layout(); fig.savefig(os.path.join(F, 'f195_04_national.png'), dpi=150); plt.close(fig)

# 図5：同じ県の中の変化（長い差）と、条件を変えた弾力性
ld = pd.read_csv(os.path.join(R, 'longdiff_2012_2022.csv'))
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
axs[0].scatter(ld.dl * 100, ld.dg * 100, s=22, color=C3)
axs[0].axhline(0, color='#ccc', lw=.8); axs[0].axvline(0, color='#ccc', lw=.8)
axs[0].set_xlabel('光の変化 2012→2022（%、対数差）'); axs[0].set_ylabel('実質生産の変化（%、対数差）')
axs[0].set_title(f'県ごとの10年の変化：順位相関 {S["ld_2012_2022"]["rho"]:.2f}（p={S["ld_2012_2022"]["p"]:.2f}）', fontsize=10.5)
r = rob[rob.b_fe.notna()].copy()
r = r.drop_duplicates('variant')
yy = np.arange(len(r))
axs[1].scatter(r.b_fe, yy, color=[C1 if p < 0.05 else C4 for p in r.p_fe], zorder=3)
axs[1].axvline(0, color=C2, lw=1)
axs[1].set_yticks(yy); axs[1].set_yticklabels(r.variant, fontsize=8)
axs[1].set_xlabel('同じ県の中の弾力性（県と年の効果を除く）')
axs[1].set_title('条件を変えても 0 の近く（青は p<0.05）', fontsize=10.5)
axs[1].invert_yaxis()
fig.tight_layout(); fig.savefig(os.path.join(F, 'f195_05_within.png'), dpi=150); plt.close(fig)
print('ok')
