"""05 図（figures/ に5枚）"""
import json
import numpy as np, pandas as pd, networkx as nx
import matplotlib.pyplot as plt
from common import RES, FIG, SOURCE, BLUE, ORANGE, GRAY, INK, GREEN, PURPLE, RED, PERIODS

r = pd.read_csv(RES / "rates_by_year.csv", keep_default_na=False)
allr = r[r.scope == ""].pivot(index="year", columns="keyword", values="per10k")


def foot(fig, extra=""):
    fig.text(0.01, -0.02, (extra + "\n" if extra else "") + SOURCE, fontsize=7.5, color="#555", ha="left", va="top")


# 図1 語の出現率の推移
fig, axes = plt.subplots(2, 1, figsize=(10, 7.4), sharex=True)
for ax, ks in zip(axes, [[("物価", BLUE), ("賃上げ", ORANGE), ("デフレ", GRAY), ("物価高", RED)],
                         [("少子化", GREEN), ("生産性", PURPLE), ("円安", INK), ("好循環", ORANGE)]]):
    for k, col in ks:
        s = allr[k]
        ax.plot(s.index[:-1], s.values[:-1], color=col, lw=2, label=k)
        ax.plot(s.index[-2:], s.values[-2:], color=col, lw=2, ls=":")
        ax.annotate(k, (s.index[-1], s.values[-1]), xytext=(4, 0), textcoords="offset points", color=col, fontsize=10, va="center")
    ax.set_ylabel("発言1万件あたり")
    ax.grid(axis="y", color="#e5e5e5")
axes[0].set_title("国会の発言に、その語が出てくる割合（全会議、1985〜2026年）", loc="left")
axes[1].set_xlim(1985, 2028.5)
foot(fig, "2026年は10月24日まで（点線）。1つの発言に何回出ても1件と数える")
fig.savefig(FIG / "f09_rates.png"); plt.close(fig)

# 図2 物価・賃上げの出現率と統計
m = pd.read_csv(RES / "merged_macro.csv", index_col=0)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, (col, stat, lab, slab, c1) in zip(axes, [("bukka", "cpi", "「物価」の出現率", "消費者物価の上昇率（%）", BLUE),
                                                 ("chinage", "wage", "「賃上げ」の出現率", "1人あたり賃金の改定率（%）", ORANGE)]):
    ax.plot(m.index, m[col], color=c1, lw=2)
    ax.set_ylabel(lab + "（1万件あたり）", color=c1)
    ax2 = ax.twinx(); ax2.plot(m.index, m[stat], color=INK, lw=1.4, ls="--"); ax2.set_ylabel(slab)
    ax2.spines["top"].set_visible(False)
    rr = m[col].corr(m[stat])
    ax.set_title(f"{lab}と{slab.split('（')[0]}（相関 {rr:.2f}）", loc="left", fontsize=11.5)
foot(fig, "実線＝発言（左の目盛り）、破線＝統計（右の目盛り）。1985〜2025年")
fig.tight_layout(); fig.savefig(FIG / "f09_macro.png"); plt.close(fig)

# 図3 共起ネットワーク
net = json.load(open(RES / "cooc_network.json"))
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
for ax, (lab, g) in zip(axes, net.items()):
    G = nx.Graph()
    for w, n in g["nodes"].items():
        G.add_node(w, n=n)
    for a, b, j in g["edges"]:
        G.add_edge(a, b, w=j)
    G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
    pos = nx.spring_layout(G, seed=3, k=0.9, weight="w")
    sz = np.array([G.nodes[n]["n"] for n in G]); sz = 200 + 1800 * sz / sz.max()
    nx.draw_networkx_edges(G, pos, ax=ax, width=[0.5 + 6 * G[a][b]["w"] for a, b in G.edges], edge_color="#bbb")
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=sz, node_color=ORANGE if "2015" in lab else BLUE, alpha=0.35)
    nx.draw_networkx_labels(G, pos, ax=ax, font_family="Noto Sans CJK JP", font_size=9)
    ax.set_title(f"「賃上げ」と一緒に出た言葉：{lab}（{g['n']}発言）", loc="left", fontsize=11.5); ax.axis("off")
foot(fig, "抜き出した発言のうち、各年代でよく出た30語。線はよく一緒に出る組（Jaccard 係数の上位45組）、丸の大きさは出た発言の数")
fig.savefig(FIG / "f09_cooc.png"); plt.close(fig)

# 図4 トピックの構成比の推移
tp = pd.read_csv(RES / "lda_k8_topics.csv")
labels = json.load(open(RES / "lda_k8_labels.json"))
sh = pd.read_csv(RES / "lda_k8_share_by_year_all.csv", index_col=0)
sh = sh.rolling(3, center=True, min_periods=1).mean()
cols = ["#2a78d6", "#eb6834", "#3aa07a", "#7a5bd6", "#c8423b", "#d6a92a", "#4bb3c4", "#a3a29c"]
fig, ax = plt.subplots(figsize=(10.5, 5))
ax.stackplot(sh.index, *[sh[f"t{j}"] for j in range(8)], colors=cols, alpha=0.85,
             labels=[labels[str(j)] for j in range(8)])
ax.set_xlim(1985, 2026); ax.set_ylim(0, 1); ax.set_ylabel("構成比（3年移動平均）")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9, frameon=False)
ax.set_title("「賃上げ」「物価」が出た発言の話題の構成（トピックモデル、8トピック）", loc="left")
foot(fig, "年ごと・語ごとに無作為に選んだ連続100発言の、語の前後150字を使った")
fig.savefig(FIG / "f09_topics.png"); plt.close(fig)

# 図5 会議の範囲と表記ゆれ（頑健性）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for k, col in [("賃上げ", ORANGE), ("物価", BLUE)]:
    w = r[r.keyword == k].pivot(index="year", columns="scope", values="per10k")
    for sc, ls in [("", "-"), ("本会議", "--"), ("予算委員会", ":")]:
        axes[0].plot(w.index, w[sc], color=col, ls=ls, lw=1.8, label=f"{k}（{sc or '全会議'}）")
axes[0].set_title("会議の範囲を変える", loc="left"); axes[0].legend(fontsize=8, frameon=False, ncol=2)
axes[0].set_ylabel("発言1万件あたり")
for k, col in [("賃上げ", ORANGE), ("賃金引上げ", BLUE), ("賃金の引上げ", GREEN), ("ベースアップ", GRAY)]:
    axes[1].plot(allr.index, allr[k], color=col, lw=1.8, label=k)
axes[1].set_title("表記を変える", loc="left"); axes[1].legend(fontsize=8.5, frameon=False)
foot(fig, "「本会議」「予算委員会」は会議名の部分一致（分科会・公聴会を含む）")
fig.tight_layout(); fig.savefig(FIG / "f09_robust.png"); plt.close(fig)
print("ok")
