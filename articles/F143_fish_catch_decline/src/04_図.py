"""04 図: results/ から図を作る"""
import json, ast
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
R = json.load(open(RES / "results.json", encoding="utf-8"))
info = pd.read_csv(RES / "species_clusters.csv", index_col=0)
info["breaks"] = info.breaks.apply(ast.literal_eval)
shapes = pd.read_csv(RES / "species_shapes.csv", index_col=0)
shapes.index = shapes.index.astype(int)
ct = pd.read_csv(RES / "cluster_totals_by_year.csv", index_col=0)
W = pd.read_csv(ROOT / "data/species_wide.csv", index_col=0)
G = pd.read_csv(ROOT / "data/gear_wide.csv", index_col=0)
gi = pd.read_csv(RES / "gear_types.csv", index_col=0)
NAME = {0: "A 早く大きく減った", 1: "B ゆるやかに減った", 2: "C 大きな波（まいわし）", 3: "D 最大が遅く、まだ多い"}
COL = {0: "#c53030", 1: "#dd6b20", 2: "#2b6cb0", 3: "#38a169"}
GR = "#a0aec0"
SRC = "出典：農林水産省「漁業・養殖業生産統計（海面漁業生産統計調査）長期累年」をもとに作成"


def foot(fig):
    fig.text(0.01, 0.005, SRC, fontsize=7.5, color="#555")


# ---- 図1 全体の漁獲量と型ごとの内訳 ----
fig, ax = plt.subplots(figsize=(10, 4.6))
yrs = ct.index.values
stack = [ct[str(c)].values / 1e4 for c in range(4)] + [ct["対象外の魚種など"].values / 1e4]
ax.stackplot(yrs, *stack, colors=[COL[c] for c in range(4)] + [GR], alpha=.85,
             labels=[NAME[c] for c in range(4)] + ["分析の対象外の魚種など"])
ax.set_ylabel("万t")
ax.set_title(f"海面漁業の漁獲量（{R['period'][0]}〜{R['period'][1]}年）と、減り方の型ごとの内訳", loc="left")
ax.axvline(R["total_peak_year"], color="k", lw=.8, ls=":")
ax.text(R["total_peak_year"] + 1, R["total_peak_t"] / 1e4 * .97, f"最大 {R['total_peak_year']}年 {R['total_peak_t']/1e4:,.0f}万t", fontsize=9)
ax.text(2024, R["total_2024_t"] / 1e4 + 30, f"2024年\n{R['total_2024_t']/1e4:,.0f}万t", fontsize=9, ha="right")
ax.legend(loc="upper right", fontsize=8.5, frameon=False, ncol=1)
ax.set_ylim(0, 1300)
ax.set_xlim(1960, 2024)
foot(fig)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "fig1_total_by_type.png", dpi=150)
plt.close(fig)

# ---- 図2 型ごとの形（最大を1とした5年移動平均） ----
fig, axs = plt.subplots(1, 4, figsize=(12, 3.9), sharey=True)
for c, a in enumerate(axs):
    mem = info.index[info.cluster == c]
    for s in mem:
        a.plot(shapes.index, shapes[s], color=COL[c], alpha=.35 if len(mem) > 1 else 1, lw=1 if len(mem) > 1 else 2)
    if len(mem) > 1:
        a.plot(shapes.index, shapes[mem].median(axis=1), color="k", lw=2, label="中央値")
    a.set_title(f"{NAME[c]}（{len(mem)}魚種）", loc="left", fontsize=10)
    rr = info.loc[mem, "recent_ratio"].median()
    a.text(0.98, 0.95, f"直近5年は最大の\n{rr*100:.0f}%（中央値）", transform=a.transAxes, ha="right", va="top", fontsize=8.5)
    a.set_xlim(1960, 2024)
    a.set_xticks([1960, 1980, 2000, 2020])
    lab = sorted(mem, key=lambda s: -info.loc[s, "peak_t"])[:4]
    a.set_xlabel("例：" + "、".join(lab), fontsize=8)
axs[0].set_ylabel("最大の年を1とした漁獲量")
fig.suptitle("減り方の型（k-means、42魚種、1960〜2024年）。細い線が各魚種", x=0.01, ha="left", fontsize=11)
foot(fig)
fig.subplots_adjust(left=.06, right=.99, top=.82, bottom=.2, wspace=.12)
fig.savefig(FIG / "fig2_type_shapes.png", dpi=150)
plt.close(fig)

# ---- 図3 魚種ごとのヒートマップ ----
ordr = info.sort_values(["cluster", "peak_year"]).index
M = shapes[ordr].T.values
fig, ax = plt.subplots(figsize=(10, 9))
im = ax.imshow(M, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1, extent=[1959.5, 2024.5, len(ordr) - .5, -.5])
ax.set_yticks(range(len(ordr)))
ax.set_yticklabels([f"{s}" for s in ordr], fontsize=8)
for k, s in enumerate(ordr):
    ax.add_patch(plt.Rectangle((1955.3, k - .5), 3.6, 1, color=COL[info.loc[s, "cluster"]], clip_on=False))
    for b in info.loc[s, "breaks"]:
        ax.plot(b, k, marker="|", color="#e53e3e", ms=8, mew=1.6)
