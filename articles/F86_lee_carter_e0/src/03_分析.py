"""Lee–Carter モデルで年齢別死亡率を当てはめ、平均寿命を予測する

log m(x,t) = a(x) + b(x) k(t)
- a: 当てはめ期間の log m の平均、b と k: 中心化した行列の特異値分解の第1成分（Σb=1, Σk=0）
- 2段目（Lee–Miller）: k(t) を、その年の平均寿命がJMDの値と一致するように推定し直す
- 予測: k はドリフト付きランダムウォーク。ドリフトの推定誤差も入れて 5,000 本シミュレーション
- 予測の出発点（ジャンプオフ）は、最後の年の実際の死亡率
"""
import json
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from common import DATA, RES, SEED, AGE_MAX, SEXES, e0_from_mx, e0_from_mx_age

NSIM = 5000
H_END = 2070


def mat(long, sex, y0, y1, amax=AGE_MAX):
    d = long[(long.sex == sex) & (long.year.between(y0, y1))]
    D = d.pivot(index="year", columns="age", values="deaths")
    E = d.pivot(index="year", columns="age", values="exposure")
    if amax < AGE_MAX:
        D2 = D.loc[:, :amax].copy(); D2[amax + 1] = D.loc[:, amax + 1:].sum(axis=1)
        E2 = E.loc[:, :amax].copy(); E2[amax + 1] = E.loc[:, amax + 1:].sum(axis=1)
        D, E = D2, E2
    M = (D / E).clip(lower=1e-7)
    return M, D, E


def fit_lc(M, adjust=True):
    L = np.log(M.values)
    a = L.mean(axis=0)
    U, s, Vt = np.linalg.svd(L - a, full_matrices=False)
    b = Vt[0]; k = U[:, 0] * s[0]
    sc = b.sum(); b = b / sc; k = k * sc
    expl = s[0] ** 2 / (s ** 2).sum()
    if adjust:
        k2 = []
        for i, y in enumerate(M.index):
            target = e0_from_mx(M.values[i])
            f = lambda kk: e0_from_mx(np.exp(a + b * kk)) - target
            k2.append(brentq(f, k[i] - 200, k[i] + 200))
        k = np.array(k2)
    return a, b, k, expl


def forecast(M, a, b, k, years, rng, nsim=NSIM, jump="actual"):
    T = len(k)
    dk = np.diff(k)
    drift = dk.mean(); sd = dk.std(ddof=1)
    h = np.arange(1, len(years) + 1)
    drift_sim = rng.normal(drift, sd / np.sqrt(T - 1), nsim)
    eps = rng.normal(0, sd, (nsim, len(h))).cumsum(axis=1)
    ks = drift_sim[:, None] * h[None, :] + eps            # k(T+h) - k(T)
    base = np.log(M.values[-1]) if jump == "actual" else a + b * k[-1]
    e0 = np.empty((nsim, len(h)))
    for i in range(nsim):
        for j in range(len(h)):
            e0[i, j] = e0_from_mx(np.exp(base + b * ks[i, j]))
    # 中心（ドリフトそのもの）
    cen = np.array([e0_from_mx(np.exp(base + b * drift * hh)) for hh in h])
    e65c = np.array([e0_from_mx_age(np.exp(base + b * drift * hh), 65) for hh in h])
    return e0, cen, e65c, drift, sd


def qtab(years, e0, cen):
    q = np.percentile(e0, [2.5, 10, 50, 90, 97.5], axis=0)
    return pd.DataFrame({"year": years, "center": cen, "p025": q[0], "p10": q[1], "p50": q[2],
                         "p90": q[3], "p975": q[4]})


