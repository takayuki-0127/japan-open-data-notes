"""03 分析：「100年に1度の大雨」は本当に100年に1度なのか。

1. 地点ごとに GEV（一般化極値分布）を年最大日降水量に当てはめ、100年再現レベルを出す（最尤法・L積率法）。
2. 前半（1901〜1960）で決めた「100年に1度」の値を、後半（1961〜2025）に何回超えたかを数える。
   - 単純な期待値は「年数 × 1%」。
   - ただし60年分から推定した値そのものが揺れるので、気候が変わらなくても超える回数は増える。
     これを、地点ごとの GEV から乱数でつくった「気候が変わらない世界」で同じ手順をくり返して求め、比べる。
3. 30年ごとに区切って当てはめ、100年再現レベルが年代でどう変わったかを見る（地域でまとめる指標洪水法も）。
4. 頑健性：前半・後半の区切り、学習の長さ、推定法、地点を1つずつ抜く、場所を移した可能性のある地点を除く。
   月最大の表があれば、GPD（しきい値3通り）とブロックの長さ（半年・1年・2年）も（05_月最大.py）。
"""
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.special import gamma

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
SEED = 167
RNG = np.random.default_rng(SEED)


# ---------- GEV（scipy の c は形状パラメータ ξ の符号を反転したもの） ----------
def _nll(th, x):
    c, loc, lsc = th
    sc = math.exp(lsc)
    z = (x - loc) / sc
    if abs(c) < 1e-6:
        return len(x) * lsc + np.sum(z) + np.sum(np.exp(-z))
    t = 1 - c * z  # scipy の向き（c = -ξ）
    if np.any(t <= 0):
        return 1e10
    return len(x) * lsc + (1 - 1 / c) * np.sum(np.log(t)) + np.sum(t ** (1 / c))


