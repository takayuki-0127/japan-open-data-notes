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
SRC = "出典：日本銀行「時系列統計データ」、総務省「家計消費状況調査」（二人以上の世帯）をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
A = pd.read_csv(RES / "annual_table.csv", index_col=0)
D = pd.read_csv(RES / "h3_table.csv", index_col=0)
def save(fig, name, src=SRC):
    fig.text(0.01, 0.01, src, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：銀行券と電子マネー（2つの図に分ける）
fig, axes = plt.subplots(2, 1, figsize=(8.2, 6.2), sharex=True); fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.1, hspace=0.3)
a = A.loc[2005:]
axes[0].plot(a.index, a.notes_avg / 1e4, color=BLUE, lw=2.2, marker="o", ms=3.5)
axes[0].set_title("日本銀行券発行高（年平均、兆円）", fontsize=10, loc="left"); axes[0].grid(axis="y", color="#e6e5e1", lw=0.6)
axes[0].annotate(f"{int(m['peak_year'])}年 {m['peak_value'] / 1e4:.1f}兆円", (m["peak_year"], m["peak_value"] / 1e4), xytext=(-60, 8), textcoords="offset points", fontsize=8.5)
axes[1].plot(D.index, D.use_share, color=GREEN, lw=2.2, marker="o", ms=3.5)
axes[1].set_title("電子マネーを利用した世帯員がいる世帯の割合（%、二人以上の世帯）", fontsize=10, loc="left"); axes[1].grid(axis="y", color="#e6e5e1", lw=0.6)
axes[1].set_ylim(0, 70); axes[1].set_xlabel("年"); axes[1].set_xticks(range(2005, 2026, 5))
fig.suptitle("電子マネーが広がる間も、お札は2023年まで増え続けた", x=0.02, ha="left", fontsize=13, y=0.975)
fig.text(0.02, 0.915, f"銀行券 2015→2023年 +{m['H1']['growth_2015_2023']:.1f}%、2023→2025年 {m['H1']['growth_2023_2025']:.1f}%（対数差）。電子マネーの利用 2010年{m['emoney']['2010'][0]:.1f}% → 2025年{m['emoney']['2025'][0]:.1f}%", fontsize=8.5, color=INK2)
save(fig, "fig1_notes_and_emoney.png")

# 図2：年ごとの関係
x = D.loc[2011:2025]
fig, ax = plt.subplots(figsize=(7.6, 5.2)); fig.subplots_adjust(left=0.11, right=0.97, top=0.85, bottom=0.13)
ax.scatter(x.d_use, x.g_notes, color=BLUE, s=45)
for yy, r in x.iterrows():
    ax.annotate(str(yy), (r.d_use, r.g_notes), xytext=(4, 3), textcoords="offset points", fontsize=8)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlabel("電子マネーを利用した世帯の割合の前年からの上がり幅（ポイント）"); ax.set_ylabel("銀行券（年平均）の伸び率（%、対数差）")
ax.grid(color="#e6e5e1", lw=0.6)
h3 = m["H3"]
fig.suptitle("電子マネーが広がった年ほどお札の伸びが鈍った、とは言えない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.9, f"2011〜2025年。傾き {h3['coef']:+.2f}（p={h3['p']:.2f}）", fontsize=9, color=INK2)
save(fig, "fig2_emoney_vs_notes_growth.png")

# 図3：月の前年同月比（券種別）とコールレート
t = pd.read_csv(RES / "requestion_monthly_yoy.csv")
t = t[t.year >= 2021]; xx = t.year + (t.month - 1) / 12
fig, axes = plt.subplots(2, 1, figsize=(8.4, 6.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]}); fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.1, hspace=0.25)
axes[0].plot(xx, t.yoy_y10000, color=BLUE, lw=2, label="1万円札")
axes[0].plot(xx, t.yoy_y1000, color=ORANGE, lw=2, label="千円札")
axes[0].axhline(0, color=INK2, lw=0.8); axes[0].set_ylabel("前年同月比（%）"); axes[0].legend(frameon=False, fontsize=8.5, loc="upper right")
axes[0].grid(axis="y", color="#e6e5e1", lw=0.6)
for ev, lab, yt in ((2023 + 11 / 12, "2023年12月\n1万円札が前年割れ", 5.2), (2024 + 6 / 12, "2024年7月\n新しい銀行券", -2.9)):
    for ax in axes: ax.axvline(ev, color=GRAY, lw=1, ls="--")
    axes[0].text(ev + 0.03, yt, lab, fontsize=8, color=INK2)
axes[1].plot(xx, t.call, color=GREEN, lw=2); axes[1].set_ylabel("コールレート（%）"); axes[1].grid(axis="y", color="#e6e5e1", lw=0.6); axes[1].set_xlabel("年")
fig.suptitle("お札が減り始めたのは、金利が上がる前の2023年12月", x=0.02, ha="left", fontsize=13, y=0.975)
fig.text(0.02, 0.915, "日本銀行券発行高（月末）の券種別の前年同月比と、無担保コールレート（翌日物、月平均）", fontsize=9, color=INK2)
save(fig, "fig3_monthly_by_denomination.png")

# 図4：券種別の伸び
h4 = m["H4"]
fig, ax = plt.subplots(figsize=(7.6, 4.6)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.15)
labs = ["1万円札", "5千円札", "千円札"]; vals = [h4["g_10000"], h4["g_5000"], h4["g_1000"]]
bars = ax.bar(labs, vals, color=[BLUE, GRAY, ORANGE], width=0.55)
for bb, v in zip(bars, vals): ax.text(bb.get_x() + bb.get_width() / 2, v + 0.4, f"+{v:.1f}", ha="center", fontsize=10)
ax.set_ylabel("2015→2025年の伸び（%、対数差、12月末の金額）"); ax.set_ylim(0, 25); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("1万円札だけが増えたのではなく、千円札も増えた", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"1万円札の割合（12月末の金額）：2010年 {m['H2']['share_2010']:.1f}% → 2025年 {m['H2']['share_2025']:.1f}%", fontsize=9, color=INK2)
save(fig, "fig4_denominations.png")
print("ok")
