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

SRC = "出典：厚生労働省「人口動態統計」（確定数）第9.5表・第10.5表をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
Y = pd.read_csv(RES / "yearly_ratios.csv")


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(Y.year, Y.crude_ratio, color=C[1], lw=2.4, marker="o", ms=3.5, label="見かけの比（その年の離婚÷その年の婚姻）")
    ax.plot(Y.year, Y.ptdr, color=C[0], lw=2.4, marker="o", ms=3.5, label="期間の合計離婚率（同居期間ごとに、その年数前の婚姻で割って足す）")
    for col, c in (("crude_ratio", C[1]), ("ptdr", C[0])):
        ax.annotate(f"{Y[col].iloc[-1]:.1f}%", (Y.year.iloc[-1], Y[col].iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=10, color=c)
    ax.axhline(100 / 3, color="#999999", ls="--", lw=1)
    ax.text(2015.5, 33.7, "3組に1組（33.3%）", fontsize=9, color="#777777")
    ax.set_xlim(1999.5, 2027.5); ax.set_ylim(20, 45)
    ax.set_ylabel("%")
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    ax.set_title("見かけの比は36.6%、同居期間を考えた率は29.5%（2025年）", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC)
    save(fig, "fig1_crude_vs_period.png")


def fig2():
    c = pd.read_csv(RES / "cohort_cumulative.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for k, (m0, g) in enumerate(c.groupby("cohort")):
        ax.plot(g.years_married, g.cum_pct, color=C[k], lw=2.4, label=f"{m0}年に結婚")
        ax.annotate(f"{g.cum_pct.iloc[-1]:.1f}%", (g.years_married.iloc[-1], g.cum_pct.iloc[-1]), xytext=(5, 0), textcoords="offset points", va="center", fontsize=9.5, color=C[k])
    ax.axhline(100 / 3, color="#999999", ls="--", lw=1)
    ax.set_xlim(0, 29); ax.set_ylim(0, 40)
    ax.set_xlabel("結婚してからの年数（2025年まで）")
    ax.set_ylabel("離婚した累積の割合（その年の婚姻件数に対する%）")
    ax.legend(loc="upper left", fontsize=9.5, frameon=False)
    ax.set_title("2000年に結婚した夫婦は、26年目までに30.4%が離婚", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC + "。5年刻みの同居期間は各年に均等に配った近似")
    save(fig, "fig2_cohort_cumulative.png")


def fig3():
    d = pd.read_csv(ROOT / "data" / "divorce_by_duration.csv")
    s = d[d.year == 2025].set_index("duration").n
    cats = ["0", "1", "2", "3", "4", "5-10", "10-15", "15-20", "20-25", "25-30", "30-35", "35+"]
    labs = ["1年未満", "1〜2年", "2〜3年", "3〜4年", "4〜5年", "5〜10年", "10〜15年", "15〜20年", "20〜25年", "25〜30年", "30〜35年", "35年以上"]
    known = s[cats].sum()
    v = 100 * s[cats] / known
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(range(len(cats)), v, color=[C[0]] * 5 + [C[2]] * 7)
    for i, vv in enumerate(v):
        ax.text(i, vv + 0.4, f"{vv:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(range(len(cats)), labs, rotation=30, fontsize=8.5)
    ax.set_ylabel("2025年の離婚に占める割合（%）")
    ax.text(0.98, 0.95, f"同居5年以上が{100 - v[:5].sum():.0f}%、10年以上が{v[6:].sum():.0f}%\n（5年以上は5年刻みの区分）", transform=ax.transAxes, ha="right", va="top", fontsize=9.5)
    ax.set_title("その年の離婚の多くは、何年も前に結婚した夫婦（2025年）", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.18)
    source(fig, SRC + "。同居期間不詳を除く")
    save(fig, "fig3_duration_2025.png")


def fig4():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(Y.year, Y.share_20plus, color=C[3], lw=2.4, marker="o", ms=3.5, label="同居20年以上")
    ax.plot(Y.year, Y.share_under5, color=C[0], lw=2.4, marker="o", ms=3.5, label="同居5年未満")
    for col, c in (("share_20plus", C[3]), ("share_under5", C[0])):
        ax.annotate(f"{Y[col].iloc[-1]:.1f}%", (Y.year.iloc[-1], Y[col].iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=10, color=c)
        ax.annotate(f"{Y[col].iloc[0]:.1f}%", (Y.year.iloc[0], Y[col].iloc[0]), xytext=(-6, 0), textcoords="offset points", va="center", ha="right", fontsize=10, color=c)
    ax.set_xlim(1997, 2027.5); ax.set_ylim(0, 45)
    ax.set_ylabel("離婚件数に占める割合（%）")
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    ax.set_title("同居20年以上の離婚の割合は16.5%→24.2%に上がった", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。同居期間不詳を除く")
    save(fig, "fig4_long_duration_share.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
