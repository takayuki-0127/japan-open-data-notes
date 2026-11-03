"""04 図: results/ と data/panel_units.csv から図を作る"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for fp in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    font_manager.fontManager.addfont(fp)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
C1, C2, C3, C4, GR = "#2b6cb0", "#dd6b20", "#38a169", "#805ad5", "#a0aec0"
conc = pd.read_csv(RES / "concentration_by_year.csv")
R = json.load(open(RES / "results.json"))
SRC = "出典：総務省「住民基本台帳に基づく人口、人口動態及び世帯数」（各年1月1日）をもとに作成"

# ---- 図1 人数と集中度の推移 ----
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
a = ax[0]
a.bar(conc.year, conc.foreign / 1e4, color=C1, alpha=.85)
a.set_title("外国人住民の数（各年1月1日）", loc="left")
a.set_ylabel("万人")
for y, v, s in zip(conc.year, conc.foreign, conc.share):
    if y in (2014, 2020, 2022, 2026):
        a.text(y, v / 1e4 + 6, f"{v/1e4:.0f}万人\n({s*100:.1f}%)", ha="center", fontsize=8.5)
a.set_ylim(0, 470)
a = ax[1]
a.plot(conc.year, conc.D_muni, "o-", color=C2, label="市区町村単位")
a.plot(conc.year, conc.D_pref, "s--", color=C4, label="都道府県単位")
a.set_title("日本人との住む場所の違い（非類似度指数 D）", loc="left")
a.set_ylabel("D（0＝同じ分布、1＝完全に別）")
a.set_ylim(0.15, 0.34)
a.legend(frameon=False)
for y in (2014, 2026):
    v = conc.set_index("year").loc[y, "D_muni"]
    a.annotate(f"{v:.3f}", (y, v), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
fig.text(0.01, 0.0, SRC + "。( ) 内は総人口に占める割合", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(FIG / "fig1_trend_and_D.png", dpi=150)
plt.close(fig)

# ---- 図2 ローレンツ曲線 ----
p = pd.read_csv(ROOT / "data/panel_units.csv", dtype={"code5": str})
fig, ax = plt.subplots(figsize=(5.8, 5.4))
for y, c in [(2014, GR), (2020, C4), (2026, C2)]:
    g = p[p.year == y]
    s = g.pop_for / g.pop_tot
    o = np.argsort(s.values)
    x = np.concatenate([[0], np.cumsum(g.jp.values[o]) / g.jp.sum()])
    yy = np.concatenate([[0], np.cumsum(g.pop_for.values[o]) / g.pop_for.sum()])
    gi = conc.set_index("year").loc[y, "gini_muni"]
    ax.plot(x, yy, color=c, lw=2, label=f"{y}年（ジニ係数 {gi:.3f}）")
ax.plot([0, 1], [0, 1], color="#333", lw=.8, ls=":")
ax.set_xlabel("日本人住民の累積割合（外国人の割合が低い市区町村から順に）")
ax.set_ylabel("外国人住民の累積割合")
ax.set_title("市区町村のローレンツ曲線", loc="left")
ax.legend(frameon=False, loc="upper left")
ax.text(0.98, 0.04, "対角線に近いほど\n日本人と同じように分布", ha="right", fontsize=9, color="#555", transform=ax.transAxes)
fig.text(0.01, 0.005, "出典：総務省「住民基本台帳に基づく人口…」をもとに作成", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "fig2_lorenz.png", dpi=150)
plt.close(fig)

# ---- 図3 増え方：初めの割合・人口規模・地域×種類 ----
gq = pd.read_csv(RES / "growth_by_initial_ratio_quintile.csv")
gs = pd.read_csv(RES / "growth_by_size.csv")
ga = pd.read_csv(RES / "growth_by_area_type.csv")
fig, ax = plt.subplots(1, 3, figsize=(13, 4.4), gridspec_kw={"width_ratios": [1, 1, 1.5]})
a = ax[0]
lab = ["最も低い\n20%", "2", "3", "4", "最も高い\n20%"]
a.bar(range(5), gq.growth * 100, color=C1)
a.set_xticks(range(5), lab)
a.set_title("2014年の外国人の割合（5分位）別", loc="left", fontsize=11)
a.set_ylabel("2014→2026年の増加率（%）")
for i, v in enumerate(gq.growth):
    a.text(i, v * 100 + 4, f"+{v*100:.0f}%", ha="center", fontsize=9)
a = ax[1]
a.bar(range(4), gs.growth * 100, color=C3)
a.set_xticks(range(4), ["1万人\n未満", "1万〜\n5万人", "5万〜\n20万人", "20万人\n以上"])
a.set_title("2014年の人口規模別", loc="left", fontsize=11)
for i, v in enumerate(gs.growth):
    a.text(i, v * 100 + 4, f"+{v*100:.0f}%", ha="center", fontsize=9)
a = ax[2]
areas = ["東京圏", "名古屋圏", "大阪圏", "地方圏"]
types = ["特別区・政令市の区", "市", "町村"]
cols = [C4, C1, C2]
w = 0.26
for k, t in enumerate(types):
    vals = [ga[(ga.area == ar) & (ga.mtype == t)].growth.values[0] * 100 for ar in areas]
    a.bar(np.arange(4) + (k - 1) * w, vals, w, color=cols[k], label=t)
a.set_xticks(range(4), areas)
a.axhline(R["national_growth"] * 100, color="#333", lw=.8, ls=":")
a.text(-0.45, R["national_growth"] * 100 + 3, f"全国 +{R['national_growth']*100:.0f}%", ha="left", fontsize=8.5)
a.set_title("地域 × 市区町村の種類別", loc="left", fontsize=11)
a.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=3)
for a in ax:
    a.set_ylim(0, 250)
fig.text(0.01, 0.0, "出典：総務省「住民基本台帳に基づく人口…」（2014年・2026年1月1日）をもとに作成。地域：東京圏＝埼玉・千葉・東京・神奈川、名古屋圏＝岐阜・愛知・三重、大阪圏＝京都・大阪・兵庫・奈良", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(FIG / "fig3_growth_speed.png", dpi=150)
plt.close(fig)

# ---- 図4 増え方の分解 ----
yr = pd.read_csv(RES / "flows_by_year_national.csv")
fat = pd.read_csv(RES / "flows_by_area_type.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 5.0), gridspec_kw={"width_ratios": [1.2, 1]})
a = ax[0]
x = yr.year.values
comp = [("net_abr", "国外との転入−転出", C1), ("natural", "出生−死亡", C3),
        ("net_dom", "国内の転入−転出", C4), ("other", "その他（職権による記載・消除、帰化など）", C2)]
pos = np.zeros(len(x)); neg = np.zeros(len(x))
for k, lab, c in comp:
    v = yr[k].values / 1e4
    bottom = np.where(v >= 0, pos, neg)
    a.bar(x, v, bottom=bottom, color=c, label=lab, width=.75)
    pos = pos + np.where(v >= 0, v, 0); neg = neg + np.where(v < 0, v, 0)
a.plot(x, yr.flow_total / 1e4, "k_", ms=14, mew=2.2, label="増減（合計）")
a.axhline(0, color="#333", lw=.6)
a.set_ylabel("万人")
a.set_title("全国の外国人住民の増減の内訳（各年中）", loc="left")
a.legend(frameon=False, fontsize=8, loc="upper left")
a.set_ylim(-22, 58)
a = ax[1]
labels = []
abr, oth, dom, nat = [], [], [], []
for ar in ["東京圏", "名古屋圏", "大阪圏", "地方圏"]:
    for t, tl in [("特別区・政令市の区", "区"), ("市", "市"), ("町村", "町村")]:
        r = fat[(fat.area == ar) & (fat.mtype == t)].iloc[0]
        labels.append(f"{ar}・{tl}")
        abr.append(r.net_abr_per_stock14); oth.append(r.other_per_stock14)
        dom.append(r.net_dom_per_stock14); nat.append(r.natural_per_stock14)
yy = np.arange(len(labels))[::-1]
a.barh(yy, abr, color=C1, label="国外との転入−転出")
a.barh(yy, oth, color=C2, label="その他")
left_pos = np.array(abr); left_neg = np.array(oth)
dom = np.array(dom)
a.barh(yy, np.where(dom >= 0, dom, 0), left=left_pos, color=C4, label="国内の転入−転出")
a.barh(yy, np.where(dom < 0, dom, 0), left=left_neg, color=C4)
a.set_yticks(yy, labels, fontsize=8.5)
a.axvline(0, color="#333", lw=.6)
a.set_xlabel("2014〜2025年の累計 ÷ 2014年1月1日の外国人住民数")
a.set_title("地域 × 種類別の累計（初めの人数あたり）", loc="left")
a.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.45, -0.13), ncol=3)
fig.text(0.01, 0.0, "出典：総務省「住民基本台帳に基づく人口、人口動態及び世帯数」（外国人住民）をもとに作成。出生−死亡は右図では小さいため省略", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(FIG / "fig4_flow_decomposition.png", dpi=150)
plt.close(fig)

# ---- 図5 国籍・地域別の集中度 ----
nd = pd.read_csv(RES / "nationality_concentration.csv")
order = nd[nd.year == 2022].sort_values("D").nat.tolist()
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6))
a = ax[0]
for i, n in enumerate(order):
    d15 = nd[(nd.year == 2015) & (nd.nat == n)].D.values[0]
    d22 = nd[(nd.year == 2022) & (nd.nat == n)].D.values[0]
    a.plot([d15, d22], [i, i], color=GR, lw=2)
    a.scatter(d15, i, color=GR, zorder=3, s=36)
    a.scatter(d22, i, color=C2 if n != "総数" else "#000", zorder=3, s=46)
a.set_yticks(range(len(order)), order)
a.scatter([], [], color=GR, label="2015年末"); a.scatter([], [], color=C2, label="2022年末")
a.legend(frameon=False, loc="lower right")
a.set_xlabel("日本人との住む場所の違い（非類似度指数 D）")
a.set_title("国籍・地域別の D（市区町村単位）", loc="left")
a = ax[1]
for i, n in enumerate(order):
    s15 = nd[(nd.year == 2015) & (nd.nat == n)].share_chiho.values[0]
    s22 = nd[(nd.year == 2022) & (nd.nat == n)].share_chiho.values[0]
    a.plot([s15 * 100, s22 * 100], [i, i], color=GR, lw=2)
    a.scatter(s15 * 100, i, color=GR, zorder=3, s=36)
    a.scatter(s22 * 100, i, color=C1 if n != "総数" else "#000", zorder=3, s=46)
a.axvline(R["concentration"][0]["share_chiho_pop"] * 100, color="#333", lw=.8, ls=":")
a.text(R["concentration"][0]["share_chiho_pop"] * 100 - .5, len(order) - 1.4, "総人口の\n地方圏の割合\n（約47〜49%）", fontsize=8, ha="right")
a.set_yticks(range(len(order)), order)
a.set_xlabel("地方圏に住む割合（%）")
a.set_title("国籍・地域別の地方圏に住む割合", loc="left")
fig.text(0.01, 0.0, "出典：出入国在留管理庁「在留外国人統計」（市区町村別 国籍・地域別、2015年末・2022年末）、総務省「住民基本台帳に基づく人口…」をもとに作成。国籍・地域の区分は公表表の区分", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(FIG / "fig5_nationality.png", dpi=150)
plt.close(fig)
print("figs done")
