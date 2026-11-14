"""設計A：bite の差の差（2016年に一斉に始まる）と、前提の確かめ（計画の 1〜7）。"""
import numpy as np
import pandas as pd
from scipy import stats

from common import DATA, SEED, fe_reg, r, save_json, wild_cluster_p

p = pd.read_csv(DATA / "panel.csv")
A = p[p.year.between(2008, 2019)].copy()
BASE, PRE, POST = 2015, list(range(2008, 2015)), list(range(2016, 2020))
out = {}

# ---- 主の推定と、first stage・副の指標・プラセボの指標（同じ形の差の差）
rows = []
for y, lab in [("emp_rate", "就業率（主）"), ("unemp_rate", "完全失業率"), ("log_wage", "短時間の時給 100×log（効いているか）"),
               ("log_pop15", "15歳以上人口 100×log（効かないはずの指標）")]:
    f = fe_reg(A, y, ["did_a"])
    b, se = f["b"][0], f["se"][0]
    t = b / se
    pv = 2 * stats.t.sf(abs(t), f["G"] - 1)
    rows.append({"指標": lab, "y": y, "推定値": r(b), "標準誤差": r(se), "下限95": r(b - stats.t.ppf(.975, f["G"] - 1) * se),
                 "上限95": r(b + stats.t.ppf(.975, f["G"] - 1) * se), "p": r(pv), "最小検出効果80": r(2.8 * se), "n": f["n"]})
did = pd.DataFrame(rows)
did.to_csv(DATA.parent / "results" / "a_did.csv", index=False)
print(did)

# ---- wild cluster bootstrap（主の指標と first stage）
wb = []
for y in ["emp_rate", "unemp_rate", "log_wage"]:
    for wt in ["rademacher", "webb"]:
        pw, t0 = wild_cluster_p(A, y, "did_a", B=9999, weights=wt)
        wb.append({"y": y, "重み": wt, "t": r(t0), "p_wild": r(pw)})
wb = pd.DataFrame(wb)
wb.to_csv(DATA.parent / "results" / "a_wild_bootstrap.csv", index=False)
print(wb)

# ---- イベントスタディ（基準2015年）
ev_cols = []
for yr in PRE + POST:
    c = f"ev_{yr}"
    A[c] = (A.treat_a * (A.year == yr)).astype(int)
    ev_cols.append(c)
es_all = {}
for y in ["emp_rate", "unemp_rate", "log_wage"]:
    f = fe_reg(A, y, ev_cols)
    es_all[y] = f
    pre_idx = [ev_cols.index(f"ev_{yr}") for yr in PRE if not (y == "log_wage" and yr == 2008)]
es_rows = []
for y, f in es_all.items():
    for i, c in enumerate(ev_cols):
        if np.isnan(f["b"][i]) or (y == "log_wage" and c == "ev_2008"):
            continue
        es_rows.append({"y": y, "year": int(c[3:]), "beta": r(f["b"][i]), "se": r(f["se"][i]),
                        "lo95": r(f["b"][i] - 1.96 * f["se"][i]), "hi95": r(f["b"][i] + 1.96 * f["se"][i])})
    es_rows.append({"y": y, "year": BASE, "beta": 0.0, "se": 0.0, "lo95": 0.0, "hi95": 0.0})
es = pd.DataFrame(es_rows).sort_values(["y", "year"])
es.to_csv(DATA.parent / "results" / "a_event_study.csv", index=False)

# 事前トレンドの同時検定（Wald、F 分布 自由度 G−1）
def joint_pre(f, idx, G=47):
    b, V = f["b"][idx], f["V"][np.ix_(idx, idx)]
    W = float(b @ np.linalg.solve(V, b))
    q = len(idx)
    F = W / q
    return W, F, float(stats.f.sf(F, q, G - 1))

# 賃金は2009年からなので、2008年の列はデータがなく推定されない（fe_reg で落ちる）。ここでは就業率・失業率だけ
pre_idx = [ev_cols.index(f"ev_{yr}") for yr in PRE]
post_idx = [ev_cols.index(f"ev_{yr}") for yr in POST]
pt = []
for y in ["emp_rate", "unemp_rate"]:
    W, F, pv = joint_pre(es_all[y], pre_idx)
    pt.append({"y": y, "Wald": r(W), "F": r(F), "p": r(pv), "自由度": len(pre_idx)})
pt = pd.DataFrame(pt)
pt.to_csv(DATA.parent / "results" / "a_pretrend_test.csv", index=False)
print(pt)

# ---- 事前トレンド検定の力（Roth 2022 の考え方）：直線のずれ δ_t = s×(t−2015) を置いて、検定が見つける確率
f = es_all["emp_rate"]
Vpre = f["V"][np.ix_(pre_idx, pre_idx)]
Lpre = np.linalg.cholesky(Vpre)
rel_pre = np.array(PRE) - BASE
rng = np.random.default_rng(SEED)
Z = rng.standard_normal((20000, len(PRE)))
crit = stats.f.ppf(0.95, len(PRE), 46) * len(PRE)
Vinv = np.linalg.inv(Vpre)
def power(s):
    draws = s * rel_pre + Z @ Lpre.T
    W = np.einsum("ij,jk,ik->i", draws, Vinv, draws)
    return float(np.mean(W > crit))
