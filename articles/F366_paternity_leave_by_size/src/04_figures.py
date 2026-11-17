"""04_figures.py : 図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
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
BLUE, ORANGE, GRAY, LIGHT = "#2a78d6", "#eb6834", "#555555", "#9bb7d9"
SRC = "出典：厚生労働省「雇用均等基本調査」事業所調査（各年度）をもとに作成者が加工して作成"
META = {"Software": None}
SZ = ["500人以上", "100〜499人", "30〜99人", "5〜29人"]
COLS = {"500人以上": "#08519c", "100〜499人": "#3182bd", "30〜99人": "#6baed6", "5〜29人": ORANGE, "総数": GRAY}


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    t = pd.read_csv(RES / "male_rate_by_size.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for s in SZ + ["総数"]:
        ax.plot(t.index, t[s], color=COLS[s], lw=2.2 if s in ("500人以上", "5〜29人") else 1.4, ls="--" if s == "総数" else "-",
                marker="o" if s != "総数" else None, ms=3, label=s if s != "総数" else "全体")
    for s in ["500人以上", "5〜29人"]:
        ax.annotate(f"{t.loc[2025, s]:.1f}", (2025, t.loc[2025, s]), xytext=(5, 0), textcoords="offset points", va="center", color=COLS[s], fontsize=9.5)
    ax.axvline(2022.5, color="#bbbbbb", lw=1, ls=":")
    ax.text(2022.6, 66, "産後パパ育休\n（2022年10月〜）", fontsize=7.5, color="#777777", va="top")
    ax.set_ylim(0, 70)
    ax.set_xlim(2008.5, 2026.4)
    ax.set_ylabel("男性の育児休業取得率（%）")
    ax.set_xlabel("調査年度")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.set_title("男性の取得率：500人以上は60.7%、5〜29人は42.9%（2025年度）", loc="left", fontsize=11.5)
    save(fig, "fig1_male_rate_by_size.png")


def fig2():
    t = pd.read_csv(RES / "male_rate_by_size.csv", index_col=0).loc[2015:]
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.6))
    axs[0].bar(t.index, t.gap_500_vs_5_29, color=[BLUE if v >= 0 else ORANGE for v in t.gap_500_vs_5_29])
    for y, v in t.gap_500_vs_5_29.items():
        axs[0].text(y, v + (0.6 if v >= 0 else -1.8), f"{v:.1f}", ha="center", fontsize=8)
    axs[0].axhline(0, color=GRAY, lw=1)
    axs[0].set_title("差（500人以上 − 5〜29人、ポイント）", loc="left", fontsize=10.5)
    axs[1].plot(t.index, t.ratio_500_vs_5_29, color=BLUE, lw=2.2, marker="o", ms=4)
    for y in [2019, 2025]:
        axs[1].annotate(f"{t.loc[y, 'ratio_500_vs_5_29']:.2f}", (y, t.loc[y, "ratio_500_vs_5_29"]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9)
    axs[1].axhline(1, color=GRAY, lw=1)
    axs[1].set_ylim(0, 2.6)
    axs[1].set_title("比（500人以上 ÷ 5〜29人、倍）", loc="left", fontsize=10.5)
    for ax in axs:
        ax.set_xticks(range(2015, 2026, 2))
        ax.set_xlabel("調査年度")
    fig.suptitle("規模の差はポイントで広がった。比は年ごとの揺れが大きい", x=0.01, ha="left", fontsize=11.5)
    save(fig, "fig2_gap_and_ratio.png")


def fig3():
    p = pd.read_csv(RES / "male_period_grouped.csv")
    p = p[p["size"] == "総数"].set_index("year")
    parts = [("lt2w", "2週間未満", ORANGE), ("w2_1m", "2週間〜1か月未満", "#f2b880"), ("m1_3", "1〜3か月未満", "#6baed6"), ("ge3m", "3か月以上", "#08519c")]
    ys = list(p.index)
    x = np.arange(len(ys))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bottom = np.zeros(len(ys))
    for k, lab, c in parts:
        ax.bar(x, p[k], bottom=bottom, color=c, label=lab, width=0.6)
        for i, v in enumerate(p[k]):
            if v >= 6:
                ax.text(i, bottom[i] + v / 2, f"{v:.0f}", ha="center", va="center", fontsize=8.5, color="white" if k in ("lt2w", "ge3m") else "black")
        bottom += p[k].values
    ax.set_xticks(x, [f"{y}年度" for y in ys])
    ax.set_ylabel("男性の育児休業後復職者の割合（%）")
    ax.set_ylim(0, 112)
    ax.legend(loc="upper center", ncol=4, frameon=False, fontsize=8.5)
    ax.grid(axis="x", visible=False)
    ax.set_title("男性の休業期間：2週間未満は71.4%（2018年度）→20.8%（2025年度）", loc="left", fontsize=11.5)
    save(fig, "fig3_period_distribution.png")


def fig4():
    q = pd.read_csv(RES / "requestion_male_over_female.csv", index_col=0)
    x = np.arange(len(SZ))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar(x - 0.2, q.loc[2019, SZ], width=0.4, color=LIGHT, label="2019年度")
    ax.bar(x + 0.2, q.loc[2025, SZ], width=0.4, color=BLUE, label="2025年度")
    for i, s in enumerate(SZ):
        ax.text(i + 0.2, q.loc[2025, s] + 1, f"{q.loc[2025, s]:.1f}", ha="center", fontsize=9, color=BLUE)
        ax.text(i - 0.2, q.loc[2019, s] + 1, f"{q.loc[2019, s]:.1f}", ha="center", fontsize=9, color="#5b7fae")
    ax.set_xticks(x, SZ)
    ax.set_ylim(0, 80)
    ax.set_ylabel("男性の取得率 ÷ 女性の取得率（%）")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(axis="x", visible=False)
    ax.set_title("女性の取得率に対する男性の取得率：どの規模でも5割を超えた", loc="left", fontsize=11.5)
    save(fig, "fig4_male_over_female.png")


fig1()
fig2()
fig3()
fig4()
