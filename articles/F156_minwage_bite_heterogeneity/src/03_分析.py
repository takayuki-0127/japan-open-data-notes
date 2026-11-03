"""最低賃金の効き方は「賃金の低さ」で違うか。
(A) 全国の引き上げ × 県の賃金の低さ（年の効果を除いても残る、県による差）
(B) 同じ年の中の、県による上げ幅の違い（因果フォレスト・LinearDML）
を同じパネルで推定し、賃金（短時間労働者の時給）と雇用（就業率など）で比べる。
"""
import json, warnings
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from common import DATA, RES, SEED
warnings.filterwarnings("ignore")
rng = np.random.default_rng(SEED)

w = pd.read_csv(DATA / "panel_wage.csv")
e = pd.read_csv(DATA / "panel_emp.csv")
MODS = {"low_wage": "賃金の低さ（2009〜11年の短時間労働者の平均時給、低いほど＋）",
        "bite": "最低賃金÷平均時給（2009〜11年）",
        "low_mw": "最低賃金の低さ（2011年度の額、低いほど＋）"}
for d in (w, e):
    d["low_wage"] = -(d.wage0 - d.wage0.mean()) / d.wage0.std()
    d["bite"] = (d.bite0 - d.bite0.mean()) / d.bite0.std()
    d["low_mw"] = -(d.lmw0 - d.lmw0.mean()) / d.lmw0.std()
    d["terc"] = pd.qcut(d.drop_duplicates("code").set_index("code").wage0.rank(method="first"), 3, labels=["低", "中", "高"]).reindex(d.code).values

W_MAIN = w[w.year.between(2012, 2019)].copy()
E_MAIN = e[e.year.between(2012, 2019) | e.year.between(2023, 2025)].dropna(subset=["d_emp", "lag_d_emp"]).copy()
OUT = {"wage": ("dlw", W_MAIN), "workers": ("dlworkers", W_MAIN), "emp": ("d_emp", E_MAIN), "unemp": ("d_unemp", E_MAIN)}
LABEL = {"wage": "短時間労働者の時給（前年比、%）", "workers": "短時間労働者の数（前年比、%）",
         "emp": "就業率（前年差、%pt）", "unemp": "完全失業率（前年差、%pt）"}

def fit(formula, d, groups="code"):
    return smf.ols(formula, d).fit(cov_type="cluster", cov_kwds={"groups": d[groups]})

def inter(y, d, mod, extra="", fe="C(year)"):
    f = f"{y} ~ dlmw + dlmw:{mod} + {mod} + {fe}{extra}"
    m = fit(f, d)
    k = f"dlmw:{mod}"
    return dict(main=m.params["dlmw"], main_se=m.bse["dlmw"], b=m.params[k], se=m.bse[k], p=m.pvalues[k], n=int(m.nobs))

rows = []
# (A) 主分析：交互作用（年の効果あり）。県の水準の違い（mod の主効果）も入れる
for o, (y, d) in OUT.items():
    for mod in MODS:
        ex = " + lag_d_emp" if o in ("emp", "unemp") else ""
        r = inter(y, d, mod, ex); r.update(outcome=o, mod=mod, spec="基本"); rows.append(r)
main = pd.DataFrame(rows)

# 3つに分けた県（平均時給の高・中・低）ごとの傾き：年の効果があるので「高」との差だけを見る
grp = []
for o, (y, d) in OUT.items():
    ex = " + lag_d_emp" if o in ("emp", "unemp") else ""
    m = fit(f"{y} ~ dlmw:C(terc, Treatment('高')) + C(terc) + C(year){ex}", d)
    for g in ["低", "中"]:
        k = f"dlmw:C(terc, Treatment('高'))[{g}]"
        grp.append(dict(outcome=o, group=g, diff=m.params[k], se=m.bse[k], p=m.pvalues[k]))
    # 年ごとの全国の引き上げ×グループ（イベント風）：2012年からの累積の差
grp = pd.DataFrame(grp)

# 長い差（2011→2019年）：県ごとの変化と賃金の低さ
L = w[w.year.isin([2011, 2019])].pivot(index="code", columns="year", values="wage")
pb = w.drop_duplicates("code").set_index("code")
E = e[e.year.isin([2011, 2019])].pivot(index="code", columns="year", values="emp_rate")
long = pd.DataFrame({"pref": pb.pref, "wage0": pb.wage0, "bite0": pb.bite0, "region": pb.region,
                     "dlw_11_19": np.log(L[2019] / L[2011]) * 100,
                     "dlmw_11_19": (np.log(pb.index.map(lambda c: 1)) * 0),
                     "demp_11_19": E[2019] - E[2011]})
mwc = w[w.year.isin([2012, 2020])].pivot(index="code", columns="year", values="mw_june")  # 2011→2019年度
long["dlmw_11_19"] = np.log(mwc[2020] / mwc[2012]) * 100
long.round(4).to_csv(RES / "long_diff.csv")
lc = {k: float(np.corrcoef(long[a], long[b])[0, 1]) for k, (a, b) in
      {"wage_vs_wage0": ("dlw_11_19", "wage0"), "mw_vs_wage0": ("dlmw_11_19", "wage0"), "emp_vs_wage0": ("demp_11_19", "wage0"),
       "wage_vs_bite0": ("dlw_11_19", "bite0"), "emp_vs_bite0": ("demp_11_19", "bite0")}.items()}

# (B) 同じ年の中の上げ幅の違いだけを使う：DML（年ダミーで T と Y を残差にする）
from econml.dml import CausalForestDML, LinearDML
from lightgbm import LGBMRegressor
from sklearn.linear_model import LassoCV
from sklearn.model_selection import GroupKFold

