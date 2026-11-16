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
main = json.loads((RES / "main.json").read_text(encoding="utf-8"))
WORK = ["20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40〜44歳", "45〜49歳", "50〜54歳", "55〜59歳", "60〜64歳"]


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=6.5, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    cv = pd.read_csv(RES / "curves_index.csv")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for y, c, lw in [(2006, LIGHT, 2), (2015, GRAY, 1.6), (2025, BLUE, 2.4)]:
        d = cv[(cv.sex == "男") & (cv.year == y)].set_index("age").loc[WORK]
        ax.plot(range(len(WORK)), d.index_20_24, color=c, lw=lw, marker="o", ms=4, label=f"{y}年")
        k = int(np.argmax(d.index_20_24.values))
        ax.annotate(f"{d.index_20_24.iloc[k]:.1f}", (k, d.index_20_24.iloc[k]), xytext=(0, -16 if y == 2006 else 7), textcoords="offset points",
                    ha="center", color=c, fontsize=9.5)
    ax.set_xticks(range(len(WORK)), WORK, rotation=30)
    ax.set_ylabel("20〜24歳 = 100")
    ax.set_title("男の年齢別の所定内給与（20〜24歳=100）：山の高さは206から181に", loc="left", fontsize=11.5)
    ax.legend(loc="upper left", frameon=False)
    save(fig, "fig1_male_wage_curve.png")


def fig2():
    a = pd.read_csv(RES / "growth_by_age.csv")
    a = a[a.sex == "男"].set_index("age").loc[WORK]
    x = np.arange(len(WORK))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(x - 0.2, a.g_2006_2019, width=0.4, color=LIGHT, label="2006→2019年")
    ax.bar(x + 0.2, a.g_2019_2025, width=0.4, color=BLUE, label="2019→2025年")
    ax.plot(x, a.g_2006_2025, color=ORANGE, marker="D", ms=5, lw=0, label="2006→2025年（通し）")
    for i, v in enumerate(a.g_2006_2025):
        ax.text(i, max(v, a.g_2019_2025.iloc[i]) + 1.2, f"{v:.1f}", ha="center", color=ORANGE, fontsize=9)
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xticks(x, WORK, rotation=30)
    ax.set_ylabel("所定内給与の伸び（%）")
    ax.set_title("男の年齢別の伸び：20代は約2割、40〜54歳は5%以下（2006→2025年）", loc="left", fontsize=11.5)
    ax.legend(loc="upper center", frameon=False, ncol=3)
    ax.grid(axis="x", visible=False)
    save(fig, "fig2_male_growth_by_age.png")


def fig3():
    t = pd.read_csv(RES / "ratio_timeseries.csv", index_col=0)
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), sharey=True)
    ax = axs[0]
    for col, lab, c, ls in [("male_50_54_over_20_24", "学歴計", BLUE, "-"), ("male_univ", "大学・大学院卒", GREEN, "-"),
                            ("male_high", "高校卒", ORANGE, "-"), ("male_fixed_edu2006", "学歴計（学歴構成を2006年に固定）", GRAY, "--")]:
        ax.plot(t.index, t[col], color=c, lw=2 if ls == "-" else 1.4, ls=ls, label=lab)
    ax.set_title("学歴別", loc="left", fontsize=11)
    ax.set_ylabel("50〜54歳 ÷ 20〜24歳（倍）")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    ax = axs[1]
    for col, lab, c in [("male_1000", "1,000人以上", BLUE), ("male_100_999", "100〜999人", GREEN), ("male_10_99", "10〜99人", ORANGE)]:
        ax.plot(t.index, t[col], color=c, lw=2, label=lab)
        ax.annotate(f"{t[col].iloc[-1]:.2f}", (t.index[-1], t[col].iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", color=c, fontsize=9)
    ax.set_title("企業規模別", loc="left", fontsize=11)
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    for ax in axs:
        ax.set_xticks(range(2006, 2026, 4))
    fig.suptitle("男の50〜54歳÷20〜24歳：学歴の中でも下がり、大企業ほど大きく下がった", x=0.01, ha="left", fontsize=11.5)
    save(fig, "fig3_ratio_by_edu_size.png")


def fig4():
    c = pd.read_csv(RES / "cohort_growth_male.csv")
    c = c[c.end_year - c.start_year == 10]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    cols = [BLUE, GREEN, ORANGE, GRAY, "#a05cc8"]
    for a, col in zip(["20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40〜44歳"], cols):
        d = c[c.start_age == a]
        ax.plot(d.start_year, d.growth_pct, color=col, lw=2, marker="o", ms=3.5, label=f"{a} → 10年後")
    ax.set_xlabel("出発の年（10年後の年 = 出発の年 + 10）")
    ax.set_ylabel("同じ世代の10年間の伸び（%）")
    ax.set_xticks(range(2006, 2016))
    ax.set_title("同じ世代を10年追うと、あとから出発した世代ほど伸びは大きい（男）", loc="left", fontsize=11.5)
    ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=2)
    save(fig, "fig4_cohort_10yr_growth.png")


fig1()
fig2()
fig3()
fig4()
