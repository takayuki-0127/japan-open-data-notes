"""空き家率：市区町村の分布、2018→2023年の変化、都道府県の差、住宅数・居住世帯のある住宅の増減との関係"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x = load_muni()
x["rate"] = x.vacant / x.houses * 100
x["other_rate"] = x.other / x.houses * 100
m = munis(x)

# 市区町村の分布（2018・2023年）
q = m.groupby("year").rate.describe(percentiles=[.1, .25, .5, .75, .9]).round(2)
q["n_20plus"] = m.groupby("year").rate.apply(lambda s: (s >= 20).sum())
q["n_25plus"] = m.groupby("year").rate.apply(lambda s: (s >= 25).sum())
nat = x[x.code == "00000"].set_index("year")[["houses", "vacant", "rate", "other_rate"]]
q = q.join(nat.rename(columns=lambda c: "全国_" + c))
q.to_csv(RES / "w1_distribution.csv", encoding="utf-8-sig"); print(q.T.to_string())

# 2018年と2023年の両方にある市区町村
a = m[m.year == 2018].set_index("code"); b = m[m.year == 2023].set_index("code")
j = a.join(b, lsuffix="_18", rsuffix="_23", how="inner")
j["d_rate"] = j.rate_23 - j.rate_18
j["d_other"] = j.other_rate_23 - j.other_rate_18
j["g_houses"] = (j.houses_23 / j.houses_18 - 1) * 100
j["g_occ"] = (j.occupied_23 / j.occupied_18 - 1) * 100
j["name"] = j.name_23; j["level"] = j.level_23
j["pref"] = j.index.str[:2]
pr = x[(x.level == "a") & (x.code != "00000")].drop_duplicates("code")
pn = dict(zip(pr.code.str[:2], pr.name))
j["pref_name"] = j.pref.map(pn)
print("両年ある市区町村", len(j), "上がった割合", (j.d_rate > 0).mean().round(3), "変化の中央値", j.d_rate.median().round(2))
print("2018と2023の空き家率の相関", j[["rate_18", "rate_23"]].corr().iloc[0, 1].round(3))

# ランキング（2023年の空き家率、上がり幅）。住宅数1万戸未満は振れが大きいので、上がり幅は1万戸以上でも示す
cols = ["pref_name", "name", "level", "houses_23", "rate_18", "rate_23", "d_rate", "other_rate_23", "g_houses", "g_occ"]
top = j.nlargest(15, "rate_23")[cols]; low = j.nsmallest(10, "rate_23")[cols]
up = j.nlargest(15, "d_rate")[cols]; up10k = j[j.houses_23 >= 10000].nlargest(10, "d_rate")[cols]
down = j.nsmallest(10, "d_rate")[cols]
rk = pd.concat({"空き家率が高い": top, "空き家率が低い": low, "上がり幅が大きい": up, "上がり幅が大きい（1万戸以上）": up10k, "下がり幅が大きい": down})
rk.to_csv(RES / "w1_ranking.csv", encoding="utf-8-sig")
for k, v in [("高い", top), ("低い", low), ("上昇", up), ("上昇1万戸以上", up10k), ("低下", down)]:
    print("--", k); print(v.round(1).to_string())

# 都道府県
p = x[x.level == "a"].pivot_table(index=["code", "name"], columns="year", values=["rate", "other_rate"]).reset_index()
p.columns = ["code", "name", "other_18", "other_23", "rate_18", "rate_23"]
p["d_rate"] = p.rate_23 - p.rate_18; p["d_other"] = p.other_23 - p.other_18
p = p.sort_values("rate_23", ascending=False)
p.to_csv(RES / "w1_pref.csv", index=False, encoding="utf-8-sig")
pp = p[p.code != "00000"]
print(pp.round(2).to_string())
print("上がった都道府県", (pp.d_rate > 0).sum(), "/", len(pp))
# 市区町村の差のうち都道府県で説明できる割合（2023年）
mm = m[m.year == 2023].copy(); mm["pref"] = mm.code.str[:2]
fit = sm.OLS.from_formula("rate ~ C(pref)", mm).fit()
print("都道府県ダミーのR2（2023年）", round(fit.rsquared, 3))

# 他の指標との関係：空き家率の変化 ~ 住宅数の増加率＋居住世帯のある住宅の増加率
ok = j[(j.houses_18 > 0)]
r1 = sm.OLS(ok.d_rate, sm.add_constant(ok[["g_houses", "g_occ"]])).fit(cov_type="HC1")
r2 = sm.OLS(ok.d_rate, sm.add_constant(ok[["g_occ"]])).fit(cov_type="HC1")
r3 = sm.OLS(ok.d_rate, sm.add_constant(ok[["rate_18"]])).fit(cov_type="HC1")
reg = pd.DataFrame([{"model": "Δ空き家率 ~ 住宅数増加率＋居住世帯あり増加率", "b_houses": r1.params["g_houses"], "se_houses": r1.bse["g_houses"],
                     "b_occ": r1.params["g_occ"], "se_occ": r1.bse["g_occ"], "r2": r1.rsquared, "n": int(r1.nobs)},
                    {"model": "Δ空き家率 ~ 居住世帯あり増加率", "b_occ": r2.params["g_occ"], "se_occ": r2.bse["g_occ"], "r2": r2.rsquared, "n": int(r2.nobs)},
                    {"model": "Δ空き家率 ~ 2018年の空き家率", "b_rate18": r3.params["rate_18"], "se_rate18": r3.bse["rate_18"], "r2": r3.rsquared, "n": int(r3.nobs)}])
reg.to_csv(RES / "w1_regression.csv", index=False, encoding="utf-8-sig"); print(reg.round(3).T)
print("相関 Δ空き家率 vs 住宅数増加率", ok[["d_rate", "g_houses"]].corr().iloc[0, 1].round(3), " vs 居住世帯あり増加率", ok[["d_rate", "g_occ"]].corr().iloc[0, 1].round(3))
# 居住世帯のある住宅が減った市区町村と増えた市区町村
ok["occ_grp"] = pd.cut(ok.g_occ, [-100, -3, 0, 3, 100], labels=["−3%未満", "−3〜0%", "0〜3%", "3%以上"])
gg = ok.groupby("occ_grp").agg(n=("d_rate", "size"), d_rate_med=("d_rate", "median"), up_share=("d_rate", lambda s: (s > 0).mean()),
                                g_houses_med=("g_houses", "median"), rate18_med=("rate_18", "median"))
gg.to_csv(RES / "w1_by_occ_change.csv", encoding="utf-8-sig"); print(gg.round(2))
j.reset_index().to_csv(RES / "w1_muni_change.csv", index=False, encoding="utf-8-sig",
                       columns=["code", "pref_name", "name", "level", "houses_18", "houses_23", "rate_18", "rate_23", "d_rate", "other_rate_18", "other_rate_23", "g_houses", "g_occ"])

# 図1：分布
fig, ax = plt.subplots(figsize=(8.6, 4.0))
bins = np.arange(0, 46, 1)
for y, c, a_ in [(2018, GRAY, .55), (2023, BLUE, .65)]:
    s = m[m.year == y].rate
    ax.hist(s.clip(upper=45.5), bins=bins, color=c, alpha=a_, label=f"{y}年（{len(s):,}市区町村、中央値{s.median():.1f}%）")
for y, c in [(2018, GRAY), (2023, BLUE)]:
    ax.axvline(nat.loc[y, "rate"], color=c, ls="--", lw=1.2)
ax.text(nat.loc[2023, "rate"] + .4, ax.get_ylim()[1] * .92, f"全国 {nat.loc[2018, 'rate']:.1f}%→{nat.loc[2023, 'rate']:.1f}%", fontsize=9, color=INK)
ax.set_xlabel("空き家率（空き家÷総住宅数、%）"); ax.set_ylabel("市区町村の数")
ax.set_title("市区町村の空き家率の分布（2018年と2023年）", loc="left"); ax.legend(frameon=False, fontsize=9)
note(ax, SOURCE + "。市区町村は市、政令市の区・特別区、人口1万5千人以上の町村。45%以上は右端にまとめた", y=-0.17)
fig.savefig(FIG / "w1_dist.png"); plt.close(fig)

# 図2：都道府県
fig, ax = plt.subplots(figsize=(8.6, 9.4))
pp2 = pp.sort_values("rate_23")
yy = np.arange(len(pp2))
ax.hlines(yy, pp2.rate_18, pp2.rate_23, color=LIGHT, lw=2)
ax.scatter(pp2.rate_18, yy, color=GRAY, s=18, label="2018年", zorder=3)
ax.scatter(pp2.rate_23, yy, color=BLUE, s=22, label="2023年", zorder=3)
ax.scatter(pp2.other_23, yy, color=ORANGE, marker="|", s=60, label="2023年のうち使い道のない空き家", zorder=3)
ax.set_yticks(yy); ax.set_yticklabels(pp2.name, fontsize=8)
ax.axvline(nat.loc[2023, "rate"], color=INK, lw=.8, ls=":")
ax.set_xlabel("空き家率（%）"); ax.set_title("都道府県の空き家率（2018年→2023年）", loc="left")
ax.legend(frameon=False, fontsize=9, loc="lower right"); note(ax, y=-0.06)
fig.savefig(FIG / "w1_pref.png"); plt.close(fig)

# 図3：居住世帯のある住宅の増減と空き家率の変化
fig, ax = plt.subplots(figsize=(8.6, 5.0))
sz = np.clip(ok.houses_23 / 2500, 3, 60)
for lv, c, lab in [("3", ORANGE, "町村"), ("2", BLUE, "市"), ("0", PURPLE, "政令市の区・特別区")]:
    s = ok[ok.level == lv]
    ax.scatter(s.g_occ, s.d_rate, s=sz[s.index], color=c, alpha=.45, lw=0, label=lab)
xs = np.linspace(-15, 15, 50)
ax.plot(xs, r2.params["const"] + r2.params["g_occ"] * xs, color=INK, lw=1.2)
ax.axhline(0, color=GRAY, lw=.8); ax.axvline(0, color=GRAY, lw=.8)
ax.set_xlim(-15, 15); ax.set_ylim(-15, 15)
ax.set_xlabel("居住世帯のある住宅の増加率（2018→2023年、%）"); ax.set_ylabel("空き家率の変化（ポイント）")
ax.set_title("住む人のいる住宅が減った所ほど、空き家率が上がった", loc="left")
ax.text(-14.5, 13.5, f"傾き {r2.params['g_occ']:.2f}（標準誤差{r2.bse['g_occ']:.2f}）、相関 {ok[['d_rate', 'g_occ']].corr().iloc[0, 1]:.2f}、{len(ok):,}市区町村", fontsize=9)
ax.legend(frameon=False, fontsize=9, loc="lower right"); note(ax, SOURCE + "。円の大きさは2023年の住宅数", y=-0.13)
fig.savefig(FIG / "w1_change.png"); plt.close(fig)
print("figures done")
