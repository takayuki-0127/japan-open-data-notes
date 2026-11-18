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
SRC = "出典：総務省・経済産業省「経済センサス‐活動調査」（令和3年・平成28年、2007年以前と2014年は商業統計）をもとに作成者が加工して作成"
META = {"Software": None}
m = json.load(open(R / "main.json", encoding="utf-8"))
NM = {"6098": "中古品（骨とう品を除く）", "5912": "中古自動車", "5933": "中古電気製品", "6062": "古本", "6097": "骨とう品", "I2": "小売業計"}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.015, SRC, fontsize=7.0, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


# 図1：中古品小売業の販売額と、小売業計に占める割合（1994〜2016年）
u = m["used6098"]
yrs = [1994, 1997, 2002, 2007, 2012, 2014, 2016]
fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.6))
ax = axs[0]
ax.bar(range(len(yrs)), [u["sales_oku"][str(y)] for y in yrs], color=C[0], width=0.65)
for i, y in enumerate(yrs):
    ax.text(i, u["sales_oku"][str(y)] + 60, f"{u['sales_oku'][str(y)]:,.0f}", ha="center", fontsize=8.4, color=INK2)
ax.set_xticks(range(len(yrs))); ax.set_xticklabels(yrs, fontsize=9)
ax.set_ylabel("販売額（億円）")
ax.set_title("販売額", loc="left", fontsize=10.5, color=INK2)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax = axs[1]
ax.plot(range(len(yrs)), [u["share_pct"][str(y)] for y in yrs], color=C[1], lw=2.2, marker="o")
for i, y in enumerate(yrs):
    ax.text(i, u["share_pct"][str(y)] + 0.012, f"{u['share_pct'][str(y)]:.2f}%", ha="center", fontsize=8.4, color=INK2)
ax.axvspan(3.5, 4.5, color="#ecebe7", zorder=0)
ax.text(4, 0.02, "2012年は\n調査の切り替え", ha="center", fontsize=8, color=INK2)
ax.set_xticks(range(len(yrs))); ax.set_xticklabels(yrs, fontsize=9)
ax.set_ylim(0, 0.36)
ax.set_ylabel("小売業計の販売額に占める割合（%）")
ax.set_title("小売業計に占める割合", loc="left", fontsize=10.5, color=INK2)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.suptitle(f"中古品小売業（骨とう品を除く）の販売額は、小売業計の0.05%から0.31%に（1994→2016年）", x=0.01, ha="left", fontsize=12.5, color=INK)
fig.text(0.01, 0.015, SRC, fontsize=7.0, color=INK2)
fig.subplots_adjust(left=0.08, right=0.98, top=0.84, bottom=0.14, wspace=0.3)
save(fig, "fig1_used_goods_share.png")

# 図2：2016→2021年（法人の事業所）の販売額と事業所数の伸び
codes = ["6098", "5912", "5933", "6062", "6097", "I2"]
sales_g = [m["corp_2016_2021"][c]["growth_pct"] if c in m["corp_2016_2021"] else m["other_used"][c]["corp_growth_2016_2021_pct"] for c in codes]
rob = pd.read_csv(R / "robustness.csv", dtype={"code": str})
s = pd.read_csv(R / "series_used_retail.csv", dtype={"code": str})
ec = s.pivot(index="year", columns="code", values="est_corp")
est_g = [float((ec.loc[2021, c] / ec.loc[2016, c] - 1) * 100) for c in codes]
fig, ax = plt.subplots(figsize=(9.0, 4.8))
x = np.arange(len(codes))
ax.bar(x - 0.19, sales_g, width=0.36, color=C[0], label="販売額（小売）")
ax.bar(x + 0.19, est_g, width=0.36, color=C[3], label="事業所数")
for xi, v in zip(x - 0.19, sales_g):
    ax.text(xi, v + (0.8 if v >= 0 else -2.6), f"{v:+.1f}", ha="center", fontsize=8.6, color=INK2)
