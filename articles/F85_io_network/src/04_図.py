"""F85 図：python src/04_図.py → figures/*.png"""
import json
import numpy as np, pandas as pd, networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import RES, FIG, load_table, matrices

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f and "Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
C1, C2, C3, CG = "#2b6cb0", "#dd6b20", "#2f855a", "#a0aec0"

df = pd.read_csv(RES / "sectors_2020.csv", dtype={"部門コード": str})
S = json.load(open(RES / "summary.json", encoding="utf-8"))

# 1. 後方連関×前方連関
fig, ax = plt.subplots(figsize=(8.5, 6.5))
k = df["キーセクター"]
ax.scatter(df.loc[~k, "後方連関"], df.loc[~k, "前方連関"], s=np.sqrt(df.loc[~k, "国内生産額_十億円"]) * 1.2, c=CG, alpha=.6, label="その他")
ax.scatter(df.loc[k, "後方連関"], df.loc[k, "前方連関"], s=np.sqrt(df.loc[k, "国内生産額_十億円"]) * 1.2, c=C2, alpha=.8, label="キーセクター（両方 >1）")
ax.axhline(1, c="k", lw=.8); ax.axvline(1, c="k", lw=.8)
lab = set(df.nlargest(4, "後方連関")["部門"]) | set(df.nlargest(5, "前方連関")["部門"]) | set(df.nlargest(4, "国内生産額_十億円")["部門"]) | {"自動車部品", "電気"}
for _, r in df[df["部門"].isin(lab)].iterrows():
    ax.annotate(r["部門"], (r["後方連関"], r["前方連関"]), fontsize=8.5, xytext=(4, 3), textcoords="offset points")
ax.set_xlabel("後方連関（買い手としての波及の大きさ、平均＝1）"); ax.set_ylabel("前方連関（売り手としての波及の大きさ、平均＝1）")
ax.set_title(f"108部門の後方連関と前方連関（2020年）：両方が1を超えるキーセクターは{S['キーセクター数']}部門", fontsize=11)
ax.text(0.99, 0.01, "円の大きさ＝国内生産額", transform=ax.transAxes, ha="right", fontsize=8, color="gray")
ax.legend(loc="upper left", fontsize=9, frameon=False)
fig.tight_layout(); fig.savefig(FIG / "f85_linkage.png", dpi=150); plt.close(fig)

# 2. ネットワーク（国内の中間取引の上位の流れ）
t = load_table("2020"); m = matrices(t)
Zd = (1 - m["m"])[:, None] * t["Z"]; np.fill_diagonal(Zd, 0)
idx = np.dstack(np.unravel_index(np.argsort(-Zd.ravel()), Zd.shape))[0][:45]
G = nx.DiGraph()
for i, j in idx:
    G.add_edge(int(i), int(j), weight=float(Zd[i, j]))
pr = dict(zip(range(len(df)), df["PageRank"]))
pos = nx.kamada_kawai_layout(G.to_undirected(), weight=None)
pos = nx.spring_layout(G, pos=pos, seed=3, k=1.4, weight=None, iterations=60)
fig, ax = plt.subplots(figsize=(11, 9))
wmax = max(d["weight"] for *_, d in G.edges(data=True))
nx.draw_networkx_edges(G, pos, ax=ax, width=[0.4 + 4 * d["weight"] / wmax for *_, d in G.edges(data=True)],
                       edge_color="#718096", alpha=.5, arrows=True, arrowsize=8, connectionstyle="arc3,rad=0.08")
nodes = list(G.nodes())
nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_size=[200 + 12000 * pr[n] for n in nodes],
                       node_color=[C2 if df.loc[n, "キーセクター"] else C1 for n in nodes], alpha=.85, ax=ax)
for n in nodes:
    x, y = pos[n]
    ax.text(x, y + 0.045, df.loc[n, "部門"], fontsize=8, ha="center", va="bottom", bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=.7))
ax.set_title("国内の中間取引で大きい45本の流れ（矢印は売り手→買い手、太さ＝金額、円の大きさ＝PageRank）", fontsize=10.5)
ax.axis("off"); fig.tight_layout(); fig.savefig(FIG / "f85_network.png", dpi=150); plt.close(fig)

# 3. 中心性・Domar・抽出：上位12
fig, axes = plt.subplots(1, 3, figsize=(13, 5.6))
for ax, col, ttl, c, fmt in [(axes[0], "PageRank", "PageRank（よく買われる部門）", C1, "{:.3f}"),
                             (axes[1], "Domar", "Domar ウエイト（生産額÷GDP）", C3, "{:.2f}"),
                             (axes[2], "抽出_全体", "仮想的抽出：ほかの部門の生産の減少率", C2, "{:.1%}")]:
    d = df.nlargest(12, col).iloc[::-1]
    ax.barh(d["部門"], d[col], color=c)
    for y, v in enumerate(d[col]):
        ax.text(v, y, " " + fmt.format(v), va="center", fontsize=8)
    ax.set_title(ttl, fontsize=10.5); ax.tick_params(axis="y", labelsize=8.5)
    ax.set_xlim(0, d[col].max() * 1.3)
