"""F277 03 分析：計画（PLAN.md）の H1〜H4 と頑健性 R1〜R4 → results/"""
import os, json
import numpy as np, pandas as pd, statsmodels.api as sm
HERE = os.path.dirname(os.path.abspath(__file__))
P = pd.read_csv(os.path.join(HERE, "..", "data", "processed", "panel.csv"))
RES = os.path.join(HERE, "..", "results"); os.makedirs(RES, exist_ok=True)
X5 = ["t4", "cpi", "spr", "di_biz", "di_emp"]
out = {}

def fit(df, y, xs):
    m = sm.OLS(df[y], sm.add_constant(df[xs])).fit()
    return m

def loo(df, y, xs):
    e = []
    for i in df.index:
        tr = df.drop(i)
        m = fit(tr, y, xs)
        pr = m.predict(sm.add_constant(df.loc[[i], xs], has_constant="add"))
        e.append(float(df.loc[i, y] - pr.iloc[0]))
    return np.array(e)

def rmse(e): return float(np.sqrt(np.mean(np.square(e))))

# H1：第4表方式（Y = T4）
P["gap_t4"] = P["y"] - P["t4"]
a = P[P.year <= 2006]["gap_t4"]; b = P[P.year >= 2007]["gap_t4"]
out["H1"] = dict(mean_abs_gap_2003_2006=float(a.abs().mean()), mean_gap_2003_2006=float(a.mean()),
                 mean_gap_2007_2026=float(b.mean()),
                 mean_gap_by_period={k: float(P[(P.year >= lo) & (P.year <= hi)]["gap_t4"].mean())
                                     for k, (lo, hi) in {"2003-2006": (2003, 2006), "2007-2015": (2007, 2015),
                                                         "2016-2019": (2016, 2019), "2021-2026": (2021, 2026)}.items()},
                 rmse_t4_rule=rmse(P["gap_t4"]))
out["H1"]["verdict"] = "支持" if (out["H1"]["mean_abs_gap_2003_2006"] <= 0.5 and out["H1"]["mean_gap_2007_2026"] >= 1.0) else "外れ"

# M1, M2（24年全体）
m1 = fit(P, "y", ["t4"]); m2 = fit(P, "y", X5)
e1 = loo(P, "y", ["t4"]); e2 = loo(P, "y", X5)
out["M1"] = dict(coef=m1.params.round(4).to_dict(), r2=m1.rsquared, loo_rmse=rmse(e1))
out["M2"] = dict(coef=m2.params.round(4).to_dict(), se=m2.bse.round(4).to_dict(), p=m2.pvalues.round(4).to_dict(),
                 r2=m2.rsquared, adj_r2=m2.rsquared_adj, loo_rmse=rmse(e2),
                 loo_r2=1 - np.sum(e2 ** 2) / np.sum((P["y"] - P["y"].mean()) ** 2))
out["H2"] = dict(r2=m2.rsquared, verdict="支持" if m2.rsquared >= 0.7 else "外れ")
P["fit_m2"] = m2.fittedvalues; P["res_m2"] = m2.resid; P["loo_res_m2"] = e2
# 標準化した係数（1標準偏差あたり）
sd = P[X5].std(); out["M2"]["coef_per_sd"] = {k: float(m2.params[k] * sd[k]) for k in X5}
# H4
r2020 = float(P.loc[P.year == 2020, "res_m2"].iloc[0])
out["H4"] = dict(res_2020=r2020, min_year=int(P.loc[P["res_m2"].idxmin(), "year"]),
                 verdict="支持" if int(P.loc[P["res_m2"].idxmin(), "year"]) == 2020 else "外れ")
