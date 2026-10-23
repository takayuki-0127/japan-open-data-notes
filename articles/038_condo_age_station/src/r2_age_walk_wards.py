"""R2：築年数・駅からの距離で㎡単価はどれだけ下がるか（ヘドニック回帰の区切りダミー）と、23区のどこが一番上がったか（区ごとのヘドニック指数）"""
from common import *
import statsmodels.formula.api as smf
d, _ = load()
d["age_bin"] = pd.cut(d.age, [-1, 2, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60], labels=["0-2", "3-5", "6-10", "11-15", "16-20", "21-25", "26-30", "31-35", "36-40", "41-50", "51-60"])
d["walk_bin"] = pd.cut(d.walk, [-1, 3, 5, 7, 10, 15, 20, 60], labels=["0-3", "4-5", "6-7", "8-10", "11-15", "16-20", "21+"])
F = "lppm2 ~ C(year_q) + C(muni) + C(age_bin) + C(walk_bin) + larea + I(larea**2) + C(struct) + renov"
m = smf.ols(F, d).fit(cov_type="cluster", cov_kwds={"groups": d.muni.astype("category").cat.codes})
ci = m.conf_int()
def bins(var, labels):
    out = []
    for l in labels:
        k = f"C({var})[T.{l}]"
        out.append({"bin": l, "pct": (np.exp(m.params.get(k, 0.0)) - 1) * 100, "lo": (np.exp(ci.loc[k, 0]) - 1) * 100 if k in ci.index else 0, "hi": (np.exp(ci.loc[k, 1]) - 1) * 100 if k in ci.index else 0, "n": int((d[var] == l).sum())})
    return pd.DataFrame(out)
A = bins("age_bin", d.age_bin.cat.categories); W = bins("walk_bin", d.walk_bin.cat.categories)
A.round(2).to_csv(RES / "r2_age.csv", index=False, encoding="utf-8-sig"); W.round(2).to_csv(RES / "r2_walk.csv", index=False, encoding="utf-8-sig")
print(A.round(1)); print(W.round(1)); print("renov", (np.exp(m.params.renov) - 1) * 100)
# 区ごとのヘドニック指数（2015〜16年 → 2024〜25年）
rows = []
G = "lppm2 ~ C(year) + age + I(age**2) + larea + I(larea**2) + walk + I(walk**2) + C(struct) + renov"
for w in WARDS:
    x = d[(d.muni == w) & (d.year <= 2025)]
    r = smf.ols(G, x).fit(cov_type="HC1")
    c = pd.Series({y: r.params.get(f"C(year)[T.{y}]", 0.0) for y in range(2015, 2026)})
    rows.append({"ward": w, "n": len(x), "chg_pct": (np.exp(c[[2024, 2025]].mean() - c[[2015, 2016]].mean()) - 1) * 100,
                 "chg_2020_2025": (np.exp(c[2025] - c[2020]) - 1) * 100, "ppm2_2015_16_median": x[x.year <= 2016].ppm2.median(), "ppm2_2024_25_median": x[x.year >= 2024].ppm2.median()})
