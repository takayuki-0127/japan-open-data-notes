"""03 分析：料率の水準 R・保険金の水準 C・長期の損害率 L を都道府県ごとに出し、H1〜H4 と頑健性を確かめる。
主な期間は全契約の集計がそろう 2017〜2024年度（8年）。"""
import json, pathlib
import numpy as np, pandas as pd
from scipy import stats
B = pathlib.Path(__file__).resolve().parents[1]
df = pd.read_csv(B / "data" / "processed" / "fire_pref_fy2014_2024.csv")
PREF = [p for p in df.pref.unique() if p not in ("分類不能", "合計")]
assert len(PREF) == 47
d = df[df.pref.isin(PREF)].copy()
d["prem"] = d.prem_k * 1e3; d["claim"] = d.claim_k * 1e3; d["amt"] = d.amount_mil * 1e6
MAIN = list(range(2017, 2025))
(B / "results").mkdir(exist_ok=True)
rng = np.random.default_rng(272)

def levels(sub, per="amount"):
    g = sub.groupby("pref")[["prem", "claim", "amt", "n_new"]].sum().loc[PREF]
    den = g.amt / 1e3 if per == "amount" else g.n_new   # 保険金額1,000円あたり or 1件あたり
    return pd.DataFrame({"R": g.prem / den, "C": g.claim / den, "L": g.claim / g.prem, "prem": g.prem})

def slope(x, y, w=None, nboot=4000):
    X = np.column_stack([np.ones_like(x), x])
    W = np.ones_like(x) if w is None else w / w.mean()
    beta = np.linalg.solve(X.T @ (W[:, None] * X), X.T @ (W * y))
    res = y - X @ beta; n = len(x)
    s2 = (W * res ** 2).sum() / (n - 2)
    cov = s2 * np.linalg.inv(X.T @ (W[:, None] * X))
    se = np.sqrt(cov[1, 1]); t = stats.t.ppf(0.975, n - 2)
    bs = []
    for _ in range(nboot):
        i = rng.integers(0, n, n)
        Xi = X[i]; Wi = W[i]
        try: bs.append(np.linalg.solve(Xi.T @ (Wi[:, None] * Xi), Xi.T @ (Wi * y[i]))[1])
        except np.linalg.LinAlgError: pass
    lo, hi = np.percentile(bs, [2.5, 97.5])
    r2 = 1 - (W * res ** 2).sum() / (W * (y - np.average(y, weights=W)) ** 2).sum()
    return dict(b=float(beta[1]), ci_lo=float(beta[1] - t * se), ci_hi=float(beta[1] + t * se), boot_lo=float(lo), boot_hi=float(hi), r2=float(r2))

def h12(lv, w=None):
    rho = stats.spearmanr(lv.R, lv.C)
    pr = stats.pearsonr(np.log(lv.R), np.log(lv.C))
    s = slope(np.log(lv.C.values), np.log(lv.R.values), None if w is None else lv.prem.values)
    return dict(spearman=float(rho.statistic), spearman_p=float(rho.pvalue), pearson_log=float(pr.statistic), **{"slope_" + k: v for k, v in s.items()},
                sd_logR=float(np.log(lv.R).std(ddof=1)), sd_logC=float(np.log(lv.C).std(ddof=1)), sd_logL=float(np.log(lv.L).std(ddof=1)),
                ratio_maxmin_R=float(lv.R.max() / lv.R.min()), ratio_maxmin_C=float(lv.C.max() / lv.C.min()), ratio_maxmin_L=float(lv.L.max() / lv.L.min()))