grid = np.round(np.arange(0, 0.301, 0.005), 3)
pw = pd.DataFrame({"slope": grid, "power": [power(s) for s in grid]})
pw["post_bias"] = pw["slope"] * np.mean(np.array(POST) - BASE)   # 処置後4年の平均に乗る偏り
pw.to_csv(DATA.parent / "results" / "a_pretest_power.csv", index=False)
s50 = float(pw.loc[pw.power >= 0.5, "slope"].iloc[0])
s80 = float(pw.loc[pw.power >= 0.8, "slope"].iloc[0])

# ---- 平行トレンドが崩れたときの感度（Rambachan–Roth の考え方を簡略化）
bpost = f["b"][post_idx]
Vpost = f["V"][np.ix_(post_idx, post_idx)]
wv = np.ones(len(POST)) / len(POST)
theta = float(wv @ bpost)
se_theta = float(np.sqrt(wv @ Vpost @ wv))
bpre_full = np.r_[f["b"][pre_idx], 0.0]                        # 2008〜2014, 2015=0
mpre = float(np.max(np.abs(np.diff(bpre_full))))               # 処置前の1年あたりの最大の動き
k = np.array(POST) - BASE                                      # 1,2,3,4
def rm_ci(Mbar):
    # 処置後の年 k のずれは |δ_k| ≤ k×M̄×mpre まで。平均の偏りの最大は mean(k)×M̄×mpre
    bias = float(np.mean(k)) * Mbar * mpre
    return theta - bias - 1.96 * se_theta, theta + bias + 1.96 * se_theta
rm = pd.DataFrame([{"Mbar": m, "lo": r(rm_ci(m)[0]), "hi": r(rm_ci(m)[1])} for m in np.round(np.arange(0, 2.01, 0.05), 2)])
rm.to_csv(DATA.parent / "results" / "a_sensitivity_rm.csv", index=False)
# 0 をまたぐ（＝「上がった」とも言えなくなる）最小の M̄。もともと 0 をまたいでいれば 0
cross0 = rm[(rm.lo <= 0) & (rm.hi >= 0)]
breakdown0 = float(cross0.Mbar.iloc[0]) if len(cross0) else np.nan
# 「0.5%pt 以上下がった」を否定できなくなる最小の M̄（下限が −0.5 を下回る）
below = rm[rm.lo < -0.5]
breakdown_neg05 = float(below.Mbar.iloc[0]) if len(below) else np.nan

# 直線の延長：処置前の係数（2008〜2015）に直線を GLS で当て、処置後に延ばした分を引く
Xl = np.c_[np.ones(len(PRE) + 1), np.r_[rel_pre, 0]]
Vfull = np.zeros((len(PRE) + 1, len(PRE) + 1))
Vfull[:len(PRE), :len(PRE)] = Vpre
Vfull[-1, -1] = 1e-8
# 2015年は 0 に固定されているので、切片なしで傾きだけ当てる（δ_2015 = 0）
xs = np.r_[rel_pre, 0][:-1].astype(float)
Wi = np.linalg.inv(Vpre)
slope = float((xs @ Wi @ f["b"][pre_idx]) / (xs @ Wi @ xs))
g_slope = (xs @ Wi) / (xs @ Wi @ xs)                           # slope = g_slope · b_pre
cvec = np.r_[-np.mean(k) * g_slope, wv]                        # theta_lin = wv·b_post − mean(k)×slope
idx_all = pre_idx + post_idx
Vall = f["V"][np.ix_(idx_all, idx_all)]
theta_lin = theta - float(np.mean(k)) * slope
se_lin = float(np.sqrt(cvec @ Vall @ cvec))

# ---- プラセボの時期：2012年に始まったとみなす（2008〜2015年）
P = p[p.year.between(2008, 2015)].copy()
P["did_fake"] = P.treat_a * (P.year >= 2012)
fp = fe_reg(P, "emp_rate", ["did_fake"])
fpu = fe_reg(P, "unemp_rate", ["did_fake"])

main = did.set_index("y")
out = {
    "design_a": {
        "n_treat": int(A.drop_duplicates("code").treat_a.sum()), "n_ctrl": int((1 - A.drop_duplicates("code").treat_a).sum()),
        "did_emp": main.loc["emp_rate"].to_dict(), "did_unemp": main.loc["unemp_rate"].to_dict(),
        "first_stage_wage": main.loc["log_wage"].to_dict(), "placebo_pop15": main.loc["log_pop15"].to_dict(),
        "pretrend_p_emp": float(pt.set_index("y").loc["emp_rate", "p"]),
        "pretrend_p_unemp": float(pt.set_index("y").loc["unemp_rate", "p"]),
        "pretest_power": {"slope_50": s50, "slope_80": s80, "bias_50": s50 * float(np.mean(k)), "bias_80": s80 * float(np.mean(k))},
        "event_post_mean": {"theta": r(theta), "se": r(se_theta)},
        "rm": {"mpre": r(mpre), "breakdown_cross0": breakdown0, "breakdown_lo_below_-0.5": breakdown_neg05},
        "linear_extrapolation": {"pre_slope_per_year": r(slope), "theta": r(theta_lin), "se": r(se_lin),
                                 "lo95": r(theta_lin - 1.96 * se_lin), "hi95": r(theta_lin + 1.96 * se_lin)},
        "placebo_2012_emp": {"b": r(fp["b"][0]), "se": r(fp["se"][0])},
        "placebo_2012_unemp": {"b": r(fpu["b"][0]), "se": r(fpu["se"][0])},
        "wild": wb.to_dict(orient="records"),
    }
}
save_json(out, "a_main.json")
print(out)
