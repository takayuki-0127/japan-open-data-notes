"""04_figures.py : 図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
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
BLUE, ORANGE, GRAY, GREEN, LIGHT = "#2a78d6", "#eb6834", "#555555", "#3a9e6f", "#9bb7d9"
SRC = "出典：厚生労働省「労働組合基礎調査」時系列表（各年6月30日現在、雇用者数は総務省「労働力調査」6月分）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=6.8, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    d = pd.read_csv(RES / "density_decomposition_series.csv", index_col=0).loc[2013:]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for col, lab, c, ls in [("employees", "雇用者数", ORANGE, "-"), ("unit_members", "組合員数（単位組合）", BLUE, "-"),
                            ("part_members", "パートの組合員数", GREEN, "--"), ("ft_members", "パート以外の組合員数", "#08519c", "--")]:
        idx = d[col] / d.loc[2013, col] * 100
        ax.plot(idx.index, idx, color=c, lw=2.2, ls=ls, marker="o", ms=3.5, label=lab)
        ax.annotate(f"{idx.loc[2025]:.1f}", (2025, idx.loc[2025]), xytext=(5, 0), textcoords="offset points", va="center", color=c, fontsize=9)
    ax.axhline(100, color=GRAY, lw=1)
    ax.set_xlim(2012.5, 2026.2)
    ax.set_ylabel("2013年 = 100")
    ax.set_xlabel("年（6月30日現在）")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.set_title("組合員は横ばい、雇用者は11%増：組織率の低下は分母の伸びによる", loc="left", fontsize=11.5)
    save(fig, "fig1_members_vs_employees.png")


def fig2():
    d = pd.read_csv(RES / "density_decomposition_series.csv", index_col=0).loc[2013:]
    q = pd.read_csv(RES / "requestion_fixed_part_share.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for col, lab, c, ls in [("ft_density", "パート以外", "#08519c", "-"), ("density_unit", "全体（単位組合員）", BLUE, "-"), ("part_density", "パート", GREEN, "-")]:
        ax.plot(d.index, d[col], color=c, lw=2.2, ls=ls, marker="o", ms=3.5, label=lab)
        for y in [2013, 2025]:
            ax.annotate(f"{d.loc[y, col]:.1f}", (y, d.loc[y, col]), xytext=(0, 7), textcoords="offset points", ha="center", color=c, fontsize=9)
    ax.plot(q.index, q.fixed_part_share_2013, color=GRAY, lw=1.4, ls=":", label="全体（パートの割合を2013年に固定）")
    ax.set_ylim(0, 25)
    ax.set_ylabel("推定組織率（%）")
    ax.set_xlabel("年（6月30日現在）")
    ax.legend(loc="center right", frameon=False, fontsize=9)
    ax.set_title("パート以外の組織率は21.3%→18.6%、パートは6.6%→8.8%", loc="left", fontsize=11.5)
    save(fig, "fig2_density_part_fulltime.png")


def fig3():
    z = pd.read_csv(RES / "members_by_firm_size_2013_2025.csv", index_col=0)
    order = ["5000人以上", "1000〜4999人", "500〜999人", "300〜499人", "100〜299人", "30〜99人", "29人以下", "民営その他", "民営以外"]
    lab = ["5,000人以上", "1,000〜4,999人", "500〜999人", "300〜499人", "100〜299人", "30〜99人", "29人以下", "民営のその他", "国公営"]
    z = z.loc[order]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    cols = [BLUE if v >= 0 else ORANGE for v in z.chg_pct]
    ax.barh(range(len(order)), z.chg_pct, color=cols)
    for i, (v, m) in enumerate(zip(z.chg_pct, z.m2025)):
        ax.text(v + (1 if v >= 0 else -1), i, f"{v:+.1f}%（{m / 1e4:.0f}万人）", va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_yticks(range(len(order)), lab)
    ax.invert_yaxis()
    ax.set_xlim(-60, 45)
    ax.set_xlabel("単位労働組合員数の増減（2013→2025年、%）。かっこは2025年の人数")
    ax.grid(axis="y", visible=False)
    ax.set_title("企業規模別の組合員数：5,000人以上は+18.5%、100〜299人は−17.1%", loc="left", fontsize=11.5)
    save(fig, "fig3_members_by_firm_size.png")


fig1()
fig2()
fig3()
