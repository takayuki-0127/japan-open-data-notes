"""F112 03 分析：救急隊の「全部出払い」を待ち行列モデル（M/M/c・M/G/c）とシミュレーションで見る

前提（公表値）
- 救急自動車の出動件数 7,718,380件（令和6年）、人口 126,095,170人 → 1万人あたり年612.1件
- 不搬送 12.7%、入電〜医師引継ぎ（病院収容所要時間）平均44.6分と、その時間別の搬送人員（第37表）
- 入電時刻別（2時間ごと）・月別・曜日別の件数
前提（公表されていない＝仮定。結果は仮定を変えて並べる）
- 引継ぎ後に次の出動ができるまでの時間 R（帰署・資器材の補充など）：基準20分（10・30・40分）
- 不搬送の出動1件で隊がふさがる時間 N：基準30分（20・40分）
- 隊は24時間すべて出動できる。隣の本部からの応援は「待ち」とは別に数える
"""
import json, math, heapq
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats, optimize

ROOT = Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
SEED = 112

hourly = pd.read_csv(D / "hourly_transport_2h.csv")
monthly = pd.read_csv(D / "monthly_dispatch.csv")
weekday = pd.read_csv(D / "weekday_dispatch.csv")
hosp = pd.read_csv(D / "hospital_time_bins.csv")
size = pd.read_csv(D / "time_by_hq_size.csv")
trend = pd.read_csv(D / "national_trend.csv")
pref = pd.read_csv(D / "prefecture_teams_dispatch.csv")

DISP, POP, TEAMS = 7718380, 126095170, 5485
RATE = DISP / POP * 1e4              # 1万人あたり年間出動件数
P_NOTRANS = 980067 / DISP            # 不搬送の割合
H_MEAN = 44.6
out = {"rate_per_10k": RATE, "p_notrans": P_NOTRANS, "teams_per_100k": TEAMS / POP * 1e5}

# ---------------------------------------------------------------- 病院収容所要時間の分布（区間データに当てはめ）
edges = list(hosp.lo) + [np.inf]
cnt = hosp["搬送人員"].values


def nll(par, dist):
    if dist == "lognorm":
        mu, sg = par
        if sg <= 0: return 1e18
        F = stats.norm.cdf((np.log(np.maximum(edges, 1e-9)) - mu) / sg)
        F[0] = 0.0
    else:
        k, th = np.exp(par)
        F = stats.gamma.cdf(edges, k, scale=th)
    p = np.clip(np.diff(F), 1e-15, 1)
    return -(cnt * np.log(p)).sum()


fit_ln = optimize.minimize(nll, [np.log(40), 0.4], args=("lognorm",), method="Nelder-Mead").x
fit_ga = optimize.minimize(nll, [np.log(8), np.log(5)], args=("gamma",), method="Nelder-Mead").x
ln_mean = math.exp(fit_ln[0] + fit_ln[1] ** 2 / 2)
ga_k, ga_th = np.exp(fit_ga)
out["fit"] = {"lognorm_mu": fit_ln[0], "lognorm_sigma": fit_ln[1], "lognorm_mean": ln_mean, "lognorm_median": math.exp(fit_ln[0]),
              "gamma_k": ga_k, "gamma_theta": ga_th, "gamma_mean": ga_k * ga_th, "published_mean": H_MEAN}
# 公表平均 44.6分に合わせる（σ はそのまま、μ だけずらす）
MU44 = math.log(H_MEAN) - fit_ln[1] ** 2 / 2
SG = fit_ln[1]
# 当てはまりの確認（区間ごとの割合）
Fln = stats.norm.cdf((np.log(np.maximum(edges, 1e-9)) - fit_ln[0]) / SG); Fln[0] = 0
out["fit"]["bin_share_obs"] = list(np.round(cnt / cnt.sum(), 4))
out["fit"]["bin_share_lognorm"] = list(np.round(np.diff(Fln), 4))


def mean_busy(R=20, N=30, H=H_MEAN):
    """出動1件あたり隊がふさがる平均時間（分）"""
    return (1 - P_NOTRANS) * (H + R) + P_NOTRANS * N


# ---------------------------------------------------------------- Erlang の式
def erlang_b(c, a):
    b = 1.0
    for k in range(1, c + 1):
        b = a * b / (k + a * b)
    return b


def erlang_c(c, a):
    """呼が来たとき c 隊すべてがふさがっている確率（待ちがある M/M/c）。a=λS（アーラン）"""
    if a >= c: return 1.0
    b = erlang_b(c, a)
    return c * b / (c - a * (1 - b))


