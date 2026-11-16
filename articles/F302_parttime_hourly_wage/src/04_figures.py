"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
BLUE, ORANGE, GRAY, INK2 = "#2a78d6", "#eb6834", "#9a9893", "#52514e"
SRC = "出典：厚生労働省「毎月勤労統計調査」（事業所規模5人以上、年平均）をもとに作成者が加工。時給＝所定内給与÷所定内労働時間"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

lv = pd.read_csv(RES / "tl_hourly_by_year.csv").set_index("year")
# 図1：時給の推移（2015年＝100）
fig, ax = plt.subplots(figsize=(8, 4.9)); fig.subplots_adjust(left=0.09, right=0.86, top=0.83, bottom=0.14)
for col, c, nm in (("part", BLUE, "パートタイム労働者"), ("general", GRAY, "一般労働者")):
    s = 100 * lv[col] / lv.loc[2015, col]
    ax.plot(lv.index, s, color=c, lw=2, marker="o", ms=3.5)
    ax.text(2025.3, s.iloc[-1], f"{nm}\n{s.iloc[-1]:.1f}（{lv[col].iloc[-1]:,.0f}円）", fontsize=8.5, va="center")
ax.axhline(100, color="#cfcdc8", lw=0.8); ax.set_xlim(2009.5, 2025.5); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.set_ylabel("時給（2015年＝100）"); ax.set_xlabel("年")
fig.suptitle("パートの時給は、一般労働者より速く上がった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"2015→2025年の伸び（対数差）：パート +{m['main']['part_growth']:.1f}%、一般 +{m['main']['general_growth']:.1f}%。一般に対するパートの時給の比 {m['hourly_2015']['ratio_part_to_general']:.3f} → {m['hourly_2025']['ratio_part_to_general']:.3f}", fontsize=9, color=INK2)
save(fig, "fig1_hourly_index.png")

# 図2：時給の伸び ＝ 月給の伸び ＋ 時間の縮み
fig, ax = plt.subplots(figsize=(8, 4.4)); fig.subplots_adjust(left=0.2, right=0.95, top=0.8, bottom=0.2)
y = [1, 0]; labs = ["パートタイム労働者", "一般労働者"]
mp = [q["part"]["monthly_pay_growth"], q["general"]["monthly_pay_growth"]]
hs = [q["part"]["hours_shrink"], q["general"]["hours_shrink"]]
ax.barh(y, mp, color=BLUE, height=0.5, label="月給（所定内給与）の伸び")
ax.barh(y, hs, left=mp, color=ORANGE, height=0.5, label="所定内労働時間の縮み", edgecolor="#fcfcfb", linewidth=2)
for yi, a, b in zip(y, mp, hs):
    ax.text(a / 2, yi, f"{a:.1f}", ha="center", va="center", color="white", fontsize=10)
    ax.text(a + b / 2, yi, f"{b:.1f}", ha="center", va="center", color="white", fontsize=10)
    ax.text(a + b + 0.4, yi, f"＝ 時給 +{a + b:.1f}", va="center", fontsize=10)
ax.set_yticks(y); ax.set_yticklabels(labs); ax.set_xlim(0, 34); ax.set_xlabel("2015→2025年の伸び（%、対数差）")
ax.legend(frameon=False, fontsize=8.5, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2)
fig.suptitle("時給の差の6割は、パートの働く時間が短くなった分", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.87, f"時給の差 {q['gap_hourly']:.1f}ポイント ＝ 月給の伸びの差 {q['gap_from_monthly_pay']:.1f} ＋ 時間の縮みの差 {q['gap_from_hours']:.1f}", fontsize=9, color=INK2)
save(fig, "fig2_hourly_decomposition.png")

# 図3：産業別（産業分類の順）
b = pd.read_csv(RES / "by_industry_2015_2025.csv")
fig, ax = plt.subplots(figsize=(8, 6)); fig.subplots_adjust(left=0.22, right=0.96, top=0.86, bottom=0.11)
yy = np.arange(len(b))[::-1]
for yi, r in zip(yy, b.itertuples()):
    ax.plot([r.general, r.part], [yi, yi], color="#cfcdc8", lw=2, zorder=1)
ax.scatter(b.general, yy, color=GRAY, s=45, zorder=2, label="一般労働者")
ax.scatter(b.part, yy, color=BLUE, s=45, zorder=3, label="パートタイム労働者")
ax.set_yticks(yy); ax.set_yticklabels(b.name, fontsize=9); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("時給の伸び 2015→2025年（%、対数差）"); ax.grid(axis="x", color="#e6e5e1", lw=0.6)
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.suptitle(f"16産業のうち{m['main']['n_ind_part_faster']}産業で、パートの時給のほうが速く上がった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.905, "産業は日本標準産業分類の順。鉱業はパートの人数が少なく、値が大きくぶれる", fontsize=9, color=INK2)
save(fig, "fig3_by_industry.png")

# 図4：年ごとの伸びの差
g = lv.loc[2011:2025, "yoy_gap"]
fig, ax = plt.subplots(figsize=(8, 4.6)); fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.14)
ax.bar(g.index, g.values, color=[BLUE if v > 0 else ORANGE for v in g.values], width=0.6)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(range(2011, 2026, 2))
for a, b_, v in ((2015, 2019, m["yoy_gap_2015_2019"]), (2023, 2025, m["yoy_gap_2023_2025"])):
    ax.plot([a - 0.35, b_ + 0.35], [v, v], color="#0b0b0b", lw=1.2, ls="--")
ax.set_ylabel("前年比の差（パート − 一般、%pt）"); ax.set_xlabel("年"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle(f"パートが上回った年は15年のうち{m['n_years_part_faster_2011_2025']}年。最近だけの話ではない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"時給の前年比の差。破線は平均：2015〜19年 {m['yoy_gap_2015_2019']:+.2f}、2023〜25年 {m['yoy_gap_2023_2025']:+.2f}（%pt）で、ほぼ同じ", fontsize=9, color=INK2)
save(fig, "fig4_yoy_gap.png")
print("ok")
