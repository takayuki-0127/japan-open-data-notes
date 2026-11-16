"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：財務省・日本銀行「国際収支統計」、日本銀行「外国為替相場」、日本政府観光局「訪日外客数」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
t = pd.read_csv(R / "annual_table.csv").set_index("year")

# 図1 旅行の受取・支払・ネット
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(t.index, t.travel_rec, color=C[1], lw=2, label="受取（訪日客の日本での支出など）")
ax.plot(t.index, t.travel_pay, color=C[0], lw=2, label="支払（日本人の海外での支出など）")
ax.bar(t.index, t.travel, color=C[2], width=0.75, alpha=0.8, label="旅行収支（ネット）")
ax.axhline(0, color=INK2, lw=0.8)
ax.text(2025, t.loc[2025, "travel"] + 0.25, f"{t.loc[2025,'travel']:.1f}", ha="center", fontsize=9)
ax.text(2019, t.loc[2019, "travel"] + 0.25, f"{t.loc[2019,'travel']:.1f}", ha="center", fontsize=9)
ax.set_ylabel("兆円（暦年）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"旅行収支は{m['first_surplus_year']}年に黒字になり、2025年は{m['travel_2025']:.1f}兆円（2019年の{m['travel_ratio_2025_2019']:.1f}倍）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig1_travel_balance.png", SRC)

# 図2 訪日客数と1人あたりの受取（円・ドル）
s = t.loc[2003:2025]
fig, ax = plt.subplots(1, 2, figsize=(9.6, 4.8))
ax[0].bar(s.index, s.visitors_man, color=C[0], width=0.75)
ax[0].set_ylabel("訪日外客数（万人）"); style(ax[0])
ax[0].set_title("訪日客の数", loc="left", fontsize=11)
ok = s.visitors_man > 500
ax[1].plot(s.index[ok], s.rec_per_visitor_yen[ok] / 1e4, color=C[1], lw=2.2, marker="o", ms=3, label="円（万円）")
ax2 = ax[1].twinx()
ax2.plot(s.index[ok], s.rec_per_visitor_usd[ok], color=C[0], lw=2.2, marker="s", ms=3, label="ドル（右軸）")
ax[1].set_ylabel("1人あたりの受取（万円）", color=C[1]); ax2.set_ylabel("1人あたりの受取（ドル）", color=C[0])
ax[1].set_ylim(0, 26); ax2.set_ylim(0, 2000)
ax2.spines["top"].set_visible(False)
style(ax[1])
ax[1].set_title("1人あたりの受取（円とドル）", loc="left", fontsize=11)
fig.suptitle(f"2019→25年：人数は+{m['d_visitors_growth_pct']:.0f}%、1人あたりは円で+{m['d_per_visitor_yen_growth_pct']:.0f}%、ドルでは+{m['d_per_visitor_usd_growth_pct']:.0f}%", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.07, right=0.92, top=0.84, bottom=0.17, wspace=0.42)
save(fig, F / "fig2_visitors_per_capita.png", SRC, "注：1人あたり＝旅行の受取÷訪日外客数。2020〜22年（訪日客が500万人未満）は1人あたりを示さない。受取には留学生などの支出も入る。")

# 図3 サービス収支の内訳
s = t.loc[1996:2025]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
items = [("travel", "旅行", C[2]), ("transport", "輸送", C[3]), ("other_services", "その他サービス", C[0])]
pos = np.zeros(len(s)); neg = np.zeros(len(s))
for c, lab, col in items:
    v = s[c].values
    bottom = np.where(v >= 0, pos, neg)
    ax.bar(s.index, v, bottom=bottom, color=col, width=0.8, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(s.index, s.services, color=INK, lw=1.8, marker="o", ms=3, label="サービス収支")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("兆円（暦年）")
ax.legend(frameon=False, loc="lower left", fontsize=9, ncol=2)
style(ax)
ax.set_title(f"旅行の黒字{m['travel_2025']:.1f}兆円より、その他サービスの赤字{-m['other_services_2025']:.1f}兆円の方が大きい", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig3_services_breakdown.png", SRC, "注：その他サービスには、デジタル関連（コンピュータサービス、著作権等使用料など）、保険・金融、専門・経営コンサルティングなどが入る。")

# 図4 2019→2025年の変化
g = pd.read_csv(R / "services_change.csv")
fig, ax = plt.subplots(figsize=(8.8, 4.6))
cols = [C[2] if v > 0 else C[1] for v in g.change]
ax.barh(g.item[::-1], g.change[::-1], color=cols[::-1])
for yy, v in enumerate(g.change[::-1]):
    ax.text(v + (0.12 if v >= 0 else -0.12), yy, f"{v:+.2f}兆円", va="center", ha="left" if v >= 0 else "right", fontsize=9.5)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-8.5, 6)
ax.set_xlabel("2019→2025年の変化（兆円）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"旅行の黒字の増加は、その他サービスの赤字の拡大の{q['travel_offset_pct']:.0f}%しか埋めていない", loc="left", fontsize=12)
fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.18)
save(fig, F / "fig4_change_2019_2025.png", SRC)
