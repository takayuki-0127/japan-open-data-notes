"""03c 元記事 020「失業率は何か月先まで予測できるか？（SARIMA・128回のローリング評価）」を今の手順で作り直す。
元の手順：次数を2014年までの AIC で固定、比べる相手は単純な2つ、コロナ期を除いた平均絶対誤差。
今の手順：①比べる相手に季節ナイーブ・ETS を足す ②Diebold–Mariano 検定（HAC）で差を確かめる ③コロナ期を除かない・期間を分ける
④予測区間の当たり方（80%・95%）⑤次数を毎年選び直す。"""
from common import *
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from scipy import stats
import itertools, time

y = load_unemp()
ORDER, SORDER = (2, 1, 2), (0, 1, 1, 12)          # 元記事が 2000〜2014年の AIC で選んだ次数
def select_order(tr):
    best = None
    for p, q, P, Q in itertools.product([0, 1, 2], [0, 1, 2], [0, 1], [0, 1]):
        try:
            r = SARIMAX(tr, order=(p, 1, q), seasonal_order=(P, 1, Q, 12)).fit(disp=False)
            if best is None or r.aic < best[0]: best = (r.aic, (p, 1, q), (P, 1, Q, 12))
        except Exception: pass
    return best[1], best[2]

origins = pd.date_range("2015-01-01", "2025-08-01", freq="MS")
re_orders, cur = {}, None
for yr in range(2015, 2026):                     # ⑤ 毎年1月に、その時点までのデータで次数を選び直す
    re_orders[yr] = select_order(y.loc[:f"{yr}-01-01"]); print(yr, re_orders[yr])
rows = []; t0 = time.time()
for origin in origins:
    tr = y.loc[:origin]
    r = SARIMAX(tr, order=ORDER, seasonal_order=SORDER).fit(disp=False); f = r.get_forecast(12)
    m = f.predicted_mean; c80 = f.conf_int(alpha=.2); c95 = f.conf_int(alpha=.05)
    o2, s2 = re_orders[origin.year]
    m2 = SARIMAX(tr, order=o2, seasonal_order=s2).fit(disp=False).get_forecast(12).predicted_mean
    ets = ExponentialSmoothing(tr, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12).fit().forecast(12)
    for h, t in enumerate(m.index, start=1):
        if t not in y.index: continue
        rows.append({"origin": origin, "h": h, "target": t, "actual": y.loc[t], "sarima": m.iloc[h - 1], "sarima_reselect": m2.iloc[h - 1],
                     "ets": ets.iloc[h - 1], "naive_last": y.loc[origin],
                     "snaive": y.loc[t - pd.DateOffset(years=1)] if h <= 12 else np.nan,
                     "snaive_drift": y.loc[t - pd.DateOffset(years=1)] + (y.loc[origin] - y.loc[origin - pd.DateOffset(years=1)]),
                     "lo80": c80.iloc[h - 1, 0], "hi80": c80.iloc[h - 1, 1], "lo95": c95.iloc[h - 1, 0], "hi95": c95.iloc[h - 1, 1]})
ev = pd.DataFrame(rows); print("fits", round(time.time() - t0, 1), len(ev))
ev["covid"] = ev.target.between("2020-03-01", "2021-12-01") | ev.origin.between("2020-01-01", "2021-12-01")
ev.to_csv(RES / "c_rolling_forecasts.csv.gz", index=False)
M = ["sarima", "sarima_reselect", "ets", "naive_last", "snaive", "snaive_drift"]

def mae(df): return pd.Series({m: (df[m] - df.actual).abs().mean() for m in M})
by_h = ev[~ev.covid].groupby("h").apply(mae); by_h_all = ev.groupby("h").apply(mae)
by_h.round(4).to_csv(RES / "c_mae_by_h_excl_covid.csv"); by_h_all.round(4).to_csv(RES / "c_mae_by_h_all.csv")
orig = pd.read_csv(ORIG / "020_t1_mae_by_h.csv").set_index("h")
print("repro diff max", (by_h[["sarima", "naive_last", "snaive_drift"]] - orig).abs().max().max())
print(by_h.round(3)); print(by_h_all.round(3))

def dm(e1, e2, h):
    """Diebold–Mariano（絶対誤差の差、h−1 次の Newey–West 分散、Harvey らの小標本補正）"""
    dlt = np.abs(e1) - np.abs(e2); n = len(dlt); mu = dlt.mean()
    g = [np.mean((dlt[k:] - mu) * (dlt[:n - k] - mu)) for k in range(h)]
    v = (g[0] + 2 * sum((1 - k / h) * g[k] for k in range(1, h))) / n
    stat = mu / np.sqrt(max(v, 1e-12)); stat *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return mu, stat, 2 * stats.t.sf(abs(stat), n - 1)
dmr = []
for per, df in {"コロナ期を除く（元と同じ）": ev[~ev.covid], "すべて": ev,
                "2015〜2019年が予測先": ev[(ev.target < "2020-01-01") & ~ev.covid], "2022年以降が予測先": ev[(ev.target >= "2022-01-01") & ~ev.covid]}.items():
    for h in range(1, 13):
        g = df[df.h == h].sort_values("origin")
        e = {m: (g[m] - g.actual).values for m in M}
        for rival in ["naive_last", "snaive_drift", "snaive", "ets"]:
            mu, st, p = dm(e["sarima"], e[rival], h)
            dmr.append({"period": per, "h": h, "rival": rival, "n": len(g), "mae_sarima": np.abs(e["sarima"]).mean(), "mae_rival": np.abs(e[rival]).mean(),
                        "diff": mu, "dm": st, "p": p})