for xi, v in zip(x + 0.19, est_g):
    ax.text(xi, v + (0.8 if v >= 0 else -2.6), f"{v:+.1f}", ha="center", fontsize=8.6, color=INK2)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([NM[c].replace("（骨とう品を除く）", "\n（骨とう品を除く）") + ("\n小売業" if c not in ("I2",) else "") for c in codes], fontsize=8.6)
ax.set_ylim(-42, 22)
ax.set_ylabel("2016→2021年の増減率（%）")
ax.legend(frameon=False, fontsize=9, loc="lower right")
finish(fig, ax, "法人の店で比べると、中古品小売業の販売額は+7.6%、小売業計は+2.1%（2016→2021年）")
fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.2)
save(fig, "fig2_corp_growth_2016_2021.png")

# 図3：インターネット販売の割合（2016年と2021年）
fig, ax = plt.subplots(figsize=(8.4, 4.6))
y = np.arange(len(codes))[::-1]
a = [m["internet_share"][c]["2016"] for c in codes]; b = [m["internet_share"][c]["2021"] for c in codes]
for yi, x0, x1 in zip(y, a, b):
    ax.plot([x0, x1], [yi, yi], color=GRID, lw=3, zorder=1)
ax.scatter(a, y, color=C[0], s=34, zorder=2, label="2016年")
ax.scatter(b, y, color=C[1], s=34, zorder=3, label="2021年")
for yi, x1 in zip(y, b):
    ax.text(x1 + 0.4, yi + 0.12, f"{x1:.1f}%", fontsize=8.6, color=C[1])
ax.set_yticks(y); ax.set_yticklabels([NM[c] + ("小売業" if c != "I2" else "") for c in codes], fontsize=9)
ax.set_xlim(0, 20)
ax.set_xlabel("小売の販売額のうちインターネット販売の割合（%、法人の事業所）")
ax.legend(frameon=False, fontsize=9, loc="lower right")
rq = m["requestion_store_vs_internet"]["6098"]
finish(fig, ax, f"中古品小売業のネット販売は7.1%→14.6%。伸びた{rq['d_total_oku']:.0f}億円はほぼネットの分", grid="x")
fig.subplots_adjust(left=0.26, right=0.97, top=0.88, bottom=0.15)
save(fig, "fig3_internet_share.png")

# 図4：中古の品目は、どの店で売られたか（2021年）
w = pd.read_csv(R / "where_used_items_sold.csv", dtype={"item_code": str})
order = ["乗用車（中古）", "トラック（中古）", "中古品（骨とう品を除く）", "中古電気製品", "古本", "骨とう品"]
w = w.set_index("item").loc[order]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
yy = np.arange(len(order))[::-1]
home = 100 - w.outside_share_pct.values
ax.barh(yy, home, color=C[0], label="その品目の名前の業種の店（例：中古自動車小売業）")
ax.barh(yy, w.outside_share_pct.values, left=home, color=C[3], label="ほかの業種の店（新車の販売店・無店舗小売など）")
for yi, h, o, tot in zip(yy, home, w.outside_share_pct.values, w.sales_retail_mil.values):
    ax.text(h / 2, yi, f"{h:.0f}%", ha="center", va="center", color="white", fontsize=9)
    ax.text(100.8, yi, f"{tot / 100:,.0f}億円", va="center", fontsize=8.6, color=INK2)
ax.set_yticks(yy); ax.set_yticklabels(order, fontsize=9)
ax.set_xlim(0, 115)
ax.set_xlabel("その品目の販売額の内訳（%、2021年、小売業の法人の事業所）")
ax.legend(frameon=False, fontsize=8.4, loc="upper center", bbox_to_anchor=(0.45, -0.17), ncol=1)
finish(fig, ax, "中古の車・中古品・古本は7〜8割が専門の業種の店。電気製品と骨とう品は5割台", grid="x")
fig.subplots_adjust(left=0.22, right=0.97, top=0.88, bottom=0.3)
save(fig, "fig4_where_sold.png")
print("figures done")
