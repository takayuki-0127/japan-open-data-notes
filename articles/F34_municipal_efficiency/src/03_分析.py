"""03 分析：人口規模の5グループごとに DEA（CCR・BCC・スーパー効率）、全体で SFA（費用フロンティア）を推定し、
2つの手法の順位の一致、効率と地理条件の関係（2段階目）、出力・入力・年を変えた頑健性を調べる。
市区町村ごとの効率値（results/_eff_by_municipality.csv）は、個別の順位表として公開しないため GitHub には置かない。"""
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr, kendalltau
from common import DATA, RES, GLAB, dea_input, sfa_cost

log = open(RES / "run_log_03.txt", "w", encoding="utf-8")


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s); log.write(s + "\n")


m = pd.read_csv(DATA / "municipal_2022.csv", dtype={"code": str})
n0 = len(m)
m = m[m["pop"] > 0].reset_index(drop=True)   # 2020年に人口0の町（原発事故の避難指示区域）を除く
p(f"対象：{len(m)} 市区町村（人口0の {n0 - len(m)} を除く）")

SPECS = {
    "基本":                 dict(inp=["spend"], out=["pop", "pop65", "pupils", "nursery", "habitable_ha"]),
    "需要だけ":             dict(inp=["spend"], out=["pop", "pop65", "pop14", "habitable_ha"]),
    "施設を足す":           dict(inp=["spend"], out=["pop", "pop65", "pupils", "nursery", "habitable_ha", "library", "kominkan"]),
    "入力＝職員数":         dict(inp=["staff"], out=["pop", "pop65", "pupils", "nursery", "habitable_ha"]),
    "入力＝歳出と職員数":   dict(inp=["spend", "staff"], out=["pop", "pop65", "pupils", "nursery", "habitable_ha"]),
    "災害復旧費を含む":     dict(inp=["spend_all"], out=["pop", "pop65", "pupils", "nursery", "habitable_ha"]),
}


def run_dea(d, spec, super_eff=False):
    crs = pd.Series(np.nan, index=d.index); vrs = crs.copy(); sup = crs.copy()
    for g in GLAB:
        ix = d.index[d.group == g]
        X, Y = d.loc[ix, spec["inp"]].values, d.loc[ix, spec["out"]].values
        crs[ix] = dea_input(X, Y, vrs=False)
        vrs[ix] = dea_input(X, Y, vrs=True)
        if super_eff:
            sup[ix] = dea_input(X, Y, vrs=False, super_eff=True)
    return crs, vrs, sup


# ---------- DEA（基本） ----------
crs, vrs, sup = run_dea(m, SPECS["基本"], super_eff=True)
m["dea_crs"], m["dea_vrs"], m["dea_super"] = crs, vrs, sup
m["scale_eff"] = m.dea_crs / m.dea_vrs

# ---------- SFA（費用フロンティア、全体で1本） ----------
def sfa_design(d, out, inp="spend"):
    X = pd.DataFrame({"const": 1.0}, index=d.index)
    for c in out:
        X["ln_" + c] = np.log(d[c] + 1)
    X["ln_pop2"] = np.log(d["pop"]) ** 2 / 2
    return np.log(d[inp]), X


yv, Xv = sfa_design(m, SPECS["基本"]["out"])
sf = sfa_cost(yv, Xv, names=Xv.columns)
m["sfa"] = sf["eff"]
p("\n[SFA 費用フロンティア] λ=σu/σv =", round(sf["lambda"], 2), " σu =", round(sf["sigma_u"], 3),
  " σv =", round(sf["sigma_v"], 3), " 対数尤度 =", round(sf["loglik"], 1), " 収束", sf["converged"])
p(pd.DataFrame({"係数": sf["beta"], "SE": sf["se"]}).round(3).to_string())
pd.DataFrame({"coef": sf["beta"], "se": sf["se"]}).to_csv(RES / "sfa_coefficients.csv", encoding="utf-8")
# OLS 残差の歪度（費用関数なら正の歪み＝非効率の存在）
ols = sm.OLS(yv, Xv).fit()
from scipy.stats import skew
p("OLS 残差の歪度：", round(skew(ols.resid), 3), "（正なら費用フロンティアの形と合う）")

# ---------- グループ別の要約 ----------
rows = []
for g in GLAB:
    d = m[m.group == g]
    rows.append({"group": g, "n": len(d),
                 "spend_per_capita_median_kyen": (d.spend / d["pop"] * 1000).median(),
                 "dea_vrs_median": d.dea_vrs.median(), "dea_vrs_q25": d.dea_vrs.quantile(.25), "dea_vrs_q75": d.dea_vrs.quantile(.75),
                 "dea_vrs_share_eff": (d.dea_vrs > 0.9999).mean(),
                 "dea_crs_median": d.dea_crs.median(), "dea_crs_share_eff": (d.dea_crs > 0.9999).mean(),
                 "scale_eff_median": d.scale_eff.median(),
                 "sfa_median": d.sfa.median(), "sfa_q25": d.sfa.quantile(.25), "sfa_q75": d.sfa.quantile(.75),
                 "spearman_dea_sfa": spearmanr(d.dea_vrs, d.sfa).correlation,
                 "kendall_dea_sfa": kendalltau(d.dea_vrs, d.sfa).correlation})
