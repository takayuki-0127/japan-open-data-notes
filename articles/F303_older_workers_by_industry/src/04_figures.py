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
SRC = "出典：総務省「労働力調査」基本集計 年平均（第II-2-1表）をもとに作成者が加工。医療・福祉、公務、分類不能の産業は除く"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
t = pd.read_csv(RES / "decomp_2018_2025.csv")  # 産業分類の順（col の順）
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：産業ごとの60歳以上の増減（産業分類の順）
fig, ax = plt.subplots(figsize=(8, 6.2)); fig.subplots_adjust(left=0.28, right=0.95, top=0.86, bottom=0.11)
yy = np.arange(len(t))[::-1]
ax.barh(yy, t.d_old, color=[BLUE if v > 0 else ORANGE for v in t.d_old], height=0.6)
for yi, v in zip(yy, t.d_old):
    ax.text(v + (0.6 if v >= 0 else -0.6), yi, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
ax.set_yticks(yy); ax.set_yticklabels(t.industry, fontsize=9); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-36, 30); ax.set_xlabel("60歳以上の就業者の増減 2018→2025年（万人）"); ax.grid(axis="x", color="#e6e5e1", lw=0.6)
fig.suptitle("60歳以上の増加は多くの産業に散らばり、農業・林業では減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.905, f"対象17産業の計 {m['main']['d_old_total']:+.0f}万人（増えた産業の計 +{m['main']['gross_increase']:.0f}、減った産業の計 {m['main']['gross_decrease']:.0f}）。産業は分類の順", fontsize=9, color=INK2)
save(fig, "fig1_change_by_industry.png")

# 図2：分解
mm = m["main"]
items = [("産業の規模の変化\n（割合は2018年のまま）", mm["scale_total"]), ("産業の中で60歳以上の\n割合が上がった分", mm["within_share_total"]),
         ("交差の項", mm["interaction_total"]), ("合計", mm["d_old_total"])]
fig, ax = plt.subplots(figsize=(7.8, 4.8)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.2)
cols = [ORANGE if v < 0 else BLUE for _, v in items[:3]] + [GRAY]
bars = ax.bar([i for i, _ in items], [v for _, v in items], color=cols, width=0.55)
for bb, (_, v) in zip(bars, items):
    ax.text(bb.get_x() + bb.get_width() / 2, v + (1.5 if v >= 0 else -4), f"{v:+.1f}", ha="center", fontsize=10)
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylabel("万人"); ax.set_ylim(-25, 75); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("増えた分は、産業の中で年齢が上に寄った分だった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.87, "60歳以上の就業者の増減（2018→2025年、対象17産業の計）の分解", fontsize=9, color=INK2)
save(fig, "fig2_shift_share.png")

# 図3：産業の伸びと60歳以上の割合の変化
fig, ax = plt.subplots(figsize=(7.6, 5.4)); fig.subplots_adjust(left=0.11, right=0.97, top=0.85, bottom=0.13)
gx = 100 * np.log(t.N_end / t.N_start); gy = t.share_end_pct - t.share_start_pct
ok = t.N_start >= 10
ax.scatter(gx[ok], gy[ok], s=20 + t.N_start[ok] / 4, color=BLUE, alpha=0.6, edgecolor="#fcfcfb")
OFF = {"建設業": (-6, -12, "right"), "情報通信業": (-6, 6, "right"), "製造業": (6, 4, "left")}
for xi, yi, nm, o in zip(gx, gy, t.industry, ok):
    if o:
        dx, dy, ha = OFF.get(nm, (5, 3, "left"))
        ax.annotate(nm, (xi, yi), xytext=(dx, dy), textcoords="offset points", fontsize=7.5, color="#0b0b0b", ha=ha)
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("産業の就業者の伸び 2018→2025年（%、対数差）"); ax.set_ylabel("60歳以上の割合の変化（ポイント）"); ax.grid(color="#e6e5e1", lw=0.6)
fig.suptitle("人が減った産業ほど年齢が上に寄った、とは言えない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.9, f"順位相関 {mm['spearman_growth_vs_dshare']:+.2f}（p={mm['spearman_p']:.2f}、17産業）。図は就業者10万人以上の産業。円の大きさは2018年の就業者数", fontsize=9, color=INK2)
save(fig, "fig3_growth_vs_share.png")

# 図4：55〜59歳 → 5年後の60〜64歳 の比
r = pd.read_csv(RES / "requestion_cohort.csv")
w = r.pivot(index="industry", columns="period", values="ratio")
order = [x for x in t.industry if x in q["by_industry_big"]] + ["対象17産業の計"]
w = w.loc[order]
fig, ax = plt.subplots(figsize=(8, 6)); fig.subplots_adjust(left=0.3, right=0.95, top=0.86, bottom=0.11)
yy = np.arange(len(w))[::-1]
for yi, (_, row) in zip(yy, w.iterrows()):
    ax.plot([row["2013-2018"], row["2020-2025"]], [yi, yi], color="#cfcdc8", lw=2, zorder=1)
ax.scatter(w["2013-2018"], yy, color=GRAY, s=40, zorder=2, label="2013年55〜59歳 → 2018年60〜64歳")
ax.scatter(w["2020-2025"], yy, color=BLUE, s=40, zorder=3, label="2020年55〜59歳 → 2025年60〜64歳")
ax.axvline(1, color=INK2, lw=0.8, ls="--")
ax.set_yticks(yy); ax.set_yticklabels(w.index, fontsize=9); ax.set_xlabel("5年後の60〜64歳の人数 ÷ 5年前の55〜59歳の人数")
ax.legend(frameon=False, fontsize=8.5, loc="lower right"); ax.grid(axis="x", color="#e6e5e1", lw=0.6)
fig.suptitle("60歳をまたいで残る割合は、全体ではほとんど変わらない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.905, f"対象17産業の計 {q['total_2013_2018']:.3f} → {q['total_2020_2025']:.3f}。55〜59歳が10万人以上の産業のうち、上がったのは{q['n_big']}産業中{q['n_big_ratio_up']}", fontsize=9, color=INK2)
save(fig, "fig4_cohort_ratio.png")
print("ok")