fig.suptitle(f"「要」の産業は物差しで入れ替わる（PageRank と Domar の順位相関 {S['指標の順位相関_PageRank_Domar']:.2f}）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f85_centrality.png", dpi=150); plt.close(fig)

# 4. ショックの伝わり方
dem = S["需要ショック"]; sup = S["供給ショック"]
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
ax = axes[0]
d = pd.DataFrame([dict(部門=v["部門"], 自部門=v["自部門"], 他部門=v["生産減_十億円"] - v["自部門"]) for v in dem.values()]).sort_values("他部門")
ax.barh(d["部門"], d["自部門"] / 1000, color=CG, label="その部門自身")
ax.barh(d["部門"], d["他部門"] / 1000, left=d["自部門"] / 1000, color=C1, label="ほかの部門へ波及")
for y, (a, b) in enumerate(zip(d["自部門"], d["他部門"])):
    ax.text((a + b) / 1000, y, f" {(a + b) / 1000:.2f}兆円（波及 {b / (a + b):.0%}）", va="center", fontsize=8.5)
ax.set_xlim(0, 3.4); ax.set_xlabel("国内生産の減少（兆円）"); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("需要ショック：最終需要が1兆円減ったとき（競争輸入型）", fontsize=10.5)
ax = axes[1]
d = pd.DataFrame([dict(部門=v["部門"], 倍率=v["倍率"], 他=v["他部門の割合"]) for v in sup.values()]).sort_values("倍率")
ax.barh(d["部門"], d["倍率"], color=C2)
for y, (a, b) in enumerate(zip(d["倍率"], d["他"])):
    ax.text(a, y, f" {a:.2f}倍（下流へ {b:.0%}）", va="center", fontsize=8.5)
ax.axvline(1, c="k", lw=.8); ax.set_xlim(0, 3.4); ax.set_xlabel("生産の減少 ÷ 付加価値の減少")
ax.set_title("供給ショック：付加価値が10%減ったときの下流への波及（Ghosh）", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "f85_shock.png", dpi=150); plt.close(fig)

# 5. 頑健性：指標どうしの順位相関と、年・統合・閉鎖型
cm = pd.read_csv(RES / "rank_corr_measures.csv", index_col=0)
rob = S["頑健性"]
fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
ax = axes[0]
im = ax.imshow(cm.values, cmap="RdBu_r", vmin=-1, vmax=1)
lbl = [c.replace("抽出_全体", "仮想的抽出") for c in cm.columns]
ax.set_xticks(range(len(lbl))); ax.set_xticklabels(lbl, rotation=45, ha="right", fontsize=8.5)
ax.set_yticks(range(len(lbl))); ax.set_yticklabels(lbl, fontsize=8.5)
for i in range(len(lbl)):
    for j in range(len(lbl)):
        ax.text(j, i, f"{cm.values[i, j]:.2f}", ha="center", va="center", fontsize=7.5, color="white" if abs(cm.values[i, j]) > .6 else "black")
ax.set_title("8つの物差しどうしの順位相関（108部門）", fontsize=10.5)
ax = axes[1]
items = [("2015年表：後方連関", rob["2015年表との順位相関"]["後方連関"]), ("2015年表：前方連関", rob["2015年表との順位相関"]["前方連関"]),
         ("2015年表：Domar", rob["2015年表との順位相関"]["Domar"]), ("2015年表：PageRank", rob["2015年表との順位相関"]["PageRank"]),
         ("閉鎖型（輸入を考えない）：後方連関", rob["閉鎖型との順位相関_後方連関"]),
         ("帰属家賃・分類不明を除く：PageRank", rob["除外との順位相関"]["PageRank"]),
         ("PageRank 減衰率0.5", rob["PageRank_alpha"]["0.5"]), ("PageRank 減衰率0.95", rob["PageRank_alpha"]["0.95"])]
ax.barh([a for a, _ in items][::-1], [b for _, b in items][::-1], color=C1)
for y, v in enumerate([b for _, b in items][::-1]):
    ax.text(v, y, f" {v:.3f}", va="center", fontsize=8.5)
ax.set_xlim(0, 1.15); ax.set_title("設定を変えたときの、基本の結果との順位相関", fontsize=10.5); ax.tick_params(axis="y", labelsize=8.5)
fig.tight_layout(); fig.savefig(FIG / "f85_robust.png", dpi=150); plt.close(fig)
print("ok")
