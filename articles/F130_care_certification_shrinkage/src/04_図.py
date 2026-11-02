"""04 図（Noto Sans CJK JP）。保険者名・都道府県名は図に出さない。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import poisson
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
ROOT = pathlib.Path(__file__).resolve().parents[1]; R = ROOT/'results'; FIG = ROOT/'figures'; FIG.mkdir(exist_ok=True)
S = json.load(open(R/'results.json'))
d = pd.read_csv(R/'insurer_2024_estimates.csv')
C1, C2, C3, G = '#4f7cac', '#c8553d', '#e0a03a', '#9aa5b1'

# 1 年齢の帯ごとの認定率と、保険者ごとの85歳以上の割合
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw=dict(width_ratios=[1, 1.4]))
br = S['desc']['band_rates']; labs = ['65〜74歳', '75〜84歳', '85歳以上']; v = [br['6574'], br['7584'], br['85p']]
axes[0].bar(labs, [x*100 for x in v], color=[C1, C3, C2])
for i, x in enumerate(v): axes[0].text(i, x*100 + 1.5, f'{x*100:.1f}%', ha='center', fontsize=10)
axes[0].set_ylabel('要介護（要支援）認定率（%）'); axes[0].set_title('全国の年齢別の認定率（2024年度末）', loc='left', fontsize=11)
axes[1].hist(d.share85*100, bins=40, color=G, edgecolor='white')
p5, p95 = S['desc']['share85_p5_p95']
for x in (p5, p95): axes[1].axvline(x*100, color=C2, ls='--', lw=1)
axes[1].text(p5*100, axes[1].get_ylim()[1]*0.92, f' 5%点 {p5*100:.0f}%', color=C2, fontsize=9)
axes[1].text(p95*100, axes[1].get_ylim()[1]*0.92, f' 95%点 {p95*100:.0f}%', color=C2, fontsize=9)
axes[1].set_xlabel('第1号被保険者のうち85歳以上の割合（%）'); axes[1].set_ylabel('保険者の数')
axes[1].set_title(f'保険者ごとの85歳以上の割合（{len(d):,}保険者）', loc='left', fontsize=11)
fig.tight_layout(); fig.savefig(FIG/'fig1_age_rates.png', dpi=150); plt.close()

# 2 年齢構成から見込んだ認定率と、実際の認定率
fig, ax = plt.subplots(figsize=(6.8, 5.4))
ex = d.E / d.ins_total * 100; cr = d.crude * 100
sz = np.clip(d.ins_total / 3000, 3, 80)
ax.scatter(ex, cr, s=sz, alpha=0.35, color=C1, edgecolor='none')
lim = [min(ex.min(), cr.min()) - 1, max(ex.max(), cr.max()) + 1]
ax.plot(lim, lim, color='k', lw=0.8, ls='--'); ax.text(lim[1]-0.3, lim[1]-1.2, '見込みどおり', ha='right', fontsize=9)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel('年齢構成だけから見込んだ認定率（%）\n＝全国の年齢別の認定率 × その保険者の年齢構成')
ax.set_ylabel('実際の認定率（%）')
ax.set_title(f'年齢構成で説明できるのは、粗い認定率のばらつきの約{S["desc"]["r2_crude_on_expected"]*100:.0f}%\n（決定係数、被保険者数で重みづけ。点の大きさ＝被保険者数）', loc='left', fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG/'fig2_expected_vs_crude.png', dpi=150); plt.close()

# 3 ファンネルプロット
fig, ax = plt.subplots(figsize=(7.6, 5))
ax.scatter(d.E, d.SR, s=6, alpha=0.4, color=C1, edgecolor='none')
e = np.logspace(np.log10(max(d.E.min(), 5)), np.log10(d.E.max()), 300)
for q, ls, lab in [(.025, '--', '95%'), (.001, ':', '99.8%')]:
    ax.plot(e, poisson.ppf(q, e)/e, color='k', ls=ls, lw=0.9, label=f'偶然のばらつきの範囲（{lab}）')
    ax.plot(e, poisson.ppf(1-q, e)/e, color='k', ls=ls, lw=0.9)
ax.axhline(1, color=G, lw=0.8); ax.set_xscale('log'); ax.set_ylim(0.3, 1.9)
ax.set_xlabel('年齢構成から見込んだ認定者数（人、対数目盛）'); ax.set_ylabel('年齢調整した認定率の比（実際 ÷ 見込み）')
ax.legend(frameon=False, fontsize=9, loc='upper right')
ax.set_title(f'小さい保険者ほど比は大きくぶれるが、範囲の外にある保険者も{S["funnel"]["out998"]*100:.0f}%（99.8%の範囲）', loc='left', fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG/'fig3_funnel.png', dpi=150); plt.close()

# 4 縮小：生の比と、階層ベイズで縮めた比（規模別）
fig, ax = plt.subplots(figsize=(7.6, 5))
order = d.ins_total.rank(pct=True)
small = order <= 0.2; large = order > 0.8
ax.scatter(d.SR[~small & ~large], d.theta[~small & ~large], s=5, color=G, alpha=0.4, label='中間の60%')
ax.scatter(d.SR[small], d.theta[small], s=8, color=C2, alpha=0.6, label='被保険者数が少ない20%')
ax.scatter(d.SR[large], d.theta[large], s=8, color=C1, alpha=0.7, label='被保険者数が多い20%')
ax.plot([0.3, 1.9], [0.3, 1.9], color='k', lw=0.8, ls='--')
ax.set_xlim(0.3, 1.9); ax.set_ylim(0.5, 1.6)
ax.set_xlabel('生の比（実際 ÷ 見込み）'); ax.set_ylabel('階層ベイズで縮めた比')
ax.legend(frameon=False, fontsize=9, loc='upper left')
o = S['out20']
ax.set_title(f'小さい保険者の極端な比ほど、全国と県の平均へ大きく引き戻される\n（±20%を超える保険者：生の比 {o["raw"]*100:.0f}% → 縮めた比 {o["post"]*100:.0f}%）', loc='left', fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG/'fig4_shrinkage.png', dpi=150); plt.close()

# 5 年齢調整で説明できた割合（本推定と頑健性）
rows = [('本推定（2024年度・3つの帯・全要介護度）', S['main'])]
names = {'bands2': '年齢の帯を2つ（65〜74歳／75歳以上）', 'care2plus': '要介護2以上だけ', 'support_only': '要支援1・2だけ',
         'exclude_small_lt3000': '被保険者3,000人未満を除く', 'prior_sd0.1': 'ばらつきの事前分布を狭く（0.1）', 'prior_sd2': 'ばらつきの事前分布を広く（2）',
         'year_2020': '2020年度', 'year_2021': '2021年度', 'year_2022': '2022年度', 'year_2023': '2023年度'}
for r in S['robustness']: rows.append((names.get(r['label'], r['label']), r))
fig, ax = plt.subplots(figsize=(8.6, 5.6))
for i, (n, r) in enumerate(rows[::-1]):
    lo, hi = r['explained_ci']; m = r['explained']
    ax.plot([lo*100, hi*100], [i, i], color=C1 if i < len(rows)-1 else C2, lw=2)
    ax.plot(m*100, i, 'o', color=C1 if i < len(rows)-1 else C2)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([n for n, _ in rows[::-1]], fontsize=9)
ax.axvline(0, color='k', lw=0.6); ax.axvline(100, color=G, lw=0.6, ls=':')
ax.set_xlabel('年齢調整で小さくなった、保険者間の「本当のばらつき」（分散）の割合（%）\n点＝事後平均、線＝95%区間')
ax.set_title('高齢化（年齢構成）で説明できるのは、地域差の3割前後', loc='left', fontsize=11)
fig.tight_layout(); fig.savefig(FIG/'fig5_explained.png', dpi=150); plt.close()
print('ok')
