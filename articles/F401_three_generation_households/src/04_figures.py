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

SRC = "出典：総務省「国勢調査」（e-Stat）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
RN = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
W = pd.read_csv(RES / "region_share.csv").set_index("region")
TN = pd.read_csv(RES / "region_typeshare_new.csv").set_index("region")
TO = pd.read_csv(RES / "region_typeshare_old.csv").set_index("region")
PW = pd.read_csv(RES / "pref_share.csv").set_index("pref")
RQ = pd.read_csv(RES / "requestion_elderly.csv").set_index("region")


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    yo = [int(c) for c in TO.columns]; yn = [int(c) for c in TN.columns]
    ax.plot(yo, TO.loc["全国"], color="#999999", lw=1.8, ls="--", marker="o", ms=4, label="親・夫婦・子の型（旧分類）")
    ax.plot(yn, TN.loc["全国"], color=C[1], lw=2.2, marker="o", ms=4, label="親・夫婦・子の型（新分類）")
    y3 = [int(c) for c in W.columns]
    ax.plot(y3, W.loc["全国"], color=C[0], lw=2.6, marker="o", ms=5, label="3世代世帯（直系3世代以上が同居）")
    for y, v in zip(y3, W.loc["全国"]):
        ax.annotate(f"{v:.1f}%", (y, v), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9, color=C[0])
    for y in (1980, 2025):
        v = TO.loc["全国", str(y)] if y == 1980 else TN.loc["全国", str(y)]
        ax.annotate(f"{v:.1f}%", (y, v), xytext=(0, -15), textcoords="offset points", ha="center", fontsize=9, color="#555555" if y == 1980 else C[1])
    ax.set_xlim(1977, 2028); ax.set_ylim(0, 17)
    ax.set_ylabel("一般世帯に占める割合（%）")
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.set_title("3世代世帯の割合は2010年7.1%→2025年2.9%。目安の型は1980年から下がり続けた", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。親・夫婦・子の型＝夫婦，子供と両親／ひとり親／親と他の親族から成る世帯")
    save(fig, "fig1_national.png")


def fig2():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(len(RN)); w = 0.2
    cols = ["#c6dbef", "#6baed6", "#2171b5", "#08306b"]
    for k, (y, c) in enumerate(zip(["2010", "2015", "2020", "2025"], cols)):
        ax.bar(x + (k - 1.5) * w, W.loc[RN, y], width=w, color=c, label=f"{y}年")
    for xi, r in zip(x, RN):
        ax.text(xi + 1.5 * w, W.loc[r, "2025"] + 0.25, f"{W.loc[r,'2025']:.1f}", ha="center", fontsize=8.5)
        ax.text(xi - 1.5 * w, W.loc[r, "2010"] + 0.25, f"{W.loc[r,'2010']:.1f}", ha="center", fontsize=8.5, color="#555555")
    ax.set_xticks(x, RN)
    ax.set_ylim(0, 17)
    ax.set_ylabel("3世代世帯の割合（%）")
    ax.legend(loc="upper right", fontsize=9, frameon=False, ncol=4)
    ax.grid(axis="x", visible=False)
    ax.set_title("8地方すべてで5年ごとに下がった。2025年も東北（6.5%）と中部（4.8%）に多い", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。地方は北から南の順。2025年は原数値")
    save(fig, "fig2_region.png")


C8 = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#bcbd22", "#7f7f7f", "#e377c2", "#17becf"]


def fig3():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for k, r in enumerate(RN):
        d = PW[PW.region == r]
        ax.scatter(d["2010"], 100 * (d["2025"] / d["2010"] - 1), s=36, color=C8[k], label=r, alpha=0.9, edgecolor="white", lw=0.5)
    ax.set_xlabel("2010年の3世代世帯の割合（%、都道府県）")
    ax.set_ylabel("2010→2025年の割合の変化率（%）")
    ax.set_ylim(-68, -48); ax.set_xlim(0, 23)
    ax.legend(loc="lower right", fontsize=8.5, frameon=False, ncol=2)
    ax.text(0.5, -49.5, f"順位相関 {M['pref_rho_2010_vs_ratio_2025']:+.2f}（割合が高かった県ほど、変化率で見た減り方は小さい）", fontsize=9)
    ax.set_title("割合が高かった県は、ポイントでは大きく減ったが、率では減り方が小さい", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC + "。点は47都道府県")
    save(fig, "fig3_pref_scatter.png")


def fig4():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(len(RN)); w = 0.2
    ax.bar(x - 1.5 * w, RQ.loc[RN, "share_2010"], width=w, color="#9ecae1", label="3世代世帯 2010年")
    ax.bar(x - 0.5 * w, RQ.loc[RN, "share_2020"], width=w, color=C[0], label="3世代世帯 2020年")
    ax.bar(x + 0.5 * w, RQ.loc[RN, "single65_share_2010"], width=w, color="#fdae6b", label="65歳以上の単独世帯 2010年")
    ax.bar(x + 1.5 * w, RQ.loc[RN, "single65_share_2020"], width=w, color=C[1], label="65歳以上の単独世帯 2020年")
    ax.set_xticks(x, RN)
    ax.set_ylim(0, 19)
    ax.set_ylabel("一般世帯に占める割合（%）")
    ax.legend(loc="upper right", fontsize=8.5, frameon=False, ncol=2)
    ax.grid(axis="x", visible=False)
    ax.set_title("2010年は東北・中部で3世代世帯が65歳以上の単独世帯より多かったが、2020年は逆に", loc="left", fontsize=11)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。地方は北から南の順。原数値のそろう2010年と2020年")
    save(fig, "fig4_elderly_single.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
