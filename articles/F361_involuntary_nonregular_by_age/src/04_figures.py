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
SRC = "出典：総務省「労働力調査」詳細集計（年平均）をもとに作成者が加工して作成"
SRC2 = "出典：総務省「労働力調査」詳細集計（年平均）、厚生労働省「一般職業紹介状況」をもとに作成者が加工して作成"
META = {"Software": None}
main = json.loads((RES / "main.json").read_text(encoding="utf-8"))
AGES = ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65歳以上"]


def save(fig, name, src=SRC):
    fig.text(0.01, 0.012, src, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    x = pd.read_csv(RES / "share_vs_jobs_ratio.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(x.index, x.share, color=BLUE, lw=2.4, marker="o", ms=4, label="不本意の割合（左の目盛り）")
    for y in [2013, 2019, 2025]:
        ax.annotate(f"{x.loc[y, 'share']:.1f}%", (y, x.loc[y, "share"]), xytext=(0, 8), textcoords="offset points",
                    ha="center", color=BLUE, fontsize=9.5)
    ax.set_ylim(0, 22)
    ax.set_ylabel("非正規のうち「正規の仕事がないから」の割合（%）")
    ax2 = ax.twinx()
    ax2.plot(x.index, x.jr, color=ORANGE, lw=1.6, ls="--", marker="s", ms=3.5, label="有効求人倍率（右の目盛り）")
    ax2.set_ylim(0, 2.2)
    ax2.set_ylabel("有効求人倍率（倍、年平均）")
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left", frameon=False)
    ax.set_xticks(range(2013, 2026, 2))
    ax.set_title("不本意の割合は19.2%から8.4%に。求人倍率が下がった年も下がり続けた", loc="left", fontsize=11.5)
    save(fig, "fig1_involuntary_share_trend.png", SRC2)


def fig2():
    sh = pd.read_csv(RES / "share_by_sex_age.csv", header=[0, 1], index_col=0)
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), sharey=True)
    xx = np.arange(len(AGES))
    for ax, sex in zip(axs, ["男", "女"]):
        v13 = [sh.loc[2013, (sex, a)] for a in AGES]
        v25 = [sh.loc[2025, (sex, a)] for a in AGES]
        ax.bar(xx - 0.2, v13, width=0.4, color=LIGHT, label="2013年")
        ax.bar(xx + 0.2, v25, width=0.4, color=BLUE, label="2025年")
        for i, v in enumerate(v25):
            ax.text(i + 0.2, v + 0.6, f"{v:.1f}", ha="center", fontsize=8.5, color=BLUE)
        ax.axhline(sh.loc[2025, ("男女計", "年齢計")], color=ORANGE, lw=1.2, ls="--", label="全体（男女計・年齢計、2025年）")
        ax.set_xticks(xx, AGES, rotation=30)
        ax.set_title(sex, loc="left", fontsize=11)
        ax.grid(axis="x", visible=False)
    axs[0].set_ylabel("不本意の割合（%）")
    h, l = axs[0].get_legend_handles_labels()
    axs[1].legend(h, l, loc="upper right", frameon=False)
    fig.suptitle("年齢・男女別の不本意の割合：男の25〜54歳は2025年でも約2割", x=0.01, ha="left", fontsize=11.5)
    save(fig, "fig2_share_by_sex_age.png")


def fig3():
    ss = main["shiftshare_age6"]
    comp = pd.read_csv(RES / "age_composition.csv", index_col=0)
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), gridspec_kw={"width_ratios": [1, 1.3]})
    ax = axs[0]
    vals = [ss["total_pt"], ss["within_pt"], ss["composition_pt"]]
    labs = ["低下の\n全体", "各年齢の\n中の低下", "年齢構成\nの変化"]
    ax.bar(range(3), vals, color=[GRAY, BLUE, ORANGE])
    for i, v in enumerate(vals):
        ax.text(i, v - 0.6, f"{v:.1f}", ha="center", va="top", fontsize=10)
    ax.set_xticks(range(3), labs)
    ax.set_ylabel("2013→2025年の変化（ポイント）")
    ax.set_ylim(-13, 1)
    ax.set_title("分解（年齢6区分）", loc="left", fontsize=11)
    ax.grid(axis="x", visible=False)
    ax = axs[1]
    cols = ["#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", ORANGE]
    bottom = np.zeros(len(comp))
    for a, c in zip(AGES, cols):
        ax.bar(comp.index, comp[a], bottom=bottom, color=c, label=a)
        bottom += comp[a].values
    ax.set_ylabel("非正規の年齢構成（%）")
    ax.set_ylim(0, 100)
    ax.set_xticks(range(2013, 2026, 2))
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=8.5)
    ax.set_title("非正規の年齢構成（65歳以上が10.5%→20.6%）", loc="left", fontsize=11)
    fig.suptitle("低下の9割は各年齢の中の低下で、年齢構成の変化は1割に満たない", x=0.01, ha="left", fontsize=11.5)
    save(fig, "fig3_shiftshare.png")


def fig4():
    q = pd.read_csv(RES / "requestion_reason_mix.csv")
    order = ["都合のよい時間", "家計の補助・学費", "家事・育児等と両立", "通勤時間が短い", "専門的な技能", "正規の仕事がない", "その他"]
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), sharey=True)
    for ax, (s, a, t) in zip(axs, [("男女計", "年齢計", "男女計・年齢計"), ("男", "25〜34歳", "男・25〜34歳")]):
        z = q[(q.sex == s) & (q.age == a)].set_index("reason").loc[order]
        cols = [ORANGE if v < 0 else BLUE for v in z.change_pt]
        ax.barh(range(len(order)), z.change_pt, color=cols)
        for i, v in enumerate(z.change_pt):
            ax.text(v + (0.5 if v >= 0 else -0.5), i, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
        ax.axvline(0, color=GRAY, lw=1)
        ax.set_title(t, loc="left", fontsize=11)
        ax.set_xlabel("理由の割合の変化（2013→2025年、ポイント）")
        lim = max(abs(z.change_pt).max() * 1.35, 5)
        ax.set_xlim(-lim, lim)
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(range(len(order)), order)
    axs[0].invert_yaxis()
    fig.suptitle("代わりに増えた理由は「都合のよい時間に働きたいから」", x=0.01, ha="left", fontsize=11.5)
    save(fig, "fig4_reason_mix_change.png")


fig1()
fig2()
fig3()
fig4()
