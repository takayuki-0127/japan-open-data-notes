"""04_figures.py : 図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
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
BLUE, ORANGE, GRAY, GREEN = "#2a78d6", "#eb6834", "#555555", "#3a9e6f"
SRC = "出典：厚生労働省「賃金構造基本統計調査」（2006〜2019年は令和2年と同じ推計方法による参考集計）をもとに作成者が加工して作成"
SRC_OLD = "出典：厚生労働省「賃金構造基本統計調査」時系列（〜令和元年）・新規学卒者の表をもとに作成者が加工して作成"
META = {"Software": None}
main = json.loads((RES / "main.json").read_text(encoding="utf-8"))
s = pd.read_csv(RES / "series_yoy.csv", index_col=0)


def save(fig, name, src=SRC):
    fig.text(0.01, 0.012, src, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    d = s.loc[2007:2025]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(d.index, d.ng_univ_yoy, color=BLUE, lw=2.2, marker="o", ms=4, label="新卒・大学")
    ax.plot(d.index, d.ng_high_yoy, color=GREEN, lw=1.6, marker="o", ms=3, label="新卒・高校")
    ax.plot(d.index, d.gen_all_yoy, color=ORANGE, lw=2.2, marker="s", ms=4, label="一般労働者 全体（年齢計）")
    ax.axhline(0, color=GRAY, lw=1)
    for col, c in [("ng_univ_yoy", BLUE), ("gen_all_yoy", ORANGE)]:
        ax.annotate(f"{d.loc[2025, col]:.1f}%", (2025, d.loc[2025, col]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=c, fontsize=10)
    ax.annotate(f"2008年：差 {d.loc[2008, 'gap_univ_all_yoy']:.1f}ポイント\n（全体は前年より下がった）", (2008, d.loc[2008, "ng_univ_yoy"]),
                xytext=(2013.6, -2.6), fontsize=8.5, color=GRAY, arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.8))
    ax.set_title("所定内給与の前年比：2025年の大学新卒5.6%は2007年以降で最大、全体は3.1%", loc="left", fontsize=11.5)
    ax.set_ylabel("前年比（%）")
    ax.set_xlabel("年（各年6月分）")
    ax.set_xlim(2006.5, 2026.3)
    ax.set_xticks(range(2007, 2026, 2))
    ax.legend(loc="upper left", frameon=False)
    save(fig, "fig1_yoy_newgrad_vs_all.png")


def fig2():
    c = pd.read_csv(RES / "cum_2019_2025.csv")
    order = ["新卒 大学", "新卒 高校", "一般労働者 20〜24歳", "一般労働者 25〜29歳", "一般労働者 30〜34歳",
             "一般労働者 35〜39歳", "一般労働者 40〜44歳", "一般労働者 45〜49歳", "一般労働者 50〜54歳",
             "一般労働者 55〜59歳", "一般労働者 年齢計"]
    c = c.set_index("group").loc[order]
    labels = [g.replace("一般労働者 ", "").replace("新卒 ", "新卒・") for g in order]
    labels[-1] = "全体（年齢計）"
    colors = [BLUE, BLUE] + ["#9bb7d9"] * 8 + [ORANGE]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(range(len(order)), c.growth_pct, color=colors)
    for i, v in enumerate(c.growth_pct):
        ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(range(len(order)), labels, rotation=35, ha="right")
    ax.set_ylabel("2019年→2025年の伸び（%）")
    ax.set_title("2019→2025年の所定内給与の伸び：若いほど大きく、50〜54歳は5.2%", loc="left", fontsize=11.5)
    ax.grid(axis="x", visible=False)
    save(fig, "fig2_cum_growth_by_age.png")


def fig3():
    o = pd.read_csv(RES / "old_series_univ_male.csv", index_col=0).loc[1977:2019]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(o.index, o.yoy_calc, color="#9bb7d9", label="大卒・男の初任給（旧推計方法、1977〜2019年）")
    nm = s.loc[2020:2025]
    # 新方式の男の大学（参考に重ねる）
    ng = pd.read_csv(ROOT / "data" / "newgrad.csv")
    m = ng[(ng.edu == "大学") & (ng.sex == "男") & (ng["size"] == "企業規模計")].set_index("year")["wage"].sort_index()
    my = (m / m.shift(1) - 1) * 100
    ax.bar(my.loc[2020:2025].index, my.loc[2020:2025], color=BLUE, label="大学・男の新卒（新しい推計方法、2020〜2025年）")
    thr = main["H4_old"]["threshold"]
    ax.axhline(thr, color=ORANGE, lw=1.2, ls="--")
    ax.text(1990, thr + 0.25, f"2025年の大学新卒（男女計）の伸び {thr:.1f}%", color=ORANGE, fontsize=9)
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_title("大卒の初任給の前年比：5.6%を超えたのは1977年（7.1%）だけ。1990・91年は5.6%弱", loc="left", fontsize=11.5)
    ax.set_ylabel("前年比（%）")
    ax.set_xlabel("年")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    del nm
    save(fig, "fig3_long_run_starting_pay.png", SRC_OLD)


def fig4():
    q = pd.read_csv(RES / "requestion_newgrad_vs_25_29.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(q.index, q.univ_new_over_25_29_all * 100, color=BLUE, lw=2.2, marker="o", ms=4,
            label="大学新卒 ÷ 25〜29歳（学歴計）")
    u = q.loc[2020:2025, "univ_new_over_25_29_univ"] * 100
    ax.plot(u.index, u, color=GREEN, lw=1.8, marker="o", ms=3.5, label="大学新卒 ÷ 25〜29歳の大学卒（2020年〜）")
    ax.plot(q.index, q.high_new_over_20_24_all * 100, color=GRAY, lw=1.4, ls="--", label="高校新卒 ÷ 20〜24歳（学歴計）")
    for col, c in [("univ_new_over_25_29_all", BLUE)]:
        ax.annotate(f"{q.loc[2025, col] * 100:.1f}", (2025, q.loc[2025, col] * 100), xytext=(6, 0),
                    textcoords="offset points", va="center", color=c)
    ax.set_title("新卒と少し上の世代の差は縮まった：大学新卒は25〜29歳の93.9%に", loc="left", fontsize=11.5)
    ax.set_ylabel("新卒の給与 ÷ 比べる年齢の給与（%）")
    ax.set_xlabel("年（各年6月分）")
    ax.set_xticks(range(2006, 2026, 2))
    ax.set_ylim(81, 98.5)
    ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=2)
    save(fig, "fig4_newgrad_vs_late20s.png")


fig1()
fig2()
fig3()
fig4()
