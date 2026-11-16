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
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
GRAY, INK2 = "#9a9893", "#52514e"
SRC = "出典：観光庁「宿泊旅行統計調査」年確定値（2012・2015・2018・2019・2022〜2025年）第7表・第8表をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
O = pd.read_csv(RES / "occupancy.csv", index_col=0); U = pd.read_csv(RES / "used_rooms.csv", index_col=0); S = pd.read_csv(RES / "supply_rooms.csv", index_col=0)
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)
x = O.index.values
# 図1：稼働率の推移
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.84, top=0.83, bottom=0.14)
for col, c, lab, off in [("シティホテル", C6[1], "シティホテル", -3.0), ("ビジネスホテル", C6[0], "ビジネスホテル", 2.0), ("all", INK2, "全体", 0), ("リゾートホテル", C6[2], "リゾートホテル", 0), ("旅館", C6[3], "旅館", 0)]:
    ax.plot(x, O[col], color=c, lw=2.4 if col == "all" else 1.8, marker="o", ms=4); ax.text(2025.4, O[col].iloc[-1] + off, lab, fontsize=9, color=c, va="center")
ax.set_ylabel("客室稼働率（%、年平均）"); ax.set_xlabel("年（調べた8年分）"); ax.set_ylim(0, 90); ax.set_xticks(x); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("2025年の客室稼働率は、まだ2019年に届いていない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"全体：2019年 {m['H1']['y2019']:.1f}% → 2025年 {m['H1']['y2025']:.1f}%。シティホテル {O.loc[2019,'シティホテル']:.1f}% → {O.loc[2025,'シティホテル']:.1f}%、ビジネスホテル {O.loc[2019,'ビジネスホテル']:.1f}% → {O.loc[2025,'ビジネスホテル']:.1f}%", fontsize=9, color=INK2)
save(fig, "fig1_occupancy_by_type.png")
# 図2：2019→2025年の分解
ty = [("all", "全体"), ("ビジネスホテル", "ビジネスホテル"), ("シティホテル", "シティホテル"), ("リゾートホテル", "リゾートホテル"), ("旅館", "旅館")]
dd = [m["H2"]] + [m["by_type_2019_2025"][k] for k, _ in ty[1:]]
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.15)
xx = np.arange(len(ty)); w = 0.26
for k, (key, col, lab) in enumerate([("used", INK2, "利用客室数"), ("supply", C6[0], "売れる客室（推計）"), ("occupancy", C6[1], "稼働率")]):
    vals = [z[key] for z in dd]; ax.bar(xx + (k - 1) * w, vals, w, color=col, label=lab)
    for xi, v in zip(xx + (k - 1) * w, vals): ax.text(xi, v + (0.4 if v >= 0 else -1.0), f"{v:+.0f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(xx); ax.set_xticklabels([l for _, l in ty]); ax.set_ylim(-16, 14)
ax.set_ylabel("2019→2025年の変化（対数差×100）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=8.5, loc="lower left", ncol=3)
fig.suptitle("使われた客室の伸びより、売れる客室の伸びが大きかった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, "利用客室数の伸び ＝ 売れる客室（利用客室数 ÷ 稼働率）の伸び ＋ 稼働率の伸び", fontsize=9, color=INK2)
save(fig, "fig2_decomposition_2019_2025.png")
# 図3：供給と利用（2012年＝100）
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.84, top=0.83, bottom=0.14)
for ser, c, lab in [(S["all"], C6[0], "売れる客室（推計）"), (U["all"], INK2, "利用客室数")]:
    v = 100 * ser / ser.loc[2012]; ax.plot(x, v, color=c, lw=2, marker="o", ms=4); ax.text(2025.4, v.iloc[-1], lab, fontsize=9, color=c, va="center")
ax.axhline(100, color=GRAY, lw=0.6, ls=":"); ax.set_ylabel("指数（2012年＝100）"); ax.set_xlabel("年（調べた8年分）"); ax.set_ylim(80, 160); ax.set_xticks(x); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("2012〜2019年は稼働率も上がり、2019年以降は売れる客室だけが伸びた", x=0.02, ha="left", fontsize=12.5, y=0.97)
h4 = m["H4"]
fig.text(0.02, 0.885, f"全体。2012→2019年：利用 {h4['used']:+.0f}（供給 {h4['supply']:+.0f}、稼働率 {h4['occupancy']:+.0f}）。2019→2025年：利用 {m['H2']['used']:+.0f}（供給 {m['H2']['supply']:+.0f}、稼働率 {m['H2']['occupancy']:+.0f}）", fontsize=9, color=INK2)
save(fig, "fig3_supply_vs_used.png")
# 図4：シティホテルの月別稼働率
mm = pd.read_csv(RES / "requestion_monthly_occupancy.csv")
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.86, top=0.83, bottom=0.14)
for y, c in [(2019, GRAY), (2023, "#86b6ef"), (2025, C6[1])]:
    g = mm[mm.year == y]; ax.plot(g.month, g["シティホテル"], color=c, lw=2, marker="o", ms=4); ax.text(12.3, g["シティホテル"].iloc[-1] + {2019: 0, 2023: -1.2, 2025: 1.0}[y], f"{y}年", fontsize=9, color=c, va="center")
ax.axhline(80, color=GRAY, lw=0.6, ls=":"); ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{i}月" for i in range(1, 13)])
ax.set_ylabel("シティホテルの客室稼働率（%）"); ax.set_ylim(40, 90); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
c19, c25 = q["シティホテル"]["2019"], q["シティホテル"]["2025"]
fig.suptitle("混む月の稼働率も、2019年ほどは高くない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"シティホテル（全国）。80%以上の月：2019年 {c19['months_ge80']}か月（最高 {c19['max']:.1f}%）、2025年 {c25['months_ge80']}か月（最高 {c25['max']:.1f}%）", fontsize=9, color=INK2)
save(fig, "fig4_city_hotel_monthly.png")
print("ok")