def wq_mean(c, a, S):
    """待つ呼の平均待ち時間（分）。M/M/c"""
    if a >= c: return np.inf
    return S / (c - a)


# ---------------------------------------------------------------- 時間による変動（2時間×月×曜日）
h_share = hourly["合計"].values / hourly["合計"].sum()            # 2時間ごとの割合
h_fac = h_share * 12                                              # 平均=1
days_in = np.array([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])  # 令和6年（うるう年）
m_fac = (monthly["出動件数"].values / days_in) / (DISP / 366)
w_fac = weekday["出動件数"].values / weekday["出動件数"].mean()
# 3つの係数をかけ合わせた「状態」の重み（各状態の時間の長さ）と強さ
states = []
for mi in range(12):
    for wi in range(7):
        for hi in range(12):
            states.append((days_in[mi] / 366 / 7 / 12, m_fac[mi] * w_fac[wi] * h_fac[hi], mi, wi, hi))
st_w = np.array([s[0] for s in states]); st_f = np.array([s[1] for s in states])
st_f = st_f / (st_w * st_f).sum()  # 時間で平均すると1
out["factor"] = {"hour_peak": float(h_fac.max()), "hour_low": float(h_fac.min()), "month_peak": float(m_fac.max()),
                 "month_low": float(m_fac.min()), "weekday_max": float(w_fac.max()), "weekday_min": float(w_fac.min()),
                 "combined_max": float(st_f.max()), "share_time_above_1_5": float(st_w[st_f > 1.5].sum())}


def psa(c, pop, S, fac=st_f, w=st_w):
    """時間帯ごとに定常とみなした近似（呼の重み付き平均）"""
    lam_min = RATE * pop / 1e4 / 366 / 1440       # 1分あたり
    a = lam_min * S * fac
    pc = np.array([erlang_c(c, x) for x in a])
    return float((w * fac * pc).sum() / (w * fac).sum())


def stationary(c, pop, S):
    lam_min = RATE * pop / 1e4 / 366 / 1440
    return erlang_c(c, lam_min * S)


S0 = mean_busy()
out["S_base_min"] = S0
POPS = [50000, 100000, 300000]
rows = []
for pop in POPS:
    for c in range(1, 26):
        a = RATE * pop / 1e4 / 366 / 1440 * S0
        if c < a: continue
        rows.append({"pop": pop, "c": c, "util": a / c, "stationary": stationary(c, pop, S0), "psa": psa(c, pop, S0),
                     "per_year_psa": psa(c, pop, S0) * RATE * pop / 1e4})
grid = pd.DataFrame(rows)
grid.to_csv(RES / "allbusy_by_teams.csv", index=False)

# ---- 時間帯別（10万人・4隊と5隊、平均時間 S0 と S0+10）
hour_rows = []
for c in [3, 4, 5, 6]:
    for dS in [0, 10]:
        for hi in range(12):
            msk = np.array([s[4] == hi for s in states])
            hour_rows.append({"c": c, "dS": dS, "hour_from": hi * 2, "p": psa(c, 100000, S0 + dS, st_f[msk], st_w[msk])})
pd.DataFrame(hour_rows).to_csv(RES / "allbusy_by_hour_100k.csv", index=False)

# ---- 「1隊増やす」と「平均時間が延びる」の釣り合い（10万人）
eq = []
for c in [3, 4, 5]:
    base = psa(c, 100000, S0)
    minus = psa(c - 1, 100000, S0) if c > 1 else np.nan
    plus = psa(c + 1, 100000, S0)
    # 1隊減らしたのと同じ確率になる平均時間の延び
    f = lambda d: psa(c, 100000, S0 + d) - minus
    d_eq = optimize.brentq(f, 0, 300) if minus > base else np.nan
    eq.append({"c": c, "p_base": base, "p_minus1": minus, "p_plus1": plus, "p_plus10min": psa(c, 100000, S0 + 10),
               "p_2019_hosp": psa(c, 100000, mean_busy(H=39.5)), "p_2022_hosp": psa(c, 100000, mean_busy(H=47.2)),
               "dS_equiv_minus1team": d_eq})
eqdf = pd.DataFrame(eq)
eqdf.to_csv(RES / "team_vs_time_100k.csv", index=False)

