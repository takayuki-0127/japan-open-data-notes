"""F201 前編の分析。
(1) 最低賃金はどこまで届いたか：全国の影響率・未満率、県の bite（最低賃金÷短時間労働者の平均時給）
(2) 同じパネルで推定の方法を並べる：二方向固定効果（差の差）・県別トレンドつき・隣り合う県の比較・合成コントロール
(3) 違い：bite の高さ別（3分位）の時給への届き方と就業率への効き方
すべて「最低賃金10%上昇あたり」にそろえる。
"""
import json
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy.optimize import minimize
from common import DATA, RAW, RES, SEED, EXCL

rng = np.random.default_rng(SEED)
p = pd.read_csv(DATA / "panel_emp.csv")
w = pd.read_csv(DATA / "panel_wage.csv")
out = {}

# ---------------- (1) 届き方 ----------------
imp = pd.read_csv(RAW / "national_impact_rate.csv")
out["impact"] = {"2005": float(imp.loc[imp.year == 2005, "impact_rate_pct"].iloc[0]),
                 "2014": float(imp.loc[imp.year == 2014, "impact_rate_pct"].iloc[0]),
                 "2019": float(imp.loc[imp.year == 2019, "impact_rate_pct"].iloc[0]),
                 "2024": float(imp.loc[imp.year == 2024, "impact_rate_pct"].iloc[0]),
                 "under_mean": float(imp.undercoverage_rate_pct.mean()),
                 "under_min": float(imp.undercoverage_rate_pct.min()),
                 "under_max": float(imp.undercoverage_rate_pct.max())}
k = w.dropna(subset=["kaitz"]).groupby("year")["kaitz"].agg(["min", "median", "max", "mean", "std"]).reset_index()
k.to_csv(RES / "kaitz_by_year.csv", index=False)
out["kaitz"] = {str(int(r.year)): {"min": r["min"], "median": r["median"], "max": r["max"], "sd": r["std"]}
                for _, r in k.iterrows() if r.year in (2009, 2014, 2019, 2021, 2025)}
kt = w.groupby(["year", "bite_terc"])["kaitz"].mean().unstack()
kt.to_csv(RES / "kaitz_by_tercile.csv")

# 時給への届き方（パススルー）：時給の前年比 ~ 最低賃金の前年比、年の効果、県クラスター（2010〜19年。2020年は調査の変更で外す）
ww = w[(w.year >= 2010) & (w.year <= 2019)].dropna(subset=["dlw", "dlmw"]).copy()
def clus(fit_formula, df, grp):
    m = smf.ols(fit_formula, df).fit(cov_type="cluster", cov_kwds={"groups": df[grp]})
    return m
m = clus("dlw ~ dlmw + C(year)", ww, "code")
pt = {"all": [m.params["dlmw"], m.bse["dlmw"], int(m.nobs)]}
for g in ["低", "中", "高"]:
    d = ww[ww.bite_terc == g]
    mm = clus("dlw ~ dlmw + C(year)", d, "code")
    pt[g] = [mm.params["dlmw"], mm.bse["dlmw"], int(mm.nobs)]
# 交互作用でまとめて推定（年の効果あり）
ww["hi"] = (ww.bite_terc == "高").astype(int)
mi = clus("dlw ~ dlmw + dlmw:hi + hi + C(year)", ww, "code")
pt["hi_minus_rest"] = [mi.params["dlmw:hi"], mi.bse["dlmw:hi"], int(mi.nobs)]
out["passthrough"] = pt
pd.DataFrame(pt, index=["coef", "se", "n"]).T.to_csv(RES / "wage_passthrough.csv")

# ---------------- (2) 推定の方法を並べる ----------------
def main_sample(df, excl=True, y0=2008, y1=2025):
    d = df[(df.year >= y0) & (df.year <= y1)].copy()
    if excl:
        d = d[~d.year.isin(EXCL)]
    return d

rows = []
def add(method, outcome, b, se, n, note, sample):
    rows.append(dict(method=method, outcome=outcome, per10=b * np.log(1.1), lo=(b - 1.96 * se) * np.log(1.1),
                     hi=(b + 1.96 * se) * np.log(1.1), se10=se * np.log(1.1), n=n, note=note, sample=sample))

