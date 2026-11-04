# F183 分析：自家用乗用車の世帯当たり台数は、どこで減りはじめたのか（都道府県）
import json, numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm
rng = np.random.default_rng(183)
R = {}
nat = pd.read_csv("data/national.csv").set_index("year")
pp = pd.read_csv("data/pref_panel.csv")
cov = pd.read_csv("data/pref_covariates.csv").set_index("pref")
popb = pd.read_csv("data/pref_population_ssdse_b.csv")
kei = pd.read_csv("data/kei_panel.csv")
PREFS = list(cov.index)

def hinge(y, t, cand, shift=None):
    """y = a + b t + c max(0, t-τ) (+ d 1[t>=2014]) を τ ごとに最小二乗。最良の τ と事後の傾き、BIC を返す"""
    best = None
    for tau in cand:
        X = np.c_[np.ones_like(t), t - 2005, np.maximum(0, t - tau)]
        if shift is not None: X = np.c_[X, (t >= shift).astype(float)]
        b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b; sse = float(e @ e)
        if best is None or sse < best[1]: best = (tau, sse, b)
    tau, sse, b = best; n = len(y); k = 4 + (shift is not None)
    X0 = np.c_[np.ones_like(t), t - 2005] if shift is None else np.c_[np.ones_like(t), t - 2005, (t >= shift).astype(float)]
    b0, *_ = np.linalg.lstsq(X0, y, rcond=None); e0 = y - X0 @ b0
    bic1 = n * np.log(sse / n) + k * np.log(n); bic0 = n * np.log(float(e0 @ e0) / n) + (k - 2) * np.log(n)
    return dict(tau=int(tau), pre=float(b[1]), post=float(b[1] + b[2]), dbic=float(bic0 - bic1))

# ---- 1. 全国 ----
n = nat.copy(); n["dlog_rate"] = np.log(n.rate).diff(); n["dlog_cars"] = np.log(n.cars).diff(); n["dlog_hh"] = np.log(n.hh).diff()
R["national_peak_year"] = int(n.rate.idxmax()); R["national_peak_rate"] = float(n.rate.max())
R["national_2026"] = n.loc[2026, ["rate", "cars", "hh"]].tolist()
per = {"1976-1996": (1976, 1996), "1997-2006": (1997, 2006), "2007-2013": (2007, 2013), "2014-2026": (2014, 2026), "2014-2026_ex2014": (2015, 2026)}
R["national_decomp_pct_per_year"] = {k: {c: round(100 * n.loc[a:b, c].mean(), 3) for c in ["dlog_rate", "dlog_cars", "dlog_hh"]} for k, (a, b) in per.items()}
y = n.loc[1990:, "rate"].values; t = np.arange(1990, 2027).astype(float)
R["national_hinge_1990_2026"] = hinge(y, t, range(1995, 2022))
R["national_hinge_1990_2026_shift2014"] = hinge(y, t, range(1995, 2022), shift=2014)
cars_g = n.loc[2005:, "dlog_cars"]; R["national_cars_growth_pct"] = (100 * cars_g).round(3).to_dict()
R["national_cars_peak_year"] = int(n.cars.idxmax())