# ---------------------------------------------------------------- 全国の推移（隊1つあたりの負担と稼働率の目安）
tr = trend.copy()
tr["p_notrans_approx"] = 1 - tr["救急自動車_搬送人員"] / tr["救急自動車_出動件数"]
tr["per_team_per_day"] = tr["救急自動車_出動件数"] / tr["救急隊数_4月1日"] / 365
for R in [10, 20, 30]:
    S = (1 - tr.p_notrans_approx) * (tr["病院収容所要時間_分"] + R) + tr.p_notrans_approx * 30
    tr[f"util_R{R}"] = tr["救急自動車_出動件数"] * S / 60 / (tr["救急隊数_4月1日"] * 8760)
tr.to_csv(RES / "national_util_trend.csv", index=False)

# ---------------------------------------------------------------- 都道府県のばらつき（名前は出さない）
pf = pref.copy()
pf["per_team_per_day"] = pf["出動件数_R6"] / pf["救急隊数_R7"] / 366
pf["teams_per_100k"] = pf["救急隊数_R7"] / pf["人口"] * 1e5
pf["util_base"] = pf["出動件数_R6"] * S0 / 60 / (pf["救急隊数_R7"] * 8784)
pf[["per_team_per_day", "teams_per_100k", "util_base"]].describe().to_csv(RES / "prefecture_spread.csv")
out["pref"] = {"per_team_per_day_min": pf.per_team_per_day.min(), "per_team_per_day_med": pf.per_team_per_day.median(),
               "per_team_per_day_max": pf.per_team_per_day.max(), "util_min": pf.util_base.min(), "util_med": pf.util_base.median(),
               "util_max": pf.util_base.max(), "teams_per_100k_min": pf.teams_per_100k.min(), "teams_per_100k_max": pf.teams_per_100k.max(),
               "corr_teamsper100k_vs_util": float(np.corrcoef(pf.teams_per_100k, pf.util_base)[0, 1])}
pf[["per_team_per_day", "teams_per_100k", "util_base"]].to_csv(RES / "prefecture_values_anonymous.csv", index=False)

# ---------------------------------------------------------------- シミュレーション（時間変動つき M/G/c）
rng_master = np.random.default_rng(SEED)
DAYS = 366
dow0 = 0  # 令和6年1月1日は月曜


def make_intensity(cv_day, rng, years):
    """1分ごとではなく2時間ごとの強さ（1分あたりの到着率の倍率）を返す"""
    blocks = []
    for y in range(years):
        d = 0
        for mi in range(12):
            for _ in range(days_in[mi]):
                wi = (dow0 + d) % 7
                g = rng.gamma(1 / cv_day ** 2, cv_day ** 2) if cv_day > 0 else 1.0
                for hi in range(12):
                    blocks.append(m_fac[mi] * w_fac[wi] * h_fac[hi] * g)
                d += 1
    b = np.array(blocks)
    return b / b.mean()


def sample_busy(n, rng, dist, R, N):
    tr_ = rng.random(n) >= P_NOTRANS
    if dist == "lognorm":
        h = rng.lognormal(MU44, SG, n)
    elif dist == "gamma":
        h = rng.gamma(ga_k, H_MEAN / ga_k, n)
    elif dist == "lognorm_fit":
        h = rng.lognormal(fit_ln[0], SG, n)
    elif dist == "exp":
        return rng.exponential(mean_busy(R, N), n)
    elif dist == "const":
        h = np.full(n, H_MEAN)
    nt = rng.exponential(N, n)
    return np.where(tr_, h + R, nt)


def simulate(c, pop, years=10, dist="lognorm", R=20, N=30, cv_day=0.0, policy="queue", seed=0):
    """policy=queue：全部ふさがっていれば空くまで待つ／loss：応援に回る（自隊はふさがらない）"""
    rng = np.random.default_rng(seed)
    inten = make_intensity(cv_day, rng, years)
    lam_min = RATE * pop / 1e4 / 366 / 1440
    # 2時間ブロックごとにポアソン数→一様に配置
    nblk = len(inten)
    k = rng.poisson(lam_min * 120 * inten)
    t = np.repeat(np.arange(nblk) * 120.0, k) + rng.random(k.sum()) * 120
    t.sort()
    s = sample_busy(len(t), rng, dist, R, N)
    free = [0.0] * c  # 各隊が次に空く時刻
    heapq.heapify(free)
    n_all = 0; waits = []
    for ti, si in zip(t, s):
        f0 = free[0]
        if f0 > ti:
            n_all += 1
            if policy == "queue":
                w = f0 - ti
                waits.append(w)
                heapq.heapreplace(free, f0 + si)
            # loss：自隊はふさがらない
        else:
            heapq.heapreplace(free, ti + si)
    n = len(t)
    waits = np.array(waits) if waits else np.zeros(0)
    return {"n": n, "p_allbusy": n_all / n, "per_year": n_all / years,
            "wait_mean_if_wait": float(waits.mean()) if len(waits) else 0.0,
            "p_wait_gt10": float((waits > 10).sum() / n)}