R = pd.DataFrame(rows).sort_values("chg_pct", ascending=False); R.round(1).to_csv(RES / "r2_wards.csv", index=False, encoding="utf-8-sig"); print(R.round(1).to_string())
cr = np.corrcoef(R.ppm2_2015_16_median, R.chg_pct)[0, 1]
s = {"age_0_2_vs_11_15": A.set_index("bin").loc["11-15", "pct"], "age_21_25": A.set_index("bin").loc["21-25", "pct"], "age_31_35": A.set_index("bin").loc["31-35", "pct"], "age_41_50": A.set_index("bin").loc["41-50", "pct"], "age_51_60": A.set_index("bin").loc["51-60", "pct"],
     "walk_11_15": W.set_index("bin").loc["11-15", "pct"], "walk_16_20": W.set_index("bin").loc["16-20", "pct"], "walk_8_10": W.set_index("bin").loc["8-10", "pct"], "walk_21p": W.set_index("bin").loc["21+", "pct"],
     "renov_pct": (np.exp(m.params.renov) - 1) * 100, "ward_top": R.ward.iloc[0], "ward_top_chg": R.chg_pct.iloc[0], "ward_2nd": R.ward.iloc[1], "ward_2nd_chg": R.chg_pct.iloc[1], "ward_3rd": R.ward.iloc[2], "ward_3rd_chg": R.chg_pct.iloc[2],
     "ward_bottom": R.ward.iloc[-1], "ward_bottom_chg": R.chg_pct.iloc[-1], "ward_2bottom": R.ward.iloc[-2], "ward_2bottom_chg": R.chg_pct.iloc[-2], "ward_median_chg": R.chg_pct.median(),
     "corr_initial_price_growth": cr, "n": int(m.nobs)}
pd.Series(s).to_csv(RES / "r2_summary.csv", header=["value"]); print(pd.Series(s))

fig, axs = plt.subplots(1, 2, figsize=(10.5, 4), sharey=True)
for ax, T, xl, base in [(axs[0], A, "築年数（年）", "0〜2年"), (axs[1], W, "最寄駅から徒歩（分）", "0〜3分")]:
    xx = np.arange(len(T)); ax.errorbar(xx, T.pct, yerr=[T.pct - T.lo, T.hi - T.pct], fmt="o-", color=BLUE, ecolor=LIGHT, capsize=3)
    ax.set_xticks(xx, T.bin, fontsize=8.5); ax.set_xlabel(xl); ax.axhline(0, color=INK, lw=0.6); ax.set_title(f"{base}と比べた㎡単価の差", loc="left", fontsize=11)
axs[0].set_ylabel("%（ほかの条件をそろえて）")
fig.suptitle(f"築31〜35年で約{-A.set_index('bin').loc['31-35', 'pct']:.0f}%安く、駅から徒歩11〜15分で約{-W.set_index('bin').loc['11-15', 'pct']:.0f}%安い", x=0.01, ha="left", fontsize=12.5)
fig.text(0.01, -0.04, SOURCE + "（2015〜2026年、ヘドニック回帰。線は95%区間）", fontsize=7, color="#8a8984"); fig.tight_layout(); fig.savefig(FIG / "r2_age_walk.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 6.4)); yy = np.arange(len(R))
ax.barh(yy, R.chg_pct, color=[ORANGE if v >= R.chg_pct.quantile(0.75) else BLUE for v in R.chg_pct])
for i, v in enumerate(R.chg_pct): ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8.5)
ax.set_yticks(yy, R.ward); ax.invert_yaxis(); ax.set_xlabel("㎡単価の上昇率（2015〜16年 → 2024〜25年、質をそろえて）")
ax.set_title(f"23区で一番上がったのは{R.ward.iloc[0]}（{R.chg_pct.iloc[0]:.0f}%）、低いのは{R.ward.iloc[-1]}（{R.chg_pct.iloc[-1]:.0f}%）", loc="left", fontsize=12)
fig.text(0.01, -0.03, SOURCE + "（区ごとにヘドニック回帰）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "r2_wards.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.scatter(R.ppm2_2015_16_median, R.chg_pct, s=28, color=LIGHT, edgecolor=BLUE)
for _, r in R.iterrows(): ax.annotate(r.ward, (r.ppm2_2015_16_median, r.chg_pct), xytext=(3, 2), textcoords="offset points", fontsize=8)
ax.set_xlabel("2015〜16年の㎡単価（中央値、万円）"); ax.set_ylabel("上昇率（%、質をそろえて）")
ax.set_title(f"もともと高い区ほど、さらに上がった（相関 {cr:.2f}）", loc="left")
fig.text(0.01, -0.04, SOURCE, fontsize=7, color="#8a8984"); fig.savefig(FIG / "r2_initial_growth.png"); plt.close(fig)