# ---- 2. 都道府県 ----
rows = []
for p in PREFS:
    d = pp[pp.pref == p].set_index("year").sort_index()
    t = d.index.values.astype(float); r = d.rate.values
    h = hinge(r, t, range(2007, 2024)); hs = hinge(r, t, range(2007, 2024), shift=2014)
    d10 = d.loc[2010:]; h10 = hinge(d10.rate.values, d10.index.values.astype(float), range(2012, 2024))
    pc = popb[popb.pref == p].set_index("fy")["pop"]  # 年度 fy の10月人口 ≒ 翌年3月の台数に対応
    cpc = (d.cars.shift(0).reindex(pc.index + 1).values / pc.values)
    cpc = pd.Series(cpc, index=pc.index + 1).dropna()
    rows.append(dict(pref=p, peak_rate_year=int(d.rate.idxmax()), peak_rate=float(d.rate.max()), rate2005=float(d.rate.iloc[0]), rate2026=float(d.loc[2026, "rate"]),
                     hinge_tau=h["tau"], hinge_pre=h["pre"], hinge_post=h["post"], hinge_dbic=h["dbic"],
                     hinge_shift_tau=hs["tau"], hinge_shift_post=hs["post"], hinge10_tau=h10["tau"],
                     peak_cars_year=int(d.cars.idxmax()), peak_cars_pc_year=int(cpc.idxmax()) if len(cpc) else np.nan,
                     cars_pc_2013=float(cpc.loc[2013]), cars_pc_2024=float(cpc.loc[2024]),
                     dlog_rate_16_26=float(np.log(d.loc[2026, "rate"] / d.loc[2016, "rate"])),
                     dlog_cars_16_26=float(np.log(d.loc[2026, "cars"] / d.loc[2016, "cars"])),
                     dlog_hh_16_26=float(np.log(d.loc[2026, "hh"] / d.loc[2016, "hh"])),
                     dlog_rate_05_26=float(np.log(d.loc[2026, "rate"] / d.loc[2005, "rate"])),
                     dlog_cars_05_26=float(np.log(d.loc[2026, "cars"] / d.loc[2005, "cars"])),
                     dlog_hh_05_26=float(np.log(d.loc[2026, "hh"] / d.loc[2005, "hh"]))))
pr = pd.DataFrame(rows).set_index("pref").join(cov)
pr["dlog_cpc_13_24"] = np.log(pr.cars_pc_2024 / pr.cars_pc_2013)
pr["log_density"] = np.log(pr.density_hab); pr["log_rail"] = np.log(pr.rail_per1000)
pr.to_csv("results/pref_change_points.csv", encoding="utf-8")
R["pref_peak_rate_year_hist"] = pr.peak_rate_year.value_counts().sort_index().to_dict()
R["pref_hinge_tau_hist"] = pr.hinge_tau.value_counts().sort_index().to_dict()
R["pref_peak_cars_year_hist"] = pr.peak_cars_year.value_counts().sort_index().to_dict()
R["pref_peak_cars_pc_year_hist"] = pr.peak_cars_pc_year.value_counts().sort_index().to_dict()
R["n_rate_2026_below_2005"] = int((pr.rate2026 < pr.rate2005).sum())
R["n_cars_2026_above_2016"] = int((pr.dlog_cars_16_26 > 0).sum()); R["n_cars_pc_2024_above_2013"] = int((pr.dlog_cpc_13_24 > 0).sum())
R["median_peak_rate_year"] = float(pr.peak_rate_year.median()); R["median_hinge_tau"] = float(pr.hinge_tau.median())
R["hinge_dbic_gt6"] = int((pr.hinge_dbic > 6).sum())
# 減り方の分解（2016→2026）：Δlog率 = Δlog台数 − Δlog世帯
R["decomp_16_26_median_pct"] = {c: round(100 * pr[c].median(), 2) for c in ["dlog_rate_16_26", "dlog_cars_16_26", "dlog_hh_16_26"]}
pr["share_from_hh"] = -pr.dlog_hh_16_26 / pr.dlog_rate_16_26
R["share_of_decline_from_hh_median"] = float(pr.share_from_hh[pr.dlog_rate_16_26 < 0].median())

# ---- 3. 人口密度・鉄道との関係 ----
def sp(x, y, d=pr, perm=5000):
    rho = stats.spearmanr(d[x], d[y]).statistic
    pz = np.mean([abs(stats.spearmanr(rng.permutation(d[x].values), d[y]).statistic) >= abs(rho) for _ in range(perm)])
    loo = [stats.spearmanr(d.drop(i)[x], d.drop(i)[y]).statistic for i in d.index]
    ex3 = d.drop(["東京", "神奈川", "大阪"]); rex = stats.spearmanr(ex3[x], ex3[y]).statistic
    return dict(rho=round(float(rho), 3), p_perm=round(float(pz), 4), loo_min=round(min(loo), 3), loo_max=round(max(loo), 3), ex_big3=round(float(rex), 3))
