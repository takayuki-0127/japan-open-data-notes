"""04 図：カテゴリ別の割合（2枚）、手法の系統×カテゴリ（2枚）、1記事あたりの項目数の推移（1枚）。"""
import pandas as pd, numpy as np, pathlib, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.unicode_minus'] = False
B = pathlib.Path(__file__).resolve().parent.parent
R, F = B / 'results', B / 'figures'; F.mkdir(exist_ok=True)
cat = pd.read_csv(R / 'category_rates.csv', index_col=0)
fc = pd.read_csv(R / 'family_by_category.csv', index_col=0)
per = pd.read_csv(R / 'items_per_article.csv', index_col=0)

def bars(kind, fn, title, color):
    t = cat[cat.kind == kind].sort_values('記事の割合')
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(t))
    ax.barh(y, t['記事の割合'] * 100, color=color, alpha=.85, label='記事の割合（主の数え方）')
    ax.scatter(t['厳しい辞書'] * 100, y, marker='o', facecolor='white', edgecolor='k', zorder=3, label='辞書を厳しくした場合')
    ax.scatter(t['単一ラベル'] * 100, y, marker='x', color='k', zorder=3, label='1項目1カテゴリにした場合')
    for i, v in enumerate(t['記事の割合'] * 100): ax.text(v + 1, i, f'{v:.0f}%', va='center', fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(t.index); ax.set_xlim(0, 100)
    ax.set_xlabel('そのカテゴリが1回以上出た記事の割合（%、118本中）'); ax.set_title(title)
    ax.legend(loc='lower right', fontsize=8); fig.tight_layout(); fig.savefig(F / fn, dpi=150); plt.close(fig)

bars('change', 'fig1_change_categories.png', '設計から変えたこと：何がいちばん多かったか', '#2b6cb0')
bars('cannot', 'fig2_cannot_categories.png', '言えないこと：何がいちばん多かったか', '#c05621')

def heat(kind, fn, title, cmap):
    m = fc[(fc.kind == kind) & (fc.n_articles >= 5)].drop(columns=['kind'])
    n = m.pop('n_articles')
    cols = cat[cat.kind == kind].sort_values('記事の割合', ascending=False).index
    m = m.reindex(columns=cols).fillna(0)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    im = ax.imshow(m.values * 100, cmap=cmap, vmin=0, vmax=100, aspect='auto')
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=30, ha='right', fontsize=9)
    ax.set_yticks(range(len(m))); ax.set_yticklabels([f'{i}（{int(k)}本）' for i, k in zip(m.index, n)])
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j] * 100; ax.text(j, i, f'{v:.0f}', ha='center', va='center', fontsize=8, color='white' if v > 60 else 'black')
    fig.colorbar(im, ax=ax, label='記事の割合（%）'); ax.set_title(title)
    fig.tight_layout(); fig.savefig(F / fn, dpi=150); plt.close(fig)

heat('change', 'fig3_family_change.png', '手法の系統ごとの「設計から変えたこと」（記事5本以上の系統）', 'Blues')
heat('cannot', 'fig4_family_cannot.png', '手法の系統ごとの「言えないこと」（記事5本以上の系統）', 'Oranges')

fig, ax = plt.subplots(figsize=(9, 4.5))
p = per.sort_values('num')
for k, c, lab in (('change', '#2b6cb0', '設計から変えたこと'), ('cannot', '#c05621', '言えないこと')):
    ax.scatter(p.num, p[k], s=10, color=c, alpha=.35)
    ax.plot(p.num, p[k].rolling(15, center=True, min_periods=5).mean(), color=c, lw=2, label=f'{lab}（15本の移動平均）')
ax.set_xlabel('記事の番号（F）'); ax.set_ylabel('1記事あたりの項目数'); ax.legend(fontsize=9)
ax.set_title('1記事あたりの項目数は F80〜F100 あたりで最も多かった')
fig.tight_layout(); fig.savefig(F / 'fig5_items_per_article.png', dpi=150); plt.close(fig)
print(sorted(p.name for p in F.glob('*.png')))
