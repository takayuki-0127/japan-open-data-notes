"""04_figures.py：図4枚（PNG）。日付などのメタデータは入れない。"""
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
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#9a9893"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：厚生労働省「賃金構造基本統計調査」（遡及集計、令和元年・令和2年の表、時系列表）をもとに作成者が加工して作成"
META = {"Software": None}
SIZE_LAB = {"計": "10人以上計", "1000+": "1,000人以上", "100-999": "100〜999人", "10-99": "10〜99人"}


def finish(fig, title):
    fig.suptitle(title, x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.text(0.01, 0.012, SRC, fontsize=7.4, color=INK2)


# 図1：所定内給与額（男女計）、古い方法と新しい方法、2006〜2019年と2020年
ts = pd.read_csv(R / "timeseries_old_new.csv")
m = json.load(open(R / "main.json", encoding="utf-8"))
G = pd.read_csv(R / "requestion_2020_growth.csv")
fig, ax = plt.subplots(figsize=(9.2, 4.8))
ax.plot(ts["year"], ts["old_計"], color=GRAY, lw=2, marker="o", ms=4, label="古い方法（2019年までの公表値）")
ax.plot(ts["year"], ts["new_計"], color=BLUE, lw=2, marker="o", ms=4, label="新しい方法（2020年と同じ方法で集計し直した値）")
v20 = float(G[(G["sex"] == "計") & (G["size"] == "計")]["y2020"].iloc[0])
ax.scatter([2020], [v20], color=ORANGE, s=40, zorder=3, label="2020年（新しい方法）")
for y in [2006, 2019]:
    r = ts[ts["year"] == y].iloc[0]
    ax.annotate(f"差 {r['diff_計_pct']:+.2f}%", (y, r["new_計"]), xytext=(0, -22), textcoords="offset points", ha="center", fontsize=9, color=BLUE)
ax.set_ylabel("所定内給与額（千円、6月分）"); ax.set_xlabel("年")
ax.set_ylim(285, 315)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9)
finish(fig, "所定内給与額（一般労働者、男女計）：古い方法と新しい方法の差は0.8%以内")
fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.17)
fig.savefig(F / "fig1_level_old_new.png", dpi=150, metadata=META); plt.close(fig)

# 図2：産業別、2019年の新旧の差（賃金と労働者数）
I = pd.read_csv(R / "diff_2019_industry.csv").sort_values("industry", ascending=False)
tot = m["total_2019"]
lab = list(I["name"]) + []
fig, axes = plt.subplots(1, 2, figsize=(10, 6.2), sharey=True)
y = np.arange(len(I))
axes[0].barh(y, I["diff_shoteinai_pct"], color=BLUE, height=0.65)
axes[0].axvline(tot["shoteinai"]["diff_pct"], color=ORANGE, lw=1.2, ls="--")
axes[0].text(tot["shoteinai"]["diff_pct"], len(I) - 0.3, f"産業計 {tot['shoteinai']['diff_pct']:+.2f}%", color=ORANGE, fontsize=8.5, ha="right")
axes[0].set_xlim(-4, 4); axes[0].axvline(0, color=INK2, lw=0.6)
axes[0].set_title("所定内給与額の差（％）", fontsize=10.5, color=INK)
axes[1].barh(y, I["diff_workers_pct"], color=GRAY, height=0.65)
axes[1].axvline(tot["workers"]["diff_pct"], color=ORANGE, lw=1.2, ls="--")
axes[1].text(tot["workers"]["diff_pct"] + 1, len(I) - 0.3, f"産業計 +{tot['workers']['diff_pct']:.1f}%", color=ORANGE, fontsize=8.5)
axes[1].set_title("推計の労働者数の差（％）", fontsize=10.5, color=INK)
axes[0].set_yticks(y); axes[0].set_yticklabels(I["name"], fontsize=8.8)
for a in axes:
    a.grid(axis="x", color=GRID, lw=0.8); a.set_axisbelow(True)
fig.text(0.5, 0.055, "差＝新しい方法 ÷ 古い方法 − 1。2019年、男女計・企業規模10人以上。産業は分類の記号の順（医療・福祉は扱わない話題のため除く）", ha="center", fontsize=8, color=INK2)
finish(fig, "2019年：産業別の賃金の差は±2.4%以内、推計の労働者数は8〜86%多い")
fig.subplots_adjust(left=0.24, right=0.98, top=0.89, bottom=0.13, wspace=0.08)
fig.savefig(F / "fig2_industry_wage_vs_workers.png", dpi=150, metadata=META); plt.close(fig)