def twfe(df, y, trend=False):
    f = f"{y} ~ log_mw + C(code) + C(year)" + (" + C(code):year" if trend else "")
    return clus(f, df, "code")

for y in ["emp_rate", "unemp_rate"]:
    for excl, lab in [(True, "2008–25（2020–22除く）"), (False, "2008–25（全年）")]:
        d = main_sample(p, excl)
        m = twfe(d, y); add("差の差（二方向固定効果）", y, m.params["log_mw"], m.bse["log_mw"], int(m.nobs), "県と年の効果", lab)
        m = twfe(d, y, True); add("差の差＋県別トレンド", y, m.params["log_mw"], m.bse["log_mw"], int(m.nobs), "県ごとの直線の傾きも除く", lab)
    d = main_sample(p, True, 2008, 2019)
    m = twfe(d, y); add("差の差（二方向固定効果）", y, m.params["log_mw"], m.bse["log_mw"], int(m.nobs), "県と年の効果", "2008–19")
    m = twfe(d, y, True); add("差の差＋県別トレンド", y, m.params["log_mw"], m.bse["log_mw"], int(m.nobs), "県ごとの直線の傾きも除く", "2008–19")

# 隣り合う県の比較（ペア×年の効果：同じ年・同じ県境の両側だけで比べる）
pairs = pd.read_csv(RAW / "pref_border_pairs_from_F15.csv")
def border(df, y, pairs_):
    st = []
    for i, r in pairs_.reset_index(drop=True).iterrows():
        for c in (r.a, r.b):
            s = df[df.code == c][["code", "year", y, "log_mw"]].copy(); s["pair"] = i; st.append(s)
    s = pd.concat(st)
    s["py"] = s.pair.astype(str) + "_" + s.year.astype(str)
    s["pc"] = s.pair.astype(str) + "_" + s.code.astype(str)
    # 二重の固定効果を内側で除く（within）：ペア×年とペア×県
    for v in [y, "log_mw"]:
        s[v + "_t"] = s[v] - s.groupby("py")[v].transform("mean")
        s[v + "_t"] = s[v + "_t"] - s.groupby("pc")[v + "_t"].transform("mean")
    m = smf.ols(f"{y}_t ~ log_mw_t - 1", s).fit(cov_type="cluster", cov_kwds={"groups": s["code"]})
    return m, s
bord = {}
for y in ["emp_rate", "unemp_rate"]:
    for excl, lab in [(True, "2008–25（2020–22除く）"), (False, "2008–25（全年）")]:
        d = main_sample(p, excl)
        m, s = border(d, y, pairs)
        add("隣り合う県の比較", y, m.params["log_mw_t"], m.bse["log_mw_t"], int(m.nobs), f"{len(pairs)}組の県境、ペア×年の効果", lab)
        if y == "emp_rate" and excl:
            bord["n_pairs"] = len(pairs); bord["within_sd_logmw"] = float(s["log_mw_t"].std())
            bord["twfe_resid_sd_logmw"] = None
    d = main_sample(p, True, 2008, 2019)
    m, s = border(d, y, pairs)
    add("隣り合う県の比較", y, m.params["log_mw_t"], m.bse["log_mw_t"], int(m.nobs), f"{len(pairs)}組の県境、ペア×年の効果", "2008–19")
# 頑健性：同じ県境で市区町村ペアが5組以上ある県境だけ
pairs5 = pairs[pairs.n_muni_pairs >= 5]
m, s = border(main_sample(p, True), "emp_rate", pairs5)
add("隣り合う県の比較", "emp_rate", m.params["log_mw_t"], m.bse["log_mw_t"], int(m.nobs), f"市区町村ペア5組以上の{len(pairs5)}組", "2008–25（2020–22除く）・接する部分が長い県境")
# 使える変動の大きさ（二方向固定効果の残差）
d = main_sample(p, True)
r = smf.ols("log_mw ~ C(code) + C(year)", d).fit().resid
bord["twfe_resid_sd_logmw"] = float(r.std())
out["variation"] = bord

