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

SRC = "出典：総務省「住宅・土地統計調査」土地集計（2008・2013・2018・2023年）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))


def fig1():
    t = pd.read_csv(RES / "japan_trend.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(len(t))
    ax.bar(x, t.unused_lots / 1e4, 0.55, color=C[0], label="空き地＋原野などの件数（万件、左）")
    va = t.vacant_lots / 1e4
    ax.bar(x[2:], va[2:], 0.55, color=C[1], label="うち空き地（2018年から別に集計）")
    for xi, v in zip(x, t.unused_lots / 1e4):
        ax.text(xi, v + 2, f"{v:.1f}", ha="center", fontsize=9.5)
    for xi, v in zip(x[2:], va[2:]):
        ax.text(xi, v / 2, f"{v:.1f}", ha="center", fontsize=9, color="white")
    ax.set_xticks(x, [f"{y}年" for y in t.year])
    ax.set_ylim(0, 250)
    ax.set_ylabel("世帯が住まい以外に持つ宅地などの件数（万件）")
    ax2 = ax.twinx()
    ax2.plot(x, t.unused_share, color=GRAY, marker="o", lw=1.5, label="全件数に占める割合（%、右）")
    for xi, v in zip(x, t.unused_share):
        ax2.text(xi + 0.08, v + 0.25, f"{v:.1f}%", fontsize=8.5, color=GRAY)
    ax2.set_ylim(0, 24); ax2.set_ylabel("割合（%）"); ax2.grid(False); ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8.5, frameon=False)
    ax.set_title("世帯が持つ使っていない土地：件数は2013年が山、割合は16%台で横ばい", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.12)
    source(fig, SRC)
    save(fig, "fig1_japan_unused_lots.png")


def fig2():
    rg = M["regions"]
    names = list(rg.keys())
    x = np.arange(len(names))
    a = [rg[n]["vacant_share_2018"] for n in names]; b = [rg[n]["vacant_share_2023"] for n in names]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(x - 0.2, a, 0.4, color="#9cbfe9", label="2018年")
    ax.bar(x + 0.2, b, 0.4, color=C[0], label="2023年")
    for xi, (u, v) in enumerate(zip(a, b)):
        ax.text(xi - 0.2, u + 0.3, f"{u:.1f}", ha="center", fontsize=8.5)
        ax.text(xi + 0.2, v + 0.3, f"{v:.1f}", ha="center", fontsize=8.5)
    cr = M["city_vs_rest"]["2023"]
    ax.text(0.99, 0.97, f"2023年 政令市に住む世帯 {cr['city_vacant_share']:.1f}%／政令市以外 {cr['rest_vacant_share']:.1f}%",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color=GRAY)
    ax.set_xticks(x, names)
    ax.set_ylim(0, 25)
    ax.set_ylabel("空き地の件数 ÷ 持っている宅地などの件数（%）")
    ax.set_title("空き地の割合（住む地方別、北から南）：8地方のうち7つで下がった", loc="left", fontsize=12)
    ax.legend(loc="upper right", fontsize=9, frameon=False, bbox_to_anchor=(1, 0.92))
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC + "。地方は世帯の住む場所で、土地の場所ではない")
    save(fig, "fig2_region_vacant_share.png")


def fig3():
    P = pd.read_csv(RES / "prefecture_table.csv")
    s = P[P.year == 2023]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.scatter(s.inh_share, s.vacant_share, s=s.lots / 4000, color=C[0], alpha=0.6, edgecolor="white")
    b = np.polyfit(s.inh_share, s.vacant_share, 1)
    xs = np.linspace(s.inh_share.min(), s.inh_share.max(), 10)
    ax.plot(xs, b[1] + b[0] * xs, color=C[1], lw=1.5)
    c = M["corr_2023"]
    ax.text(0.98, 0.04, f"相関係数 r = {c['r']:+.2f}（47都道府県、p = {c['p']:.2f}）\n円の大きさは所有件数", transform=ax.transAxes, va="bottom", ha="right", fontsize=9.5)
    ax.set_xlabel("相続・贈与で取得した件数の割合（%）")
    ax.set_ylabel("空き地の割合（%）")
    ax.set_title("相続で受け継いだ土地の多い県ほど空き地が多い、とは言えない（2023年）", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.17)
    source(fig, SRC)
    save(fig, "fig3_inheritance_vs_vacant.png")


def fig4():
    st = pd.read_csv(RES / "requestion_stability.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.scatter(st.vacant_share_2018, st.vacant_share_2023, color=C[2], alpha=0.75, edgecolor="white", s=45)
    lim = (5, 25)
    ax.plot(lim, lim, color="#999999", ls="--", lw=1)
    ax.text(21.5, 22.6, "2018年と同じ", fontsize=8.5, color="#777777", rotation=33)
    q = M["requestion_stability"]
    ax.text(0.02, 0.96, f"2018年と2023年の相関 r = {q['r_2018_2023']:.2f}\n47のうち {q['n_down']} 都道府県で下がった（変化の中央値 {q['median_change']:+.1f}ポイント）",
            transform=ax.transAxes, va="top", fontsize=9.5)
    ax.set_xlim(*lim); ax.set_ylim(*lim)
    ax.set_xlabel("2018年の空き地の割合（%）"); ax.set_ylabel("2023年の空き地の割合（%）")
    ax.set_title("県の差は5年たっても続く：点の多くは破線の下（割合が下がった）", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.17)
    source(fig, SRC)
    save(fig, "fig4_stability_2018_2023.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
