import json, pathlib
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in f or 'NotoSansJP' in f: font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
ROOT = pathlib.Path(__file__).resolve().parents[1]; FIG = ROOT / 'figures'; FIG.mkdir(exist_ok=True)
S = json.load(open(ROOT / 'results' / 'summary.json'))
LAB = ['～49', '50～99', '100～149', '150～199', '200～249', '250～299', '300～399', '400～499']
W = np.array([50, 50, 50, 50, 50, 50, 100, 100]); x = np.arange(8)
G = ['有配偶の女性', '配偶者のいない女性', '有配偶の男性', '配偶者のいない男性']
COL = ['#c0392b', '#e59866', '#2e86c1', '#85c1e9']

# 1 所得の分布（2022、50万円あたりの割合）
fig, ax = plt.subplots(figsize=(9, 5))
for g, c in zip(G, COL):
    n = np.array(S['main'][f'2022_{g}']['counts']); d = n / n.sum() / W * 50 * 100
    ax.plot(x, d, marker='o', color=c, lw=2.5 if g == '有配偶の女性' else 1.6, label=g)
ax.axvspan(0.5, 2.5, color='#f2d7d5', alpha=.5); ax.text(1.5, ax.get_ylim()[1] * .93, '50～149万円', ha='center', color='#922b21')
ax.set_xticks(x); ax.set_xticklabels(LAB); ax.set_xlabel('主な仕事からの年間収入（万円）'); ax.set_ylabel('50万円あたりの割合（%）')
ax.set_title('非正規で働く人の年間収入の分布（2022年）\n有配偶の女性だけ、50～149万円に大きく偏っている', loc='left')
ax.legend(frameon=False); ax.grid(alpha=.3)
fig.text(.01, .01, '出典：総務省「令和4年就業構造基本調査」第66表を加工。300万円以上は100万円刻みのため、50万円あたりに換算', fontsize=8, color='gray')
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(FIG / 'f82_dist.png', dpi=150); plt.close()

# 2 有配偶女性：実際と反実仮想
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
for ax, y in zip(axs, (2017, 2022)):
    r = S['main'][f'{y}_有配偶の女性']; n = np.array(r['counts']) / 1e4 / W * 50; p = np.array(r['pred']) / 1e4 / W * 50
    ax.bar(x, n, color=['#bbb', '#c0392b', '#c0392b', '#bbb', '#bbb', '#bbb', '#bbb', '#bbb'], label='実際')
    ax.plot(x, p, color='k', marker='o', lw=2, label='窓の外から作った「なめらかな分布」')
    ax.set_xticks(x); ax.set_xticklabels(LAB, rotation=40, fontsize=8); ax.set_title(f'{y}年：窓の中の超過 {r["excess"]/1e4:.0f}万人（反実仮想の{r["b"]+1:.1f}倍）', fontsize=10)
    ax.grid(alpha=.3, axis='y')
axs[0].set_ylabel('人数（万人、50万円あたり）'); axs[0].legend(frameon=False, fontsize=9)
fig.suptitle('有配偶の女性（非正規）：50～149万円の人数は、なめらかな分布の約3倍', x=.01, ha='left')
fig.text(.01, .01, '反実仮想：50～149万円を除いた6階級の密度の対数に2次式を当てはめたもの。出典：総務省「就業構造基本調査」（2017・2022年）を加工', fontsize=8, color='gray')
fig.tight_layout(rect=(0, .04, 1, .95)); fig.savefig(FIG / 'f82_bunching.png', dpi=150); plt.close()

# 3 就業調整をしている割合（所得階級別）
fig, ax = plt.subplots(figsize=(9, 5))
for g, c in zip(G, COL):
    ax.plot(x, np.array(S['adjust_share'][f'2022_{g}']) * 100, marker='o', color=c, lw=2.5 if g == '有配偶の女性' else 1.6, label=f'{g}（2022）')
ax.plot(x, np.array(S['adjust_share']['2017_有配偶の女性']) * 100, ls='--', color='#c0392b', lw=1.2, label='有配偶の女性（2017）')
ax.set_xticks(x); ax.set_xticklabels(LAB); ax.set_xlabel('主な仕事からの年間収入（万円）'); ax.set_ylabel('就業調整をしている人の割合（%）')
ax.set_title('「就業調整をしている」と答えた人の割合\n有配偶の女性は50～149万円で5割を超え、150万円を超えると1割を切る', loc='left')
ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.3)
fig.text(.01, .01, '就業調整：年収の調整や労働時間の調整をしていること（調査票の設問）。出典：総務省「就業構造基本調査」を加工', fontsize=8, color='gray')
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(FIG / 'f82_adjust_share.png', dpi=150); plt.close()

