"""図6枚。"""
import sys, json, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from zz_f288_common import DISTS, TRUE_MODEL

out = sys.argv[1] if len(sys.argv) > 1 else "."
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["svg.hashsalt"] = "f288"
plt.rcParams["figure.dpi"] = 110
R, F = f"{out}/results", f"{out}/figures"
t = pd.read_csv(f"{R}/E_table_seed288.csv")
A = pd.read_csv(f"{R}/A_sims_seed288.csv.gz")
C = pd.read_csv(f"{R}/G_r4_table.csv")
M = json.load(open(f"{R}/main.json"))
NS = sorted(t.n.unique())
COL = {"gpd0.2": "#9ecae1", "gpd0.4": "#4292c6", "gpd0.5": "#2171b5", "gpd0.6": "#08519c", "gpd0.8": "#08306b",
       "ln1.0": "#fdae6b", "ln1.5": "#e6550d", "weib0.6": "#31a354", "exp": "#636363"}
LAB = {k: v[0] for k, v in DISTS.items()}


def save(fig, name):
    fig.savefig(f"{F}/{name}", bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)


# 図1 検出力
fig, ax = plt.subplots(figsize=(8, 5))
for d in ["gpd0.2", "gpd0.4", "gpd0.6", "gpd0.8", "ln1.0", "ln1.5", "weib0.6", "exp"]:
    s = t[t.dist == d].sort_values("n")
    ls = "-" if d.startswith("gpd") else ("--" if d != "exp" else ":")
    ax.plot(s.n, s.heavy5 * 100, ls, marker="o", ms=3, color=COL[d], label=LAB[d])
ax.axhline(80, color="gray", lw=0.8); ax.axhline(5, color="gray", lw=0.8, ls=":")
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS)
ax.set_xlabel("損害の件数 n"); ax.set_ylabel("「裾が重い」と判定された割合（%）")
ax.set_title("図1 件数ごとの「裾が重い」の判定（GPD 対 指数の尤度比検定、5%）")
ax.legend(fontsize=8, ncol=2, loc="lower right")
save(fig, "f288_1_power.png")

# 図2 ξ̂ の幅
fig, axs = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)
for ax, d in zip(axs, ["gpd0.4", "ln1.5"]):
    s = t[t.dist == d].sort_values("n")
    ax.fill_between(s.n, s.xi_q05, s.xi_q95, color=COL[d], alpha=0.25, label="推定の5〜95%")
    ax.plot(s.n, s.xi_med, color=COL[d], marker="o", ms=3, label="推定の中央値")
    tr = DISTS[d][1]
    ax.axhline(tr, color="k", lw=1, label=f"本当の ξ={tr}")
    if d == "gpd0.4":
        ax.axhspan(tr - 0.15, tr + 0.15, color="gray", alpha=0.12, label="±0.15")
    ax.axhline(1, color="red", lw=0.8, ls=":", label="ξ=1（平均が無限大の境）")
    ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS, fontsize=8)
    ax.set_ylim(-1.0, 1.6); ax.set_xlabel("損害の件数 n"); ax.set_title(LAB[d])
    ax.legend(fontsize=7, loc="lower right")
axs[0].set_ylabel("GPD の裾の指数 ξ の最尤推定")
fig.suptitle("図2 裾の指数の推定はどこまで絞れるか")
save(fig, "f288_2_xi_range.png")

# 図3 AIC で選ばれた分布
names = ["exp", "weib", "lnorm", "gpd"]
nlab = {"exp": "指数", "weib": "ワイブル", "lnorm": "対数正規", "gpd": "GPD"}
ncol = {"exp": "#bdbdbd", "weib": "#31a354", "lnorm": "#e6550d", "gpd": "#2171b5"}
fig, axs = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
sel = [15, 30, 100, 500]
for ax, d in zip(axs, ["gpd0.4", "ln1.5"]):
    s = A[A.dist == d]
    bottom = np.zeros(len(sel))
    for m in names:
        v = np.array([(s[s.n == n].pick_aic == m).mean() * 100 for n in sel])
        ax.bar([str(n) for n in sel], v, bottom=bottom, color=ncol[m], label=nlab[m])
        bottom += v
    ax.set_title(f"本当は {LAB[d]}"); ax.set_xlabel("損害の件数 n")
axs[0].set_ylabel("AIC で選ばれた割合（%）"); axs[1].legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1.0))
fig.suptitle("図3 4つの分布から AIC で選ぶと、どれが選ばれるか")
save(fig, "f288_3_aic_pick.png")

# 図4 平均が無限大に見える割合
fig, ax = plt.subplots(figsize=(8, 4.8))
for d in ["gpd0.5", "gpd0.6", "gpd0.8", "ln1.5", "weib0.6"]:
    s = t[t.dist == d].sort_values("n")
    ax.plot(s.n, s.ge1 * 100, "-" if d.startswith("gpd") else "--", marker="o", ms=3, color=COL[d], label=LAB[d])
ax.axhline(10, color="gray", lw=0.8)
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS)
ax.set_xlabel("損害の件数 n"); ax.set_ylabel("推定 ξ が1以上になった割合（%）")
ax.set_title("図4 本当は平均が有限なのに「平均が無限大」に見える割合")
ax.legend(fontsize=8)
save(fig, "f288_4_infinite_mean.png")

# 図5 しきい値を上げると（R4）
fig, axs = plt.subplots(1, 2, figsize=(10, 4.3))
qc = {0.8: "#fdae6b", 0.9: "#e6550d", 0.95: "#a63603"}
for q in [0.8, 0.9, 0.95]:
    s = C[C.q == q].sort_values("n")
    axs[0].plot(s.n, s.heavy5 * 100, marker="o", ms=3, color=qc[q], label=f"上位{int(round((1-q)*100))}%")
    axs[1].plot(s.n, s.xi_med, marker="o", ms=3, color=qc[q], label=f"上位{int(round((1-q)*100))}%")
for ax in axs:
    ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS, fontsize=8); ax.set_xlabel("超えた損害の件数 n"); ax.legend(fontsize=8)
axs[0].set_ylabel("「裾が重い」と判定された割合（%）"); axs[1].set_ylabel("推定 ξ の中央値")
axs[1].axhline(0, color="k", lw=0.8)
fig.suptitle("図5 対数正規（本当は ξ=0）の損害の上位だけを使っても、裾は重く見える")
save(fig, "f288_5_threshold.png")

# 図6 問い直し
r = M["reask"]["15"]
order = ["exp", "ln1.0", "weib0.6", "gpd0.2", "gpd0.6", "gpd0.5", "gpd0.4", "gpd0.8", "ln1.5"]
order = sorted(order, key=lambda d: r[d]["both"])
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.barh([LAB[d] for d in order], [r[d]["both"] * 100 for d in order], color=[COL[d] for d in order])
for i, d in enumerate(order):
    ax.text(r[d]["both"] * 100 + 0.1, i, f"{r[d]['both']*100:.1f}%", va="center", fontsize=8)
ax.set_xlabel("15件で「4つの AIC の差が2未満」かつ「推定 ξ が0.37〜0.57」になった割合（%）")
ax.set_title("図6 F260 と同じような15件の結果は、どの本当の分布からも出る")
save(fig, "f288_6_reask.png")
print("figs ok")
