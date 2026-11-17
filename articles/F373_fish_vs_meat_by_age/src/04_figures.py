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
BLUE, ORANGE, GRAY, GREEN, LIGHT, RED = "#2a78d6", "#eb6834", "#555555", "#3a9e6f", "#9bb7d9", "#c8453b"
SRC = "出典：総務省「家計調査」家計収支編 二人以上の世帯 年報（品目別、世帯主の年齢階級別）をもとに作成者が加工して作成"
META = {"Software": None}
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]
ACOL = ["#9bb7d9", "#5f95d6", "#2a78d6", "#1b4f8f", "#eb6834", "#c8453b"]


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    r = pd.read_csv(RES / "national_ratio.csv")
    a = r[(r.farm_households == "除く") & (r.year < 2000)]
    b = r[r.farm_households == "含む"]
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.5))
    ax = axes[0]
    for s, ls in [(a, "--"), (b, "-")]:
        ax.plot(s.year, s.fish_amt / 1000, color=BLUE, lw=2, ls=ls, label="生鮮魚介" if ls == "-" else None)
        ax.plot(s.year, s.meat_amt / 1000, color=RED, lw=2, ls=ls, label="生鮮肉" if ls == "-" else None)
    ax.set_ylabel("1世帯当たり年間の支出（千円、名目）")
    ax.set_title("支出金額", fontsize=11)
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="lower left")
    ax.text(1991, 92, "破線：1999年以前（農林漁家世帯を除く）", fontsize=8, color=GRAY)
    ax = axes[1]
    for s, ls in [(a, "--"), (b, "-")]:
        ax.plot(s.year, s.amt_ratio, color=ORANGE, lw=2, ls=ls, label="金額" if ls == "-" else None)
        ax.plot(s.year, s.qty_ratio, color=GREEN, lw=2, ls=ls, label="量（g）" if ls == "-" else None)
    ax.axhline(1, color="#888888", lw=1)
    for y, col, k in [(2004, ORANGE, "amt_ratio"), (2006, GREEN, "qty_ratio")]:
        v = float(b[b.year == y][k].iloc[0])
        ax.annotate(f"{y}年に逆転", xy=(y, v), xytext=(y - 11, v + 0.45 if k == "amt_ratio" else v + 0.85),
                    fontsize=9, color=col, arrowprops=dict(arrowstyle="->", color=col, lw=1))
    ax.set_title("生鮮肉 ÷ 生鮮魚介（1より上なら肉が多い）", fontsize=11)
    ax.set_ylim(0, 3.2)
    ax.legend(frameon=False, loc="upper left")
    fig.suptitle("全国では、金額で2004年、量で2006年に肉が魚を上回った（二人以上の世帯）", fontsize=12)
    save(fig, "fig1_national_cross.png")


def fig2():
    ar = pd.read_csv(RES / "ratio_by_age.csv")
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ys = []
    for a, c in zip(AGES, ACOL):
        s = ar[ar.age == a]
        ax.plot(s.year, s.amt_ratio, color=c, lw=2, marker="o", ms=3.5)
        ys.append(float(s.amt_ratio.iloc[-1]))
    # 右端のラベルが重ならないよう、上から順に最小の間隔をあける
    order = np.argsort(ys)[::-1]
    pos = {}
    last = None
    for i in order:
        y = ys[i] if last is None else min(ys[i], last - 0.16)
        pos[i] = y
        last = y
    for i, (a, c) in enumerate(zip(AGES, ACOL)):
        ax.text(2025.3, pos[i], f"{a}（{ys[i]:.2f}）", fontsize=8.5, color=c, va="center")
    ax.axhline(1, color="#888888", lw=1)
    ax.set_xlim(2012.5, 2027.8)
    ax.set_xticks(range(2013, 2026, 2))
    ax.set_ylim(0, 4.4)
    ax.set_ylabel("生鮮肉 ÷ 生鮮魚介（金額）")
    ax.set_title("年齢が高いほど魚寄り。70歳以上も2014年に肉が上回った", fontsize=12)
    save(fig, "fig2_ratio_by_age.png")


def fig3():
    ch = pd.read_csv(RES / "change_2013_2025.csv").set_index("age").loc[AGES]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    x = np.arange(len(AGES))
    ax.bar(x - 0.19, ch.fish_qty_pct, 0.38, color=BLUE, label="生鮮魚介（量）")
    ax.bar(x + 0.19, ch.meat_qty_pct, 0.38, color=RED, label="生鮮肉（量）")
    for i, (f, m) in enumerate(zip(ch.fish_qty_pct, ch.meat_qty_pct)):
        ax.text(i - 0.19, f - 4, f"{f:.0f}", ha="center", fontsize=8.5)
        ax.text(i + 0.19, m + 1.5, f"{m:+.0f}", ha="center", fontsize=8.5)
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(AGES)
    ax.set_ylim(-62, 35)
    ax.set_ylabel("2013→2025年の変化（%）")
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("差が開いたのは、主に魚の量が減ったから（どの年齢でも3〜5割減）", fontsize=12)
    save(fig, "fig3_fish_meat_change.png")


def fig4():
    c = pd.read_csv(RES / "cohort_ratio_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.4), sharey=True)
    w = 0.26
    cols = [("cross_gap", LIGHT, "同じ年の10歳上との差"), ("cohort_10y", ORANGE, "同じ世代の10年の変化"),
            ("same_age", "#bbbbbb", "同じ年齢の10年の変化")]
    for ax, var, ttl in [(axes[0], "amt_ratio", "肉÷魚（金額）"), (axes[1], "qty_ratio", "肉÷魚（量）")]:
        s = c[c["var"] == var].set_index("t0").loc[[2015, 2014, 2013]]
        for j, (k, col, nm) in enumerate(cols):
            ax.bar(np.arange(3) + (j - 1) * w, s[k], w, color=col, label=nm)
            for i, v in enumerate(s[k]):
                ax.text(i + (j - 1) * w, v + (2 if v >= 0 else -6), f"{v:.0f}", ha="center", fontsize=7.5)
        ax.axhline(0, color="#888888", lw=0.8)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["2015→\n2025", "2014→\n2024", "2013→\n2023"], fontsize=9)
        ax.set_title(ttl, fontsize=11)
    axes[0].set_ylabel("4つの年齢区間の平均（対数の差 ×100）")
    axes[0].set_ylim(-40, 80)
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("同じ世代を10年追うと、肉÷魚は上がった（年を取っても魚に寄っていない）", fontsize=12)
    save(fig, "fig4_cohort_ratio.png")


def main():
    fig1()
    fig2()
    fig3()
    fig4()
    print(json.dumps(sorted(p.name for p in FIG.glob("*.png")), ensure_ascii=False))


if __name__ == "__main__":
    main()