def simulate_dayonly(c, pop, n_day, years=10, R=20, N=30, seed=0):
    """c 隊のうち n_day 隊は 8〜20時だけ出動できる場合（待ちあり）"""
    rng = np.random.default_rng(seed)
    inten = make_intensity(0.0, rng, years)
    lam_min = RATE * pop / 1e4 / 366 / 1440
    k = rng.poisson(lam_min * 120 * inten)
    t = np.repeat(np.arange(len(inten)) * 120.0, k) + rng.random(k.sum()) * 120
    t.sort()
    s = sample_busy(len(t), rng, "lognorm", R, N)
    free = np.zeros(c); is_day = np.array([i < n_day for i in range(c)])
    n_all = 0
    for ti, si in zip(t, s):
        tod = ti % 1440
        usable = np.ones(c, bool) if 480 <= tod < 1200 else ~is_day
        cand = np.where(usable)[0]
        j = cand[np.argmin(free[cand])]
        if free[j] > ti:
            n_all += 1
            free[j] = free[j] + si
        else:
            free[j] = ti + si
    return n_all / len(t)


sim_rows = []
base_cfg = dict(dist="lognorm", R=20, N=30, cv_day=0.0, policy="queue")
# 基準（10万人、3〜6隊）と、5万人・30万人
for pop, cs in [(100000, [3, 4, 5, 6]), (50000, [1, 2, 3, 4]), (300000, [8, 10, 12, 13, 14])]:
    for c in cs:
        r = simulate(c, pop, seed=1000 + c, **base_cfg)
        sim_rows.append({"scenario": "base", "pop": pop, "c": c, **r, "psa": psa(c, pop, S0), "stationary": stationary(c, pop, S0)})
# 仮定を変える（10万人、4隊と5隊）
variants = [
    ("dist=exp", dict(dist="exp")), ("dist=gamma", dict(dist="gamma")), ("dist=const", dict(dist="const")),
    ("dist=lognorm_fit(平均%.1f分)" % ln_mean, dict(dist="lognorm_fit")),
    ("R=10", dict(R=10)), ("R=30", dict(R=30)), ("R=40", dict(R=40)),
    ("N=20", dict(N=20)), ("N=40", dict(N=40)),
    ("cv_day=0.1", dict(cv_day=0.1)), ("cv_day=0.2", dict(cv_day=0.2)),
    ("policy=loss", dict(policy="loss")),
]
for name, kw in variants:
    cfg = {**base_cfg, **kw}
    for c in [4, 5]:
        r = simulate(c, 100000, seed=2000 + c, **cfg)
        Sv = mean_busy(cfg["R"], cfg["N"])
        sim_rows.append({"scenario": name, "pop": 100000, "c": c, **r, "psa": psa(c, 100000, Sv), "stationary": stationary(c, 100000, Sv)})
# 乱数を変えたくり返し（基準、10万人4隊・5隊）
for c in [4, 5]:
    ps = [simulate(c, 100000, seed=s, **base_cfg)["p_allbusy"] for s in range(3000, 3010)]
    out[f"seed_spread_c{c}"] = {"mean": float(np.mean(ps)), "min": float(np.min(ps)), "max": float(np.max(ps))}
# 日勤だけの隊がある場合（10万人・5隊のうち1隊が日中だけ）
for nd in [0, 1, 2]:
    sim_rows.append({"scenario": f"day_only={nd}", "pop": 100000, "c": 5, "p_allbusy": simulate_dayonly(5, 100000, nd, seed=4000 + nd)})
sim = pd.DataFrame(sim_rows)
sim.to_csv(RES / "simulation.csv", index=False)

out["grid_100k"] = grid[grid["pop"] == 100000].set_index("c")[["util", "psa", "stationary", "per_year_psa"]].round(5).to_dict("index")
out["eq_100k"] = eqdf.round(5).to_dict("records")
out["trend"] = tr[["year", "per_team_per_day", "util_R10", "util_R20", "util_R30"]].round(4).to_dict("records")
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["rate_per_10k", "p_notrans", "teams_per_100k", "S_base_min", "fit", "factor", "pref"]}, ensure_ascii=False, indent=1, default=float))
print(grid[grid["pop"] == 100000].round(4).to_string())
print(eqdf.round(4).to_string())
print(sim.round(4).to_string())
print(tr.round(3).to_string())
print({k: v for k, v in out.items() if k.startswith("seed_spread")})
