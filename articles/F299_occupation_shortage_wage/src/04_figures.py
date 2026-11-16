"""図を作る（PNG、日付などのメタデータを入れない）。"""
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
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "svg.hashsalt": "f299", "figure.dpi": 100})
BLUE, ORANGE, GRAY, INK2 = "#2a78d6", "#eb6834", "#9a9893", "#52514e"
SRC = "出典：厚生労働省「一般職業紹介状況」「賃金構造基本統計調査」（e-Stat）をもとに作成者が加工。医療・福祉・介護と管理的職業は除く"
d = pd.read_csv(RES / "group_table.csv")
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))

def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# 図1：散布図
fig, ax = plt.subplots(figsize=(8, 5.6)); fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.14)
s = 20 + 380 * d.workers_2022 / d.workers_2022.max()
ax.scatter(d.ratio_fy2022_all, d.g_pay_22_25, s=s, color=BLUE, alpha=0.55, edgecolor="#fcfcfb", linewidth=1)
b = m["H1"]["slope"]
x = np.linspace(0, d.ratio_fy2022_all.max() * 1.03, 50)
xm = np.average(d.ratio_fy2022_all, weights=d.workers_2022); ym = np.average(d.g_pay_22_25, weights=d.workers_2022)
ax.plot(x, ym + b * (x - xm), color=ORANGE, lw=2, label=f"労働者数で重みをつけた回帰線（傾き {b:+.2f}、p={m['H1']['p']:.2f}）")
ax.axhline(m["mean_growth_22_25_weighted"], color=GRAY, lw=1, ls="--")
ax.text(9.9, m["mean_growth_22_25_weighted"] + 0.6, f"全体の平均 +{m['mean_growth_22_25_weighted']:.1f}%", ha="right", color=INK2, fontsize=8.5)
lab = {"建設躯体工事": (0, 8), "保安職業（警備員など）": (0, 10), "一般事務": (12, 4), "建築・土木・測量技術者": (0, -16), "電気工事": (0, 8),
       "情報処理・通信技術者": (0, -16)}
for r in d.itertuples():
    if r.group_name in lab:
        dx, dy = lab[r.group_name]
        ax.annotate(r.group_name, (r.ratio_fy2022_all, r.g_pay_22_25), xytext=(dx, dy), textcoords="offset points", fontsize=8, color="#0b0b0b",
                    ha="left" if dx else "center")
ax.set_xlabel("2022年度の有効求人倍率（パートを含む常用、倍）"); ax.set_ylabel("所定内給与の伸び 2022→2025年（%、対数差）")
ax.set_ylim(-22, 22); ax.set_xlim(0, 10.3); ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(loc="lower left", frameon=False, fontsize=8.5)
fig.suptitle("求人倍率の高い職業ほど賃金が速く上がった、とは言えなかった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.895, f"45の職業。円の大きさは2022年の労働者数。傾きはむしろ負（並べ替え検定 p={m['H1']['perm_p']:.2f}）", fontsize=9, color=INK2)
save(fig, "fig1_scatter_ratio_growth.png")

# 図2：3つに分けた伸び
t = pd.read_csv(RES / "h2_tercile.csv")
fig, ax = plt.subplots(figsize=(7.5, 4.8)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.2)
names = [f"{r.tercile}\n（{r.ratio_min:.2f}〜{r.ratio_max:.2f}倍、{int(r.n)}職業）" for r in t.itertuples()]
bars = ax.bar(names, t.growth_w, color=BLUE, width=0.55)
for bb, v in zip(bars, t.growth_w):
    ax.text(bb.get_x() + bb.get_width() / 2, v + 0.2, f"+{v:.1f}%", ha="center", fontsize=10)
ax.set_ylabel("所定内給与の伸び 2022→2025年（%）"); ax.set_ylim(0, 13); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.set_xlabel("2022年度の有効求人倍率で3つに分けた職業のグループ")
fig.suptitle("倍率の高いグループの伸びは、低いグループより小さかった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.87, f"労働者数で重みをつけた平均。高い−低い＝{m['H2_gap_top_minus_bottom']:+.1f}%pt（事前の基準は +1%pt 以上）", fontsize=9, color=INK2)
save(fig, "fig2_tercile_growth.png")

# 図3：頑健性の傾き
r = pd.read_csv(RES / "robustness_h1.csv")
r = r[r.spec != "R7 倍率を対数に（追加）"].reset_index(drop=True)  # 単位が違うので図からは外す（表には載せる）
fig, ax = plt.subplots(figsize=(8, 5.2)); fig.subplots_adjust(left=0.38, right=0.97, top=0.84, bottom=0.15)
yy = np.arange(len(r))[::-1]
ax.errorbar(r.slope, yy, xerr=1.96 * r.se, fmt="o", color=BLUE, ecolor=BLUE, elinewidth=2, capsize=0, markersize=7)
ax.axvline(0, color=GRAY, lw=1)
ax.set_yticks(yy); ax.set_yticklabels(r.spec, fontsize=9)
ax.set_xlabel("倍率が1高いと、3年の賃金の伸びが何%pt 違うか（点＝推定、線＝95%区間）")
fig.suptitle("定義や期間を変えても、傾きは0か負のあたり", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.89, "どの組み合わせでも、正で意味のある傾き（人手不足の職業ほど速く上がる）は出なかった", fontsize=9, color=INK2)
save(fig, "fig3_robustness_slopes.png")

# 図4：倍率の持続（問い直しの補足）
fig, ax = plt.subplots(figsize=(7.2, 5.4)); fig.subplots_adjust(left=0.11, right=0.97, top=0.86, bottom=0.14)
ax.scatter(d.ratio_fy2022_all, d.ratio_jun2025_all, s=s, color=BLUE, alpha=0.55, edgecolor="#fcfcfb", linewidth=1)
ax.plot([0, 10], [0, 10], color=GRAY, lw=1, ls="--"); ax.text(9.6, 9.0, "変わらない線", color=INK2, fontsize=8.5, ha="right")
o = d[d.group_id == "eng_other"].iloc[0]
ax.annotate("その他の技術者（2024年に分類の扱いが\n変わったとみられ、求人が急に増えた）", (o.ratio_fy2022_all, o.ratio_jun2025_all), xytext=(12, -4),
            textcoords="offset points", fontsize=8, color="#0b0b0b", va="top")
ax.set_xlabel("2022年度の有効求人倍率（倍）"); ax.set_ylabel("2025年6月までの12か月の有効求人倍率（倍）")
ax.set_xlim(0, 10.3); ax.set_ylim(0, 10.3); ax.grid(color="#e6e5e1", lw=0.6)
cc = np.corrcoef(d.ratio_fy2022_all, d.ratio_jun2025_all)[0, 1]
fig.suptitle("人手が足りない職業は、3年たっても足りないまま", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.895, f"職業の間の相関 {cc:.2f}。3年間で倍率の順番はほとんど入れ替わらなかった", fontsize=9, color=INK2)
save(fig, "fig4_ratio_persistence.png")
m2 = {"ratio_corr_2022_2025": round(float(cc), 3)}
(RES / "fig_numbers.json").write_text(json.dumps(m2, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok")
