"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
GRAY, INK2 = "#9a9893", "#52514e"
SRC = "出典：経済産業省「工場立地動向調査」2025年調査（経年掲載、e-Stat）をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
M = pd.read_csv(RES / "requestion_manufacturing_by_year.csv", index_col=0)
U = pd.read_csv(RES / "requestion_utilities_by_year.csv", index_col=0)
T = pd.read_csv(RES / "total_by_year.csv", index_col=0)
def save(fig, name, src=SRC):
    fig.text(0.01, 0.01, src, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)
x = M.index.values

# 図1：立地件数（製造業）と新設
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.84, top=0.83, bottom=0.14)
ax.plot(x, M["count"], color=C6[0], lw=2, marker="o", ms=4); ax.text(2025.4, M["count"].iloc[-1] + 30, "製造業の立地件数", fontsize=9, color=C6[0])
ax.plot(x, T.new_count, color=C6[1], lw=2, marker="o", ms=4); ax.text(2025.4, T.new_count.iloc[-1] - 70, "新設の件数\n（電気業なども含む）", fontsize=9, color=C6[1])
for a, b in [(2015, 2019), (2021, 2025)]: ax.axvspan(a - 0.4, b + 0.4, color="#e6e5e1", lw=0, alpha=0.6)
ax.set_ylabel("件数（件）"); ax.set_xlabel("年"); ax.set_xticks(range(2006, 2026, 2)); ax.set_ylim(0, 2000); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
h = q["count"]
fig.suptitle("工場の立地件数は、2021年以降も増えていない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"1,000㎡以上の用地を取得した工場。製造業の年平均：2015〜19年 {h['avg_2015_19']:.0f}件 → 2021〜25年 {h['avg_2021_25']:.0f}件（対数差×100 で {h['dlog']:.0f}）", fontsize=9, color=INK2)
save(fig, "fig1_location_counts.png")

# 図2：設備投資額（製造業と電気業など）
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.15)
ax.bar(x, M.capex_mil / 1e6, color=C6[0], width=0.72, label="製造業")
ax.bar(x, U.capex_mil / 1e6, bottom=M.capex_mil / 1e6, color=GRAY, width=0.72, label="電気業・ガス業・熱供給業", edgecolor="white", lw=1)
ax.set_xticks(x[::2]); ax.set_ylabel("設備投資の予定額（兆円、名目）"); ax.set_xlabel("年"); ax.set_ylim(0, 2.3); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.legend(frameon=False, fontsize=9, loc="upper right")
fig.suptitle("製造業の設備投資の予定額は増えたが、発電所などは減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"年平均（2015〜19年→2021〜25年）：製造業 {q['capex_mil']['avg_2015_19']/1e6:.2f}兆→{q['capex_mil']['avg_2021_25']/1e6:.2f}兆円（対数差×100 で {q['capex_mil']['dlog']:+.0f}）、電気業など {q['utilities_capex']['avg_2015_19']/1e6:.2f}兆→{q['utilities_capex']['avg_2021_25']/1e6:.2f}兆円", fontsize=9, color=INK2)
save(fig, "fig2_capex_manuf_utilities.png")

# 図3：1件当たりの面積と設備投資額（製造業、2015〜19年平均＝100）
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.82, top=0.83, bottom=0.14)
for col, c, lab in [("capex_per_site", C6[1], "1件当たり設備投資額"), ("area_per_site", C6[2], "1件当たり敷地面積"), ("count", C6[0], "件数")]:
    s = 100 * M[col] / M.loc[2015:2019, col].mean(); ax.plot(x, s, color=c, lw=2, marker="o", ms=4); ax.text(2025.4, s.iloc[-1], lab, fontsize=9, color=c, va="center")
ax.axhline(100, color=GRAY, lw=0.6, ls=":")
ax.set_ylabel("指数（2015〜19年平均＝100）"); ax.set_xlabel("年"); ax.set_xticks(range(2006, 2026, 2)); ax.set_ylim(40, 220); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("件数は減り、1件の案件は大きくなった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"製造業。2015〜19年→2021〜25年（対数差×100）：件数 {q['count']['dlog']:.0f}、1件当たり面積 {q['area_per_site']['dlog']:+.0f}、1件当たり設備投資額 {q['capex_per_site']['dlog']:+.0f}（名目）", fontsize=9, color=INK2)
save(fig, "fig3_per_site.png")

# 図4：設備投資額の増減の業種別の寄与（製造業）
c = pd.read_csv(RES / "capex_contrib_by_industry.csv", index_col=0)
c = c.drop(index=[k for k in ["電気業", "ガス業", "熱供給業"] if k in c.index])
c["contrib"] = 100 * c.change / (q["capex_mil"]["avg_2021_25"] - q["capex_mil"]["avg_2015_19"])
c = c.sort_values("change")
show = pd.concat([c.head(4), c.tail(7)])
fig, ax = plt.subplots(figsize=(8.4, 5.2)); fig.subplots_adjust(left=0.24, right=0.95, top=0.83, bottom=0.13)
cols = [C6[0] if v > 0 else C6[1] for v in show.change]
ax.barh(range(len(show)), show.change / 100, color=cols, height=0.65)
for i, (v, s) in enumerate(zip(show.change / 100, show.contrib)):
    ax.text(v + (8 if v > 0 else -8), i, f"{v:+,.0f}億円", va="center", ha="left" if v > 0 else "right", fontsize=8.5)
ax.set_yticks(range(len(show))); ax.set_yticklabels(show.index); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("設備投資の予定額の年平均の増減（億円、2015〜19年→2021〜25年）"); ax.set_xlim(-600, 750); ax.grid(axis="x", color="#e6e5e1", lw=0.6)
fig.suptitle("増えたのは輸送用機械・金属製品・非鉄金属。電子部品は小さかった", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.885, f"製造業の増加分のうち 輸送用機械 {q['manuf_capex_contrib_pct']['輸送用機械']:.0f}%。電子部品・デバイスは2021〜25年の製造業の設備投資額の {q['electronics_share_of_manuf_capex_2021_25']:.1f}%", fontsize=9, color=INK2)
save(fig, "fig4_capex_by_industry.png")
print("ok")
