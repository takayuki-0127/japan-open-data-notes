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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「公共施設状況調経年比較表」（市町村）、「人口推計」をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.95, top=0.89, bottom=0.15)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
n = pd.read_csv(R / "national_by_year.csv", index_col=0)
x = n.loc[2011:]

# 図1
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c in [("m2_per_person", "人口1人あたりの延面積", C[1]), ("bld_admin_total", "建物の延面積（全国の合計）", C[0]), ("pop_thousand", "人口", C[2])]:
    v = 100 * x[col] / x[col][2011]
    ax.plot(v.index, v, color=c, lw=2.3, marker="o", ms=4.5, label=lab)
    ax.annotate(f"{v.iloc[-1]:.1f}", (v.index[-1], v.iloc[-1]), textcoords="offset points", xytext=(7, 0), va="center", fontsize=9, color=INK)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlim(2010.5, 2025.3)
ax.set_xlabel("年度")
ax.set_ylabel("指数（2011年度＝100）")
ax.legend(frameon=False, loc="upper left")
rb0 = pd.read_csv(R / "robustness.csv").iloc[0]
finish(fig, ax, f"人口は{-rb0.pop_change_pct:.2f}%減ったが、市町村の建物の延面積は{rb0.area_change_pct:.1f}%増。1人あたりは{rb0.per_capita_change_pct:.1f}%増")
save(fig, "fig1_area_population.png")

# 図2：用途別
u = m["use_change_pct"]
labs = [("bld_school", "学校（小・中・義務教育）"), ("bld_housing", "公営住宅"), ("bld_honchosha", "本庁舎"), ("bld_public_other", "その他の公共用の施設")]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
vals = [u[k] for k, _ in labs]
ax.barh(range(len(labs)), vals, color=[C[0] if v < 0 else C[1] for v in vals], height=0.55)
for i, v in enumerate(vals):
    ax.text(v + (0.3 if v >= 0 else -0.3), i, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=10, color=INK)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(range(len(labs)), [l for _, l in labs])
ax.invert_yaxis()
ax.set_xlim(-6, 15)
ax.set_xlabel("建物の延面積の変化（2011→2024年度、%）")
finish(fig, ax, "学校は減ったが、本庁舎・公営住宅・その他の施設は増えた", grid="x")
fig.subplots_adjust(left=0.24)
save(fig, "fig2_by_use.png")

# 図3：県別の散布図
p = pd.read_csv(R / "pref_change_2011_2024.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.scatter(p.pop_change_pct, p.bld_admin_total_pc_change_pct, s=40, color=C[0], edgecolor="#fcfcfb", lw=1.5, zorder=3)
b, a = np.polyfit(p.pop_change_pct, p.bld_admin_total_pc_change_pct, 1)
xx = np.linspace(p.pop_change_pct.min(), p.pop_change_pct.max(), 10)
ax.plot(xx, a + b * xx, color=C[1], lw=1.8, label=f"当てはめた直線（傾き {b:.2f}）")
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
h3 = m["hypotheses"]["H3"]
ax.text(0.98, 0.95, f"相関係数 {h3['pearson']:.2f}（順位の相関 {h3['spearman']:.2f}）", transform=ax.transAxes, ha="right", fontsize=9.5, color=INK)
ax.set_xlabel("人口の変化（2011→2024年度、%）　※点は47都道府県")
ax.set_ylabel("人口1人あたりの延面積の変化（%）")
ax.legend(frameon=False, loc="lower left")
finish(fig, ax, "人口が減った県ほど、1人あたりの延面積が増えた", grid="both")
save(fig, "fig3_pref_scatter.png")

# 図4：施設の数
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for (col, lab), c in zip([("kokaido_n", "公会堂・市民会館"), ("toshokan_n", "図書館"), ("taiikukan_n", "体育館"), ("shisho_n", "支所・出張所"), ("jidokan_n", "児童館"), ("kominkan_n", "公民館")], C):
    v = 100 * n[col] / n[col][2006]
    ax.plot(v.index, v, color=c, lw=2.0, marker="o", ms=3.5, label=f"{lab}（{int(n[col][2006]):,}→{int(n[col].iloc[-1]):,}）")
    ax.annotate(f"{v.iloc[-1]:.0f}", (v.index[-1], v.iloc[-1]), textcoords="offset points", xytext=(7, 0), va="center", fontsize=9, color=INK)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlim(2005.5, 2025.5)
ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(3))
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, q: f"{v:.0f}"))
ax.set_xlabel("年度")
ax.set_ylabel("施設の数の指数（2006年度＝100）")
ax.legend(frameon=False, loc="lower left", fontsize=9, ncol=2)
finish(fig, ax, "公民館は4分の1減ったが、図書館・体育館・市民会館は増えた")
save(fig, "fig4_facility_counts.png")
