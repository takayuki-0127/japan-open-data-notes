"""問い直し（結果を見てから足した）：要請期間の中で、月ごとに見込みからの差はどう動いたか。
2022年7月〜2023年3月の各月（要請のない10・11月を含む）に別々のダミーを置き、同じ回帰で推定する。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "daily.csv", parse_dates=["date"]).set_index("date").sort_index()
d["temp"] = (d.temp_fukuoka + d.temp_kagoshima) / 2
d["ln_d"] = np.log(d.demand_gwh)
d["daytype"] = np.where(d.holiday == 1, "hol", d.dow.astype(str))
d["tb"] = np.clip(np.floor(d.temp), -2, 31).astype(int).astype(str)
months = pd.period_range("2022-07", "2023-03", freq="M")
names = []
for p in months:
    n = f"m{p.year}{p.month:02d}"
    d[n] = ((d.index.year == p.year) & (d.index.month == p.month)).astype(int)
    names.append(n)
f = smf.ols("ln_d ~ " + " + ".join(names) + " + C(tb) + C(daytype) + C(month) + C(fy)", d).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
rows = []
for p, n in zip(months, names):
    b, se = f.params[n], f.bse[n]
    rows.append({"month": f"{p.year}-{p.month:02d}", "request": int(p.month in (7, 8, 9, 12, 1, 2, 3)),
                 "pct": round(float((np.exp(b) - 1) * 100), 2), "lo": round(float((np.exp(b - 1.96 * se) - 1) * 100), 2),
                 "hi": round(float((np.exp(b + 1.96 * se) - 1) * 100), 2)})
t = pd.DataFrame(rows)
t.to_csv(R / "requestion_by_month.csv", index=False)
req = t[t.request == 1]
out = {"by_month": rows, "n_request_months_below_minus1": int((req.pct <= -1).sum()), "n_request_months": int(len(req)),
       "min_month": str(req.loc[req.pct.idxmin(), "month"]), "min_pct": float(req.pct.min()),
       "max_month": str(req.loc[req.pct.idxmax(), "month"]), "max_pct": float(req.pct.max()),
       "n_request_months_ci_excludes_0": int(((req.hi < 0) | (req.lo > 0)).sum())}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(t.to_string()); print({k: v for k, v in out.items() if k != "by_month"})
