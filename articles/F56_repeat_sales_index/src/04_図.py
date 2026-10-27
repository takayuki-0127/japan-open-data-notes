"""04：図を作る（03 の結果を読む）"""
from common import *
idx = pd.read_csv(RES / 'index_quarterly.csv')
s = pd.read_csv(RES / 'summary.csv', index_col=0)['value']
rb = pd.read_csv(RES / 'robustness.csv', index_col=0)['chg_2015_2025_pct']
gap = pd.read_csv(RES / 'gap_dist.csv', index_col=0)['pairs']
rev = pd.read_csv(RES / 'revision_2020.csv')
x = pd.PeriodIndex(idx.quarter, freq='Q').to_timestamp()
NOTE = SOURCE + '（東京都の中古マンション等、2015年1〜3月期〜2026年1〜3月期）'

# 1 指数の比較
fig, ax = plt.subplots(figsize=(9.5, 4.6))
ax.fill_between(x, idx.rs_cs_lo, idx.rs_cs_hi, color='#f6c9b4', alpha=0.6)
ax.plot(x, idx.rs_cs, color=ORANGE, lw=2, label=f"繰り返し売買法（そのまま）：+{s.chg_rs_cs:.0f}%")
ax.plot(x, idx.rs_ageadj, color=PURPLE, lw=2, label=f"繰り返し売買法（築年の効果を差し引く）：+{s.chg_rs_ageadj:.0f}%")
ax.plot(x, idx.hedonic_all, color=BLUE, lw=2, label=f"ヘドニック法：+{s.chg_hed_all:.0f}%")
ax.plot(x, idx['median'], color=GRAY, lw=1.2, ls='--', label=f"単純な中央値：+{s.chg_median:.0f}%")
ax.axhline(100, color=INK, lw=0.6); ax.set_ylabel('2015年1〜3月期＝100')
ax.legend(frameon=False, loc='upper left', fontsize=9.5)
ax.set_title('東京の中古マンション価格指数：同じ住戸の売り直しで測ると上がり方は小さく見える', loc='left', fontsize=12)
fig.text(0.01, -0.06, NOTE + '\n%は2015年平均→2025年平均。オレンジの帯は繰り返し売買法の95%区間（ブートストラップ200回）', fontsize=7, color='#8a8984')
fig.savefig(FIG / 'f56_index.png'); plt.close(fig)

# 2 方法別の上昇率と、差の理由
fig, ax = plt.subplots(figsize=(8.5, 3.8))
labs = ['単純な中央値', '繰り返し売買法\n（そのまま）', '繰り返し売買法\n（築年の効果を差し引く）', 'ヘドニック法']
vals = [s.chg_median, s.chg_rs_cs, s.chg_rs_ageadj, s.chg_hed_all]
cols = [GRAY, ORANGE, PURPLE, BLUE]
ax.barh(labs[::-1], vals[::-1], color=cols[::-1])
for i, v in enumerate(vals[::-1]): ax.text(v + 1, i, f'+{v:.1f}%', va='center', fontsize=10)
ax.set_xlim(0, 95); ax.set_xlabel('2015年→2025年の上昇率（%）')
ax.set_title(f'同じ住戸は売り直すまでに古くなる：1年で約{abs(s.ann_age_effect_pct):.1f}%分。差し引くとヘドニックに近づく', loc='left', fontsize=11.5)
fig.text(0.01, -0.06, NOTE + '\n築年の効果はヘドニック回帰の築年数の係数（2次）から計算', fontsize=7, color='#8a8984')
fig.savefig(FIG / 'f56_methods.png'); plt.close(fig)

