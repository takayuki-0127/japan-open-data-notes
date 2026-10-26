"""04 図"""
import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import ROOT
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f:
        font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False
FIG = ROOT / 'figures'; FIG.mkdir(exist_ok=True)
R = json.load(open(ROOT / 'results/results.json', encoding='utf-8'))
df = pd.read_csv(ROOT / 'data/analysis_2010_2015.csv', index_col=0)
BLUE, GRAY, ORANGE = '#2b6cb0', '#8a8f98', '#dd6b20'


def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG / name, dpi=150); plt.close(fig)


# 1 散布図
fig, ax = plt.subplots(figsize=(7.5, 5))
x = df.D * 10; y = df.Y
ax.scatter(x, y, s=6, alpha=0.25, color=GRAY, edgecolor='none')
bins = pd.qcut(x, 20)
m = pd.DataFrame({'x': x, 'y': y}).groupby(bins, observed=True).mean()
ax.plot(m.x, m.y, 'o-', color=BLUE, ms=4, label='20等分した平均')
b = np.polyfit(x, y, 1)
ax.set_xlim(x.quantile(0.005), x.quantile(0.995)); ax.set_ylim(y.quantile(0.005), y.quantile(0.995))
ax.axhline(0, color='k', lw=0.5); ax.axvline(0, color='k', lw=0.5)
ax.set_xlabel('保育所等に通う子どもの変化（0〜5歳100人あたり、2010→15年）')
ax.set_ylabel('女性の労働力率の変化（ポイント）')
ax.set_title(f'単純に並べると：相関 {R["describe"]["corr"]:.2f}（{R["describe"]["n"]:,}市区町村）')
ax.legend(loc='upper left', frameon=False)
save(fig, 'f16_1_scatter.png')

# 2 推定値の比較
lab = {'ols_naive': '単純な回帰\n（何もそろえない）', 'ols_ctrl': '重回帰\n（同じ変数を直線で）', 'dml_lasso': 'DML\n（Lasso）', 'dml_rf': 'DML\n（ランダムフォレスト）', 'dml_lgbm': 'DML\n（LightGBM）'}
fig, ax = plt.subplots(figsize=(7.5, 4.6))
for i, k in enumerate(lab):
    r = R[k]; c = BLUE if k.startswith('dml') else GRAY
    ax.errorbar(i, r['coef'], yerr=[[r['coef'] - r['lo']], [r['hi'] - r['coef']]], fmt='o', color=c, capsize=5, ms=7)
    ax.text(i + 0.08, r['coef'], f"{r['coef']:+.3f}", va='center', fontsize=9)
ax.axhline(0, color='k', lw=0.6)
ax.set_xticks(range(len(lab))); ax.set_xticklabels(lab.values(), fontsize=9)
ax.set_ylabel('労働力率の変化（ポイント）\n在所児が100人あたり10人増えるごと')
ax.set_title('比べ方で推定値はどう変わるか（95%信頼区間）')
save(fig, 'f16_2_estimates.png')

# 3 交差適合の繰り返し
reps = np.array(R['dml_rf_rep20']['reps'])
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.hist(reps, bins=12, color=BLUE, alpha=0.8)
ax.axvline(np.median(reps), color=ORANGE, lw=2, label=f'中央値 {np.median(reps):+.3f}')
ax.axvline(0, color='k', lw=0.6)
ax.set_xlabel('推定値（ポイント、在所児10人増あたり）'); ax.set_ylabel('回数')
ax.set_title(f'データの分け方を20通り変えた推定値（範囲 {reps.min():+.3f}〜{reps.max():+.3f}）')
ax.legend(frameon=False)
save(fig, 'f16_3_repetitions.png')

# 4 都市と地方
H = R['hetero']
fig, ax = plt.subplots(figsize=(7.5, 4.4))
keys = list(H.keys())
for i, k in enumerate(keys):
    r = H[k]
    ax.errorbar(r['coef'], i, xerr=[[r['coef'] - r['lo']], [r['hi'] - r['coef']]], fmt='o', color=BLUE if i < 3 else ORANGE, capsize=4)
    ax.text(r['hi'] + 0.01, i, f"{r['coef']:+.3f}（{r['n']}）", va='center', fontsize=9)
ax.axvline(0, color='k', lw=0.6)
ax.axvline(R['dml_rf']['coef'], color=GRAY, ls='--', lw=1)
ax.set_yticks(range(len(keys))); ax.set_yticklabels(keys); ax.invert_yaxis()
ax.set_xlabel('労働力率の変化（ポイント、在所児10人増あたり）')
ax.set_title('人口密度・2010年の水準で分けた推定（DML・ランダムフォレスト）')
save(fig, 'f16_4_hetero.png')

# 5 予測に効いた変数
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
for ax, t, title in zip(axes, ['Y', 'D'], ['女性の労働力率の変化を予測', '在所児の変化を予測']):
    s = pd.Series(R['importance'][t]).sort_values()
    ax.barh(s.index, s.values, color=BLUE if t == 'Y' else ORANGE)
    ax.set_title(title); ax.tick_params(axis='y', labelsize=8.5); ax.set_xlabel('重要度')
fig.suptitle('2つの予測に効いた地域の条件（ランダムフォレスト）')
save(fig, 'f16_5_importance.png')

# 6 頑健性とプラセボ
rob = dict(R['robust']); rob = {'基本（DML・ランダムフォレスト）': R['dml_rf'], **rob, 'プラセボ：前の5年の変化（2005→10）': R['placebo']}
fig, ax = plt.subplots(figsize=(7.5, 5.6))
for i, (k, r) in enumerate(rob.items()):
    c = ORANGE if 'プラセボ' in k else (BLUE if i == 0 else GRAY)
    ax.errorbar(r['coef'], i, xerr=[[r['coef'] - r['lo']], [r['hi'] - r['coef']]], fmt='o', color=c, capsize=3)
ax.axvline(0, color='k', lw=0.6)
ax.set_yticks(range(len(rob))); ax.set_yticklabels(rob.keys(), fontsize=9); ax.invert_yaxis()
ax.set_xlabel('推定値（ポイント、在所児10人増あたり）')
ax.set_title('設定を変えた推定と、前の期間でのプラセボ（95%信頼区間）')
save(fig, 'f16_6_robust.png')
print('ok')
