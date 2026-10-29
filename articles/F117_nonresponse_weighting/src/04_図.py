# F117 04 図
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
from pathlib import Path
from common import SIZES, AGES, SIZE_JA, AGE_JA
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False})
A = Path(__file__).resolve().parents[1]; D = A / 'data'; R = A / 'results'; FG = A / 'figures'; FG.mkdir(exist_ok=True)
C1, C2, C3, CG = '#1f4e79', '#d98c3f', '#b5482b', '#9aa5b1'

# 図1：回収率の推移と、単独世帯の割合のずれ
rr = pd.read_csv(D / 'response_rates.csv'); gap = pd.read_csv(R / 'gap_size_years.csv')
fig, axs = plt.subplots(1, 2, figsize=(10, 4.3))
ax = axs[0]
ax.plot(rr.year, rr.rr_household, 'o-', color=C1, label='世帯票')
m = rr.rr_income.notna(); ax.plot(rr.year[m], rr.rr_income[m], 's--', color=C2, label='所得票')
for y, v in zip(rr.year, rr.rr_household):
    if y in (1996, 2003, 2010, 2019, 2025): ax.text(y, v + 1.2, f'{v:.1f}', ha='center', fontsize=8.5, color=C1)
ax.set_ylim(50, 95); ax.set_ylabel('回収率（％）'); ax.set_xlabel('調査の年'); ax.legend(frameon=False, fontsize=9)
ax.set_title('回収率（公表資料の数字があった年）', loc='left', fontsize=10.5)
ax = axs[1]
ax.plot(gap.year, gap.census_single, 'o-', color=C3, label='国勢調査（一般世帯）')
ax.plot(gap.year, gap.survey_single, 'o-', color=C1, label='国民生活基礎調査（世帯票）')
for y, c, s in zip(gap.year, gap.census_single, gap.survey_single):
    ax.annotate('', xy=(y, s), xytext=(y, c), arrowprops=dict(arrowstyle='-', color=CG, lw=1))
    ax.text(y + 0.6, (c + s) / 2, f'{c - s:.1f}', fontsize=8.5, color='#555')
ax.set_ylabel('単独世帯の割合（％）'); ax.set_xlabel('国勢調査の年（2020年の調査は2019・2021年の平均）')
ax.legend(frameon=False, fontsize=9, loc='upper left'); ax.set_title('単独世帯の割合と、その差（ポイント）', loc='left', fontsize=10.5)
fig.suptitle('図1　回収率が下がるあいだ、単独世帯の差は2020年まで広がり、2025年は縮んだ', x=0.01, ha='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig1_rr_and_single_gap.png', dpi=160); plt.close(fig)

# 図2：2025年の構成（国勢調査÷所得票）
sz = pd.read_csv(R / 'compare_size_2025.csv', index_col=0); ag = pd.read_csv(R / 'compare_headage_2025.csv', index_col=0)
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw=dict(width_ratios=[6, 7]))
for ax, df, lab, idx in [(axs[0], sz, SIZE_JA, SIZES), (axs[1], ag, AGE_JA, AGES)]:
    x = np.arange(len(idx)); w = .38
    sv = df['survey_income'] if 'survey_income' in df else df.iloc[:, 1]
    ax.bar(x - w / 2, df.loc[idx, 'census'], w, color=C3, label='国勢調査 2025年')
    ax.bar(x + w / 2, sv.loc[idx], w, color=C1, label='所得票（2024年の所得）')
    for i, k in enumerate(idx):
        r = df.loc[k, 'census'] / sv.loc[k]
        ax.text(i, max(df.loc[k, 'census'], sv.loc[k]) + 0.8, f'×{r:.2f}', ha='center', fontsize=8.5, color='#333')
    ax.set_xticks(x); ax.set_xticklabels([lab[k] for k in idx], fontsize=9); ax.set_ylabel('世帯の割合（％）')
axs[0].set_title('世帯人員', loc='left', fontsize=10.5); axs[1].set_title('世帯主の年齢', loc='left', fontsize=10.5)
axs[0].legend(frameon=False, fontsize=9)
fig.suptitle('図2　所得票は、単独世帯と世帯主の若い世帯が少ない（×は 国勢調査÷所得票）', x=0.01, ha='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig2_composition_2025.png', dpi=160); plt.close(fig)

# 図3：重み付けのし直しで、平均・中央値・低所得の割合はどう動くか
rw = pd.read_csv(R / 'reweight_2024.csv')
lab = {'公表どおり（重み付けなし）': '公表どおり', '世帯人員（6区分）': '世帯人員', '世帯構造（5区分）': '世帯構造',
       '世帯主の年齢（7区分）': '世帯主の年齢', '人数＋年齢のレーキング': '人数＋年齢\n（レーキング）', '人数×年齢の事後層化（42セル）': '人数×年齢\n（42セル）'}