# 3 ペアの数と間隔
fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.7))
g = gap.copy(); g.index = g.index / 4
axs[0].bar(g.index, g.values, width=0.22, color=ORANGE)
axs[0].set_xlabel('1回目と2回目の取引の間隔（年）'); axs[0].set_title(f'ペア {int(s.n_pairs_strict):,}組の間隔（中央値 {s.gap_median_q/4:.2f}年）', loc='left', fontsize=10.5)
axs[1].plot(x, idx.n_trans, color=GRAY, label='すべての取引')
axs[1].plot(x, idx.n_pairs_end, color=ORANGE, label='ペアの2回目の取引')
axs[1].legend(frameon=False, fontsize=9); axs[1].set_title('四半期ごとの件数', loc='left', fontsize=10.5)
axs[1].tick_params(axis='x', labelsize=8)
fig.suptitle('「同じ建物・同じ間取り・同じ面積」を同じ住戸とみなしてペアを作った', x=0.01, ha='left', fontsize=12)
fig.text(0.01, -0.06, NOTE, fontsize=7, color='#8a8984'); fig.tight_layout(); fig.savefig(FIG / 'f56_pairs.png'); plt.close(fig)

# 4 ペアに入った取引と全体の違い
fig, axs = plt.subplots(1, 4, figsize=(10.5, 3.2))
items = [('築年数（平均、年）', s.pair_age1_mean, s.all_age_mean), ('面積（平均、㎡）', s.pair_area_mean, s.all_area_mean),
         ('23区の割合（%）', s.pair_23share, s.all_23share), ('駅まで（平均、分）', s.pair_walk_mean, s.all_walk_mean)]
for ax, (lab, a, b) in zip(axs, items):
    ax.bar(['ペア', '全体'], [a, b], color=[ORANGE, GRAY]); ax.set_title(lab, fontsize=10, loc='left')
    for i, v in enumerate([a, b]): ax.text(i, v, f'{v:.1f}', ha='center', va='bottom', fontsize=9)
fig.suptitle('ペアになる取引は、狭め・やや新しめ・23区が多め（投資用の小さい住戸が多いのかもしれない：推測）', x=0.01, ha='left', fontsize=11.5)
fig.text(0.01, -0.06, NOTE + '\nペアの築年数は1回目の取引の時点', fontsize=7, color='#8a8984'); fig.tight_layout(); fig.savefig(FIG / 'f56_sample.png'); plt.close(fig)

# 5 頑健性
r = rb.copy()
fig, ax = plt.subplots(figsize=(9, 4.8))
c = [GRAY if k.startswith('（参考）') else (PURPLE if '築年' in k else ORANGE) for k in r.index]
ax.barh(r.index[::-1], r.values[::-1], color=c[::-1])
for i, v in enumerate(r.values[::-1]): ax.text(v + 1, i, f'+{v:.1f}%', va='center', fontsize=9)
ax.set_xlim(0, 95); ax.set_xlabel('2015年→2025年の上昇率（%）'); ax.tick_params(axis='y', labelsize=9)
ax.set_title('ペアの作り方を変えても、繰り返し売買法（そのまま）は+32〜47%', loc='left', fontsize=12)
fig.text(0.01, -0.05, NOTE, fontsize=7, color='#8a8984'); fig.savefig(FIG / 'f56_robust.png'); plt.close(fig)

# 6 改定（GitHub のみ）
xr = pd.PeriodIndex(rev.quarter, freq='Q').to_timestamp()
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.plot(xr, rev.rs_full, color=ORANGE, lw=2, label='繰り返し売買法（全期間のデータ）')
ax.plot(xr, rev.rs_upto2020, color=ORANGE, lw=1.2, ls='--', label='繰り返し売買法（2020年末までのデータ）')
ax.plot(xr, rev.hed_full, color=BLUE, lw=2, label='ヘドニック法（全期間）')
ax.plot(xr, rev.hed_upto2020, color=BLUE, lw=1.2, ls='--', label='ヘドニック法（2020年末まで）')
ax.legend(frameon=False, fontsize=9); ax.set_ylabel('2015年1〜3月期＝100')
ax.set_title(f'あとから取引が加わると過去の値も動く：平均で繰り返し売買法 {s.revision_rs_mean:.2f}%、ヘドニック法 {s.revision_hed_mean:.2f}%', loc='left', fontsize=11)
fig.text(0.01, -0.06, NOTE + '（繰り返し売買法はここだけ重みなし）', fontsize=7, color='#8a8984'); fig.savefig(FIG / 'f56_revision.png'); plt.close(fig)
print('ok')