grp = pd.DataFrame(rows)
grp.to_csv(RES / "by_group.csv", index=False, encoding="utf-8")
p("\n[グループ別]\n" + grp.round(3).to_string())
p("全体：DEA(BCC) と SFA の順位相関（グループ内の順位で）",
  round(spearmanr(m.groupby("group").dea_vrs.rank(pct=True), m.groupby("group").sfa.rank(pct=True)).correlation, 3))

# 上位・下位25%の一致（グループ内）
def quart_agree(a, b):
    qa = a.groupby(m.group).rank(pct=True); qb = b.groupby(m.group).rank(pct=True)
    top = ((qa > .75) & (qb > .75)).sum() / (qa > .75).sum()
    bot = ((qa <= .25) & (qb <= .25)).sum() / (qa <= .25).sum()
    return top, bot


t, b_ = quart_agree(m.dea_vrs, m.sfa)
p(f"グループ内の上位25%のうち、もう一方の手法でも上位25%：{t:.1%}／下位25%どうし：{b_:.1%}")

# スーパー効率：フロンティアを作っている町（効率1）の中での差
fr = m[m.dea_crs > 0.9999]
p(f"\n[スーパー効率] CCR で効率1の町 {len(fr)}、スーパー効率の中央値 {fr.dea_super.median():.2f}、"
  f"2を超える町 {int((fr.dea_super > 2).sum())}、解なし {int(fr.dea_super.isna().sum())}")

