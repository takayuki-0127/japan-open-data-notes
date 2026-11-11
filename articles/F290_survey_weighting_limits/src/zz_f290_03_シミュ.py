"""F290 アンケートの回答の偏りを重み付けでどこまで補正できるか（シミュレーション）
母集団：就業構造基本調査 第52表（2022年。頑健性で2017年）の6変数の多重クロス表（就業時間の総数は除く）
出力：results/A_main.csv（場面×方法の評価）、results/B_robust.csv、results/C_tipping.csv、results/main.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
SEED = 290

AGE_C = {"15〜24歳": 0.0, "25〜34歳": 0.3, "35〜44歳": 0.3, "45〜54歳": 0.1, "55〜64歳": -0.2, "65〜74歳": -0.6, "75歳以上": -1.2}
SEX_C = {"女": 0.2, "男": 0.0}
EMP_C = {"正規": 0.0, "非正規": 0.2, "役員": -0.5, "自営業主など": -0.4}
HRS_C = {"200日以上・週35〜59時間": 0.0, "200日以上・週35時間未満": 0.3, "200日以上・週60時間以上": -0.6, "200日未満": 0.3}

def inc_code(s):
    return int(s.split("_")[0])
# 所得コード：01 50万未満 … 04 150〜199 / 05〜11 200〜799 / 12 800〜899 …（700万以上 = 11以上）
def inc_coef(c):
    return 0.2 if c <= 4 else (-0.3 if c >= 11 else 0.0)
def inc6(c):  # <100, 100-199, 200-299, 300-499, 500-699, 700+
    return 0 if c <= 2 else 1 if c <= 4 else 2 if c <= 6 else 3 if c <= 8 else 4 if c <= 10 else 5
def inc4(c):  # <200, 200-399, 400-699, 700+
    return 0 if c <= 4 else 1 if c <= 7 else 2 if c <= 10 else 3

def population(year):
    d = pd.read_csv(ROOT / "data" / "side_job_long.csv")
    d = d[(d.year == year) & (d.hours != "総数") & (d.n > 0)].copy()
    d["ic"] = d.income.map(inc_code)
    d["inc6"] = d.ic.map(inc6); d["inc4"] = d.ic.map(inc4)
    d["y"] = (d.side == "副業あり").astype(int)
    d["sexage"] = d.sex + d.age
    d["sae"] = d.sexage + d.emp
    d["P"] = d.n / d.n.sum()
    return d.reset_index(drop=True)

def eta(d, scen, scale=1.0, delta=np.log(2)):
    e = d.age.map(AGE_C) + d.sex.map(SEX_C)
    if scen in ("S2", "S3"):
        e = e + d.emp.map(EMP_C) + d.hours.map(HRS_C) + d.ic.map(inc_coef)
    e = e * scale
    if scen == "S3":
        e = e + delta * scale * d.y
    return e.values

def calib_a(d, e, rate):
    lo, hi = -15.0, 10.0
    for _ in range(80):
        m = (lo + hi) / 2
        r = (d.P.values / (1 + np.exp(-(m + e)))).sum()
        lo, hi = (m, hi) if r < rate else (lo, m)
    return (lo + hi) / 2

def codes(d, cols):
    return [pd.factorize(d[c])[0] for c in cols]

def poptot(d, code):
    return np.bincount(code, weights=d.P.values)

def rake(r, margins, pops, iters=200, tol=1e-10):
    w = np.ones_like(r, dtype=float)
    for _ in range(iters):
        mx = 0.0
        for cd, pp in zip(margins, pops):
            cur = np.bincount(cd, weights=r * w, minlength=len(pp))
            cur = cur / cur.sum()
            f = np.where(cur > 0, pp / np.where(cur > 0, cur, 1), 1.0)
            w = w * f[cd]
            mx = max(mx, np.abs(f[cur > 0] - 1).max())
        if mx < tol:
            break
    return w

def poststrat(r, code, pp):
    R = np.bincount(code, weights=r, minlength=len(pp))
    if np.any((pp > 0) & (R == 0)):
        return None
    f = np.where(R > 0, pp / np.where(R > 0, R / R.sum(), 1), 0)
    return f[code]

def summarize(r, w, y):
    rw = r * w
    n = r.sum()
    est = (rw * y).sum() / rw.sum()
    deff = n * (r * w * w).sum() / rw.sum() ** 2
    return est, deff, n

def tvd(r, w, code, pp):
    q = np.bincount(code, weights=r * w, minlength=len(pp)); q = q / q.sum()
    return 0.5 * np.abs(q - pp).sum()

def run(d, scen, reps, n_resp=5000, rate=0.20, scale=1.0, delta=np.log(2), incvar="inc6", seed=SEED):
    rng = np.random.default_rng(seed)
    e = eta(d, scen, scale, delta)
    a = calib_a(d, e, rate)
    p = 1 / (1 + np.exp(-(a + e)))
    ninv = int(round(n_resp / rate))
    y = d.y.values; truth = (d.P * d.y).sum()
    c_sex, c_age, c_emp, c_hrs, c_inc, c_sa, c_sae = codes(d, ["sex", "age", "emp", "hours", incvar, "sexage", "sae"])
    P = {k: poptot(d, c) for k, c in dict(sex=c_sex, age=c_age, emp=c_emp, hrs=c_hrs, inc=c_inc, sa=c_sa, sae=c_sae).items()}
    out = []
    for rep in range(reps):
        inv = rng.multinomial(ninv, d.P.values)
        r = rng.binomial(inv, p).astype(float)
        ws = {}
        ws["M0"] = np.ones_like(r)
        ws["M1"] = poststrat(r, c_sa, P["sa"])
        ws["M2"] = rake(r, [c_sex, c_age, c_emp], [P["sex"], P["age"], P["emp"]])
        ws["M3"] = rake(r, [c_sex, c_age, c_emp, c_hrs, c_inc], [P["sex"], P["age"], P["emp"], P["hrs"], P["inc"]])
        m4 = poststrat(r, c_sae, P["sae"]); fb = m4 is None
        ws["M4"] = ws["M2"] if fb else m4
        ws["M2h"] = rake(r, [c_sex, c_age, c_emp, c_hrs], [P["sex"], P["age"], P["emp"], P["hrs"]])
        for m, w in ws.items():
            if w is None:
                w = rake(r, [c_sex, c_age], [P["sex"], P["age"]])
            est, deff, n = summarize(r, w, y)
            se = np.sqrt(deff * est * (1 - est) / n)
            out.append(dict(rep=rep, method=m, est=est, deff=deff, n=n, cover=int(abs(est - truth) <= 1.96 * se),
                            halfw=1.96 * se, tvd_inc=tvd(r, w, c_inc, P["inc"]), tvd_hrs=tvd(r, w, c_hrs, P["hrs"]),
                            fallback=int(fb and m == "M4")))
    o = pd.DataFrame(out); o["truth"] = truth; o["resp_rate"] = (d.P * p).sum()
    return o

def noise_tvd(d, n, reps, incvar="inc6", seed=SEED + 1):
    rng = np.random.default_rng(seed)
    c_inc, c_hrs = codes(d, [incvar, "hours"])
    pi, ph = poptot(d, c_inc), poptot(d, c_hrs)
    ti, th = [], []
    for _ in range(reps):
        r = rng.multinomial(n, d.P.values).astype(float)
        w = np.ones_like(r)
        ti.append(tvd(r, w, c_inc, pi)); th.append(tvd(r, w, c_hrs, ph))
    return float(np.quantile(ti, .95)), float(np.quantile(th, .95))

def agg(o):
    g = o.groupby("method")
    t = o.truth.iloc[0]
    s = pd.DataFrame(dict(mean_est=g.est.mean(), bias_pt=(g.est.mean() - t) * 100, sd_pt=g.est.std() * 100,
                          rmse_pt=g.est.apply(lambda v: np.sqrt(((v - t) ** 2).mean())) * 100, coverage=g.cover.mean(),
                          deff=g.deff.mean(), halfw_pt=g.halfw.mean() * 100, n=g.n.mean(), tvd_inc=g.tvd_inc.mean(),
                          tvd_hrs=g.tvd_hrs.mean(), fallback=g.fallback.mean()))
    s["truth_pct"] = t * 100; s["resp_rate"] = o.resp_rate.iloc[0]
    return s.reset_index()

if __name__ == "__main__":
    REPS = 500
    d22 = population(2022)
    truth = float((d22.P * d22.y).sum())
    main = []
    for sc in ["S1", "S2", "S3"]:
        a = agg(run(d22, sc, REPS)); a.insert(0, "scenario", sc); main.append(a)
        print(sc, "done", flush=True)
    A = pd.concat(main); A.to_csv(RES / "A_main.csv", index=False, float_format="%.6f")
    ti, th = noise_tvd(d22, 5000, 2000)
    # 頑健性
    rob = []
    def rr(tag, d, **kw):
        for sc in ["S2", "S3"]:
            a = agg(run(d, sc, 200, **kw)); a.insert(0, "scenario", sc); a.insert(0, "variant", tag); rob.append(a)
    rr("base200", d22)
    rr("R1_rate10", d22, rate=0.10); rr("R1_rate40", d22, rate=0.40)
    rr("R2_scale0.5", d22, scale=0.5); rr("R2_scale2", d22, scale=2.0)
    rr("R3_n2000", d22, n_resp=2000); rr("R3_n20000", d22, n_resp=20000)
    d17 = population(2017); rr("R4_2017", d17)
    rr("R5_inc4", d22, incvar="inc4")
    B = pd.concat(rob); B.to_csv(RES / "B_robust.csv", index=False, float_format="%.6f")
    print("robust done", flush=True)
    # 問い直し：δ を変えたときの M3 の偏りと区間の半幅
    tip = []
    for orr in [1.0, 1.1, 1.2, 1.3, 1.5, 1.75, 2.0, 2.5, 3.0]:
        o = run(d22, "S3", 300, delta=np.log(orr))
        a = agg(o); a.insert(0, "odds_ratio", orr); tip.append(a[a.method.isin(["M0", "M3", "M2h"])])
    C = pd.concat(tip); C.to_csv(RES / "C_tipping.csv", index=False, float_format="%.6f")
    # 仮説
    def g(sc, m, col):
        return float(A[(A.scenario == sc) & (A.method == m)][col].iloc[0])
    b0, b1, b3 = g("S2", "M0", "bias_pt"), g("S2", "M1", "bias_pt"), g("S2", "M3", "bias_pt")
    H = {}
    H["H1"] = dict(removed_share_M1=1 - abs(b1) / abs(b0), supported=bool(1 - abs(b1) / abs(b0) < 0.5))
    H["H2"] = dict(removed_share_M3=1 - abs(b3) / abs(b0), supported=bool(abs(b3) <= 0.1 * abs(b0)))
    H["H3"] = dict(bias_pt=g("S3", "M3", "bias_pt"), coverage=g("S3", "M3", "coverage"),
                   supported=bool(abs(g("S3", "M3", "bias_pt")) >= 2 and g("S3", "M3", "coverage") < 0.5))
    H["H4"] = dict(tvd_inc_M2h=g("S3", "M2h", "tvd_inc"), noise95_inc=ti, bias_pt_M2h=g("S3", "M2h", "bias_pt"),
                   supported=bool(g("S3", "M2h", "tvd_inc") < ti and abs(g("S3", "M2h", "bias_pt")) >= 2))
    H["H5"] = dict(deff_M3=g("S2", "M3", "deff"), supported=bool(g("S2", "M3", "deff") >= 1.3))
    js = dict(truth_pct=truth * 100, pop=float(d22.n.sum()), noise95_tvd_inc=ti, noise95_tvd_hrs=th, hypotheses=H,
              reps=REPS, seed=SEED)
    (RES / "main.json").write_text(json.dumps(js, ensure_ascii=False, indent=1))
    print(json.dumps(H, ensure_ascii=False, indent=1))
