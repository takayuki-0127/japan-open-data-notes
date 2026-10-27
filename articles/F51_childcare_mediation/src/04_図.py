"""04 図"""
import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from common import ROOT, UNIT
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f:
        font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False
FIG = ROOT / 'figures'; FIG.mkdir(exist_ok=True)
R = json.load(open(ROOT / 'results/results.json', encoding='utf-8'))
d = pd.read_csv(ROOT / 'data/analysis.csv', dtype={'code': str})
BLUE, GRAY, ORANGE = '#2b6cb0', '#8a8f98', '#dd6b20'
K = 1000  # 出生率は 0.001 単位（‰ポイント）で表示


def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG / name, dpi=150); plt.close(fig)


def ci(v, k):
    return f"[{v['ci'][k][0]*K:+.1f}, {v['ci'][k][1]*K:+.1f}]"


# 1 経路の図
m = R['main']
fig, ax = plt.subplots(figsize=(8, 4.2)); ax.axis('off'); ax.set_xlim(0, 10); ax.set_ylim(0, 5)
def box(x, y, t):
    ax.add_patch(FancyBboxPatch((x - 1.4, y - .45), 2.8, .9, boxstyle='round,pad=0.05', fc='#edf2f7', ec=BLUE))
    ax.text(x, y, t, ha='center', va='center', fontsize=10.5)
box(1.6, 1, '保育所に通う子どもの増加\n（0〜5歳100人あたり+10人）'); box(5, 4, '女性の労働力率の変化\n（2010→15年）'); box(8.4, 1, '合計特殊出生率の変化\n（2013〜17年→2018〜22年）')
ax.annotate('', (4.0, 3.55), (2.4, 1.45), arrowprops=dict(arrowstyle='->', color=BLUE, lw=1.6))
ax.annotate('', (7.6, 1.45), (6.0, 3.55), arrowprops=dict(arrowstyle='->', color=BLUE, lw=1.6))
ax.annotate('', (7.0, 1), (3.0, 1), arrowprops=dict(arrowstyle='->', color=GRAY, lw=1.6))
ax.text(1.0, 2.7, f"a = {m['a']:+.3f} pt\n{['[{:+.3f}, {:+.3f}]'.format(*m['ci']['a'])][0]}", fontsize=9.5, color=BLUE)
ax.text(6.9, 2.7, f"b = {m['b']*K:+.2f}‰/pt\n{['[{:+.2f}, {:+.2f}]'.format(m['ci']['b'][0]*K, m['ci']['b'][1]*K)][0]}", fontsize=9.5, color=BLUE)
ax.text(5, .45, f"直接 c' = {m['cp']*K:+.1f}‰  {ci(m,'cp')}", ha='center', fontsize=9.5, color=GRAY)
ax.text(5, 2.0, f"間接 a×b = {m['ab']*K:+.2f}‰  {ci(m,'ab')}", ha='center', fontsize=10.5, color=ORANGE)
ax.set_title(f"経路ごとの効果（{m['n']:,}市区町村、‰ポイント＝出生率0.001）", fontsize=11)
save(fig, 'f51_paths.png')

# 2 3つの関係の散布図
fig, axs = plt.subplots(1, 3, figsize=(12, 4))
pairs = [('T', 'M', '在所児の増加（100人あたり人）', '労働力率の変化（pt）', UNIT, 1),
         ('M', 'Y', '労働力率の変化（pt）', '出生率の変化（‰）', 1, K),
         ('T', 'Y', '在所児の増加（100人あたり人）', '出生率の変化（‰）', UNIT, K)]
for ax, (xc, yc, xl, yl, sx, sy) in zip(axs, pairs):
    x = d[xc] * sx; y = d[yc] * sy
    ax.scatter(x, y, s=5, alpha=.25, color=GRAY, edgecolor='none')
    b = pd.qcut(x, 20, duplicates='drop'); g = pd.DataFrame({'x': x, 'y': y}).groupby(b, observed=True).mean()
    ax.plot(g.x, g.y, 'o-', color=BLUE, ms=3.5)
    lo, hi = x.quantile([.01, .99]); ax.set_xlim(lo, hi); ax.set_ylim(*y.quantile([.01, .99]))
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_title(f"相関 {np.corrcoef(x, y)[0,1]:+.2f}", fontsize=10)
fig.suptitle('処置・媒介・結果の関係（灰色の点は市区町村、青は20等分した平均。条件の調整前）', fontsize=11)
save(fig, 'f51_scatter.png')

