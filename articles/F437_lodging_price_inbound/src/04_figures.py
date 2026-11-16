"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：総務省「消費者物価指数」2025年基準、日本政府観光局（JNTO）「訪日外客数」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
a = pd.read_csv(R / "annual.csv").set_index("year").loc[2003:2025]

# 図1 年平均の指数と訪日客
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax2 = ax.twinx()
ax2.bar(a.index, a.visitors / 1e6, color=GRID, width=0.7, label="訪日外客数（右目盛、百万人）")
ax2.set_ylim(0, 90); ax2.set_ylabel("訪日外客数（百万人）", color=INK2); ax2.spines["top"].set_visible(False)
ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
ax.plot(a.index, a.lodging_z, color=C[1], lw=2.4, marker="o", ms=4, label="宿泊料")
ax.plot(a.index, a.all_z, color=C[0], lw=1.6, label="総合")
ax.set_ylabel("消費者物価指数（2025年＝100）")
ax.set_ylim(55, 105)
ax.set_xticks(range(2003, 2026, 2))
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"宿泊料は2012→2019年に+{m['lodging_2012_2019_pct']:.1f}%、2019→2025年に+{m['lodging_2019_2025_pct']:.1f}%（総合は+{m['all_2012_2019_pct']:.1f}%、+{m['all_2019_2025_pct']:.1f}%）", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.92, top=0.91, bottom=0.14)
save(fig, F / "fig1_annual_index.png", SRC, "注：年平均。2020〜2023年の宿泊料は Go To トラベル・全国旅行支援の割引で下がっている。宿泊料の指数は全国と東京都区部で同じ値。")

# 図2 月次の前年同月比の散布図
y = pd.read_csv(R / "yoy.csv").set_index("ym")
fig, ax = plt.subplots(figsize=(8.8, 5.2))
p1 = y.loc[201301:201912]; p2 = y.loc[202501:202609]
ax.scatter(p1.vis, p1.lodging, s=22, color=C[0], alpha=0.75, label=f"2013〜2019年（相関{m['corr_vis_lodging_2013_2019']:.2f}）")
ax.scatter(p2.vis, p2.lodging, s=30, color=C[1], alpha=0.9, marker="D", label="2025年1月〜2026年9月")
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("訪日外客数の前年同月比（%）"); ax.set_ylabel("宿泊料の前年同月比（%）")
ax.set_ylim(-4, 13.5)
ax.legend(frameon=False, loc="upper right", fontsize=9, ncol=2)
style(ax); ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_title(f"月ごとでは、訪日客の増え方と宿泊料の上がり方の相関は弱い（{m['corr_vis_lodging_all']:.2f}、{m['n_all']}か月）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, F / "fig2_monthly_scatter.png", SRC, "注：2020年1月〜2024年12月（割引とコロナの時期、その翌年）は除いた。")

# 図3 年ごとの変化の散布図
c = pd.read_csv(R / "annual_change.csv").set_index("year")
pre = c.loc[2004:2019]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.scatter(pre.d_visitors, pre.d_lodging, s=34, color=C[0], label="2004〜2019年")
for yr, r in pre.iterrows():
    if yr in (2009, 2011, 2014, 2015, 2019, 2012):
        ax.annotate(str(yr), (r.d_visitors, r.d_lodging), xytext=(4, 4), textcoords="offset points", fontsize=8.5, color=INK2)
xx = np.linspace(-35, 42, 50)
ax.plot(xx, q["slope_annual_2004_2019"] * xx + q["intercept_annual"], color=C[0], lw=1.2, ls="--", label=f"2004〜2019年の直線（傾き{q['slope_annual_2004_2019']:.3f}）")
for yr, col in ((2024, C[5]), (2025, C[1])):
    ax.scatter(c.d_visitors[yr], c.d_lodging[yr], s=60, color=col, marker="D", zorder=3)
    ax.annotate(f"{yr}年", (c.d_visitors[yr], c.d_lodging[yr]), xytext=(6, -4), textcoords="offset points", fontsize=9.5, color=col)
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("訪日外客数の前年からの変化（対数差×100）"); ax.set_ylabel("宿泊料の前年からの変化（対数差×100）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax); ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_title(f"年で見ると連動（相関{q['corr_annual_2004_2019']:.2f}）。2025年は直線の見込み+{q['pred_d_lodging_2025']:.1f}に対し+{q['d_lodging_2025']:.1f}", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, F / "fig3_annual_change.png", SRC, "注：2024年は前年（2023年）が全国旅行支援の割引の時期で、比べる元が低い。2020〜2023年は図から省いた。")

# 図4 季節の形 2025年
s = pd.read_csv(R / "season.csv")
g = s[s.year == 2025].set_index("month"); g19 = s[s.year == 2019].set_index("month")
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(g.index, g.lodging_rel, color=C[1], lw=2.4, marker="o", label="宿泊料 2025年")
ax.plot(g.index, g.visitors_rel, color=C[0], lw=2.4, marker="s", label="訪日外客数 2025年")
ax.plot(g19.index, g19.lodging_rel, color=C[1], lw=1.0, ls="--", label="宿泊料 2019年")
ax.plot(g19.index, g19.visitors_rel, color=C[0], lw=1.0, ls="--", label="訪日外客数 2019年")
ax.axhline(100, color=INK2, lw=0.8)
ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{i}月" for i in range(1, 13)])
ax.set_ylabel("その年の平均＝100")
ax.legend(frameon=False, loc="lower left", fontsize=9, ncol=2)
style(ax)
ax.set_title(f"宿泊料の山は8月（{q['lodging_peak_rel_2025']:.0f}）、訪日客の山は4月。季節の形の相関は2019年−{-q['season_corr_2019']:.2f}、2025年{q['season_corr_2025']:.2f}", loc="left", fontsize=11)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig4_season.png", SRC)
