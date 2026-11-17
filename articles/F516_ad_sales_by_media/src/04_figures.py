"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：経済産業省「特定サービス産業動態統計調査」長期データ（広告業の売上高）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.96, top=0.89, bottom=0.15)


INTX = matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:.0f}")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
t = pd.read_csv(R / "tv_internet.csv", index_col=0)
Y1 = m["year_last"]

# 図1
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = t.loc[2006:]
ax.plot(x.index, x.tv / 1e6, color=C[1], lw=2.4, marker="o", ms=4, label="テレビ（4媒体広告）")
ax.plot(x.index, x.internet / 1e6, color=C[0], lw=2.4, marker="o", ms=4, label="インターネット広告")
cy = m["hypotheses"]["H1"]["first_year_internet_over_tv"]
ax.axvline(cy, color=INK2, lw=0.8, ls=":")
ax.text(cy - 0.2, 0.25, f"{cy}年に逆転\n（実数）", ha="right", fontsize=9, color=INK2)
for col in ["tv", "internet"]:
    for y in [2006, Y1]:
        ax.annotate(f"{x[col][y] / 1e6:.2f}", (y, x[col][y] / 1e6), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=INK)
ax.set_ylim(0, 2.0)
ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(2)); ax.xaxis.set_major_formatter(INTX)
ax.set_xlabel("年")
ax.set_ylabel("広告業の売上（兆円）")
ax.legend(frameon=False, loc="center left")
finish(fig, ax, "広告会社の売上では、インターネットがテレビを上回ったのは2021年")
save(fig, "fig1_tv_vs_internet.png")

# 図2：媒体の割合
sh = pd.read_csv(R / "share_by_year.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c in [("tv", "テレビ", C[1]), ("internet", "インターネット", C[0]), ("sp_pr", "SP・PR・催事企画", C[2]),
                    ("newspaper", "新聞", C[3]), ("insert_dm", "折込み・ダイレクトメール", C[4])]:
    s = sh[col].dropna()
    ax.plot(s.index, s, color=c, lw=2.0, label=lab)
    ax.annotate(f"{s.iloc[-1]:.1f}", (s.index[-1], s.iloc[-1]), textcoords="offset points", xytext=(6, 0), va="center", fontsize=9, color=INK)
ax.set_xlim(1987, 2027)
ax.set_xlabel("年")
ax.set_ylabel("広告業の売上高合計に占める割合（%）")
ax.set_ylim(0, 36)
ax.legend(frameon=False, loc="lower left", ncol=3, fontsize=9, bbox_to_anchor=(0.0, 0.0))
finish(fig, ax, f"テレビの割合は2000年{m['share_2000_tv']:.1f}%→{Y1}年{m['share_last']['tv']:.1f}%、新聞は{m['share_2000_newspaper']:.1f}%→{m['share_last']['newspaper']:.1f}%")
save(fig, "fig2_media_share.png")

# 図3：実数の伸びと調整済みの伸び（インターネット）
rv = pd.read_csv(R / "raw_vs_adjusted.csv")
gi = rv[rv.item == "internet"].set_index("year")
fig, ax = plt.subplots(figsize=(8.8, 5.0))
xx = np.arange(len(gi)); w = 0.4
ax.bar(xx - w / 2, gi.raw_growth, w * 0.95, color="#86b6ef", label="実数の前年比（調査対象の追加を含む）")
ax.bar(xx + w / 2, gi.adjusted_growth, w * 0.95, color=C[0], label="調整済みの前年比（同じ対象どうし）")
for i, (y, q) in enumerate(gi.iterrows()):
    if abs(q.gap) >= 5:
        ax.text(i - w / 2, q.raw_growth + 1.5, f"{q.raw_growth:.0f}", ha="center", fontsize=8.6, color=INK)
        ax.text(i + w / 2, q.adjusted_growth + (1.5 if q.adjusted_growth >= 0 else -4), f"{q.adjusted_growth:.1f}", ha="center", fontsize=8.6, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xx, [str(y) if y % 2 == 1 else "" for y in gi.index])
ax.set_ylabel("インターネット広告の売上の前年比（%）")
ax.set_ylim(-5, 80)
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "インターネットの実数の伸びには、2009・2011・2020年に調査対象の追加による段差")
save(fig, "fig3_internet_raw_vs_adjusted.png")

# 図4：比
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = t.loc[2006:]
ax.plot(x.index, x.ratio_internet_tv, color=C[0], lw=2.4, marker="o", ms=4, label="実数の比")
ax.plot(x.index, x.ratio_from_index, color=C[0], lw=2.0, ls="--", marker="o", ms=4, label="調整済みの伸びでつないだ比（2006年基点）")
ax.axhline(1, color=INK, lw=1.0, ls=":")
ax.text(2006.2, 1.03, "1＝インターネットとテレビが同じ", fontsize=9, color=INK2)
for col in ["ratio_internet_tv", "ratio_from_index"]:
    ax.annotate(f"{x[col][Y1]:.2f}", (Y1, x[col][Y1]), textcoords="offset points", xytext=(6, 0), va="center", fontsize=9, color=INK)
ax.set_xlim(2005.5, 2025.5)
ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(2)); ax.xaxis.set_major_formatter(INTX)
ax.set_ylim(0, 1.4)
ax.set_xlabel("年")
ax.set_ylabel("インターネット広告 ÷ テレビ")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "同じ対象どうしの伸びでつなぐと、インターネットはまだテレビの半分ほど")
save(fig, "fig4_ratio_raw_vs_index.png")
