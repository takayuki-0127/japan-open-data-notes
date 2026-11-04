# 04 図：data/metrics_by_year.csv と results/*.csv から図を作る。
import sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
m = pd.read_csv(f'{OUT}/data/metrics_by_year.csv')
NAME = {'keizai': '経済白書・経済財政白書', 'joho': '通信白書・情報通信白書', 'kokudo': '国土交通白書'}
COL = {'keizai': '#2a6f97', 'joho': '#e07a5f', 'kokudo': '#3d8b5a'}

def roll(s, w=5): return s.rolling(w, center=True, min_periods=3).mean()

def panel(ax, col, ylab, scale=1):
    for wp in ['keizai', 'joho', 'kokudo']:
        t = m[m.wp == wp].sort_values('year')
        if t.empty: continue
        ax.plot(t.year, t[col] * scale, 'o', ms=2.5, alpha=.35, color=COL[wp])
        ax.plot(t.year, roll(t[col] * scale), '-', lw=2, color=COL[wp], label=NAME[wp])
    ax.set_ylabel(ylab); ax.grid(axis='y', alpha=.3)

fig, ax = plt.subplots(figsize=(8, 4.6))
panel(ax, 'len_mean', '1文の平均の長さ（字）')
ax.set_title('1文の長さ：経済白書は1980年代までに短くなったが、2020年代にまた長くなった', loc='left', fontsize=11)
ax.legend(frameon=False, fontsize=9); ax.set_xlabel('白書の年（点は各年、線は前後5年の平均）')
fig.tight_layout(); fig.savefig(f'{OUT}/figures/fig1_sentence_length.png', dpi=150); plt.close()

fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
panel(axs[0], 'kanji_nonum', '文字に占める割合（%）', 100); axs[0].set_title('漢字（漢数字を除く）', loc='left', fontsize=11)
panel(axs[1], 'kata_text', '文字に占める割合（%）', 100); axs[1].set_title('カタカナ', loc='left', fontsize=11)
axs[0].legend(frameon=False, fontsize=8)
fig.suptitle('文字：漢字の割合はほぼ横ばいで、増えたのはカタカナ', x=0.01, ha='left', fontsize=12)
fig.tight_layout(); fig.savefig(f'{OUT}/figures/fig2_kanji.png', dpi=150); plt.close()

fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
panel(axs[0], 'kango', '漢語の割合（語の%）', 100); axs[0].set_title('漢語（音読みの語）の割合', loc='left', fontsize=11)
panel(axs[1], 'gairai', '外来語の割合（語の%）', 100); axs[1].set_title('外来語（カタカナ語など）の割合', loc='left', fontsize=11)
axs[0].legend(frameon=False, fontsize=8)
fig.suptitle('語彙：漢語（音読みの語）は減らず、外来語は約2倍に', x=0.01, ha='left', fontsize=12)
fig.tight_layout(); fig.savefig(f'{OUT}/figures/fig3_vocab.png', dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(8, 4.6))
panel(ax, 'jread', 'jReadability（大きいほどやさしい）')
ax.axhline(0.5, color='gray', lw=.8, ls=':'); ax.text(m.year.min(), 0.55, '0.5（ここから上が「上級後半」の区分）', fontsize=8, color='gray')
ax.set_title('総合の読みやすさ（jReadability）：どの年も、いちばん難しい区分より下にとどまる', loc='left', fontsize=11)
ax.legend(frameon=False, fontsize=9); ax.set_xlabel('白書の年')
fig.tight_layout(); fig.savefig(f'{OUT}/figures/fig4_jread.png', dpi=150); plt.close()

r = pd.read_csv(f'{OUT}/results/robust_summary.csv')
fig, ax = plt.subplots(figsize=(9, 5))
r = r.iloc[::-1].reset_index(drop=True)
for i, row in r.iterrows():
    c = '#2a6f97' if row.hi < 0 else ('#c0392b' if row.lo > 0 else 'gray')
    ax.plot([row.lo, row.hi], [i, i], color=c, lw=2); ax.plot(row.per10y, i, 'o', color=c)
ax.axvline(0, color='k', lw=.8)
ax.set_yticks(range(len(r))); ax.set_yticklabels(r.label, fontsize=8)
ax.set_xlabel('2004〜2025年の、1文の長さの変化（字／10年、95%区間）')
ax.set_title('2004年以降：はっきり短くなった条件は1つもない（赤＝はっきり長くなった）', loc='left', fontsize=11)
fig.tight_layout(); fig.savefig(f'{OUT}/figures/fig5_robustness.png', dpi=150); plt.close()
print('ok')
