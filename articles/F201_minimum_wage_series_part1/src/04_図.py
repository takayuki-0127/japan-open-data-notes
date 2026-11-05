import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RAW, RES, FIG, DATA, setup_font

setup_font()
C1, C2, C3, CG = "#1f5f8b", "#d1495b", "#edae49", "#8d99ae"
main = json.load(open(RES / "main.json"))

# 図1 全国の影響率・未満率
imp = pd.read_csv(RAW / "national_impact_rate.csv")
sp = pd.read_csv(RAW / "national_impact_rate_special_tab.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(imp.year, imp.impact_rate_pct, "-o", color=C1, label="影響率（改定後の最低賃金を下回ることになる人の割合）")
ax.plot(imp.year, imp.undercoverage_rate_pct, "-o", color=CG, ms=4, label="未満率（改定前の最低賃金をすでに下回っている人の割合）")
ax.plot(sp.year, sp.impact_rate_pct, "s--", color=C2, label="影響率（賃金構造基本統計調査の特別集計・5人以上の事業所）")
ax.annotate("2020年は引き上げが\nほぼ0円（+1円）", (2020, 4.7), (2015.3, 2.5), arrowprops=dict(arrowstyle="->", color="gray"), fontsize=9)
ax.set_ylabel("%"); ax.set_xticks(range(2005, 2025, 3))
ax.set_title("最低賃金の「影響率」は20年で1.6%→23.2%（最低賃金に関する基礎調査）", fontsize=11)
ax.legend(fontsize=8.5, loc="upper left"); ax.grid(alpha=.3)
fig.text(0.01, 0.01, "出典：厚生労働省「最低賃金に関する基礎調査」（30人未満の事業所ほか）・「賃金構造基本統計調査特別集計」\n（中央最低賃金審議会 目安に関する小委員会の資料から転記）", fontsize=7, color="gray")
fig.tight_layout(rect=(0, .06, 1, 1)); fig.savefig(FIG / "fig1_impact_rate.png"); plt.close(fig)

# 図2 県のカイツ指標
k = pd.read_csv(RES / "kaitz_by_year.csv"); kt = pd.read_csv(RES / "kaitz_by_tercile.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.fill_between(k.year, k["min"], k["max"], color=CG, alpha=.25, label="47都道府県の最小〜最大")
ax.plot(k.year, k["median"], "-o", color="black", ms=4, label="中央値")
for g, c in zip(["高", "中", "低"], [C2, C3, C1]):
    lab = {"高": "最低賃金が平均時給に近い県（bite 上位1/3）", "中": "中位1/3", "低": "遠い県（bite 下位1/3）"}[g]
    ax.plot(kt.index, kt[g], "-", color=c, lw=1.6, label=lab)
ax.axvspan(2019.5, 2020.5, color="gray", alpha=.15); ax.text(2020, 0.47, "2020年に\n調査の作り方\nが変わる", ha="center", fontsize=8)
ax.set_ylabel("最低賃金 ÷ 短時間労働者の平均時給"); ax.set_ylim(0.43, 0.85)
ax.set_title("短時間労働者の平均時給に対する最低賃金の高さ（県別、カイツ指標）", fontsize=11)
ax.legend(fontsize=8, loc="lower left", ncol=2); ax.grid(alpha=.3)
fig.text(0.01, 0.01, "出典：厚生労働省「賃金構造基本統計調査」短時間労働者 都道府県別（10人以上、産業計・男女計）、地域別最低賃金（6月時点の額）", fontsize=7, color="gray")
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(FIG / "fig2_kaitz_pref.png"); plt.close(fig)

# 図3 推定の方法を並べる（就業率、10%あたり）
t = pd.read_csv(RES / "method_comparison.csv")
sel = [("差の差（二方向固定効果）", "2008–25（2020–22除く）"), ("差の差＋県別トレンド", "2008–25（2020–22除く）"),
       ("隣り合う県の比較", "2008–25（2020–22除く）"), ("合成コントロール", "前2008–19・後2023–25")]
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.4), sharey=True)
for ax, y, ttl in zip(axes, ["emp_rate", "unemp_rate"], ["就業率（%pt）", "完全失業率（%pt）"]):
    for i, (m, s) in enumerate(sel):
        r = t[(t.method == m) & (t["sample"] == s) & (t.outcome == y)].iloc[0]
        ax.errorbar(r.per10, i, xerr=[[r.per10 - r.lo], [r.hi - r.per10]], fmt="o", color=[C1, C3, C2, "purple"][i], capsize=4, ms=7)
        ax.text(r.hi + 0.05, i, f"{r.per10:+.2f}", va="center", fontsize=9)
    ax.axvline(0, color="gray", lw=1); ax.set_title(ttl, fontsize=11); ax.grid(alpha=.3, axis="x")
axes[0].set_yticks(range(len(sel))); axes[0].set_yticklabels([s[0] for s in sel], fontsize=9.5); axes[0].invert_yaxis()
fig.suptitle("同じ県×年のデータで4つの方法を並べると（最低賃金10%上昇あたり、95%区間）", fontsize=11.5)
fig.text(0.01, 0.01, "就業率・失業率は労働力調査の都道府県別モデル推計値ほか（F01 のパネル）。合成コントロールの区間は並べ替え200回の標準偏差から", fontsize=7, color="gray")
fig.tight_layout(rect=(0, .04, 1, .95)); fig.savefig(FIG / "fig3_method_comparison.png"); plt.close(fig)