# H3：2003〜2015で当てはめ、2016〜2026を予測
tr = P[P.year <= 2015]; te = P[P.year >= 2016].copy()
m3 = fit(tr, "y", X5)
te["pred_m3"] = m3.predict(sm.add_constant(te[X5], has_constant="add"))
te["gap_m3"] = te["y"] - te["pred_m3"]
m3b = fit(tr, "y", ["t4"])
te["pred_m3b"] = m3b.predict(sm.add_constant(te[["t4"]], has_constant="add")); te["gap_m3b"] = te["y"] - te["pred_m3b"]
out["H3"] = dict(train_r2=m3.rsquared, coef=m3.params.round(4).to_dict(),
                 mean_gap_2016_2026=float(te["gap_m3"].mean()),
                 mean_gap_2016_2026_excl2020=float(te[te.year != 2020]["gap_m3"].mean()),
                 by_year={int(r.year): [round(r.y, 3), round(r.pred_m3, 3), round(r.gap_m3, 3)] for r in te.itertuples()},
                 t4only_mean_gap=float(te["gap_m3b"].mean()),
                 t4only_mean_gap_excl2020=float(te[te.year != 2020]["gap_m3b"].mean()))
out["H3"]["verdict"] = "支持" if out["H3"]["mean_gap_2016_2026"] >= 1.0 else "外れ"
P = P.merge(te[["year", "pred_m3", "gap_m3", "pred_m3b"]], on="year", how="left")

# 比べる基準：前年と同じ上げ幅（2004〜）
q = P[P.year >= 2004]
out["naive_prev"] = dict(rmse=rmse(q["y"] - q["y_prev"]), m2_loo_rmse_same_years=rmse(q["loo_res_m2"]))
mlag = fit(q, "y", X5 + ["y_prev"]); el = loo(q.reset_index(drop=True), "y", X5 + ["y_prev"])
out["M2_plus_lag"] = dict(coef=mlag.params.round(4).to_dict(), p=mlag.pvalues.round(4).to_dict(), r2=mlag.rsquared, loo_rmse=rmse(el))

# 頑健性
rob = {}
# R1 物価を暦年の前年比に
X5c = ["t4", "cpi_cal", "spr", "di_biz", "di_emp"]
mr1 = fit(P, "y", X5c); er1 = loo(P, "y", X5c)
tr1 = fit(tr, "y", X5c); g1 = te["y"] - tr1.predict(sm.add_constant(te[X5c], has_constant="add"))
rob["R1_cpi_calendar"] = dict(r2=mr1.rsquared, loo_rmse=rmse(er1), h3_mean_gap=float(g1.mean()),
                              res_min_year=int(P.loc[mr1.resid.idxmin(), "year"]))
# R2 2020年と2009年を除く
d2 = P[~P.year.isin([2020, 2009])].reset_index(drop=True)
mr2 = fit(d2, "y", X5); er2 = loo(d2, "y", X5)
tr2 = d2[d2.year <= 2015]; te2 = d2[d2.year >= 2016]
g2 = te2["y"] - fit(tr2, "y", X5).predict(sm.add_constant(te2[X5], has_constant="add"))
rob["R2_excl_2020_2009"] = dict(r2=mr2.rsquared, loo_rmse=rmse(er2), h3_mean_gap=float(g2.mean()),
                                h1_gap_2007_2026=float((d2[d2.year >= 2007]["y"] - d2[d2.year >= 2007]["t4"]).mean()))
# R3 目安に近い値（上乗せの単純平均を引いた値、2016〜2025）
te3 = te[te.year <= 2025].copy()
rob["R3_meyasu_approx"] = dict(mean_gap_vs_m3=float((te3["y_meyasu_approx"] - te3["pred_m3"]).mean()),
                               mean_gap_vs_m3_excl2020=float((te3[te3.year != 2020]["y_meyasu_approx"] - te3[te3.year != 2020]["pred_m3"]).mean()),
                               mean_gap_vs_t4=float((te3["y_meyasu_approx"] - te3["t4"]).mean()),
                               mean_addon_by_year={int(r.year): round(float(P.loc[P.year == r.year, "addon_mean"].iloc[0]), 2) for r in te3.itertuples()})
