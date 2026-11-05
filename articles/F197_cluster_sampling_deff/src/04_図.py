"""04 図：5枚。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib import font_manager

from common import FIG, IND, IND_ORDER, RES

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
KJ = {"national_random": "全国でばらばらに5つずつ", "pref_random": "同じ都道府県の中でばらばらに5つずつ",
      "adjacent": "同じ都道府県の中でコードが隣り合う5つ", "prefecture": "都道府県まるごと（平均37）"}
KC = {"national_random": "#9aa0a6", "pref_random": "#4c8bf5", "adjacent": "#e8710a", "prefecture": "#8e44ad"}
COL = dict(zip(IND_ORDER, ["#e8710a", "#8e44ad", "#34a853", "#4c8bf5", "#a0522d", "#d93025", "#5f6368"]))

g = pd.read_csv(RES / "design_grid.csv")
g = g[g.year == "y"]
g120 = g[g.n == 120]
sim = pd.read_csv(RES / "simulation_n120.csv")
labs = [IND[k].replace("あたり", "あたり\n").replace("の人口", "の\n人口").replace("の全国", "の\n全国") for k in IND_ORDER]

# 図1 級内相関（ICC）：地区の作り方で比べる
icc = pd.read_csv(RES / "icc_m5.csv", index_col=0).reindex(IND_ORDER)
fig, ax = plt.subplots(figsize=(10.5, 4.8))
w = 0.2
x = np.arange(len(IND_ORDER))
for i, k in enumerate(["national_random", "pref_random", "prefecture", "adjacent"]):
    ax.bar(x + (i - 1.5) * w, icc[k], w, color=KC[k], label=KJ[k])
ax.axhline(0, color="#444", lw=0.8)
ax.set_xticks(x, labs, fontsize=9)
ax.set_ylabel("級内相関（同じ地区の中の似かより）")
ax.set_title("同じ地区に入る市区町村は、どれだけ似ているか（級内相関）")
ax.legend(fontsize=8.5, frameon=False, loc="upper right")
fig.text(0.01, 0.01, "1,729市区町村（SSDSE-A 2026年版）。ランダムな分け方は40通りの平均。", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "f197_01_icc.png", dpi=150)
plt.close(fig)

# 図2 設計効果（DEFF）と地区の大きさ
adj = g120[g120.kind == "adjacent"]
pref = g120[g120.kind == "prefecture"].set_index("ind")
fig, ax = plt.subplots(figsize=(9.5, 5.2))
for k in IND_ORDER:
    d = adj[adj.ind == k].sort_values("m")
    ax.plot(d.m, d.deff, "-o", color=COL[k], label=IND[k], ms=4)
    ax.plot([37], [pref.loc[k, "deff"]], "s", color=COL[k], ms=6)
mm = np.array([2, 3, 5, 10, 20])
ax.axhline(1, color="#888", lw=0.8, ls=":")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xticks([2, 3, 5, 10, 20, 37], ["2", "3", "5", "10", "20", "都道府県\n（平均37）"])
ax.set_yticks([1, 2, 3, 5, 10, 20, 30], ["1", "2", "3", "5", "10", "20", "30"])
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_xlabel("1つの地区に入る市区町村の数")
ax.set_ylabel("設計効果（単純無作為に比べて分散が何倍か）")
ax.set_title("地区が大きいほど、同じ人数でも誤差が大きくなる")
ax.legend(fontsize=8.5, frameon=False, ncol=2, loc="upper left")
fig.text(0.01, 0.01, "同じ都道府県の中でコードが隣り合う市区町村をまとめた地区。調べる市区町村は約120。■は都道府県まるごと。", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "f197_02_deff_by_size.png", dpi=150)
plt.close(fig)

# 図3 実質の標本の大きさ（120を調べたとき、単純無作為の何件分か）
neff = pd.read_csv(RES / "neff_adjacent_n120.csv", index_col=0).reindex(IND_ORDER)
cols = ["2.0", "5.0", "10.0", "20.0", "prefecture"]
cl = ["2", "5", "10", "20", "都道府県"]
fig, ax = plt.subplots(figsize=(10.5, 4.8))
w = 0.16
for i, c in enumerate(cols):
    ax.bar(x + (i - 2) * w, neff[c], w, label=f"地区の大きさ {cl[i]}", color=plt.cm.Oranges(0.35 + 0.13 * i))
ax.axhline(120, color="#444", lw=0.8, ls="--")
ax.text(len(IND_ORDER) - 0.5, 123, "実際に調べた数 120", ha="right", fontsize=8.5)
ax.set_xticks(x, labs, fontsize=9)
ax.set_ylabel("単純無作為なら何件分の精度か")
ax.set_title("120の市区町村を調べても、地区で選ぶと実質は数十件分")
ax.legend(fontsize=8.5, frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.12))
fig.tight_layout()
fig.savefig(FIG / "f197_03_effective_n.png", dpi=150)
plt.close(fig)

# 図4 95%区間の当たり方：単純無作為の式のままと、地区を考えた式
fig, axs = plt.subplots(1, 3, figsize=(12, 4.8), sharey=True)
for ax, (kind, m, t) in zip(axs, [("adjacent", 5.0, "隣り合う5つ（25地区）"), ("adjacent", 10.0, "隣り合う10（13地区）"),
                                  ("prefecture", None, "都道府県まるごと（3地区）")]):
    d = sim[sim.kind == kind]
    if m:
        d = d[d.m == m]
    d = d.set_index("ind").reindex(IND_ORDER)
    yy = np.arange(len(IND_ORDER))
    ax.hlines(yy, d.cover_naive, d.cover_cluster, color="#bbb")
    ax.plot(d.cover_naive, yy, "o", color="#d93025", label="単純無作為の式のまま")
    ax.plot(d.cover_cluster, yy, "o", color="#1a73e8", label="地区を考えた式")
    ax.axvline(0.95, color="#444", lw=0.8, ls="--")
    ax.set_xlim(0.25, 1.0)
    ax.set_title(t, fontsize=10)
    ax.set_xlabel("95%区間が本当の値を含んだ割合")
axs[0].set_yticks(yy, labs, fontsize=9)
axs[0].invert_yaxis()
axs[0].legend(fontsize=8.5, frameon=False, loc="lower left")
fig.suptitle("地区で選んだのに単純無作為の式で誤差を出すと、区間は当たらない（調べる数は約120、4,000回）")
fig.tight_layout()
fig.savefig(FIG / "f197_04_coverage.png", dpi=150)
plt.close(fig)

# 図5 誤差を大きくしているのは何か：地区の作り方での分解（m=5）
d5 = g120[g120.m == 5.0].pivot_table(index="ind", columns="kind", values="deff").reindex(IND_ORDER)
fig, ax = plt.subplots(figsize=(10.5, 4.8))
w = 0.26
for i, k in enumerate(["national_random", "pref_random", "adjacent"]):
    ax.bar(x + (i - 1) * w, d5[k], w, color=KC[k], label=KJ[k])
ax.axhline(1, color="#444", lw=0.8)
ax.set_xticks(x, labs, fontsize=9)
ax.set_ylabel("設計効果")
ax.set_title("同じ5つずつでも、「近いところをまとめる」と誤差が大きくなる")
ax.legend(fontsize=8.5, frameon=False, loc="upper right")
fig.text(0.01, 0.01, "調べる市区町村は約120（24〜25地区）。ばらばらの分け方は40通りの平均。", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "f197_05_decomposition.png", dpi=150)
plt.close(fig)
print("ok")