# 図4 使える変動と検出力
mde = pd.read_csv(RES / "mde.csv")
v = main["variation"]
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2))
lab = ["県と年を除いた残り\n（差の差）", "同じ県境の両側の差\n（隣り合う県）", "上位10県と合成県の\n上げ幅の差（合成）"]
vals = [v["twfe_resid_sd_logmw"] * 100, v["within_sd_logmw"] * 100, (main["synth_rise_top10_mean"] - main["synth_rise_bottom20_mean"]) * 100]
axes[0].bar(range(3), vals, color=[C1, C2, "purple"]); axes[0].set_xticks(range(3)); axes[0].set_xticklabels(lab, fontsize=8.5)
for i, x in enumerate(vals): axes[0].text(i, x, f"{x:.2f}%", ha="center", va="bottom", fontsize=9)
axes[0].set_ylabel("最低賃金の差の大きさ（%）"); axes[0].set_title("推定に使える「上げ幅の差」は小さい", fontsize=10.5)
mm = mde.drop_duplicates("method").copy()
sy = main["synth"]["emp_rate|上位10県 vs 下位20県"]
mm = pd.concat([mm, pd.DataFrame([{"method": "合成コントロール", "mde80": 2.8 * sy["se_perm"] / sy["dose"] * np.log(1.1)}])], ignore_index=True)
axes[1].barh(range(len(mm)), mm.mde80, color=[C1, C3, C2, "purple"][:len(mm)]); axes[1].set_yticks(range(len(mm))); axes[1].set_yticklabels(mm.method, fontsize=9)
for i, x in enumerate(mm.mde80): axes[1].text(x, i, f" {x:.2f}", va="center", fontsize=9)
axes[1].invert_yaxis(); axes[1].set_xlabel("80%の確率で見つけられる最小の差（就業率 %pt、10%あたり）")
axes[1].axvline(0.18, color="black", ls="--"); axes[1].text(0.25, -0.62, "← 雇用の弾力性 −0.3 にあたる大きさ（約0.18）", fontsize=8)
axes[1].set_title("見つけられる最小の差", fontsize=10.5, pad=20)
fig.tight_layout(); fig.savefig(FIG / "fig4_variation_mde.png"); plt.close(fig)

# 図5 合成コントロールの差の推移
g = pd.read_csv(RES / "synth_gaps_emp.csv", index_col=0)
pl = pd.read_csv(RES / "synth_placebo_emp_rate.csv")
fig, ax = plt.subplots(figsize=(8, 4.4))
for c in g.columns: ax.plot(g.index, g[c], color=CG, lw=.8, alpha=.7)
ax.plot(g.index, g.mean(1), color=C2, lw=2.5, label="上げ幅の大きい10県の平均（実際 − 合成）")
ax.axhspan(np.percentile(pl.placebo_gap, 2.5), np.percentile(pl.placebo_gap, 97.5), xmin=0.83, color=C1, alpha=.15, label="無作為に選んだ10県の後期の差（95%の範囲）")
ax.axvspan(2019.5, 2022.5, color="gray", alpha=.12); ax.text(2021, ax.get_ylim()[1] * 0.85, "コロナ期\n（使わない）", ha="center", fontsize=8)
ax.axhline(0, color="black", lw=.8); ax.set_ylabel("就業率の差（%pt）"); ax.set_xticks(range(2008, 2026, 2))
ax.set_title("合成コントロール：2019→25年度に大きく上げた10県と、似た動きの「合成県」の差", fontsize=10.5)
ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig5_synth_gap.png"); plt.close(fig)

# 図6 違い：bite の高さ別と産業別（F15）
h = pd.read_csv(RES / "heterogeneity_bite.csv")
fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.2))
he = h[(h.outcome == "emp_rate") & (h.group.isin(["低", "中", "高"]))]
names = {"低": "最低賃金が平均時給から\n遠い県（下位1/3）", "中": "中位1/3", "高": "近い県\n（上位1/3）"}
for i, r in enumerate(he.itertuples()):
    axes[0].errorbar(i, r.per10, yerr=1.96 * r.se10, fmt="o", color=[C1, C3, C2][i], capsize=5, ms=8)
    axes[0].text(i + .08, r.per10, f"{r.per10:+.2f}", fontsize=9)
d = h[(h.outcome == "emp_rate") & (h.group == "高−低")].iloc[0]
axes[0].set_xticks(range(3)); axes[0].set_xticklabels([names[g] for g in he.group], fontsize=8.5); axes[0].axhline(0, color="gray")
axes[0].set_ylabel("就業率（%pt、10%あたり）"); axes[0].set_title(f"県の bite 別（差の差）。近い−遠い＝{d.per10:+.2f}（±{1.96*d.se10:.2f}）", fontsize=9.5)
ind = [("宿泊・飲食", 0.314, -3.299, 3.927), ("卸売・小売", 4.091, -0.102, 8.285), ("製造業", 2.717, -0.116, 5.549), ("全産業", 0.257, -1.55, 2.065)]
for i, (n_, b, lo, hi) in enumerate(ind):
    axes[1].errorbar(b * 10, i, xerr=[[b * 10 - lo * 10], [hi * 10 - b * 10]], fmt="o", color=C1 if n_ != "全産業" else "black", capsize=4)
axes[1].set_yticks(range(4)); axes[1].set_yticklabels([x[0] for x in ind]); axes[1].invert_yaxis(); axes[1].axvline(0, color="gray")
axes[1].set_xlabel("従業者数の変化（%、最低賃金10%あたり）"); axes[1].set_title("産業別（F15：県境をはさむ市区町村の比較）", fontsize=9.5)
fig.tight_layout(); fig.savefig(FIG / "fig6_heterogeneity.png"); plt.close(fig)
print("ok")