# 3 総合・直接・間接の比較（基本・statsmodels）
s = R['statsmodels']
fig, ax = plt.subplots(figsize=(8, 4.4))
labs = ['総合効果 c', '直接効果 c′', '間接効果 a×b']
vals = [m['c'], m['cp'], m['ab']]; los = [m['ci']['c'][0], m['ci']['cp'][0], m['ci']['ab'][0]]; his = [m['ci']['c'][1], m['ci']['cp'][1], m['ci']['ab'][1]]
sv = [s['Total effect'], s['ADE (average)'], s['ACME (average)']]
y = np.arange(3)
ax.errorbar(np.array(vals) * K, y + .12, xerr=[(np.array(vals) - los) * K, (np.array(his) - vals) * K], fmt='o', color=BLUE, capsize=3, label='積の方法（ブートストラップ1,000回）')
ax.errorbar(np.array([v[0] for v in sv]) * K, y - .12, xerr=[[(v[0] - v[1]) * K for v in sv], [(v[2] - v[0]) * K for v in sv]], fmt='s', color=ORANGE, capsize=3, label='statsmodels Mediation（500回）')
ax.axvline(0, color='k', lw=.8); ax.set_yticks(y); ax.set_yticklabels(labs); ax.invert_yaxis()
ax.set_xlabel('出生率の変化（‰ポイント、在所児+10人あたり）'); ax.legend(fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
ax.set_title('効果の分け方（95%区間）', fontsize=11)
save(fig, 'f51_decomp.png')

# 4 感度分析
g = pd.DataFrame(R['sens']['grid'], columns=['rho', 'acme']); g = g[g.rho.abs() <= 0.3]
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(g.rho, g.acme * K, color=BLUE); ax.axhline(0, color='k', lw=.8); ax.axvline(0, color=GRAY, lw=.8, ls=':')
rt = R['sens']['rho_tilde']; ax.axvline(rt, color=ORANGE, ls='--', lw=1)
ax.text(rt, ax.get_ylim()[1] * .85, f' ρ = {rt:+.3f} で間接効果が0', color=ORANGE, fontsize=9.5)
ax.set_xlabel('ρ：労働力率と出生率の両方を動かす「見えない要因」の強さ（誤差の相関）'); ax.set_ylabel('間接効果（‰ポイント）')
ax.set_title('感度分析：見えない交絡があると、間接効果はどう変わるか', fontsize=11)
save(fig, 'f51_sensitivity.png')

# 5 頑健性
rb = R['robust']
names = list(rb.keys())
fig, ax = plt.subplots(figsize=(8.5, 4.6))
for i, k in enumerate(names):
    v = rb[k]; ax.errorbar(v['ab'] * K, i, xerr=[[(v['ab'] - v['ci']['ab'][0]) * K], [(v['ci']['ab'][1] - v['ab']) * K]], fmt='o', color=ORANGE if i == 0 else BLUE, capsize=3)
    ax.text(ax.get_xlim()[1] if False else 0, i, '', fontsize=8)
ax.axvline(0, color='k', lw=.8); ax.set_yticks(range(len(names))); ax.set_yticklabels([f"{k}（{rb[k]['n']:,}）" for k in names], fontsize=9); ax.invert_yaxis()
ax.set_xlabel('間接効果 a×b（‰ポイント、95%区間）'); ax.set_title('頑健性：設定を変えたときの間接効果', fontsize=11)
save(fig, 'f51_robust.png')

# 6 人口規模別
bs = R['by_size']
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
ks = list(bs.keys())
axs[0].errorbar(range(3), [bs[k]['a'] for k in ks], yerr=[[bs[k]['a'] - bs[k]['ci']['a'][0] for k in ks], [bs[k]['ci']['a'][1] - bs[k]['a'] for k in ks]], fmt='o', color=BLUE, capsize=3)
axs[0].set_title('a：在所児+10人 → 労働力率（pt）', fontsize=10)
axs[1].errorbar(range(3), [bs[k]['ab'] * K for k in ks], yerr=[[(bs[k]['ab'] - bs[k]['ci']['ab'][0]) * K for k in ks], [(bs[k]['ci']['ab'][1] - bs[k]['ab']) * K for k in ks]], fmt='o', color=ORANGE, capsize=3)
axs[1].set_title('間接効果 a×b（‰ポイント）', fontsize=10)
for ax in axs:
    ax.axhline(0, color='k', lw=.8); ax.set_xticks(range(3)); ax.set_xticklabels([f"人口{k}（{bs[k]['n']}）" for k in ks])
fig.suptitle('人口規模を3つに分けた場合（95%区間）', fontsize=11)
save(fig, 'f51_by_size.png')
print('ok')