# 合成コントロール：2019→2025年度の上げ幅が全国より大きかった県（上位10県）を「処置」、上げ幅の小さい下位20県を「候補」
mw = pd.read_csv(RAW / "minimum_wage_2002_2026.csv")
mw = mw.merge(p[["pref", "code"]].drop_duplicates(), on="pref")
mw["rise"] = np.log(mw["2025"]) - np.log(mw["2019"])
mw = mw.sort_values("rise", ascending=False).reset_index(drop=True)
def synth(df, y, treated, donors, pre_years, post_years):
    Y = df.pivot(index="year", columns="code", values=y)
    X0 = Y.loc[pre_years, donors].values; att = []; wts = {}
    for c in treated:
        x1 = Y.loc[pre_years, c].values
        n = len(donors)
        obj = lambda v: np.sum((x1 - X0 @ v) ** 2)
        cons = ({"type": "eq", "fun": lambda v: v.sum() - 1},)
        res = minimize(obj, np.ones(n) / n, bounds=[(0, 1)] * n, constraints=cons, method="SLSQP", options={"maxiter": 500})
        v = res.x
        gap = Y.loc[:, c].values - Y.loc[:, donors].values @ v
        pre_rmse = np.sqrt(np.mean((gap[np.isin(Y.index, pre_years)]) ** 2))
        att.append(dict(code=c, pre_rmse=pre_rmse, post_gap=float(np.mean(gap[np.isin(Y.index, post_years)])),
                        gaps=dict(zip(Y.index.astype(int), gap))))
        wts[c] = v
    return att, wts
def dose(treated, donors, wts):
    # 処置県の上げ幅 − 合成県の上げ幅（合成の重みで平均）
    rise = mw.set_index("code")["rise"]
    return float(np.mean([rise[c] - rise[donors].values @ wts[c] for c in treated]))
pre = list(range(2008, 2020)); post = [2023, 2024, 2025]
sc = {}
for y in ["emp_rate", "unemp_rate"]:
    for ntr, nd, lab in [(10, 20, "上位10県 vs 下位20県"), (5, 20, "上位5県 vs 下位20県"), (10, 30, "上位10県 vs 下位30県")]:
        treated = mw.code[:ntr].tolist(); donors = mw.code[-nd:].tolist()
        att, wts = synth(p, y, treated, donors, pre, post)
        good = [a for a in att]
        eff = np.mean([a["post_gap"] for a in good]); ds = dose(treated, donors, wts)
        # 並べ替え（候補の県を1つずつ「処置」にしたときの差）：上位と同じ数を無作為に選び500回
        plac = []
        if lab == "上位10県 vs 下位20県":
            pool = mw.code[ntr:].tolist()
            for _ in range(200):
                pt_ = rng.choice(pool, ntr, replace=False).tolist(); dn = [c for c in pool if c not in pt_]
                dn = rng.choice(dn, nd, replace=False).tolist()
                a2, w2 = synth(p, y, pt_, dn, pre, post)
                plac.append(np.mean([a["post_gap"] for a in a2]))
            plac = np.array(plac)
            pval = float(np.mean(np.abs(plac) >= abs(eff)))
            pd.DataFrame({"placebo_gap": plac}).to_csv(RES / f"synth_placebo_{y}.csv", index=False)
            se_pl = float(plac.std())
            if y == "emp_rate":
                g = pd.DataFrame({a["code"]: a["gaps"] for a in att}); g.index.name = "year"; g.to_csv(RES / "synth_gaps_emp.csv")
                pd.DataFrame({"code": treated, "pre_rmse": [a["pre_rmse"] for a in att], "post_gap": [a["post_gap"] for a in att]}).to_csv(RES / "synth_treated.csv", index=False)
        else:
            pval = None; se_pl = None
        sc[(y, lab)] = dict(att=eff, dose=ds, per10=eff / ds * np.log(1.1), p_perm=pval, se_perm=se_pl,
                            pre_rmse=float(np.mean([a["pre_rmse"] for a in att])), treated=treated)
        if se_pl is not None:
            add("合成コントロール", y, eff / ds, se_pl / ds, ntr * len(p.year.unique()), f"{lab}、並べ替え200回", "前2008–19・後2023–25")
        else:
            rows.append(dict(method="合成コントロール", outcome=y, per10=eff / ds * np.log(1.1), lo=np.nan, hi=np.nan, se10=np.nan,
                             n=ntr, note=lab, sample="前2008–19・後2023–25"))
