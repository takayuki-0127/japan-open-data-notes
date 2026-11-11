"""分析：解約率の見え方、Kaplan–Meier、Cox、コホートの定着率表、LTV と外挿の仕方、頑健性。"""
import pandas as pd, numpy as np, json, pathlib, warnings
from lifelines import KaplanMeierFitter, CoxPHFitter, WeibullFitter, LogNormalFitter, ExponentialFitter
from lifelines.statistics import multivariate_logrank_test, proportional_hazard_test
from scipy.optimize import minimize
from scipy.special import betaln
warnings.filterwarnings("ignore")
B = pathlib.Path(__file__).resolve().parents[1]; R = B / "results"; R.mkdir(exist_ok=True)
rng = np.random.default_rng(241)
t = pd.read_csv(B / "data/telco_clean.csv")
t["d"] = t["duration"].clip(lower=0.5)       # 0か月（入ったばかり）は0.5か月として扱う
out = {}

# --- A. 見かけの解約率と KM ---
out["n"] = len(t); out["naive_churn_share"] = t.event.mean()
km = KaplanMeierFitter().fit(t.d, t.event)
S = lambda m: float(km.survival_function_at_times(m).iloc[0])
out["km_S"] = {m: S(m) for m in [1, 3, 6, 12, 24, 36, 48, 60, 72]}
# 月ごとの解約の起こりやすさ（ハザード）：生命表
lt = []
for m in range(1, 73):
    risk = (t.duration >= m).sum(); ev = ((t.duration == m) & (t.event == 1)).sum()
    lt.append((m, risk, ev, ev / risk if risk else np.nan))
lt = pd.DataFrame(lt, columns=["month", "at_risk", "events", "hazard"]); lt.to_csv(R / "A_life_table.csv", index=False)
out["hazard_m1"] = lt.hazard.iloc[0]; out["hazard_m12"] = lt.hazard.iloc[11]; out["hazard_m24_36"] = lt.hazard.iloc[23:36].mean(); out["hazard_m60_71"] = lt.hazard.iloc[59:71].mean()
# 「解約した人の平均在籍月数」と「平均在籍月数（KMの制限平均）」
from lifelines.utils import restricted_mean_survival_time as rmst
out["mean_tenure_churners"] = t.loc[t.event == 1, "duration"].mean()
out["mean_tenure_all_observed"] = t.duration.mean()
out["rmst72"] = float(rmst(km, t=72))
pd.DataFrame({"month": km.survival_function_.index, "S": km.survival_function_.values[:, 0]}).to_csv(R / "A_km_overall.csv", index=False)

# --- B. 契約の種類ごと ---
kmc = {}
for c, g in t.groupby("Contract"):
    k = KaplanMeierFitter().fit(g.d, g.event); kmc[c] = k
    pd.DataFrame({"month": k.survival_function_.index, "S": k.survival_function_.values[:, 0]}).to_csv(R / f"B_km_{c.replace(' ','_').replace('-','_')}.csv", index=False)
out["contract"] = {c: {"n": int((t.Contract == c).sum()), "S12": float(k.survival_function_at_times(12).iloc[0]), "S24": float(k.survival_function_at_times(24).iloc[0]),
                     "S72": float(k.survival_function_at_times(72).iloc[0]), "rmst72": float(rmst(k, t=72))} for c, k in kmc.items()}
lr = multivariate_logrank_test(t.d, t.Contract, t.event); out["logrank_p"] = float(lr.p_value); out["logrank_chi2"] = float(lr.test_statistic)

# --- C. Cox ---
X = pd.DataFrame({"d": t.d, "e": t.event,
    "1年契約": (t.Contract == "One year").astype(int), "2年契約": (t.Contract == "Two year").astype(int),
    "光回線": (t.InternetService == "Fiber optic").astype(int), "回線なし": (t.InternetService == "No").astype(int),
    "電子小切手払い": (t.PaymentMethod == "Electronic check").astype(int),
    "月額10ドル高い": t.MonthlyCharges / 10, "高齢者": t.SeniorCitizen, "パートナーあり": (t.Partner == "Yes").astype(int),
    "技術サポートあり": (t.TechSupport == "Yes").astype(int), "紙の請求書なし": (t.PaperlessBilling == "Yes").astype(int)})
