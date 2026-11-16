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
SRC = "出典：総務省「家計調査」家計収支編 二人以上の世帯 第4-6表（1世帯当たり年間）をもとに作成者が加工して作成"
META = {"Software": None}
fmt = matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}")


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


t = pd.read_csv(R / "by_year.csv", index_col=0)
m = json.load(open(R / "main.json", encoding="utf-8"))

# 図1
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(t.index, t.rice, color=C[1], lw=2.4, marker="o", ms=4, label="米")
ax.plot(t.index, t.bread, color=C[0], lw=2.4, marker="o", ms=4, label="パン（食パン＋他のパン）")
for y in [2002, 2011, 2023, 2025]:
    for col, dy in [("rice", 9 if y != 2011 else -15), ("bread", -15 if y != 2011 else 9)]:
        if y == 2023 and col == "rice":
            dy = -15
        if y == 2023 and col == "bread":
            dy = 9
        ax.annotate(f"{t[col][y]:,.0f}", (y, t[col][y]), textcoords="offset points", xytext=(0, dy), ha="center", fontsize=8.6, color=INK)
over = m["hypotheses"]["H1"]["years_bread_over_rice"]
for y in over:
    ax.axvspan(y - 0.5, y + 0.5, color="#cde2fb", alpha=0.5, lw=0)
ax.text(2018, 15200, "色の帯：パンが米を上回った年", ha="center", fontsize=9, color=INK2)
ax.yaxis.set_major_formatter(fmt)
ax.set_ylim(14000, 46000)
ax.set_xlabel("年")
ax.set_ylabel("1世帯当たり年間の支出（円）")
ax.legend(frameon=False, loc="upper center")
finish(fig, ax, "パンは2011年に初めて米を上回り、2025年に米が上に戻った")
save(fig, "fig1_rice_vs_bread.png")

# 図2：米の金額・量・価格（2002年＝100）
fig, ax = plt.subplots(figsize=(8.8, 5.0))
base = 2002
for col, lab, c in [("rice", "支出金額", C[1]), ("rice_qty_kg", "購入数量（kg）", C[2]), ("rice_price_per_kg", "平均価格（円/kg）", C[3])]:
    v = 100 * t[col] / t[col][base]
    ax.plot(t.index, v, color=c, lw=2.2, label=lab)
    ax.annotate(f"{v.iloc[-1]:.0f}", (t.index[-1], v.iloc[-1]), textcoords="offset points", xytext=(6, 0), va="center", fontsize=9, color=INK)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
d = m["decomposition"][0]
ax.text(2003, 172, f"2023→2025年の米の支出 +{d['change']:,.0f}円のうち\n価格の上昇による分 {d['price_share_pct']:.0f}%、量の増加による分 {100 - d['price_share_pct']:.0f}%",
        fontsize=9.2, color=INK, va="top")
ax.set_xlim(2001, 2027)
ax.set_xlabel("年")
ax.set_ylabel("指数（2002年＝100）")
ax.legend(frameon=False, loc="center left")
finish(fig, ax, "米の支出は量の減少で下がり、2024〜25年は価格の上昇で跳ね上がった")
save(fig, "fig2_rice_qty_price.png")

# 図3：パンの内訳
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(t.index, t.other_bread, color=C[0], lw=2.2, label="他のパン（菓子パン・調理パンなど）")
ax.plot(t.index, t.plain_bread, color=C[2], lw=2.2, label="食パン")
for col in ["other_bread", "plain_bread"]:
    for y in [2002, 2023]:
        ax.annotate(f"{t[col][y]:,.0f}", (y, t[col][y]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8.6, color=INK)
ax.yaxis.set_major_formatter(fmt)
ax.set_ylim(0, 27000)
ax.set_xlabel("年")
ax.set_ylabel("1世帯当たり年間の支出（円）")
ax.legend(frameon=False, loc="lower right")
h4 = m["hypotheses"]["H4"]
finish(fig, ax, f"2002→2023年のパンの増加は、他のパンが+{h4['other_increase']:,.0f}円、食パンが+{h4['plain_increase']:,.0f}円")
save(fig, "fig3_bread_breakdown.png")

# 図4：年齢別の比
ra = pd.read_csv(R / "ratio_by_age.csv")
groups = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上", "平均"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(groups)); w = 0.27
for i, (y, c) in enumerate([(2002, "#b7d3f6"), (2023, C[0]), (2025, C[1])]):
    v = ra[ra.year == y].set_index("group").loc[groups, "ratio"].values
    ax.bar(x + (i - 1) * w, v, w * 0.95, color=c, label=f"{y}年")
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 1) * w, vi + 0.03, f"{vi:.2f}", ha="center", fontsize=7.6, color=INK)
ax.axhline(1, color=INK, lw=1.0, ls="--")
ax.text(len(groups) - 0.5, 1.03, "1＝パンと米が同じ", ha="right", fontsize=9, color=INK2)
ax.set_xticks(x, ["世帯主\n" + g if g != "平均" else "全世帯\nの平均" for g in groups], fontsize=9)
ax.set_ylabel("パンの支出 ÷ 米の支出")
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "2025年にパンが米を上回ったのは、世帯主が30代の世帯だけ")
fig.subplots_adjust(bottom=0.18)
save(fig, "fig4_ratio_by_age.png")