# 図3：企業規模別、賃金の差と人数の割合
S = pd.read_csv(R / "diff_2019_sex_size.csv"); S = S[S["sex"] == "計"].set_index("size")
q = json.load(open(R / "requestion.json", encoding="utf-8"))["size_shift_share"]
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6))
zs = ["1000+", "100-999", "10-99"]
x = np.arange(len(zs))
vals = [S.loc[z, "diff_shoteinai_pct"] for z in zs]
axes[0].bar(x, vals, color=[BLUE if v > 0 else ORANGE for v in vals], width=0.55)
for i, v in enumerate(vals):
    axes[0].text(i, v + (0.06 if v > 0 else -0.16), f"{v:+.2f}%", ha="center", fontsize=9)
axes[0].axhline(0, color=INK2, lw=0.6)
axes[0].set_ylim(-1.6, 1.4)
axes[0].set_xticks(x); axes[0].set_xticklabels([SIZE_LAB[z] for z in zs])
axes[0].set_title("所定内給与額の差（新÷旧−1、％）", fontsize=10.5, color=INK)
w = 0.38
axes[1].bar(x - w / 2, [q["share_old"][z] for z in zs], w, color=GRAY, label="古い方法")
axes[1].bar(x + w / 2, [q["share_new"][z] for z in zs], w, color=BLUE, label="新しい方法")
for i, z in enumerate(zs):
    axes[1].text(i - w / 2, q["share_old"][z] + 0.5, f"{q['share_old'][z]:.1f}", ha="center", fontsize=8.5, color=INK2)
    axes[1].text(i + w / 2, q["share_new"][z] + 0.5, f"{q['share_new'][z]:.1f}", ha="center", fontsize=8.5, color=INK)
axes[1].set_xticks(x); axes[1].set_xticklabels([SIZE_LAB[z] for z in zs])
axes[1].set_title("労働者の人数の割合（％）", fontsize=10.5, color=INK)
axes[1].legend(frameon=False, fontsize=9, loc="upper right"); axes[1].set_ylim(0, 45)
for a in axes:
    a.grid(axis="y", color=GRID, lw=0.8); a.set_axisbelow(True)
finish(fig, "2019年：1,000人以上は下がり10〜99人は上がる。10〜99人の人数の割合が増え、全体を押し下げる")
fig.subplots_adjust(left=0.07, right=0.98, top=0.84, bottom=0.15, wspace=0.18)
fig.savefig(F / "fig3_size_wage_and_share.png", dpi=150, metadata=META); plt.close(fig)

# 図4（問い直し）：2019年→2020年の伸び、比べる2019年の値で変わる
fig, ax = plt.subplots(figsize=(9.2, 4.6))
cases = [("計", "計"), ("計", "1000+"), ("計", "100-999"), ("計", "10-99"), ("男", "1000+"), ("女", "1000+")]
labs = ["男女計\n10人以上計", "男女計\n1,000人以上", "男女計\n100〜999人", "男女計\n10〜99人", "男\n1,000人以上", "女\n1,000人以上"]
x = np.arange(len(cases))
go = [float(G[(G["sex"] == s) & (G["size"] == z)]["growth_vs_old"].iloc[0]) for s, z in cases]
gn = [float(G[(G["sex"] == s) & (G["size"] == z)]["growth_vs_new"].iloc[0]) for s, z in cases]
ax.bar(x - 0.2, go, 0.38, color=GRAY, label="2019年の古い方法の値と比べる")
ax.bar(x + 0.2, gn, 0.38, color=BLUE, label="2019年の新しい方法の値と比べる")
for i, (a, b) in enumerate(zip(go, gn)):
    ax.text(i - 0.2, a + (0.06 if a >= 0 else -0.2), f"{a:+.2f}", ha="center", fontsize=8.3, color=INK2)
    ax.text(i + 0.2, b + (0.06 if b >= 0 else -0.2), f"{b:+.2f}", ha="center", fontsize=8.3, color=INK)
ax.axhline(0, color=INK2, lw=0.6)
ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=9)
ax.set_ylabel("2019年→2020年の所定内給与額の伸び（％）")
ax.set_ylim(-2.0, 2.8)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9, loc="upper left")
finish(fig, "2020年の伸びは、比べる2019年の値で最大1.3ポイント変わる（男・1,000人以上は符号が逆）")
fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.2)
fig.savefig(F / "fig4_growth_2020_by_base.png", dpi=150, metadata=META); plt.close(fig)
print("ok")
