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
SRC = "出典：厚生労働省「一般職業紹介状況」職業別労働市場関係指標（パートを含む常用、年度の月平均）をもとに作成者が加工して作成"
META = {"Software": None}
MAJOR = ["管理", "専門・技術", "事務", "販売", "サービス", "保安", "農林漁業", "生産工程", "輸送・機械運転", "建設・採掘", "運搬・清掃・包装等"]


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    t = pd.read_csv(RES / "mismatch_timeseries.csv")
    lk = pd.read_csv(RES / "mismatch_linked.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for era, c, lab in [("H23分類", BLUE, "大分類（平成23年改定の分類）"), ("R4分類", GREEN, "大分類（令和4年改定の分類）")]:
        d = t[t.era == era]
        ax.plot(d.fy, d.mm_major * 100, color=c, lw=2.2, marker="o", ms=4, label=lab)
    for era, c in [("H23分類", BLUE), ("R4分類", GREEN)]:
        d = t[t.era == era]
        ax.plot(d.fy, d.mm_sub * 100, color=c, lw=1.2, ls="--", marker="o", ms=2.5)
    ax.plot([], [], color=GRAY, ls="--", lw=1.2, label="中分類（点線）")
    ax.set_ylim(0, 45)
    ax.set_ylabel("ミスマッチ指標（%）")
    ax.set_xlabel("年度")
    ax2 = ax.twinx()
    ax2.bar(lk.index, lk.jobs_ratio_total, color="#dddddd", width=0.6, zorder=0, label="有効求人倍率（右の目盛り）")
    ax2.set_ylim(0, 4.5)
    ax2.set_ylabel("有効求人倍率（倍）")
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=9, ncol=2)
    ax.set_xticks(range(2012, 2026, 2))
    ax.set_title("職業の構成のずれ：14年間ほぼ30%で、景気がよい年にやや大きい", loc="left", fontsize=11.5)
    save(fig, "fig1_mismatch_index.png")


def fig2():
    d = pd.read_csv(RES / "major_shares_r4.csv", header=[0, 1], index_col=0).loc[2025]
    y = np.arange(len(MAJOR))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(y - 0.2, [d[("求職の構成比", k)] for k in MAJOR], height=0.4, color=ORANGE, label="求職者の構成比")
    ax.barh(y + 0.2, [d[("求人の構成比", k)] for k in MAJOR], height=0.4, color=BLUE, label="求人の構成比")
    for i, k in enumerate(MAJOR):
        ax.text(d[("求職の構成比", k)] + 0.4, i - 0.2, f"{d[('求職の構成比', k)]:.1f}", va="center", fontsize=8, color=ORANGE)
        ax.text(d[("求人の構成比", k)] + 0.4, i + 0.2, f"{d[('求人の構成比', k)]:.1f}", va="center", fontsize=8, color=BLUE)
    ax.set_yticks(y, MAJOR)
    ax.invert_yaxis()
    ax.set_xlabel("構成比（%、2025年度）")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="y", visible=False)
    ax.set_title("2025年度：事務は求職者の31.6%、求人の9.6%", loc="left", fontsize=11.5)
    save(fig, "fig2_shares_2025.png")


def fig3():
    a = pd.read_csv(RES / "major_shares_h23.csv", header=[0, 1], index_col=0).loc[2012]
    b = pd.read_csv(RES / "major_shares_r4.csv", header=[0, 1], index_col=0).loc[2025]
    y = np.arange(len(MAJOR))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(y - 0.2, [a[("求人倍率", k)] for k in MAJOR], height=0.4, color=LIGHT, label="2012年度")
    ax.barh(y + 0.2, [b[("求人倍率", k)] for k in MAJOR], height=0.4, color=BLUE, label="2025年度")
    for i, k in enumerate(MAJOR):
        ax.text(b[("求人倍率", k)] + 0.08, i + 0.2, f"{b[('求人倍率', k)]:.2f}", va="center", fontsize=8, color=BLUE)
    ax.axvline(1, color=GRAY, lw=1, ls="--")
    ax.set_yticks(y, MAJOR)
    ax.invert_yaxis()
    ax.set_xlabel("有効求人倍率（倍）")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="y", visible=False)
    ax.set_title("職業別の求人倍率：どの職業でも上がり、事務は0.24→0.42倍", loc="left", fontsize=11.5)
    save(fig, "fig3_ratio_by_major.png")


def fig4():
    d = pd.read_csv(RES / "requestion_ratio_dispersion.csv")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for era, c, lab in [("H23分類", BLUE, "平成23年改定の分類"), ("R4分類", GREEN, "令和4年改定の分類")]:
        z = d[d.era == era]
        ax.plot(z.fy, z.wsd_log_ratio, color=c, lw=2.2, marker="o", ms=4, label=lab)
    ax.set_ylim(0.6, 0.9)
    ax.set_ylabel("職業別の求人倍率の散らばり\n（対数の標準偏差、求職者数で重み）")
    ax.set_xlabel("年度")
    ax.set_xticks(range(2012, 2026, 2))
    ax.legend(loc="upper left", frameon=False)
    ax.set_title("職業の間の求人倍率の散らばりも、ほとんど変わっていない", loc="left", fontsize=11.5)
    save(fig, "fig4_ratio_dispersion.png")


fig1()
fig2()
fig3()
fig4()
