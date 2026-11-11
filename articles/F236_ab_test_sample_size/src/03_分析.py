# 03 分析：A/B テストは何人集めれば「差」が分かるのか
# A 割合の指標：必要な人数（1群あたり）＝ 基準の割合 × 見つけたい差（相対）
# B シミュレーションで検出力と第1種の誤りを確かめる
# C テストの日数（1日の訪問者数別、週単位に切り上げ）
# D 検出力が低いと何が起きるか（有意になった結果の「差の大きさの誇張」と「向きの誤り」）
# E 金額の指標：公開データの形のばらつき → 必要な人数、上限で切る（ウィンザー化）とどれだけ減るか
# F 頑健性：検出力・α・片側／両側、割り付けの比、分布の形、近似と厳密、乱数の種
import json, math, numpy as np, pandas as pd
from pathlib import Path
from scipy import stats

R = Path(__file__).resolve().parents[1]
OUT = R / "results"; OUT.mkdir(exist_ok=True)
P = json.load(open(R / "data" / "metric_params.json"))
exec(open(R / "src" / "02_整形.py").read().split("rng = np.random")[0])   # sampler と b, alpha を読み込む
SEED = 20261111
res = {}

def z(q): return stats.norm.ppf(q)

def n_prop(p1, rel, alpha=.05, power=.8, two=True, ratio=1.0):
    """2つの割合の差の検定に必要な1群（対照群）あたりの人数。ratio=処置群/対照群"""
    p2 = p1 * (1 + rel); d = abs(p2 - p1)
    za = z(1 - alpha / 2) if two else z(1 - alpha); zb = z(power)
    pbar = (p1 + ratio * p2) / (1 + ratio)
    num = (za * math.sqrt(pbar * (1 - pbar) * (1 + 1 / ratio)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2) / ratio)) ** 2
    return math.ceil(num / d ** 2)

def n_mean(sd, delta, alpha=.05, power=.8):
    return math.ceil(2 * (z(1 - alpha / 2) + z(power)) ** 2 * sd ** 2 / delta ** 2)

# ---------- A 必要な人数の表 ----------
BASE = [0.01, 0.02, 0.05, 0.10, 0.30, round(P["share_2024"], 4)]
LIFT = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30]
rows = [{"baseline": p, "rel_lift": l, "n_per_arm": n_prop(p, l)} for p in BASE for l in LIFT]
A = pd.DataFrame(rows); A.to_csv(OUT / "A_n_per_arm.csv", index=False)
res["A"] = {f"{p}_{l}": int(n) for p, l, n in A[["baseline", "rel_lift", "n_per_arm"]].values}

# 「4倍の法則」：差を半分にすると人数は約4倍
res["A_halving_ratio_p5"] = n_prop(.05, .05) / n_prop(.05, .10)

# ---------- B シミュレーション（検出力・第1種の誤り） ----------
rng = np.random.default_rng(SEED)
def sim_power(p1, rel, n1, n2=None, sims=10000, alpha=.05, rng=rng):
    n2 = n2 or n1; p2 = p1 * (1 + rel)
    x1 = rng.binomial(n1, p1, sims); x2 = rng.binomial(n2, p2, sims)
    q1, q2 = x1 / n1, x2 / n2; pp = (x1 + x2) / (n1 + n2)
    se = np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2)); zz = (q2 - q1) / np.where(se > 0, se, np.nan)
    sig = np.abs(zz) > z(1 - alpha / 2)
    return np.nanmean(sig), q2 - q1, sig
