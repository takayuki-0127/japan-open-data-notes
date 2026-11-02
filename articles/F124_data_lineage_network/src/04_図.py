import os, json
import pandas as pd, numpy as np, networkx as nx
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Arc
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
B = os.path.join(os.path.dirname(__file__), '..'); D, R, F = f'{B}/data', f'{B}/results', f'{B}/figures'
deg = pd.read_csv(f'{R}/dataset_degree.csv'); co = pd.read_csv(f'{R}/dataset_cooccurrence.csv')
ru = pd.read_csv(f'{D}/article_reuse.csv'); art = pd.read_csv(f'{D}/articles.csv'); S = json.load(open(f'{R}/summary.json', encoding='utf-8'))
groups = list(deg.group.drop_duplicates()); cmap = plt.get_cmap('tab10'); gc = {g: cmap(i % 10) for i, g in enumerate(groups)}
# 図1 よく使ったデータ
t = deg.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 6.2))
ax.barh(t.dataset, t.n_articles, color=[gc[g] for g in t.group])
for y, v in enumerate(t.n_articles): ax.text(v + 0.4, y, f'{v}本', va='center', fontsize=9)
ax.set_xlabel('使った看板記事の数（F01〜F120 の118本）'); ax.set_title('よく使ったデータ 上位15（README の「データ」「出典」から名寄せ）')
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=gc[g], label=g) for g in t.group.drop_duplicates()], loc='lower right', fontsize=8)
fig.tight_layout(); fig.savefig(f'{F}/fig1_top_datasets.png', dpi=150); plt.close()
# 図2 データの組み合わせネットワーク
G = nx.Graph(); top = deg[deg.n_articles >= 3]
for _, r in top.iterrows(): G.add_node(r.dataset, n=r.n_articles, g=r.group)
for _, r in co[co.w >= 2].iterrows():
    if r.a in G and r.b in G: G.add_edge(r.a, r.b, w=r.w)
G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
pos = nx.kamada_kawai_layout(G)
pos = nx.spring_layout(G, pos=pos, seed=7, k=1.6, weight=None, iterations=60)
lp = {n: np.array(pos[n], dtype=float) for n in G}
names = list(G)
for _ in range(60):
    moved = False
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = lp[names[i]], lp[names[j]]
            if abs(a[0] - b[0]) < 0.32 and abs(a[1] - b[1]) < 0.09:
                lp[names[j]] = b + np.array([0, -0.1 if b[1] <= a[1] else 0.1]); moved = True
    if not moved: break
pos = lp
fig, ax = plt.subplots(figsize=(12, 9.5))
nx.draw_networkx_edges(G, pos, width=[0.6 + 0.6 * G[u][v]['w'] for u, v in G.edges], alpha=0.35, edge_color='gray', ax=ax)
nx.draw_networkx_nodes(G, pos, node_size=[60 + 45 * G.nodes[n]['n'] for n in G], node_color=[gc[G.nodes[n]['g']] for n in G], alpha=0.85, ax=ax)
for n in G: ax.text(lp[n][0], lp[n][1] - 0.045, n, fontsize=8, ha='center', va='top', bbox=dict(boxstyle='round,pad=0.1', fc='white', ec='none', alpha=0.7))
ax.set_title('同じ記事で一緒に使ったデータ（3本以上で使ったデータ、2本以上で一緒に使った組み合わせ）\n円の大きさ＝使った記事の数、線の太さ＝一緒に使った記事の数', fontsize=10)
ax.axis('off'); fig.tight_layout(); fig.savefig(f'{F}/fig2_dataset_network.png', dpi=150); plt.close()
# 図3 記事どうしの再利用（弧の図）
num = lambda a: int(a[1:])
fig, ax = plt.subplots(figsize=(12, 5.2))
for _, r in ru.iterrows():
    x1, x2 = num(r.from_article), num(r.to_article); c = (x1 + x2) / 2; w = abs(x2 - x1)
    strict = r.in_code == 1
    ax.add_patch(Arc((c, 0), w, min(w, 70) * 0.8, theta1=0, theta2=180, lw=1.3 if strict else 0.7,
                     color='#c0392b' if strict else '#7f8c8d', alpha=0.75 if strict else 0.4))
outd = ru.groupby('from_article').size()
for a in art.article:
    n = outd.get(a, 0); ax.plot(num(a), 0, 'o', ms=2 + 1.2 * n, color='#2c3e50' if n else '#bdc3c7')
top6 = outd.sort_values(ascending=False).head(6)
ax.text(1, -9, '多く使われた元の記事：' + '、'.join(f'{a}（{v}本）' for a, v in top6.items()) + '　※円の大きさ＝使われた本数', fontsize=9)
ax.set_xlim(-2, 124); ax.set_ylim(-12, 32); ax.set_yticks([]); ax.set_xlabel('記事の番号（左の記事のデータを、右の記事が使った）')
ax.set_title('記事どうしのデータの使い回し（赤＝コードが別記事のフォルダを読む、灰＝README のデータ・出典欄で別記事に触れた）')
for s in ['top', 'right', 'left']: ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(f'{F}/fig3_reuse_arcs.png', dpi=150); plt.close()
# 図4 時期ごとの使い回しの割合
lo = S['reuse_loose']['trend']; st = S['reuse_strict']['trend']; k = list(lo.keys()); x = np.arange(len(k))
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.bar(x - 0.2, [lo[i] * 100 for i in k], 0.4, label='README か コードで別記事のデータを使った', color='#7f8c8d')
ax.bar(x + 0.2, [st[i] * 100 for i in k], 0.4, label='コードが別記事のフォルダを読んだ（厳しめ）', color='#c0392b')
for i, v in enumerate(k): ax.text(i - 0.2, lo[v] * 100 + 1.5, f'{lo[v]*100:.0f}%', ha='center', fontsize=8); ax.text(i + 0.2, st[v] * 100 + 1.5, f'{st[v]*100:.0f}%', ha='center', fontsize=8)
ax.set_xticks(x, k); ax.set_ylabel('前の記事のデータを使った記事の割合（%）'); ax.set_ylim(0, 100); ax.legend(fontsize=8, loc='upper left')
ax.set_title('後半の記事ほど、前の記事のデータを使い回していた')
fig.tight_layout(); fig.savefig(f'{F}/fig4_reuse_trend.png', dpi=150); plt.close()
# 図5 使い回した記事のつまずき
p = pd.read_csv(f'{R}/pitfalls_reuse_vs_not.csv'); p = p[p.category != '既存データの再利用'].sort_values('diff')
fig, ax = plt.subplots(figsize=(9, 6.3)); y = np.arange(len(p))
ax.barh(y - 0.2, p.reusers * 100, 0.4, label=f"使い回した記事（{S['n_reusers']}本）", color='#c0392b')
ax.barh(y + 0.2, p.non_reusers * 100, 0.4, label=f"使い回していない記事（{118 - S['n_reusers']}本）", color='#95a5a6')
ax.set_yticks(y, [c + ('  *' if pv < 0.05 else '') for c, pv in zip(p.category, p.p)], fontsize=9)
ax.set_xlabel('その項目が README に出てくる記事の割合（%）、* は Fisher の正確検定で p<0.05'); ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.11), ncol=2)
ax.set_title('「設計から変えたこと」「言えないこと」の出方（F122 の分類を使用）')
fig.tight_layout(); fig.savefig(f'{F}/fig5_pitfalls.png', dpi=150); plt.close()
print('ok')
