"""06 SQL照合：予算の積み上げと、バックテストの集計を SQL（sql/10・20）でも計算し、pandas の結果と比べる。DuckDB で実行。"""
import json, pathlib
import duckdb
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
con = duckdb.connect()
b = pd.read_csv(RES / "D_budget_store_month_base.csv")
con.register("budget_store_month", b)
q1 = con.execute((ROOT / "sql" / "10_budget_rollup.sql").read_text(encoding="utf-8")).df().set_index("area")
p1 = b.groupby("area")[["sales", "gross_profit", "labor_cost", "other_cost", "operating_profit"]].sum()
p1.loc["全社"] = p1.sum()
d1 = float((q1[p1.columns].loc[p1.index] / p1 - 1).abs().max().max())
A = pd.read_csv(RES / "A_company_backtest_annual.csv.gz")
con.register("backtest", A[["seed", "origin", "level", "unit", "model", "method", "fc", "act"]])
q2 = con.execute((ROOT / "sql" / "20_backtest_mape.sql").read_text(encoding="utf-8")).df()
p2 = (A.assign(a=(A.fc / A.act - 1).abs()).groupby(["level", "method", "model"]).a.mean() * 100).rename("p").reset_index()
z = q2.merge(p2, on=["level", "method", "model"])
d2 = float((z.mape_pct - z.p).abs().max())
out = {"budget_rollup_max_rel_diff": d1, "backtest_mape_max_abs_diff_pt": d2, "rows_backtest": int(len(A)), "groups": int(len(z))}
q1.to_csv(RES / "G_sql_budget_rollup.csv", float_format="%.0f")
json.dump(out, open(RES / "G_sql_check.json", "w"), ensure_ascii=False, indent=1)
print(out)
