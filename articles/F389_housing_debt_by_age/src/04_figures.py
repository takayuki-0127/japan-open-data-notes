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

SRC = "出典：総務省「家計調査（貯蓄・負債編）」二人以上の世帯 第8-5表・第8-24表（2008〜2025年）をもとに作成者が加工して作成"
w = pd.read_csv(RES / "panel_wide.csv")
w = w[w.household == "two_plus"]
AG = ["30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳〜"]


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for i, a in enumerate(AG):
        s = w[w.age == a]
        ax.plot(s.year, s.D, color=C[i], lw=2.2, marker="o", ms=3, label=a)
        ax.annotate(f"{a} {s.D.iloc[-1]:,.0f}", (s.year.iloc[-1], s.D.iloc[-1]), xytext=(5, 0),
                    textcoords="offset points", va="center", fontsize=9, color=C[i])
    s = w[w.age == "〜29歳"]
    ax.plot(s.year, s.D, color="#999999", lw=1.2, ls="--", label="〜29歳（参考、集計世帯数27〜69）")
    ax.set_xlim(2007.5, 2028.3)
    ax.set_xticks(range(2008, 2026, 2))
    ax.set_ylabel("負債を持つ世帯1世帯あたり（万円）")
    ax.set_title("住宅・土地のための負債（負債を持つ世帯）：30代は2008年の2倍に", loc="left", fontsize=12)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC)
    save(fig, "fig1_debt_per_holder.png")


def fig2():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for i, a in enumerate(AG):
        s = w[w.age == a]
        ax.plot(s.year, s.p, color=C[i], lw=2.2, marker="o", ms=3)
        dy = {"30〜39歳": -7, "40〜49歳": 7}.get(a, 0)
        ax.annotate(f"{a} {s.p.iloc[-1]:.1f}%", (s.year.iloc[-1], s.p.iloc[-1]), xytext=(5, dy),
                    textcoords="offset points", va="center", fontsize=9, color=C[i])
    ax.set_xlim(2007.5, 2028.3)
    ax.set_xticks(range(2008, 2026, 2))
    ax.set_ylim(0, 80)
    ax.set_ylabel("負債を持つ世帯の割合（%）")
    ax.set_title("負債を持つ世帯の割合：30代は56%→67%、60代はほぼ横ばい", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC + "。割合は負債保有世帯の調整集計世帯数÷全世帯")
    save(fig, "fig2_holding_share.png")


def fig3():
    d = pd.read_csv(RES / "decomposition_main.csv")
    d = d[d.age.isin(["30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳〜"])]
    x = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(x - 0.2, d.dlogP, 0.4, color=C[1], label="負債を持つ世帯の割合の変化")
    ax.bar(x + 0.2, d.dlogD, 0.4, color=C[0], label="1世帯あたりの額の変化")
    for xi, (p_, d_, m_) in enumerate(zip(d.dlogP, d.dlogD, d.dlogM)):
        ax.text(xi - 0.2, p_ + (2 if p_ >= 0 else -6), f"{p_:+.0f}", ha="center", fontsize=9)
        ax.text(xi + 0.2, d_ + (2 if d_ >= 0 else -6), f"{d_:+.0f}", ha="center", fontsize=9)
        ax.text(xi, -52, f"平均の変化\n{m_:+.0f}", ha="center", fontsize=8.5, color=GRAY)
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_xticks(x, d.age)
    ax.set_ylim(-60, 80)
    ax.set_ylabel("2008〜10年平均→2023〜25年平均の変化（対数差×100）")
    ax.set_title("30〜50代の平均の伸びは、主に1世帯あたりの額の伸び", loc="left", fontsize=12)
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC + "。2つの棒の和＝全世帯の平均の変化")
    save(fig, "fig3_decomposition.png")


def fig4():
    s = w[w.age == "30〜39歳"]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(s.year, s.H_debt, color=C[1], lw=2.2, marker="o", ms=3, label="負債（全体）")
    ax.plot(s.year, s.H_savings, color=C[2], lw=2.2, marker="o", ms=3, label="貯蓄")
    ax2 = ax.twinx()
    ax2.plot(s.year, s.H_savings / s.H_debt * 100, color=GRAY, lw=1.2, ls="--", label="貯蓄÷負債（右目盛り）")
    ax2.set_ylim(0, 60)
    ax2.set_ylabel("貯蓄÷負債（%）")
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax.set_ylim(0, 3200)
    ax.set_xticks(range(2008, 2026, 2))
    ax.set_ylabel("負債を持つ30代の世帯1世帯あたり（万円）")
    ax.set_title("負債を持つ30代の世帯：負債も貯蓄も約1.9倍、貯蓄÷負債は3割台のまま", loc="left", fontsize=12)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, frameon=False)
    fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.12)
    source(fig, SRC)
    save(fig, "fig4_savings_vs_debt_30s.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
