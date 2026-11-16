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
SRC = "出典：経済産業省「平成19年商業統計表 第1巻 産業編（総括表）」第1表をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
t = pd.read_csv(RES / "retail_total_by_year.csv", dtype={"year": str}).set_index("year")
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)
Y1 = ["1982", "1985", "1988", "1991"]; Y2 = ["1991r", "1994", "1997", "1999", "2002", "2004", "2007"]
X = lambda ys: [1991 if y == "1991r" else int(y) for y in ys]

# 図1：個人と法人の事業所数
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.84, top=0.83, bottom=0.14)
for col, c, lab in [("est_indiv", C6[1], "個人経営の店"), ("est_corp", C6[0], "法人（会社など）の店")]:
    ax.plot(X(Y1), t.loc[Y1, col] / 1e4, color=c, lw=1.4, ls=":", marker="o", ms=3)
    ax.plot(X(Y2), t.loc[Y2, col] / 1e4, color=c, lw=2, marker="o", ms=4)
    ax.text(2007.6, t.loc["2007", col] / 1e4 + (4 if col == "est_indiv" else -4), lab, fontsize=9, va="center", color=c)
ax.set_ylabel("小売業の事業所数（万）"); ax.set_xlabel("調査年"); ax.set_ylim(0, 140); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
M = m["main"]
fig.suptitle("小売の店の減少は、ほぼ全部が個人の店だった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"1991→2007年：個人 {M['indiv'][0]/1e4:.1f}万→{M['indiv'][1]/1e4:.1f}万、法人 {M['corp'][0]/1e4:.1f}万→{M['corp'][1]/1e4:.1f}万。点線は1991年の分類の組み替え前", fontsize=9, color=INK2)
save(fig, "fig1_establishments_indiv_corp.png")

# 図2：店の数・売場面積・1店当たり売場面積（1991年=100）
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.8, top=0.83, bottom=0.14)
b = t.loc["1991r"]
series = [("est_total", C6[1], "事業所数"), ("floor_m2", C6[2], "売場面積"), (None, C6[0], "1店当たり売場面積")]
for col, c, lab in series:
    s = (t.loc[Y2, "floor_m2"] / t.loc[Y2, "est_total"]) / (b.floor_m2 / b.est_total) * 100 if col is None else t.loc[Y2, col] / b[col] * 100
    ax.plot(X(Y2), s, color=c, lw=2, marker="o", ms=4); ax.text(2007.6, s.iloc[-1], lab, fontsize=9, va="center", color=c)
ax.axhline(100, color=GRAY, lw=0.6, ls=":")
ax.set_ylabel("指数（1991年＝100）"); ax.set_xlabel("調査年"); ax.set_ylim(50, 210); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("店は減り、売場は広がった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"小売業計。1991→2007年（対数差×100）：売場面積 {M['floor_dlog']:+.0f}、1店当たり {M['floor_per_est'][0]:.0f}㎡→{M['floor_per_est'][1]:.0f}㎡（{M['floor_per_est_dlog']:+.0f}）、販売額 {M['sales_dlog']:+.0f}", fontsize=9, color=INK2)
save(fig, "fig2_floor_and_count.png")

# 図3：業種ごとの売場面積の伸びと個人の店の伸び
p = pd.read_csv(RES / "industry_panel_1991r_2007.csv", dtype={"code": str})
fig, ax = plt.subplots(figsize=(8.4, 5.2)); fig.subplots_adjust(left=0.1, right=0.97, top=0.83, bottom=0.14)
ax.scatter(p.dx, p.di, s=8 + 300 * p.i0 / p.i0.max(), color=C6[0], alpha=0.55, edgecolor="white", lw=0.8)
H = m["H3"]; xs = np.linspace(p.dx.min(), p.dx.max(), 50)
a = np.average(p.di, weights=p.i0) - H["slope"] * np.average(p.dx, weights=p.i0)
ax.plot(xs, a + H["slope"] * xs, color=INK2, lw=1.2)
for _, r in p.sort_values("i0", ascending=False).head(4).iterrows():
    ax.annotate(r["name"].replace("（製造小売でないもの）", "").replace("（調剤薬局を除く）", ""), (r.dx, r.di), xytext=(6, 4), textcoords="offset points", fontsize=8, color=INK2)
ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("売場面積の伸び（1991→2007年、対数差×100）"); ax.set_ylabel("個人経営の店の数の伸び（対数差×100）"); ax.grid(color="#e6e5e1", lw=0.5)
fig.suptitle("売場が広がった業種ほど個人の店が減った、とは言えない", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"小売業の細分類 {H['n']} 業種。円の大きさは1991年の個人の店の数。重みつきの傾き {H['slope']:+.2f}（p={H['p']:.2f}）", fontsize=9, color=INK2)
save(fig, "fig3_industry_scatter.png")

# 図4：個人の店の割合（中分類、1991→2007年）
bm = m["by_major"]; codes = list(bm)
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.32, right=0.95, top=0.82, bottom=0.15)
for k, c in enumerate(codes):
    s0 = 100 * bm[c]["indiv"][0] / (bm[c]["indiv"][0] + bm[c]["corp"][0]); s1 = 100 * bm[c]["indiv"][1] / (bm[c]["indiv"][1] + bm[c]["corp"][1])
    ax.plot([s0, s1], [k, k], color=GRAY, lw=1.5)
    ax.scatter([s0], [k], color=GRAY, s=40, zorder=3); ax.scatter([s1], [k], color=C6[0], s=40, zorder=3)
    ax.text(s1 - 1.5, k + 0.18, f"{s1:.0f}%", fontsize=8.5, ha="right"); ax.text(s0 + 1.5, k + 0.18, f"{s0:.0f}%", fontsize=8.5, color=INK2)
ax.set_yticks(range(len(codes))); ax.set_yticklabels([bm[c]["name"] for c in codes]); ax.invert_yaxis()
ax.set_xlim(0, 85); ax.set_xlabel("店の数に占める個人経営の割合（%）"); ax.grid(axis="x", color="#e6e5e1", lw=0.6)
ax.scatter([], [], color=GRAY, label="1991年"); ax.scatter([], [], color=C6[0], label="2007年"); ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.suptitle("どの業種の中でも、個人の店の割合は下がった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"細分類 {q['n_industries']} 業種のうち {q['n_indiv_share_fell']} 業種で下がった。全体の下がり方 {q['indiv_share_change']:.1f}ポイントのうち、業種の中の変化が {q['within']:.1f}", fontsize=9, color=INK2)
save(fig, "fig4_indiv_share_by_group.png")
print("ok")