Brows = []
for p, l in [(.01, .10), (.02, .10), (.05, .05), (.05, .10), (.10, .05), (.10, .10), (.30, .02), (P["share_2024"], .02)]:
    n = n_prop(p, l)
    pw, _, _ = sim_power(p, l, n)
    fp, _, _ = sim_power(p, 0.0, n)
    pw_half, _, _ = sim_power(p, l, n // 2)
    Brows.append({"baseline": p, "rel_lift": l, "n_per_arm": n, "sim_power": pw, "sim_alpha": fp, "sim_power_half_n": pw_half})
B = pd.DataFrame(Brows); B.to_csv(OUT / "B_sim_check.csv", index=False)
res["B"] = B.round(4).to_dict("records")
# 検出力の曲線（p=5%・+10%）：人数を変える
n0 = n_prop(.05, .10); curve = []
for f in [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
    n = int(n0 * f); pw, _, _ = sim_power(.05, .10, n, sims=6000)
    # 正規近似の理論値
    p1, p2 = .05, .055; se = math.sqrt(p1 * (1 - p1) / n + p2 * (1 - p2) / n)
    th = 1 - stats.norm.cdf(z(.975) - (p2 - p1) / se) + stats.norm.cdf(-z(.975) - (p2 - p1) / se)
    curve.append({"n_per_arm": n, "frac_of_required": f, "sim_power": pw, "theory_power": th})
pd.DataFrame(curve).to_csv(OUT / "B_power_curve_p5_l10.csv", index=False)

# ---------- C テストの日数 ----------
TRAF = [1000, 5000, 20000, 100000]          # 1日の訪問者数（2群の合計）
Crows = []
for p, l in [(.02, .10), (.05, .05), (.05, .10), (.05, .20), (.10, .10)]:
    n = n_prop(p, l)
    for t in TRAF:
        d = math.ceil(2 * n / t); w = max(1, math.ceil(d / 7))
        Crows.append({"baseline": p, "rel_lift": l, "n_per_arm": n, "daily_visitors": t, "days_raw": d, "weeks": w, "days_week_rounded": 7 * w})
C = pd.DataFrame(Crows); C.to_csv(OUT / "C_duration.csv", index=False)
# 4週間で見つけられる最小の差（MDE）
def mde_prop(p, n, alpha=.05, power=.8):
    lo, hi = 1e-4, 5.0
    for _ in range(80):
        m = (lo + hi) / 2
        if n_prop(p, m, alpha, power) > n: lo = m
        else: hi = m
    return hi
Mrows = [{"baseline": p, "daily_visitors": t, "weeks": w, "mde_rel": mde_prop(p, t * 7 * w // 2)}
         for p in [.02, .05, .10] for t in TRAF for w in [1, 2, 4]]
M = pd.DataFrame(Mrows); M.to_csv(OUT / "C_mde_by_traffic.csv", index=False)
res["C_mde_4w_p5"] = {int(r.daily_visitors): round(r.mde_rel, 4) for r in M.query("baseline==0.05 and weeks==4").itertuples()}

# ---------- D 検出力が低いと何が起きるか ----------
Drows = []
p1, l = .05, .10
for target in [0.1, 0.2, 0.3, 0.5, 0.8, 0.9]:
    n = n_prop(p1, l, power=target)
    pw, diff, sig = sim_power(p1, l, n, sims=20000)
    true = p1 * l; ds = diff[sig]
    Drows.append({"target_power": target, "n_per_arm": n, "sim_power": pw,
                  "exaggeration": float(np.mean(np.abs(ds)) / true) if len(ds) else np.nan,
                  "sign_error": float(np.mean(ds < 0)) if len(ds) else np.nan})
Dd = pd.DataFrame(Drows); Dd.to_csv(OUT / "D_winners_curse.csv", index=False)
res["D"] = Dd.round(4).to_dict("records")

# ---------- E 金額の指標 ----------
rng_e = np.random.default_rng(SEED + 1)
pool = sampler(rng_e, 3_000_000) * P["scale"]
buy = rng_e.random(len(pool)) < P["share_2024"]
spend = np.where(buy, pool, 0.0)                       # 全員の金額（買わない人は0）
mu, sd = spend.mean(), spend.std()
Erows = []
for lab, cap_q in [("そのまま", None), ("上位1%で切る", .99), ("上位5%で切る", .95)]:
    v = spend if cap_q is None else np.minimum(spend, np.quantile(spend[spend > 0], cap_q))
    for rel in [.02, .05, .10]:
        Erows.append({"metric": "金額（全員）", "treatment": lab, "rel_lift": rel, "mean": v.mean(), "sd": v.std(),
                      "cv": v.std() / v.mean(), "n_per_arm": n_mean(v.std(), v.mean() * rel)})
# 割合の指標（買ったかどうか）と、買った人の金額だけ
for rel in [.02, .05, .10]:
    Erows.append({"metric": "買った割合", "treatment": "-", "rel_lift": rel, "mean": P["share_2024"], "sd": math.sqrt(P["share_2024"] * (1 - P["share_2024"])),
                  "cv": math.sqrt((1 - P["share_2024"]) / P["share_2024"]), "n_per_arm": n_prop(P["share_2024"], rel)})
    u = spend[spend > 0]
    Erows.append({"metric": "買った人の金額", "treatment": "そのまま", "rel_lift": rel, "mean": u.mean(), "sd": u.std(), "cv": u.std() / u.mean(),
                  "n_per_arm": math.ceil(n_mean(u.std(), u.mean() * rel) / P["share_2024"])})   # 来た人の数に直す
E = pd.DataFrame(Erows); E.to_csv(OUT / "E_spend_metric.csv", index=False)
res["E"] = E.round(3).to_dict("records")

# 金額のシミュレーション：+5% の効果（全員の金額が1.05倍）、上限で切っても検出力は保てるか・推定はずれるか
rng_s = np.random.default_rng(SEED + 2)
rel = .05; n = n_mean(sd, mu * rel); sims = 400
cap99 = np.quantile(spend[spend > 0], .99)
hit = {"raw": 0, "cap99": 0}; est = {"raw": [], "cap99": []}
for s in range(sims):
    a = spend[rng_s.integers(0, len(spend), n)]; bb = spend[rng_s.integers(0, len(spend), n)] * (1 + rel)
    for k, f in [("raw", lambda v: v), ("cap99", lambda v: np.minimum(v, cap99))]:
        va, vb = f(a), f(bb); t = stats.ttest_ind(vb, va, equal_var=False)
        hit[k] += t.pvalue < .05; est[k].append(vb.mean() / va.mean() - 1)
res["E_sim"] = {"n_per_arm": n, "sims": sims, "power_raw": hit["raw"] / sims, "power_cap99": hit["cap99"] / sims,
                "mean_est_raw": float(np.mean(est["raw"])), "mean_est_cap99": float(np.mean(est["cap99"]))}

# ---------- F 頑健性 ----------
Frows = []
for lab, kw in [("主：両側α5%・検出力80%", {}), ("検出力90%", {"power": .9}), ("α1%", {"alpha": .01}), ("片側α5%", {"two": False})]:
    Frows.append({"check": lab, "baseline": .05, "rel_lift": .10, "n_per_arm_control": n_prop(.05, .10, **kw)})
for ratio in [1.0, 0.5, 0.25, 0.111]:   # 処置群/対照群（1:1, 2:1, 4:1, 9:1）
    nc = n_prop(.05, .10, ratio=ratio)
    Frows.append({"check": f"割り付け 対照:処置 = 1:{ratio:.3g}", "baseline": .05, "rel_lift": .10, "n_per_arm_control": nc,
                  "total": int(nc * (1 + ratio))})
F = pd.DataFrame(Frows); F.to_csv(OUT / "F_robust_design.csv", index=False)
res["F_design"] = F.round(0).to_dict("records")

# 分布の形：同じ平均・同じ CV の対数正規と比べる（必要な人数は同じ式なので、シミュレーションの検出力で比べる）
cv_u = pool.std() / pool.mean(); s2 = math.log(1 + cv_u ** 2)
rng_l = np.random.default_rng(SEED + 3)
logn = rng_l.lognormal(math.log(pool.mean()) - s2 / 2, math.sqrt(s2), len(pool))
spend_ln = np.where(buy, logn, 0.0)
hits = 0; sims2 = 300
for s in range(sims2):
    a = spend_ln[rng_l.integers(0, len(spend_ln), n)]; bb = spend_ln[rng_l.integers(0, len(spend_ln), n)] * (1 + rel)
    hits += stats.ttest_ind(bb, a, equal_var=False).pvalue < .05
res["F_shape"] = {"lognormal_power": hits / sims2, "lognormal_p99_user": float(np.quantile(logn, .99)), "main_p99_user": float(np.quantile(pool, .99))}

# 近似と厳密：小さい基準（1%）で、正規近似の人数のときのシミュレーション検出力（B と同じ）／乱数の種を変える
seeds = []
for sd_ in [1, 2, 3, 4, 5]:
    r_ = np.random.default_rng(sd_)
    pw, _, _ = sim_power(.05, .10, n_prop(.05, .10), sims=10000, rng=r_)
    seeds.append(pw)
res["F_seeds_power_p5_l10"] = [round(x, 4) for x in seeds]
res["params"] = P
json.dump(res, open(OUT / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(A.pivot(index="baseline", columns="rel_lift", values="n_per_arm"))
print(B.round(3)); print(Dd.round(3)); print(E.round(2)); print(F); print(json.dumps({k: res[k] for k in ["E_sim", "F_shape", "F_seeds_power_p5_l10", "C_mde_4w_p5", "A_halving_ratio_p5"]}, ensure_ascii=False, default=float))
