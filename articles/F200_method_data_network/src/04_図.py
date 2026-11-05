"""図を作る（Noto Sans CJK JP）"""
import os, json
import numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.unicode_minus'] = False
B = os.path.join(os.path.dirname(__file__), '..'); R = os.path.join(B, 'results'); F = os.path.join(B, 'figures'); D = os.path.join(B, 'data')
os.makedirs(F, exist_ok=True)
S = json.load(open(os.path.join(R, 'summary.json'), encoding='utf-8'))
dic = json.load(open(os.path.join(D, 'dictionaries.json'), encoding='utf-8'))
FAM, DG = dic['families'], dic['data_groups']
COL = dict(zip(FAM, ['#c0392b', '#2c7fb8', '#f39c12', '#8e44ad', '#16a085', '#27ae60', '#d35400', '#7f8c8d', '#e84393', '#34495e', '#b8860b', '#00a8b5', '#6c5ce7']))
TOOLS = ['ブートストラップ', '標本誤差・不確かさ', '置換検定', 'モンテカルロ・擬似データ', '交差検証・予測の評価']

# 図1 よく使った手法（上位20）
c = pd.read_csv(os.path.join(R, 'method_counts.csv')).head(20).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 7.2))
bars = ax.barh(c.method, c.articles, color=[COL[f] for f in c.family], edgecolor='black', linewidth=0.4)
for b, t in zip(bars, c.method):
    if t in TOOLS: b.set_hatch('///'); b.set_alpha(0.75)
for y, v in enumerate(c.articles): ax.text(v + 0.4, y, str(v), va='center', fontsize=9)
ax.set_xlabel('使った記事の数（197本のうち）')
ax.set_title('図1 よく使った手法の上位20（斜線は、どの手法にも添えて使う「道具」）', fontsize=12, loc='left')
fams = [f for f in FAM if f in set(c.family)]
ax.legend(handles=[Patch(color=COL[f], label=f) for f in fams], fontsize=8, loc='lower right', frameon=False)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(F, 'fig1_top_methods.png'), dpi=150); plt.close()

# 図2 手法の区分 × データのグループ（観測÷見込み、数字は記事の数）
cells = pd.read_csv(os.path.join(R, 'family_x_datagroup_cells.csv'))
obs = cells.pivot(index='family', columns='group', values='observed').reindex(index=FAM, columns=DG)
rat = cells.pivot(index='family', columns='group', values='ratio').reindex(index=FAM, columns=DG)
exp = cells.pivot(index='family', columns='group', values='expected').reindex(index=FAM, columns=DG)
st = pd.read_csv(os.path.join(R, 'unused_stability.csv'))
stable = set(map(tuple, st[st.n_conditions >= 4][['family', 'group']].values))
fig, ax = plt.subplots(figsize=(11, 7.4))
im = ax.imshow(np.log2(rat.values), cmap='RdBu_r', vmin=-3, vmax=3, aspect='auto')
for i, f in enumerate(FAM):
    for k, g in enumerate(DG):
        v = int(obs.loc[f, g]); ax.text(k, i, str(v), ha='center', va='center', fontsize=9, color='black' if abs(np.log2(rat.loc[f, g])) < 2 else 'white')
        if (f, g) in stable: ax.add_patch(Rectangle((k - 0.5, i - 0.5), 1, 1, fill=False, edgecolor='black', linewidth=2.2))
ax.set_xticks(range(len(DG))); ax.set_xticklabels(DG, rotation=35, ha='right', fontsize=9)
ax.set_yticks(range(len(FAM))); ax.set_yticklabels(FAM, fontsize=9)
cb = plt.colorbar(im, ax=ax, shrink=0.8); cb.set_label('独立なときの見込みとの比（log2、赤＝多い・青＝少ない）')
ax.set_title('図2 手法の区分 × データのグループ（数字は記事の数。太枠は6条件中4条件以上で「見込みがあるのに0本」）', fontsize=11, loc='left')
plt.tight_layout(); plt.savefig(os.path.join(F, 'fig2_family_x_data.png'), dpi=150); plt.close()

# 図3 手法どうしのつながり（同じ記事で2本以上一緒に使った）
nodes = pd.read_csv(os.path.join(R, 'method_network_nodes.csv')); edges = pd.read_csv(os.path.join(R, 'method_network_edges.csv'))
G = nx.Graph()
for r in nodes.itertuples():
    if r.degree > 0: G.add_node(r.method, family=r.family, articles=r.articles)
for r in edges.itertuples(): G.add_edge(r.u, r.v, w=r.articles)
pos = nx.spring_layout(G, weight='w', seed=200, k=0.8, iterations=400)
fig, ax = plt.subplots(figsize=(11, 9))
nx.draw_networkx_edges(G, pos, ax=ax, width=[0.4 + 0.35 * G[u][v]['w'] for u, v in G.edges()], alpha=0.35, edge_color='#555')
nx.draw_networkx_nodes(G, pos, ax=ax, node_size=[25 + 14 * G.nodes[n]['articles'] for n in G], node_color=[COL[G.nodes[n]['family']] for n in G], edgecolors='black', linewidths=0.4)
lab = {n: n for n in G if G.nodes[n]['articles'] >= 10 or G.degree(n) >= 9}
nx.draw_networkx_labels(G, pos, labels=lab, font_family='Noto Sans CJK JP', font_size=8, ax=ax)
ax.legend(handles=[Patch(color=COL[f], label=f) for f in FAM], fontsize=8, loc='lower left', frameon=False, ncol=2)
ax.set_title(f"図3 同じ記事で一緒に使った手法のつながり（2本以上、{G.number_of_nodes()}手法・{G.number_of_edges()}本）。円の大きさは使った記事の数", fontsize=11, loc='left')
ax.axis('off'); plt.tight_layout(); plt.savefig(os.path.join(F, 'fig3_method_network.png'), dpi=150); plt.close()

