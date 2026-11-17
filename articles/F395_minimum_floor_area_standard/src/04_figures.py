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

SRC = "出典：総務省「住宅・土地統計調査」（2008・2013・2018・2023年）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
YRS = [2008, 2013, 2018, 2023]


def fig1():
    t = M["share_by_tenure"]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for key, lab, c in [("借家", "借家", C[1]), ("総数", "全体", "#222222"), ("持ち家", "持ち家", C[0])]:
        v = [t[str(y)][key] for y in YRS]
        ax.plot(YRS, v, color=c, lw=2.4, marker="o", label=lab)
        for x, vv in zip(YRS, v):
            ax.text(x, vv + 0.5, f"{vv:.1f}", ha="center", fontsize=9, color=c)
    cnt = M["below_count"]
    ax.text(0.02, 0.6, "水準未満の世帯数（万）\n" + "、".join(f"{y}年 {cnt[str(y)]/1e4:.0f}" for y in YRS), transform=ax.transAxes, fontsize=9.5)
    ax.set_xticks(YRS); ax.set_xlim(2006, 2025)
    ax.set_ylim(0, 22)
    ax.set_ylabel("最低居住面積水準に満たない世帯の割合（%）")
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    ax.set_title("水準に満たない世帯の割合：全体は6.9%→6.5%とほぼ横ばい", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。分母は水準の状況が不詳の世帯を除く")
    save(fig, "fig1_share_by_tenure.png")


def fig2():
    s, w = M["share_by_size"], M["size_composition"]
    sz = list(s["2008"].keys()); x = np.arange(len(sz))
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(x - 0.2, [s["2008"][k] for k in sz], 0.4, color="#9cbfe9", label="2008年")
    ax.bar(x + 0.2, [s["2023"][k] for k in sz], 0.4, color=C[0], label="2023年")
    for xi, k in enumerate(sz):
        ax.text(xi - 0.2, s["2008"][k] + 0.2, f"{s['2008'][k]:.1f}", ha="center", fontsize=8.5)
        ax.text(xi + 0.2, s["2023"][k] + 0.2, f"{s['2023'][k]:.1f}", ha="center", fontsize=8.5)
        ax.text(xi, -1.6, f"世帯の構成\n{w['2008'][k]:.0f}%→{w['2023'][k]:.0f}%", ha="center", fontsize=8, color=GRAY)
    d = M["decomposition_2008_2023"]
    ax.text(0.98, 0.95, f"全体の変化 {d['total']:+.2f}ポイント\n＝ 人数ごとの割合の変化 {d['within']:+.2f}\n＋ 単身の世帯が増えた分（構成）{d['composition']:+.2f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9.5)
    ax.set_xticks(x, sz)
    ax.set_ylim(-2.5, 16)
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_ylabel("水準に満たない世帯の割合（%）")
    ax.legend(loc="upper center", fontsize=9.5, frameon=False)
    ax.set_title("6人以上を除く人数で割合は下がったが、割合の高い単身の世帯が増えた", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC)
    save(fig, "fig2_by_size.png")


def fig3():
    rg = M["regions"]; names = list(rg.keys()); x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for k, (y, c) in enumerate([(2008, "#9cbfe9"), (2023, C[0])]):
        v = [rg[n][str(y)] for n in names]
        ax.bar(x + (k - 0.5) * 0.4, v, 0.4, color=c, label=f"{y}年")
        for xi, vv in zip(x, v):
            ax.text(xi + (k - 0.5) * 0.4, vv + 0.15, f"{vv:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(x, names)
    ax.set_ylim(0, 12)
    ax.set_ylabel("水準に満たない世帯の割合（%）")
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    ax.set_title("地方別（北から南）：関東と近畿で高く、大きく下がったのもこの2つ", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC)
    save(fig, "fig3_regions.png")


def fig4():
    q = M["requestion"]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    v = [q[str(y)]["rent_single"] for y in YRS]
    ax.bar(YRS, v, 3, color=C[1], label="水準に満たない世帯のうち、借家の単身の世帯の割合")
    for x, vv, y in zip(YRS, v, YRS):
        ax.text(x, vv + 1, f"{vv:.1f}%", ha="center", fontsize=9.5)
        ax.text(x, 5, f"{q[str(y)]['rent_single_count']/1e4:.0f}万世帯\n（借家の単身の\n{q[str(y)]['rent_single_rate']:.1f}%）", ha="center", fontsize=8.5, color="white")
    ax.set_xticks(YRS); ax.set_ylim(0, 85)
    ax.set_ylabel("割合（%）")
    ax.legend(loc="upper left", fontsize=9.5, frameon=False)
    ax.set_title("水準に満たない世帯の7割は、借家に住む単身の世帯になった", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC)
    save(fig, "fig4_rent_single.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
