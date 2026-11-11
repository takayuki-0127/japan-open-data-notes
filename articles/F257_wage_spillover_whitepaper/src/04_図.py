"""04 図：figures/ に6枚"""
import json
import numpy as np, pandas as pd
import matplotlib, matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import RES, FIG, DATA, IND_NAME
FIG.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
SRC = "出典：厚生労働省「毎月勤労統計調査」"
C1, C2, C3, C4 = "#2b6cb0", "#d97706", "#2f855a", "#9b2c2c"
def save(fig, name, note):
    fig.text(0.01, 0.01, note, fontsize=8.5, color="#555"); fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / name, dpi=150); plt.close(fig)

# 図1 広さ：前年比+1/2/3%以上の産業の割合
br = pd.read_csv(RES / "h1_breadth_by_year.csv")
fig, ax = plt.subplots(figsize=(10, 5.2))
for th, c in ((1, C3), (2, C1), (3, C4)):
    ax.plot(br.年, br[f"share_ge{th}"], marker="o", ms=4, color=c, label=f"+{th}%以上")
ax.axvspan(2014.5, 2019.5, color="#eee", zorder=0); ax.text(2017, 95, "比べる基準\n2015〜19年", ha="center", fontsize=9, color="#666")
ax.set_ylim(0, 105); ax.set_ylabel("16産業のうちの割合（%）")
ax.set_title("一般労働者の所定内給与の前年比が＋1%・＋2%・＋3%以上だった産業の割合")
ax.legend(frameon=False, loc="upper left")
save(fig, "fig1_breadth.png", SRC + "（5人以上、公表の前年比）。16大産業を1つずつ数えた割合")

# 図2 2025年の産業別の前年比
ind = pd.read_csv(DATA / "industry_general.csv", dtype={"産業分類": str})
y = ind[ind.年 == 2025].copy(); y["名"] = y.産業分類.map(IND_NAME); y = y.sort_values("yoy_sched")
y2 = ind[ind.年 == 2019].set_index("産業分類").yoy_sched
fig, ax = plt.subplots(figsize=(10, 6.2))
yy = y.yoy_sched.clip(upper=8)
ax.barh(y.名, yy, color=[C1 if v >= 2 else "#a0aec0" for v in y.yoy_sched])
ax.scatter(y.産業分類.map(y2), y.名, color=C2, zorder=3, s=22, label="2019年")
for i, (v, n) in enumerate(zip(y.yoy_sched, y.名)):
    ax.text(min(v, 8) + 0.15, i, f"{v:+.1f}%", va="center", fontsize=9)
ax.axvline(2, color="#555", lw=0.8, ls="--"); ax.axvline(0, color="#333", lw=0.8)
ax.set_xlim(-3.5, 9.5); ax.set_xlabel("前年比（%）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("2025年の一般労働者の所定内給与の前年比（産業別、棒）と2019年（点）")
save(fig, "fig2_industry_2025.png", SRC + "（5人以上）。鉱業は+19.0%で、図は8%で切った。灰色の棒は+2%未満")

# 図3 規模別の伸び（一般・パート）
gap = pd.read_csv(RES / "h2_size_gap.csv", dtype={"就業形態": str})
fig, axs = plt.subplots(1, 2, figsize=(12, 5), sharey=False)
for ax, f, t in ((axs[0], "1", "一般労働者（月の所定内給与）"), (axs[1], "2", "パート（1時間あたり所定内給与）")):
    c = "所定内給与" if f == "1" else "hourly"
    g = gap[(gap.就業形態 == f) & (gap.指標 == c) & (gap.年 >= 2015)]
    ax.plot(g.年, g.yoy_500plus, marker="o", ms=4, color=C1, label="500人以上")
    ax.plot(g.年, g.yoy_5_29, marker="s", ms=4, color=C2, label="5〜29人")
    ax.axhline(0, color="#333", lw=0.7); ax.set_title(t); ax.set_ylabel("前年比（%）")
axs[0].legend(frameon=False)
fig.suptitle("事業所の規模別の伸び：一般は大きい事業所が上、パートは小さい事業所が上（2024〜25年）")
save(fig, "fig3_size_growth.png", SRC + "の実数から計算（調査対象の入れ替えの段差を含む）。事業所規模")

# 図4 水準の比（5〜29人÷500人以上）と企業規模の改定率の差
summ = gap[(gap.年 >= 2010)]
fig, axs = plt.subplots(1, 2, figsize=(12, 5))
for f, c, lab, col in (("1", "所定内給与", "一般（月額）", C1), ("2", "hourly", "パート（時給）", C2)):
    g = summ[(summ.就業形態 == f) & (summ.指標 == c)]
    axs[0].plot(g.年, g.ratio_small_large * 100, marker="o", ms=4, color=col, label=lab)
axs[0].set_title("5〜29人の事業所の水準 ÷ 500人以上（%）"); axs[0].legend(frameon=False)
p1 = pd.read_csv(RES / "h2_firm_size_rate.csv", index_col=0).loc[2005:]
axs[1].plot(p1.index, p1["5,000人以上"], color=C1, marker="o", ms=3, label="5,000人以上")
axs[1].plot(p1.index, p1["100～299人"], color=C2, marker="s", ms=3, label="100〜299人")
axs[1].set_title("1人あたり賃金の改定率（企業規模、%）"); axs[1].xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True)); axs[1].legend(frameon=False)
fig.suptitle("差は縮んだか：一般の水準の比は2023年から下がり、企業規模の改定率の差は広がった")
save(fig, "fig4_gap_levels.png", "出典：厚生労働省「毎月勤労統計調査」（左）、「賃金引上げ等の実態に関する調査」（右）")