# 4 グループ別の集積の大きさ ＋ 反実仮想の作り方
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
ax = axs[0]; w = .38
for i, y in enumerate((2017, 2022)):
    b = [S['main'][f'{y}_{g}']['b'] for g in G]
    ax.bar(np.arange(4) + (i - .5) * w, b, w, label=f'{y}年', color=['#7f8c8d', '#2c3e50'][i])
    for j, v in enumerate(b): ax.text(j + (i - .5) * w, v + .04, f'{v:.2f}', ha='center', fontsize=8)
ax.set_xticks(range(4)); ax.set_xticklabels([g.replace('の', 'の\n') for g in G], fontsize=9); ax.set_ylabel('集積の大きさ b（超過人数÷反実仮想）')
ax.set_title('グループ別：窓の中の超過の大きさ', fontsize=10); ax.legend(frameon=False); ax.grid(alpha=.3, axis='y')
ax = axs[1]
lab = ['多項式（窓の外）', '就業調整をしていない\n有配偶女性の形', '配偶者のいない\n女性の形', '有配偶の男性の形']
for i, y in enumerate((2017, 2022)):
    v = [S['main'][f'{y}_有配偶の女性']['b'], S['comparison_cf'][f'{y}_就業調整していない有配偶女性']['b'], S['comparison_cf'][f'{y}_配偶者のいない女性']['b'], S['comparison_cf'][f'{y}_有配偶の男性']['b']]
    ax.bar(np.arange(4) + (i - .5) * w, v, w, label=f'{y}年', color=['#7f8c8d', '#2c3e50'][i])
    for j, vv in enumerate(v): ax.text(j + (i - .5) * w, vv + .05, f'{vv:.2f}', ha='center', fontsize=8)
ax.set_xticks(range(4)); ax.set_xticklabels(lab, fontsize=8); ax.set_title('有配偶の女性：反実仮想の作り方を変えると', fontsize=10); ax.grid(alpha=.3, axis='y')
fig.text(.01, .01, 'b=1 は「なめらかな分布より2倍多い」。比較グループの形は窓の外の人数に合わせて拡大縮小。出典：総務省「就業構造基本調査」を加工', fontsize=8, color='gray')
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(FIG / 'f82_groups.png', dpi=150); plt.close()

# 5 頑健性
import pandas as pd
R = pd.DataFrame(S['robust'])
specs = list(dict.fromkeys(R.spec)); fig, ax = plt.subplots(figsize=(9, 5.2))
for i, y in enumerate((2017, 2022)):
    v = [R[(R.year == y) & (R.spec == s)].b.iloc[0] for s in specs]
    ax.barh(np.arange(len(specs)) + (i - .5) * .38, v, .38, label=f'{y}年', color=['#7f8c8d', '#2c3e50'][i])
ax.axvline(0, color='k', lw=.8); ax.set_yticks(range(len(specs))); ax.set_yticklabels(specs, fontsize=9); ax.invert_yaxis()
ax.set_xlabel('有配偶の女性の集積の大きさ b'); ax.legend(frameon=False)
ax.set_title('頑健性：当てはめ方を変えると b は1.2～2.9。\n100万円刻みにまとめると窓の外の点が足りず、測れなくなる', loc='left', fontsize=11)
ax.grid(alpha=.3, axis='x')
fig.tight_layout(); fig.savefig(FIG / 'f82_robust.png', dpi=150); plt.close()

# 6 雇用形態・年齢（2022）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
E = S['by_emp_2022']; ks = list(E)
axs[0].bar(range(len(ks)), [E[k]['b'] for k in ks], color='#2c3e50')
for i, k in enumerate(ks): axs[0].text(i, E[k]['b'] + .05, f"{E[k]['b']:.2f}\n({E[k]['total']/1e4:.0f}万人)", ha='center', fontsize=8)
axs[0].set_xticks(range(len(ks))); axs[0].set_xticklabels([k.replace('労働者派遣事業所の', '') for k in ks]); axs[0].set_title('雇用形態別の集積の大きさ（有配偶女性）', fontsize=10); axs[0].grid(alpha=.3, axis='y')
A_ = S['by_age_2022']
axs[1].plot([a['age'].replace('歳', '') for a in A_], [a['adjust_share'] * 100 for a in A_], marker='o', color='#c0392b', label='就業調整をしている割合')
axs[1].plot([a['age'].replace('歳', '') for a in A_], [a['window_share'] * 100 for a in A_], marker='s', color='#2c3e50', label='50～149万円にいる割合')
axs[1].tick_params(axis='x', rotation=60, labelsize=8); axs[1].set_ylabel('%'); axs[1].legend(frameon=False, fontsize=9); axs[1].grid(alpha=.3)
axs[1].set_title('年齢別（有配偶女性、2022年）', fontsize=10)
fig.text(.01, .01, '出典：総務省「令和4年就業構造基本調査」第66表を加工', fontsize=8, color='gray')
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(FIG / 'f82_emp_age.png', dpi=150); plt.close()
print('ok')
