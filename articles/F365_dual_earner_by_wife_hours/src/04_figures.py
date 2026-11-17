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
BLUE, ORANGE, GRAY, LIGHT = "#2a78d6", "#eb6834", "#555555", "#9bb7d9"
SRC = "出典：総務省「労働力調査」基本集計 第IV-7表（年平均、2020年国勢調査基準）をもとに作成者が加工して作成"
META = {"Software": None}
PARTS = [("週35時間以上", "妻 週35時間以上", "#08519c"), ("週15～34時間", "妻 週15〜34時間", "#6baed6"),
         ("週1～14時間", "妻 週1〜14時間", "#c6dbef"), ("休業者", "妻 休業（その週に働いていない）", "#d9d9d9")]


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def stacked(ax, t, years, width=0.6):
    bottom = np.zeros(len(years))
    for k, lab, c in PARTS:
        vals = t.loc[years, k].values
        ax.bar(years, vals, bottom=bottom, color=c, width=width, label=lab)
        bottom += vals
    return bottom


def fig1():
    t = pd.read_csv(RES / "dual_vs_housewife_2018_2025.csv", index_col=0)
    ys = list(t.index)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    top = stacked(ax, t, ys)
    for y, v, f in zip(ys, top, t.dual_ft35):
        ax.text(y, v + 15, f"{t.loc[y, 'dual']:.0f}", ha="center", fontsize=8.5)
        ax.text(y, f / 2, f"{f:.0f}", ha="center", va="center", fontsize=8.5, color="white")
    ax.plot(ys, t.housewife, color=ORANGE, lw=2.4, marker="o", ms=5, label="専業主婦世帯")
    for y in [ys[0], ys[-1]]:
        ax.annotate(f"専業主婦 {t.loc[y, 'housewife']:.0f}", (y, t.loc[y, "housewife"]), xytext=(0, 9), textcoords="offset points", ha="center", color=ORANGE, fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    ax.set_ylim(0, 1700)
    ax.set_ylabel("世帯数（万世帯）")
    ax.set_xlabel("年")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=3)
    ax.set_title("共働き世帯1,344万のうち、妻が週35時間以上は556万（2025年）", loc="left", fontsize=11.5)
    ax.grid(axis="x", visible=False)
    save(fig, "fig1_dual_by_wife_hours.png")


def fig2():
    t = pd.read_csv(RES / "dual_vs_housewife_2018_2025.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(t.index, t.ratio_dual_hw, color=BLUE, lw=2.4, marker="o", ms=4, label="共働き全体 ÷ 専業主婦")
    ax.plot(t.index, t.ratio_ft35_hw, color="#08519c", lw=2.0, ls="--", marker="s", ms=4, label="妻が週35時間以上の共働き ÷ 専業主婦")
    ax.axhline(1, color=GRAY, lw=1)
    ax.axhline(2, color=GRAY, lw=1, ls=":")
    for col in ["ratio_dual_hw", "ratio_ft35_hw"]:
        for y in [2018, 2025]:
            ax.annotate(f"{t.loc[y, col]:.2f}", (y, t.loc[y, col]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9)
    ax.set_ylim(0, 3.2)
    ax.set_ylabel("専業主婦世帯に対する倍率（倍）")
    ax.set_xlabel("年")
    ax.legend(loc="upper left", frameon=False)
    ax.set_title("妻が週35時間以上の共働きが専業主婦世帯を上回ったのは2023年から", loc="left", fontsize=11.5)
    save(fig, "fig2_ratio_to_housewife.png")


def fig3():
    t = pd.read_csv(RES / "dual_vs_housewife_2018_2025.csv", index_col=0)
    ch = t.loc[2025] - t.loc[2018]
    items = [("週35時間以上", "共働き：妻 週35時間以上"), ("週15～34時間", "共働き：妻 週15〜34時間"), ("週1～14時間", "共働き：妻 週1〜14時間"),
             ("休業者", "共働き：妻 休業"), ("housewife", "専業主婦世帯")]
    vals = [ch[k] for k, _ in items]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    cols = [BLUE if v >= 0 else ORANGE for v in vals]
    ax.barh(range(len(items)), vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(v + (3 if v >= 0 else -3), i, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=10)
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_yticks(range(len(items)), [lab for _, lab in items])
    ax.invert_yaxis()
    ax.set_xlim(-170, 110)
    ax.set_xlabel("2018→2025年の増減（万世帯）")
    ax.grid(axis="y", visible=False)
    ax.set_title("共働きの増加113万のうち72万は、妻が週35時間以上の世帯", loc="left", fontsize=11.5)
    save(fig, "fig3_change_2018_2025.png")


def fig4():
    a = pd.read_csv(RES / "dual_vs_housewife_2018_2025.csv", index_col=0)
    k = pd.read_csv(RES / "dual_vs_housewife_couple_with_children.csv", index_col=0)
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), sharey=True)
    for ax, t, ttl in [(axs[0], a, "夫婦のいる世帯（全体）"), (axs[1], k, "夫婦と子供から成る世帯")]:
        ys = [2018, 2025]
        stacked(ax, t, ys, width=2.2)
        ax.bar([y + 2.4 for y in ys], t.loc[ys, "housewife"], width=2.2, color=ORANGE, label="専業主婦世帯")
        for y in ys:
            ax.text(y, t.loc[y, "dual"] + 15, f"共働き {t.loc[y, 'dual']:.0f}\n（35時間以上 {t.loc[y, 'share_ft35']:.0f}%）", ha="center", fontsize=8)
            ax.text(y + 2.4, t.loc[y, "housewife"] + 15, f"{t.loc[y, 'housewife']:.0f}", ha="center", fontsize=8.5, color=ORANGE)
        ax.set_xticks([2019.2, 2026.2], ["2018年", "2025年"])
        ax.set_title(ttl, loc="left", fontsize=11)
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, 1650)
    axs[0].set_ylabel("世帯数（万世帯）")
    h, l = axs[0].get_legend_handles_labels()
    axs[1].legend(h, l, loc="upper right", frameon=False, fontsize=8)
    fig.suptitle("子どものいる世帯では、妻が週35時間以上の共働きは37%", x=0.01, ha="left", fontsize=11.5)
    save(fig, "fig4_couples_with_children.png")


fig1()
fig2()
fig3()
fig4()