def fit_mle(x):
    """最尤法。L積率法の値を始点に Nelder-Mead で対数尤度を最大にする（scipy の汎用 fit と同じ解で、速い）。"""
    x = np.asarray(x, float)
    k, xi, a = fit_lmom(x)
    k = float(np.clip(k, -0.45, 0.45))
    r = optimize.minimize(_nll, [k, xi, math.log(a)], args=(x,), method="Nelder-Mead",
                          options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
    c, loc, lsc = r.x
    return c, loc, math.exp(lsc)


def fit_lmom(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    i = np.arange(1, n + 1)
    b0 = x.mean()
    b1 = np.sum((i - 1) / (n - 1) * x) / n
    b2 = np.sum((i - 1) * (i - 2) / ((n - 1) * (n - 2)) * x) / n
    l1, l2, l3 = b0, 2 * b1 - b0, 6 * b2 - 6 * b1 + b0
    t3 = l3 / l2
    z = 2 / (3 + t3) - math.log(2) / math.log(3)
    k = 7.8590 * z + 2.9554 * z ** 2
    a = l2 * k / ((1 - 2 ** (-k)) * gamma(1 + k))
    xi = l1 - a * (1 - gamma(1 + k)) / k
    return k, xi, a  # Hosking の k は scipy の c と同じ向き


def rl(params, T):
    c, loc, sc = params
    return stats.genextreme.ppf(1 - 1 / T, c, loc=loc, scale=sc)


FIT = {"mle": fit_mle, "lmom": fit_lmom}


def load():
    a = pd.read_csv(D / "annual_max.csv")
    return {s: g.set_index("year")["amax"] for s, g in a.groupby("station")}


# ---------- 2. 前半で決めて後半で数える ----------
def split_count(series, train, test, method="mle", T=100, min_train=0.9, min_test=0.9):
    rows = []
    for s, x in series.items():
        tr = x[(x.index >= train[0]) & (x.index <= train[1])]
        te = x[(x.index >= test[0]) & (x.index <= test[1])]
        if len(tr) < min_train * (train[1] - train[0] + 1) or len(te) < min_test * (test[1] - test[0] + 1):
            continue
        p = FIT[method](tr.values)
        thr = rl(p, T)
        rows.append({"station": s, "n_train": len(tr), "n_test": len(te), "rl": thr,
                     "exceed": int((te > thr).sum()), "xi": -p[0]})
    return pd.DataFrame(rows)


def sim_baseline(series, train, test, method="mle", T=100, reps=200):
    """気候が変わらない世界：地点ごとに全期間の GEV から年最大をつくり、同じ手順で超えた回数を数える。"""
    tot_exp, tot_years = 0.0, 0
    per = []
    for s, x in series.items():
        tr = x[(x.index >= train[0]) & (x.index <= train[1])]
        te = x[(x.index >= test[0]) & (x.index <= test[1])]
        if len(tr) < 0.9 * (train[1] - train[0] + 1) or len(te) < 0.9 * (test[1] - test[0] + 1):
            continue
        p = fit_mle(x.values)
        c, loc, sc = p
        cnt = []
        for _ in range(reps):
            ytr = stats.genextreme.rvs(c, loc=loc, scale=sc, size=len(tr), random_state=RNG)
            yte = stats.genextreme.rvs(c, loc=loc, scale=sc, size=len(te), random_state=RNG)
            q = FIT[method](ytr)
            cnt.append(np.sum(yte > rl(q, T)))
        per.append({"station": s, "mean_exceed": float(np.mean(cnt)), "n_test": len(te)})
    return pd.DataFrame(per)


def pois_p(obs, exp):
    # 両側：観測が期待より多いか少ないか（ポアソン）
    lo = stats.poisson.cdf(obs, exp)
    hi = stats.poisson.sf(obs - 1, exp)
    return float(min(1, 2 * min(lo, hi)))


def main():
    S = load()
    out = {}

    # 1. 全期間の当てはめ
    full = []
    for s, x in S.items():
        pm, pl = fit_mle(x.values), fit_lmom(x.values)
        # 100年値の95%区間（パラメトリック・ブートストラップ200回）
        bs = []
        for _ in range(200):
            y = stats.genextreme.rvs(*pm, size=len(x), random_state=RNG)
            bs.append(rl(fit_mle(y), 100))
        rec = x.max()
        rp = 1 / stats.genextreme.sf(rec, *pm)
        full.append({"station": s, "n": len(x), "first": int(x.index.min()), "xi_mle": -pm[0],
                     "rl100_mle": rl(pm, 100), "rl100_lo": np.percentile(bs, 2.5), "rl100_hi": np.percentile(bs, 97.5),
                     "rl100_lmom": rl(pl, 100), "rl10_mle": rl(pm, 10), "record": rec,
                     "record_year": int(x.idxmax()), "record_return_period": rp})
    full = pd.DataFrame(full).sort_values("station")
    full.to_csv(R / "gev_full_period.csv", index=False)
    full["ci_width_ratio"] = (full.rl100_hi - full.rl100_lo) / full.rl100_mle
    out["full"] = {
        "stations": len(full),
        "xi_median": float(full.xi_mle.median()),
        "xi_pos_share": float((full.xi_mle > 0).mean()),
        "ci_width_ratio_median": float(full.ci_width_ratio.median()),
        "record_rp_median": float(full.record_return_period.median()),
        "record_rp_over100": int((full.record_return_period > 100).sum()),
        "records_after_1961": int((full.record_year >= 1961).sum()),
        "rl100_mle_lmom_diff_median_pct": float(((full.rl100_lmom / full.rl100_mle - 1) * 100).median()),
    }

    # 2. 前半で決めて後半で数える（主分析）
    main_split = split_count(S, (1901, 1960), (1961, 2025))
    main_split.to_csv(R / "split_1901_1960_to_1961_2025.csv", index=False)
    base = sim_baseline(S, (1901, 1960), (1961, 2025))
    base.to_csv(R / "baseline_stationary_sim.csv", index=False)
    obs = int(main_split.exceed.sum())
    naive = float(main_split.n_test.sum() * 0.01)
    simexp = float(base.mean_exceed.sum())
    out["main"] = {"stations": len(main_split), "station_years": int(main_split.n_test.sum()),
                   "observed": obs, "naive_expected": naive, "stationary_expected": simexp,
                   "p_vs_naive": pois_p(obs, naive), "p_vs_stationary": pois_p(obs, simexp),
                   "stations_with_exceed": int((main_split.exceed > 0).sum()),
                   "max_exceed_station": int(main_split.exceed.max())}
    # 後半で決めて前半で数える（逆向き）
    rev = split_count(S, (1961, 2025), (1901, 1960))
    rev_base = sim_baseline(S, (1961, 2025), (1901, 1960), reps=100)
    out["reverse"] = {"stations": len(rev), "observed": int(rev.exceed.sum()),
                      "naive_expected": float(rev.n_test.sum() * 0.01),
                      "stationary_expected": float(rev_base.mean_exceed.sum()),
                      "p_vs_stationary": pois_p(int(rev.exceed.sum()), float(rev_base.mean_exceed.sum()))}

    # 頑健性：区切り・学習の長さ・推定法・再現期間
    rob = []
    settings = [
        ("主分析 1901-60→1961-2025 最尤", (1901, 1960), (1961, 2025), "mle", 100),
        ("推定法 L積率", (1901, 1960), (1961, 2025), "lmom", 100),
        ("区切り 1901-50→1951-2025", (1901, 1950), (1951, 2025), "mle", 100),
        ("区切り 1901-70→1971-2025", (1901, 1970), (1971, 2025), "mle", 100),
        ("学習30年 1931-60→1961-2025", (1931, 1960), (1961, 2025), "mle", 100),
        ("学習30年 1961-90→1991-2025", (1961, 1990), (1991, 2025), "mle", 100),
        ("学習90年 1901-90→1991-2025", (1901, 1990), (1991, 2025), "mle", 100),
        ("50年に1度 1901-60→1961-2025", (1901, 1960), (1961, 2025), "mle", 50),
        ("20年に1度 1901-60→1961-2025", (1901, 1960), (1961, 2025), "mle", 20),
    ]
    for name, tr, te, m, T in settings:
        sc = split_count(S, tr, te, method=m, T=T)
        reps = 100 if name != settings[0][0] else 200
        bb = sim_baseline(S, tr, te, method=m, T=T, reps=reps) if name != settings[0][0] else base
        o, ne, se = int(sc.exceed.sum()), float(sc.n_test.sum() / T), float(bb.mean_exceed.sum())
        rob.append({"setting": name, "stations": len(sc), "station_years": int(sc.n_test.sum()),
                    "observed": o, "naive_expected": round(ne, 2), "stationary_expected": round(se, 2),
                    "ratio_obs_stationary": round(o / se, 2) if se else None,
                    "p_vs_stationary": round(pois_p(o, se), 3), "p_vs_naive": round(pois_p(o, ne), 3)})
    rob = pd.DataFrame(rob)
    rob.to_csv(R / "robustness_split.csv", index=False)

    # 地点を1つずつ抜く（主分析）
    loo = []
    for s in main_split.station:
        o = int(main_split[main_split.station != s].exceed.sum())
        e = float(base[base.station != s].mean_exceed.sum())
        loo.append({"drop": s, "observed": o, "stationary_expected": e, "ratio": o / e})
    loo = pd.DataFrame(loo)
    loo.to_csv(R / "leave_one_station_out.csv", index=False)
    out["loo"] = {"ratio_min": float(loo.ratio.min()), "ratio_max": float(loo.ratio.max())}
    # 観測場所を移したことが知られる東京（2014年 大手町→北の丸公園）を除く
    no_tokyo = main_split[main_split.station != "東京"]
    out["no_tokyo"] = {"observed": int(no_tokyo.exceed.sum()),
                       "stationary_expected": float(base[base.station != "東京"].mean_exceed.sum())}

    # 3. 30年ごとの100年再現レベル
    win = [(1901, 1930), (1931, 1960), (1961, 1990), (1991, 2020)]
    wrows = []
    for s, x in S.items():
        for a, b in win:
            w = x[(x.index >= a) & (x.index <= b)]
            if len(w) < 27:
                continue
            pm = fit_mle(w.values)
            wrows.append({"station": s, "window": f"{a}-{b}", "n": len(w), "median": float(w.median()),
                          "rl100_mle": rl(pm, 100), "rl100_lmom": rl(fit_lmom(w.values), 100),
                          "rl10_mle": rl(pm, 10), "xi": -pm[0]})
    wr = pd.DataFrame(wrows)
    wr.to_csv(R / "gev_by_30yr_window.csv", index=False)
    piv = wr.pivot(index="station", columns="window", values="rl100_mle")
    piv_l = wr.pivot(index="station", columns="window", values="rl100_lmom")
    piv10 = wr.pivot(index="station", columns="window", values="rl10_mle")
    pivm = wr.pivot(index="station", columns="window", values="median")
    allw = piv.dropna()
    ratio = allw["1991-2020"] / allw["1901-1930"]
    ratio_l = (piv_l.dropna()["1991-2020"] / piv_l.dropna()["1901-1930"])
    ratio10 = (piv10.dropna()["1991-2020"] / piv10.dropna()["1901-1930"])
    ratiom = (pivm.dropna()["1991-2020"] / pivm.dropna()["1901-1930"])
    out["windows"] = {"stations_all4": int(len(allw)),
                      "rl100_ratio_median": float(ratio.median()),
                      "rl100_ratio_up_share": float((ratio > 1).mean()),
                      "rl100_ratio_q": [float(ratio.quantile(q)) for q in (0.25, 0.75)],
                      "rl100_ratio_lmom_median": float(ratio_l.median()),
                      "rl10_ratio_median": float(ratio10.median()),
                      "median_ratio_median": float(ratiom.median()),
                      "sign_test_p": float(stats.binomtest(int((ratio > 1).sum()), len(ratio)).pvalue)}

    # 地域でまとめる（指標洪水法）：各地点の年最大を、その地点の全期間の中央値で割ってから30年ごとに束ねる
    idx = []
    for s, x in S.items():
        idx.append(pd.DataFrame({"year": x.index, "y": x.values / x.median(), "station": s}))
    idx = pd.concat(idx)
    reg = []
    for a, b in win:
        w = idx[(idx.year >= a) & (idx.year <= b)]
        p = fit_lmom(w.y.values)
        g100 = rl(p, 100)
        # 年ごとにまとめて抜き出すブートストラップ（同じ年の地点間の相関を残す）
        yrs = np.arange(a, b + 1)
        bs = []
        for _ in range(300):
            pick = RNG.choice(yrs, size=len(yrs), replace=True)
            ww = pd.concat([w[w.year == y] for y in pick])
            bs.append(rl(fit_lmom(ww.y.values), 100))
        reg.append({"window": f"{a}-{b}", "n": len(w), "growth100": g100,
                    "lo": np.percentile(bs, 2.5), "hi": np.percentile(bs, 97.5),
                    "exceed_share_over_2x_median": float((w.y > 2).mean())})
    reg = pd.DataFrame(reg)
    reg.to_csv(R / "regional_growth_curve_by_window.csv", index=False)
    out["regional"] = reg.round(3).to_dict(orient="records")

    # 後半の年に、前半基準の100年値を超えた年の一覧
    ex = []
    for _, r in main_split.iterrows():
        x = S[r.station]
        for y, v in x[(x.index >= 1961) & (x.index > 0)].items():
            if v > r.rl:
                ex.append({"station": r.station, "year": int(y), "amax": v, "rl100_1901_1960": round(r.rl, 1)})
    ex = pd.DataFrame(ex).sort_values("year")
    ex.to_csv(R / "exceedances_after_1961.csv", index=False)
    out["exceed_by_decade"] = ex.groupby(ex.year // 10 * 10).size().to_dict() if len(ex) else {}
    out["exceed_by_decade"] = {int(k): int(v) for k, v in out["exceed_by_decade"].items()}

    out["robustness"] = rob.to_dict(orient="records")
    (R / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
