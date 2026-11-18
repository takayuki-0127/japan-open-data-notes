"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, D, F = ROOT / "results", ROOT / "data", ROOT / "figures"
F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f476"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7d5fc4", "#3aa6b9", "#b5651d", "#6b8e23", "#999999"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC_FBS = "出典：農林水産省「食料需給表」（令和6年度確報の累年表、令和7年度概算。年度）をもとに作成者が加工して作成"
SRC_CROP = "出典：農林水産省「作物統計」収穫量累年統計 小麦（産年）をもとに作成者が加工して作成"
META = {"Software": None}
NORTH_SOUTH = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]


def finish(fig, ax, title, src, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, src, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


f = pd.read_csv(R / "ssr_by_fy.csv")
c = pd.read_csv(D / "crop_wheat_region_year.csv")
m = json.loads((R / "main.json").read_text(encoding="utf-8"))

# 図1：自給率の推移
fig, ax = plt.subplots(figsize=(9, 5.2))
fig.subplots_adjust(left=0.08, right=0.97, top=0.86, bottom=0.14)
ax.plot(f.fy, f.ssr, color=C[0], lw=2.2, label="自給率（国内生産量÷国内消費仕向量）")
ax.plot(f.fy, f.ssr_nofeed, color=C[1], lw=1.4, ls="--", label="飼料用を除いた分母で計算")
for a, b in [(2000, 2004), (2020, 2024)]:
    v = f[(f.fy >= a) & (f.fy <= b)].ssr.mean()
    ax.hlines(v, a, b, color=INK, lw=3)
    ax.annotate(f"{a}〜{str(b)[2:]}年度平均 {v:.1f}%", ((a + b) / 2, v), xytext=(0, -16), textcoords="offset points", fontsize=9, color=INK, ha="center")
lo = m["ssr_min"]
ax.annotate(f"底：{lo['fy']}年度 {lo['ssr']:.1f}%", (lo["fy"], lo["ssr"]), xytext=(10, -4), textcoords="offset points", fontsize=9, color=INK2)
last = f.iloc[-1]
ax.annotate(f"{int(last.fy)}年度（概算）\n{last.ssr:.1f}%", (last.fy, last.ssr), xytext=(-6, 30), textcoords="offset points", fontsize=9, color=C[0], ha="center", arrowprops=dict(arrowstyle="-", color=C[0], lw=0.8))
ax.set_xlim(1959, 2027); ax.set_ylim(0, 50)
ax.set_ylabel("%（重量ベース）")
ax.legend(frameon=False, loc="upper right", fontsize=9.5)
finish(fig, ax, "小麦の自給率は1973年度の3.7%が底。2020年代は16%台に上がった", SRC_FBS)
save(fig, "fig1_ssr_long.png")

# 図2：地方別の収穫量（積み上げ、北から南）
piv = c[c.region.isin(NORTH_SOUTH) & (c.year >= 1958)].pivot(index="year", columns="region", values="harvest_t")[NORTH_SOUTH].fillna(0) / 1000
fig, ax = plt.subplots(figsize=(9, 5.4))
fig.subplots_adjust(left=0.08, right=0.80, top=0.86, bottom=0.14)
ax.stackplot(piv.index, [piv[g].values for g in NORTH_SOUTH], labels=NORTH_SOUTH, colors=C, alpha=0.9, lw=0)
h, l = ax.get_legend_handles_labels()
ax.legend(h, l, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=9, title="北から南の順", title_fontsize=9)
ax.set_ylabel("収穫量（千t）"); ax.set_xlim(1958, 2024)
finish(fig, ax, "産地は北へ移った：今の収穫量の約3分の2は北海道", SRC_CROP + "。北陸の2002〜11年産は秘匿（x）のため0として描画")
save(fig, "fig2_harvest_by_region.png")

# 図3：北海道と都府県の作付面積と単収（2000〜04年産平均＝100）
fig, axs = plt.subplots(1, 2, figsize=(9.4, 4.8), sharey=True)
fig.subplots_adjust(left=0.08, right=0.98, top=0.80, bottom=0.17, wspace=0.08)
for ax, g in zip(axs, ["北海道", "都府県"]):
    s = c[(c.region == g) & (c.year >= 2000)].set_index("year")[["area_ha", "harvest_t"]]
    base = s.loc[2000:2004].mean()
    yld = s.harvest_t / s.area_ha
    ybase = base.harvest_t / base.area_ha
    ax.plot(s.index, s.area_ha / base.area_ha * 100, color=C[0], lw=2, label="作付面積")
    ax.plot(s.index, yld / ybase * 100, color=C[1], lw=1.6, label="単収（収穫量÷面積）")
    ax.plot(s.index, s.harvest_t / base.harvest_t * 100, color=INK, lw=1.2, ls=":", label="収穫量")
    ax.axhline(100, color=INK2, lw=0.8)
    ay = m["area_yield"][g]
    ax.set_title(f"{g}：2020〜24年産平均は面積{ay['area_pct']:+.0f}%・単収{ay['yield_pct']:+.0f}%", fontsize=10.5, loc="left", color=INK)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_xlim(2000, 2024)
axs[0].set_ylabel("2000〜04年産平均＝100")
axs[0].legend(frameon=False, fontsize=9, loc="upper left")
fig.suptitle("北海道は面積と単収の両方で増え、単収の方がやや大きい", x=0.01, ha="left", fontsize=12.5, color=INK)
fig.text(0.01, 0.01, SRC_CROP, fontsize=7.6, color=INK2)
save(fig, "fig3_area_yield.png")

# 図4：問い直し。地方の割合の変化（北から南）
q = pd.read_csv(R / "requestion_region_shares.csv")
periods = ["1960〜1964", "2000〜2004", "2020〜2024"]
fig, ax = plt.subplots(figsize=(9, 5.4))
fig.subplots_adjust(left=0.12, right=0.97, top=0.86, bottom=0.14)
y = np.arange(len(NORTH_SOUTH))
w = 0.26
for i, p in enumerate(periods):
    s = q[q.period == p].set_index("region").loc[NORTH_SOUTH]
    ax.barh(y + (i - 1) * w, s.harvest_share_pct, height=w, color=[C[9], C[3], C[0]][i], label=f"{p}年産平均")
    for yy, v in zip(y + (i - 1) * w, s.harvest_share_pct):
        if v >= 5:
            ax.text(v + 0.6, yy, f"{v:.0f}%", va="center", fontsize=8, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(NORTH_SOUTH); ax.invert_yaxis()
ax.set_xlabel("全国の収穫量に占める割合（%）")
ax.legend(frameon=False, loc="lower right", fontsize=9)
finish(fig, ax, "1960年代の産地は関東・東山と九州。今は北海道が6割を超える", SRC_CROP, grid="x")
save(fig, "fig4_region_share_then_now.png")