cph = CoxPHFitter().fit(X, "d", "e")
cs = cph.summary[["exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]]; cs.to_csv(R / "C_cox.csv")
out["cox"] = {k: [float(v) for v in cs.loc[k, ["exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]]] for k in cs.index}
out["cox_concordance"] = float(cph.concordance_index_)
ph = proportional_hazard_test(cph, X, time_transform="rank"); phs = ph.summary; phs.to_csv(R / "C_ph_test.csv")
out["ph_violations"] = [str(i) for i in phs.index[phs.p < 0.01]]
# 契約で層別した Cox（比例ハザードの崩れへの手当て）
Xs = X.drop(columns=["1年契約", "2年契約"]).assign(契約=t.Contract.values)
cph_s = CoxPHFitter().fit(Xs, "d", "e", strata=["契約"])
out["cox_strat"] = {k: float(v) for k, v in cph_s.summary["exp(coef)"].items()}
# 半分で学習して、残り半分の定着を当てる（較正）
idx = rng.permutation(len(X)); tr, te = X.iloc[idx[:len(X)//2]], X.iloc[idx[len(X)//2:]]
c2 = CoxPHFitter().fit(tr, "d", "e")
pred = c2.predict_survival_function(te.drop(columns=["d", "e"]), times=[12, 24]).mean(axis=1)
k_te = KaplanMeierFitter().fit(te.d, te.e)
out["calib"] = {"pred12": float(pred.loc[12]), "obs12": float(k_te.survival_function_at_times(12).iloc[0]),
                "pred24": float(pred.loc[24]), "obs24": float(k_te.survival_function_at_times(24).iloc[0]), "cindex_test": float(c2.score(te, "concordance_index"))}

# --- D. コホートの定着率表（法人、設立年×経過年） ---
h = pd.read_csv(B / "data/houjin_cohort.csv.gz")
rows = []
for (kind, coh), g in h.groupby(["kind_j", "cohort"]):
    for y in range(1, 11):
        m = 12 * y
        maxobs = (pd.Timestamp("2026-09-30") - pd.Timestamp(f"{coh}-12-31")).days / 30.4375   # 全員が m か月観察できるか
        if maxobs < m: continue
        alive = ((g.months >= m) | (g.event == 0) & (g.months >= m)).sum()
        dead = ((g.event == 1) & (g.months < m)).sum()
        rows.append((kind, coh, y, len(g), 1 - dead / len(g)))
coh = pd.DataFrame(rows, columns=["kind", "cohort", "year", "n", "retention"]); coh.to_csv(R / "D_cohort_retention.csv", index=False)
piv = coh[coh.kind == "株式会社"].pivot(index="cohort", columns="year", values="retention")
out["cohort_KK_y1"] = {int(k): float(v) for k, v in piv[1].items()}
out["cohort_KK_y5"] = {int(k): float(v) for k, v in piv[5].dropna().items()}
gk = coh[coh.kind == "合同会社"].pivot(index="cohort", columns="year", values="retention")
out["cohort_GK_y5"] = {int(k): float(v) for k, v in gk[5].dropna().items()}
# コホート表と KM の一致（全員が5年見られる 2016〜2020 年設立）
sub = h[(h.cohort <= 2020) & (h.kind_j == "株式会社")]
k5 = KaplanMeierFitter().fit(sub.months.clip(lower=0.01), sub.event)
out["houjin_km_5y_vs_table"] = [float(k5.survival_function_at_times(60).iloc[0]), float(1 - ((sub.event == 1) & (sub.months < 60)).sum() / len(sub))]

# --- E. LTV（1人あたりの将来の売上、月割引 年5%と置く・例示） ---
arpu = t.MonthlyCharges.mean(); out["arpu"] = arpu
disc = (1 + 0.05) ** (-1 / 12)
Sm = np.array([S(m) for m in range(0, 73)])
def ltv_from_S(Sv, arpu=arpu): return float(sum(arpu * Sv[m] * disc ** m for m in range(len(Sv))))
out["ltv_72_km"] = ltv_from_S(Sm)
# 72か月より先の外挿：(a) 最後の12か月の解約率で一定、(b) Weibull、(c) 指数（全期間一定）、(d) sBG（離脱しやすさが人ごとに違う）
hz = lt.hazard.iloc[60:72].mean()
S_a = np.concatenate([Sm, Sm[-1] * (1 - hz) ** np.arange(1, 289)])
wb = WeibullFitter().fit(t.d, t.event); ex = ExponentialFitter().fit(t.d, t.event); ln_ = LogNormalFitter().fit(t.d, t.event)
mm = np.arange(0, 361)
S_w = wb.survival_function_at_times(np.maximum(mm, 1e-6)).values; S_e = ex.survival_function_at_times(np.maximum(mm, 1e-6)).values; S_l = ln_.survival_function_at_times(np.maximum(mm, 1e-6)).values
# sBG：毎月の解約確率 θ が Beta(α,β) に従う。打ち切りありの尤度
dur = np.ceil(t.d.values).astype(int); ev = t.event.values
def nll(p):
    a, b = np.exp(p)
    S_ = lambda n: np.exp(betaln(a, b + n) - betaln(a, b))           # n か月残っている確率
    P_ = lambda n: np.exp(betaln(a + 1, b + n - 1) - betaln(a, b))   # ちょうど n か月目に辞める確率
    return -(np.sum(np.log(P_(dur[ev == 1]))) + np.sum(np.log(S_(dur[ev == 0]))))
res = minimize(nll, [0, 1], method="Nelder-Mead"); a, b = np.exp(res.x); out["sbg"] = [float(a), float(b)]
S_s = np.exp(betaln(a, b + mm) - betaln(a, b))
H = 360
out["ltv_30y"] = {"KMのあと一定": ltv_from_S(S_a[:H + 1]), "Weibull": ltv_from_S(S_w[:H + 1]), "指数（一定）": ltv_from_S(S_e[:H + 1]),
                  "対数正規": ltv_from_S(S_l[:H + 1]), "sBG（人ごとに違う）": ltv_from_S(S_s[:H + 1])}
out["aic"] = {"Weibull": float(wb.AIC_), "指数": float(ex.AIC_), "対数正規": float(ln_.AIC_), "sBG": float(2 * res.fun + 4)}
out["ltv_naive_arpu_over_churn"] = float(arpu / (t.event.mean()))     # よくある誤り：ARPU ÷ 見かけの解約率
out["ltv_naive_month_churn"] = float(arpu / lt.hazard.mean())
out["S72_models"] = {"KM": float(Sm[72]), "Weibull": float(S_w[72]), "指数": float(S_e[72]), "対数正規": float(S_l[72]), "sBG": float(S_s[72])}
pd.DataFrame({"month": mm, "KM_then_const": S_a[:361], "Weibull": S_w, "Exponential": S_e, "LogNormal": S_l, "sBG": S_s}).to_csv(R / "E_extrapolation.csv", index=False)
# 契約別 LTV（72か月まで、KM）
out["ltv72_contract"] = {}
for c, k in kmc.items():
    g = t[t.Contract == c]; Sv = np.array([float(k.survival_function_at_times(m).iloc[0]) for m in range(73)])
    out["ltv72_contract"][c] = ltv_from_S(Sv, g.MonthlyCharges.mean())
# ブートストラップ（顧客を復元抽出、300回）で LTV72 の区間
bs = []
for i in range(300):
    s = t.sample(len(t), replace=True, random_state=1000 + i)
    k = KaplanMeierFitter().fit(s.d, s.event); Sv = k.survival_function_at_times(range(73)).values
    bs.append(ltv_from_S(Sv, s.MonthlyCharges.mean()))
out["ltv72_ci"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]

# --- F. 打ち切りを無視したら（解約した人だけで平均在籍を出す誤り）・0か月を除く・割引率 ---
t1 = t[t.duration > 0]; k1 = KaplanMeierFitter().fit(t1.duration, t1.event)
out["rob_drop0_S12"] = float(k1.survival_function_at_times(12).iloc[0]); out["rob_drop0_S72"] = float(k1.survival_function_at_times(72).iloc[0])
out["rob_disc"] = {}
for r in [0.0, 0.03, 0.10]:
    dd = (1 + r) ** (-1 / 12); out["rob_disc"][str(r)] = float(sum(arpu * Sm[m] * dd ** m for m in range(73)))
json.dump(out, open(R / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:6000])