R = {}
m = d[d.fy.isin(MAIN)]
lv = levels(m); lv.to_csv(B / "results" / "A_levels_fy2017_2024.csv", float_format="%.6g")
R["main"] = h12(lv)
R["main"]["national_L"] = float(m.claim.sum() / m.prem.sum())
R["main"]["L_iqr"] = [float(x) for x in lv.L.quantile([0.25, 0.5, 0.75])]
R["main"]["L_range"] = [float(lv.L.min()), float(lv.L.max())]
R["H1"] = dict(value=R["main"]["spearman"], verdict="支持" if R["main"]["spearman"] >= 0.5 else "外れ")
R["H2"] = dict(value=R["main"]["slope_b"], ci=[R["main"]["slope_ci_lo"], R["main"]["slope_ci_hi"]],
               verdict="支持" if (R["main"]["slope_b"] > 0 and R["main"]["slope_ci_hi"] < 1) else "外れ")

# H3：各都道府県の支払保険金が最大の1年を除く
yr = m.groupby(["pref", "fy"])[["prem", "claim", "amt"]].sum().reset_index()
top = yr.loc[yr.groupby("pref").claim.idxmax(), ["pref", "fy"]]
R["H3_top_year_counts"] = {int(k): int(v) for k, v in top.fy.value_counts().sort_index().items()}
m3 = m.merge(top.assign(drop=1), on=["pref", "fy"], how="left")
lv3 = levels(m3[m3["drop"].isna()])
sd_all, sd_drop = R["main"]["sd_logL"], float(np.log(lv3.L).std(ddof=1))
R["H3"] = dict(sd_logL_all=sd_all, sd_logL_drop=sd_drop, reduction=1 - sd_drop / sd_all,
               verdict="支持" if 1 - sd_drop / sd_all >= 1 / 3 else "外れ",
               spearman_RC_drop=float(stats.spearmanr(lv3.R, lv3.C).statistic))
lv3.to_csv(B / "results" / "B_levels_drop_top_year.csv", float_format="%.6g")
# 単年の損害率の散らばり（参考）
yr["L"] = yr.claim / yr.prem
R["single_year_sd_logL"] = {int(f): float(np.log(g.L).std(ddof=1)) for f, g in yr.groupby("fy")}

# H4：前半の損害率と、その後の料率の相対水準の変化
def rel(sub):
    g = sub.groupby("pref")[["prem", "amt"]].sum().loc[PREF]; r = g.prem / g.amt
    tot = sub.prem.sum() / sub.amt.sum(); return r / tot
E, Lt = [2017, 2018, 2019], [2022, 2023, 2024]
lvE = levels(m[m.fy.isin(E)])
dR = np.log(rel(m[m.fy.isin(Lt)]) / rel(m[m.fy.isin(E)]))
h4 = stats.spearmanr(lvE.L, dR)
# 機械的な相関を避ける：前半の保険金の水準を、後半の料率で割った損害率でも見る
lvL = levels(m[m.fy.isin(Lt)])
alt = stats.spearmanr(lvE.C / lvL.R, dR)
alt2 = stats.spearmanr(lvE.C / lvE.C.mean() , dR)
R["H4"] = dict(spearman=float(h4.statistic), p=float(h4.pvalue), verdict="支持" if h4.statistic >= 0.3 else "外れ",
               spearman_C_over_Rlate=float(alt.statistic), spearman_C_only=float(alt2.statistic),
               dR_sd=float(dR.std(ddof=1)), dR_range=[float(dR.min()), float(dR.max())],
               national_R_change=float(np.log((m[m.fy.isin(Lt)].prem.sum() / m[m.fy.isin(Lt)].amt.sum()) / (m[m.fy.isin(E)].prem.sum() / m[m.fy.isin(E)].amt.sum()))))
pd.DataFrame({"L_2017_19": lvE.L, "dlogRrel_1719_2224": dR}).to_csv(B / "results" / "C_H4.csv", float_format="%.6g")

