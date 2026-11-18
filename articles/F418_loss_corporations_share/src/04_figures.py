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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7d5ba6"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：国税庁「会社標本調査」各年度分 第2表・調査結果の概要 第6表をもとに作成者が加工して作成"
META = {"Software": None}
m = json.load(open(R / "main.json", encoding="utf-8"))
yr = pd.read_csv(R / "yearly.csv", index_col=0)
off = pd.read_csv(ROOT / "data" / "official_table6.csv")
sb = pd.read_csv(R / "by_size_band.csv")
ind = pd.read_csv(R / "by_industry.csv")


def finish(fig, ax, title, grid="y", bottom=0.15):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.015, SRC, fontsize=7.4, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.88, bottom=bottom)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


# 図1：欠損法人の割合の推移
fig, ax = plt.subplots(figsize=(8.4, 4.6))
oc = off[off.basis == "年分"]
ax.plot(oc.fiscal_year, oc.loss_share_pct, color=C[0], lw=1.4, ls="--", marker="o", ms=3.5, label="公表値（暦年の「年分」、2003〜2006年）")
of = off[off.basis == "年度分"].drop_duplicates("fiscal_year", keep="last")
ax.plot(of.fiscal_year, of.loss_share_pct, color=C[0], lw=2.2, marker="o", ms=4, label="公表値（事業年度の「年度分」、2006〜2024年度分）")
ax.plot(yr.index, yr.share_all, color=C[1], lw=0, marker="x", ms=6, label="第2表から計算（2007〜2024年度分）")
ax.axhline(60, color=INK2, lw=0.9, ls=":")
ax.text(2003.1, 60.4, "60%", color=INK2, fontsize=9)
pk = m["peak_year"]
ax.annotate(f"{m['peak_share']}%（{pk}年度分）", (pk, m["peak_share"]), xytext=(pk + 1.2, 73.6), fontsize=9.5, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.annotate(f"{m['share_2024']}%（2024年度分）", (2024, m["share_2024"]), xytext=(2018.3, 57.6), fontsize=9.5, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_ylim(55, 76)
ax.set_xlim(2002.5, 2025)
ax.set_xticks(range(2003, 2025, 3))
ax.set_ylabel("欠損法人の割合（%）")
ax.set_xlabel("年分・年度分")
ax.legend(frameon=False, fontsize=8.6, loc="upper left", bbox_to_anchor=(0.0, 0.25))
finish(fig, ax, "欠損法人の割合は2009年度分の72.8%から下がり、2024年度分は60.3%")
save(fig, "fig1_share_trend.png")

# 図2：資本金の規模別（2011〜2024年度分）
fig, ax = plt.subplots(figsize=(8.4, 4.6))
bands = ["1,000万円以下", "1,000万円超1億円以下", "1億円超"]
for i, k in enumerate(bands):
    s = sb[(sb.band == k) & (sb.year >= 2011)]
    n24 = m["size_n_2024"][k]
    ax.plot(s.year, s.share, color=C[i], lw=2.2, marker="o", ms=3.5)
    ax.text(2024.25, s.share.iloc[-1], f"{k}\n（2024年度分 {n24:,}社）", color=C[i], fontsize=8.8, va="center")
ax.plot(yr.index[yr.index >= 2011], yr.share_all[yr.index >= 2011], color=INK2, lw=1.2, ls="--")
ax.text(2015.3, 59.6, "全体（点線）", color=INK2, fontsize=9)
ax.set_xlim(2010.5, 2028.6)
ax.set_ylim(15, 80)
ax.set_xticks(range(2011, 2025, 2))
ax.set_ylabel("欠損法人の割合（%）")
ax.set_xlabel("年度分（資本金の区切りがそろう2011年度分以降）")
st = m["size_step"]["1億円超"]
finish(fig, ax, f"資本金1億円超は2011→2013年度分だけで{-st['d2011_2013']}%pt 下がり、その後はほぼ横ばい")
save(fig, "fig2_by_size.png")

# 図3：法人数の割合と営業収入で重みづけした割合
fig, ax = plt.subplots(figsize=(8.4, 4.6))
ax.plot(yr.index, yr.share_all, color=C[0], lw=2.2, marker="o", ms=3.5, label="法人数で数えた割合")
ax.plot(yr.index, yr.sales_share_loss, color=C[1], lw=2.2, marker="o", ms=3.5, label="営業収入（売上）で重みづけした割合")
for y in [2011, 2024]:
    ax.text(y + (0.6 if y == 2011 else 0), yr.sales_share_loss[y] + (2.0 if y == 2011 else -3.8), f"{yr.sales_share_loss[y]:.1f}%", color=C[1], fontsize=9, ha="left" if y == 2011 else "center")
    ax.text(y, yr.share_all[y] + 1.8, f"{yr.share_all[y]:.1f}%", color=C[0], fontsize=9, ha="center")
ax.set_ylim(0, 82)
ax.set_xticks(range(2007, 2025, 2))
ax.set_ylabel("欠損法人が占める割合（%）")
ax.set_xlabel("年度分")
ax.legend(frameon=False, fontsize=9, loc="lower left")
finish(fig, ax, "売上で重みづけすると、欠損法人の割合は2024年度分で2割ほど")
save(fig, "fig3_count_vs_sales.png")

# 図4：業種別（2011年度分と2024年度分、業種は統計の並び順）
fig, ax = plt.subplots(figsize=(8.4, 5.6))
order = list(m["industry"]["2012"].keys())
y = np.arange(len(order))[::-1]
a = [m["industry"]["2012"][k] for k in order]; b2 = [m["industry"]["2024"][k] for k in order]
for yi, x0, x1 in zip(y, a, b2):
    ax.plot([x1, x0], [yi, yi], color=GRID, lw=3, zorder=1)
ax.scatter(a, y, color=C[0], s=30, zorder=2, label="2012年度分")
ax.scatter(b2, y, color=C[1], s=30, zorder=3, label="2024年度分")
ax.set_yticks(y); ax.set_yticklabels(order, fontsize=9)
ax.axvline(60, color=INK2, lw=0.9, ls=":")
ax.set_xlim(48, 88)
ax.set_xlabel("欠損法人の割合（%、連結・通算法人を除く）")
ax.legend(frameon=False, fontsize=9, loc="lower right")
finish(fig, ax, f"17業種すべてで下がった。高い・低いの並びは2012年度分とほぼ同じ\n（順位相関{m['industry']['spearman_2012_2024']}）", grid="x", bottom=0.13)
fig.subplots_adjust(left=0.2, top=0.86)
save(fig, "fig4_by_industry.png")
print("figures done")
