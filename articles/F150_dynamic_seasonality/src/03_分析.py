"""本体：3系列それぞれに、季節を固定したモデルと、季節が年々ゆっくり変わるモデル（動的調和回帰）を当てて比べる"""
import json, numpy as np, pandas as pd
from scipy import stats
from ds import load, fit, seasonal, profile, yearly, sigma_share
from common import RES

WIN = {"births": [(2000, 2004), (2021, 2025)], "inbound": [(2005, 2009), (2015, 2019), (2024, 2025)],
       "power": [(2017, 2019), (2023, 2025)]}
ORIG = {"births": list(range(2014, 2025)), "inbound": list(range(2011, 2019)) + [2023, 2024],
        "power": list(range(2020, 2025))}
summary, prof_rows, year_rows, seas_rows, fc_rows = {}, [], [], [], []
for name in ["births", "inbound", "power"]:
    y, _ = load(name)
    r0 = fit(y, stochastic=False); r1 = fit(y, stochastic=True)
    lr = 2 * (r1.llf - r0.llf)
    # 季節の分散が0かどうかは境界の検定。混合カイ二乗（0.5χ²0+0.5χ²1）で p 値を出す
    p = 0.5 * stats.chi2.sf(max(lr, 0), 1)
    s1, s0 = seasonal(r1), seasonal(r0)
    seas_rows.append(pd.DataFrame({"series": name, "date": s1.index, "seasonal_tv": s1.values, "seasonal_fixed": s0.values}))
    yr = yearly(s1); yr["series"] = name; year_rows.append(yr)
    for w in WIN[name]:
        pr = profile(s1, w)
        prof_rows.append(dict(series=name, window=f"{w[0]}-{w[1]}", **{f"m{m:02d}": v for m, v in pr.items()},
                              amplitude=pr.max() - pr.min(), peak=int(pr.idxmax()), trough=int(pr.idxmin())))
    # 12か月先の予測（拡大窓）：前年12月までで当て、翌年1〜12月を予測
    for o in ORIG[name]:
        tr = y[:f"{o}-12-01"]; te = y[f"{o+1}-01-01":f"{o+1}-12-01"].dropna()
        if len(te) < 12 or tr.dropna().shape[0] < 48: continue
        f0 = fit(tr, stochastic=False).forecast(12); f1 = fit(tr, stochastic=True).forecast(12)
        last = y[f"{o}-01-01":f"{o}-12-01"]
        sn = last.values - last.mean() + tr.dropna()[-12:].mean()  # 前年の形を前年の水準で
        for lab, f in [("fixed", f0.values), ("time_varying", f1.values), ("seasonal_naive", sn)]:
            e = te.values - f[:len(te)]
            fc_rows.append(dict(series=name, origin=o, model=lab, mae_pct=100 * np.mean(np.abs(e)),
                                shape_mae_pct=100 * np.mean(np.abs((e - e.mean())))))
    sp = sigma_share(r1)
    summary[name] = dict(n=int(y.notna().sum()), start=str(y.index[0].date()), end=str(y.index[-1].date()),
                         llf_fixed=r0.llf, llf_tv=r1.llf, lr=lr, p_value=p, aic_fixed=r0.aic, aic_tv=r1.aic,
                         sigma2=sp, mean_abs_yoy_change_pt=float(100 * s1.diff(12).abs().mean()))
    print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in summary[name].items() if k != "sigma2"})

pd.DataFrame(prof_rows).to_csv(RES / "profiles.csv", index=False)
pd.concat(year_rows).to_csv(RES / "yearly_amplitude.csv", index=False)
pd.concat(seas_rows).to_csv(RES / "seasonal_states.csv", index=False)
fc = pd.DataFrame(fc_rows); fc.to_csv(RES / "forecast_by_origin.csv", index=False)
fcs = fc.groupby(["series", "model"])[["mae_pct", "shape_mae_pct"]].mean().round(2)
fcs.to_csv(RES / "forecast_summary.csv"); print(fcs)
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(pd.DataFrame(prof_rows).round(1).to_string())
