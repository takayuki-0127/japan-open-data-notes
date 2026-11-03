import pathlib, os, json, ast
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
HERE = pathlib.Path(__file__).resolve().parent.parent; os.chdir(HERE); os.makedirs('figures', exist_ok=True)
for p in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 150})
C0, C1, C2 = '#9AA5B1', '#E0A458', '#C0504D'   # 変わらない／一部で弱まる・動いた／結論が変わった
INK = '#2F3A45'; ACC = '#3E7CB1'
S = json.load(open('results/summary.json')); T = pd.read_csv('results/type_effect.csv')
H = pd.read_csv('results/articles.csv'); J = H[H.level.notna()].copy(); J['lv'] = J.level.astype(int)
LBL = ['変わらない', '一部で弱まる・動いた', '結論が変わった・逆になった']

# 図1 判定の分布（全体と記事の種類）
F = pd.read_csv('data/raw/f125_articles.csv')[['fid', 'type', 'outcome']]
M = J.merge(F, on='fid', how='left')
rows = [('全体（113本）', J.lv)]
for k, nm in [('E', '効果・関係の推定'), ('P', '予測'), ('D', '記述・方法')]:
    s = M[M.type == k].lv; rows.append((f'{nm}（{len(s)}本）', s))
fig, ax = plt.subplots(figsize=(8.6, 3.6))
for i, (nm, s) in enumerate(rows[::-1]):
    left = 0
    for k, c in zip([0, 1, 2], [C0, C1, C2]):
        v = (s == k).mean() * 100
        ax.barh(i, v, left=left, color=c, height=0.62, edgecolor='white')
        if v >= 6: ax.text(left + v / 2, i, f'{v:.0f}%', ha='center', va='center', color='white' if k else INK, fontsize=10)
        left += v
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows[::-1]])
ax.set_xlim(0, 100); ax.set_xlabel('記事の割合（%）')
ax.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in [C0, C1, C2]], LBL, ncol=3, loc='upper center', bbox_to_anchor=(0.45, 1.2), frameon=False, fontsize=9.5)
ax.set_title('頑健性チェックで、記事の結論はどれだけ動いたか（手作業の判定）', loc='left', fontsize=12, pad=30)
fig.tight_layout(); fig.savefig('figures/fig1_levels.png'); plt.close()

# 図2 よく使ったチェックと、よく効いたチェック
T = T.sort_values('ran_share')
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 4.6), sharey=True, gridspec_kw={'width_ratios': [1, 1.1]})
y = np.arange(len(T))
a1.barh(y, T.ran_share * 100, color=C0, height=0.6)
for yy, v in zip(y, T.ran_share * 100): a1.text(v + 1, yy, f'{v:.0f}%', va='center', fontsize=9, color=INK)
a1.set_yticks(y); a1.set_yticklabels(T.type); a1.set_xlim(0, 100); a1.set_xlabel('そのチェックをした記事の割合（%）'); a1.set_title('よく使ったチェック', loc='left', fontsize=11)
ci = np.array([ast.literal_eval(c) for c in T.hit_ci]) * 100
a2.errorbar(T.hit_rate * 100, y, xerr=[T.hit_rate * 100 - ci[:, 0], ci[:, 1] - T.hit_rate * 100], fmt='o', color=ACC, ecolor='#B8C7D6', capsize=0, ms=6)
for yy, v, n, m in zip(y, T.hit_rate * 100, T.ran, T.moved_among_ran): a2.text(41, yy, f'{m}/{n}', va='center', fontsize=8.5, color='#6B7785')
a2.set_xlim(0, 46); a2.set_xlabel('そのチェックが結論を動かした割合（%、95%区間）'); a2.set_title('よく効いたチェック', loc='left', fontsize=11)
a2.text(41, len(T) - 0.3, '動かした/した', fontsize=8, color='#6B7785', ha='center')
fig.suptitle('いちばん多く使われたチェックが、いちばん効いたわけではない', x=0.02, ha='left', fontsize=12)
fig.tight_layout(); fig.savefig('figures/fig2_used_vs_effective.png'); plt.close()

