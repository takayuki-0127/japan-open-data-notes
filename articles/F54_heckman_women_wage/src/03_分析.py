"""集計データ版の Heckman の2段階推定。
1段目：セル（都道府県×年齢階級）の「働いている割合」p を probit 変換し、年齢＋都道府県の条件（X）＋除外制約の変数（Z）で回帰（人数で重みづけ）。
2段目：働いている人の平均賃金（対数）を 年齢＋X＋逆ミルズ比 λ で回帰（労働者数で重みづけ）。λ の係数 θ（=ρσ）が選択バイアスの大きさ。
信頼区間は都道府県を単位にしたブートストラップ（500回）。"""
import numpy as np, pandas as pd, json
import statsmodels.api as sm
from scipy.stats import norm
from common import DATA, RES, AGES, SEED

cell = pd.read_csv(DATA/"cells.csv")
cell["logw"] = np.log(cell["wage"])
cell["childage"] = cell["age"].isin(["25-29","30-34","35-39","40-44"]).astype(float)
for z in ["cap_per_child","enroll_per_child","tfr","wait_per_cap"]:
    cell[z+"_x_child"] = cell[z] * cell["childage"]
X = ["log_minwage","jobs_ratio","univ_rate","log_pop"]

def design(d, cols):
    A = pd.get_dummies(d["age"], prefix="a", drop_first=True, dtype=float)
    M = pd.concat([A, d[cols].astype(float)], axis=1)
    return sm.add_constant(M, has_constant="add")

def heckman(d, Z, pvar="p_main", drop_lambda=False):
    p = d[pvar].clip(0.01, 0.99)
    y1 = norm.ppf(p)
    W1 = d["known"]
    s1 = sm.WLS(y1, design(d, X+Z), weights=W1).fit()
    idx = s1.fittedvalues
    lam = pd.Series(norm.pdf(idx) / norm.cdf(idx), index=d.index)
    D2 = design(d, X)
    if not drop_lambda:
        D2["lambda"] = lam.values
    s2 = sm.WLS(d["logw"], D2, weights=d["workers"]).fit()
    theta = s2.params.get("lambda", 0.0)
    corr = d["logw"] - theta*lam               # 全員が働いた場合の平均（対数賃金）の推定
    zF = None
    if Z:
        r = s1.f_test(", ".join(f"{z} = 0" for z in Z))
        zF = float(np.squeeze(r.fvalue))
    return dict(theta=float(theta), s1=s1, s2=s2, lam=lam, corr=corr, zF=zF)

def summarize(d, res):
    w = d["workers"]
    obs = np.exp(np.average(d["logw"], weights=d["known"]))
    cor = np.exp(np.average(res["corr"], weights=d["known"]))
    return obs, cor

def boot(d, Z, pvar="p_main", B=500):
    rng = np.random.default_rng(SEED)
    prefs = d["pref"].unique()
    th, gap = [], []
    for b in range(B):
        pick = rng.choice(prefs, len(prefs), replace=True)
        bd = pd.concat([d[d["pref"]==p] for p in pick], ignore_index=True)
        try:
            r = heckman(bd, Z, pvar)
        except Exception:
            continue
        o, c = summarize(bd, r)
        th.append(r["theta"]); gap.append(c/o - 1)
    return np.percentile(th,[2.5,97.5]).tolist(), np.percentile(gap,[2.5,97.5]).tolist()

out = {}
specs = {
    "base": (["cap_per_child_x_child","tfr_x_child"], "p_main"),
}
fem = cell[cell["sex"]=="女"].reset_index(drop=True)
mal = cell[cell["sex"]=="男"].reset_index(drop=True)

