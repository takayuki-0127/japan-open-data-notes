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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「地方公共団体定員管理調査」「住民基本台帳に基づく人口、人口動態及び世帯数調査」をもとに作成者が加工して作成"
META = {"Software": None}
ORDER = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上", "指定都市"]


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
bs = pd.read_csv(R / "by_size.csv")
b25 = bs[bs.year == 2025].set_index("size").loc[ORDER]
x = np.arange(len(ORDER))
xt = [f"{s}\n（{int(b25.n[s])}団体）" for s in ORDER]

# 図1
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(x, b25.general_median, 0.6, color=C[0], label="中央値")
ax.errorbar(x, b25.general_median, yerr=[b25.general_median - b25.general_q1, b25.general_q3 - b25.general_median], fmt="none", ecolor=INK2, capsize=4, lw=1.2, label="四分位の幅（真ん中の半分）")
for xi, v in zip(x, b25.general_median):
    ax.text(xi + 0.32, v, f"{v:.1f}", va="bottom", fontsize=9, color=INK)
ax.set_xticks(x, xt, fontsize=8.8)
ax.set_ylabel("住民1,000人あたりの一般行政の職員数（人）")
ax.legend(frameon=False, loc="upper right")
h1 = m["hypotheses"]["H1"]
finish(fig, ax, f"5千人未満の町村は1,000人あたり{h1['small_median']:.1f}人、10万〜30万人の市の{h1['ratio']:.1f}倍（2025年）")
save(fig, "fig1_per1000_by_size.png")

# 図2
d = pd.read_csv(R / "per1000_by_municipality.csv", dtype={"code": str})
d = d[(d.year == 2025) & (d.general > 0)]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.scatter(d["pop"], d.general, s=8, color=C[0], alpha=0.45, lw=0)
b, a = np.polyfit(np.log(d["pop"]), np.log(d.general), 1)
xx = np.logspace(np.log10(d["pop"].min()), np.log10(d["pop"].max()), 50)
ax.plot(xx, np.exp(a) * xx ** b, color=C[1], lw=2, label=f"当てはめた線：人口が10倍で職員は{10 ** b:.1f}倍（傾き {b:.2f}）")
ax.plot(xx, xx * float(np.exp(np.log(d.general).mean() - np.log(d["pop"]).mean())), color=INK2, lw=1, ls="--", label="人口に比例する場合（傾き1）")
ax.set_xscale("log"); ax.set_yscale("log")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
ax.set_xlabel("人口（人、対数目盛）　※点は1,741の市区町村")
ax.set_ylabel("一般行政の職員数（人、対数目盛）")
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
finish(fig, ax, "人口が大きいほど、1人あたりの職員は少ない（2025年）", grid="both")
save(fig, "fig2_scatter_loglog.png")

# 図3：2020→2025年の変化
c = pd.read_csv(R / "change_2020_2025.csv", index_col=0).loc[ORDER]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
w = 0.38
ax.bar(x - w / 2, c.pop_change_pct, w * 0.95, color=C[2], label="人口の変化")
ax.bar(x + w / 2, c.staff_change_pct, w * 0.95, color=C[0], label="一般行政の職員数の変化")
for xi, a1, a2 in zip(x, c.pop_change_pct, c.staff_change_pct):
    ax.text(xi - w / 2, a1 - 0.6, f"{a1:.1f}", ha="center", va="top", fontsize=8.6, color=INK)
    ax.text(xi + w / 2, a2 + (0.3 if a2 >= 0 else -0.6), f"{a2:.1f}", ha="center", va="bottom" if a2 >= 0 else "top", fontsize=8.6, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, ORDER, fontsize=9)
ax.set_ylim(-13, 6)
ax.set_ylabel("2020→2025年の変化（%）")
ax.legend(frameon=False, loc="lower right")
finish(fig, ax, "小さな町村は人口が1割減っても職員はほぼ同じ。大きな市は職員が3%台増えた")
save(fig, "fig3_change_2020_2025.png")

# 図4：一般管理と福祉関係
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(x - w / 2, b25.gen_admin_median, w * 0.95, color=C[3], label="一般管理（総務・企画・税務など）")
ax.bar(x + w / 2, b25.welfare_median, w * 0.95, color=C[4], label="福祉関係（民生など）")
for xi, a1, a2 in zip(x, b25.gen_admin_median, b25.welfare_median):
    ax.text(xi - w / 2, a1 + 0.2, f"{a1:.1f}", ha="center", fontsize=8.6, color=INK)
    ax.text(xi + w / 2, a2 + 0.2, f"{a2:.1f}", ha="center", fontsize=8.6, color=INK)
ax.set_xticks(x, ORDER, fontsize=9)
ax.set_ylabel("住民1,000人あたりの職員数（中央値、人）")
ax.legend(frameon=False, loc="upper right")
h4 = m["hypotheses"]["H4"]
finish(fig, ax, f"規模の差は一般管理で大きい（5千人未満は10万〜30万人の{h4['ratio_gen_admin']:.1f}倍、福祉は{h4['ratio_welfare']:.1f}倍）")
save(fig, "fig4_admin_vs_welfare.png")
