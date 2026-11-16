"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.unicode_minus": False})
EL, LA, NE = "#d4561f", "#2a78d6", "#a3a29d"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：気象庁「エルニーニョ監視速報」「日本の季節平均気温」「過去の気象データ検索」をもとに作成者が加工して作成"
META = {"Software": None}


def mi(v, fmt):
    return format(v, fmt).replace("-", "−")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def minus_ticks(ax, axis="y"):
    if axis == "y":
        ax.set_yticks(ax.get_yticks()); ax.set_yticklabels([mi(t, "g") for t in ax.get_yticks()])
    else:
        ax.set_xticks(ax.get_xticks()); ax.set_xticklabels([mi(t, "g") for t in ax.get_xticks()])


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
t = pd.read_csv(R / "summer_table.csv", index_col=0)
col = np.where(t["elnino_summer"] == 1, EL, np.where(t["lanina_summer"] == 1, LA, NE))

# ---- 図1：日本の夏の気温と、エルニーニョ・ラニーニャの夏 -------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 4.8))
x = t.index.values.astype(float)
b = np.polyfit(x, t["jp_jja"].values, 1)
ax.plot(x, t["jp_jja"], color=GRID, lw=1.2, zorder=1)
ax.scatter(x, t["jp_jja"], c=col, s=30, zorder=3, edgecolor="white", lw=0.5)
ax.plot(x[[0, -1]], np.polyval(b, x[[0, -1]]), color=INK2, lw=1.1, ls="--", zorder=2)
ax.axhline(0, color=INK2, lw=0.6)
for lab, c_ in (("エルニーニョの夏", EL), ("ラニーニャの夏", LA), ("どちらでもない夏", NE)):
    ax.scatter([], [], c=c_, s=30, label=lab)
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
ax.set_ylabel("夏（6〜8月）の平均気温の偏差（℃）")
ax.set_ylim(-2.0, 2.5); minus_ticks(ax); ax.set_ylim(-2.0, 2.5)
ax.text(2025, -1.75, f"破線：長期の上昇（10年あたり{main['trend_jp_jja_per_decade']:.2f}℃）", fontsize=9, color=INK2, ha="right")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("日本の夏の平均気温（15地点平均、1991〜2020年平均からの差）、1949〜2025年", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig1_timeseries.png")

# ---- 図2：群ごとの平均（長期の上昇を除いた残り） ----------------------------------------------------------
H1 = main["H1"]; reg = main["H2"]["by_region"]
groups = ["日本（15地点）", "北日本", "東日本", "西日本", "沖縄・奄美"]
vals = [(H1["mean_el"], H1["mean_neu"], H1["mean_la"])] + [(reg[g]["mean_el"], reg[g]["mean_neu"], reg[g]["mean_la"]) for g in groups[1:]]
fig, ax = plt.subplots(figsize=(8.4, 4.8))
xx = np.arange(len(groups)); w = 0.26
for k, (lab, c_) in enumerate((("エルニーニョの夏", EL), ("どちらでもない夏", NE), ("ラニーニャの夏", LA))):
    v = [vv[k] for vv in vals]
    ax.bar(xx + (k - 1) * w, v, width=w * 0.95, color=c_, label=lab)
    for xi, vi in zip(xx + (k - 1) * w, v):
        ax.text(xi, vi + (0.02 if vi >= 0 else -0.02), mi(vi, "+.2f"), ha="center", va="bottom" if vi >= 0 else "top", fontsize=8)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xx); ax.set_xticklabels(groups)
ax.set_ylim(-0.5, 0.45); minus_ticks(ax)
ax.set_ylabel("長期の上昇を除いた残りの平均（℃）")
ax.legend(frameon=False, loc="upper right", fontsize=9, ncol=3)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("エルニーニョの夏は、どの地方でも平均して低め（22回・37回・18回）", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig2_groups.png")

# ---- 図3：NINO.3 と夏の気温の散布図 ---------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.4, 5.2))
ax.scatter(t["nino3_jja"], t["jp_resid"], c=col, s=34, edgecolor="white", lw=0.5)
sl = np.polyfit(t["nino3_jja"], t["jp_resid"], 1)
xs = np.array([-1.6, 3.0])
ax.plot(xs, np.polyval(sl, xs), color=INK2, lw=1, ls="--")
q = main["H4"]["cool_threshold_resid"]
ax.axhline(q, color=LA, lw=0.8, ls=":")
ax.text(-1.65, q - 0.06, "これより下が「冷夏」（下から3分の1）", fontsize=8.5, color=LA, ha="left", va="top")
for y in (1993, 2003, 2023, 2010):
    if y in t.index:
        ax.annotate(str(y), (t.loc[y, "nino3_jja"], t.loc[y, "jp_resid"]), xytext=(4, 3), textcoords="offset points", fontsize=8.5, color=INK2)
ax.set_xlabel("6〜8月の NINO.3 の海面水温の基準値との差（℃）")
ax.set_ylabel("日本の夏の気温（長期の上昇を除いた残り、℃）")
ax.set_xticks([-1, 0, 1, 2, 3]); ax.set_yticks([-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5])
minus_ticks(ax, "x"); minus_ticks(ax, "y")
ax.set_xlim(-1.7, 3.1); ax.set_ylim(-2.0, 1.6)
ax.text(-1.6, 1.4, f"相関 {mi(main['H3']['r'], '.2f')}（77年）", fontsize=9.5, color=INK2)
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("夏の NINO.3 と日本の夏の気温（点の色は図1と同じ）", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC, fontsize=7, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig3_scatter.png")

# ---- 図4：月別と段階別 ------------------------------------------------------------------------------
fig, axs = plt.subplots(1, 2, figsize=(9, 4.4), gridspec_kw={"width_ratios": [1, 1.3]})
ax = axs[0]
m = pd.DataFrame(req["month"])
ax.bar(m["month"], m["diff_el_neu"], color=EL, width=0.6)
for i, (v, p) in enumerate(zip(m["diff_el_neu"], m["p_el"])):
    ax.text(i, v - 0.02, f"{mi(v, '+.2f')}\n(p={p:.2f})", ha="center", va="top", fontsize=8.5)
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylim(-0.8, 0.1); minus_ticks(ax)
ax.set_ylabel("どちらでもない夏との差（℃）")
ax.set_title("月別（4地方の平均）", fontsize=10.5, loc="left")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax = axs[1]
p = pd.DataFrame(req["phase"])
labs = ["始まりの年", "前の冬から\n続く", "前の冬にあり\n夏には終わった"]
ax.bar(labs, p["diff_vs_neutral"], color=[EL, EL, "#f4b48f"], width=0.6)
for i, (v, pp, n) in enumerate(zip(p["diff_vs_neutral"], p["p"], p["n"])):
    ax.text(i, v - 0.02, f"{mi(v, '+.2f')}\n({n}回, p={pp:.2f})", ha="center", va="top", fontsize=8.5)
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylim(-0.8, 0.1); minus_ticks(ax)
ax.set_title("エルニーニョの段階別（日本の15地点）", fontsize=10.5, loc="left")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.text(0.01, 0.01, SRC + "。長期の上昇を除いた残りで比べた", fontsize=7, color=INK2)
fig.tight_layout(rect=(0, 0.04, 1, 1))
save(fig, "fig4_month_phase.png")
print("figures done")
