"""04_figures.py : 図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if pathlib.Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#888888", "axes.grid": True,
                     "grid.color": "#e6e6e6", "grid.linewidth": 0.8})
BLUE, ORANGE, GRAY, GREEN, LIGHT = "#2a78d6", "#eb6834", "#555555", "#3a9e6f", "#9bb7d9"
SRC = "出典：厚生労働省「賃金構造基本統計調査」（一般労働者、産業計、6月分の所定内給与。2006〜2019年は令和2年と同じ推計方法による参考集計）をもとに作成者が加工して作成"
META = {"Software": None}
COLS = {"1000人以上": "#08519c", "100〜999人": "#6baed6", "10〜99人": ORANGE, "企業規模計": GRAY}
T = pd.read_csv(RES / "ratio_60_64_to_55_59.csv", index_col=0)
main = json.loads((RES / "main.json").read_text(encoding="utf-8"))


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=6.5, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def mark(ax):
    ax.set_xticks(range(2006, 2026, 2))
    ax.axvline(2012.5, color="#bbbbbb", lw=1, ls=":")
    ax.text(2012.6, ax.get_ylim()[1] - 1, "希望者全員の65歳までの雇用\n（2013年4月〜）", fontsize=7.5, color="#777777", va="top")


def fig1():
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for sz in ["1000人以上", "100〜999人", "10〜99人", "企業規模計"]:
        s = T[f"男_{sz}"]
        ax.plot(s.index, s, color=COLS[sz], lw=2.2 if sz != "企業規模計" else 1.6, ls="--" if sz == "企業規模計" else "-",
                marker="o", ms=3, label="規模計" if sz == "企業規模計" else sz)
        dy = {"100〜999人": 4, "企業規模計": -5}.get(sz, 0)
        ax.annotate(f"{s.loc[2025]:.1f}", (2025, s.loc[2025]), xytext=(5, dy), textcoords="offset points", va="center", color=COLS[sz], fontsize=9)
    ax.set_ylim(55, 100)
    ax.set_xlim(2005.5, 2026.3)
    mark(ax)
    ax.set_ylabel("60〜64歳 ÷ 55〜59歳（%）")
    ax.set_xlabel("年（各年6月分）")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.set_title("男の60〜64歳は55〜59歳の80.5%。1,000人以上は73.5%、10〜99人は93.4%（2025年）", loc="left", fontsize=11)
    save(fig, "fig1_male_ratio_by_size.png")


def fig2():
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for k, lab, c, ls in [("女_企業規模計", "女（学歴計）", ORANGE, "-"), ("男_企業規模計", "男（学歴計）", BLUE, "-"),
                          ("男_高校", "男・高校卒", GREEN, "--"), ("男_大学大学院", "男・大学大学院卒", "#08519c", "--")]:
        s = T[k]
        ax.plot(s.index, s, color=c, lw=2.0, ls=ls, marker="o", ms=3, label=lab)
        ax.annotate(f"{s.loc[2025]:.1f}", (2025, s.loc[2025]), xytext=(5, 0), textcoords="offset points", va="center", color=c, fontsize=9)
    ax.set_ylim(55, 100)
    ax.set_xlim(2005.5, 2026.3)
    mark(ax)
    ax.set_ylabel("60〜64歳 ÷ 55〜59歳（%）")
    ax.set_xlabel("年（各年6月分）")
    ax.legend(loc="lower left", frameon=False, fontsize=9, ncol=2)
    ax.set_title("女は88.6%。男の大学・大学院卒は2006年も2025年も78%台（途中は72%まで下がった）", loc="left", fontsize=11.5)
    save(fig, "fig2_sex_education.png")


def fig3():
    w = main["wages"]
    sizes = ["1000人以上", "100〜999人", "10〜99人"]
    x = np.arange(len(sizes))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    a = [w[f"男_{s}_2025"][0] for s in sizes]
    b = [w[f"男_{s}_2025"][1] for s in sizes]
    ax.bar(x - 0.2, a, width=0.4, color=LIGHT, label="55〜59歳")
    ax.bar(x + 0.2, b, width=0.4, color=BLUE, label="60〜64歳")
    for i in range(len(sizes)):
        ax.text(i - 0.2, a[i] + 5, f"{a[i]:.1f}", ha="center", fontsize=9)
        ax.text(i + 0.2, b[i] + 5, f"{b[i]:.1f}", ha="center", fontsize=9, color=BLUE)
        ax.text(i, max(a[i], b[i]) + 40, f"差 {a[i] - b[i]:.1f}千円", ha="center", fontsize=9.5, color=ORANGE)
    ax.set_xticks(x, sizes)
    ax.set_ylim(0, 620)
    ax.set_ylabel("所定内給与（千円、男、2025年）")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(axis="x", visible=False)
    ax.set_title(f"男の所定内給与（2025年）：1,000人以上は月{(a[0] - b[0]) / 10:.1f}万円、10〜99人は{(a[2] - b[2]) / 10:.1f}万円の差", loc="left", fontsize=11.5)
    save(fig, "fig3_male_wage_levels_2025.png")


def fig4():
    n = pd.read_csv(RES / "requestion_worker_ratio.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for sz in ["1000人以上", "100〜999人", "10〜99人", "企業規模計"]:
        s = n[f"男_{sz}"]
        ax.plot(s.index, s, color=COLS[sz], lw=2.2 if sz != "企業規模計" else 1.6, ls="--" if sz == "企業規模計" else "-",
                marker="o", ms=3, label="規模計" if sz == "企業規模計" else sz)
    ax.set_ylim(0, 100)
    mark(ax)
    ax.set_ylabel("60〜64歳 ÷ 55〜59歳の労働者数（%、男）")
    ax.set_xlabel("年（各年6月分）")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.set_title("一般労働者の数：60〜64歳は55〜59歳の約7割（男、2013年以降）", loc="left", fontsize=11.5)
    save(fig, "fig4_worker_count_ratio.png")


fig1()
fig2()
fig3()
fig4()