# 図3 結論を動かしたチェックの種類
mv1 = J[J.lv == 1].mover.value_counts(); mv2 = J[J.lv == 2].mover.value_counts()
ty = (mv1.add(mv2, fill_value=0)).sort_values().index
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.barh(range(len(ty)), [mv1.get(t, 0) for t in ty], color=C1, height=0.6, label='一部で弱まる・動いた（55本）')
ax.barh(range(len(ty)), [mv2.get(t, 0) for t in ty], left=[mv1.get(t, 0) for t in ty], color=C2, height=0.6, label='結論が変わった・逆になった（23本）')
for i, t in enumerate(ty): ax.text(mv1.get(t, 0) + mv2.get(t, 0) + 0.2, i, f'{int(mv1.get(t, 0) + mv2.get(t, 0))}', va='center', fontsize=9, color=INK)
ax.set_yticks(range(len(ty))); ax.set_yticklabels(ty); ax.set_xlabel('記事の数（いちばん結論を動かしたチェックで数える）')
ax.legend(frameon=False, fontsize=9.5, loc='lower right'); ax.set_title('結論を動かしたのは、どの種類のチェックだったか', loc='left', fontsize=12)
fig.tight_layout(); fig.savefig('figures/fig3_movers.png'); plt.close()

# 図4 F125 の結論の判定との関係
lab = {'Y': 'はっきり', 'U': '言い切れない', 'N': '見えなかった'}
fig, ax = plt.subplots(figsize=(8.4, 3.2))
for i, o in enumerate(['N', 'U', 'Y']):
    s = M[M.outcome == o].lv; left = 0
    for k, c in zip([0, 1, 2], [C0, C1, C2]):
        v = (s == k).mean() * 100; ax.barh(i, v, left=left, color=c, height=0.6, edgecolor='white')
        if v >= 6: ax.text(left + v / 2, i, f'{v:.0f}%', ha='center', va='center', color='white' if k else INK, fontsize=10)
        left += v
ax.set_yticks(range(3)); ax.set_yticklabels([f'{lab[o]}（{(M.outcome == o).sum()}本）' for o in ['N', 'U', 'Y']])
ax.set_xlim(0, 100); ax.set_xlabel('記事の割合（%）')
ax.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in [C0, C1, C2]], LBL, ncol=3, loc='upper center', bbox_to_anchor=(0.45, 1.28), frameon=False, fontsize=9.5)
ax.set_title('F125 で結論が「はっきり」だった記事ほど、頑健性チェックで結論が変わりにくい', loc='left', fontsize=11.5, pad=34)
fig.tight_layout(); fig.savefig('figures/fig4_by_conclusion.png'); plt.close()

# 図5 チェックの数と判定
fig, ax = plt.subplots(figsize=(8.6, 3.8))
for k, c in zip([0, 1, 2], [C0, C1, C2]):
    s = J[J.lv == k]; ax.scatter(s.n, s.n_checks, s=26, color=c, label=LBL[k], alpha=.9, edgecolor='white', linewidth=.5)
ax.set_xlabel('記事の番号（F01〜F125）'); ax.set_ylabel('README に書いた\nチェックの数')
ax.legend(frameon=False, fontsize=9, ncol=3, loc='upper left')
med = J.groupby('lv').n_checks.median()
ax.set_title(f'チェックを多く書いた記事ほど結論が動いた、とは言えない（中央値 {med[0]:.0f}・{med[1]:.0f}・{med[2]:.0f}件）', loc='left', fontsize=11.5)
fig.tight_layout(); fig.savefig('figures/fig5_checks_count.png'); plt.close()

# 図6 頑健性：数え方を変えたときの効き目
R = pd.read_csv('results/robustness.csv')
cols = [('variables', '変数・調整'), ('model', 'モデル・推定法'), ('period', '期間・時期'), ('definition', '定義・指標'), ('sample', '対象を絞る・除く')]
fig, ax = plt.subplots(figsize=(9.2, 4.4))
rr = R[R.check != '項目10件あたりで数える'].reset_index(drop=True)
mk = ['o', 's', '^', 'D', 'v']; colors = [ACC, '#5B8E7D', '#E0A458', '#8E6C8A', '#9AA5B1']
for j, (c, nm) in enumerate(cols):
    ax.plot(rr[c] * 100, np.arange(len(rr)) + (j - 2) * 0.1, mk[j], color=colors[j], label=nm, ms=6)
ax.set_yticks(range(len(rr))); ax.set_yticklabels(rr.check, fontsize=9.5); ax.invert_yaxis()
ax.set_xlabel('そのチェックをした記事のうち、結論を動かした割合（%）')
ax.legend(frameon=False, fontsize=9, ncol=5, loc='upper center', bbox_to_anchor=(0.4, 1.13))
ax.set_title('数え方を変えても「対象を絞る・除く」は効き目が小さい側', loc='left', fontsize=12, pad=26)
fig.tight_layout(); fig.savefig('figures/fig6_robustness.png'); plt.close()
print('ok')
