"""R1：東京の中古マンションは、質をそろえると何%上がったか。ヘドニック回帰（築年数・広さ・駅からの距離・場所をそろえた）で価格指数を作り、単純な中央値と比べる"""
from common import *
import statsmodels.formula.api as smf
d, log = load()
pd.Series(log).to_csv(RES / "r1_sample_log.csv", header=["rows"])
F = "lppm2 ~ C(year_q) + C(muni) + age + I(age**2) + larea + I(larea**2) + walk + I(walk**2) + C(struct) + renov"
m = smf.ols(F, d).fit(cov_type="cluster", cov_kwds={"groups": d.muni.astype("category").cat.codes})
print("n", int(m.nobs), "R2", round(m.rsquared, 3))
qs = sorted(d.year_q.unique())
coef = pd.Series({q: (m.params.get(f"C(year_q)[T.{q}]", 0.0)) for q in qs})
idx = pd.DataFrame({"hedonic": np.exp(coef - coef.iloc[0]) * 100})
med = d.groupby("year_q").ppm2.median(); idx["median"] = med / med.iloc[0] * 100
idx["n"] = d.groupby("year_q").size(); idx["mean_age"] = d.groupby("year_q").age.mean(); idx["mean_area"] = d.groupby("year_q").area.mean(); idx["median_age"] = d.groupby("year_q").age.median(); idx["median_walk"] = d.groupby("year_q").walk.median()
idx["share_23"] = d.groupby("year_q").ward23.mean() * 100
# 95%区間（2015Q1 との差）
ci = m.conf_int()
idx["hed_lo"] = [100 if q == qs[0] else np.exp(ci.loc[f"C(year_q)[T.{q}]", 0]) * 100 for q in qs]
idx["hed_hi"] = [100 if q == qs[0] else np.exp(ci.loc[f"C(year_q)[T.{q}]", 1]) * 100 for q in qs]
idx.round(2).to_csv(RES / "r1_index.csv", encoding="utf-8-sig"); print(idx.round(1).iloc[[0, 4, 8, 12, 20, 24, 28, 32, 36, 40, 41, 42, 43, 44]])
# 年平均（2015年＝100）
yr = idx.assign(y=[q[:4] for q in idx.index]).groupby("y")[["hedonic", "median"]].mean()
yr = yr / yr.iloc[0] * 100; yr.round(1).to_csv(RES / "r1_index_yearly.csv", encoding="utf-8-sig"); print(yr.round(1))
cg = lambda a, b: (yr.loc[b] / yr.loc[a] - 1) * 100
# 23区と多摩などの比較
sub = {}
for nm, x in [("23区", d[d.ward23]), ("23区以外", d[~d.ward23])]:
    mm = smf.ols(F, x).fit(); c = pd.Series({q: mm.params.get(f"C(year_q)[T.{q}]", 0.0) for q in qs})
    sub[nm] = np.exp(c - c.iloc[0]) * 100
sub = pd.DataFrame(sub); sub.round(2).to_csv(RES / "r1_index_23_vs_other.csv", encoding="utf-8-sig")
sy = sub.assign(y=[q[:4] for q in sub.index]).groupby("y").mean(); sy = sy / sy.iloc[0] * 100
s = {"n": int(m.nobs), "r2": m.rsquared, "hed_2025_vs_2015": cg("2015", "2025")["hedonic"], "med_2025_vs_2015": cg("2015", "2025")["median"],
     "hed_2025_vs_2020": cg("2020", "2025")["hedonic"], "med_2025_vs_2020": cg("2020", "2025")["median"],
     "hed_cagr_15_25": ((yr.loc["2025", "hedonic"] / 100) ** (1 / 10) - 1) * 100,
     "w23_2025_vs_2015": sy.loc["2025", "23区"] - 100, "other_2025_vs_2015": sy.loc["2025", "23区以外"] - 100,
     "median_age_2015": d[d.year == 2015].age.median(), "median_age_2025": d[d.year == 2025].age.median(),
     "median_area_2015": d[d.year == 2015].area.median(), "median_area_2025": d[d.year == 2025].area.median(), "mean_age_2015": d[d.year == 2015].age.mean(), "mean_age_2025": d[d.year == 2025].age.mean(), "mean_area_2015": d[d.year == 2015].area.mean(), "mean_area_2025": d[d.year == 2025].area.mean(),
     "share23_2015": d[d.year == 2015].ward23.mean() * 100, "share23_2025": d[d.year == 2025].ward23.mean() * 100,
     "median_ppm2_2015": d[d.year == 2015].ppm2.median(), "median_ppm2_2025": d[d.year == 2025].ppm2.median(),
     "b_age": m.params["age"], "b_age2": m.params["I(age ** 2)"], "b_walk": m.params["walk"], "b_renov": m.params["renov"]}
pd.Series(s).to_csv(RES / "r1_summary.csv", header=["value"]); print(pd.Series(s).round(3))

x = pd.PeriodIndex(idx.index, freq="Q").to_timestamp()
fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.fill_between(x, idx.hed_lo, idx.hed_hi, color=LIGHT, alpha=0.6)
ax.plot(x, idx.hedonic, color=BLUE, lw=2, label="質をそろえた指数（ヘドニック）")
ax.plot(x, idx["median"], color=ORANGE, lw=1.4, ls="--", label="単純な中央値（㎡単価）")
ax.axhline(100, color=INK, lw=0.6); ax.set_ylabel("2015年1〜3月期＝100"); ax.legend(frameon=False, loc="upper left")
ax.set_title(f"東京の中古マンション㎡単価：質をそろえると10年で約{s['hed_2025_vs_2015']:.0f}%上昇（中央値では{s['med_2025_vs_2015']:.0f}%）", loc="left", fontsize=12)
fig.text(0.01, -0.04, SOURCE + "（東京都の中古マンション等、四半期。帯は95%区間）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "r1_index.png"); plt.close(fig)

fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.4))
for ax, c, lab in zip(axs, ["mean_age", "mean_area", "share_23"], ["取引された物件の築年数（平均、年）", "面積（平均、㎡）", "23区の取引の割合（%）"]):
    ax.plot(x, idx[c], color=GRAY); ax.set_title(lab, fontsize=10, loc="left")
    ax.tick_params(axis="x", labelsize=8)
axs[2].set_ylim(75, 95)
fig.suptitle("取引される物件の中身も変わっている（だから中央値だけでは比べにくい）", x=0.01, ha="left", fontsize=12)
fig.text(0.01, -0.05, SOURCE, fontsize=7, color="#8a8984"); fig.tight_layout(); fig.savefig(FIG / "r1_mix.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 3.8))
ax.plot(x, sub["23区"], color=BLUE, lw=2, label="23区"); ax.plot(x, sub["23区以外"], color=GREEN, lw=2, label="23区以外（多摩など）")
ax.axhline(100, color=INK, lw=0.6); ax.set_ylabel("2015年1〜3月期＝100"); ax.legend(frameon=False, loc="upper left")
ax.set_title("23区の上がり方が大きい", loc="left")
fig.text(0.01, -0.05, SOURCE + "（それぞれ別にヘドニック回帰）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "r1_23_vs_other.png"); plt.close(fig)
