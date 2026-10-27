"""04 図：5枚（figures/）"""
import json, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

R = ROOT / 'results'; F = ROOT / 'figures'
d = make_xy(2020)
res = pd.read_csv(R / 'coef_base.csv'); grid = pd.read_csv(R / 'coef_grid.csv')
rob = pd.read_csv(R / 'robustness.csv'); qq = pd.read_csv(R / 'dist_compare.csv')
C_OLS, C_QR, C_GRAY = '#d9822b', '#2b6cb0', '#888888'

# 1 所得の分布
fig, ax = plt.subplots(figsize=(8, 4.6))
v = d['所得'].clip(upper=600)
ax.hist(v, bins=np.arange(200, 605, 10), color='#9fbfe0', edgecolor='white')
for q, ls in [(0.1, '--'), (0.5, '-'), (0.9, '--')]:
    x = d['所得'].quantile(q); ax.axvline(x, color=C_QR, ls=ls, lw=1.4)
    ax.text(x + 3, ax.get_ylim()[1] * 0.92, f'{int(q*100)}%点\n{x:.0f}万円', color=C_QR, fontsize=9, va='top')
ax.set_xlabel('納税者1人あたり課税対象所得（万円、600万円以上は右端にまとめた）'); ax.set_ylabel('市区町村の数')
ax.set_title(f'市区町村の所得の分布（{len(d):,}市区町村、2020年度）')
ax.text(0.99, 0.6, f'右に長い分布：\n最大 {d["所得"].max():.0f}万円', transform=ax.transAxes, ha='right', fontsize=9, color='#444')
fig.tight_layout(); fig.savefig(F / 'f32_dist.png', dpi=150); plt.close(fig)

# 2 分位点ごとの係数の推移（主な5変数）
fig, axes = plt.subplots(1, 5, figsize=(15, 3.9), sharey=False)
for ax, c in zip(axes, MAIN5):
    g = grid[grid['var'] == c]; r = res[(res['var'] == c) & (res.model == 'QR')]; o = res[(res['var'] == c) & (res.model == 'OLS')].iloc[0]
    ax.plot(g.q * 100, g.coef * 100, color=C_QR, lw=1.8)
    ax.errorbar(r.q * 100, r.coef * 100, yerr=[(r.coef - r.lo) * 100, (r.hi - r.coef) * 100], fmt='o', color=C_QR, ms=4, capsize=3)
    ax.axhspan(o.lo * 100, o.hi * 100, color=C_OLS, alpha=0.18); ax.axhline(o.coef * 100, color=C_OLS, lw=1.5)
    ax.axhline(0, color='#333', lw=0.6)
    ax.set_title(c, fontsize=11); ax.set_xlabel('分位点（%）'); ax.set_xticks([10, 50, 90])
axes[0].set_ylabel('1標準偏差あたりの所得の差（%）')
fig.suptitle('分位点ごとの係数（青：分位点回帰と95%区間、橙：最小二乗法）', fontsize=12)
fig.tight_layout(); fig.savefig(F / 'f32_coef_path.png', dpi=150); plt.close(fig)

# 3 最小二乗法と10%点・90%点の比較（9変数）
fig, ax = plt.subplots(figsize=(8.5, 5.2))
names = XNAMES[::-1]; y = np.arange(len(names))
for k, (lab, sel, col, off) in enumerate([('10%点', ('QR', 0.1), '#7fb3e6', -0.25), ('最小二乗法', ('OLS', None), C_OLS, 0), ('90%点', ('QR', 0.9), '#1a4f8a', 0.25)]):
    rr = []
    for c in names:
        s = res[(res['var'] == c) & (res.model == sel[0])]
        if sel[1] is not None: s = s[np.isclose(s.q, sel[1])]
        rr.append(s.iloc[0])
    rr = pd.DataFrame(rr)
    ax.errorbar(rr.coef * 100, y + off, xerr=[(rr.coef - rr.lo) * 100, (rr.hi - rr.coef) * 100], fmt='o', color=col, ms=5, capsize=2, label=lab)
ax.axvline(0, color='#333', lw=0.6); ax.set_yticks(y); ax.set_yticklabels(names)
ax.set_xlabel('1標準偏差あたりの所得の差（%）'); ax.legend(loc='lower right', fontsize=9)
ax.set_title('所得の低い町（10%点）と高い町（90%点）で、効き方は違うか')
fig.tight_layout(); fig.savefig(F / 'f32_compare.png', dpi=150); plt.close(fig)

# 4 予測した分布と実際の分布（分位点のQQ）
fig, ax = plt.subplots(figsize=(6.4, 5.4))
ax.plot(qq['実際_万円'], qq['分位点回帰_万円'], 'o', ms=3.5, color=C_QR, label='分位点回帰から作った分布')
ax.plot(qq['実際_万円'], qq['最小二乗法＋正規誤差_万円'], 's', ms=3.5, color=C_OLS, label='最小二乗法＋正規分布の誤差')
lim = [qq['実際_万円'].min() * 0.95, qq['実際_万円'].max() * 1.03]
ax.plot(lim, lim, color='#333', lw=0.8); ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel('実際の所得の分位点（万円）'); ax.set_ylabel('モデルから作った所得の分位点（万円）')
ax.set_title('予測した分布は、実際の分布の形を再現できるか'); ax.legend(fontsize=9, loc='upper left')
fig.tight_layout(); fig.savefig(F / 'f32_dist_fit.png', dpi=150); plt.close(fig)

# 5 頑健性：主な5変数の 10%点・50%点・90%点（対数の設定だけ）
tags = ['base', '23区・政令市を除く', '県ダミーあり', '2015年']
lab = {'base': '本体（2020年）', '23区・政令市を除く': '23区・政令市を除く', '県ダミーあり': '県ダミーあり', '2015年': '2015年度'}
cols = ['#2b6cb0', '#38a169', '#805ad5', '#d69e2e']
ROB5 = ['大卒の割合', '65歳以上の割合', '第1次産業の割合', 'log人口密度', '単独世帯の割合']
fig, axes = plt.subplots(1, 5, figsize=(15, 3.9))
for ax, c in zip(axes, ROB5):
    for k, t in enumerate(tags):
        r = rob[(rob.tag == t) & (rob.model == 'QR') & (rob['var'] == c)].sort_values('q')
        x = r.q.values * 100 + (k - 1.5) * 3
        ax.errorbar(x, r.coef * 100, yerr=[(r.coef - r.lo) * 100, (r.hi - r.coef) * 100], fmt='o-', color=cols[k], ms=3.5, capsize=2, lw=1, label=lab[t])
    ax.axhline(0, color='#333', lw=0.6); ax.set_xticks([10, 50, 90]); ax.set_title(c, fontsize=11); ax.set_xlabel('分位点（%）')
axes[0].set_ylabel('1標準偏差あたりの所得の差（%）'); axes[-1].legend(fontsize=8, loc='best')
fig.suptitle('設定を変えても、分位点ごとの違いは残るか', fontsize=12)
fig.tight_layout(); fig.savefig(F / 'f32_robust.png', dpi=150); plt.close(fig)
print('ok')