# 頑健性
rob = {}
rob["per_contract"] = h12(levels(m, per="contract"))
rob["first_half_2017_2020"] = h12(levels(m[m.fy.isin([2017, 2018, 2019, 2020])]))
rob["second_half_2021_2024"] = h12(levels(m[m.fy.isin([2021, 2022, 2023, 2024])]))
nat = m.groupby("fy").claim.sum().sort_values(ascending=False)
top2 = [int(x) for x in nat.index[:2]]
rob["drop_top2_national_years"] = dict(years=top2, **h12(levels(m[~m.fy.isin(top2)])))
rob["weighted_by_premium"] = h12(lv, w=True)
rob["one_year_contracts_2014_2016"] = h12(levels(d[d.fy.isin([2014, 2015, 2016])]))
R["robust"] = rob
R["national_by_fy"] = {int(f): dict(L=float(g.claim.sum() / g.prem.sum()), R=float(g.prem.sum() / g.amt.sum() * 1e3), claim_oku=float(g.claim.sum() / 1e8))
                       for f, g in d.groupby("fy")}
json.dump(R, open(B / "results" / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: R[k] for k in ["main", "H1", "H2", "H3", "H4", "H3_top_year_counts"]}, ensure_ascii=False, indent=1))
for k, v in rob.items(): print(k, {a: round(b, 3) if isinstance(b, float) else b for a, b in v.items() if a in ("spearman", "pearson_log", "slope_b", "slope_ci_lo", "slope_ci_hi", "sd_logL", "years")})

# 問い直し（結果を見てから追加）：8年の実績の保険金は、リスクのものさしとしてどれだけ揺れるか
import itertools
yrs = MAIN; rs = []; rRs = []
for half in itertools.combinations(yrs, 4):
    if 2017 not in half: continue          # 同じ分け方を2回数えない（35通り）
    a = levels(m[m.fy.isin(half)]); b = levels(m[~m.fy.isin(half)])
    rs.append(stats.pearsonr(np.log(a.C), np.log(b.C)).statistic)
    rRs.append(stats.pearsonr(np.log(a.R), np.log(b.R)).statistic)
r_half = float(np.median(rs)); rel = 2 * r_half / (1 + r_half)
relR = 2 * float(np.median(rRs)) / (1 + float(np.median(rRs)))
r_obs = R["main"]["pearson_log"]
rq = dict(n_splits=len(rs), split_half_r_C=r_half, split_half_r_C_range=[float(min(rs)), float(max(rs))], reliability_C_8yr=rel,
          split_half_r_R=float(np.median(rRs)), reliability_R_8yr=relR,
          corr_observed=r_obs, corr_corrected=float(r_obs / np.sqrt(rel * relR)),
          slope_observed=R["main"]["slope_b"], slope_corrected=float(R["main"]["slope_b"] / rel))
# 何年あれば信頼性0.8に届くか（Spearman-Brown、1年あたりの信頼性から）
r1 = r_half / (4 - 3 * r_half)            # 4年の相関から1年あたりへ
rq["reliability_1yr"] = float(r1)
rq["years_for_rel_0_8"] = float(0.8 * (1 - r1) / (r1 * (1 - 0.8)))
# 大きな2年（2018・2019）を除いた6年で同じこと
yrs6 = [y for y in yrs if y not in top2]; rs6 = []
for half in itertools.combinations(yrs6, 3):
    if yrs6[0] not in half: continue
    a = levels(m[m.fy.isin(half)]); b = levels(m[m.fy.isin([y for y in yrs6 if y not in half])])
    rs6.append(stats.pearsonr(np.log(a.C), np.log(b.C)).statistic)
rq["split_half_r_C_excl_top2"] = float(np.median(rs6)); rq["reliability_C_6yr_excl_top2"] = float(2 * np.median(rs6) / (1 + np.median(rs6)))
R["reask"] = rq
json.dump(R, open(B / "results" / "main.json", "w"), ensure_ascii=False, indent=1)
print("reask", json.dumps(rq, ensure_ascii=False, indent=1))

