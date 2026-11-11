"""F277 05 レビュー検算（独立レビューを受けて追加、結果を見た後の分析）→ results/review_checks.json"""
import os, json
import numpy as np, pandas as pd, statsmodels.api as sm
HERE = os.path.dirname(os.path.abspath(__file__))
P = pd.read_csv(os.path.join(HERE, "..", "results", "A_panel_with_fits.csv"))
J = json.load(open(os.path.join(HERE, "..", "results", "main.json"), encoding="utf-8"))
X5 = ["t4", "cpi", "spr", "di_biz", "di_emp"]
def loo(df, y, xs):
    df = df.reset_index(drop=True); e = []
    for i in df.index:
        m = sm.OLS(df.drop(i)[y], sm.add_constant(df.drop(i)[xs])).fit()
        e.append(float(df.loc[i, y] - m.predict(sm.add_constant(df.loc[[i], xs], has_constant="add")).iloc[0]))
    return np.array(e)
rmse = lambda e: float(np.sqrt(np.mean(np.square(e))))
out = {}
q = P[P.year >= 2004]
nv = q["y"] - q["y_prev"]
out["naive_errors_2020_2021"] = {int(y): round(float(v), 3) for y, v in zip(q.year, nv) if y in (2020, 2021)}
# 条件ごとに同じ年で比べる（第4表だけ・5指標・前年と同じ）
conds = {"base_2004_2026": q, "excl_2009_2020": q[~q.year.isin([2009, 2020])], "excl_2009_2020_2021": q[~q.year.isin([2009, 2020, 2021])]}
tab = {}
for k, d in conds.items():
    tab[k] = dict(n=len(d), naive=rmse(d["y"] - d["y_prev"]), t4_only_loo=rmse(loo(d, "y", ["t4"])), five_loo=rmse(loo(d, "y", X5)),
                  five_cal_loo=rmse(loo(d, "y", ["t4", "cpi_cal", "spr", "di_biz", "di_emp"])))
out["same_years_compare"] = tab
out["t4_only_loo_all24"] = J["M1"]["loo_rmse"]
# 円
qy = P[P.year >= 2004].copy(); qy["t4_yen"] = qy["t4"] / 100 * qy["mw_prev"]; qy["prev_yen"] = qy["y_yen"].shift(1)
qy = qy.dropna(subset=["prev_yen"])
out["yen_same_years"] = dict(n=len(qy), naive=rmse(qy["y_yen"] - qy["prev_yen"]),
                             five_loo=rmse(loo(qy, "y_yen", ["t4_yen", "cpi", "spr", "di_biz", "di_emp"])))
# 考察で挙げた形（前年＋春季賃上げ＋雇用人員DI）を事後に試す
for nm, xs in {"prev_spr_emp": ["y_prev", "spr", "di_emp"], "prev_spr": ["y_prev", "spr"], "t4_prev": ["t4", "y_prev"]}.items():
    m = sm.OLS(q["y"], sm.add_constant(q[xs])).fit()
    out["posthoc_" + nm] = dict(coef=m.params.round(4).to_dict(), p=m.pvalues.round(4).to_dict(), r2=m.rsquared, loo=rmse(loo(q, "y", xs)))
out["posthoc_prev_spr_emp_excl2020"] = rmse(loo(q[q.year != 2020], "y", ["y_prev", "spr", "di_emp"]))
# 問い直しの寄与（2021年を除いた係数）
b_all = J["reask"]["prev_spr_emp"]["coef"]["y_prev"]; b_ex = J["reask"]["prev_spr_emp_excl2021"]["coef"]["y_prev"]
y25 = float(P.loc[P.year == 2026, "y_prev"].iloc[0])
out["reask_contrib_2026"] = dict(coef_all=b_all, coef_excl2021=b_ex, low=b_ex * y25, high=b_all * y25)
d16 = P[(P.year >= 2016)]
out["reask_contrib_mean_2016_2026"] = dict(low=float((b_ex * d16["y_prev"]).mean()), high=float((b_all * d16["y_prev"]).mean()))
out["y_2009_2011_range"] = [float(P.loc[P.year.between(2009, 2011), "y"].min()), float(P.loc[P.year.between(2009, 2011), "y"].max())]
json.dump(out, open(os.path.join(HERE, "..", "results", "review_checks.json"), "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda x: round(float(x), 4)))
