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
BLUE, ORANGE, GRAY, GREEN, LIGHT = "#2a78d6", "#eb6834", "#555555", "#3a9e6f", "#9bb7d9"
SRC = "出典：総務省「労働力調査」詳細集計 長期時系列（年平均・四半期平均、労働者派遣事業所の派遣社員）をもとに作成者が加工して作成"
META = {"Software": None}
AGES = ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65歳以上"]


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    s = pd.read_csv(RES / "dispatched_annual.csv", index_col=0)
    q = pd.read_csv(RES / "dispatched_quarterly.csv")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(q.t + 0.125, q["派遣社員"], color="#bbbbbb", lw=1, label="男女計（四半期）")
    ax.plot(s.index + 0.5, s["派遣社員"], color=BLUE, lw=2.4, marker="o", ms=4, label="男女計（年平均）")
    ax.plot(s.index + 0.5, s["女"], color=ORANGE, lw=1.6, marker="o", ms=3, label="女")
    ax.plot(s.index + 0.5, s["男"], color=GREEN, lw=1.6, marker="o", ms=3, label="男")
    for y in [2008, 2012, 2025]:
        ax.annotate(f"{s.loc[y, '派遣社員']:.0f}", (y + 0.5, s.loc[y, "派遣社員"]), xytext=(0, 8), textcoords="offset points", ha="center", color=BLUE, fontsize=9.5)
    for x, t in [(2004, "製造業への派遣の解禁"), (2012.75, "法改正（日雇い派遣の原則禁止）"), (2013, "調査票の変更"), (2015.75, "法改正（期間の上限の見直し）")]:
        ax.axvline(x, color="#cccccc", lw=1, ls=":")
    ax.text(2004.1, 172, "製造業への派遣\nの解禁（2004年）", fontsize=7.5, color="#777777", va="top")
    ax.text(2013.1, 172, "法改正（2012年10月）\n調査票の変更（2013年）", fontsize=7.5, color="#777777", va="top")
    ax.text(2015.85, 40, "法改正\n（2015年9月）", fontsize=7.5, color="#777777")
    ax.set_ylim(0, 175)
    ax.set_ylabel("派遣社員（万人）")
    ax.set_xlabel("年")
    ax.legend(loc="lower right", frameon=False, fontsize=9, ncol=2)
    ax.set_title("派遣社員は2008年140万人→2012年91万人→2025年156万人（年平均）", loc="left", fontsize=11.5)
    save(fig, "fig1_dispatched_trend.png")


def fig2():
    sh = pd.read_csv(RES / "dispatched_age_share.csv", index_col=0)
    cols = ["#c6dbef", "#9ecae1", "#6baed6", ORANGE, "#d95f0e", "#993404"]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bottom = np.zeros(len(sh))
    for a_, c in zip(AGES, cols):
        ax.bar(sh.index, sh[a_], bottom=bottom, color=c, label=a_, width=0.8)
        bottom += sh[a_].values
    o45 = sh[["45〜54歳", "55〜64歳", "65歳以上"]].sum(axis=1)
    ax.plot(o45.index, 100 - o45, color="black", lw=1.4, ls="--", label="45歳以上の境目")
    ax.set_ylim(0, 100)
    ax.set_ylabel("派遣社員の年齢構成（%）")
    ax.set_xlabel("年")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=9, reverse=True)
    ax.set_title("派遣社員のうち45歳以上は26.4%（2008年）→55.8%（2025年）", loc="left", fontsize=11.5)
    save(fig, "fig2_age_composition.png")


def fig3():
    s = pd.read_csv(RES / "dispatched_annual.csv", index_col=0)
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.6))
    axs[0].plot(s.index, s.share_of_nonregular, color=BLUE, lw=2.2, marker="o", ms=3.5)
    axs[0].set_title("非正規の職員・従業員に占める割合（%）", loc="left", fontsize=10.5)
    axs[1].plot(s.index, s.share_of_employees, color=GREEN, lw=2.2, marker="o", ms=3.5)
    axs[1].set_title("役員を除く雇用者に占める割合（%）", loc="left", fontsize=10.5)
    for ax, col in zip(axs, ["share_of_nonregular", "share_of_employees"]):
        for y in [2008, 2012, 2025]:
            ax.annotate(f"{s.loc[y, col]:.1f}", (y, s.loc[y, col]), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
        ax.set_xlabel("年")
    fig.suptitle("割合で見ると：非正規の中では7.9%→7.3%、雇用者の中では2.7%のまま", x=0.01, ha="left", fontsize=11.5)
    save(fig, "fig3_shares.png")


fig1()
fig2()
fig3()
