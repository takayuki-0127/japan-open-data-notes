"""04 図：5枚。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib import font_manager

from common import FIG, RES, Y

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
C = {"srs": "#9aa0a6", "prop": "#4c8bf5", "neyman_prior": "#e8710a", "neyman_pop": "#8e44ad", "equal": "#34a853"}
JA = {"srs": "単純無作為", "prop": "層別・比例配分", "neyman_prior": "層別・ネイマン配分（前回の値）",
      "neyman_pop": "層別・ネイマン配分（前回の人口で共通）", "equal": "層別・等配分"}
YJ = {k: v[1] for k, v in Y.items()}

grid = pd.read_csv(RES / "precision_grid.csv")
st = pd.read_csv(RES / "strata_H5.csv")

# 図1 5つの層：件数と、合計に占める割合と、n=100 の配分
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
def _man(v):
    return f"{v/1e4:.1f}万" if v < 1e5 else f"{v/1e4:.0f}万"
lab = [f"層{k+1}\n{_man(a)}〜{_man(b)}人" for k, a, b in zip(st["層"], st["前回人口の最小"], st["前回人口の最大"])]
x = np.arange(5)
ax[0].bar(x - 0.27, st["件数"] / st["件数"].sum() * 100, 0.27, color="#9aa0a6", label="市区町村の数")
ax[0].bar(x, st["世帯数の合計に占める割合%"], 0.27, color="#4c8bf5", label="世帯数の合計")
ax[0].bar(x + 0.27, st["農家数の合計に占める割合%"], 0.27, color="#34a853", label="農家数の合計")
ax[0].set_xticks(x, lab, fontsize=8)
ax[0].set_ylabel("全体に占める割合（%）")
ax[0].set_title("前回の人口で5つの層に分けると")
ax[0].legend(frameon=False, fontsize=9)
w = 0.27
ax[1].bar(x - w, st["n_prop(世帯)"], w, color=C["prop"], label="比例配分")
ax[1].bar(x, st["n_neyman_prior(世帯)"], w, color=C["neyman_prior"], label="ネイマン（世帯数に合わせる）")
ax[1].bar(x + w, st["n_neyman_prior(農家)"], w, color="#34a853", label="ネイマン（農家数に合わせる）")
for i, v in enumerate(st["n_neyman_prior(世帯)"]):
    ax[1].text(i, v + 1.5, str(v), ha="center", fontsize=8, color=C["neyman_prior"])
ax[1].set_xticks(x, [f"層{k+1}" for k in x])
ax[1].set_ylabel("選ぶ市区町村の数（合計100）")
ax[1].set_title("100市区町村をどの層から選ぶか")
ax[1].legend(frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "f196_01_strata.png", dpi=150)
plt.close(fig)

# 図2 指標ごとの誤差（CV%）：n=100、5層
m = grid[(grid.strata == "cumsqrtf") & (grid.H == 5) & (grid.n == 100)]
order = ["households", "elderly", "births", "employees", "farms", "aging_mean"]
fig, ax = plt.subplots(figsize=(9, 4.8))
yy = np.arange(len(order))
for j, a in enumerate(["srs", "prop", "neyman_prior", "neyman_pop"]):
    vals = [m[(m.y == k) & (m.alloc == a)]["cv"].iloc[0] for k in order]
    ax.scatter(vals, yy + (j - 1.5) * 0.17, color=C[a], s=36, label=JA[a], zorder=3)
for i in yy:
    ax.axhline(i, color="#eeeeee", lw=8, zorder=0)
ax.set_yticks(yy, [YJ[k] for k in order])
ax.invert_yaxis()
ax.set_xlabel("合計（または平均）の推定の誤差の大きさ：標準誤差÷本当の値（%）")
ax.set_title("1,740市区町村から100を選んで全国の合計を推定したとき（5層）")
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.tight_layout()
fig.savefig(FIG / "f196_02_cv_by_indicator.png", dpi=150)
plt.close(fig)

# 図3 層の数と効率
fig, ax = plt.subplots(1, 3, figsize=(12, 4), sharey=False)
for i, k in enumerate(["households", "farms", "aging_mean"]):
    for skind, ls in [("cumsqrtf", "-"), ("quantile", "--")]:
        for a in ["prop", "neyman_prior"]:
            s = grid[(grid.strata == skind) & (grid.n == 100) & (grid.alloc == a) & (grid.y == k)].sort_values("H")
            ax[i].plot(s.H, s.eff, ls, color=C[a], marker="o", ms=3.5,
                       label=f"{'比例' if a=='prop' else 'ネイマン'}・{'累積√f' if skind=='cumsqrtf' else '同じ件数'}")
    ax[i].axhline(1, color="#999999", lw=0.8)
    ax[i].set_yscale("log")
    ax[i].yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    if k == "households":
        ax[i].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax[i].set_yticks([1, 2, 5, 10, 20, 50])
    else:
        ax[i].yaxis.set_minor_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax[i].set_title(YJ[k])
    ax[i].set_xlabel("層の数")
ax[0].set_ylabel("効率（単純無作為の分散÷層別の分散、対数目盛）")
ax[0].legend(frameon=False, fontsize=8)
fig.suptitle("層を増やすと：n=100", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "f196_03_layers.png", dpi=150)
plt.close(fig)

# 図4 多目的：ある指標に合わせた配分を、ほかの指標に使うと
cr = pd.read_csv(RES / "cross_allocation_H5_n100.csv", index_col=0)
fig, ax = plt.subplots(figsize=(7.6, 5.4))
v = np.log10(cr.values)
im = ax.imshow(v, cmap="RdBu", vmin=-1.2, vmax=1.2)
for i in range(cr.shape[0]):
    for j in range(cr.shape[1]):
        ax.text(j, i, f"{cr.values[i, j]:.2f}", ha="center", va="center", fontsize=9,
                color="white" if abs(v[i, j]) > 0.7 else "black")
ax.set_xticks(range(cr.shape[1]), [YJ[k] for k in cr.columns], rotation=35, ha="right", fontsize=9)
ax.set_yticks(range(cr.shape[0]), [YJ[k] for k in cr.index], fontsize=9)
ax.set_xlabel("精度を測る指標")
ax.set_ylabel("配分を合わせた指標（前回の値のネイマン配分）")
ax.set_title("効率（1より大きい＝単純無作為より良い）")
fig.tight_layout()
fig.savefig(FIG / "f196_04_cross_allocation.png", dpi=150)
plt.close(fig)

# 図5 シミュレーション：世帯数の合計の推定（5,000回）
sim = pd.read_csv(RES / "simulation_n100.csv")
fig, ax = plt.subplots(figsize=(9, 4.4))
bins = np.linspace(0.3, 2.2, 96)
for a in ["srs", "prop", "neyman_prior"]:
    e = np.load(RES / f"sim_households_{a}.npy")
    r = sim[(sim.y == "households") & (sim.alloc == a)].iloc[0]
    ax.hist(e, bins=bins, histtype="step", lw=1.6, color=C[a],
            label=f"{JA[a]}：誤差{r.cv_sim:.1f}%、95%区間の当たり{r.coverage95*100:.0f}%")
ax.axvline(1, color="black", lw=0.8)
ax.set_xlabel("推定した世帯数の合計 ÷ 本当の合計")
ax.set_ylabel("回数（5,000回のうち）")
ax.set_title("100市区町村を選んで世帯数の合計を推定する、を5,000回")
ax.legend(frameon=False, fontsize=8.5)
fig.tight_layout()
fig.savefig(FIG / "f196_05_simulation.png", dpi=150)
plt.close(fig)
print("ok")