fig, axs = plt.subplots(1, 3, figsize=(11, 4.3), sharey=True)
y = np.arange(len(rw))[::-1]
for ax, col, ttl, fmt in [(axs[0], 'mean_scaled', '平均所得（万円）', '{:.0f}'), (axs[1], 'median', '中央値（万円）', '{:.0f}'),
                          (axs[2], 'below200', '200万円未満の世帯（％）', '{:.1f}')]:
    v = rw[col].values; b = v[0]
    cols = [CG] + [C3 if (x - b) * (1 if col != 'below200' else -1) < 0 else C1 for x in v[1:]]
    ax.scatter(v, y, color=cols, s=45, zorder=3); ax.axvline(b, color=CG, ls=':', lw=1)
    for xi, yi in zip(v, y): ax.text(xi, yi + 0.22, fmt.format(xi), ha='center', fontsize=8.5)
    ax.set_title(ttl, loc='left', fontsize=10.5); ax.grid(axis='x', color='#eee')
axs[0].set_yticks(y); axs[0].set_yticklabels([lab[m] for m in rw.method], fontsize=9)
fig.suptitle('図3　何に合わせて重みを付け直すかで、平均所得は539〜586万円に動いた（2024年の所得）', x=0.01, ha='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig3_reweight.png', dpi=160); plt.close(fig)

# 図4：シミュレーション：回収率を下げたときの平均所得のずれ（重み付けなし／人数＋年齢でレーキング）
sm = pd.read_csv(R / 'sim_summary.csv'); sm = sm[sm.gamma == '基本']
sc = ['MAR（人数と年齢だけ）', '低所得ほど答えない', '高所得ほど答えない', '両端が答えない']
ttl = {'MAR（人数と年齢だけ）': '答えるかは人数と年齢だけで決まる', '低所得ほど答えない': '＋ 低所得ほど答えない',
       '高所得ほど答えない': '＋ 高所得ほど答えない', '両端が答えない': '＋ 低所得と高所得が答えない'}
fig, axs = plt.subplots(1, 4, figsize=(12, 3.9), sharey=True)
for ax, s in zip(axs, sc):
    d = sm[sm.scenario == s].sort_values('rate')
    ax.plot(d.rate * 100, d.un_mean_bias, 'o-', color=CG, label='重み付けなし')
    ax.plot(d.rate * 100, d.rk_mean_bias, 'o-', color=C1, label='人数＋年齢で\nレーキング')
    ax.axhline(0, color='k', lw=.7); ax.axvline(62.6, color=C3, ls=':', lw=1)
    ax.set_title(ttl[s], loc='left', fontsize=9.5); ax.set_xlabel('回収率（％）'); ax.invert_xaxis()
axs[0].set_ylabel('平均所得のずれ（万円、答え 569万円）'); axs[0].legend(frameon=False, fontsize=8.5)
axs[0].text(61.5, axs[0].get_ylim()[1] * .9, '2025年\n62.6%', color=C3, fontsize=8)
fig.suptitle('図4　答えが分かっている架空の世帯で：重み付けで戻るのは「人数と年齢で説明できる分」だけ（30回の平均）', x=0.01, ha='left', fontsize=11)
fig.tight_layout(); fig.savefig(FG / 'fig4_simulation.png', dpi=160); plt.close(fig)

# 図5：地域・市郡別の回収率
ra = pd.read_csv(D / 'response_rates_area.csv')
fig, ax = plt.subplots(figsize=(8.6, 4.4))
y = np.arange(len(ra))[::-1]
ax.hlines(y, ra.rr_2025, ra.rr_2022, color='#ccc', lw=2)
ax.scatter(ra.rr_2022, y, color=CG, s=40, label='2022年', zorder=3); ax.scatter(ra.rr_2025, y, color=C1, s=40, label='2025年', zorder=3)
for yi, a, b in zip(y, ra.rr_2022, ra.rr_2025): ax.text(b - 0.8, yi - 0.05, f'{b:.1f}', ha='right', va='center', fontsize=8.5, color=C1)
ax.set_yticks(y); ax.set_yticklabels(ra.area, fontsize=9.5); ax.set_xlabel('世帯票の回収率（％）'); ax.set_xlim(48, 82)
ax.axhline(len(ra) - 1.5, color='#eee'); ax.axhline(3.5, color='#eee')
ax.legend(frameon=False, fontsize=9, loc='upper right', bbox_to_anchor=(1.0, 0.93))
ax.set_title('図5　回収率は大都市で低く、郡部と17ポイント差（世帯票）', loc='left', fontsize=11.5)
fig.tight_layout(); fig.savefig(FG / 'fig5_rr_area.png', dpi=160); plt.close(fig)
print('ok')