# 図5 パート時給の伸びと最低賃金の伸び
pt = pd.read_csv(RES / "h3_part_mw.csv", index_col=0).loc[2010:2025]
M = json.load(open(RES / "main.json"))["h3"]["main_cy_2010_25"]
fig, axs = plt.subplots(1, 2, figsize=(12, 5))
axs[0].plot(pt.index, pt.yoy_hourly, marker="o", ms=4, color=C1, label="パートの時給（所定内）")
axs[0].plot(pt.index, pt.mw_yoy, marker="s", ms=4, color=C2, label="最低賃金（暦年に直した値）")
axs[0].axhline(0, color="#333", lw=0.7); axs[0].set_ylabel("前年比（%）"); axs[0].legend(frameon=False); axs[0].set_title("前年比の推移")
axs[1].scatter(pt.mw_yoy, pt.yoy_hourly, color=C1)
for yr, r in pt.iterrows():
    if yr in (2010, 2020, 2021, 2024, 2025): axs[1].annotate(str(yr), (r.mw_yoy, r.yoy_hourly), fontsize=8.5, xytext=(4, 2), textcoords="offset points")
xs = np.linspace(pt.mw_yoy.min(), pt.mw_yoy.max(), 10); axs[1].plot(xs, M["a"] + M["b"] * xs, color=C4, lw=1)
axs[1].set_xlabel("最低賃金の前年比（%）"); axs[1].set_ylabel("パート時給の前年比（%）")
axs[1].set_title(f"傾き {M['b']:.2f}、R² {M['r2']:.2f}（2010〜25年、16年）")
fig.suptitle("パートの時給は、最低賃金の伸びとよく連動する")
save(fig, "fig5_part_mw.png", SRC + "（5人以上・産業計）、地域別最低賃金の全国加重平均。暦年＝前年度の額×3/4＋その年度の額×1/4")

# 図6 再問い：最低賃金への近さと伸び
rb = pd.read_csv(RES / "reask_bite_growth.csv")
fig, ax = plt.subplots(figsize=(10, 6))
for kind, col, mk in (("産業", C1, "o"), ("規模", C2, "s")):
    d = rb[rb.区分 == kind]; ax.scatter(d.bite_2022, d.growth_22_25, color=col, marker=mk, s=40, label=kind + ("（5人以上）" if kind == "産業" else "（産業計）"))
    for _, r in d.iterrows():
        off = {"5〜29人": (6, -12), "鉱業": (4, 6), "運輸・郵便": (4, -12), "500人以上": (4, 6), "金融・保険": (-6, -14)}.get(r.名前, (4, 2))
        ax.annotate(r.名前, (r.bite_2022, r.growth_22_25), fontsize=8.5, xytext=off, textcoords="offset points", color=col if kind == "規模" else "#222")
mwg = json.load(open(RES / "reask.json"))["mw_growth_22_25"]
ax.axhline(mwg, color="#555", ls="--", lw=0.8); ax.text(1.72, mwg + 0.2, f"最低賃金 +{mwg:.1f}%", fontsize=9, color="#555")
ax.set_xlabel("2022年のパート時給 ÷ 最低賃金（倍）"); ax.set_ylabel("パート時給の伸び 2022→2025年（%）")
ax.set_title("最低賃金に近い（倍率が低い）ところほど、パートの時給は少し速く上がった"); ax.legend(frameon=False, loc="lower left")
save(fig, "fig6_reask_bite.png", SRC + "、地域別最低賃金。産業は公表の前年比をつないだ値、規模は実数から計算")
print("ok")
