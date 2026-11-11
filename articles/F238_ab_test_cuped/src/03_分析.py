"""03 分析：前の期間のデータ（共変量）で、A/B テストの推定のばらつきをどれだけ減らせるか。

A. 市区町村を単位にした模擬テスト（SSDSE の公開データ。効果は人工的に足す）
B. 架空のサービスのユーザー単位のシミュレーション（指標の種類・前の期間の長さ・新規ユーザーの割合）
C. 落とし穴：テスト中に測った値を共変量にすると、効果が消える
結果は results/ に書く。乱数の種は固定。
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
rng = np.random.default_rng(20261111)
Z = stats.norm.ppf(0.975)
Z80 = stats.norm.ppf(0.8)
OUT = {}
METHODS = ["naive", "diff", "cuped", "regadj", "strat"]


def estimators(y, x, t, strata=None):
    """y: 結果、x: 前の値、t: 0/1。差の推定と標準誤差を手法ごとに返す。"""
    res = {}
    y1, y0 = y[t == 1], y[t == 0]
    n1, n0 = len(y1), len(y0)
    # 1) 素の差
    res["naive"] = (y1.mean() - y0.mean(), np.sqrt(y1.var(ddof=1) / n1 + y0.var(ddof=1) / n0))
    # 2) 差の差（y−x、前の値をそのまま引く）
    d = y - x
    res["diff"] = (d[t == 1].mean() - d[t == 0].mean(),
                   np.sqrt(d[t == 1].var(ddof=1) / n1 + d[t == 0].var(ddof=1) / n0))
    # 3) CUPED（θ＝cov(y,x)/var(x) を両群まとめて推定）
    c = np.cov(y, x, ddof=1)
    theta = c[0, 1] / c[1, 1]
    ya = y - theta * (x - x.mean())
    res["cuped"] = (ya[t == 1].mean() - ya[t == 0].mean(),
                    np.sqrt(ya[t == 1].var(ddof=1) / n1 + ya[t == 0].var(ddof=1) / n0))
    # 4) 回帰調整（群ごとに傾き。Lin 2013 と同じ点推定）
    xm = x.mean()
    est, var = 0.0, 0.0
    for g, sgn in ((1, 1), (0, -1)):
        yy, xx = y[t == g], x[t == g]
        cg = np.cov(yy, xx, ddof=1)
        b = cg[0, 1] / cg[1, 1]
        adj = yy - b * (xx - xm)
        est += sgn * adj.mean()
        var += adj.var(ddof=1) / len(yy)
    res["regadj"] = (est, np.sqrt(var))
    # 5) 前の値の5分位で層別（事後層化）
    if strata is not None:
        est, var = 0.0, 0.0
        for s in np.unique(strata):
            m = strata == s
            w = m.mean()
            a, b_ = y[m & (t == 1)], y[m & (t == 0)]
            est += w * (a.mean() - b_.mean())
            var += w ** 2 * (a.var(ddof=1) / len(a) + b_.var(ddof=1) / len(b_))
        res["strat"] = (est, np.sqrt(var))
    return res


# ---------------------------------------------------------------- A. 市区町村
def run_geo(geo, metrics, reps, power_reps):
    rows, dist = [], {}
    for key, label in metrics:
        y0 = geo[key].to_numpy(float)
        x = geo[key + "_pre"].to_numpy(float)
        n = len(y0)
        rho = np.corrcoef(y0, x)[0, 1]
        q = np.asarray(pd.qcut(x, 5, labels=False))
        ests = {m: [] for m in METHODS}
        rej = {m: 0 for m in METHODS}
        for r in range(reps):
            t = np.zeros(n, int)
            t[rng.permutation(n)[: n // 2]] = 1
            for m, (e, se) in estimators(y0, x, t, q).items():
                ests[m].append(e)
                rej[m] += abs(e / se) > Z
        sd_naive = np.std(ests["naive"], ddof=1)
        delta = (Z + Z80) * sd_naive  # 素の差で検出力80%になる大きさ
        pw = {m: 0 for m in METHODS}
        pw_small = {m: 0 for m in METHODS}
        for r in range(power_reps):
            t = np.zeros(n, int)
            t[rng.permutation(n)[: n // 2]] = 1
            for dd, store in ((delta, pw), (delta / 2, pw_small)):
                for m, (e, se) in estimators(y0 + dd * t, x, t, q).items():
                    store[m] += abs(e / se) > Z
        for m in METHODS:
            sd = np.std(ests[m], ddof=1)
            rows.append(dict(metric=key, label=label, rho=rho, method=m, sd=sd,
                             var_ratio=(sd / sd_naive) ** 2, type1=rej[m] / reps,
                             power_full=pw[m] / power_reps, power_half=pw_small[m] / power_reps,
                             delta_pct_of_mean=delta / y0.mean() * 100, mean_y=y0.mean()))
        dist[key] = {m: np.array(v) for m, v in ests.items()}
    return pd.DataFrame(rows), dist


GEO_M = [("birth_rate", "出生率（人口千人あたり）"), ("log_emp_ratio", "従業者数÷人口（対数）"),
         ("aging", "高齢化率（%）"), ("births", "出生数（人）")]
geo = pd.read_csv(D / "geo_metrics.csv", dtype={"area_code": str})
A, distA = run_geo(geo, GEO_M, reps=4000, power_reps=1000)
A.to_csv(R / "A_geo_methods.csv", index=False)
np.savez_compressed(R / "A_geo_dist.npz", **{f"{k}__{m}": v for k, d_ in distA.items() for m, v in d_.items()})
OUT["A_n"] = len(geo)
OUT["A"] = {k: {r.method: dict(rho=round(r.rho, 3), var_ratio=round(r.var_ratio, 3), type1=round(r.type1, 4),
                               power_full=round(r.power_full, 3), power_half=round(r.power_half, 3),
                               delta_pct=round(r.delta_pct_of_mean, 2))
                for r in A[A.metric == k].itertuples()} for k, _ in GEO_M}

# 頑健性：避難指示区域の12市町村も入れる／対数をとらない従業者比
geo_all = pd.read_csv(D / "geo_metrics_all.csv", dtype={"area_code": str})
A2, _ = run_geo(geo_all, [("birth_rate", "出生率（全市区町村）"), ("emp_ratio", "従業者数÷人口（全・対数なし）")], 2000, 400)
A3, _ = run_geo(geo, [("emp_ratio", "従業者数÷人口（対数なし）")], 2000, 400)
AR = pd.concat([A2.assign(frame="all"), A3.assign(frame="main")])
AR.to_csv(R / "A_geo_robust.csv", index=False)
OUT["A_robust"] = {f"{r.frame}:{r.metric}:{r.method}": dict(rho=round(r.rho, 3), var_ratio=round(r.var_ratio, 3),
                                                            type1=round(r.type1, 3)) for r in AR.itertuples()}

# ---------------------------------------------------------------- B. 架空のサービス
# 1人ごとの「使いやすさ」λ をガンマ分布で置き、週ごとの回数をポアソンで引く。金額は1回ごとに対数正規。
# 値はすべて置いた値（実在のサービスではない）。テストの期間は2週間。
SCEN = {
    "purchase_revenue": dict(label="まれに買う：1人あたり購入金額", K=0.35, SCALE=0.12, money=True),
    "purchase_count": dict(label="まれに買う：1人あたり購入回数", K=0.35, SCALE=0.12, money=False),
    "visits": dict(label="よく来る：1人あたり訪問回数", K=1.5, SCALE=2.0, money=False),
}
MU, SIG = np.log(5000) - 0.5 * 0.9 ** 2, 0.9   # 1回の金額の平均 約5,000円
TEST_W = 2


def spend(lam, weeks, money, rng):
    cnt = rng.poisson(lam * weeks)
    if not money:
        return cnt.astype(float)
    tot = np.zeros(len(lam))
    m = cnt > 0
    c = cnt[m]
    draws = rng.lognormal(MU, SIG, c.sum())
    tot[m] = np.add.reduceat(draws, np.r_[0, np.cumsum(c)[:-1]])
    return tot


NB = 400_000
rowsB, POP = [], {}
for sk, sc in SCEN.items():
    lam = rng.gamma(sc["K"], sc["SCALE"], NB)
    y = spend(lam, TEST_W, sc["money"], rng)
    POP[sk] = dict(lam=lam, y=y)
    for pre_w in [1, 2, 4, 8, 13, 26]:
        x = spend(lam, pre_w, sc["money"], rng)
        rho = np.corrcoef(y, x)[0, 1]
        rowsB.append(dict(scenario=sk, label=sc["label"], pre_weeks=pre_w, rho=rho, var_ratio=1 - rho ** 2,
                          mean_y=y.mean(), cv=y.std() / y.mean()))
        if pre_w == 4:
            POP[sk]["x4"] = x
B = pd.DataFrame(rowsB)
B.to_csv(R / "B_pre_length.csv", index=False)
OUT["B_pre"] = {f"{r.scenario}:{r.pre_weeks}w": dict(rho=round(r.rho, 3), var_ratio=round(r.var_ratio, 3)) for r in B.itertuples()}
OUT["B_meta"] = {sk: dict(mean=round(float(POP[sk]["y"].mean()), 3), cv=round(float(POP[sk]["y"].std() / POP[sk]["y"].mean()), 2),
                          share_zero=round(float((POP[sk]["y"] == 0).mean()), 3)) for sk in SCEN}

# 金額の指標：前の期間の「回数」も使う／ウィンザー化（上位1%を切る）と組み合わせる
pr = POP["purchase_revenue"]
y, x4 = pr["y"], pr["x4"]
xc4 = spend(pr["lam"], 4, False, rng)  # 同じ人の前4週の回数（金額とは別に引き直した近似）
X = np.c_[np.ones(NB), x4, xc4]
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
vr_multi = (y - X @ beta).var() / y.var()
cap_y, cap_x = np.quantile(y, 0.99), np.quantile(x4, 0.99)
yw, xw = np.minimum(y, cap_y), np.minimum(x4, cap_x)
W = dict(vr_cuped_raw=1 - np.corrcoef(y, x4)[0, 1] ** 2, vr_multi=vr_multi,
         vr_wins_only=yw.var() / y.var(), rho_wins=np.corrcoef(yw, xw)[0, 1])
W["vr_wins_cuped"] = W["vr_wins_only"] * (1 - W["rho_wins"] ** 2)
OUT["B_revenue"] = {k: round(float(v), 4) for k, v in W.items()}

# 新規ユーザー（前の期間のデータがない人）の割合：訪問回数、前4週
vv = POP["visits"]
rowsN = []
for s in [0, 0.2, 0.4, 0.6, 0.8]:
    new = rng.random(NB) < s
    x = np.where(new, 0.0, vv["x4"])
    X = np.c_[np.ones(NB), x, new.astype(float)]
    beta, *_ = np.linalg.lstsq(X, vv["y"], rcond=None)
    vr = (vv["y"] - X @ beta).var() / vv["y"].var()
    rho_old = np.corrcoef(vv["y"][~new], vv["x4"][~new])[0, 1]
    rowsN.append(dict(new_share=s, var_ratio=vr, approx=1 - (1 - s) * rho_old ** 2))
Nn = pd.DataFrame(rowsN)
Nn.to_csv(R / "B_new_users.csv", index=False)
OUT["B_new"] = {f"{r.new_share:.1f}": dict(var_ratio=round(r.var_ratio, 3), approx=round(r.approx, 3)) for r in Nn.itertuples()}

# 日数の例：1日の訪問者 5,000人（2群合計）、両側5%・検出力80%
def need_n(sk, rel, vr):
    yy = POP[sk]["y"]
    return 2 * (Z + Z80) ** 2 * yy.var() * vr / (rel * yy.mean()) ** 2
vr_of = lambda sk, w: float(B.query("scenario==@sk and pre_weeks==@w").var_ratio.iloc[0])
ex = []
for sk, rel in [("visits", 0.02), ("visits", 0.05), ("purchase_revenue", 0.05), ("purchase_revenue", 0.10)]:
    opts = [("素の差", 1.0), ("CUPED（前4週）", vr_of(sk, 4)), ("CUPED（前13週）", vr_of(sk, 13))]
    if sk == "purchase_revenue":
        opts.append(("ウィンザー化＋CUPED（前4週）", W["vr_wins_cuped"]))
    for lab, vr in opts:
        n = need_n(sk, rel, vr)
        ex.append(dict(scenario=sk, mde=rel, method=lab, var_ratio=vr, n_per_arm=n, days=int(np.ceil(2 * n / 5000))))
EX = pd.DataFrame(ex)
EX.to_csv(R / "B_days_example.csv", index=False)
OUT["B_days"] = [dict(s=r.scenario, mde=r.mde, method=r.method, vr=round(r.var_ratio, 3), n=int(r.n_per_arm), days=r.days) for r in EX.itertuples()]

# 有限の標本で：第1種の誤りと検出力（訪問回数、1群 3,000人、前4週、効果 +3%）
reps, n, eff = 2000, 3000, 0.03
cnt0 = {m: 0 for m in ["naive", "diff", "cuped", "regadj"]}
cnt1 = dict(cnt0)
sc = SCEN["visits"]
for r in range(reps):
    lam = rng.gamma(sc["K"], sc["SCALE"], 2 * n)
    pre = spend(lam, 4, False, rng)
    t = np.zeros(2 * n, int); t[rng.permutation(2 * n)[:n]] = 1
    post0 = spend(lam, TEST_W, False, rng)
    post1 = spend(lam * np.where(t == 1, 1 + eff, 1.0), TEST_W, False, rng)
    for y_, store in ((post0, cnt0), (post1, cnt1)):
        for m, (e, se) in estimators(y_, pre, t).items():
            store[m] += abs(e / se) > Z
OUT["B_finite"] = dict(n_per_arm=n, reps=reps, effect=eff, type1={m: cnt0[m] / reps for m in cnt0},
                       power={m: cnt1[m] / reps for m in cnt1})

# θ をテストの前のデータだけで決めても同じか（訪問回数）
lam = rng.gamma(sc["K"], sc["SCALE"], 2 * n)
a = spend(lam, 4, False, rng); b = spend(lam, TEST_W, False, rng)        # テストの前の2つの期間
theta_hist = np.cov(b, a)[0, 1] / np.var(a, ddof=1)
pre = spend(lam, 4, False, rng); post = spend(lam, TEST_W, False, rng)
theta_in = np.cov(post, pre)[0, 1] / np.var(pre, ddof=1)
vr_t = lambda th: np.var(post - th * pre, ddof=1) / np.var(post, ddof=1)
OUT["B_theta"] = dict(theta_hist=round(theta_hist, 4), theta_in=round(theta_in, 4),
                      vr_hist=round(vr_t(theta_hist), 4), vr_in=round(vr_t(theta_in), 4))

# サンプル1回分（SQL の検算用）：訪問回数、1群 3,000人、効果 +3%
lam = rng.gamma(sc["K"], sc["SCALE"], 2 * n)
pre = spend(lam, 4, False, rng)
t = np.zeros(2 * n, int); t[rng.permutation(2 * n)[:n]] = 1
post = spend(lam * np.where(t == 1, 1 + eff, 1.0), TEST_W, False, rng)
sim = pd.DataFrame(dict(user_id=np.arange(1, 2 * n + 1), arm=np.where(t == 1, "B", "A"),
                        pre_visits=pre.astype(int), visits=post.astype(int)))
sim.to_csv(D / "sim_users.csv.gz", index=False)
res = estimators(sim.visits.to_numpy(float), sim.pre_visits.to_numpy(float), (sim.arm == "B").to_numpy().astype(int))
OUT["B_sample"] = {m: dict(est=round(e, 4), se=round(se, 4), z=round(e / se, 2)) for m, (e, se) in res.items()}

# ---------------------------------------------------------------- C. 落とし穴：テスト中の値を共変量にする
# 新しい画面（B）は「訪問回数」を増やし、それを通じて購入金額も増える、と置く。
sc = SCEN["purchase_revenue"]
rowsC = []
n = 20_000
for r in range(800):
    lam = rng.gamma(sc["K"], sc["SCALE"], 2 * n)
    t = np.zeros(2 * n, int); t[rng.permutation(2 * n)[:n]] = 1
    pre = spend(lam, 4, True, rng)
    lam_t = lam * np.where(t == 1, 1.10, 1.0)          # 効果：買いやすさ +10%
    visits = rng.poisson(lam_t * TEST_W * 6).astype(float)  # テスト中の訪問回数（効果を受ける）
    post = spend(lam_t, TEST_W, True, rng)
    true = 0.10 * post[t == 0].mean()
    rowsC.append(dict(true=true, naive=estimators(post, pre, t)["naive"][0],
                      cuped_pre=estimators(post, pre, t)["cuped"][0],
                      cuped_during=estimators(post, visits, t)["cuped"][0]))
C = pd.DataFrame(rowsC)
C.to_csv(R / "C_post_treatment.csv", index=False)
OUT["C_mean_ratio"] = {c: round(float((C[c] / C.true).mean()), 3) for c in ["naive", "cuped_pre", "cuped_during"]}
OUT["C_median_ratio"] = {c: round(float((C[c] / C.true).median()), 3) for c in ["naive", "cuped_pre", "cuped_during"]}

json.dump(OUT, open(R / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(OUT, ensure_ascii=False, indent=1, default=float))
