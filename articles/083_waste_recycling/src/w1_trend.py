"""1人1日当たりのごみ排出量とリサイクル率：全国の推移、市区町村の分布、収束（β・σ）"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x = load_muni()
x = x[(x["pop"] > 0) & (x.total_t >= 0)].copy()
YRS = sorted(x.fy.unique())

# 全国（市区町村の合計から計算）
g = x.groupby("fy").agg(pop=("pop", "sum"), tot=("total_t", "sum"), proc=("proc_t", "sum"), dres=("dres_t", "sum"),
                        reuse=("reuse_t", "sum"), grp=("group_t", "sum"), fin=("final_t", "sum"))
g["gpd"] = g.tot * 1e6 / g["pop"] / 365
g["recy"] = (g.dres + g.reuse + g.grp) / (g.proc + g.grp) * 100
x["life_t"] = x.gpd_life * x["pop"] * 365 / 1e6; x["biz_t"] = x.gpd_biz * x["pop"] * 365 / 1e6
x["home_t"] = x.gpd_home * x["pop"] * 365 / 1e6
for k in ("life", "biz", "home"):
    ok = x[f"{k}_t"].notna()
    g[f"gpd_{k}"] = x[ok].groupby("fy")[f"{k}_t"].sum() * 1e6 / x[ok].groupby("fy")["pop"].sum() / 365
g.to_csv(RES / "w1_national.csv", encoding="utf-8-sig")
print(g.round(1).to_string())

# 市区町村の分布（毎年の人口加重しない、市区町村単位の分位点）
q = x.groupby("fy").agg(n=("code", "size"), gpd_p10=("gpd", lambda s: s.quantile(.1)), gpd_med=("gpd", "median"),
                        gpd_p90=("gpd", lambda s: s.quantile(.9)), recy_p10=("recy", lambda s: s.quantile(.1)),
                        recy_med=("recy", "median"), recy_p90=("recy", lambda s: s.quantile(.9)),
                        recy30=("recy", lambda s: (s >= 30).mean() * 100))
# σ収束：期間中ずっと同じコードで出てくる市区町村（バランスパネル）での log(g/人日) の標準偏差
bal_codes = x.groupby("code").fy.nunique()
bal = x[x.code.isin(bal_codes[bal_codes == len(YRS)].index)]
q["sd_log_gpd_bal"] = bal.groupby("fy").gpd.apply(lambda s: np.log(s[s > 0]).std())
q["cv_recy_bal"] = bal.groupby("fy").recy.apply(lambda s: s.std() / s.mean())
q["n_bal"] = bal.groupby("fy").size()
q.to_csv(RES / "w1_distribution.csv", encoding="utf-8-sig"); print(q.round(3).to_string())

# β収束：2012→2024 の変化率を2012年の水準で説明（2012年以降は市区町村の数がほぼ一定）
a = x[x.fy == 2012].set_index("code"); b = x[x.fy == 2024].set_index("code")
j = a.join(b, lsuffix="_0", rsuffix="_1", how="inner")
j = j[(j.gpd_0 > 0) & (j.gpd_1 > 0)]
j["g"] = np.log(j.gpd_1 / j.gpd_0) / 12 * 100
m = sm.OLS(j.g, sm.add_constant(np.log(j.gpd_0))).fit(cov_type="HC1")
jr = j.dropna(subset=["recy_0", "recy_1"])
m2 = sm.OLS(jr.recy_1 - jr.recy_0, sm.add_constant(jr.recy_0)).fit(cov_type="HC1")
beta = pd.DataFrame([{"var": "log(g/人日)の年率変化(%) ~ log(2012年の水準)", "slope": m.params.iloc[1], "se": m.bse.iloc[1], "n": int(m.nobs), "r2": m.rsquared},
                     {"var": "リサイクル率の変化(ポイント) ~ 2012年のリサイクル率", "slope": m2.params.iloc[1], "se": m2.bse.iloc[1], "n": int(m2.nobs), "r2": m2.rsquared}])
beta.to_csv(RES / "w1_beta.csv", index=False, encoding="utf-8-sig"); print(beta.round(3))
print("減った市区町村の割合", (j.gpd_1 < j.gpd_0).mean(), "中央値の変化", (j.gpd_1 / j.gpd_0 - 1).median())

# 2024年度のランキング（人口10万人以上の市区）
b24 = x[x.fy == 2024].copy()
big = b24[b24["pop"] >= 100000]
low = big.nsmallest(10, "gpd")[["pref", "name", "pop", "gpd", "recy"]]; high = big.nlargest(10, "gpd")[["pref", "name", "pop", "gpd", "recy"]]
rec = big.nlargest(10, "recy")[["pref", "name", "pop", "gpd", "recy"]]
allrec = b24.nlargest(10, "recy")[["pref", "name", "pop", "gpd", "recy"]]
pd.concat({"排出量が少ない": low, "排出量が多い": high, "リサイクル率が高い（10万人以上）": rec, "リサイクル率が高い（全市区町村）": allrec}).to_csv(RES / "w1_ranking_2024.csv", encoding="utf-8-sig")
print(low.round(1).to_string()); print(high.round(1).to_string()); print(rec.round(1).to_string()); print(allrec.round(1).to_string())
print("10万人以上の市区数", len(big))

# 図1：全国の推移
fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9))
ax = axes[0]
ax.plot(g.index, g.gpd, "o-", color=BLUE, lw=2, ms=4, label="合計")
ax.plot(g.index, g.gpd_life, "s-", color=GREEN, lw=1.6, ms=3, label="生活系（家庭から）")
ax.plot(g.index, g.gpd_biz, "^-", color=ORANGE, lw=1.6, ms=3, label="事業系（お店・会社から）")
ok = g.gpd_home.notna(); ax.plot(g.index[ok], g.gpd_home[ok], "d-", color=PURPLE, lw=1.6, ms=3, label="家庭系（資源ごみ等を除く）")
for yy in (2007, 2024): ax.text(yy, g.gpd[yy] + 18, f"{g.gpd[yy]:.0f}", ha="center", fontsize=9, color=BLUE)
ax.set_ylabel("1人1日当たり（g）"); ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=8.5, loc="center left", bbox_to_anchor=(0.02, 0.43))
ax.set_title("1人1日当たりのごみの量", loc="left", fontsize=11.5)
ax = axes[1]
ax.plot(g.index, g.recy, "o-", color=GREEN, lw=2, ms=4)
for yy in (2007, 2011, 2024): ax.text(yy, g.recy[yy] + .15, f"{g.recy[yy]:.1f}%", ha="center", fontsize=9)
ax.set_ylim(17, 22.5); ax.set_ylabel("リサイクル率（%）"); ax.set_title("リサイクル率（全国）", loc="left", fontsize=11.5)
for a_ in axes: a_.set_xticks(range(2008, 2025, 4))
fig.suptitle("全国のごみの量とリサイクル率（2007〜2024年度）", x=.02, y=1.04, ha="left", fontsize=12.5)
note(axes[0], SOURCE + "\n市区町村の値を合計して計算。生活系・事業系は人口で重みづけ", -0.16)
fig.savefig(FIG / "w1_national.png"); plt.close(fig)

# 図2：市区町村の分布と収束
fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9))
ax = axes[0]
ax.fill_between(q.index, q.gpd_p10, q.gpd_p90, color=LIGHT, alpha=.7, label="下から10%〜90%の範囲")
ax.plot(q.index, q.gpd_med, "o-", color=BLUE, lw=2, ms=4, label="中央値")
ax.set_ylabel("1人1日当たり（g）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("市区町村ごとの1人1日当たりのごみ", loc="left", fontsize=11.5)
ax = axes[1]
lo_, hi_ = np.log(j.gpd_0).quantile([.005, .995])
ax.scatter(np.log(j.gpd_0), j.g, s=6, color=BLUE, alpha=.35, lw=0)
xs = np.linspace(lo_, hi_, 50)
ax.plot(xs, m.params.iloc[0] + m.params.iloc[1] * xs, color=ORANGE, lw=2)
ax.axhline(0, color=INK, lw=.6)
tick = [500, 700, 1000, 1400]; ax.set_xticks(np.log(tick)); ax.set_xticklabels(tick); ax.set_xlim(lo_ - .05, hi_ + .05)
ax.set_xlabel("2012年度の1人1日当たり（g、対数目盛）"); ax.set_ylabel("2012→2024年度の年率変化（%）")
ax.set_ylim(-8, 6)
ax.set_title(f"多かった所ほど減った（傾き{m.params.iloc[1]:.2f}）", loc="left", fontsize=11.5)
note(axes[0], SOURCE, -0.2)
fig.savefig(FIG / "w1_converge.png"); plt.close(fig)

# 図3：ランキング（人口10万人以上）
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4), sharex=True)
for ax, d, col, t in [(axes[0], low.iloc[::-1], GREEN, "少ない10市区"), (axes[1], high.iloc[::-1], ORANGE, "多い10市区")]:
    ax.barh(range(len(d)), d.gpd, color=col)
    ax.set_yticks(range(len(d))); ax.set_yticklabels([f"{p}{n}" for p, n in zip(d.pref, d.name)], fontsize=9)
    for i, v in enumerate(d.gpd): ax.text(v + 10, i, f"{v:.0f}", va="center", fontsize=8.5)
    ax.set_title(f"1人1日当たりが{t}", loc="left", fontsize=11.5)
axes[0].set_xlabel("g/人日"); axes[1].set_xlabel("g/人日")
fig.suptitle(f"人口10万人以上の{len(big)}市区で比べた2024年度の1人1日当たりのごみ", x=.02, y=1.03, ha="left", fontsize=12)
note(axes[0], SOURCE, -0.2)
fig.savefig(FIG / "w1_ranking.png"); plt.close(fig)
