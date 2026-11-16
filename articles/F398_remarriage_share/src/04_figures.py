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

SRC = "出典：厚生労働省「人口動態統計」（確定数）第9.5表・第9.7表をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
Y = pd.read_csv(RES / "yearly_shares.csv")


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(Y.year, Y.share_any_re, color=C[0], lw=2.4, marker="o", ms=2.5)
    ax.axhline(25, color="#999999", ls="--", lw=1)
    ax.text(1953, 25.4, "4組に1組（25%）", fontsize=9, color="#777777")
    for y in (1952, 1990, 2005, 2015, 2025):
        v = float(Y.set_index("year").share_any_re[y])
        ax.annotate(f"{y}年 {v:.1f}%", (y, v), xytext={1952: (6, 6), 1990: (0, -16), 2025: (-4, -16)}.get(y, (0, 9)), textcoords="offset points",
                    ha={1952: "left", 2025: "right"}.get(y, "center"), fontsize=9)
    ax.set_xlim(1950, 2027); ax.set_ylim(0, 32)
    ax.set_ylabel("夫妻のどちらかまたは両方が再婚の婚姻の割合（%）")
    ax.set_title("再婚を含む婚姻の割合：2005年に25%を超え、2015年の26.8%をピークに23.8%へ", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。1966年より前は5年おきなどの値")
    save(fig, "fig1_share_any_remarriage.png")


def fig2():
    y = Y[Y.year >= 1970]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(y.year, y.share_husband_re, color=C[0], lw=2.4, label="夫が再婚（夫妻とも再婚を含む）")
    ax.plot(y.year, y.share_wife_re, color=C[1], lw=2.4, label="妻が再婚（夫妻とも再婚を含む）")
    for col, c in (("share_husband_re", C[0]), ("share_wife_re", C[1])):
        ax.annotate(f"{y[col].iloc[-1]:.1f}%", (y.year.iloc[-1], y[col].iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=10, color=c)
    ax.set_xlim(1968, 2029); ax.set_ylim(0, 25)
    ax.set_ylabel("婚姻件数に占める割合（%）")
    ax.legend(loc="upper left", fontsize=9.5, frameon=False)
    ax.set_title("夫が再婚の割合は、1970年以降ずっと妻より2ポイントほど高い", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC)
    save(fig, "fig2_husband_wife.png")


def fig3():
    a = pd.read_csv(RES / "remarriage_age_share.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for sex, c in (("夫", C[0]), ("妻", C[1])):
        s = a[a.sex == sex]
        ax.plot(s.year, s.age50, color=c, lw=2.4, marker="o", ms=3, label=f"再婚の{sex}")
        ax.annotate(f"{s.age50.iloc[-1]:.1f}%", (s.year.iloc[-1], s.age50.iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=10, color=c)
    ax.set_xlim(1988, 2028.5); ax.set_ylim(0, 40)
    ax.set_ylabel("再婚する人のうち50歳以上の割合（%）")
    ax.legend(loc="upper left", fontsize=9.5, frameon=False)
    ax.set_title("再婚する人のうち50歳以上は、夫21.6%→33.8%、妻13.9%→26.6%（2000→2025年）", loc="left", fontsize=11)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。その年に結婚生活に入り届け出たもの、年齢不詳を除く")
    save(fig, "fig3_remarriage_age50.png")


def fig4():
    q = pd.read_csv(RES / "requestion_counts.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(q.year, q.first_both / 1e4, color=C[2], lw=2.4, label="夫妻とも初婚")
    ax2 = ax.twinx()
    ax2.plot(q.year, q.any_re / 1e4, color=C[3], lw=2.4, label="再婚を含む（右目盛り）")
    ax.set_ylim(0, 110); ax2.set_ylim(0, 22)
    ax.set_ylabel("夫妻とも初婚の婚姻件数（万）"); ax2.set_ylabel("再婚を含む婚姻件数（万）")
    ax2.grid(False); ax2.spines["right"].set_visible(True)
    rq = M["requestion"]
    ax.text(0.98, 0.95, f"夫妻とも初婚：{rq['first_peak_year']}年 {rq['first_peak']/1e4:.1f}万 → 2025年 {rq['first_2025']/1e4:.1f}万\n再婚を含む：{rq['re_peak_year']}年 {rq['re_peak']/1e4:.1f}万 → 2025年 {rq['re_2025']/1e4:.1f}万",
            transform=ax.transAxes, ha="right", va="top", fontsize=9.5)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=9.5, frameon=False)
    ax.set_title("初婚どうしは1972年から減り続け、再婚を含む婚姻は2006年まで増えた", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.91, top=0.9, bottom=0.1)
    source(fig, SRC)
    save(fig, "fig4_counts.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