out["synth"] = {f"{k[0]}|{k[1]}": {kk: (vv if not isinstance(vv, (np.floating,)) else float(vv)) for kk, vv in v.items()} for k, v in sc.items()}
out["synth_treated_prefs_top10"] = mw.pref[:10].tolist()
out["synth_rise_top10_mean"] = float(mw.rise[:10].mean()); out["synth_rise_bottom20_mean"] = float(mw.rise[-20:].mean())

# ---------------- (3) bite の高さ別の就業率への効き方 ----------------
d = main_sample(p, True).copy()
het = {}
for g in ["低", "中", "高"]:
    d[f"lmw_{g}"] = d.log_mw * (d.bite_terc == g)
for y in ["emp_rate", "unemp_rate"]:
    m = clus(f"{y} ~ lmw_低 + lmw_中 + lmw_高 + C(code) + C(year)", d, "code")
    het[y] = {g: [m.params[f"lmw_{g}"] * np.log(1.1), m.bse[f"lmw_{g}"] * np.log(1.1)] for g in ["低", "中", "高"]}
    # 高 − 低 の差
    cv = m.cov_params(); dif = m.params["lmw_高"] - m.params["lmw_低"]
    sdd = np.sqrt(cv.loc["lmw_高", "lmw_高"] + cv.loc["lmw_低", "lmw_低"] - 2 * cv.loc["lmw_高", "lmw_低"])
    het[y]["高−低"] = [dif * np.log(1.1), sdd * np.log(1.1)]
out["het_emp"] = het
pd.DataFrame([dict(outcome=y, group=g, per10=v[0], se10=v[1]) for y in het for g, v in het[y].items()]).to_csv(RES / "heterogeneity_bite.csv", index=False)

tab = pd.DataFrame(rows)
tab.to_csv(RES / "method_comparison.csv", index=False)
# 検出力：主な指定の標準誤差から、80%で見つけられる最小の差（10%あたり、%pt）
mde = tab[(tab.outcome == "emp_rate") & (tab["sample"] == "2008–25（2020–22除く）")][["method", "note", "se10"]].copy()
mde["mde80"] = 2.8 * mde.se10
mde.to_csv(RES / "mde.csv", index=False)
out["mde"] = mde.to_dict("records")
out["method_table_main"] = tab[(tab["sample"].isin(["2008–25（2020–22除く）", "前2008–19・後2023–25"]))].to_dict("records")

# ---------------- 後編（F202）に渡す数字 ----------------
emp = tab[(tab.outcome == "emp_rate")]
out["for_F202"] = {
    "emp_per10_range_main": [float(emp.per10.min()), float(emp.per10.max())],
    "emp_per10_lo95_min": float(emp.lo.min()), "emp_per10_hi95_max": float(emp.hi.max()),
    "kaitz_2025_by_pref": w[w.year == 2025].set_index("code")["kaitz"].round(4).to_dict(),
    "passthrough_all": pt["all"][:2],
    "note": "シナリオ計算（全国一律など）では、就業率の弾力性を per10 の幅（方法の違い）と95%区間の両端で振る。時給へのパススルーは passthrough を使う。"
}
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(tab.round(3).to_string())
print(json.dumps({k: out[k] for k in ["impact", "passthrough", "variation", "het_emp"]}, ensure_ascii=False, default=float, indent=0)[:3000])
for k, v in sc.items():
    print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "treated"})
print(out["synth_treated_prefs_top10"], out["synth_rise_top10_mean"], out["synth_rise_bottom20_mean"])
