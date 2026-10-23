"""ごみの処理のしかたの変化、市区町村の人口規模とごみ・リサイクル率、都道府県のごみ処理経費"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x = load_muni(); x = x[x["pop"] > 0].copy()
c = load_pref_cost()

# 1) 処理のしかた（全国、ごみ処理量に占める割合）
t = x.groupby("fy")[["proc_t", "inc_t", "land_t", "mid_t", "dres_t", "final_t", "total_t"]].sum()
for k in ("inc_t", "land_t", "mid_t", "dres_t"): t[k.replace("_t", "_sh")] = t[k] / t.proc_t * 100
t["final_mt"] = t.final_t / 1e6
t.to_csv(RES / "w2_treatment.csv", encoding="utf-8-sig"); print(t[["inc_sh", "land_sh", "mid_sh", "dres_sh", "final_mt"]].round(2).to_string())

# 2) 人口規模別（2024年度）
b = x[x.fy == 2024].copy()
bins = [0, 5000, 10000, 30000, 100000, 300000, 1e9]
labs = ["5千人未満", "5千〜1万", "1万〜3万", "3万〜10万", "10万〜30万", "30万以上"]
b["size"] = pd.cut(b["pop"], bins, labels=labs, right=False)
s = b.groupby("size").agg(n=("code", "size"), pop=("pop", "sum"), gpd_med=("gpd", "median"), life_med=("gpd_life", "median"),
                          home_med=("gpd_home", "median"), biz_med=("gpd_biz", "median"), recy_med=("recy", "median"),
                          recy_p25=("recy", lambda v: v.quantile(.25)), recy_p75=("recy", lambda v: v.quantile(.75)))
s.to_csv(RES / "w2_by_size_2024.csv", encoding="utf-8-sig"); print(s.round(1).to_string())
bb = b[(b.gpd > 0)]
ms = sm.OLS(np.log(bb.gpd), sm.add_constant(np.log(bb["pop"]))).fit(cov_type="HC1")
bh = b[(b.gpd_home > 0)]
mh = sm.OLS(np.log(bh.gpd_home), sm.add_constant(np.log(bh["pop"]))).fit(cov_type="HC1")
bz = b[(b.gpd_biz > 0)]
mz = sm.OLS(np.log(bz.gpd_biz), sm.add_constant(np.log(bz["pop"]))).fit(cov_type="HC1")
el = pd.DataFrame([{"y": k, "elasticity": m.params.iloc[1], "lo": m.conf_int().iloc[1, 0], "hi": m.conf_int().iloc[1, 1], "n": int(m.nobs)} for k, m in [("合計", ms), ("家庭系", mh), ("事業系", mz)]])
el.to_csv(RES / "w2_pop_elasticity_2024.csv", index=False, encoding="utf-8-sig"); print(el.round(3))

# 3) 都道府県のごみ処理経費（市区町村＋一部事務組合、組合分担金を除く）
pp = x.groupby(["fy", "pref"]).agg(pop=("pop", "sum"), tot=("total_t", "sum")).reset_index()
small = x[x["pop"] < 30000].groupby(["fy", "pref"])["pop"].sum().rename("pop_small").reset_index()
cc = c.merge(pp, on=["fy", "pref"], how="left").merge(small, on=["fy", "pref"], how="left")
cc["pop_small"] = cc.pop_small.fillna(0)
cc["yen_pc"] = cc.total * 1000 / cc["pop"]; cc["opex_pc"] = cc.opex * 1000 / cc["pop"]
cc["yen_per_t"] = cc.total * 1000 / cc.tot; cc["small_sh"] = cc.pop_small / cc["pop"] * 100
cc.to_csv(RES / "w2_pref_cost.csv", index=False, encoding="utf-8-sig")
nat = cc.groupby("fy").agg(total=("total", "sum"), opex=("opex", "sum"), build=("build", "sum"), pop=("pop", "sum"), tot=("tot", "sum"))
nat["yen_pc"] = nat.total * 1000 / nat["pop"]; nat["opex_pc"] = nat.opex * 1000 / nat["pop"]; nat["build_pc"] = nat.build * 1000 / nat["pop"]
nat["yen_per_t"] = nat.total * 1000 / nat.tot
nat.to_csv(RES / "w2_national_cost.csv", encoding="utf-8-sig"); print(nat[["yen_pc", "opex_pc", "build_pc", "yen_per_t"]].round(0).to_string())
c24 = cc[cc.fy == 2024]
mc = sm.OLS(c24.opex_pc, sm.add_constant(c24.small_sh)).fit(cov_type="HC1")
print("処理維持管理費/人 ~ 3万人未満の人口割合:", mc.params.round(1).to_dict(), mc.bse.round(1).to_dict(), round(mc.rsquared, 3))
print(c24.sort_values("opex_pc")[["pref", "opex_pc", "yen_pc", "small_sh"]].round(0).to_string())
pd.DataFrame([{"slope_yen_per_pct": mc.params.iloc[1], "se": mc.bse.iloc[1], "r2": mc.rsquared, "corr": c24.opex_pc.corr(c24.small_sh)}]).to_csv(RES / "w2_cost_vs_small.csv", index=False, encoding="utf-8-sig")

# 図1：処理のしかた
fig, ax = plt.subplots(figsize=(8.2, 3.9))
cols = [("inc_sh", "直接焼却", ORANGE), ("mid_sh", "焼却以外の中間処理（粗大ごみ・資源化施設など）", BLUE), ("dres_sh", "直接資源化", GREEN), ("land_sh", "直接埋立", GRAY)]
bottom = np.zeros(len(t))
for k, lab_, col in cols:
    ax.bar(t.index, t[k], bottom=bottom, color=col, label=lab_, width=.8); bottom += t[k].values
for yy in (2007, 2024):
    ax.text(yy, t.loc[yy, "inc_sh"] / 2, f"{t.loc[yy, 'inc_sh']:.1f}%", ha="center", va="center", color="white", fontsize=9, rotation=90)
ax.set_ylim(0, 100); ax.set_ylabel("ごみ処理量に占める割合（%）"); ax.set_xticks(range(2008, 2025, 4))
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(.5, -.1))
ax.set_title("ごみの処理のしかた（全国）", loc="left")
note(ax, SOURCE, -0.33)
fig.savefig(FIG / "w2_treatment.png"); plt.close(fig)

# 図2：人口規模別
fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9))
xi = np.arange(len(s))
ax = axes[0]
ax.bar(xi - .2, s.home_med, .4, color=GREEN, label="家庭系")
ax.bar(xi + .2, s.biz_med, .4, color=ORANGE, label="事業系")
ax.set_xticks(xi); ax.set_xticklabels([f"{l}\n({n})" for l, n in zip(labs, s.n)], fontsize=8)
ax.set_ylabel("1人1日当たり（g、市区町村の中央値）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("人口規模別の1人1日当たりのごみ", loc="left", fontsize=11.5)
ax = axes[1]
ax.bar(xi, s.recy_med, .6, color=BLUE)
ax.errorbar(xi, s.recy_med, yerr=[s.recy_med - s.recy_p25, s.recy_p75 - s.recy_med], fmt="none", color=INK, lw=1, capsize=3)
ax.set_xticks(xi); ax.set_xticklabels(labs, fontsize=8); ax.set_ylabel("リサイクル率（%、中央値）")
ax.set_title("人口規模別のリサイクル率", loc="left", fontsize=11.5)
fig.suptitle("2024年度、人口規模別に見たごみの量とリサイクル率（かっこ内は市区町村数、ひげは25〜75%）", x=.02, y=1.04, ha="left", fontsize=11.5)
note(axes[0], SOURCE, -0.22)
fig.savefig(FIG / "w2_size.png"); plt.close(fig)

# 図3：経費
fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9))
ax = axes[0]
ax.bar(nat.index, nat.opex_pc / 1000, color=BLUE, label="処理及び維持管理費")
ax.bar(nat.index, nat.build_pc / 1000, bottom=nat.opex_pc / 1000, color=ORANGE, label="建設・改良費")
ax.plot(nat.index, nat.yen_pc / 1000, "o", color=INK, ms=3, label="合計（その他を含む）")
for yy in (2007, 2012, 2024): ax.text(yy, nat.yen_pc[yy] / 1000 + .3, f"{nat.yen_pc[yy] / 1000:.1f}", ha="center", fontsize=8.5)
ax.set_ylabel("1人当たり（千円、名目）"); ax.set_xticks(range(2008, 2025, 4)); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_title("ごみ処理の経費（全国、1人当たり）", loc="left", fontsize=11.5)
ax = axes[1]
ax.scatter(c24.small_sh, c24.opex_pc / 1000, color=BLUE, s=22)
for _, r in c24.iterrows():
    if r.pref in set(c24.nlargest(4, "opex_pc").pref) | set(c24.nsmallest(2, "opex_pc").pref) | {"東京都"}:
        ax.annotate(r.pref, (r.small_sh, r.opex_pc / 1000), fontsize=7.5, xytext=(3, 2), textcoords="offset points")
xs = np.linspace(0, c24.small_sh.max(), 20); ax.plot(xs, (mc.params.iloc[0] + mc.params.iloc[1] * xs) / 1000, color=ORANGE, lw=1.6)
ax.set_xlabel("人口3万人未満の市町村に住む人の割合（%）"); ax.set_ylabel("処理及び維持管理費（千円/人）")
ax.set_title(f"都道府県別（2024年度、相関{c24.opex_pc.corr(c24.small_sh):.2f}）", loc="left", fontsize=11.5)
note(axes[0], SOURCE + "\n市区町村と一部事務組合の経費（組合分担金を除く）。物価の変化は差し引いていない", -0.2)
fig.savefig(FIG / "w2_cost.png"); plt.close(fig)
