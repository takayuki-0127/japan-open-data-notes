import json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import DATA, RES, FIG
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, C3, GR = "#2a6f97", "#c8553d", "#6a994e", "#888888"
MODL = {"low_wage": "平均時給の低さ", "bite": "最低賃金÷平均時給", "low_mw": "最低賃金の低さ"}
OUTL = {"wage": "短時間労働者の時給\n（前年比 %）", "emp": "就業率\n（前年差 %pt）", "unemp": "完全失業率\n（前年差 %pt）", "workers": "短時間労働者の数\n（前年比 %）"}

# 図1 長い差
L = pd.read_csv(RES / "long_diff.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
for a, col, yl, c in [(ax[0], "dlw_11_19", "短時間労働者の時給の伸び（2011→19年、%）", C1), (ax[1], "demp_11_19", "就業率の変化（2011→19年、%pt）", C2)]:
    a.scatter(L.wage0, L[col], s=28, color=c, alpha=.8)
    b = np.polyfit(L.wage0, L[col], 1); xs = np.linspace(L.wage0.min(), L.wage0.max(), 10)
    a.plot(xs, np.polyval(b, xs), color=GR, lw=1.2)
    r = np.corrcoef(L.wage0, L[col])[0, 1]
    a.set_xlabel("2009〜11年の短時間労働者の平均時給（円）"); a.set_ylabel(yl); a.set_title(f"相関 {r:+.2f}", fontsize=11)
fig.suptitle("図1　時給が低かった県ほど時給はやや大きく伸びたが、就業率の変化とはほぼ無関係（47都道府県）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig1_long_diff.png", dpi=150); plt.close(fig)

# 図2 使える変動
w = pd.read_csv(DATA / "panel_wage.csv"); w = w[w.year.between(2010, 2025)]
g = w.groupby("year").dlmw.agg(["mean", "std"])
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.bar(g.index - 0.2, g["mean"], width=0.4, color=C1, label="全国平均の引き上げ（%）＝(A)が使う変動")
ax.bar(g.index + 0.2, g["std"], width=0.4, color=C2, label="同じ年の中の県によるばらつき（標準偏差）＝(B)が使う変動")
ax.set_xlabel("賃金の調査年（6月。最低賃金は前年度の額）"); ax.set_ylabel("最低賃金の前年比（%）")
ax.legend(frameon=False, fontsize=10); ax.set_title("図2　県による上げ幅の違いは、全国の引き上げの1割前後しかない", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig2_variation.png", dpi=150); plt.close(fig)

# 図3 交互作用（基本）
m = pd.read_csv(RES / "interaction_main.csv")
fig, ax = plt.subplots(1, 3, figsize=(12, 4.2))
for a, o in zip(ax, ["wage", "emp", "unemp"]):
    s = m[m.outcome == o].reset_index(drop=True)
    for i, r in s.iterrows():
        a.errorbar(r.b, i, xerr=1.96 * r.se, fmt="o", color=[C1, C2, C3][i], capsize=3)
    a.axvline(0, color=GR, lw=1); a.set_yticks(range(len(s))); a.set_yticks(range(3)); a.set_yticklabels([MODL[x] for x in s["mod"]] if o == "wage" else ["", "", ""])
    a.set_title(OUTL[o].replace("\n", ""), fontsize=11); a.invert_yaxis()
ax[1].set_xlabel("全国1%の引き上げあたり、賃金の低さが1標準偏差大きい県での差（95%区間）")
fig.suptitle("図3　(A) 全国の引き上げ×県の賃金の低さ：時給は「最低賃金の低い県」で大きく動き、雇用は弱い差", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig3_interaction.png", dpi=150); plt.close(fig)

# 図4 頑健性
rb = pd.read_csv(RES / "robustness.csv")
keys = [("wage", "low_mw", "時給 × 最低賃金の低さ"), ("emp", "bite", "就業率 × 最低賃金÷平均時給"), ("unemp", "low_wage", "失業率 × 平均時給の低さ")]
fig, ax = plt.subplots(1, 3, figsize=(13, 4.8))
for a, (o, md, t) in zip(ax, keys):
    s = rb[(rb.outcome == o) & (rb["mod"] == md)].reset_index(drop=True)
    for i, r in s.iterrows():
        c = C2 if "地方×年" in r.spec else C1
        a.errorbar(r.b, i, xerr=1.96 * r.se, fmt="o", color=c, capsize=3)
    a.axvline(0, color=GR, lw=1); a.set_yticks(range(len(s)))
    a.set_yticklabels([x.replace("（同じ地方の中だけで比べる）", "\n（同じ地方の中で比べる）").replace("（2020年の断絶は除く）", "") for x in s.spec], fontsize=9)
    a.invert_yaxis(); a.set_title(t, fontsize=11)
fig.suptitle("図4　頑健性：雇用の差は「同じ地方の中」で比べると消える（赤）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig4_robustness.png", dpi=150); plt.close(fig)

# 図5 プラセボ
td = pd.read_csv(RES / "placebo_t_draws.csv"); pp = pd.read_csv(RES / "placebo_year_permutation.csv")
fig, ax = plt.subplots(1, 3, figsize=(12, 3.9))
for a, (o, md, t) in zip(ax, keys):
    x = td[(td.outcome == o) & (td["mod"] == md)].t; r = pp[(pp.outcome == o) & (pp["mod"] == md)].iloc[0]
    a.hist(x, bins=30, color="#bbbbbb"); a.axvline(r.t_obs, color=C2, lw=2)
    a.set_title(f"{t}\n実際の t={r.t_obs:.2f}、並べ替えで同じ以上 {r.p_perm*100:.0f}%", fontsize=10)
    a.set_xlabel("年を並べ替えたときの t 値（300回）")
fig.suptitle("図5　プラセボ：全国の引き上げの年をでたらめに並べ替えても、t 値はしばしば±2を超える", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig5_placebo.png", dpi=150); plt.close(fig)

# 図6 森
cv = pd.read_csv(RES / "forest_curve.csv"); bl = pd.read_csv(RES / "forest_blp.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
for a, o, c, yl in [(ax[0], "wage", C1, "時給の前年比（%）／最低賃金1%"), (ax[1], "emp", C2, "就業率の前年差（%pt）／最低賃金1%")]:
    s = cv[cv.outcome == o]; r = bl[bl.outcome == o].iloc[0]
    a.plot(s.low_wage, s.cate, color=c); a.fill_between(s.low_wage, s.lo, s.hi, color=c, alpha=.2); a.axhline(0, color=GR, lw=1)
    a.set_xlabel("平均時給の低さ（標準化、右ほど低い）"); a.set_ylabel(yl)
    a.set_title(f"地方を外した検証 p={r.blp_p:.2f}", fontsize=11)
fig.suptitle("図6　(B) 同じ年の中の上げ幅の違いだけを使う因果フォレスト：効果の差は区間の中に埋もれる", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig6_forest.png", dpi=150); plt.close(fig)
print("ok")
