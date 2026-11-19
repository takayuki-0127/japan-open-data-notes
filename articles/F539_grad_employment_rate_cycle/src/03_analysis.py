"""就職率と前年度の有効求人倍率の関係：水準の回帰、差分の回帰、期間別、ブロック・ブートストラップ、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"; RES.mkdir(exist_ok=True)
df = pd.read_csv(BASE / "data" / "panel.csv", index_col="grad_year")
SEED = 20261116
Y0, Y1 = 1964, 2025


def ols(y, X, hac=3):
    X = sm.add_constant(X, has_constant="add")
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac})


def level(d, ycol="univ_t", xcol="yuko_fy_lag1", dummy=True):
    d = d[[ycol, xcol]].dropna().copy()
    X = d[[xcol]].copy()
    if dummy:
        X["post2000"] = (d.index >= 2000).astype(float)
    return ols(d[ycol], X), d


def diff(d, ycol="univ_t", xcol="yuko_fy_lag1", drop=()):
    dd = d[[ycol, xcol]].dropna().diff().dropna()
    dd = dd.drop([y for y in drop if y in dd.index])
    return ols(dd[ycol], dd[[xcol]]), dd


def coef(res, name):
    ci = res.conf_int().loc[name]
    return {"b_per_0.1": round(res.params[name] / 10, 3), "ci_lo_per_0.1": round(ci[0] / 10, 3), "ci_hi_per_0.1": round(ci[1] / 10, 3),
            "p": round(float(res.pvalues[name]), 4), "n": int(res.nobs), "r2": round(float(res.rsquared), 3)}


base = df.loc[Y0:Y1]
main = {}
# H1 水準の回帰（倍率のみ）と H3（2000年以降ダミー）
r_lv0, d0 = level(base, dummy=False)
r_lv, d1 = level(base, dummy=True)
main["H1"] = {**coef(r_lv0, "yuko_fy_lag1")}
main["H1"]["judge"] = "支持" if main["H1"]["b_per_0.1"] >= 1 else "外れ"
main["level_with_post2000"] = {**coef(r_lv, "yuko_fy_lag1"), "post2000": round(float(r_lv.params["post2000"]), 2),
                               "post2000_ci": [round(float(x), 2) for x in r_lv.conf_int().loc["post2000"]],
                               "const": round(float(r_lv.params["const"]), 2)}
main["H3"] = {"post2000_pt": main["level_with_post2000"]["post2000"], "ci": main["level_with_post2000"]["post2000_ci"],
              "judge": "支持" if main["level_with_post2000"]["post2000"] <= -3 else "外れ"}

# H2 差分
r_df, dd = diff(base)
main["H2"] = coef(r_df, "yuko_fy_lag1")
main["H2"]["judge"] = "支持" if main["H2"]["ci_lo_per_0.1"] > 0 else "外れ"

# 非対称（倍率が上がった年と下がった年）
dd2 = dd.copy()
dd2["up"] = dd2["yuko_fy_lag1"].clip(lower=0); dd2["down"] = dd2["yuko_fy_lag1"].clip(upper=0)
r_as = ols(dd2["univ_t"], dd2[["up", "down"]])
main["asymmetry"] = {"up": coef(r_as, "up"), "down": coef(r_as, "down"),
                     "n_up_years": int((dd2["yuko_fy_lag1"] > 0).sum()), "n_down_years": int((dd2["yuko_fy_lag1"] < 0).sum())}

# H4 男女
r_m, _ = diff(base, "univ_m"); r_f, _ = diff(base, "univ_f")
main["H4"] = {"male": coef(r_m, "yuko_fy_lag1"), "female": coef(r_f, "yuko_fy_lag1")}
main["H4"]["ratio_f_m"] = round(main["H4"]["female"]["b_per_0.1"] / main["H4"]["male"]["b_per_0.1"], 3)
main["H4"]["judge"] = "支持" if main["H4"]["ratio_f_m"] >= 1.2 else "外れ"

# 期間別（差分）
per = {}
for a, b in [(1964, 1990), (1991, 2010), (2011, 2025)]:
    r, _ = diff(df.loc[a:b])
    per[f"{a}-{b}"] = coef(r, "yuko_fy_lag1")
main["by_period_diff"] = per

# ブロック・ブートストラップ（差分の係数、ブロック長4）
rng = np.random.default_rng(SEED)
arr = dd[["univ_t", "yuko_fy_lag1"]].to_numpy()
n, L, B = len(arr), 4, 1000
bs = []
for _ in range(B):
    idx = []
    while len(idx) < n:
        s = rng.integers(0, n - L + 1)
        idx.extend(range(s, s + L))
    a = arr[idx[:n]]
    x = a[:, 1] - a[:, 1].mean(); y = a[:, 0] - a[:, 0].mean()
    bs.append((x @ y) / (x @ x) / 10)
bs = np.array(bs)
main["H2_block_bootstrap"] = {"B": B, "block": L, "seed": SEED, "ci_lo": round(float(np.quantile(bs, 0.025)), 3),
                              "ci_hi": round(float(np.quantile(bs, 0.975)), 3)}

# 主な年の値
pick = [1991, 1993, 2000, 2003, 2008, 2010, 2019, 2021, 2025]
main["years"] = {str(y): {"univ_t": df.loc[y, "univ_t"], "yuko_fy_lag1": df.loc[y, "yuko_fy_lag1"]} for y in pick}
mn = base["univ_t"].idxmin(); mx = base["univ_t"].idxmax()
main["min_year"] = {"year": int(mn), "univ_t": float(base.loc[mn, "univ_t"]), "yuko_fy_lag1": float(base.loc[mn, "yuko_fy_lag1"])}
main["max_year"] = {"year": int(mx), "univ_t": float(base.loc[mx, "univ_t"]), "yuko_fy_lag1": float(base.loc[mx, "yuko_fy_lag1"])}
main["corr_level"] = round(float(d0.corr().iloc[0, 1]), 3)
main["corr_diff"] = round(float(dd.corr().iloc[0, 1]), 3)

# 頑健性（差分の係数、0.1あたり）
rob = []
def add(name, d, ycol="univ_t", xcol="yuko_fy_lag1", note="", drop=()):
    r, _ = diff(d, ycol, xcol, drop)
    c = coef(r, xcol)
    rob.append({"check": name, **c, "note": note})
add("主（大学計、前年度の有効求人倍率、1964〜2025年）", base)
add("新規求人倍率にする", base, xcol="shinki_fy_lag1", note="新規は有効より水準が高い")
add("卒業した年の年度の有効求人倍率", base, xcol="yuko_fy_lag0")
add("前年（暦年）の有効求人倍率", base, xcol="yuko_cy_lag1")
add("2020・2021年の変化を除く", base, drop=(2020, 2021), note="前の年からの変化のうち2020年と2021年を除く")
add("1990年以降だけ", df.loc[1990:2025])
add("短期大学", base, ycol="jc_t")
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rob.to_dict(orient="records")

# 水準の回帰の当てはめ（図用）
fit = d1.copy()
fit["fitted"] = r_lv.fittedvalues
fit["resid"] = r_lv.resid
fit.round(3).to_csv(RES / "level_fit.csv")
base.round(3).to_csv(RES / "series.csv")
pd.DataFrame({"b_per_0.1": bs}).describe().round(3).to_csv(RES / "bootstrap_summary.csv")
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True, default=float), encoding="utf-8")
print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H4", "asymmetry", "by_period_diff", "H2_block_bootstrap", "min_year", "max_year", "corr_level", "corr_diff"]}, ensure_ascii=False, indent=1))
print(rob.to_string())
