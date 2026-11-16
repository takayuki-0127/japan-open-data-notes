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
SRC = "出典：総務省「消費者物価指数」（2025年基準、全国）、厚生労働省「毎月勤労統計調査」（飲食店、5人以上）をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
M = pd.read_csv(RES / "monthly_yoy.csv", index_col=0)
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)
x = M[(M.year >= 2010)]
xx = x.year + (x.month - 1) / 12

# 図1：前年比の推移
fig, ax = plt.subplots(figsize=(8.6, 5)); fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.14)
ax.plot(xx, x.y_cpi_eatout, color=BLUE, lw=2, label="外食（消費者物価）")
ax.plot(xx, x.y_cpi_processed_food, color=ORANGE, lw=1.8, label="食料工業製品（消費者物価）")
ax.plot(xx, x.y_wage_restaurant, color=GREEN, lw=1.8, label="飲食店の1時間あたり所定内給与（12か月平均）")
for a, b in ((2014 + 3 / 12, 2015 + 2 / 12), (2019 + 9 / 12, 2020 + 8 / 12)):
    ax.axvspan(a, b, color="#f0efec", lw=0)
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylabel("前年同月比（%、対数差）"); ax.set_xlabel("年"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.set_xticks(range(2010, 2027, 2)); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
fig.suptitle("外食の値上がりは、食材の値上がりと一緒に動いてきた", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, "灰色の帯は消費税率の変更の影響がある期間（回帰から除いた）", fontsize=9, color=INK2)
save(fig, "fig1_yoy_lines.png")

# 図2：2021年12月→2026年9月の外食の上昇の割り当て
h3 = m["H3"]
items = [("外食の上昇", h3["eatout_rise"]), ("食料工業製品の分", h3["contrib_food"]), ("時給の分", h3["contrib_wage"]),
         ("一定の上昇（定数）", h3["contrib_const"]), ("説明できない分", h3["residual"])]
fig, ax = plt.subplots(figsize=(8, 4.8)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.18)
cols = [BLUE, ORANGE, GREEN, GRAY, "#cfcdc8"]
bars = ax.bar([i for i, _ in items], [v for _, v in items], color=cols, width=0.6)
for bb, (_, v) in zip(bars, items): ax.text(bb.get_x() + bb.get_width() / 2, v + 0.3, f"{v:.1f}", ha="center", fontsize=10)
ax.set_ylabel("2021年12月→2026年9月（対数差×100）"); ax.set_ylim(0, 20); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
plt.setp(ax.get_xticklabels(), fontsize=9)
fig.suptitle("外食の上昇17.2のうち、食材の分が9.2、時給の分は1.4", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"前年比の回帰（ラグ6か月）の係数で割り当てた。同じ期間に食料工業製品は +{h3['processed_food_rise']:.1f}、飲食店の時給は +{h3['wage_rise']:.1f}", fontsize=9, color=INK2)
save(fig, "fig2_contributions.png")

# 図3：時給のラグと係数
t = pd.read_csv(RES / "requestion_wage_lags.csv")
fig, ax = plt.subplots(figsize=(8, 4.8)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.14)
ax.errorbar(t.wage_lag, t.b_wage, yerr=[t.b_wage - t.lo, t.hi - t.b_wage], fmt="o", color=GREEN, ecolor=GREEN, elinewidth=2, capsize=0, ms=7)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(t.wage_lag)
ax.set_xlabel("飲食店の時給の前年比を何か月前の値にしたか"); ax.set_ylabel("外食の前年比への係数（点と95%区間）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("時給が効くのは、1年半〜2年遅れで、大きさも小さい", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"食料工業製品はラグ3か月で固定。有意（p<0.05）なのはラグ{q['sig_lags'][0]}・{q['sig_lags'][-1]}か月だけで、係数は最大 {q['max_b_wage']:.2f}（食料工業製品は {q['b_food_range'][0]:.2f}〜{q['b_food_range'][1]:.2f}）", fontsize=9, color=INK2)
save(fig, "fig3_wage_lags.png")

# 図4：2021年12月＝100 の水準
mm = pd.read_csv(ROOT / "data" / "monthly.csv"); mm["t"] = mm.year * 12 + mm.month - 1; mm = mm.set_index("t")
base = 2021 * 12 + 11
mm["wage_restaurant_ma"] = mm.wage_restaurant.rolling(12).mean()
z = mm.loc[base:]
zz = z.year + (z.month - 1) / 12
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.09, right=0.8, top=0.83, bottom=0.14)
for col, c, nm in (("cpi_processed_food", ORANGE, "食料工業製品"), ("cpi_eatout", BLUE, "外食"), ("cpi_other_services", GRAY, "他のサービス"),
                   ("wage_restaurant_ma", GREEN, "飲食店の時給")):
    s = 100 * z[col] / z.loc[base, col]
    ax.plot(zz, s, color=c, lw=2)
    last = s.dropna()
    ax.text(zz.loc[last.index[-1]] + 0.05, last.iloc[-1], f"{nm} {last.iloc[-1]:.1f}", fontsize=8.5, va="center")
ax.axhline(100, color="#cfcdc8", lw=0.8); ax.set_ylabel("2021年12月＝100"); ax.set_xlabel("年"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("食材は外食より大きく上がり、時給の上がり方は外食より小さかった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, "2021年12月＝100。時給は12か月移動平均（2026年8月まで）", fontsize=9, color=INK2)
save(fig, "fig4_levels_since_2021.png")
print("ok")
