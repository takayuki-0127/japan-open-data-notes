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
SRC = "出典：厚生労働省「就労条件総合調査」（各年1月1日現在、常用労働者30人以上の民営企業）をもとに作成者が加工して作成"
META = {"Software": None}
COLS = {"1000人以上": "#08519c", "300〜999人": "#3182bd", "100〜299人": "#6baed6", "30〜99人": ORANGE, "計": GRAY}
LAB = {"1000人以上": "1,000人以上", "300〜999人": "300〜999人", "100〜299人": "100〜299人", "30〜99人": "30〜99人", "計": "全体（企業の数で平均）"}


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def breaks(ax):
    for x, t in [(2008.5, "区分の変更"), (2023.5, "区分の変更")]:
        ax.axvline(x, color="#bbbbbb", lw=1, ls=":")
        ax.text(x + 0.1, ax.get_ylim()[0] + 1, t, fontsize=7.5, color="#888888", rotation=90, va="bottom")


def fig1():
    t = pd.read_csv(RES / "gap_timeseries.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for s in ["1000人以上", "300〜999人", "100〜299人", "30〜99人", "計"]:
        ax.plot(t.index, t["fm_" + s], color=COLS[s], lw=2.2 if s in ("1000人以上", "30〜99人") else 1.4,
                ls="--" if s == "計" else "-", label=LAB[s])
    for s in ["1000人以上", "30〜99人"]:
        ax.annotate(f"{t.loc[2025, 'fm_' + s]:.1f}", (2025, t.loc[2025, "fm_" + s]), xytext=(4, 0), textcoords="offset points", va="center", color=COLS[s], fontsize=9)
        ax.annotate(f"{t.loc[2001, 'fm_' + s]:.1f}", (2001, t.loc[2001, "fm_" + s]), xytext=(-4, 0), textcoords="offset points", va="center", ha="right", color=COLS[s], fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_xlim(1999.8, 2026.3)
    breaks(ax)
    ax.set_ylabel("完全週休2日制以上の企業の割合（%）")
    ax.set_xlabel("調査年（1月1日現在）")
    ax.legend(loc="lower right", frameon=False, fontsize=9, ncol=2)
    ax.set_title("完全週休2日制以上の企業：30〜99人は28.5%→63.3%、1,000人以上は73.6%→80.0%", loc="left", fontsize=11)
    save(fig, "fig1_share_by_size.png")


def fig2():
    t = pd.read_csv(RES / "gap_timeseries.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(t.index, t.gap_large_small, color=LIGHT, label="1,000人以上 − 30〜99人（完全週休2日制以上）")
    ax.plot(t.index, t.gap_ma3, color=BLUE, lw=2.2, label="同じ差の3年移動平均")
    ax.plot(t.index, t.gap_full, color=ORANGE, lw=1.4, ls="--", marker="o", ms=3, label="完全週休2日制だけで見た差")
    for y in [2001, 2012, 2025]:
        ax.text(y, t.loc[y, "gap_large_small"] + 1, f"{t.loc[y, 'gap_large_small']:.1f}", ha="center", fontsize=9)
    ax.set_ylim(0, 55)
    breaks(ax)
    ax.set_ylabel("規模の差（ポイント）")
    ax.set_xlabel("調査年（1月1日現在）")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.set_title("規模の差は45.1→16.7ポイント。縮んだのは2010〜12年と2022年以降", loc="left", fontsize=11.5)
    save(fig, "fig2_gap_large_small.png")


def fig3():
    d = pd.read_csv(RES / "shares_by_size_year.csv")
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), sharey=True)
    sizes = ["1000人以上", "300〜999人", "100〜299人", "30〜99人"]
    parts = [("w1", "週休1日制・1日半制", "#c44e52"), ("less", "完全週休2日制より少ない", "#f2b880"),
             ("full", "完全週休2日制", BLUE), ("plus", "より多い・週休3日", "#08306b")]
    for ax, y in zip(axs, [2009, 2025]):
        z = d[d.year == y].set_index("size").loc[sizes]
        z["plus"] = z["more"].fillna(0) if y <= 2023 else z["w3any"].fillna(0)
        left = np.zeros(len(sizes))
        for k, lab, c in parts:
            vals = z[k].fillna(0).values
            ax.barh(range(len(sizes)), vals, left=left, color=c, label=lab)
            for i, v in enumerate(vals):
                if v >= 6:
                    ax.text(left[i] + v / 2, i, f"{v:.0f}", ha="center", va="center", fontsize=8.5, color="white")
            left += vals
        ax.set_title(f"{y}年", loc="left", fontsize=11)
        ax.set_xlim(0, 100)
        ax.set_xlabel("企業の割合（%）")
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(range(len(sizes)), [LAB[s] for s in sizes])
    axs[0].invert_yaxis()
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 0.045))
    fig.suptitle("週休制の内訳：30〜99人では「完全週休2日制より休みが少ない制度」が3割残る", x=0.01, ha="left", fontsize=11.5)
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(FIG / "fig3_composition_2009_2025.png", dpi=150, metadata=META)
    plt.close(fig)


def fig4():
    w = pd.read_csv(RES / "requestion_one_day_off.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for s in ["1000人以上", "300〜999人", "100〜299人", "30〜99人"]:
        ax.plot(w.index, w[s], color=COLS[s], lw=2.2 if s in ("1000人以上", "30〜99人") else 1.4, label=LAB[s])
    ax.set_ylim(0, 16)
    ax.set_ylabel("週休1日制・1日半制の企業の割合（%）")
    ax.set_xlabel("調査年（1月1日現在）")
    ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=2)
    ax.set_title("週休1日制・1日半制の企業：30〜99人は7〜12%で上下し、2025年は6.7%", loc="left", fontsize=11.5)
    save(fig, "fig4_one_day_off.png")


fig1()
fig2()
fig3()
fig4()