# R4 金額（円）で
P["t4_yen"] = P["t4"] / 100 * P["mw_prev"]
P["gap_yen"] = P["y_yen"] - P["t4_yen"]
X5y = ["t4_yen", "cpi", "spr", "di_biz", "di_emp"]
mr4 = fit(P, "y_yen", X5y); er4 = loo(P, "y_yen", X5y)
tr4 = P[P.year <= 2015]; te4 = P[P.year >= 2016]
g4 = te4["y_yen"] - fit(tr4, "y_yen", X5y).predict(sm.add_constant(te4[X5y], has_constant="add"))
rob["R4_yen"] = dict(r2=mr4.rsquared, loo_rmse_yen=rmse(er4), h3_mean_gap_yen=float(g4.mean()),
                     mean_gap_yen_2003_2006=float(P[P.year <= 2006]["gap_yen"].mean()),
                     mean_gap_yen_2007_2026=float(P[P.year >= 2007]["gap_yen"].mean()),
                     gap_yen_2026=float(P.loc[P.year == 2026, "gap_yen"].iloc[0]),
                     naive_prev_rmse_yen=rmse((P["y_yen"] - P["y_yen"].shift(1)).iloc[1:]))
out["robust"] = rob

json.dump(out, open(os.path.join(RES, "main.json"), "w"), ensure_ascii=False, indent=1, default=float)
P.to_csv(os.path.join(RES, "A_panel_with_fits.csv"), index=False, float_format="%.4f")
print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda x: round(float(x), 4)))

# ---- 問い直し（結果を見た後に追加）：第4表は前年の最低賃金の引上げを映していないか ----
q = P[P.year >= 2004].reset_index(drop=True)
rq = {}
for name, xs in {"prev_only": ["y_prev"], "spr_only": ["spr"], "prev_spr": ["y_prev", "spr"],
                 "prev_spr_emp": ["y_prev", "spr", "di_emp"], "prev_spr_emp_cpi": ["y_prev", "spr", "di_emp", "cpi"]}.items():
    m = fit(q, "t4", xs)
    rq[name] = dict(coef=m.params.round(4).to_dict(), se=m.bse.round(4).to_dict(), p=m.pvalues.round(4).to_dict(), r2=m.rsquared, n=int(m.nobs))
# 2021年を除く・2009年を除く
for nm, ex in {"prev_spr_emp_excl2021": [2021], "prev_spr_emp_excl2009_2021": [2009, 2021]}.items():
    d = q[~q.year.isin(ex)]
    m = fit(d, "t4", ["y_prev", "spr", "di_emp"])
    rq[nm] = dict(coef=m.params.round(4).to_dict(), p=m.pvalues.round(4).to_dict(), r2=m.rsquared, n=int(m.nobs))
# 前年の引上げの寄与（prev_spr_emp の係数 × 前年の引上げ率）
b = rq["prev_spr_emp"]["coef"]["y_prev"]
q["t4_from_prev"] = b * q["y_prev"]
rq["contrib_prev_mean_2016_2026"] = float(q[q.year >= 2016]["t4_from_prev"].mean())
rq["t4_mean_2016_2026"] = float(q[q.year >= 2016]["t4"].mean())
rq["contrib_prev_2026"] = float(q.loc[q.year == 2026, "t4_from_prev"].iloc[0])
rq["t4_2026"] = float(q.loc[q.year == 2026, "t4"].iloc[0])
rq["case_2021"] = dict(y_prev=float(q.loc[q.year == 2021, "y_prev"].iloc[0]), t4=float(q.loc[q.year == 2021, "t4"].iloc[0]),
                       spr=float(q.loc[q.year == 2021, "spr"].iloc[0]),
                       fitted_prev_spr_emp=float(fit(q, "t4", ["y_prev", "spr", "di_emp"]).fittedvalues[q.index[q.year == 2021][0]]))
# 第4表から前年の引上げの分を除いた値で H1 の差を出し直す
P = P.merge(q[["year", "t4_from_prev"]], on="year", how="left")
P["t4_net"] = P["t4"] - P["t4_from_prev"]
rq["gap_net_mean_2007_2026"] = float((P[P.year >= 2007]["y"] - P[P.year >= 2007]["t4_net"]).mean())
out["reask"] = rq
json.dump(out, open(os.path.join(RES, "main.json"), "w"), ensure_ascii=False, indent=1, default=float)
P.to_csv(os.path.join(RES, "A_panel_with_fits.csv"), index=False, float_format="%.4f")
print(json.dumps(rq, ensure_ascii=False, indent=1, default=lambda x: round(float(x), 4)))
