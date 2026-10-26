"""因果フォレスト（econml CausalForestDML）で、県×年ごとの効果を推定する"""
import json, numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import GroupKFold
from lightgbm import LGBMRegressor
from econml.dml import CausalForestDML, LinearDML
from common import DATA, RES, X_COLS, SEED

def nuis():
    return LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=8, min_child_samples=15,
                         subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=SEED, verbose=-1)

def sample(df, years="main"):
    if years == "main":   # コロナの3年（2020〜22）を除く
        return df[~df.year.isin([2020, 2021, 2022])].copy()
    if years == "pre":    return df[df.year <= 2019].copy()
    if years == "post":   return df[df.year >= 2016].copy()
    if years == "all":    return df.copy()
    raise ValueError(years)

def arrays(d, outcome="d_emp"):
    W = pd.concat([pd.get_dummies(d.year, prefix="y", drop_first=True).astype(float),
                   d[["lag_d_emp", "lag_d_jor"]]], axis=1)
    return d[outcome].values, d["treat"].values, d[X_COLS].values, W.values, d["code"].values

def fit_cf(d, outcome="d_emp", leaf=10, depth=None, n=2000, seed=SEED):
    Y, T, X, W, g = arrays(d, outcome)
    cf = CausalForestDML(model_y=nuis(), model_t=nuis(), cv=GroupKFold(5), n_estimators=n,
                         min_samples_leaf=leaf, max_depth=depth, max_samples=0.45, honest=True,
                         inference=True, random_state=seed)
    cf.fit(Y, T, X=X, W=W, groups=g, cache_values=True)
    return cf

def ols_fd(d, outcome="d_emp"):
    """参考：前年差の回帰（年効果つき、県クラスター）"""
    Y, T, X, W, g = arrays(d, outcome)
    Z = sm.add_constant(np.column_stack([T, W]))
    r = sm.OLS(Y, Z).fit(cov_type="cluster", cov_kwds={"groups": g})
    return r.params[1], r.bse[1]

if __name__ == "__main__":
    df = pd.read_csv(DATA / "f17_panel.csv")
    d = sample(df, "main")
    cf = fit_cf(d)
    Y, T, X, W, g = arrays(d)
    ate = cf.ate_inference(X=X)
    a_lo, a_hi = ate.conf_int_mean(alpha=0.05)
    tau = cf.effect(X); lo, hi = cf.effect_interval(X, alpha=0.05)
    d["tau"], d["tau_lo"], d["tau_hi"] = tau, lo, hi
    # 線形 DML（効果は一定）と前年差の回帰
    ld = LinearDML(model_y=nuis(), model_t=nuis(), cv=GroupKFold(5), random_state=SEED)
    ld.fit(Y, T, X=None, W=np.column_stack([X, W]), groups=g)
    lsi = ld.ate_inference(); lci = lsi.conf_int_mean(alpha=0.05)
    ld_pt = float(np.ravel(lsi.mean_point)[0]); ld_ci = (np.ravel(lci[0])[0], np.ravel(lci[1])[0])
    b, se = ols_fd(d)
    # 県ごとの平均効果
    pref = d.groupby(["code", "pref"]).agg(tau=("tau", "mean"), tau_lo=("tau_lo", "mean"), tau_hi=("tau_hi", "mean"),
                                           bite=("bite", "first")).reset_index()
    pref["ci_excl0"] = (pref.tau_lo > 0) | (pref.tau_hi < 0)
    pref.round(4).to_csv(RES / "pref_effects.csv", index=False)
    d[["code", "pref", "year", "treat", "d_emp", "tau", "tau_lo", "tau_hi"]].round(5).to_csv(RES / "obs_effects.csv", index=False)
    # 特徴量の重要度
    imp = pd.Series(cf.feature_importances_, index=X_COLS).sort_values(ascending=False)
    imp.round(4).to_csv(RES / "feature_importance.csv", header=["importance"])
    # 残差（交差適合）を使った検証：BLP と GATES（予測効果の4分位）
    yr, tr = cf.residuals_[0].ravel(), cf.residuals_[1].ravel()
    # 予測効果は、県のグループごとに外した森で出す（自分を学習に使わない）
    tau_cv = np.zeros(len(d))
    for k, (tr_i, te_i) in enumerate(GroupKFold(5).split(X, groups=g)):
        sub = d.iloc[tr_i]
        m = fit_cf(sub, n=1000, seed=SEED + k)
        tau_cv[te_i] = m.effect(X[te_i])
    d["tau_cv"] = tau_cv
    cen = tau_cv - tau_cv.mean()
    blp = sm.OLS(yr, np.column_stack([tr, tr * cen])).fit(cov_type="cluster", cov_kwds={"groups": g})
    d["q"] = pd.qcut(tau_cv, 4, labels=[1, 2, 3, 4])
    gates = []
    for q, sub in d.assign(yr=yr, tr=tr).groupby("q"):
        r = sm.OLS(sub.yr, sub.tr).fit(cov_type="cluster", cov_kwds={"groups": sub.code})
        gates.append({"q": int(q), "pred_mean": sub.tau_cv.mean(), "actual": r.params.iloc[0], "se": r.bse.iloc[0], "n": len(sub)})
    gates = pd.DataFrame(gates); gates["lo"] = gates.actual - 1.96 * gates.se; gates["hi"] = gates.actual + 1.96 * gates.se
    gates.round(4).to_csv(RES / "gates.csv", index=False)
    # 上位4分の1と下位4分の1の特徴の比較
    d["grp"] = np.where(d.q == 4, "下がりにくい側（予測の上位25%）", np.where(d.q == 1, "下がりやすい側（予測の下位25%）", "中間"))
    comp = d[d.grp != "中間"].groupby("grp")[X_COLS].mean().T
    comp.round(3).to_csv(RES / "high_low_compare.csv")
    d.drop(columns=["grp"]).to_csv(DATA / "f17_panel_with_tau.csv", index=False)
    out = {"n": len(d), "n_pref": int(d.code.nunique()), "years": sorted(d.year.unique().tolist()),
           "ate": float(ate.mean_point), "ate_lo": float(np.ravel(a_lo)[0]), "ate_hi": float(np.ravel(a_hi)[0]),
           "linear_dml": ld_pt, "linear_dml_ci": [float(ld_ci[0]), float(ld_ci[1])],
           "ols_fd": float(b), "ols_fd_ci": [float(b - 1.96 * se), float(b + 1.96 * se)],
           "tau_sd": float(tau.std()), "tau_p10": float(np.percentile(tau, 10)), "tau_p90": float(np.percentile(tau, 90)),
           "share_obs_ci_excl0": float(((lo > 0) | (hi < 0)).mean()),
           "n_pref_ci_excl0": int(pref.ci_excl0.sum()),
           "blp_mean": float(blp.params[0]), "blp_mean_se": float(blp.bse[0]),
           "blp_het": float(blp.params[1]), "blp_het_se": float(blp.bse[1]), "blp_het_p": float(blp.pvalues[1]),
           "corr_tau_cv_full": float(np.corrcoef(tau, tau_cv)[0, 1]),
           "treat_sd_within_year": float(d.groupby("year").treat.std().mean())}
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(imp.round(3)); print(gates.round(3)); print(comp.round(2))
    print(pref.sort_values("tau").round(3).to_string())
