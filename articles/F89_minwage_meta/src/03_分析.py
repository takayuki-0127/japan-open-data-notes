"""メタ分析：固定効果・ランダム効果（DerSimonian–Laird と REML、Hartung–Knapp の区間）、
異質性（Q・I²・τ²）、1本ずつ外す、同じデータを使う F01 と F17 の扱い、
推定値の選び方（仕様）をすべて組み合わせたときのばらつき、統合後に見分けられる大きさ。"""
import itertools
import json
import numpy as np
import pandas as pd
from scipy import stats, optimize
from common import DATA, RES, REF_BAND

RES.mkdir(exist_ok=True)
est = pd.read_csv(DATA / "estimates_common_unit.csv")


def meta(y, se):
    y, se = np.asarray(y, float), np.asarray(se, float)
    k = len(y)
    w = 1 / se**2
    fe = np.sum(w * y) / np.sum(w)
    fe_se = np.sqrt(1 / np.sum(w))
    Q = np.sum(w * (y - fe) ** 2)
    df = k - 1
    I2 = max(0.0, (Q - df) / Q) if Q > 0 else 0.0
    c = np.sum(w) - np.sum(w**2) / np.sum(w)
    tau2_dl = max(0.0, (Q - df) / c) if c > 0 else 0.0

    def negll(t2):
        v = se**2 + t2
        wr = 1 / v
        mu = np.sum(wr * y) / np.sum(wr)
        return 0.5 * (np.sum(np.log(v)) + np.log(np.sum(wr)) + np.sum(wr * (y - mu) ** 2))
    tau2_reml = optimize.minimize_scalar(negll, bounds=(0, 50), method="bounded").x if k > 1 else 0.0
    if tau2_reml < 1e-8:
        tau2_reml = 0.0

    out = dict(k=k, fe=fe, fe_se=fe_se, fe_lo=fe - 1.96 * fe_se, fe_hi=fe + 1.96 * fe_se,
               Q=Q, Q_p=1 - stats.chi2.cdf(Q, df) if df > 0 else np.nan, I2=I2,
               tau2_dl=tau2_dl, tau2_reml=tau2_reml)
    for lab, t2 in [("dl", tau2_dl), ("reml", tau2_reml)]:
        wr = 1 / (se**2 + t2)
        mu = np.sum(wr * y) / np.sum(wr)
        s = np.sqrt(1 / np.sum(wr))
        out[f"re_{lab}"] = mu
        out[f"re_{lab}_se"] = s
        out[f"re_{lab}_lo"] = mu - 1.96 * s
        out[f"re_{lab}_hi"] = mu + 1.96 * s
        if k > 1:  # Hartung–Knapp–Sidik–Jonkman（研究が少ないときの区間）
            q = np.sum(wr * (y - mu) ** 2) / (k - 1)
            s_hk = np.sqrt(max(q, 1.0) / np.sum(wr))   # 1 未満にしない（修正版）
            tcrit = stats.t.ppf(0.975, k - 1)
            out[f"re_{lab}_hk_lo"] = mu - tcrit * s_hk
            out[f"re_{lab}_hk_hi"] = mu + tcrit * s_hk
    out["mde80_fe"] = 2.8 * fe_se
    out["weights_fe"] = list(w / w.sum())
    return out


summary = {}
emp = est[(est.outcome == "emp") & est.main].set_index("study")
m = meta(emp.est, emp.se)
summary["emp_main"] = m
summary["emp_main_inputs"] = emp[["spec", "est", "se", "lo", "hi"]].reset_index().to_dict("records")

# 統合後の検出力：本当の弾力性が −0.1・−0.3 のとき
for th in [-0.1, -0.2, -0.3]:
    z = abs(th) / m["fe_se"]
    summary.setdefault("power_fe", {})[str(th)] = float(stats.norm.cdf(z - 1.96) + stats.norm.cdf(-z - 1.96))
# 海外の目安（0〜−0.3）と重なるか
summary["overlap_ref_band"] = bool(m["fe_lo"] < REF_BAND[1] and m["fe_hi"] > REF_BAND[0])

# 1本ずつ外す
loo = []
for s in emp.index:
    sub = emp.drop(s)
    r = meta(sub.est, sub.se)
    loo.append(dict(dropped=s, fe=r["fe"], lo=r["fe_lo"], hi=r["fe_hi"], mde80=r["mde80_fe"]))
loo = pd.DataFrame(loo)

# F01 と F17 は同じ県×年のデータ → 1本にまとめる（相関 ρ を仮定）
dep = []
for rho in [0.0, 0.5, 0.8, 1.0]:
    a, b = emp.loc["F01"], emp.loc["F17"]
    w1, w2 = 1 / a.se**2, 1 / b.se**2
    comb = (w1 * a.est + w2 * b.est) / (w1 + w2)
    v = (w1**2 * a.se**2 + w2**2 * b.se**2 + 2 * rho * w1 * w2 * a.se * b.se) / (w1 + w2) ** 2
    y = [comb, emp.loc["F15"].est]
    se = [np.sqrt(v), emp.loc["F15"].se]
    r = meta(y, se)
    dep.append(dict(rho=rho, f01f17_est=comb, f01f17_se=np.sqrt(v), fe=r["fe"], lo=r["fe_lo"], hi=r["fe_hi"],
                    mde80=r["mde80_fe"]))
