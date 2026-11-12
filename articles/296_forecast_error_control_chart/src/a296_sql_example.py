"""1本の例（80週目から +10%）を CSV に書き、DuckDB の SQL で週の誤差と管理限界を出す。Python の計算と照合する"""
import json, numpy as np, pandas as pd, duckdb
from common import DATA, RES, SQL
from a296_sim import demand, fit, weekly_bias, W_TRAIN, W_BASE, W_END
rng = np.random.default_rng(29610)
y = demand(rng, 0.10); fc = np.tile(fit(y, 1, W_TRAIN), W_END)
dates = pd.date_range("2023-01-02", periods=len(y), freq="D")
df = pd.DataFrame({"sales_date": dates.date, "actual": np.round(y).astype(int), "forecast": np.round(fc, 1)})
df.to_csv(DATA / "daily_demand_example.csv", index=False)
con = duckdb.connect(); con.execute(f"CREATE TABLE daily_demand AS SELECT * FROM read_csv_auto('{DATA / 'daily_demand_example.csv'}')")
out = con.execute((SQL / "01_weekly_error_chart_duckdb.sql").read_text()).df()
out.to_csv(RES / "example_weekly_chart.csv", index=False)
b = weekly_bias(df.actual.values.astype(float), df.forecast.values.astype(float)); base = b[W_TRAIN:W_BASE]
z = (b - base.mean()) / base.std(ddof=1)
chk = {"weeks": len(out), "max_abs_diff_bias": float(np.abs(out.bias.values - b).max()), "max_abs_diff_z": float(np.abs(out.z.values - z).max()),
       "first_r1_week": int(np.argmax(out.r1_3sigma.values[W_BASE:]) + W_BASE + 1) if out.r1_3sigma.values[W_BASE:].any() else None,
       "first_r3_week": int(np.argmax(out.r3_4weeks_up.values[W_BASE:]) + W_BASE + 1) if out.r3_4weeks_up.values[W_BASE:].any() else None}
json.dump(chk, open(RES / "example_sql_check.json", "w"), indent=1); print(chk)
