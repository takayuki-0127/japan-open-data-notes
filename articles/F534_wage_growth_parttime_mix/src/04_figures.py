"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f534"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：厚生労働省「毎月勤労統計調査」全国調査 実数（調査産業計、年平均）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
d = pd.read_csv(ROOT / "data" / "maikin_tl_cy.csv", dtype={"size_code": str, "form_code": str})
P = pd.read_csv(R / "panel_5plus.csv", index_col=0)
idx = pd.read_csv(R / "index_1993.csv")
dec = pd.read_csv(R / "decomp_5plus.csv")
rq = pd.read_csv(R / "requestion_by_size.csv")

# 図1：パートの割合
fig, ax = plt.subplots(figsize=(9, 5.2))
t30 = d[(d.size_code == "0") & (d.form_code == "0")].set_index("year")
ax.plot(P.index, 100 * P.p, color=C[0], lw=2.4, label="5人以上（本線）")
ax.plot(t30.index, 100 * t30.part_workers / t30.workers, color=C[1], lw=1.8, ls="--", label="30人以上")
for y in [1993, 2025]:
    ax.annotate(f"{100*P.loc[y,'p']:.1f}%", (y, 100 * P.loc[y, "p"]), textcoords="offset points",
                xytext=(6, -3) if y == 2025 else (4, 8), fontsize=9.5, color=C[0], ha="left")
ax.set_ylabel("パートタイム労働者の割合（%）"); ax.set_ylim(0, 36); ax.set_xlim(1992, 2028); ax.legend(frameon=False, loc="upper left")
finish(fig, ax, f"パートの割合は1993年 {100*m['p_1993']:.1f}% → 2025年 {100*m['p_2025']:.1f}%（5人以上）")
save(fig, "fig1_part_share.png")

# 図2：指数
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.plot(idx.year, idx.published, color=INK, lw=2.6, label="公表の平均（就業形態計）")
ax.plot(idx.year, idx.fixed1993, color=C[0], lw=2.2, label="パートの割合を1993年に固定")
ax.plot(idx.year, idx.general, color=C[2], lw=1.6, ls="--", label="一般労働者")
ax.plot(idx.year, idx.part, color=C[1], lw=1.6, ls=":", label="パートタイム労働者")
e = idx.iloc[-1]
for col, c in [("published", INK), ("fixed1993", C[0])]:
    ax.text(2025.4, e[col], f"{e[col]:.1f}", color=c, fontsize=9.5, va="center")
ax.axhline(100, color=INK2, lw=0.8)
ax.set_xlim(1992, 2028); ax.set_ylabel("1人あたり現金給与総額（1993年＝100）")
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
finish(fig, ax, f"割合を固定すると +{m['growth_fixed1993']:.1f}%、公表の平均は +{m['growth_published']:.1f}%（1993→2025年）")
save(fig, "fig2_index_fixed_vs_published.png")

# 図3：年ごとの分解
fig, ax = plt.subplots(figsize=(9, 5.2))
x = dec.year.values
wi = (dec.within_general + dec.within_part).values; co = dec.composition.values
ax.bar(x, np.where(wi > 0, wi, 0), color=C[2], width=0.75, label="一般・パートそれぞれの賃金の変化")
ax.bar(x, np.where(wi < 0, wi, 0), color=C[2], width=0.75)
ax.bar(x, co, bottom=np.where(co < 0, np.minimum(wi, 0), np.maximum(wi, 0)), color=C[1], width=0.75, label="パートの割合の変化")
ax.plot(x, dec.published, color=INK, marker="o", ms=3.5, lw=1.2, label="公表の平均の前年比")
ax.axhline(0, color=INK2, lw=0.8)
for a, b, k in [(1994, 2007, "comp_mean_1994_2007"), (2014, 2025, "comp_mean_2014_2025")]:
    ax.annotate(f"割合の変化の平均\n{m[k]:+.2f}%/年", ((a + b) / 2, -5.2), ha="center", fontsize=9, color=C[1])
ax.set_ylim(-6.2, 7.2); ax.set_ylabel("前年比（%）への寄与"); ax.legend(frameon=False, loc="upper left", fontsize=9)
finish(fig, ax, "パートの割合の変化による押し下げは、2014年以降に小さくなった")
save(fig, "fig3_yearly_decomposition.png")

# 図4：規模別（問い直し）
fig, ax = plt.subplots(figsize=(9, 5.2))
yy = np.arange(len(rq))
ax.barh(yy + 0.2, rq.growth_fixed1993, height=0.38, color=C[0], label="パートの割合を1993年に固定")
ax.barh(yy - 0.2, rq.growth_published, height=0.38, color=INK2, label="公表の平均")
for i, r in rq.iterrows():
    ax.text(r.growth_fixed1993 + 0.4, i + 0.2, f"{r.growth_fixed1993:+.1f}%", va="center", fontsize=9)
    ax.text(max(r.growth_published, 0) + 0.4, i - 0.2, f"{r.growth_published:+.1f}%（割合 {100*r.p_1993:.0f}→{100*r.p_2025:.0f}%）", va="center", fontsize=9)
ax.set_yticks(yy, rq["size"]); ax.invert_yaxis(); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-9, 30); ax.set_xlabel("1993→2025年の伸び（%）"); ax.legend(frameon=False, loc="lower right", fontsize=9)
finish(fig, ax, "小さい事業所ほどパートの割合が増え、公表の平均の伸びが低く見える", grid="x")
fig.subplots_adjust(left=0.14)
save(fig, "fig4_by_size.png")
print("ok")