dmr = pd.DataFrame(dmr); dmr.round(4).to_csv(RES / "c_dm_tests.csv", index=False, encoding="utf-8-sig")
tab = dmr.assign(better=lambda x: x["diff"] < 0, sig=lambda x: (x["diff"] < 0) & (x.p < .05)).groupby(["period", "rival"]).agg(
    better=("better", "sum"), sig_better=("sig", "sum"), worse_sig=("p", lambda s: 0)).reset_index()
tab["worse_sig"] = dmr.assign(w=lambda x: (x["diff"] > 0) & (x.p < .05)).groupby(["period", "rival"]).w.sum().values
tab.to_csv(RES / "c_dm_summary.csv", index=False, encoding="utf-8-sig"); print(tab)

# 予測区間の当たり方
cov = ev.assign(in80=lambda x: x.actual.between(x.lo80, x.hi80), in95=lambda x: x.actual.between(x.lo95, x.hi95))
cv = pd.concat({"コロナ期を除く": cov[~cov.covid].groupby("h")[["in80", "in95"]].mean(), "すべて": cov.groupby("h")[["in80", "in95"]].mean()}, axis=1)
cv.round(3).to_csv(RES / "c_interval_coverage.csv", encoding="utf-8-sig"); print(cv.round(3))

# 元記事の主張「1〜12か月先のどこでも SARIMA が単純な予測より誤差が小さい」を、各条件で確かめる
def claim(bh, rivals=("naive_last", "snaive_drift")):
    return int(sum(all(bh.loc[h, "sarima"] < bh.loc[h, r] for r in rivals) for h in bh.index))
per_mae = {"2015〜2019年": ev[(ev.target < "2020-01-01") & ~ev.covid].groupby("h").apply(mae),
           "2022年以降": ev[(ev.target >= "2022-01-01") & ~ev.covid].groupby("h").apply(mae)}
for k, v in per_mae.items(): v.round(4).to_csv(RES / ("c_mae_by_h_2015_2019.csv" if k.startswith("2015") else "c_mae_by_h_2022plus.csv"))
s = {"reselect_orders": "; ".join(f"{k}:{v[0]}{v[1][:3]}" for k, v in re_orders.items()),
     "n_changed_orders": int(sum(v != (ORDER, SORDER) for v in re_orders.values())),
     "claim_h_orig_rivals_excl": claim(by_h), "claim_h_all_rivals_excl": claim(by_h, ("naive_last", "snaive_drift", "snaive", "ets")),
     "claim_h_orig_rivals_all": claim(by_h_all), "claim_h_2015_19": claim(per_mae["2015〜2019年"]), "claim_h_2022": claim(per_mae["2022年以降"]),
     "claim_h_2022_vs_ets": int(sum(per_mae["2022年以降"].loc[h, "sarima"] < per_mae["2022年以降"].loc[h, "ets"] for h in range(1, 13))),
     "mae_h1": by_h.loc[1].to_dict(), "mae_h12": by_h.loc[12].to_dict(), "mae_h12_all": by_h_all.loc[12].to_dict(),
     "mae_h1_2022": per_mae["2022年以降"].loc[1].to_dict(), "mae_h12_2022": per_mae["2022年以降"].loc[12].to_dict(),
     "dm_sig_vs_naive_excl": int(tab.query("period=='コロナ期を除く（元と同じ）' and rival=='naive_last'").sig_better.iloc[0]),
     "dm_sig_vs_snaivedrift_excl": int(tab.query("period=='コロナ期を除く（元と同じ）' and rival=='snaive_drift'").sig_better.iloc[0]),
     "dm_sig_vs_ets_excl": int(tab.query("period=='コロナ期を除く（元と同じ）' and rival=='ets'").sig_better.iloc[0]),
     "dm_sig_vs_naive_all": int(tab.query("period=='すべて' and rival=='naive_last'").sig_better.iloc[0]),
     "dm_sig_vs_naive_2022": int(tab.query("period=='2022年以降が予測先' and rival=='naive_last'").sig_better.iloc[0]),
     "dm_sig_vs_snaivedrift_2022": int(tab.query("period=='2022年以降が予測先' and rival=='snaive_drift'").sig_better.iloc[0]),
     "cov80_h1": cv.loc[1, ("コロナ期を除く", "in80")], "cov80_h12": cv.loc[12, ("コロナ期を除く", "in80")],
     "cov95_h1": cv.loc[1, ("コロナ期を除く", "in95")], "cov95_h12": cv.loc[12, ("コロナ期を除く", "in95")],
     "cov95_h12_all": cv.loc[12, ("すべて", "in95")], "cov80_mean": cv[("コロナ期を除く", "in80")].mean(), "cov95_mean": cv[("コロナ期を除く", "in95")].mean(),
     "n_excl": int((~ev.covid).sum()), "n_all": len(ev)}
pd.Series(s).to_csv(RES / "c_summary.csv", header=["value"], encoding="utf-8-sig"); print(pd.Series(s))
