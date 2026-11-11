"""05 SQL の照合：sql/alert_same_weekday.sql（T-SQL）を DuckDB で動くように最小限だけ置き換えて流し、
pandas で同じルールを書いたものと z と警報が一致するかを確かめる（データは架空のあおばマート、種0）。
置き換え：LOG→LN、DATEPART(weekday, x)→dayofweek(x)、STDEV→STDDEV_SAMP、N'…'→'…'。"""
import duckdb, numpy as np, pandas as pd, json
s = pd.read_csv("results/A_sim_seed0_series.csv", parse_dates=["date"])
kpi = pd.DataFrame({"kpi_date": s.date.dt.date, "kpi_value": s.orders.astype(float)})
q = open("sql/alert_same_weekday.sql").read()
q = q.replace("LOG(kpi_value)", "LN(kpi_value)").replace("DATEPART(weekday, kpi_date)", "dayofweek(kpi_date)").replace("STDEV(", "STDDEV_SAMP(").replace("N'", "'")
con = duckdb.connect(); con.register("kpi_daily", kpi)
r = con.execute(q).df()
# pandas 版
ly = np.log(kpi.kpi_value.values); wd = s.date.dt.weekday.values; n = len(ly)
e = np.full(n, np.nan)
for t in range(n):
    prev = [i for i in range(t - 1, -1, -1) if wd[i] == wd[t]][:4]
    if len(prev) == 4: e[t] = ly[t] - np.mean(ly[prev])
idx = np.where(np.isfinite(e))[0]; ev = e[idx]; z = np.full(len(ev), np.nan)
for j in range(56, len(ev)): z[j] = ev[j] / np.std(ev[j - 56:j], ddof=1)
p = pd.DataFrame({"kpi_date": kpi.kpi_date.values[idx], "z_pd": z}).dropna()
r["kpi_date"] = pd.to_datetime(r.kpi_date).dt.date.astype(str); p["kpi_date"] = p.kpi_date.astype(str)
m = r.merge(p, on="kpi_date")
diff = float(np.max(np.abs(m.z - m.z_pd.round(2))))
agree = float(((m.alert == 1) == (np.abs(m.z_pd) > 3.5)).mean())
res = dict(rows=len(m), max_abs_diff_z_rounded=diff, alert_agree=agree, alerts=int(m.alert.sum()))
json.dump(res, open("results/C_sql_check.json", "w")); print(res)