# ---------- 2段階目：効率と地理・財政の条件 ----------
def stage2(yname):
    d = m.dropna(subset=["zaiseiryoku", "keijo"]).copy()
    X = pd.DataFrame({"ln_density": np.log(d.density), "aged": d.aged, "zaiseiryoku": d.zaiseiryoku,
                      "keijo": d.keijo}, index=d.index)
    X = (X - X.mean()) / X.std()                       # 1標準偏差あたり
    X = pd.concat([X, pd.get_dummies(d.group, drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)
    r = sm.OLS(d[yname] * 100, X).fit(cov_type="HC1")
    return r, len(d)


s2 = []
for y in ["dea_vrs", "dea_crs", "sfa"]:
    r, n = stage2(y)
    for k in ["ln_density", "aged", "zaiseiryoku", "keijo"]:
        s2.append({"outcome": y, "var": k, "coef_pt_per_sd": r.params[k], "lo": r.conf_int().loc[k, 0],
                   "hi": r.conf_int().loc[k, 1], "n": n, "r2": r.rsquared})
s2 = pd.DataFrame(s2)
s2.to_csv(RES / "stage2.csv", index=False, encoding="utf-8")
p("\n[2段階目（効率×100 を1標準偏差あたり、規模グループの違いを除く、東京23区は財政力指数がないので除外）]\n" + s2.round(2).to_string())

# ---------- 頑健性：出力・入力の組み合わせ ----------
rob = {"基本": m.dea_vrs}
for name, spec in SPECS.items():
    if name == "基本":
        continue
    _, v, _ = run_dea(m, spec)
    rob[name] = v
# 外れ値（スーパー効率が上位5%）を除いてフロンティアを作り直す
cut = m.dea_super.quantile(.95)
keep = m.index[~(m.dea_super > cut)]
v2 = pd.Series(np.nan, index=m.index)
for g in GLAB:
    ix = keep[m.loc[keep, "group"] == g]
    v2[ix] = dea_input(m.loc[ix, ["spend"]].values, m.loc[ix, SPECS["基本"]["out"]].values, vrs=True)
rob["外れ値を除く"] = v2
# 東京23区を除く
ix = m.index[~m.tokyo23]
v3 = pd.Series(np.nan, index=m.index)
for g in GLAB:
    jx = ix[m.loc[ix, "group"] == g]
    v3[jx] = dea_input(m.loc[jx, ["spend"]].values, m.loc[jx, SPECS["基本"]["out"]].values, vrs=True)
rob["東京23区を除く"] = v3
R = pd.DataFrame(rob)
gr = R.groupby(m.group).rank(pct=True)
rc = []
for c in R.columns:
    ok = R[c].notna() & R["基本"].notna()
    q_base = gr.loc[ok, "基本"]; q_c = gr.loc[ok, c]
    rc.append({"spec": c, "n": int(ok.sum()), "spearman_with_base": spearmanr(R.loc[ok, "基本"].groupby(m.group[ok]).rank(pct=True),
                                                                             R.loc[ok, c].groupby(m.group[ok]).rank(pct=True)).correlation,
               "median_eff": R[c].median(), "share_eff": (R[c] > 0.9999).mean(),
               "top25_kept": ((q_base > .75) & (q_c > .75)).sum() / (q_base > .75).sum(),
               "median_abs_rank_change_pct": (q_base - q_c).abs().median() * 100})
rc = pd.DataFrame(rc)
p("\n[頑健性：出力・入力の組み合わせ（グループ内の順位の相関）]\n" + rc.round(3).to_string())

# SFA の設定を変える（出力を需要だけ・グループのダミーを入れる）
yv2, Xv2 = sfa_design(m, SPECS["需要だけ"]["out"])
sf2 = sfa_cost(yv2, Xv2, names=Xv2.columns)
Xg = pd.concat([Xv, pd.get_dummies(m.group, drop_first=True, dtype=float)], axis=1)
sf3 = sfa_cost(yv, Xg, names=Xg.columns)
for nm, s in [("SFA 需要だけ", sf2), ("SFA 規模ダミー", sf3)]:
    rc = pd.concat([rc, pd.DataFrame([{"spec": nm, "n": len(m),
                                       "spearman_with_base": spearmanr(s["eff"], m.sfa).correlation,
                                       "median_eff": np.median(s["eff"]), "share_eff": np.nan,
                                       "top25_kept": np.nan, "median_abs_rank_change_pct": np.nan}])])
    p(f"{nm}：基本の SFA との順位相関 {spearmanr(s['eff'], m.sfa).correlation:.3f}、λ={s['lambda']:.2f}")

# ---------- 頑健性：年を変える（2015年、需要だけの出力） ----------
q = pd.read_csv(DATA / "municipal_2015.csv", dtype={"code": str})
q = q[q.code.isin(m.code) & (q["pop"] > 0)].dropna(subset=["spend_all", "pop", "pop65", "pop14", "habitable_ha"]).reset_index(drop=True)
v15 = pd.Series(np.nan, index=q.index)
for g in GLAB:
    ix = q.index[q.group == g]
    v15[ix] = dea_input(q.loc[ix, ["spend_all"]].values, q.loc[ix, ["pop", "pop65", "pop14", "habitable_ha"]].values, vrs=True)
q["dea15"] = v15
mm = m[["code", "group"]].assign(dea22=R["災害復旧費を含む"] if False else np.nan)
# 2022年も「災害復旧費を含む歳出 × 需要だけの出力」で同じ形にそろえて比べる
_, v22, _ = run_dea(m, dict(inp=["spend_all"], out=["pop", "pop65", "pop14", "habitable_ha"]))
mm["dea22"] = v22
yy = mm.merge(q[["code", "dea15", "group"]].rename(columns={"group": "group15"}), on="code")
yy = yy[yy.group == yy.group15]          # 2015年と2020年で規模グループが同じ町だけ
yy["r22"] = yy.groupby("group").dea22.rank(pct=True); yy["r15"] = yy.groupby("group").dea15.rank(pct=True)
rho = spearmanr(yy.r22, yy.r15).correlation
t25 = ((yy.r22 > .75) & (yy.r15 > .75)).sum() / (yy.r15 > .75).sum()
rc = pd.concat([rc, pd.DataFrame([{"spec": "2015年（需要だけ、災害復旧費を含む）vs 2022年（同じ形）", "n": len(yy),
                                   "spearman_with_base": rho, "median_eff": yy.dea15.median(),
                                   "share_eff": (yy.dea15 > 0.9999).mean(), "top25_kept": t25,
                                   "median_abs_rank_change_pct": (yy.r22 - yy.r15).abs().median() * 100}])])
p(f"\n[年を変える] 2015年と2022年（同じ形の DEA）のグループ内順位の相関 {rho:.3f}（{len(yy)} 市区町村）、2015年の上位25%が2022年も上位25%：{t25:.1%}")
yy.to_csv(RES / "_year_compare.csv", index=False, encoding="utf-8")
rc.to_csv(RES / "robustness.csv", index=False, encoding="utf-8")

# 順位の相関（図5用）
corr = gr.corr(method="spearman")
corr.to_csv(RES / "robustness_rank_corr.csv", encoding="utf-8")

# ---------- 効率値（町ごと。GitHub には置かない） ----------
m.to_csv(RES / "_eff_by_municipality.csv", index=False, encoding="utf-8")
R.assign(code=m.code, group=m.group).to_csv(RES / "_robustness_by_municipality.csv", index=False, encoding="utf-8")

# 効率値の分布（公開用：町名なし、グループ別の分位点）
qs = m.groupby("group")[["dea_crs", "dea_vrs", "scale_eff", "sfa"]].quantile([.1, .25, .5, .75, .9]).unstack()
qs.to_csv(RES / "efficiency_quantiles_by_group.csv", encoding="utf-8")
log.close()
