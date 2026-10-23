"""高齢者（第1号被保険者）1人あたりの介護保険給付費：保険者の分布・都道府県差・年齢構成との関係・5年の伸び"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import statsmodels.api as sm
from common import load, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT, SOURCE

df = load()
ins = df[df.level == "保険者"].copy()
nat = df[df.level == "全国"].set_index("year")
y24 = ins[ins.year == 2024].copy(); y19 = ins[ins.year == 2019].copy()

# 分布
q = y24.per_capita_yen.quantile([.1, .5, .9])
desc = pd.DataFrame([dict(year=y, n=len(g), national=nat.loc[y, "per_capita_yen"], p10=g.per_capita_yen.quantile(.1),
                          median=g.per_capita_yen.median(), p90=g.per_capita_yen.quantile(.9), min=g.per_capita_yen.min(),
                          max=g.per_capita_yen.max(), cv=round(g.per_capita_yen.std() / g.per_capita_yen.mean(), 3))
                     for y, g in ins.groupby("year")])
desc.to_csv(RES / "a132_distribution.csv", index=False)
cols = ["pref", "insurer", "insured", "share75p", "share85p", "per_capita_yen"]
y24.sort_values("per_capita_yen", ascending=False)[cols].head(15).to_csv(RES / "a132_top15_2024.csv", index=False)
y24.sort_values("per_capita_yen")[cols].head(15).to_csv(RES / "a132_bottom15_2024.csv", index=False)

# 都道府県（保険者の合計で計算）
pf = y24.groupby("pref", sort=False).agg(insured=("insured", "sum"), benefit_k=("benefit_k", "sum"),
                                         a75=("age75_84", "sum"), a85=("age85p", "sum"))
pf["per_capita_yen"] = pf.benefit_k * 1000 / pf.insured
pf["share85p"] = pf.a85 / pf.insured * 100
pf19 = y19.groupby("pref", sort=False).agg(insured=("insured", "sum"), benefit_k=("benefit_k", "sum"))
pf["per_capita_2019"] = pf19.benefit_k * 1000 / pf19.insured
pf["growth_pct"] = (pf.per_capita_yen / pf.per_capita_2019 - 1) * 100
pf = pf.round(2).sort_values("per_capita_yen", ascending=False)
pf.to_csv(RES / "a132_pref_2024.csv")
# 分散のうち県の差で説明できる割合
g = y24.groupby("pref").per_capita_yen
r2_pref = 1 - ((y24.per_capita_yen - g.transform("mean")) ** 2).sum() / ((y24.per_capita_yen - y24.per_capita_yen.mean()) ** 2).sum()

# 年齢構成（75〜84歳・85歳以上の割合）で説明できる部分
X = sm.add_constant(y24[["share75p", "share85p"]].assign(share75p=lambda d: d.share75p - d.share85p).rename(columns={"share75p": "share75_84"}))
m = sm.WLS(np.log(y24.per_capita_yen), X, weights=y24.insured).fit()
y24["adj_ratio"] = np.exp(m.resid)   # 年齢構成から予想される値に対する比
y24.sort_values("adj_ratio", ascending=False)[cols + ["adj_ratio"]].head(15).round(3).to_csv(RES / "a132_top15_age_adjusted_2024.csv", index=False)
reg = pd.DataFrame([dict(r2=round(m.rsquared, 3), coef_share75_84=round(m.params["share75_84"], 4), coef_share85p=round(m.params["share85p"], 4),
                         se85=round(m.bse["share85p"], 4), r2_pref_unadjusted=round(r2_pref, 3))])
reg.to_csv(RES / "a132_regression.csv", index=False)

# 規模別のばらつき
bins = [0, 1000, 3000, 10000, 30000, 100000, 1e8]
labels = ["1千人未満", "1千〜3千", "3千〜1万", "1万〜3万", "3万〜10万", "10万人以上"]
y24["size"] = pd.cut(y24.insured, bins, labels=labels, right=False)
sz = y24.groupby("size").per_capita_yen.agg(["count", "median", lambda s: s.quantile(.1), lambda s: s.quantile(.9), "std"])
sz.columns = ["n", "median", "p10", "p90", "sd"]; sz = sz.round(0); sz.to_csv(RES / "a132_by_size_2024.csv")

# 5年の伸び（両年にある保険者）
both = y19.merge(y24, on=["pref", "insurer"], suffixes=("_19", "_24"))
both["growth_pct"] = (both.per_capita_yen_24 / both.per_capita_yen_19 - 1) * 100
both["d_share85"] = both.share85p_24 - both.share85p_19
gr = pd.DataFrame([dict(n=len(both), median_growth=round(both.growth_pct.median(), 1), share_up=round((both.growth_pct > 0).mean() * 100, 1),
                        national_growth=round((nat.loc[2024, "per_capita_yen"] / nat.loc[2019, "per_capita_yen"] - 1) * 100, 1),
                        corr_growth_dshare85=round(both.growth_pct.corr(both.d_share85), 3))])
gr.to_csv(RES / "a132_growth.csv", index=False)

# 図1 都道府県ごとの保険者の分布
order = pf.index.tolist()
fig, ax = plt.subplots(figsize=(9, 9.5))
for i, p in enumerate(order):
    v = y24[y24.pref == p].per_capita_yen / 1e4
    jitter = (np.random.default_rng(i).random(len(v)) - .5) * .5
    ax.scatter(v, i + jitter, s=7, color=LIGHT, alpha=.8, lw=0)
    ax.scatter(pf.loc[p, "per_capita_yen"] / 1e4, i, s=28, color=BLUE, zorder=3)
ax.axvline(nat.loc[2024, "per_capita_yen"] / 1e4, color=GRAY, ls="--", lw=1)
ax.set_yticks(range(len(order))); ax.set_yticklabels(order, fontsize=8); ax.invert_yaxis()
ax.set_xlabel("第1号被保険者1人あたり保険給付費（万円、2024年度）")
ax.set_title("1人あたり介護給付費：県の平均（青）と保険者（薄い点）")
fig.text(0.01, -0.02, "注：点線は全国平均31.2万円。給付費には40〜64歳（第2号）の利用分を含む\n" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a132_pref.png"); plt.close(fig)

# 図2 85歳以上の割合との関係
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(y24.share85p, y24.per_capita_yen / 1e4, s=np.clip(np.sqrt(y24.insured) / 4, 3, 60), color=BLUE, alpha=.35, lw=0)
xs = np.linspace(y24.share85p.min(), y24.share85p.max(), 50)
b = np.polyfit(y24.share85p, y24.per_capita_yen / 1e4, 1, w=np.sqrt(y24.insured))
ax.plot(xs, np.polyval(b, xs), color=ORANGE)
ax.set_xlabel("第1号被保険者に占める85歳以上の割合（%）"); ax.set_ylabel("1人あたり給付費（万円）")
ax.set_title(f"85歳以上が多い保険者ほど高い（年齢構成で差の{m.rsquared*100:.0f}%を説明）")
fig.text(0.01, -0.03, "注：点の大きさは第1号被保険者数。2024年度\n" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a132_age.png"); plt.close(fig)

# 図3 規模とばらつき
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(y24.insured, y24.per_capita_yen / 1e4, s=6, color=BLUE, alpha=.35, lw=0)
ax.set_xscale("log")
for lab, r in sz.iterrows():
    pass
ax.axhline(nat.loc[2024, "per_capita_yen"] / 1e4, color=GRAY, ls="--", lw=1)
ax.set_xlabel("第1号被保険者数（人、対数目盛）"); ax.set_ylabel("1人あたり給付費（万円）")
ax.set_title("小さな保険者ほど上下に大きくばらつく")
fig.text(0.01, -0.03, "注：2024年度。点線は全国平均\n" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a132_size.png"); plt.close(fig)

print(desc.to_string()); print(pf.head(6).to_string()); print(pf.tail(5).to_string())
print(reg.to_string()); print(sz.to_string()); print(gr.to_string())
print(pd.read_csv(RES / "a132_top15_2024.csv").head(10).to_string()); print(pd.read_csv(RES / "a132_bottom15_2024.csv").head(6).to_string())
print(pd.read_csv(RES / "a132_top15_age_adjusted_2024.csv").head(8).to_string())
print('pref range growth', pf.growth_pct.min(), pf.growth_pct.max())