# 独立レビューを受けて足した確かめ（結果のあと）
rv = {}
# (1) 補正した傾きの幅：折半の相関の幅・都道府県の再標本化・逆回帰の上限・6年分での補正
def rel_from(r): return 2 * r / (1 + r)
def yrs08(r):
    r1 = r / (4 - 3 * r); return 0.8 * (1 - r1) / (r1 * 0.2)
rlo, rhi = min(rs), max(rs)
rv["corrected_slope_split_range"] = [float(R["main"]["slope_b"] / rel_from(rhi)), float(R["main"]["slope_b"] / rel_from(rlo))]
rv["years_for_0_8_split_range"] = [float(yrs08(rhi)), float(yrs08(rlo))]
# 都道府県の再標本化（300回）：毎回、傾きと信頼性（35通りの折半の中央値）を計算し直す
yrp = m.groupby(["pref", "fy"])[["prem", "claim", "amt"]].sum()
halves = [h for h in itertools.combinations(yrs, 4) if 2017 in h]
def lvl(ix, years):
    g = yrp.loc[(ix, list(years)), :].groupby(level="pref").sum().reindex(ix)
    return np.log(g.prem / g.amt), np.log(g.claim / g.amt)
cs = []
for b in range(300):
    ix = list(rng.choice(PREF, len(PREF), replace=True))
    ixu = sorted(set(ix))
    lr, lc = lvl(ixu, yrs); lr = lr.loc[ix].values; lc = lc.loc[ix].values
    bb = np.polyfit(lc, lr, 1)[0]
    rr = []
    for h in halves:
        _, ca = lvl(ixu, h); _, cb = lvl(ixu, [y for y in yrs if y not in h])
        rr.append(np.corrcoef(ca.loc[ix].values, cb.loc[ix].values)[0, 1])
    cs.append(bb / rel_from(np.median(rr)))
rv["corrected_slope_boot95"] = [float(np.percentile(cs, 2.5)), float(np.percentile(cs, 97.5))]
lr, lc = np.log(lv.R.values), np.log(lv.C.values)
rv["reverse_regression_upper"] = float(np.var(lr, ddof=1) / np.cov(lr, lc)[0, 1])
rv["corrected_slope_6yr"] = float(rob["drop_top2_national_years"]["slope_b"] / rq["reliability_C_6yr_excl_top2"])
# (2) 料率の水準には保険期間の構成が入る：全国の R（1,000円あたり）
rv["national_R"] = {int(k): v["R"] for k, v in R["national_by_fy"].items()}
# H4 を 2022年10月の長期契約の見直しより前で終わる窓で確かめる
def rel_lvl(sub):
    g = sub.groupby("pref")[["prem", "amt"]].sum().loc[PREF]; return (g.prem / g.amt) / (sub.prem.sum() / sub.amt.sum())
for nm, Lt2 in [("2020_2021", [2020, 2021]), ("2020_2022", [2020, 2021, 2022])]:
    dR2 = np.log(rel_lvl(m[m.fy.isin(Lt2)]) / rel_lvl(m[m.fy.isin(E)]))
    rv["H4_window_" + nm] = dict(spearman=float(stats.spearmanr(lvE.L, dR2).statistic), p=float(stats.spearmanr(lvE.L, dR2).pvalue),
                                 spearman_C_over_Rlate=float(stats.spearmanr(lvE.C / levels(m[m.fy.isin(Lt2)]).R, dR2).statistic))
# (7) 料率の全国比の変化を比で
rv["dR_ratio_range"] = [float(np.exp(dR.min()) - 1), float(np.exp(dR.max()) - 1)]
# 6年の補正値の材料
rv["slope_6yr"] = float(rob["drop_top2_national_years"]["slope_b"]); rv["reliability_6yr"] = rq["reliability_C_6yr_excl_top2"]
R["review"] = rv
json.dump(R, open(B / "results" / "main.json", "w"), ensure_ascii=False, indent=1)
print("review", json.dumps(rv, ensure_ascii=False, indent=1))
