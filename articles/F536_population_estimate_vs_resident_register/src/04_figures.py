"""04_figures.py：図4枚（PNG）。日付などのメタデータは入れない。都道府県は北から南の順。"""
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
BLUE, ORANGE, GRAY, GREEN = "#2a78d6", "#eb6834", "#9a9893", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省統計局「人口推計」、総務省「住民基本台帳に基づく人口、人口動態及び世帯数調査」をもとに作成者が加工して作成"
META = {"Software": None}
NOTE = "ずれ＝住民基本台帳の人口（1月1日の値を10月1日に按分）÷ 人口推計（10月1日）− 1"


def finish(fig, title, note=NOTE):
    fig.suptitle(title, x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.text(0.01, 0.045, note, fontsize=7.8, color=INK2)
    fig.text(0.01, 0.012, SRC, fontsize=7.4, color=INK2)


NAT = pd.read_csv(R / "national_gap.csv")
# 図1：全国のずれ
fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.8))
ax = axes[0]
ax.plot(NAT["year"], NAT["gap_total_pct"], color=BLUE, lw=2, marker="o", ms=4, label="総人口")
ax.plot(NAT["year"], NAT["gap_japanese_pct"], color=GRAY, lw=2, marker="o", ms=4, label="日本人")
for y in [2014, 2024]:
    r = NAT[NAT["year"] == y].iloc[0]
    ax.annotate(f"{r['gap_total_pct']:.2f}%\n（{r['gap_total'] / 1e4:.0f}万人）", (y, r["gap_total_pct"]), xytext=(0, 10), textcoords="offset points", ha="center", fontsize=8.5, color=BLUE)
ax.set_ylim(0, 1.05); ax.set_title("総人口・日本人のずれ（％）", fontsize=10.5, color=INK)
ax.legend(frameon=False, fontsize=9, loc="lower left")
ax = axes[1]
ax.bar(NAT["year"], NAT["gap_foreign_pct"], color=ORANGE, width=0.7)
for r in NAT.itertuples():
    ax.text(r.year, r.gap_foreign_pct + 0.4, f"{r.gap_foreign_pct:.1f}", ha="center", fontsize=8, color=INK2)
ax.set_title("外国人のずれ（％、総人口 − 日本人）", fontsize=10.5, color=INK)
for a in axes:
    a.set_xlabel("年（人口推計の10月1日）"); a.set_xticks(range(2014, 2025, 2))
    a.grid(axis="y", color=GRID, lw=0.8); a.set_axisbelow(True)
finish(fig, "全国：住民基本台帳はどの年も多い。ずれは0.82%から0.5%前後に縮み、縮んだのは外国人の分")
fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.2, wspace=0.18)
fig.savefig(F / "fig1_national_gap.png", dpi=150, metadata=META); plt.close(fig)

# 図2：都道府県のずれ（2024年、棒）と2020年（点）、北から南
P = pd.read_csv(R / "pref_gap.csv"); P = P[P["kind"] == "total"]
p24 = P[P["year"] == 2024].sort_values("pref"); p20 = P[P["year"] == 2020].sort_values("pref")
fig, ax = plt.subplots(figsize=(10, 8.6))
y = np.arange(len(p24))[::-1]
cols = [BLUE if v > 0 else ORANGE for v in p24["gap_pct"]]
ax.barh(y, p24["gap_pct"], color=cols, height=0.7, label="2024年")
ax.scatter(p20["gap_pct"], y, color=INK, s=12, zorder=3, label="2020年（国勢調査の年）")
ax.set_yticks(y); ax.set_yticklabels(p24["name"], fontsize=8.2)
ax.axvline(0, color=INK2, lw=0.8)
# 地方の区切り（地方名は、その地方の行の真ん中に置く）
prev = None
for yy, rg in zip(y, p24["region"]):
    if rg != prev and prev is not None:
        ax.axhline(yy + 0.5, color=GRID, lw=1.0)
    prev = rg
for rg in p24["region"].unique():
    ys = y[(p24["region"] == rg).values]
    ax.text(3.05, ys.mean(), rg, fontsize=8.5, color=INK2, va="center")
ax.set_xlim(-2.2, 3.6)
ax.set_xlabel("ずれ（％）。プラスは住民基本台帳の方が多い")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9, loc="lower right")
finish(fig, "都道府県（北から南）：42道府県で住民基本台帳が多く、5都府県で少ない（2024年）")
fig.subplots_adjust(left=0.12, right=0.97, top=0.94, bottom=0.12)
fig.savefig(F / "fig2_pref_gap.png", dpi=150, metadata=META); plt.close(fig)

# 図3：年齢別のずれ（全国）
A = pd.read_csv(R / "age_gap.csv")
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85+"]
LAB = [a.replace("-", "〜") + "歳" if a != "85+" else "85歳以上" for a in AGES]
fig, ax = plt.subplots(figsize=(9.8, 4.8))
for t, c in [(2020, GRAY), (2024, BLUE)]:
    s = A[(A["year"] == t) & (A["pref"] == 0)].set_index("age").loc[AGES]
    ax.plot(range(len(AGES)), s["gap_pct"], color=c, lw=2, marker="o", ms=4, label=f"{t}年" + ("（国勢調査の年）" if t == 2020 else ""))
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(range(len(AGES))); ax.set_xticklabels(LAB, rotation=45, ha="right", fontsize=8.5)
ax.set_ylabel("ずれ（％）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9)
finish(fig, "年齢別（全国）：子どもと30〜40代は住民基本台帳が多く、80歳以上は少ない")
fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.27)
fig.savefig(F / "fig3_age_gap.png", dpi=150, metadata=META); plt.close(fig)

# 図4（問い直し）：都道府県の総人口のずれと20〜24歳のずれ（2024年）
Yg = pd.read_csv(R / "requestion_young.csv"); Yg = Yg[Yg["year"] == 2024]
q = json.load(open(R / "requestion.json", encoding="utf-8"))["2024"]
fig, ax = plt.subplots(figsize=(9.2, 5.6))
neg = Yg["gap_total_pct"] < 0
ax.scatter(Yg.loc[~neg, "gap_20_24_pct"], Yg.loc[~neg, "gap_total_pct"], color=BLUE, s=26, label="住民基本台帳が多い道府県")
ax.scatter(Yg.loc[neg, "gap_20_24_pct"], Yg.loc[neg, "gap_total_pct"], color=ORANGE, s=34, label="住民基本台帳が少ない都府県")
for r in Yg[neg].itertuples():
    ax.annotate(r.name, (r.gap_20_24_pct, r.gap_total_pct), xytext=(5, -3), textcoords="offset points", fontsize=8.5, color=ORANGE)
ax.axhline(0, color=INK2, lw=0.6); ax.axvline(0, color=INK2, lw=0.6)
ax.set_xlabel("20〜24歳のずれ（％）"); ax.set_ylabel("総人口のずれ（％）")
ax.text(0.98, 0.05, f"相関 {q['corr_total_vs_20_24']:.2f}", transform=ax.transAxes, ha="right", fontsize=10, color=INK)
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9, loc="upper left")
finish(fig, "20〜24歳のずれが大きい県ほど、総人口のずれも大きい（2024年、47都道府県）")
fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.18)
fig.savefig(F / "fig4_young_vs_total.png", dpi=150, metadata=META); plt.close(fig)
print("ok")