# 本体
Zb = ["cap_per_child_x_child","tfr_x_child"]
rf = heckman(fem, Zb)
rm = heckman(mal, Zb)
o_f, c_f = summarize(fem, rf); o_m, c_m = summarize(mal, rm)
ci_th_f, ci_gap_f = boot(fem, Zb)
ci_th_m, ci_gap_m = boot(mal, Zb)
out["base"] = dict(
    women=dict(theta=rf["theta"], theta_ci=ci_th_f, obs=o_f, corr=c_f, gap=c_f/o_f-1, gap_ci=ci_gap_f, firstF=rf["zF"],
               s1_coef={k: float(v) for k,v in rf["s1"].params.items() if k in Zb+X},
               s1_se={k: float(v) for k,v in rf["s1"].bse.items() if k in Zb+X}),
    men=dict(theta=rm["theta"], theta_ci=ci_th_m, obs=o_m, corr=c_m, gap=c_m/o_m-1, gap_ci=ci_gap_m, firstF=rm["zF"]),
)
# 男女差（年齢をそろえた加重平均：両性とも「女性の人口構成」で重み）
def agg(d, col, wcol="known"):
    return d.groupby("age").apply(lambda g: np.exp(np.average(g[col], weights=g[wcol])))
fem["corr"] = rf["corr"].values; mal["corr"] = rm["corr"].values
fem["lam"] = rf["lam"].values; mal["lam"] = rm["lam"].values
by_age = pd.DataFrame({
    "女_観察": agg(fem,"logw"), "女_補正": agg(fem,"corr"),
    "男_観察": agg(mal,"logw"), "男_補正": agg(mal,"corr"),
    "女_主に仕事": fem.groupby("age").apply(lambda g: np.average(g["p_main"], weights=g["known"])),
    "男_主に仕事": mal.groupby("age").apply(lambda g: np.average(g["p_main"], weights=g["known"])),
})
by_age["差_観察"] = 1 - by_age["女_観察"]/by_age["男_観察"]
by_age["差_女性補正"] = 1 - by_age["女_補正"]/by_age["男_観察"]
by_age = by_age.drop(columns=["男_補正"])
by_age.round(4).to_csv(RES/"by_age.csv")
out["gap_overall"] = dict(obs=float(1-o_f/o_m), women_corrected_vs_men_obs=float(1-c_f/o_m))
fem.to_csv(RES/"cells_women_fitted.csv", index=False); mal.to_csv(RES/"cells_men_fitted.csv", index=False)

# 頑健性
rob = []
def add(name, d, Z, pvar="p_main", sex="女"):
    r = heckman(d, Z, pvar); o, c = summarize(d, r)
    ci, gci = boot(d, Z, pvar, B=200)
    rob.append(dict(spec=name, sex=sex, theta=r["theta"], theta_lo=ci[0], theta_hi=ci[1], ratio_corr_obs=c/o, lo=1+gci[0], hi=1+gci[1], firstF=r["zF"]))
add("本体（定員×子育て年齢・出生率×子育て年齢）", fem, Zb)
add("除外＝保育所の定員×子育て年齢のみ", fem, ["cap_per_child_x_child"])
add("除外＝出生率×子育て年齢のみ", fem, ["tfr_x_child"])
add("除外＝保育所の在所児×子育て年齢", fem, ["enroll_per_child_x_child","tfr_x_child"])
add("除外＝県の水準そのもの（定員・出生率）", fem, ["cap_per_child","tfr"])
add("除外なし（関数形だけで識別）", fem, [])
add("働く＝就業者（パート含む）", fem, Zb, "p_emp")
add("東京を除く", fem[fem["pref"]!="東京都"].reset_index(drop=True), Zb)
add("25〜59歳のみ", fem[~fem["age"].isin(["20-24","60-64"])].reset_index(drop=True), Zb)
add("男性（本体と同じ設定）", mal, Zb, sex="男")
add("男性・働く＝就業者", mal, Zb, "p_emp", sex="男")
pd.DataFrame(rob).round(4).to_csv(RES/"robustness.csv", index=False)

# OLS（補正なし）との比較：2段目の X の係数
cmp = pd.DataFrame({
    "補正なし": heckman(fem, Zb, drop_lambda=True)["s2"].params[X],
    "補正あり": rf["s2"].params[X],
}).round(4)
cmp.to_csv(RES/"stage2_compare.csv")
json.dump(out, open(RES/"summary.json","w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
print(by_age.round(3)); print(pd.DataFrame(rob).round(3).to_string()); print(cmp)
print(rf["s1"].summary().tables[1]); print(rf["s2"].summary().tables[1])
