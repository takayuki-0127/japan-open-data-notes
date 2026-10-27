"""04 図"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

from common import DATA, RES, FIG, MONTHS, REGION

prof = pd.read_csv(DATA / "profile_2015_2019.csv", index_col=0)
lab = pd.read_csv(RES / "base_labels.csv", index_col=0)["type"]
cen = pd.read_csv(RES / "base_centroids.csv", index_col=0)
TCOL = {1: "#1a73e8", 2: "#e37400"}
TNAME = {1: "型1 春と秋の2つの山", 2: "型2 12月の山・8月の谷"}
x = np.arange(12)

# 1. ヒートマップ（型ごと、山の月の順）
order = []
for t in [2, 1]:
    m = prof.loc[lab[lab == t].index]
    order += list(m.assign(pk=m.values.argmax(1)).sort_values(["pk"]).index)
fig, ax = plt.subplots(figsize=(8.2, 9.2))
im = ax.imshow(prof.loc[order].values, cmap="RdBu_r", vmin=0.3, vmax=1.7, aspect="auto")
ax.set_xticks(x, MONTHS)
ax.set_yticks(range(len(order)), [f"{m}（{REGION[m]}）" for m in order], fontsize=8.5)
n2 = (lab == 2).sum()
ax.axhline(n2 - 0.5, color="k", lw=1.5)
ax.text(12.1, n2 / 2 - 0.5, "型2", va="center", color=TCOL[2], fontsize=11, fontweight="bold")
ax.text(12.1, n2 + (len(order) - n2) / 2, "型1", va="center", color=TCOL[1], fontsize=11, fontweight="bold")
cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.08)
cb.set_label("各月の人数 ÷ 年平均")
ax.set_title("36の国・地域の季節の形（2015〜19年の平均）", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "f68_heatmap.png", dpi=150)
plt.close(fig)

# 2. 2つの型
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, t in zip(axes, [1, 2]):
    for m in lab[lab == t].index:
        ax.plot(x, prof.loc[m], color=TCOL[t], alpha=0.18, lw=1)
    ax.plot(x, cen.loc[f"型{t}"], color=TCOL[t], lw=3, label="型の平均（重心）")
    ax.axhline(1, color="gray", lw=0.8, ls=":")
    ax.set_xticks(x, MONTHS, fontsize=8.5)
    ax.set_title(f"{TNAME[t]}（{(lab == t).sum()}か国・地域）", fontsize=11)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
axes[0].set_ylabel("各月の人数 ÷ 年平均")
axes[1].text(0.02, 0.05, "タイ・シンガポール・マレーシア・\nインドネシア・フィリピン・豪州", transform=axes[1].transAxes, fontsize=9)
fig.suptitle("はっきり分かれたのは2つの型（ユークリッド距離の k-means、k=2）", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "f68_types.png", dpi=150)
plt.close(fig)

# 3. k の選び方
sel = pd.read_csv(RES / "k_selection.csv")
MN = {"euclid": "ユークリッド", "dtw": "DTW", "kshape": "k-shape"}
MC = {"euclid": "#1a73e8", "dtw": "#d93025", "kshape": "#188038"}
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for mth, g in sel.groupby("method"):
    axes[0].plot(g.k, g.silhouette, "o-", color=MC[mth], label=MN[mth])
    axes[1].plot(g.k, g.stability_ari, "o-", color=MC[mth], label=MN[mth])
axes[0].set_title("シルエット（大きいほどはっきり分かれる）", fontsize=11)
axes[1].set_title("年を入れ替えても同じ分け方になるか（ARI）", fontsize=11)
for ax in axes:
    ax.set_xlabel("型の数 k")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=0.3)
fig.suptitle("年を入れ替えても同じ分け方になるのは、3手法とも k=2 がいちばん（k-shape のシルエットは k=5・7 もほぼ同じ）", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "f68_ksel.png", dpi=150)
plt.close(fig)

# 4. 共起行列（3手法 × k=3〜6）
co = pd.read_csv(RES / "coassignment_k3to6.csv", index_col=0)
Z = linkage(squareform(1 - co.values, checks=False), "average")
o = co.index[leaves_list(Z)]
fig, ax = plt.subplots(figsize=(8.6, 7.6))
im = ax.imshow(co.loc[o, o].values, cmap="Greys", vmin=0, vmax=1)
ax.set_xticks(range(len(o)), o, rotation=90, fontsize=7.5)
ax.set_yticks(range(len(o)), o, fontsize=7.5)
cb = fig.colorbar(im, ax=ax, shrink=0.7)
cb.set_label("同じ型になった割合（12通り中）")
ax.set_title("細かく分けたとき、どの国どうしがいつも一緒になるか\n（3手法 × k=3〜6 の12通り）", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "f68_coassign.png", dpi=150)
plt.close(fig)

# 5. コロナ前後
post = pd.read_csv(DATA / "profile_2023_2025.csv", index_col=0)
pp = pd.read_csv(RES / "pre_post_by_market.csv", index_col=0)
show = ["韓国", "台湾", "タイ", "英国", "米国", "ニュージーランド"]
fig, axes = plt.subplots(2, 3, figsize=(10.5, 5.6), sharey=True)
for ax, m in zip(axes.flat, show):
    ax.plot(x, prof.loc[m], color="gray", lw=2, label="2015〜19年")
    ax.plot(x, post.loc[m], color=TCOL[int(pp.loc[m, "post_type"])], lw=2, label="2023〜25年")
    ax.set_title(f"{m}（前後の相関 {pp.loc[m, 'corr_pre_post']:.2f}）", fontsize=10)
    ax.set_xticks(x, [str(i) for i in range(1, 13)], fontsize=8)
    ax.axhline(1, color="gray", lw=0.6, ls=":")
axes[0, 0].legend(frameon=False, fontsize=8.5)
fig.suptitle("コロナの前と後で、季節の形はどれくらい変わったか（線の色は後の型）", fontsize=12)
fig.text(0.5, 0.01, "月", ha="center")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "f68_prepost.png", dpi=150)
plt.close(fig)

# 6. 総数に占める型2の割合（月別）
tb = pd.read_csv(RES / "total_by_type.csv")
fig, ax = plt.subplots(figsize=(8, 4))
for y, ls in [(2019, "-"), (2025, "--")]:
    s = tb[(tb.year == y) & (tb.type == 2)].sort_values("month")
    ax.plot(x, s.share_of_total * 100, ls, color=TCOL[2], lw=2, marker="o", label=f"{y}年")
ax.set_xticks(x, MONTHS)
ax.set_ylabel("訪日客の総数に占める型2の割合（%）")
ax.set_title("型2（12月型）の国は訪日客の約12%だが、12月には2割を超える", fontsize=11)
ax.legend(frameon=False)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "f68_total.png", dpi=150)
plt.close(fig)
print("ok")