targets = ["peak_rate_year", "hinge_tau", "peak_cars_year", "dlog_rate_16_26", "dlog_cars_16_26", "dlog_hh_16_26", "dlog_cpc_13_24", "rate2026"]
R["spearman"] = {f"{y}~{x}": sp(x, y) for y in targets for x in ["log_density", "log_rail", "share65"]}
def ols(yv, xs):
    d = pr[[yv] + xs].dropna(); Z = (d[xs] - d[xs].mean()) / d[xs].std()
    m = sm.OLS(d[yv], sm.add_constant(Z)).fit(cov_type="HC3")
    return {k: [round(float(m.params[k]), 4), round(float(m.bse[k]), 4), round(float(m.pvalues[k]), 4)] for k in xs} | {"r2": round(float(m.rsquared), 3)}
R["ols"] = {f"{yv}": ols(yv, ["log_density", "log_rail", "share65"]) for yv in ["dlog_rate_16_26", "dlog_cars_16_26", "dlog_hh_16_26"]}
R["ols_rail_density_only"] = {yv: ols(yv, ["log_density", "log_rail"]) for yv in ["dlog_rate_16_26", "dlog_cars_16_26"]}
pr["dens_g"] = pd.qcut(pr.density_hab, 3, labels=["低", "中", "高"])
g = pr.groupby("dens_g", observed=True).agg(n=("rate2026", "size"), peak_rate_year=("peak_rate_year", "median"), hinge_tau=("hinge_tau", "median"),
                                           peak_cars_year=("peak_cars_year", "median"), dlog_rate=("dlog_rate_16_26", "median"), dlog_cars=("dlog_cars_16_26", "median"),
                                           dlog_hh=("dlog_hh_16_26", "median"), dlog_cpc=("dlog_cpc_13_24", "median"), rate2026=("rate2026", "median"),
                                           cars_rising=("dlog_cars_16_26", lambda s: int((s > 0).sum())))
g.to_csv("results/by_density_tercile.csv", encoding="utf-8"); R["by_density_tercile"] = g.round(4).reset_index().to_dict("records")

# ---- 4. 軽四輪（全国軽自動車協会連合会、12月末 2015〜2025） ----
k = kei[kei.month == 12].copy(); k["kpr"] = k.kei / k.hh
kr = []
for p in PREFS:
    d = k[k.pref == p].set_index("year").kpr
    sl = np.polyfit(d.index, d.values, 1)[0]
    kr.append(dict(pref=p, kei_peak_year=int(d.idxmax()), kei_slope_per10y=float(sl * 10), kei2015=float(d.loc[2015]), kei2025=float(d.loc[2025])))
kr = pd.DataFrame(kr).set_index("pref").join(pr[["dlog_rate_16_26", "log_density", "hinge_tau", "peak_rate_year"]])
kr.to_csv("results/kei_by_pref.csv", encoding="utf-8")
R["kei_peak_year_hist"] = kr.kei_peak_year.value_counts().sort_index().to_dict()
R["kei_n_rising_2015_2025"] = int((kr.kei2025 > kr.kei2015).sum())
R["kei_slope_vs_density"] = sp("log_density", "kei_slope_per10y", d=kr)
R["kei_slope_median_by_dens"] = kr.join(pr.dens_g).groupby("dens_g", observed=True).kei_slope_per10y.median().round(4).to_dict()
km = kei[kei.month == 3].copy(); km["kpr"] = km.kei / km.hh
R["kei_march_2006_2013_n_rising"] = int(sum(km[(km.pref == p) & (km.year == 2013)].kpr.values[0] > km[(km.pref == p) & (km.year == 2006)].kpr.values[0] for p in PREFS if p in km.pref.values and len(km[(km.pref == p) & (km.year.isin([2006, 2013]))]) == 2))

# ---- 5. 頑健性：変化点の決め方の一致 ----
R["agree_peak_vs_hinge_within2"] = int((abs(pr.peak_rate_year - pr.hinge_tau) <= 2).sum())
R["agree_hinge_vs_shift_within2"] = int((abs(pr.hinge_tau - pr.hinge_shift_tau) <= 2).sum())
R["agree_hinge_vs_2010start_within2"] = int((abs(pr.hinge_tau - pr.hinge10_tau) <= 2).sum())
R["rho_peak_rate_vs_hinge"] = round(float(stats.spearmanr(pr.peak_rate_year, pr.hinge_tau).statistic), 3)
# 検出力の目安：誤差の大きさ（線形からの残差SD）
json.dump(R, open("results/summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(R, ensure_ascii=False, default=float)[:6000])