ax.set_xlim(1959.5, 2024.5)
ax.set_title("魚種ごとの漁獲量（最大を1とした5年移動平均）。左の色は型、赤い縦線は変化点", loc="left", fontsize=10.5)
cb = fig.colorbar(im, ax=ax, fraction=.025, pad=.01)
cb.set_label("最大を1とした値")
foot(fig)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "fig3_heatmap.png", dpi=150)
plt.close(fig)

# ---- 図4 変化点：全体の区分線形と、魚種の変化点の年代 ----
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.3), gridspec_kw={"width_ratios": [1.25, 1]})
a = axs[0]
tot = W.loc[1960:2024, "漁獲量計"] / 1e4
a.plot(tot.index, tot.values, color="k", lw=1.2, label="漁獲量計")
edges = [1960] + R["total_breaks"] + [2025]
for (s0, s1), sl in zip(zip(edges[:-1], edges[1:]), R["total_slopes_pct"]):
    seg = tot.loc[s0:s1 - 1]
    t = seg.index.values
    p = np.polyfit(t - t.mean(), np.log(seg.values), 1)
    a.plot(t, np.exp(np.polyval(p, t - t.mean())), color="#e53e3e", lw=2)
    a.text(t.mean(), np.exp(np.polyval(p, 0)) * 1.12, f"年{sl:+.1f}%", ha="center", fontsize=9, color="#c53030")
for b in R["total_breaks"]:
    a.axvline(b, color="#e53e3e", ls=":", lw=.8)
a.set_title("漁獲量計の区分線形（対数）と変化点", loc="left", fontsize=10.5)
a.set_ylabel("万t")
a = axs[1]
dec = sorted(set(list(R["breaks_by_decade"].keys())))
allb = pd.Series(R["breaks_by_decade"]).rename(index=int).sort_index()
fb = pd.Series(R["first_break_by_decade"]).rename(index=int).reindex(allb.index, fill_value=0)
x = np.arange(len(allb))
a.bar(x - .2, allb.values, width=.4, color=GR, label="すべての変化点")
a.bar(x + .2, fb.values, width=.4, color="#c53030", label="各魚種の最初の変化点")
a.set_xticks(x)
a.set_xticklabels([f"{d}年代" for d in allb.index], fontsize=8.5)
a.set_ylabel("変化点の数")
a.set_title("42魚種の変化点の年代", loc="left", fontsize=10.5)
a.legend(frameon=False, fontsize=8.5)
foot(fig)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "fig4_changepoints.png", dpi=150)
plt.close(fig)

# ---- 図5 頑健性と漁業種類 ----
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.5), gridspec_kw={"width_ratios": [1, 1.1]})
rb = R["robustness"]
items = [("型の数 3", rb["k"]["3"]), ("型の数 5", rb["k"]["5"]), ("型の数 6", rb["k"]["6"]),
         ("Ward法", rb["ward"]), ("主要20魚種だけ", rb["top20"]), ("移動平均なし", rb["no_smoothing"]),
         ("年の8割で分け直し（平均）", rb["subsample_years_mean"]),
         ("期間 1970〜2024年", rb["period_1970_2024"]), ("期間 1960〜2000年", rb["period_1960_2000"]),
         ("期間 1990〜2024年", rb["period_1990_2024"]), ("log の標準化", rb["zscore_log"])]
a = axs[0]
y = np.arange(len(items))[::-1]
v = [i[1] for i in items]
a.barh(y, v, color=["#2b6cb0" if x >= .6 else "#dd6b20" for x in v])
a.set_yticks(y)
a.set_yticklabels([i[0] for i in items], fontsize=8.5)
for yy, vv in zip(y, v):
    a.text(vv + .01, yy, f"{vv:.2f}", va="center", fontsize=8)
a.axvline(.6, color="k", ls=":", lw=.8)
a.set_xlim(0, 1.12)
a.set_title("条件を変えたときの型の一致度（ARI、1=同じ）", loc="left", fontsize=10.5)
a = axs[1]
GC = {0: "#c53030", 1: "#dd6b20", 2: "#38a169"}
GN = {0: "最大が遅く、そのあと急減", 1: "早く減った", 2: "沿岸で保っている"}
gx = G.loc[1975:2024, gi.index]
gs = gx.rolling(5, center=True, min_periods=3).mean()
gs = gs / gs.max()
ypos = {}
for g in sorted(gi.index, key=lambda g: gs[g].iloc[-1]):
    y0 = gs[g].iloc[-1]
    if ypos:
        y0 = max(y0, max(ypos.values()) + .04)
    ypos[g] = y0
for g in gi.index:
    c = int(gi.loc[g, "cluster"])
    a.plot(gs.index, gs[g], color=GC[c], lw=1.4)
    a.text(2024.5, ypos[g], g, fontsize=7.5, color=GC[c], va="center")
for c in GN:
    a.plot([], [], color=GC[c], label=GN[c])
a.legend(frameon=False, fontsize=8, loc="lower left")
a.set_xlim(1975, 2034)
a.set_title("漁業種類で見た場合（最大を1、1975〜2024年）", loc="left", fontsize=10.5)
foot(fig)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "fig5_robustness_gear.png", dpi=150)
plt.close(fig)
print("ok")
