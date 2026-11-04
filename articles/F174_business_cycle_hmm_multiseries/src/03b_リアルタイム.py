"""03b その時点までのデータだけで判定したらどうなるか（1995年1月〜2026年8月）

毎年1月に、その前の月までのデータ（1975年4月〜、CI は1985年4月〜）で推定し直し、
その年の各月は「その月までのデータだけ」を使う確率（前向きアルゴリズム）を記録する。
標準化の平均・標準偏差も推定し直す時点までのデータで決める。
確率が2か月続けて0.5を超えた月を「後退のサイン」、2か月続けて0.5を下回った月を「回復のサイン」とする。
使うのは今の時点の改定後のデータで、当時の速報値ではない（F35 と同じ制約）。
"""
import time
import numpy as np, pandas as pd
from common import DATA, RAW, RES, SEED, MAIN
from hmmtools import fit_best, recession_states, filtered_probs, months_between

t0 = time.time()
m = pd.read_csv(DATA / "monthly.csv", parse_dates=["month"]).set_index("month")
cyc = pd.read_csv(RAW / "cycle_dates.csv"); cyc["month"] = pd.to_datetime(cyc.month + "-01")
rec = m["rec"]

SPECS = {
    "multi7": dict(cols=[f"g3_{c}" for c in MAIN], start="1975-04-01", avg=False),
    "avg7": dict(cols=[f"g3_{c}" for c in MAIN], start="1975-04-01", avg=True),
    "ci": dict(cols=["g3_ci_coin"], start="1985-04-01", avg=False),
}
K, COV = 3, "full"
years = range(1995, 2027)
out = {}
for name, sp in SPECS.items():
    full = m[sp["cols"]].loc[sp["start"]:"2026-08-01"].dropna()
    probs, prev = [], None
    for y in years:
        train = full.loc[: f"{y - 1}-12-01"]
        mu, sd = train.mean(), train.std()
        def z(df):
            Z = (df - mu) / sd
            if sp["avg"]:
                Z = Z.mean(axis=1).to_frame("avg")
            return Z
        Zt = z(train)
        if sp["avg"]:
            a_mu, a_sd = Zt.mean(), Zt.std()
            Zt = (Zt - a_mu) / a_sd
        mod, ll = fit_best(Zt.values, K, cov=COV, n_init=10, seed=SEED + y, init_model=prev)
        prev = mod
        upto = full.loc[: f"{y}-12-01"]
        Zu = z(upto)
        if sp["avg"]:
            Zu = (Zu - a_mu) / a_sd
        fp = filtered_probs(mod, Zu.values)
        rs = recession_states(mod)
        p = pd.Series(fp[:, rs].sum(axis=1), index=Zu.index).loc[f"{y}-01-01":]
        probs.append(p)
    out[name] = pd.concat(probs)
    print(name, round(time.time() - t0))
P = pd.DataFrame(out)
P["rec"] = rec.reindex(P.index)
P.to_csv(RES / "realtime_probs.csv", float_format="%.4f")

def signal_episodes(p):
    """2か月続けて0.5を超えた月に始まり、2か月続けて0.5を下回った月に終わる区間"""
    on = (p > 0.5).astype(int).values
    eps, state, start = [], 0, None
    for i in range(1, len(on)):
        if state == 0 and on[i] and on[i - 1]:
            state, start = 1, p.index[i]
        elif state == 1 and not on[i] and not on[i - 1]:
            eps.append((start, p.index[i])); state = 0
    if state == 1:
        eps.append((start, None))      # 2026年8月の時点でまだ続いている
    return eps

rows, summ = [], []
peaks = cyc[(cyc.type == "peak") & (cyc.month >= "1995-01-01")].month.tolist()
troughs = cyc[(cyc.type == "trough") & (cyc.month >= "1995-01-01")].month.tolist()
END = P.index[-1]
for name in SPECS:
    eps = signal_episodes(P[name])
    used = set()
    for p in peaks:
        t = min(x for x in troughs if x > p)
        lo, hi = p + pd.DateOffset(months=1), t      # 公式の後退期と重なる区間を対応させる
        mt = [i for i, (a, b) in enumerate(eps) if a <= hi and (b or END) >= lo]
        used |= set(mt)
        if mt:
            a = eps[mt[0]][0]; b = eps[mt[-1]][1]
            rows.append(dict(model=name, peak=p.strftime("%Y-%m"), trough=t.strftime("%Y-%m"),
                             rec_signal=a.strftime("%Y-%m"), lag_peak=months_between(p, a),
                             rev_signal=b.strftime("%Y-%m") if b is not None else "続いている",
                             lag_trough=months_between(t, b) if b is not None else np.nan,
                             n_episodes=len(mt)))
        else:
            rows.append(dict(model=name, peak=p.strftime("%Y-%m"), trough=t.strftime("%Y-%m"),
                             rec_signal="", lag_peak=np.nan, rev_signal="", lag_trough=np.nan, n_episodes=0))
    false = [eps[i] for i in range(len(eps)) if i not in used]
    false_months = sum(months_between(a, b or END) for a, b in false)
    f = (P[name] > 0.5).astype(int); r = P["rec"]
    summ.append(dict(model=name, acc=(f == r).mean(), sens=f[r == 1].mean(), spec=1 - f[r == 0].mean(),
                     n_episodes=len(eps), n_false=len(false), false_months=false_months,
                     false_list=";".join(f"{a:%Y-%m}〜{(b.strftime('%Y-%m') if b is not None else '続いている')}" for a, b in false),
                     latest_prob=float(P[name].iloc[-1])))
pd.DataFrame(rows).to_csv(RES / "realtime_turning_points.csv", index=False)
pd.DataFrame(summ).to_csv(RES / "realtime_summary.csv", index=False, float_format="%.4f")
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 200)
print(pd.DataFrame(rows).to_string()); print(pd.DataFrame(summ).round(3).to_string())
print("done", round(time.time() - t0))