def dml_frames(o):
    y, d = OUT[o]
    d = d.dropna(subset=[y, "dlmw"]).reset_index(drop=True)
    Wm = pd.get_dummies(d.year.astype(str), prefix="y", drop_first=True).astype(float)
    if o in ("emp", "unemp"):
        Wm["lag"] = d["lag_d_emp"].values
    X = d[["low_wage"]].values
    return d, d[y].values, d["dlmw"].values, X, Wm.values

forest_res, blp_rows, curve = {}, [], []
for o in ["wage", "emp"]:
    d, Y, T, X, Wm = dml_frames(o)
    groups = d["code"].values
    lin = LinearDML(model_y=LassoCV(cv=5), model_t=LassoCV(cv=5), cv=GroupKFold(5), random_state=SEED)
    lin.fit(Y, T, X=X, W=Wm, groups=groups)
    ci = lin.coef__interval(alpha=0.05)
    cf = CausalForestDML(model_y=LGBMRegressor(n_estimators=200, learning_rate=0.05, min_child_samples=10, verbose=-1, random_state=SEED),
                         model_t=LGBMRegressor(n_estimators=200, learning_rate=0.05, min_child_samples=10, verbose=-1, random_state=SEED),
                         n_estimators=2000, min_samples_leaf=10, honest=True, cv=GroupKFold(5), random_state=SEED)
    cf.fit(Y, T, X=X, W=Wm, groups=groups, cache_values=True)
    ate = cf.ate_inference(X=X)
    grid = np.linspace(X.min(), X.max(), 25).reshape(-1, 1)
    lo, hi = cf.effect_interval(grid, alpha=0.05)
    for g, m_, a, b in zip(grid[:, 0], cf.effect(grid), lo, hi):
        curve.append(dict(outcome=o, low_wage=g, cate=m_, lo=a, hi=b))
    # 県を地方ごとに外して予測し直した効果で検証（BLP）：残差の積に効果の差が表れるか
    regs = d["region"].values
    tau_oos = np.zeros(len(d))
    for r in np.unique(regs):
        tr = regs != r
        m_ = CausalForestDML(model_y=LGBMRegressor(n_estimators=200, learning_rate=0.05, min_child_samples=10, verbose=-1, random_state=SEED),
                             model_t=LGBMRegressor(n_estimators=200, learning_rate=0.05, min_child_samples=10, verbose=-1, random_state=SEED),
                             n_estimators=500, min_samples_leaf=10, honest=True, cv=GroupKFold(5), random_state=SEED)
        m_.fit(Y[tr], T[tr], X=X[tr], W=Wm[tr], groups=groups[tr])
        tau_oos[~tr] = m_.effect(X[~tr])
    ry, rt = cf.residuals_[0], cf.residuals_[1]
    dd = pd.DataFrame({"ry": ry, "rt": rt, "tau": tau_oos, "code": groups})
    dd["rt_tau"] = dd.rt * (dd.tau - dd.tau.mean())
    mb = smf.ols("ry ~ rt + rt_tau - 1", dd).fit(cov_type="cluster", cov_kwds={"groups": dd.code})
    blp_rows.append(dict(outcome=o, ate=float(ate.mean_point), ate_lo=float(ate.conf_int_mean()[0]), ate_hi=float(ate.conf_int_mean()[1]),
                         blp_het=mb.params["rt_tau"], blp_het_se=mb.bse["rt_tau"], blp_p=mb.pvalues["rt_tau"],
                         lin_inter=float(lin.coef_[0]), lin_lo=float(ci[0][0]), lin_hi=float(ci[1][0]),
                         lin_int=float(lin.intercept_), sd_T_within=float((d.dlmw - d.groupby("year").dlmw.transform("mean")).std())))
blp = pd.DataFrame(blp_rows)
pd.DataFrame(curve).round(5).to_csv(RES / "forest_curve.csv", index=False)

# 検出力：(A) の就業率の交互作用の標準誤差から、80%で見つけられる最小の差（MDE）
se_emp = main.query("outcome=='emp' and mod=='low_wage'").se.iloc[0]
emp_mean = E_MAIN.emp_rate.mean()
# 雇用の弾力性で表した「県の賃金の低さ1標準偏差あたりの差」：Δ就業率(%pt)/1%MW ÷ 就業率 ×100
mde = dict(se_inter_emp=float(se_emp), mde80_pt=float(2.8 * se_emp), mde80_elast=float(2.8 * se_emp / emp_mean * 100),
           emp_rate_mean=float(emp_mean))
# 3つのグループの差（低−高）で表したもの
g_emp = grp.query("outcome=='emp' and group=='低'").iloc[0]
mde.update(mde80_lowhigh_pt=float(2.8 * g_emp.se), mde80_lowhigh_elast=float(2.8 * g_emp.se / emp_mean * 100))

main.round(5).to_csv(RES / "interaction_main.csv", index=False)
grp.round(5).to_csv(RES / "tercile_diff.csv", index=False)
blp.round(5).to_csv(RES / "forest_blp.csv", index=False)
json.dump(dict(long_corr=lc, mde=mde, n_wage=len(W_MAIN), n_emp=len(E_MAIN),
               wage0_by_terc=W_MAIN.drop_duplicates("code").groupby("terc").wage0.agg(["min", "max", "mean"]).round(0).to_dict()),
          open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
pd.set_option("display.width", 200)
print(main.round(3)); print(grp.round(3)); print(blp.round(3).T); print(json.dumps(lc, indent=0)); print(mde)
