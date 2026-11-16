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
SRC = "出典：総務省「家計調査」二人以上の世帯 第4-6表（世帯主の年齢階級別、年次）をもとに作成者が加工"
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：年齢別の推移
b = pd.read_csv(RES / "beer_quantity_by_year.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.83, top=0.83, bottom=0.14)
for k, a in enumerate(AG):
    ax.plot(b.index, b[a], color=C6[k], lw=2)
    off = {"29歳以下": 1.2, "30～39歳": -1.2, "50～59歳": 0.6, "70歳以上": -0.6}.get(a, 0)
    ax.text(2025.4, b[a].iloc[-1] + off, a, fontsize=8.5, va="center", color="#0b0b0b")
ax.set_ylabel("ビールの購入数量（L／世帯・年）"); ax.set_xlabel("年"); ax.set_ylim(0, 60); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("ビールを買う量は、どの年齢の世帯でも減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, "二人以上の世帯、世帯主の年齢別。2020年ごろから多くの年齢で少し戻っている", fontsize=9, color=INK2)
save(fig, "fig1_beer_by_age_year.png")

# 図2：減り方（ビール と ビール類）
c1 = pd.read_csv(RES / "h1_beer_quantity_change.csv", index_col=0).loc[AG]
rb = m["robustness"][1]["detail"]
fig, ax = plt.subplots(figsize=(8.2, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.16)
x = np.arange(len(AG)); w = 0.38
ax.bar(x - w / 2, c1.logchange, w, color=C6[0], label="ビール")
ax.bar(x + w / 2, [rb[a] for a in AG], w, color=GRAY, label="ビール類（ビール＋発泡酒など）")
for xi, v in zip(x - w / 2, c1.logchange): ax.text(xi, v - 2, f"{v:.0f}", ha="center", va="top", fontsize=8.5)
for xi, a in zip(x + w / 2, AG): ax.text(xi, min(rb[a], 0) - 2, f"{rb[a]:.0f}", ha="center", va="top", fontsize=8.5)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(AG); ax.set_ylim(-120, 15)
ax.set_ylabel("購入数量の変化（対数差×100）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.suptitle("若い世帯ほど大きく減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"2002〜04年平均 → 2023〜25年平均。ビール：29歳以下と30代の平均 {m['H2']['young_mean']:.0f}、60代と70歳以上の平均 {m['H2']['old_mean']:.0f}", fontsize=9, color=INK2)
save(fig, "fig2_change_by_age.png")

# 図3：年齢の形（3つの時期）
M = pd.read_csv(RES / "requestion_period_means.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.2, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.14)
for k, (p, c) in enumerate(zip(M.index, ["#86b6ef", GRAY, "#2a78d6"])):
    ax.plot(range(len(AG)), M.loc[p, AG], color=c, lw=2.2, marker="o", ms=5, label=p + "（3年平均）")
ax.set_xticks(range(len(AG))); ax.set_xticklabels(AG); ax.set_ylabel("ビールの購入数量（L／世帯・年）"); ax.set_ylim(0, 50)
ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=9)
fig.suptitle("2015年ごろから戻ったが、30代だけは戻らなかった", x=0.02, ha="left", fontsize=13, y=0.97)
ch = q["change_2015_2024_pct"]; oth = [v for k, v in ch.items() if k != "30～39歳"]
fig.text(0.02, 0.875, f"30〜39歳：{q['same_age_30s'][0]:.1f} → {q['same_age_30s'][1]:.1f} → {q['same_age_30s'][2]:.1f} L（2015→2024年ごろ {ch['30～39歳']:+.0f}%）。ほかの年齢は {min(oth):+.0f}〜{max(oth):+.0f}%", fontsize=9, color=INK2)
save(fig, "fig3_age_profile_periods.png")

# 図4：酒類に占めるビールの割合
c4 = pd.read_csv(RES / "h4_beer_share.csv", index_col=0).loc[AG]
fig, ax = plt.subplots(figsize=(8.2, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.14)
ax.bar(x - w / 2, c4.start, w, color=GRAY, label="2002〜04年")
ax.bar(x + w / 2, c4.end, w, color=C6[0], label="2023〜25年")
for xi, v in zip(x + w / 2, c4.end): ax.text(xi, v + 0.6, f"{v:.0f}%", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(AG); ax.set_ylabel("酒類の支出に占めるビールの割合（%）"); ax.set_ylim(0, 50)
ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=9)
fig.suptitle("お酒の支出に占めるビールの割合は、どの年齢でも下がった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"下がり方：29歳以下 {c4.loc['29歳以下','change_pt']:.1f}ポイント、70歳以上 {c4.loc['70歳以上','change_pt']:.1f}ポイント", fontsize=9, color=INK2)
save(fig, "fig4_beer_share_of_alcohol.png")
print("ok")
