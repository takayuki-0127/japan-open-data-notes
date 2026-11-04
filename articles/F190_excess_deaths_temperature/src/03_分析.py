"""期待死亡数のモデルと、気温との関係"""
import json
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from common import DATA, RES, SUMMER, WINTER, SEED

rng = np.random.default_rng(SEED)
p = pd.read_csv(DATA / "monthly_panel.csv")
p["time"] = (p.year - 2000) + (p.month - 0.5) / 12
p["mf"] = p.month.astype(str)
p["logdays"] = np.log(p.days)
p["quake"] = ((p.year == 2011) & (p.month == 3)).astype(int)   # 2011年3月（震災）は学習から除く
p["season"] = np.where(p.month.isin(SUMMER), "summer", np.where(p.month.isin(WINTER), "winter", "other"))
out = {}


def fit_expected(train, trend="lin"):
    f = "deaths ~ C(mf) + time" + (" + I(time**2)" if trend == "quad" else "")
    m = smf.glm(f, data=train, family=sm.families.Poisson(), offset=train.logdays).fit(scale="X2")
    return m


def expected(m, df):
    return m.predict(df, offset=df.logdays)


# --- 1) 主モデル：2010〜2019年で学習（2011年3月を除く）、直線トレンド＋月 ---
def run(train_years=(2010, 2019), trend="lin", temp="t_anom", tag="main"):
    tr = p[(p.year >= train_years[0]) & (p.year <= train_years[1]) & (p.quake == 0)]
    m = fit_expected(tr, trend)
    q = p.copy()
    q["exp"] = expected(m, q)
    q["excess"] = q.deaths - q["exp"]
    q["ratio"] = q.deaths / q["exp"]
    # 気温との関係：学習期間の残差（比の対数）を、夏・冬それぞれ気温差に回帰
    rows = {}
    for s in ["summer", "winter"]:
        z = q[(q.year >= train_years[0]) & (q.year <= train_years[1]) & (q.quake == 0) & (q.season == s)].dropna(subset=[temp])
        r = smf.ols(f"np.log(ratio) ~ {temp}", data=z).fit(cov_type="HC3")
        b, se = r.params[temp], r.bse[temp]
        rows[s] = dict(pct_per_1C=100 * (np.exp(b) - 1), lo=100 * (np.exp(b - 1.96 * se) - 1), hi=100 * (np.exp(b + 1.96 * se) - 1),
                       p=float(r.pvalues[temp]), n=int(len(z)), r2=float(r.rsquared))
    return q, m, rows


q, m, rel = run()
out["main_relation"] = rel
q.to_csv(RES / "excess_main.csv", index=False)

# --- 2) 1つのモデルで夏の暑さ・冬の寒さを同時に（2000〜2019年、学習＝推定） ---
z = p[(p.year <= 2019) & (p.quake == 0)].copy()
z["heat"] = np.where(z.month.isin(SUMMER), z.t_anom, 0.0)
z["cold"] = np.where(z.month.isin(WINTER), z.t_anom, 0.0)
z["cold_lag"] = np.where(z.month.isin(WINTER), z.t_anom_lag1, 0.0)
mj = smf.glm("deaths ~ C(mf) + time + I(time**2) + heat + cold + cold_lag", data=z.dropna(),
             family=sm.families.Poisson(), offset=z.dropna().logdays).fit(scale="X2")
ci = mj.conf_int()
out["joint_2000_2019"] = {k: dict(pct=100 * (np.exp(mj.params[k]) - 1), lo=100 * (np.exp(ci.loc[k, 0]) - 1),
                                   hi=100 * (np.exp(ci.loc[k, 1]) - 1), p=float(mj.pvalues[k])) for k in ["heat", "cold", "cold_lag"]}

# 夏の暑さの非線形（気温差の区分ごとの比）
s = q[(q.season == "summer") & (q.year.between(2010, 2019)) & (q.quake == 0)].copy()
s["bin"] = pd.cut(s.t_anom, [-3, -0.5, 0.5, 1.0, 3])
out["summer_bins"] = s.groupby("bin", observed=True).ratio.agg(["mean", "count"]).round(4).reset_index().astype(str).values.tolist()