dep = pd.DataFrame(dep)

# 推定値の選び方（仕様）をすべて組み合わせる
cand = {s: est[(est.outcome == "emp") & (est.study == s)] for s in ["F01", "F15", "F17"]}
spec = []
for i, j, l in itertools.product(cand["F01"].index, cand["F15"].index, cand["F17"].index):
    sub = est.loc[[i, j, l]]
    r = meta(sub.est, sub.se)
    spec.append(dict(f01=est.loc[i, "spec"], f15=est.loc[j, "spec"], f17=est.loc[l, "spec"],
                     fe=r["fe"], fe_lo=r["fe_lo"], fe_hi=r["fe_hi"], re=r["re_dl"],
                     re_hk_lo=r["re_dl_hk_lo"], re_hk_hi=r["re_dl_hk_hi"], I2=r["I2"], mde80=r["mde80_fe"]))
spec = pd.DataFrame(spec).sort_values("fe").reset_index(drop=True)
summary["spec_curve"] = dict(
    n=len(spec), fe_min=spec.fe.min(), fe_max=spec.fe.max(), fe_median=spec.fe.median(),
    share_fe_ci_below0=float((spec.fe_hi < 0).mean()), share_fe_ci_above0=float((spec.fe_lo > 0).mean()),
    share_re_hk_excl0=float(((spec.re_hk_hi < 0) | (spec.re_hk_lo > 0)).mean()),
    share_I2_ge50=float((spec.I2 >= 0.5).mean()),
    mde80_min=spec.mde80.min(), mde80_max=spec.mde80.max())

# 失業率（F01・F17）
un = est[(est.outcome == "unemp") & est.main].set_index("study")
summary["unemp_main"] = meta(un.est, un.se)
summary["unemp_inputs"] = un[["spec", "est", "se", "lo", "hi"]].reset_index().to_dict("records")

# 同じくらいの精度の研究があと何本あれば、弾力性 −0.1・−0.3 を見分けられるか（独立と仮定）
need = []
se_ref = {"F01並み": emp.loc["F01"].se, "F17並み": emp.loc["F17"].se, "F15並み": emp.loc["F15"].se}
for lab, s in se_ref.items():
    for th in [0.1, 0.2, 0.3]:
        need.append(dict(ref=lab, se=s, target=th, n_needed=int(np.ceil((2.8 * s / th) ** 2))))
need = pd.DataFrame(need)
curve = []
for n in range(1, 41):
    s_pool = 1 / np.sqrt(1 / m["fe_se"] ** 2 + (n - 1) / emp.loc["F01"].se ** 2) if n >= 1 else m["fe_se"]
    for th in [0.1, 0.3]:
        z = th / s_pool
        curve.append(dict(extra_studies=n - 1, target=th, se_pool=s_pool, power=stats.norm.cdf(z - 1.96)))
curve = pd.DataFrame(curve)

# F01 の主な比較（bite の高低 × 2016年以降）は、最低賃金の上がり方がほぼ同じなので換算できない
fs = pd.read_csv(DATA / "raw" / "F01_first_stage.csv")
summary["f01_first_stage"] = fs.to_dict("records")

est.to_csv(RES / "estimates_common_unit.csv", index=False, encoding="utf-8-sig")
loo.to_csv(RES / "leave_one_out.csv", index=False, encoding="utf-8-sig")
dep.to_csv(RES / "dependence_f01_f17.csv", index=False, encoding="utf-8-sig")
spec.to_csv(RES / "spec_combinations.csv", index=False, encoding="utf-8-sig")
need.to_csv(RES / "studies_needed.csv", index=False, encoding="utf-8-sig")
curve.to_csv(RES / "power_vs_studies.csv", index=False, encoding="utf-8-sig")
summary["constants"] = json.load(open(DATA / "constants.json"))


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return round(float(o), 5)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o
json.dump(clean(summary), open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(clean({k: summary[k] for k in ["emp_main", "power_fe", "overlap_ref_band", "spec_curve", "unemp_main"]}), ensure_ascii=False, indent=1))
print(loo.round(3)); print(dep.round(3)); print(need)

# 出版バイアスの見方（参考）：研究が3本では漏斗図の非対称は判定できない。
# 仕様の違いを含む雇用の推定値すべて（17個、互いに独立ではない）で Egger 回帰を参考として出す。
import statsmodels.api as sm
allemp = est[est.outcome == "emp"]
X = sm.add_constant(1 / allemp.se)
eg = sm.WLS(allemp.est / allemp.se, X).fit()
egger = dict(n=len(allemp), intercept=eg.params.iloc[0], intercept_se=eg.bse.iloc[0], intercept_p=eg.pvalues.iloc[0],
             note="推定値は互いに独立でないため参考値")
summary["egger_all_specs"] = egger
json.dump(clean(summary), open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print("Egger", clean(egger))
