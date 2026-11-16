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

SRC = "出典：総務省「住民基本台帳に基づく人口、人口動態及び世帯数調査」をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
Y = pd.read_csv(RES / "yearly.csv").set_index("year")
P = pd.read_csv(RES / "muni_2021_2025.csv", dtype={"code": str})
RQ = pd.read_csv(RES / "requestion.csv").set_index("year")
SIZE_LAB = ["5千人未満", "5千〜1万", "1万〜3万", "3万〜10万", "10万〜30万", "30万人以上"]


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = Y.index.values
    ax.bar(x - 0.2, Y.nat_total / 1e4, width=0.4, color=C[1], label="自然増減（出生−死亡）")
    ax.bar(x + 0.2, Y.soc_total / 1e4, width=0.4, color=C[0], label="社会増減（転入−転出など）")
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_ylabel("全国の合計（万人）")
    ax.set_ylim(-100, 60)
    ax2 = ax.twinx()
    ax2.plot(x, Y.nat_dom_share, color="#222222", lw=2, marker="o", ms=4, label="人口が減った市区町村のうち、自然減のほうが大きい割合（%、右）")
    for yy in (2014, 2025):
        ax2.annotate(f"{Y.nat_dom_share[yy]:.1f}%", (yy, Y.nat_dom_share[yy]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9)
    ax2.set_ylim(0, 160); ax2.set_yticks([0, 20, 40, 60, 80, 100])
    ax2.set_ylabel("割合（%）"); ax2.grid(False); ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=8.5, frameon=False)
    ax.set_xticks(x, [str(v) for v in x], fontsize=9)
    ax.set_title("人口が減った市区町村で「自然減のほうが大きい」割合は、2014年71%→2025年94%", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.92, top=0.9, bottom=0.1)
    source(fig, SRC + "。各年1〜12月、日本人住民と外国人住民の計")
    save(fig, "fig1_yearly.png")


def fig2():
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    nr = 100 * P.natural / P.pop0; sr = 100 * P.social / P.pop0
    dec = P.change < 0
    ax.scatter(nr[~dec], sr[~dec], s=8, color="#bbbbbb", label=f"人口が増えた（{(~dec).sum()}）")
    nd = dec & (-P.natural > -P.social)
    ax.scatter(nr[nd], sr[nd], s=8, color=C[1], alpha=0.7, label=f"減った：自然減のほうが大きい（{nd.sum()}）")
    ax.scatter(nr[dec & ~nd], sr[dec & ~nd], s=14, color=C[0], label=f"減った：社会減のほうが大きい（{(dec & ~nd).sum()}）")
    t = np.linspace(-16, 0, 10)
    ax.plot(t, t, color="#555555", lw=0.8, ls="--")
    ax.text(-15.5, -13.2, "自然減＝社会減", fontsize=8.5, color="#555555")
    ax.axhline(0, color="#888888", lw=0.8); ax.axvline(0, color="#888888", lw=0.8)
    xl, yl = (-20, 4), (-16, 20)
    ax.set_xlim(*xl); ax.set_ylim(*yl)
    outside = int(((nr < xl[0]) | (nr > xl[1]) | (sr < yl[0]) | (sr > yl[1])).sum())
    ax.set_xlabel("自然増減（5年の合計、期首人口に対する%）")
    ax.set_ylabel("社会増減（5年の合計、期首人口に対する%）")
    ax.legend(loc="upper left", fontsize=8.5, frameon=False, markerscale=2)
    ax.set_title("2021〜2025年：人口が減った1,558市区町村の96.5%は、自然減のほうが大きい", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.11)
    source(fig, SRC + f"。点は1,741市区町村（政令市は市全体）。範囲外の{outside}点は省略")
    save(fig, "fig2_scatter.png")


def fig3():
    d = P[P.change < 0].copy()
    d["cat"] = np.select([(d.natural < 0) & (d.social < 0) & (d.natural < d.social), (d.natural < 0) & (d.social >= 0),
                          (d.natural < 0) & (d.social < 0) & (d.natural >= d.social)], ["a", "b", "c"], "d")
    tab = pd.crosstab(d["size"], d.cat, normalize="index").reindex(SIZE_LAB).fillna(0) * 100
    cats = [("b", "自然減・社会増", C[3]), ("a", "自然減・社会減（自然減のほうが大）", C[1]), ("c", "自然減・社会減（社会減のほうが大）", C[0]), ("d", "自然増・社会減", "#999999")]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    y = np.arange(len(SIZE_LAB))[::-1]; left = np.zeros(len(SIZE_LAB))
    for k, lab, c in cats:
        v = tab[k].values if k in tab else np.zeros(len(SIZE_LAB))
        ax.barh(y, v, left=left, color=c, height=0.6, label=lab)
        for yi, l, vi in zip(y, left, v):
            if vi >= 6:
                ax.text(l + vi / 2, yi, f"{vi:.0f}%", ha="center", va="center", color="white", fontsize=8.5)
        left += v
    n = d.groupby("size", observed=False).size().reindex(SIZE_LAB)
    ax.set_yticks(y, [f"{s}（{k}）" for s, k in zip(SIZE_LAB, n)])
    ax.set_xlim(0, 100); ax.set_xlabel("人口が減った市区町村の内訳（%）")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8.5, frameon=False)
    ax.grid(axis="y", visible=False)
    ax.set_title("規模が大きいほど「自然減・社会増」が多く、社会減のほうが大きいのは小さな町村に少し", loc="left", fontsize=11)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.91, bottom=0.25)
    source(fig, SRC + "。2021〜2025年の5年合計、期首人口の規模別（かっこ内は数）")
    save(fig, "fig3_by_size.png")


def fig4():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = RQ.index.values
    ax.plot(x, RQ.nat_dec_soc_inc, color=C[3], lw=2.2, marker="o", ms=4, label="自然減だが社会増の市区町村")
    ax.plot(x, RQ.nat_dec_soc_inc_pop_inc, color=C[2], lw=2.2, marker="o", ms=4, label="そのうち人口も増えた（社会増が自然減を上回った）")
    ax.plot(x, RQ.increase, color="#999999", lw=1.6, ls="--", marker="o", ms=3, label="人口が増えた市区町村（すべて）")
    for col, dy in (("nat_dec_soc_inc", 7), ("nat_dec_soc_inc_pop_inc", -15)):
        for yy in (2014, 2025):
            ax.annotate(f"{RQ[col][yy]}", (yy, RQ[col][yy]), xytext=(0, dy), textcoords="offset points", ha="center", fontsize=9)
    ax.set_ylim(0, 800)
    ax.set_xticks(x, [str(v) for v in x], fontsize=9)
    ax.set_ylabel("市区町村の数（1,741のうち）")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.set_title("自然減だが社会増の市区町村は267（2014年）→652（2025年）に", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。各年1〜12月")
    save(fig, "fig4_requestion.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
