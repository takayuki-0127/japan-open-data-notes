"""F237 分析：途中で見ると誤検出がどれだけ増えるか／逐次検定（α消費・mSPRT）でどう防げるか。"""
import json, os, sys, time
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
sys.path.insert(0, os.path.dirname(__file__))
from common import *

os.makedirs("results", exist_ok=True)
R = 20000; CH = 5000
t0 = time.time()
LOG = open("results/run_log.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n"); LOG.flush()

def run(pA, pB, days, seed, methods, R=R, wk=None, daily=DAILY_PER_ARM):
    """methods: dict 名前 -> 関数(cA,cB,n) -> (止まった時間の番号 or -1, 止まったときの推定 lift)。"""
    out = {k: [] for k in methods}
    for c in range(R // CH):
        cA, cB, n = sim_cum(CH, days, pA, pB, seed * 1000 + c, daily=daily, wk=wk)
        for k, f in methods.items():
            out[k].append(f(cA, cB, n))
    res = {}
    for k in methods:
        idx = np.concatenate([o[0] for o in out[k]]); lf = np.concatenate([o[1] for o in out[k]])
        res[k] = (idx, lf)
    return res

def looks_hours(days_list):
    return np.array([d * HOURS - 1 for d in days_list])

def m_fixed_looks(days_list, bound):
    h = looks_hours(days_list)
    def f(cA, cB, n):
        z = zstat(cA[:, h], cB[:, h], n[h])
        i = first_cross(z, bound)
        hh = np.where(i >= 0, h[np.maximum(i, 0)], -1)
        lift = np.full(len(i), np.nan)
        ok = i >= 0
        rows = np.where(ok)[0]
        lift[ok] = (cB[rows, hh[ok]] / cA[rows, hh[ok]]) - 1
        return hh, lift
    return f

def m_msprt(days, tau, alpha=ALPHA):
    def f(cA, cB, n):
        H = days * HOURS
        p = msprt_pvalues(cA[:, :H], cB[:, :H], n[:H], tau)
        hit = p <= alpha
        anyh = hit.any(1); hh = np.where(anyh, hit.argmax(1), -1)
        lift = np.full(len(hh), np.nan); ok = hh >= 0; rows = np.where(ok)[0]
        lift[ok] = cB[rows, hh[ok]] / cA[rows, hh[ok]] - 1
        return hh, lift
    return f

def summarize(name, res, days_max, true_lift):
    idx, lf = res
    rej = idx >= 0
    stop_day = np.where(rej, (idx + 1) / HOURS, days_max)
    d = dict(method=name, reject_rate=float(rej.mean()), se=float(np.sqrt(rej.mean() * (1 - rej.mean()) / len(rej))),
             mean_days=float(stop_day.mean()), median_stop_day_if_reject=float(np.median((idx[rej] + 1) / HOURS)) if rej.any() else np.nan)
    if true_lift > 0 and rej.any():
        pos = rej & (lf > 0)
        d["exaggeration_median"] = float(np.median(lf[pos] / true_lift)) if pos.any() else np.nan
        d["exaggeration_mean"] = float(np.mean(lf[pos] / true_lift)) if pos.any() else np.nan
        d["wrong_sign_share"] = float(((lf < 0) & rej).sum() / rej.sum())
    return d

Z = norm.ppf(1 - ALPHA / 2)
main = {}

# ---- A. 途中で見る回数と誤検出（差がないとき） ----
log("A start", round(time.time() - t0))
sched14 = {"最後に1回": [14], "2回（7・14日目）": [7, 14], "4回（週の半分ごと）": [4, 7, 11, 14],
           "7回（2日ごと）": list(range(2, 15, 2)), "14回（毎日）": list(range(1, 15))}
methods = {k: m_fixed_looks(v, [Z] * len(v)) for k, v in sched14.items()}
def m_hourly_naive(days):
    def f(cA, cB, n):
        H = days * HOURS
        z = zstat(cA[:, :H], cB[:, :H], n[:H])
        hit = np.abs(z) >= Z; anyh = hit.any(1); hh = np.where(anyh, hit.argmax(1), -1)
        lift = np.full(len(hh), np.nan); ok = hh >= 0; rows = np.where(ok)[0]
        lift[ok] = cB[rows, hh[ok]] / cA[rows, hh[ok]] - 1
        return hh, lift
    return f
methods["336回（1時間ごと）"] = m_hourly_naive(14)
resA0 = run(BASE, BASE, 14, 1, methods)
A = [dict(looks=k, **summarize(k, v, 14, 0)) for k, v in resA0.items()]
# 28日まで毎日・1時間ごと
m28 = {"28回（毎日・28日）": m_fixed_looks(list(range(1, 29)), [Z] * 28), "672回（1時間ごと・28日）": m_hourly_naive(28)}
resA28 = run(BASE, BASE, 28, 2, m28)
A += [dict(looks=k, **summarize(k, v, 28, 0)) for k, v in resA28.items()]
pd.DataFrame(A).to_csv("results/A_peeking_false_positive.csv", index=False)
main["A"] = {a["looks"]: round(a["reject_rate"], 4) for a in A}
log("A", main["A"], round(time.time() - t0))

# 何日目に「有意」が出たか（毎日見る・差なし）
idx = resA0["14回（毎日）"][0]
main["A_firstday_hist"] = {int(d): int(((idx + 1) // HOURS == d).sum()) for d in range(1, 15)}

# ---- B/C. 境界（α消費）の計算 ----
tk4 = np.array([4, 7, 11, 14]) / 14
b_obf4 = calibrate_bounds(tk4, obf_spend); b_poc4 = calibrate_bounds(tk4, pocock_spend)
tk14 = np.arange(1, 15) / 14
b_obf14 = calibrate_bounds(tk14, obf_spend); b_poc14 = calibrate_bounds(tk14, pocock_spend)
main["bounds"] = dict(obf4=b_obf4.round(3).tolist(), pocock4=b_poc4.round(3).tolist(),
                      obf14=b_obf14.round(3).tolist(), pocock14=b_poc14.round(3).tolist())
pd.DataFrame(dict(day=[4, 7, 11, 14], obf=b_obf4, pocock=b_poc4, naive=Z)).to_csv("results/C_bounds_4looks.csv", index=False)
pd.DataFrame(dict(day=range(1, 15), obf=b_obf14, pocock=b_poc14, naive=Z)).to_csv("results/C_bounds_daily.csv", index=False)
log("bounds", main["bounds"])

TAU = BASE * LIFT  # 見つけたい差の大きさ（購入率の差 0.005）
def method_set(base=BASE, lift=LIFT):
    tau = base * lift
    return {
        "固定（14日目に1回）": m_fixed_looks([14], [Z]),
        "毎日見て1.96で止める": m_fixed_looks(list(range(1, 15)), [Z] * 14),
        "4回・O'Brien-Fleming": m_fixed_looks([4, 7, 11, 14], b_obf4),
        "4回・Pocock": m_fixed_looks([4, 7, 11, 14], b_poc4),
        "毎日・O'Brien-Fleming": m_fixed_looks(list(range(1, 15)), b_obf14),
        "mSPRT（1時間ごと・14日まで）": m_msprt(14, tau),
        "mSPRT（1時間ごと・28日まで）": m_msprt(28, tau),
    }
MS = method_set()
res0 = run(BASE, BASE, 28, 3, MS)
res1 = run(BASE, BASE * (1 + LIFT), 28, 4, MS)
rows = []
for k in MS:
    dmax = 28 if "28日" in k else 14
    s0 = summarize(k, res0[k], dmax, 0); s1 = summarize(k, res1[k], dmax, LIFT)
    rows.append(dict(method=k, fpr=s0["reject_rate"], fpr_se=s0["se"], power=s1["reject_rate"],
                     mean_days_H1=s1["mean_days"], median_stop_day_H1=s1["median_stop_day_if_reject"],
                     mean_days_H0=s0["mean_days"], exaggeration_median=s1.get("exaggeration_median"),
                     exaggeration_mean=s1.get("exaggeration_mean"), wrong_sign=s1.get("wrong_sign_share")))
C = pd.DataFrame(rows); C.to_csv("results/C_methods_comparison.csv", index=False)
main["C"] = C.round(4).to_dict(orient="records")
log(C.round(3).to_string(), round(time.time() - t0))
# 止まった日の分布（差ありのとき）
dist = {}
for k in ["固定（14日目に1回）", "毎日見て1.96で止める", "4回・O'Brien-Fleming", "mSPRT（1時間ごと・28日まで）"]:
    idx = res1[k][0]; dmax = 28 if "28日" in k else 14
    sd = np.where(idx >= 0, np.ceil((idx + 1) / HOURS), np.nan)
    dist[k] = {int(d): int((sd == d).sum()) for d in range(1, dmax + 1)}
    dist[k]["no_stop"] = int((idx < 0).sum())
main["stop_day_dist_H1"] = dist

# ---- D. mSPRT の τ の選び方 ----
D = []
for tau in [0.0025, 0.005, 0.01, 0.02]:
    m = {"m": m_msprt(28, tau)}
    r0 = run(BASE, BASE, 28, 5, m, R=10000)["m"]; r1 = run(BASE, BASE * (1 + LIFT), 28, 6, m, R=10000)["m"]
    s0 = summarize("m", r0, 28, 0); s1 = summarize("m", r1, 28, LIFT)
    D.append(dict(tau=tau, tau_rel=tau / BASE, fpr=s0["reject_rate"], power=s1["reject_rate"], mean_days_H1=s1["mean_days"],
                  exaggeration_median=s1.get("exaggeration_median")))
D = pd.DataFrame(D); D.to_csv("results/D_msprt_tau.csv", index=False); main["D"] = D.round(4).to_dict(orient="records")
log(D.round(3).to_string(), round(time.time() - t0))

# ---- E. 頑健性 ----
E = []
# E1 基準の購入率を変える
for base in [0.02, 0.20]:
    tau = base * LIFT
    m = {"毎日見て1.96": m_fixed_looks(list(range(1, 15)), [Z] * 14), "4回・OBF": m_fixed_looks([4, 7, 11, 14], b_obf4),
         "mSPRT28": m_msprt(28, tau)}
    r0 = run(base, base, 28, 7 + int(base * 100), m, R=10000); r1 = run(base, base * (1 + LIFT), 28, 8 + int(base * 100), m, R=10000)
    for k in m:
        dmax = 28 if k == "mSPRT28" else 14
        E.append(dict(check=f"基準{int(base*100)}%", method=k, fpr=summarize(k, r0[k], dmax, 0)["reject_rate"],
                      power=summarize(k, r1[k], dmax, LIFT)["reject_rate"], mean_days_H1=summarize(k, r1[k], dmax, LIFT)["mean_days"]))
# E2 曜日のパターン（週末は訪問者1.6倍・購入率0.85倍、平日は0.84倍・1.06倍）
wk = [(0.84, 1.06)] * 5 + [(1.6, 0.85)] * 2
m = {"毎日見て1.96": m_fixed_looks(list(range(1, 15)), [Z] * 14), "4回・OBF": m_fixed_looks([4, 7, 11, 14], b_obf4),
     "mSPRT28": m_msprt(28, TAU), "固定14日": m_fixed_looks([14], [Z])}
r0 = run(BASE, BASE, 28, 9, m, R=10000, wk=wk); r1 = run(BASE, BASE * (1 + LIFT), 28, 10, m, R=10000, wk=wk)
for k in m:
    dmax = 28 if k == "mSPRT28" else 14
    E.append(dict(check="曜日のパターンあり", method=k, fpr=summarize(k, r0[k], dmax, 0)["reject_rate"],
                  power=summarize(k, r1[k], dmax, LIFT)["reject_rate"], mean_days_H1=summarize(k, r1[k], dmax, LIFT)["mean_days"]))
# E3 乱数を変える（3通り）
for sd in [21, 22, 23]:
    m = {"毎日見て1.96": m_fixed_looks(list(range(1, 15)), [Z] * 14), "4回・OBF": m_fixed_looks([4, 7, 11, 14], b_obf4)}
    r0 = run(BASE, BASE, 14, sd, m, R=10000)
    for k in m:
        E.append(dict(check=f"乱数{sd}", method=k, fpr=summarize(k, r0[k], 14, 0)["reject_rate"]))
# E4 予定と違う日に見た（5・9・12・14日目）→ 実際の情報の割合で境界を計算し直す
tk_act = np.array([5, 9, 12, 14]) / 14
b_act = calibrate_bounds(tk_act, obf_spend)
m = {"予定外の日・境界を計算し直す": m_fixed_looks([5, 9, 12, 14], b_act),
     "予定外の日・予定の境界のまま": m_fixed_looks([5, 9, 12, 14], b_obf4),
     "予定の4回に加えて毎日1.96で見る": m_fixed_looks(list(range(1, 15)), [Z if d not in (4, 7, 11, 14) else b_obf4[[4, 7, 11, 14].index(d)] for d in range(1, 15)])}
r0 = run(BASE, BASE, 14, 31, m, R=10000)
for k in m:
    E.append(dict(check="見る日のずれ", method=k, fpr=summarize(k, r0[k], 14, 0)["reject_rate"]))
main["bounds_actual_days"] = b_act.round(3).tolist()
# E5 片側（良くなったときだけ止める、1.645）
def m_onesided(days_list, c):
    h = looks_hours(days_list)
    def f(cA, cB, n):
        z = zstat(cA[:, h], cB[:, h], n[h]); hit = z >= c; anyh = hit.any(1)
        i = np.where(anyh, hit.argmax(1), -1); hh = np.where(i >= 0, h[np.maximum(i, 0)], -1)
        return hh, np.full(len(i), np.nan)
    return f
m = {"片側・最後に1回": m_onesided([14], norm.ppf(0.95)), "片側・毎日": m_onesided(list(range(1, 15)), norm.ppf(0.95))}
r0 = run(BASE, BASE, 14, 41, m, R=10000)
for k in m:
    E.append(dict(check="片側検定", method=k, fpr=summarize(k, r0[k], 14, 0)["reject_rate"]))
E = pd.DataFrame(E); E.to_csv("results/E_robustness.csv", index=False); main["E"] = E.round(4).to_dict(orient="records")
log(E.round(3).to_string(), round(time.time() - t0))
json.dump(main, open("results/main.json", "w"), ensure_ascii=False, indent=1, default=float)
log("done", round(time.time() - t0))