# 図4 新しい手法の出方と、主な区分の移り変わり
cum = pd.read_csv(os.path.join(R, 'cumulative_methods.csv'))
bf = pd.read_csv(os.path.join(R, 'band_family_manual.csv'), index_col=0).reindex(columns=FAM)
fig, axs = plt.subplots(1, 2, figsize=(13, 5.4), gridspec_kw=dict(width_ratios=[1, 1.25]))
ax = axs[0]; ax.step(cum.num, cum.distinct_methods, where='post', color='#2c7fb8', lw=2)
for x in [40, 80, 120, 160]: ax.axvline(x, color='#ccc', lw=0.8, ls='--')
nb = S['new_methods_by_band']
for (l, v), x in zip(nb.items(), [20, 60, 100, 140, 180]): ax.text(x, 5, f'+{v}', ha='center', fontsize=10, color='#c0392b')
ax.set_xlabel('記事の番号'); ax.set_ylabel('それまでに出てきた手法の数（辞書の区分）'); ax.set_ylim(0, 100)
ax.set_title('(a) 新しい手法は、最初の40本で6割が出そろった', fontsize=11, loc='left'); ax.spines[['top', 'right']].set_visible(False)
ax = axs[1]; share = bf.div(bf.sum(axis=1), axis=0)
left = np.zeros(len(share))
for f in FAM:
    ax.barh(share.index, share[f], left=left, color=COL[f], edgecolor='white', linewidth=0.4, label=f)
    for i, (l, v) in enumerate(zip(left, share[f])):
        if v >= 0.09: ax.text(l + v / 2, i, f'{int(bf[f].iloc[i])}', ha='center', va='center', fontsize=8, color='white')
    left += share[f].values
ax.invert_yaxis(); ax.set_xlim(0, 1); ax.set_xlabel('記事の割合（主な手法の区分・手作業）')
ax.set_title('(b) 因果推論は前半に多く、後半は「作法」と「分布・極値」が増えた', fontsize=11, loc='left')
ax.legend(fontsize=7.5, ncol=3, loc='upper center', bbox_to_anchor=(0.5, -0.13), frameon=False)
fig.suptitle('図4 時期による変化', x=0.01, ha='left', fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(F, 'fig4_over_time.png'), dpi=150); plt.close()

# 図5 頑健性：主な区分の一致と、「使われていない組み合わせ」の安定性
conf = pd.read_csv(os.path.join(R, 'primary_confusion.csv'), index_col=0).reindex(index=FAM, columns=FAM)
fig, axs = plt.subplots(1, 2, figsize=(14, 6.2), gridspec_kw=dict(width_ratios=[1.15, 1]))
ax = axs[0]; norm = conf.div(conf.sum(axis=1).replace(0, 1), axis=0)
ax.imshow(norm.values, cmap='Blues', vmin=0, vmax=1)
for i in range(len(FAM)):
    for k in range(len(FAM)):
        v = int(conf.iloc[i, k])
        if v: ax.text(k, i, str(v), ha='center', va='center', fontsize=8, color='white' if norm.iloc[i, k] > 0.6 else 'black')
ax.set_xticks(range(len(FAM))); ax.set_xticklabels(FAM, rotation=60, ha='right', fontsize=8)
ax.set_yticks(range(len(FAM))); ax.set_yticklabels(FAM, fontsize=8)
ax.set_xlabel('辞書で決めた主な区分'); ax.set_ylabel('手作業で決めた主な区分')
ax.set_title(f"(a) 主な区分の一致 {S['primary_agree']*100:.0f}%（κ {S['primary_kappa']:.2f}）", fontsize=11, loc='left')
ax = axs[1]; s2 = st.sort_values(['n_conditions', 'expected'], ascending=[True, True]).tail(12)
lbl = [f'{f} × {g}' for f, g in zip(s2.family, s2.group)]
ax.barh(lbl, s2.n_conditions, color=['#c0392b' if n >= 4 else '#bbb' for n in s2.n_conditions])
for y, (n, o, e) in enumerate(zip(s2.n_conditions, s2.observed, s2.expected)): ax.text(n + 0.08, y, f'主の条件で{o}本（見込み{e:.1f}本）', va='center', fontsize=8)
ax.set_xlim(0, 8); ax.set_xlabel('6つの条件のうち「見込みがあるのに0本」になった数')
ax.set_title('(b) 「使われていない組み合わせ」は、条件で入れ替わる', fontsize=11, loc='left'); ax.spines[['top', 'right']].set_visible(False)
fig.suptitle('図5 分類の仕方を変えたときの頑健性', x=0.01, ha='left', fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(F, 'fig5_robustness.png'), dpi=150); plt.close()
print(sorted(os.listdir(F)))
