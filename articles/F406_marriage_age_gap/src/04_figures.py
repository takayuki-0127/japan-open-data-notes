"""図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
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
C = ["#2a78d6", "#eb6834", "#1f9e74", "#8a5cc2", "#c2a01f", "#555555", "#d64f8a"]
GRAY = "#555555"
META = {"Software": None}
SRC = "出典：厚生労働省「人口動態統計」（確定数）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
GORDER = ["〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40歳以上"]


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def source(fig, text=SRC):
    fig.text(0.01, 0.012, text, fontsize=7.5, color=GRAY)


def fig1():
    m = pd.read_csv(RES / "mean_age_gap.csv").set_index("year")
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(8.6, 6.4), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
    ax.plot(m.index, m.first_h, color=C[0], lw=2, label="初婚の夫")
    ax.plot(m.index, m.first_w, color=C[1], lw=2, label="初婚の妻")
    ax.set_ylabel("平均婚姻年齢（歳）")
    ax.legend(loc="upper left", frameon=False)
    for y in (1970, 2025):
        ax.annotate(f"{m.first_h[y]:.1f}", (y, m.first_h[y]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=9, color=C[0])
        ax.annotate(f"{m.first_w[y]:.1f}", (y, m.first_w[y]), xytext=(0, -14), textcoords="offset points", ha="center", fontsize=9, color=C[1])
    ax2.plot(m.index, m.gap_first, color="#222222", lw=2)
    for y in (1970, 1990, 2005, 2025):
        ax2.annotate(f"{m.gap_first[y]:.1f}歳", (y, m.gap_first[y]), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9)
    ax2.set_ylim(0, 3.6)
    ax2.set_ylabel("夫と妻の差（歳）")
    ax.set_title(f"初婚の夫と妻の平均年齢の差は、1970年{M['gap_first_1970']}歳 → 2025年{M['gap_first_2025']}歳", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.93, bottom=0.08, hspace=0.12)
    source(fig, "出典：厚生労働省「人口動態統計」（確定数）第9.11表（1947年以降）をもとに作成者が加工して作成")
    save(fig, "fig1_mean_gap.png")


def fig2():
    d = pd.read_csv(RES / "gap_dist_share.csv").set_index("year")
    cols = [("wife_older", "妻が年上", C[1]), ("same", "同い年", C[4]), ("h1_3", "夫が1〜3歳上", "#9cc3ee"),
            ("h4_6", "夫が4〜6歳上", C[0]), ("h7p", "夫が7歳以上上", "#1b4f8f")]
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    x = np.arange(len(d))
    bottom = np.zeros(len(d))
    for k, lab, col in cols:
        ax.bar(x, d[k], bottom=bottom, color=col, width=0.75, label=lab)
        bottom += d[k].values
    for i, y in enumerate(d.index):
        if y in (1970, 1995, 2025):
            ax.text(i, d.wife_older[y] / 2, f"{d.wife_older[y]:.1f}", ha="center", va="center", fontsize=8.5, color="white")
    ax.set_xticks(x, [str(y) for y in d.index], rotation=60, fontsize=8.5)
    ax.set_ylim(0, 100); ax.set_ylabel("初婚どうしの結婚に占める割合（%）")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=5, frameon=False, fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_title(f"妻が年上の結婚は{M['wife_older_1970']}%→{M['wife_older_2025']}%、同い年は{M['same_1970']}%→{M['same_2025']}%に", loc="left", fontsize=12)
    ax.text(0, -0.30, "注：1970〜2010年は5年ごと、2014年以降は毎年（横軸の間隔は等しくない）", transform=ax.transAxes, fontsize=8, color=GRAY)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.27)
    source(fig, "出典：厚生労働省「人口動態統計」（確定数）第9.14表をもとに作成者が加工して作成")
    save(fig, "fig2_gap_distribution.png")


def fig3():
    by = pd.read_csv(RES / "by_wife_age.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 4.9))
    x = np.arange(len(GORDER)); w = 0.38
    for j, (y, col) in enumerate([(1995, "#9aa7b5"), (2025, C[1])]):
        b = by[by.year == y].set_index("g").reindex(GORDER)
        a1.bar(x + (j - 0.5) * w, b.share_of_year, width=w, color=col, label=f"{y}年")
        a2.bar(x + (j - 0.5) * w, b.wife_older, width=w, color=col, label=f"{y}年")
        for i, v in enumerate(b.wife_older):
            a2.text(i + (j - 0.5) * w, v + 0.8, f"{v:.0f}", ha="center", fontsize=8)
    for a in (a1, a2):
        a.set_xticks(x, GORDER, fontsize=9); a.grid(axis="x", visible=False); a.set_xlabel("妻の結婚したときの年齢")
    a1.set_ylabel("初婚どうしの結婚に占める割合（%）"); a1.set_title("妻の年齢の構成", fontsize=10.5)
    a2.set_ylabel("妻が年上の割合（%）"); a2.set_title("その年齢で妻が年上の割合", fontsize=10.5)
    a1.legend(frameon=False)
    d = M["decomp_main"]
    fig.suptitle(f"妻が年上の割合の上がり（+{d['change']:.1f}ポイント）のうち、{100 - d['within_share']:.0f}%は妻の結婚年齢が上がった分", x=0.01, ha="left", fontsize=12)
    fig.text(0.01, 0.06, f"分解（1995→2025年、妻の年齢5区分）：構成の変化 +{d['composition']:.1f}、同じ年齢の中での変化 +{d['within']:.1f} ポイント。"
             "夫の年齢で区分すると結果が変わる（本文の頑健性を参照）", fontsize=8, color=GRAY)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.2, wspace=0.28)
    source(fig, "出典：厚生労働省「人口動態統計」（確定数）中巻 婚姻 夫妻の年齢（各歳）別婚姻件数（初婚どうし）をもとに作成者が加工して作成")
    save(fig, "fig3_age_composition.png")


def fig4():
    d = pd.read_csv(RES / "gap_dist_share.csv").set_index("year")
    by = pd.read_csv(RES / "by_wife_age.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 4.7), gridspec_kw={"width_ratios": [1.2, 1]})
    a1.plot(d.index, d.h7p, color="#1b4f8f", lw=2, marker="o", ms=4)
    for y in (1970, 1975, 1985, 2015, 2025):
        a1.annotate(f"{d.h7p[y]:.1f}", (y, d.h7p[y]), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9)
    a1.set_ylim(0, 15); a1.set_ylabel("夫が7歳以上年上の割合（%）"); a1.set_title("初婚どうしの結婚全体", fontsize=10.5)
    x = np.arange(len(GORDER)); w = 0.38
    for j, (y, col) in enumerate([(1995, "#9aa7b5"), (2025, "#1b4f8f")]):
        b = by[by.year == y].set_index("g").reindex(GORDER)
        a2.bar(x + (j - 0.5) * w, b.h7, width=w, color=col, label=f"{y}年")
    a2.set_xticks(x, GORDER, fontsize=8.5, rotation=20); a2.grid(axis="x", visible=False)
    a2.set_ylabel("夫が7歳以上年上の割合（%）")
    a2.set_title("妻の結婚したときの年齢別", fontsize=10.5); a2.legend(frameon=False, fontsize=9)
    fig.suptitle(f"夫が7歳以上年上の結婚は、2015年{M['h7p_2015']}% → 2025年{M['h7p_2025']}%に下がった", x=0.01, ha="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.16, wspace=0.25)
    source(fig)
    save(fig, "fig4_large_gap.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
