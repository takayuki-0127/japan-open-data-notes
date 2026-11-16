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
SRC = "出典：厚生労働省「就労条件総合調査」時系列表（調査年は1月1日現在、値は前年1年間）をもとに作成者が加工して作成"
META = {"Software": None}
COLS = {"1000人以上": "#08519c", "300〜999人": "#3182bd", "100〜299人": "#6baed6", "30〜99人": ORANGE}
LAB = {"1000人以上": "1,000人以上", "300〜999人": "300〜999人", "100〜299人": "100〜299人", "30〜99人": "30〜99人"}
SHORT = {"サービス業（他に分類されないもの）": "その他のサービス", "学術研究・専門技術": "学術研究・専門"}


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def marks(ax):
    ax.axvline(2014.5, color="#bbbbbb", lw=1, ls=":")
    ax.text(2014.6, ax.get_ylim()[1] - 1.5, "調査対象の拡大", fontsize=7.5, color="#888888", va="top")
    ax.axvline(2019.5, color=GRAY, lw=1, ls="--")
    ax.text(2019.6, ax.get_ylim()[1] - 1.5, "年5日の取得の義務\n（2019年4月〜）", fontsize=7.5, color=GRAY, va="top")


def fig1():
    r = pd.read_csv(RES / "rate_by_group_year.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(r.index, r["調査産業計"], color=BLUE, lw=2.4, marker="o", ms=4)
    for y in [2009, 2015, 2019, 2025]:
        ax.annotate(f"{r.loc[y, '調査産業計']:.1f}", (y, r.loc[y, "調査産業計"]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9.5, color=BLUE)
    ax.set_ylim(40, 75)
    marks(ax)
    ax.set_ylabel("年休の取得率（%）")
    ax.set_xlabel("調査年（値は前の年の1年間）")
    ax.set_xticks(range(2009, 2026, 2))
    ax.set_title("取得率は52.4%→66.9%（2019→2025年調査）、1年あたりの上がり幅は前の2倍", loc="left", fontsize=11.5)
    save(fig, "fig1_take_rate_total.png")


def fig2():
    r = pd.read_csv(RES / "rate_by_group_year.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for s in ["1000人以上", "300〜999人", "100〜299人", "30〜99人"]:
        ax.plot(r.index, r[s], color=COLS[s], lw=2.2 if s in ("1000人以上", "30〜99人") else 1.4, label=LAB[s])
        dy = {"30〜99人": -7, "100〜299人": 3}.get(s, 0)
        ax.annotate(f"{r.loc[2025, s]:.1f}", (2025, r.loc[2025, s]), xytext=(4, dy), textcoords="offset points", va="center", color=COLS[s], fontsize=9)
    ax.set_ylim(35, 75)
    marks(ax)
    ax.set_xlim(2008.5, 2026.3)
    ax.set_ylabel("年休の取得率（%）")
    ax.set_xlabel("調査年（値は前の年の1年間）")
    ax.set_xticks(range(2009, 2026, 2))
    ax.legend(loc="lower right", frameon=False)
    ax.set_title("規模別：30〜99人は+17.7、1,000人以上は+10.4ポイント（2019→2025年調査）", loc="left", fontsize=11.5)
    save(fig, "fig2_take_rate_by_size.png")


def fig3():
    i = pd.read_csv(RES / "industry_change.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.scatter(i.r2019, i.chg_2019_2025, s=40, color=BLUE, zorder=3)
    for g, row in i.iterrows():
        if g == "医療・福祉":
            continue
        off, ha = {"不動産業": ((-6, 5), "right"), "運輸業": ((5, -12), "left"), "生活関連・娯楽": ((5, -3), "left"),
                   "教育・学習支援": ((-6, -10), "right")}.get(g, ((5, 3), "left"))
        ax.annotate(SHORT.get(g, g), (row.r2019, row.chg_2019_2025), xytext=off, textcoords="offset points", fontsize=8.5, ha=ha)
    b = np.polyfit(i.r2019, i.chg_2019_2025, 1)
    xs = np.linspace(i.r2019.min() - 1, i.r2019.max() + 1, 10)
    ax.plot(xs, b[0] * xs + b[1], color=ORANGE, lw=1.4, ls="--", label=f"直線のあてはめ（傾き {b[0]:.2f}）")
    c = np.corrcoef(i.r2019, i.chg_2019_2025)[0, 1]
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xlabel("2019年調査の取得率（%）")
    ax.set_ylabel("2019→2025年調査の上がり幅（ポイント）")
    ax.legend(loc="upper right", frameon=False, title=f"16産業、相関 {c:.2f}", title_fontsize=9)
    ax.set_title("もともと低かった産業ほど大きく上がった", loc="left", fontsize=11.5)
    save(fig, "fig3_industry_convergence.png")


def fig4():
    dcm = pd.read_csv(RES / "decomposition_2019_2025.csv").set_index("group")
    g = ["調査産業計", "1000人以上", "300〜999人", "100〜299人", "30〜99人"]
    lab = ["全体", "1,000人以上", "300〜999人", "100〜299人", "30〜99人"]
    x = np.arange(len(g))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(x - 0.3, dcm.loc[g, "granted2019"], width=0.2, color="#d9d9d9", label="付与日数 2019年調査")
    ax.bar(x - 0.1, dcm.loc[g, "granted2025"], width=0.2, color="#a6a6a6", label="付与日数 2025年調査")
    ax.bar(x + 0.1, dcm.loc[g, "taken2019"], width=0.2, color=LIGHT, label="取得日数 2019年調査")
    ax.bar(x + 0.3, dcm.loc[g, "taken2025"], width=0.2, color=BLUE, label="取得日数 2025年調査")
    for i, k in enumerate(g):
        ax.text(i + 0.3, dcm.loc[k, "taken2025"] + 0.3, f"{dcm.loc[k, 'taken2025']:.1f}", ha="center", fontsize=8.5, color=BLUE)
        ax.text(i + 0.1, dcm.loc[k, "taken2019"] + 0.3, f"{dcm.loc[k, 'taken2019']:.1f}", ha="center", fontsize=8.5, color="#5b7fae")
    ax.axhline(5, color=ORANGE, lw=1, ls="--")
    ax.text(-0.48, 5.3, "年5日", color=ORANGE, fontsize=8.5, ha="left")
    ax.set_xticks(x, lab)
    ax.set_ylabel("労働者1人平均（日）")
    ax.set_ylim(0, 24)
    ax.legend(loc="upper center", ncol=2, frameon=False, fontsize=8.5)
    ax.grid(axis="x", visible=False)
    ax.set_title("上がったのは取った日数：付与は18日前後のまま、取得は9.4→12.1日", loc="left", fontsize=11.5)
    save(fig, "fig4_days_taken_granted.png")


fig1()
fig2()
fig3()
fig4()
