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


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def source(fig, text):
    fig.text(0.01, 0.012, text, fontsize=7.5, color=GRAY)

SRC = "出典：厚生労働省「人口動態統計」（確定数）第9.18表をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
Y = pd.read_csv(RES / "yearly.csv").set_index("year")
D = pd.read_csv(ROOT / "data" / "marriage_nationality.csv")


def fig1():
    y = Y.loc[1970:]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(y.index, y.wife_foreign / 1e4, color=C[1], width=0.8, label="夫日本・妻外国")
    ax.bar(y.index, y.husband_foreign / 1e4, bottom=y.wife_foreign / 1e4, color=C[0], width=0.8, label="妻日本・夫外国")
    ax2 = ax.twinx()
    ax2.plot(y.index, y.share, color="#222222", lw=1.8, label="婚姻全体に占める割合（%、右）")
    for yr in (2006, 2015, 2025):
        ax2.annotate(f"{y.share[yr]:.1f}%", (yr, y.share[yr]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9)
    ax.set_ylim(0, 6); ax2.set_ylim(0, 9)
    ax.set_ylabel("夫妻の一方が外国籍の婚姻（万件）"); ax2.set_ylabel("割合（%）")
    ax2.grid(False); ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, frameon=False)
    ax.set_title("国際結婚は2006年の4.47万件（6.1%）がピーク、2025年は1.87万件（3.8%）", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.92, top=0.9, bottom=0.1)
    source(fig, SRC)
    save(fig, "fig1_count_share.png")


def fig2():
    w = D[(D.group == "夫日本・妻外国") & (D.year >= 1992)].pivot(index="year", columns="nationality", values="n")
    cats = [("中国", C[1]), ("フィリピン", C[3]), ("韓国・朝鮮", C[0]), ("タイ", C[4]), ("その他の国", C[2])]
    w["その他（米・英・ブラジル・ペルー）"] = w[["米国", "英国", "ブラジル", "ペルー"]].sum(axis=1)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    bottom = np.zeros(len(w))
    for col, c in cats + [("その他（米・英・ブラジル・ペルー）", "#bbbbbb")]:
        ax.bar(w.index, w[col] / 1e3, bottom=bottom / 1e3, color=c, width=0.8, label=col)
        bottom += w[col].values
    ax.set_ylabel("夫日本・妻外国の婚姻（千件）")
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    ax.set_title("外国籍の妻の国籍：中国とフィリピンが大きく減り、「その他の国」が3割に", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。フィリピン・タイなどは1992年から別に集計")
    save(fig, "fig2_wife_nationality.png")


def fig3():
    c = pd.read_csv(RES / "wife_nationality_contrib_2006_2025.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    y = np.arange(len(c))[::-1]
    ax.barh(y, c["diff"], color=[C[1] if v < 0 else C[0] for v in c["diff"]], height=0.6)
    for yi, d, s in zip(y, c["diff"], c.share_of_change):
        ax.text(d - 150 if d < 0 else d + 150, yi, f"{d:+,.0f}件（減少の{s:.0f}%）" if abs(s) >= 1 else f"{d:+,.0f}件", va="center", ha="right" if d < 0 else "left", fontsize=8.5)
    ax.axvline(0, color="#888888", lw=0.8)
    ax.set_yticks(y, c.nationality)
    ax.set_xlim(-14000, 3000)
    ax.set_xlabel("夫日本・妻外国の婚姻件数の変化（2006年→2025年、件）")
    ax.set_title("2006→2025年の減少（−2.45万件）の78%は、中国とフィリピンの妻", loc="left", fontsize=12)
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.13, right=0.97, top=0.9, bottom=0.13)
    source(fig, SRC + "。国籍は表の順")
    save(fig, "fig3_contrib.png")


def fig4():
    y = Y.loc[1970:]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(y.index, y.husband_foreign_share_of_intl, color=C[0], lw=2.4)
    for yr, dy in ((1970, 9), (1990, -18), (2006, -18), (2025, 9)):
        ax.annotate(f"{yr}年 {y.husband_foreign_share_of_intl[yr]:.1f}%", (yr, y.husband_foreign_share_of_intl[yr]), xytext=(0, dy), textcoords="offset points", ha="center", fontsize=9)
    ax.set_xlim(1967, 2028); ax.set_ylim(0, 75)
    ax.set_ylabel("国際結婚のうち「妻日本・夫外国」の割合（%）")
    ax.set_title("国際結婚のうち夫が外国籍の割合：2006年の19.5%から2025年は38.4%に", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC)
    save(fig, "fig4_husband_foreign_share.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
