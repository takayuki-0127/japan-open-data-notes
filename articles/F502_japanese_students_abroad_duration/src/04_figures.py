"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from common import ROOT

R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#8a63d2"]
INK, INK2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SRC = "出典：日本学生支援機構「日本人学生留学状況調査」（各年度、協定等に基づく留学と基づかない留学の合計）をもとに作成者が加工して作成"
META = {"Software": None}
comma = ticker.FuncFormatter(lambda v, p: f"{v:,.0f}")
P = ["m_lt1", "m1_3", "m3_6", "m6_12", "y1plus", "unknown"]
LAB = ["1か月未満", "1〜3か月", "3〜6か月", "6か月〜1年", "1年以上", "不明"]


def finish(fig, ax, title, src=SRC, pad=12):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=pad)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.012, src, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
by = pd.read_csv(R / "by_year.csv", index_col="year")

# ---- 図1：期間別の積み上げ ----
fig, ax = plt.subplots(figsize=(8.8, 5.2))
bottom = pd.Series(0, index=by.index, dtype=float)
cols = C[:5] + ["#a8a7a2"]
for k, lab, c in zip(P, LAB, cols):
    ax.bar(by.index, by[k], bottom=bottom, color=c, width=0.72, label=lab, edgecolor=BG, linewidth=1.0)
    bottom += by[k]
for y in [2009, 2018, 2020, 2024]:
    ax.text(y, by.at[y, "total"] + 1800, f"{int(by.at[y, 'total']):,}", ha="center", fontsize=8.8, color=INK)
ax.set_ylim(0, 128000)
ax.set_xticks(range(2009, 2025, 1))
ax.set_xticklabels([str(y) if y % 2 == 1 or y == 2024 else "" for y in range(2009, 2025)])
ax.set_xlabel("年度（留学を始めた年度）")
ax.set_ylabel("留学者（人）")
ax.yaxis.set_major_formatter(comma)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper left", ncol=3, fontsize=9.2)
finish(fig, ax, "留学者は2018年度の115,146人が最多。2024年度は91,054人（2018年度の79%）")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig1_total_by_period.png")

# ---- 図2：期間別の戻り（2018年度＝100） ----
rv, rv19 = m["recovery_vs_2018_pct"], m["recovery_vs_2019_pct"]
keys = ["total", "m_lt1", "m1_3", "m3_6", "m6_12", "y1plus"]
names = ["合計", "1か月未満", "1〜3か月", "3〜6か月", "6か月〜1年", "1年以上"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
yy = list(range(len(keys)))[::-1]
ax.barh([y + 0.19 for y in yy], [rv[k] for k in keys], height=0.36, color=C[0], label="2018年度＝100", edgecolor=BG, lw=1)
ax.barh([y - 0.19 for y in yy], [rv19[k] for k in keys], height=0.36, color=C[3], label="2019年度＝100", edgecolor=BG, lw=1)
for y, k in zip(yy, keys):
    ax.text(rv[k] + 1, y + 0.19, f"{rv[k]:.1f}", va="center", fontsize=8.8, color=INK)
    ax.text(rv19[k] + 1, y - 0.19, f"{rv19[k]:.1f}", va="center", fontsize=8.8, color=INK)
ax.axvline(100, color=INK2, lw=0.9, ls=":")
ax.set_yticks(yy)
ax.set_yticklabels(names)
ax.set_xlim(0, 112)
ax.set_xlabel("2024年度の留学者（基準の年度＝100）")
ax.grid(axis="x", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.065), ncol=2, fontsize=9.2)
finish(fig, ax, "どの期間も2018年度の75〜88%。短い留学だけが戻ったわけではない", pad=30)
fig.subplots_adjust(left=0.14, right=0.97, top=0.84, bottom=0.16)
save(fig, "fig2_recovery_by_period.png")

# ---- 図3：地域別の戻り（2018年度＝100） ----
REG = ["アジア", "中東", "アフリカ", "大洋州", "北米", "中南米", "欧州"]
rg = m["region"]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
x = range(len(REG))
ax.bar([i - 0.2 for i in x], [rg[g]["recovery_total_pct"] for g in REG], width=0.38, color=C[0], label="すべての期間", edgecolor=BG, lw=1)
ax.bar([i + 0.2 for i in x], [rg[g]["recovery_m3plus_pct"] for g in REG], width=0.38, color=C[2], label="3か月以上", edgecolor=BG, lw=1)
for i, g in zip(x, REG):
    ax.text(i - 0.2, rg[g]["recovery_total_pct"] + 1.5, f"{rg[g]['recovery_total_pct']:.0f}", ha="center", fontsize=8.6, color=INK)
    ax.text(i + 0.2, rg[g]["recovery_m3plus_pct"] + 1.5, f"{rg[g]['recovery_m3plus_pct']:.0f}", ha="center", fontsize=8.6, color=INK)
    ax.text(i, -13, f"2018年度\n{rg[g]['total_2018']:,}人", ha="center", va="top", fontsize=7.8, color=INK2)
ax.axhline(100, color=INK2, lw=0.9, ls=":")
ax.set_xticks(list(x))
ax.set_xticklabels(REG)
ax.set_ylim(0, 128)
ax.set_ylabel("2024年度の留学者（2018年度＝100）")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9.2)
finish(fig, ax, "北米は2018年度の65%。欧州の3か月以上の留学は2018年度を上回った（103%）")
fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=0.24)
save(fig, "fig3_region_recovery.png")

# ---- 図4：3か月以上の留学の行き先の割合 ----
mr = pd.read_csv(R / "m3plus_by_region.csv", index_col="year")
fig, ax = plt.subplots(figsize=(8.8, 5.2))
for g, c, dy in [("北米", C[0], 1.3), ("欧州", C[1], -1.3), ("アジア", C[2], 0), ("大洋州", C[3], 0)]:
    s = mr[f"{g}_share_pct"]
    ax.plot(s.index, s, color=c, lw=2.2, marker="o", ms=4.5, label=g)
    ax.text(2024.35, s.iloc[-1] + dy, f"{g} {s.iloc[-1]:.1f}%", va="center", fontsize=9, color=INK)
ax.axvspan(2019.5, 2021.5, color=GRID, alpha=0.6, lw=0)
ax.text(2020.5, 47, "2020・21年度は\n人数がごく少ない", ha="center", fontsize=8.3, color=INK2)
ax.set_xlim(2008.5, 2027)
ax.set_xticks(range(2009, 2025, 3))
ax.set_ylim(0, 52)
ax.set_xlabel("年度")
ax.set_ylabel("3か月以上の留学者に占める割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="lower left", ncol=4, fontsize=9.2)
finish(fig, ax, "3か月以上の留学の行き先は、北米が44%（2013年度）から32%に下がり、欧州が31%に")
fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=0.15)
save(fig, "fig4_m3plus_share_region.png")
print("ok")
