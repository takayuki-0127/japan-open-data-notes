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

SRC = "出典：厚生労働省「国民生活基礎調査」をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
N = pd.read_csv(RES / "national.csv").set_index("year")
R = pd.read_csv(RES / "region.csv").set_index("region")
RN = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    n = N.loc[1986:]
    s1, s2, s3 = 100 * n.c1 / n.total, 100 * n.c2 / n.total, 100 * (n.c3 + n.c4) / n.total
    ax.bar(n.index, s1, color=C[0], width=0.8, label="児童1人")
    ax.bar(n.index, s2, bottom=s1, color=C[2], width=0.8, label="児童2人")
    ax.bar(n.index, s3, bottom=s1 + s2, color=C[1], width=0.8, label="児童3人以上")
    for y in (1986, 2000, 2013, 2025):
        ax.annotate(f"{n.share[y]:.1f}%", (y, n.share[y]), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    ax.axvline(2023.5, color="#888888", lw=0.8, ls="--")
    ax.text(2023.3, 44, "2024年から児童の定義を\n「18歳未満の未婚の者」→\n「18歳未満の者」に", ha="right", fontsize=8, color="#555555")
    ax.set_ylim(0, 50); ax.set_xlim(1984.5, 2026.5)
    ax.set_ylabel("全世帯に占める割合（%）")
    ax.legend(loc="upper right", fontsize=9, frameon=False, bbox_to_anchor=(1.0, 0.82))
    ax.set_title("児童のいる世帯の割合は1986年46.2%→2025年16.7%。2022年から2割を下回る", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。児童＝18歳未満。2020年は調査なし。1995年は兵庫県を除く")
    save(fig, "fig1_national.png")


def fig2():
    S = M["structure"]
    keys = ["couple_child", "single_parent", "three_gen", "other"]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(len(keys)); w = 0.36
    a = [S[k]["n2013"] / 10 for k in keys]; b = [S[k]["n2025"] / 10 for k in keys]
    ax.bar(x - w / 2, a, width=w, color="#9ecae1", label="2013年")
    ax.bar(x + w / 2, b, width=w, color=C[0], label="2025年")
    for xi, k, v in zip(x, keys, b):
        ax.text(xi + w / 2, v + 10, f"{S[k]['pct']:+.0f}%\n（減少の{S[k]['share_of_change']:.0f}%）" if abs(S[k]["share_of_change"]) >= 1 else f"{S[k]['pct']:+.0f}%", ha="center", fontsize=8.5)
    for xi, v in zip(x, a):
        ax.text(xi - w / 2, v + 10, f"{v:,.0f}万", ha="center", fontsize=8, color="#555555")
    ax.set_xticks(x, [S[k]["label"] + "の世帯" if k != "other" else S[k]["label"] for k in keys], fontsize=9.5)
    ax.set_ylabel("児童のいる世帯（万世帯）")
    ax.set_ylim(0, 1000)
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.grid(axis="x", visible=False)
    ax.set_title("2013→2025年：三世代は56%減り、減少（−291万）の38%を占めた", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "（平成25年・令和7年）")
    save(fig, "fig2_structure.png")


def fig3():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(len(RN)); w = 0.36
    ax.bar(x - w / 2, R.loc[RN, "share2013"], width=w, color="#9ecae1", label="2013年（国民生活基礎調査）")
    ax.bar(x + w / 2, R.loc[RN, "share2025"], width=w, color=C[0], label="2025年（国民生活基礎調査）")
    ax.scatter(x + w / 2, R.loc[RN, "census2025"], marker="D", s=30, color=C[1], zorder=3, label="2025年（国勢調査、18歳未満世帯員のいる一般世帯）")
    for xi, r in zip(x, RN):
        ax.text(xi - w / 2, R.loc[r, "share2013"] + 0.4, f"{R.loc[r,'share2013']:.1f}", ha="center", fontsize=8, color="#555555")
        ax.text(xi + w / 2, max(R.loc[r, "share2025"], R.loc[r, "census2025"]) + 0.6, f"{R.loc[r,'share2025']:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(x, RN)
    ax.set_ylim(0, 34)
    ax.set_ylabel("児童のいる世帯の割合（%）")
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    ax.grid(axis="x", visible=False)
    ax.set_title("8地方とも下がり、地方の差は縮まった。北海道の2025年は国勢調査と差が大きい", loc="left", fontsize=11)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, "出典：厚生労働省「国民生活基礎調査」、総務省「国勢調査」をもとに作成者が加工して作成。地方は北から南の順")
    save(fig, "fig3_region.png")


def fig4():
    n = N.loc[1986:]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(n.index, n.child / 10, color=C[0], lw=2.4, marker="o", ms=3, label="児童のいる世帯")
    ax.plot(n.index, n.nochild / 10, color=C[1], lw=2.4, marker="o", ms=3, label="児童のいない世帯")
    for col in ("child", "nochild"):
        for y in (1986, 2025):
            ax.annotate(f"{n[col][y]/10:,.0f}万", (y, n[col][y] / 10), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9)
    ax.set_ylim(0, 5200)
    ax.set_ylabel("世帯数（万世帯）")
    q = M["requestion"]
    ax.text(2003, 900, f"割合の低下 {q['share2025']-q['share1986']:.1f}ポイントのうち\n・児童のいる世帯の減少による分 約{q['numerator_avg_pt']:.1f}\n・ほかの世帯の増加による分 約{q['denominator_avg_pt']:.1f}\n（2つの順の平均）", fontsize=9, va="top")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.set_title("児童のいる世帯は1,736万→917万（−47%）、いない世帯は2,018万→4,588万", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。2020年は調査なし")
    save(fig, "fig4_counts.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
