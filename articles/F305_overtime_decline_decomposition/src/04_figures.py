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
BLUE, ORANGE, GRAY, INK2, GREEN = "#2a78d6", "#eb6834", "#9a9893", "#52514e", "#1baf7a"
SRC = "出典：厚生労働省「毎月勤労統計調査」（一般労働者）をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
def save(fig, name, src=SRC):
    fig.text(0.01, 0.01, src, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：総時間・日数・1日あたり（2015年＝100）
y = pd.read_csv(RES / "tl_general_by_year.csv").set_index("year")
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.09, right=0.8, top=0.83, bottom=0.14)
for col, c, nm in (("total_hours", BLUE, "総実労働時間"), ("days", ORANGE, "出勤日数"), ("per_day", GRAY, "1日あたりの時間")):
    s = 100 * y[col] / y.loc[2015, col]
    ax.plot(y.index, s, color=c, lw=2.2, marker="o", ms=3.5)
    off = {"総実労働時間": 0.35, "出勤日数": -0.35}.get(nm, 0)
    ax.text(2025.3, s.iloc[-1] + off, f"{nm} {s.iloc[-1]:.1f}", fontsize=8.5, va="center")
ax.axhline(100, color="#cfcdc8", lw=0.8); ax.set_ylabel("2015年＝100"); ax.set_xlabel("年"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.set_xlim(2011.5, 2025.5)
h2 = m["H2"]
fig.suptitle("働く時間が減ったのは、出勤する日が減ったから", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"一般労働者、調査産業計（5人以上）。2015→2025年：総時間 {h2['total_logpct']:+.1f}%、日数 {h2['days_logpct']:+.1f}%、1日あたり {h2['perday_logpct']:+.1f}%（対数差）", fontsize=9, color=INK2)
save(fig, "fig1_hours_days_perday.png")

# 図2：減った時間の中身
fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.5)); fig.subplots_adjust(left=0.08, right=0.97, top=0.8, bottom=0.17, wspace=0.35)
ax = axes[0]
ax.bar(["所定内", "所定外（残業）"], [h2["sched_change_h"], h2["ot_change_h"]], color=[GRAY, BLUE], width=0.55)
for i, v in enumerate([h2["sched_change_h"], h2["ot_change_h"]]):
    ax.text(i, v - 0.4, f"{v:.1f}時間", ha="center", va="top", fontsize=9.5)
ax.set_ylim(-8.5, 0.5); ax.axhline(0, color=INK2, lw=0.8); ax.set_title("月あたりの減り（時間）", fontsize=10, loc="left"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax = axes[1]
ax.bar(["所定内", "所定外（残業）"], [h2["sched_pct"], h2["ot_pct"]], color=[GRAY, BLUE], width=0.55)
for i, v in enumerate([h2["sched_pct"], h2["ot_pct"]]):
    ax.text(i, v - 0.4, f"{v:.1f}%", ha="center", va="top", fontsize=9.5)
ax.set_ylim(-11, 0.5); ax.axhline(0, color=INK2, lw=0.8); ax.set_title("減った割合（%）", fontsize=10, loc="left"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("残業は割合では大きく減ったが、時間で見ると減った分の大半は所定内", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.875, f"一般労働者、2015→2025年。総時間 {h2['total_start']:.1f}→{h2['total_end']:.1f}時間（{h2['total_change_h']:.1f}時間）", fontsize=9, color=INK2)
save(fig, "fig2_sched_vs_ot.png")

# 図3：規模の差（500人以上 − 5〜29人）
mm = pd.read_csv(ROOT / "data" / "hours_monthly_size.csv", dtype={"size": str}); mm["ym"] = mm.year * 12 + mm.month - 1
def s_(size): return mm[(mm["size"] == size) & (mm.type == 1)].set_index("ym").sort_index().ot_hours
D = 100 * (np.log(s_("4")) - np.log(s_("9")))
D = D.loc[2016 * 12:2021 * 12 + 11]
yoy = D - D.shift(12)
fig, ax = plt.subplots(figsize=(8.4, 4.8)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.14)
xx = D.index / 12.0
ax.plot(xx, D.values, color=BLUE, lw=1.6)
for ev, lab, yt in ((2019 * 12 + 3, "2019年4月\n大企業に上限", 22.5), (2020 * 12 + 3, "2020年4月\n中小企業に上限", 21.0)):
    ax.axvline(ev / 12.0, color=ORANGE, lw=1.2, ls="--"); ax.text(ev / 12.0 + 0.04, yt, lab, fontsize=8, color=ORANGE, va="bottom")
ax.set_ylabel("所定外労働時間の差（%、対数差×100）"); ax.set_xlabel("年"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
h1 = m["H1"]
fig.suptitle("大きな事業所で先に残業が減った形は、はっきりしない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"一般労働者の所定外労働時間：事業所規模500人以上 − 5〜29人。差の差 {h1['pct']:+.1f}%（p={h1['p']:.2f}）、対照を30〜99人にすると {m['robustness_h1'][1]['pct']:+.1f}%", fontsize=9, color=INK2)
save(fig, "fig3_size_gap.png")

# 図4：産業ごとの分解（産業分類の順）
t = pd.read_csv(RES / "requestion_by_industry.csv")
fig, ax = plt.subplots(figsize=(8, 6.2)); fig.subplots_adjust(left=0.22, right=0.96, top=0.83, bottom=0.11)
yy_ = np.arange(len(t))[::-1]
ax.scatter(t.days_logpct, yy_, color=ORANGE, s=45, label="出勤日数", zorder=3)
ax.scatter(t.perday_logpct, yy_, color=GRAY, s=45, label="1日あたりの時間", zorder=3)
ax.scatter(t.total_logpct, yy_, color=BLUE, marker="|", s=200, label="総実労働時間", zorder=4)
ax.axvline(0, color=INK2, lw=0.8); ax.set_yticks(yy_); ax.set_yticklabels(t.name, fontsize=9)
ax.set_xlabel("2015→2025年の変化（%、対数差）"); ax.grid(axis="x", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
fig.suptitle(f"16産業すべてで出勤日数が減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.905, f"1日あたりの時間が減ったのは{q['n_perday_down']}産業。日数の変化の中央値 {q['median_days_logpct']:+.1f}%、1日あたり {q['median_perday_logpct']:+.1f}%。産業は分類の順", fontsize=9, color=INK2)
save(fig, "fig4_by_industry.png")
print("ok")
