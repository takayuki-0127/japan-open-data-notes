"""04 図：figures/ に6枚"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f:
        fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(H, 'results'); F = os.path.join(H, 'figures'); D = os.path.join(H, 'data')
os.makedirs(F, exist_ok=True)
BLUE, ORANGE, GRAY, GREEN, RED, PURPLE = '#2b6cb0', '#dd6b20', '#a0aec0', '#2f855a', '#c53030', '#6b46c1'

# 1 グループ別のパススルー
A = pd.read_csv(os.path.join(R, 'A1_group_passthrough.csv'))
fig, ax = plt.subplots(figsize=(9, 5.2))
g = A[A.group == '総合']
ax.fill_between(g.h, g.pt - 1.96 * g.pt_se, g.pt + 1.96 * g.pt_se, color=GRAY, alpha=.35, label='総合の95%区間')
for name, c in [('総合', 'k'), ('耐久消費財', PURPLE), ('他の工業製品', BLUE), ('食料工業製品', ORANGE), ('サービス', GREEN)]:
    s = A[A.group == name]
    ax.plot(s.h, s.pt, color=c, lw=2.4 if name == '総合' else 1.6, label=name)
ax.axhline(0, color='k', lw=.6)
ax.set_xlabel('円安が始まってからの月数'); ax.set_ylabel('パススルー率（為替1%あたりの値段の変化 %）')
ax.set_title('円安は、どのくらいの時間をかけて値段に届くのか（2015〜2026年）')
ax.legend(fontsize=9, ncol=2, loc='upper left'); ax.set_xlim(0, 24)
fig.tight_layout(); fig.savefig(os.path.join(F, 'f210_1_group_passthrough.png'), dpi=150); plt.close(fig)

# 2 品目：届く速さ（半分に届くまでの月数）と、はっきり上がった品目の数
I = pd.read_csv(os.path.join(R, 'A3_item_passthrough.csv'))
sig = I[I.t24 > 1.96]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8))
axs[0].hist(sig.half_month.dropna(), bins=np.arange(-0.5, 24.5, 1), color=BLUE)
axs[0].axvline(sig.half_month.median(), color=RED, ls='--', label=f'中央値 {sig.half_month.median():.0f}か月')
axs[0].set_xlabel('半分まで届いた月数'); axs[0].set_ylabel('品目数'); axs[0].legend()
axs[0].set_title(f'はっきり値上がりした{len(sig)}品目の「届く速さ」')
T = I.assign(sig=I.t24 > 1.96).groupby('top').agg(n=('item', 'size'), s=('sig', 'sum')).sort_values('s')
axs[1].barh(T.index, T.n, color=GRAY, label='品目数')
axs[1].barh(T.index, T.s, color=ORANGE, label='24か月後にはっきり上がった品目')
for y, (n, s) in enumerate(zip(T.n, T.s)):
    axs[1].text(n + 2, y, f'{s}/{n}', va='center', fontsize=8.5)
axs[1].set_title('10大費目ごと'); axs[1].legend(fontsize=8.5, loc='lower right')
fig.tight_layout(); fig.savefig(os.path.join(F, 'f210_2_items_speed.png'), dpi=150); plt.close(fig)

# 3 品目：パススルーと2020→2025年の値上がり
fig, ax = plt.subplots(figsize=(8.5, 6))
c = I.dropna(subset=['pt24', 'chg_2020_2025'])
c = c[(c.pt24.abs() < 3) & (c.chg_2020_2025.abs() < 80)]
sz = 10 + 300 * c.w / c.w.max()
ax.scatter(c.pt24, c.chg_2020_2025, s=sz, c=np.where(c.t24 > 1.96, ORANGE, GRAY), alpha=.6, edgecolor='none')
for _, r in c[c.item.isin(['ガソリン', '電気代', '電気洗濯機（全自動洗濯機）', 'カレールウ', '外国パック旅行費', 'チョコレート', '焼豚'])].iterrows():
    ax.annotate(r['item'], (r.pt24, r.chg_2020_2025), fontsize=8, xytext=(4, 2), textcoords='offset points')
ax.axvline(0, color='k', lw=.5); ax.axhline(0, color='k', lw=.5)
ax.set_xlabel('24か月後のパススルー率（為替1%あたり）'); ax.set_ylabel('2020→2025年の値上がり（%）')
O = json.load(open(os.path.join(R, 'main.json')))
ax.set_title(f'円安が届きやすい品目ほど、この5年で値上がりした（順位相関 {O["A"]["rho_pt_chg"]:.2f}）')
fig.tight_layout(); fig.savefig(os.path.join(F, 'f210_3_items_vs_rise.png'), dpi=150); plt.close(fig)

# 4 頑健性
RB = pd.read_csv(os.path.join(R, 'A6_robustness.csv'))
groups = ['総合', '耐久消費財', '他の工業製品', '食料工業製品', '石油製品', '電気・都市ガス・水道']
specs = list(dict.fromkeys(RB.spec))
cols = [BLUE, ORANGE, GREEN, PURPLE, RED, '#718096']
fig, ax = plt.subplots(figsize=(9.5, 6.8))
for j, sp in enumerate(specs):
    s = RB[RB.spec == sp].set_index('group').reindex(groups)
    y = np.arange(len(groups)) + (j - 2.5) * 0.12
    ax.errorbar(s.pt24, y, xerr=1.96 * s.pt24_se.abs(), fmt='o', color=cols[j], ms=4, lw=.8, label=sp)
ax.set_yticks(range(len(groups))); ax.set_yticklabels(groups); ax.invert_yaxis()
ax.axvline(0, color='k', lw=.6); ax.set_xlim(-2.5, 2.0)
ax.set_xlabel('24か月後のパススルー率（点と95%区間）'); ax.set_title('作り方を変えても、工業製品は「プラスで小さめ」。エネルギーは定まらない')
ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(F, 'f210_4_robustness.png'), dpi=150); plt.close(fig)

# 5 見通しの推移
Q = pd.read_csv(os.path.join(D, 'expectations_quarterly.csv'), index_col=0)
x = pd.to_datetime(Q.index)
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.plot(x, Q.hh_1y, color=ORANGE, lw=2, marker='o', ms=3, label='家計の1年後の見通し（消費動向調査から推定）')
ax.plot(x, Q.firm_1y, color=BLUE, lw=2, marker='o', ms=3, label='企業の1年後の見通し（短観）')
ax.plot(x, Q.firm_5y, color=BLUE, lw=1, ls=':', label='企業の5年後の見通し（短観）')
ax.plot(x, Q.all_now, color=GRAY, lw=1.5, label='その時点の物価（CPI 総合・前年比）')
ax.plot(x, Q.all_t12, color='k', lw=1.6, ls='--', label='1年後に実際になった物価')
ax.axhline(0, color='k', lw=.5)
ax.set_ylabel('%'); ax.set_title('家計の見通しはいつも実際より高く、企業の見通しは実際に近い（2014〜2026年、四半期）')
ax.legend(fontsize=8.5, loc='upper left')
fig.tight_layout(); fig.savefig(os.path.join(F, 'f210_5_expectations.png'), dpi=150); plt.close(fig)

# 6 当たり方
RB2 = pd.read_csv(os.path.join(R, 'B4_robustness.csv'))
E = RB2[(RB2.realized == '総合') & (RB2.series.isin(['家計 基本（δ推定）', '企業 全規模', '企業 大企業', '企業 中小企業']))]
B2 = pd.read_csv(os.path.join(R, 'B2_accuracy.csv'))
REG = pd.read_csv(os.path.join(R, 'B3_backward_forward.csv'))
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.8))
pers = ['2014〜2021年', '2022年〜', '全期間']
ser = ['家計 基本（δ推定）', '企業 全規模', '企業 大企業', '企業 中小企業']
lab = ['家計', '企業（全規模）', '企業（大企業）', '企業（中小企業）']
cc = [ORANGE, BLUE, '#63b3ed', '#2c5282']
w = .2
for k, (s, l, c) in enumerate(zip(ser, lab, cc)):
    v = E[E.series == s].set_index('period').reindex(pers)
    axs[0].bar(np.arange(3) + (k - 1.5) * w, v.mean_err, w, color=c, label=l)
axs[0].axhline(0, color='k', lw=.6); axs[0].set_xticks(range(3)); axs[0].set_xticklabels(pers)
axs[0].set_ylabel('見通し − 1年後の実際（ポイント）'); axs[0].set_title('平均の外れ（＋は高すぎ）'); axs[0].legend(fontsize=8.5)
lbl = ['家計', '企業']
axs[1].bar(np.arange(2) - .18, REG.b_now, .36, yerr=1.96 * REG.se_now, color=GRAY, label='その時点の物価への係数')
axs[1].bar(np.arange(2) + .18, REG.b_t12, .36, yerr=1.96 * REG.se_t12, color=GREEN, label='1年後の実際の物価への係数')
axs[1].set_xticks(range(2)); axs[1].set_xticklabels(lbl); axs[1].legend(fontsize=8.5)
axs[1].set_title('見通しは「いま」に引っぱられる（回帰の係数と95%区間）')
fig.tight_layout(); fig.savefig(os.path.join(F, 'f210_6_accuracy.png'), dpi=150); plt.close(fig)
print('ok')
