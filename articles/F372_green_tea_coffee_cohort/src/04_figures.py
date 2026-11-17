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
BLUE, ORANGE, GRAY, GREEN, LIGHT, BROWN = "#2a78d6", "#eb6834", "#555555", "#3a9e6f", "#9bb7d9", "#8a5a2b"
SRC = "出典：総務省「家計調査」家計収支編 二人以上の世帯 年報（品目別、世帯主の年齢階級別）をもとに作成者が加工して作成"
META = {"Software": None}
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    t = pd.read_csv(ROOT / "data" / "national.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.4))
    ax = axes[0]
    for item, c in [("緑茶", GREEN), ("コーヒー", BROWN)]:
        s = t[t.item == item].set_index("year")["qty_g"] / 1000
        ax.plot(s.index, s.values, color=c, lw=2, marker="o", ms=3, label=item)
        for y in (2000, 2025):
            ax.text(y, s[y] + 0.08, f"{s[y]:.2f}", ha="center", fontsize=8.5, color=c)
    ax.set_title("緑茶（茶葉）とコーヒー（豆・粉など）の購入量", fontsize=10.5)
    ax.set_ylabel("1世帯当たり年間の購入量（kg）")
    ax.set_ylim(0, 3)
    ax.legend(frameon=False, loc="upper left")
    ax = axes[1]
    for item, c in [("緑茶", GREEN), ("茶飲料", LIGHT), ("コーヒー", BROWN), ("コーヒー飲料", ORANGE)]:
        s = t[t.item == item].set_index("year")["amount"] / 1000
        ax.plot(s.index, s.values, color=c, lw=2, marker="o", ms=3, label=item)
    ax.set_title("支出金額（名目）", fontsize=10.5)
    ax.set_ylabel("1世帯当たり年間（千円）")
    ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9)
    ax.set_ylim(0, 12)
    fig.suptitle("緑茶の茶葉は25年で半分に。茶飲料とコーヒーは増えた（二人以上の世帯）", fontsize=12)
    save(fig, "fig1_national_trend.png")


def fig2():
    d = pd.read_csv(ROOT / "data" / "by_age.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.6), sharey=False)
    x = np.arange(len(AGES))
    for ax, item, ymax in [(axes[0], "緑茶", 1.4), (axes[1], "コーヒー", 3.5)]:
        s15 = d[(d.item == item) & (d.year == 2015)].set_index("age").loc[AGES, "qty_g"] / 1000
        s25 = d[(d.item == item) & (d.year == 2025)].set_index("age").loc[AGES, "qty_g"] / 1000
        ax.plot(x, s15.values, color="#aaaaaa", lw=2, marker="o", label="2015年")
        ax.plot(x, s25.values, color=GREEN if item == "緑茶" else BROWN, lw=2, marker="o", label="2025年")
        for i in range(4):
            ax.annotate("", xy=(x[i + 1] - 0.05, s25.values[i + 1]), xytext=(x[i] + 0.05, s15.values[i]),
                        arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.3, alpha=0.85))
        ax.set_xticks(x)
        ax.set_xticklabels([a.replace("歳以下", "歳\n以下").replace("歳以上", "歳\n以上") for a in AGES], fontsize=9)
        ax.set_title(f"{item}（世帯主の年齢別）", fontsize=11)
        ax.set_ylim(0, ymax)
        ax.set_ylabel("1世帯当たり年間の購入量（kg）")
        ax.legend(frameon=False, loc="upper left", fontsize=9)
    axes[0].text(0.0, 1.06, "オレンジの矢印：同じ生まれの世代を10年追った動き", fontsize=8.5, color=ORANGE)
    fig.suptitle("同じ世代を10年追うと、緑茶はほとんど増えない。コーヒーは年齢の差の分だけ増えた", fontsize=12)
    save(fig, "fig2_cohort_arrows.png")


def fig3():
    s = pd.read_csv(RES / "cohort_summary.csv", index_col=0)
    keys = [("緑茶_qty_g", "緑茶（量）"), ("コーヒー_qty_g", "コーヒー（量）"), ("緑茶_amount", "緑茶（金額）")]
    pairs = ["2015_2025", "2014_2024", "2013_2023"]
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 4.4), sharey=True)
    w = 0.26
    cols = {"mean_cross": (LIGHT, "同じ年の10歳上との差"), "mean_cohort": (ORANGE, "同じ世代の10年の変化"),
            "mean_same_age": ("#bbbbbb", "同じ年齢の10年の変化")}
    for ax, (k, lab) in zip(axes, keys):
        for j, (m, (c, nm)) in enumerate(cols.items()):
            v = [s.loc[f"{k}_{p}", m] for p in pairs]
            ax.bar(np.arange(3) + (j - 1) * w, v, w, color=c, label=nm)
            for i, val in enumerate(v):
                ax.text(i + (j - 1) * w, val + (2 if val >= 0 else -6), f"{val:.0f}", ha="center", fontsize=7.5)
        ax.axhline(0, color="#888888", lw=0.8)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["2015→\n2025", "2014→\n2024", "2013→\n2023"], fontsize=9)
        ax.set_title(lab, fontsize=11)
    axes[0].set_ylabel("4つの年齢区間の平均（対数の差 ×100、%に近い）")
    axes[0].set_ylim(-70, 115)
    axes[2].legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.suptitle("緑茶の量：同じ世代の変化（オレンジ）は、10歳上との差（水色）よりずっと小さい", fontsize=12)
    save(fig, "fig3_decomposition.png")


def fig4():
    w = pd.read_csv(RES / "shares_by_age.csv")
    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    x = np.arange(len(AGES))
    for j, (y, c) in enumerate([(2015, "#bbbbbb"), (2025, GREEN)]):
        v = w[w.year == y].set_index("age").loc[AGES, "tea_bev_share"]
        ax.bar(x + (j - 0.5) * 0.38, v.values, 0.38, color=c, label=f"{y}年")
        for i, val in enumerate(v.values):
            ax.text(x[i] + (j - 0.5) * 0.38, val + 1.2, f"{val:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(AGES)
    ax.set_ylim(0, 100)
    ax.set_ylabel("茶飲料の割合（%、緑茶＋茶飲料の金額に対して）")
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("茶にかけるお金のうち茶飲料の割合：どの年齢でも上がり、70歳以上も6割に", fontsize=12)
    save(fig, "fig4_tea_beverage_share.png")


def main():
    fig1()
    fig2()
    fig3()
    fig4()
    print(json.dumps(sorted(p.name for p in FIG.glob("*.png")), ensure_ascii=False))


if __name__ == "__main__":
    main()