# --- 3) 季節ごとの超過死亡（年×季節）と、そのうち気温で説明できる分 ---
bs, bw = rel["summer"], rel["winter"]
q["temp_part"] = 0.0
for sname, r in [("summer", bs), ("winter", bw)]:
    k = np.log(1 + r["pct_per_1C"] / 100)
    msk = q.season == sname
    q.loc[msk, "temp_part"] = q.loc[msk, "exp"] * (np.exp(k * q.loc[msk, "t_anom"]) - 1)
q["sy"] = np.where(q.month == 12, q.year + 1, q.year)   # 冬は12月を翌年の冬に
agg = q[q.season != "other"].groupby(["sy", "season"]).agg(excess=("excess", "sum"), temp_part=("temp_part", "sum"),
                                                          deaths=("deaths", "sum"), t_anom=("t_anom", "mean")).reset_index()
agg = agg[(agg.sy >= 2001) & (agg.sy <= 2025)]
agg.round(1).to_csv(RES / "season_excess.csv", index=False)
out["season_excess_selected"] = agg[agg.sy.isin([2010, 2018, 2022, 2023, 2024, 2025])].round(0).to_dict("records")

# 暑かった夏（気温差が上位）の超過と気温分
hot = agg[(agg.season == "summer")].sort_values("t_anom", ascending=False).head(6)
out["hot_summers"] = hot.round(2).to_dict("records")

# 2020年以降の超過のうち気温で説明できる割合
post = q[q.year >= 2020]
out["post2020"] = dict(excess=float(post.excess.sum()), temp_part=float(post.temp_part.sum()),
                       share=float(post.temp_part.sum() / post.excess.sum()))
pre = q[(q.year.between(2010, 2019)) & (q.quake == 0)]
out["pre_sd_ratio"] = float(pre.ratio.std())

# --- 4) 頑健性 ---
rob = []
for ty in [(2010, 2019), (2005, 2019), (2000, 2019), (2014, 2019)]:
    for tr in ["lin", "quad"]:
        for temp in ["t_anom", "tx_anom", "tn_anom", "t_unw_anom", "t_tokyo_anom", "anom15"]:
            _, _, r = run(ty, tr, temp)
            rob.append(dict(train=f"{ty[0]}-{ty[1]}", trend=tr, temp=temp,
                            summer=r["summer"]["pct_per_1C"], summer_p=r["summer"]["p"],
                            winter=r["winter"]["pct_per_1C"], winter_p=r["winter"]["p"]))
rob = pd.DataFrame(rob)
rob.round(4).to_csv(RES / "robustness.csv", index=False)
out["rob_range"] = dict(summer=[rob.summer.min(), rob.summer.max(), int((rob.summer_p < 0.05).sum()), len(rob)],
                        winter=[rob.winter.min(), rob.winter.max(), int((rob.winter_p < 0.05).sum()), len(rob)])

# COVID 期の扱い：2020〜2025年も学習に入れ、年ごとの水準（年ダミー）で吸収した場合
c = p[p.quake == 0].copy()
c = c[c.year >= 2010]
c["yr"] = c.year.astype(str)
c["heat"] = np.where(c.month.isin(SUMMER), c.t_anom, 0.0)
c["cold"] = np.where(c.month.isin(WINTER), c.t_anom, 0.0)
cv = {}
for lab, d in [("2010-2019", c[c.year <= 2019]), ("2010-2025 年ダミー", c), ("2020-2025 年ダミー", c[c.year >= 2020])]:
    mm = smf.glm("deaths ~ C(mf) + C(yr) + heat + cold", data=d, family=sm.families.Poisson(), offset=d.logdays).fit(scale="X2")
    cv[lab] = {k: [100 * (np.exp(mm.params[k]) - 1), float(mm.pvalues[k])] for k in ["heat", "cold"]}
out["covid_handling"] = cv

# 月ごとの比と気温差（散布図用）
q[["year", "month", "season", "t", "t_anom", "ratio", "excess", "exp", "deaths", "temp_part"]].to_csv(RES / "monthly_ratio.csv", index=False)
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda x: round(float(x), 3))[:6000])