def run(long, sex, y0, y1, rng, adjust=True, amax=AGE_MAX, jump="actual", nsim=NSIM, h_end=H_END):
    M, D, E = mat(long, sex, y0, y1, amax)
    a, b, k, expl = fit_lc(M, adjust)
    years = np.arange(y1 + 1, h_end + 1)
    e0, cen, e65, drift, sd = forecast(M, a, b, k, years, rng, nsim, jump)
    return dict(M=M, a=a, b=b, k=k, expl=expl, years=years, e0=e0, cen=cen, e65=e65, drift=drift, sd=sd,
                tab=qtab(years, e0, cen))


def main():
    long = pd.read_csv(DATA / "mx_long.csv")
    obs = pd.read_csv(DATA / "e0_jmd.csv").set_index("year")
    ipss = pd.read_csv(DATA / "ipss_e0.csv")
    rng = np.random.default_rng(SEED)
    summ = {}
    params, fc_rows, kt_rows = [], [], []
    for sex in SEXES:
        r = run(long, sex, 1970, 2024, rng)
        summ[f"{sex}_expl"] = round(float(r["expl"]), 4)
        summ[f"{sex}_drift"] = round(float(r["drift"]), 3)
        summ[f"{sex}_sd"] = round(float(r["sd"]), 3)
        for ag, (aa, bb) in enumerate(zip(r["a"], r["b"])):
            params.append((sex, ag, aa, bb))
        for y, kk in zip(r["M"].index, r["k"]):
            kt_rows.append((sex, y, kk))
        t = r["tab"].copy(); t["sex"] = sex; t["e65_center"] = r["e65"]
        fc_rows.append(t)
        for yy in [2045, 2050, 2070]:
            row = t[t.year == yy].iloc[0]
            summ[f"{sex}_{yy}"] = {k2: round(float(row[k2]), 2) for k2 in ["center", "p025", "p10", "p50", "p90", "p975"]}
            summ[f"{sex}_{yy}_e65"] = round(float(row["e65_center"]), 2)
            summ[f"{sex}_{yy}_P_above_ipss"] = None
        for yy in [2045, 2070]:
            ip = float(ipss.loc[ipss.year == yy, f"e0_{sex}"].iloc[0])
            j = list(r["years"]).index(yy)
            summ[f"{sex}_{yy}_ipss"] = ip
            summ[f"{sex}_{yy}_P_above_ipss"] = round(float((r["e0"][:, j] > ip).mean()), 3)
            summ[f"{sex}_{yy}_ipss_pctile"] = round(float((r["e0"][:, j] < ip).mean() * 100), 1)
        # 年あたりの延び（中心）
        summ[f"{sex}_gain_per_decade_2025_70"] = round(float((r["cen"][-1] - r["cen"][0]) / (len(r["cen"]) - 1) * 10), 2)
        summ[f"{sex}_obs_gain_per_decade_1970_2019"] = round(float((obs.loc[2019, sex] - obs.loc[1970, sex]) / 4.9), 2)
        summ[f"{sex}_obs_gain_per_decade_2010_2019"] = round(float((obs.loc[2019, sex] - obs.loc[2010, sex]) / 0.9), 2)
        summ[f"{sex}_e0_2024"] = float(obs.loc[2024, sex])
    pd.DataFrame(params, columns=["sex", "age", "a", "b"]).to_csv(RES / "lc_params.csv", index=False)
    pd.DataFrame(kt_rows, columns=["sex", "year", "k"]).to_csv(RES / "lc_kt.csv", index=False)
    pd.concat(fc_rows).to_csv(RES / "forecast_e0.csv", index=False)

    # バックテスト：過去の一時点までで当てはめ、その後の平均寿命と比べる
    bt = []
    for sex in SEXES:
        for y1 in [1989, 1994, 1999, 2004, 2009, 2014]:
            r = run(long, sex, 1970, y1, rng, nsim=2000, h_end=2024)
            for j, yy in enumerate(r["years"]):
                act = float(obs.loc[yy, sex])
                q = np.percentile(r["e0"][:, j], [2.5, 10, 90, 97.5])
                bt.append((sex, y1, yy, yy - y1, act, r["cen"][j], act - r["cen"][j],
                           q[1] <= act <= q[2], q[0] <= act <= q[3]))
    bt = pd.DataFrame(bt, columns=["sex", "fit_end", "year", "h", "actual", "center", "err", "in80", "in95"])
    bt.to_csv(RES / "backtest.csv", index=False)
    for sex in SEXES:
        s = bt[bt.sex == sex]
        summ[f"{sex}_bt_mean_err"] = round(float(s.err.mean()), 2)
        summ[f"{sex}_bt_err_h10"] = round(float(s[s.h == 10].err.mean()), 2)
        summ[f"{sex}_bt_err_h10_byend"] = {int(r.fit_end): round(float(r.err), 2) for r in s[s.h == 10].itertuples()}
        summ[f"{sex}_bt_err_h20"] = round(float(s[s.h == 20].err.mean()), 2) if (s.h == 20).any() else None
        summ[f"{sex}_bt_in80"] = round(float(s.in80.mean()), 3)
        summ[f"{sex}_bt_in95"] = round(float(s.in95.mean()), 3)
        summ[f"{sex}_bt_in95_ex2020"] = round(float(s[s.year < 2020].in95.mean()), 3)

    # b(x) の変化：前半と後半で別々に当てはめる
    bshift = []
    for sex in SEXES:
        for (y0, y1) in [(1970, 1994), (1995, 2019)]:
            M, _, _ = mat(long, sex, y0, y1)
            a, b, k, expl = fit_lc(M, adjust=False)
            for ag, bb in enumerate(b):
                bshift.append((sex, f"{y0}-{y1}", ag, bb))
    bshift = pd.DataFrame(bshift, columns=["sex", "period", "age", "b"])
    bshift.to_csv(RES / "b_by_period.csv", index=False)
    for sex in SEXES:
        for per in ["1970-1994", "1995-2019"]:
            s = bshift[(bshift.sex == sex) & (bshift.period == per)]
            summ[f"{sex}_bshare65plus_{per}"] = round(float(s[s.age >= 65].b.sum()), 3)

    # 頑健性
    rob = []
    settings = [("基本（1970〜2024年、0〜99歳＋100歳以上、2段目あり）", dict(y0=1970, y1=2024)),
                ("当てはめを1950年から", dict(y0=1950, y1=2024)),
                ("当てはめを1990年から", dict(y0=1990, y1=2024)),
                ("当てはめを2019年まで（コロナ前）", dict(y0=1970, y1=2019)),
                ("2段目（平均寿命に合わせる調整）なし", dict(y0=1970, y1=2024, adjust=False)),
                ("年齢を0〜89歳＋90歳以上", dict(y0=1970, y1=2024, amax=89)),
                ("出発点を当てはめ値にする", dict(y0=1970, y1=2024, jump="fitted"))]
    for name, kw in settings:
        for sex in SEXES:
            r = run(long, sex, kw.get("y0"), kw.get("y1"), rng, adjust=kw.get("adjust", True),
                    amax=kw.get("amax", AGE_MAX), jump=kw.get("jump", "actual"), nsim=2000)
            t = r["tab"].set_index("year")
            rob.append((name, sex, round(r["drift"], 3), round(t.loc[2045, "center"], 2), round(t.loc[2070, "center"], 2),
                        round(t.loc[2070, "p025"], 2), round(t.loc[2070, "p975"], 2)))
    rob = pd.DataFrame(rob, columns=["setting", "sex", "drift", "e0_2045", "e0_2070", "e0_2070_p025", "e0_2070_p975"])
    rob.to_csv(RES / "robustness.csv", index=False)
    summ["robust_2070_range"] = {sex: [float(rob[rob.sex == sex].e0_2070.min()), float(rob[rob.sex == sex].e0_2070.max())] for sex in SEXES}
    (RES / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    print(rob.to_string())


if __name__ == "__main__":
    main()
