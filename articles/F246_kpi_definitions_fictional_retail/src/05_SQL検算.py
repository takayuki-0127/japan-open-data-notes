"""05 SQL の検算：sql/kpi_monthly.sql（SQL Server 互換の書き方）を DuckDB で流し、03_分析.py の既存店の前年同月比と照合する。
SQL Server そのものでは動かしていない。DuckDB で通すために、[date] の角かっこを "date" に置き換えるだけの変換をする。"""
import pathlib
import duckdb
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "data"
sql = (ROOT / "sql" / "kpi_monthly.sql").read_text().replace("[date]", '"date"')
con = duckdb.connect()
con.execute(f"CREATE TABLE dim_store AS SELECT * FROM read_csv_auto('{D/'dim_store.csv'}')")
con.execute(f"CREATE TABLE dim_date AS SELECT * FROM read_csv_auto('{D/'dim_date.csv'}')")
con.execute(f"CREATE TABLE fact_store_day AS SELECT * FROM read_csv_auto('{D/'fact_store_day.csv.gz'}')")
q = con.execute(sql).df()
py = pd.read_csv(ROOT / "results" / "B_yoy_all_vs_existing_13m.csv")
m = q.merge(py, on="ym")
d1 = (m.sales_yoy - m["既存店_売上"]).abs().max()
d2 = (m.receipts_yoy - m["既存店_客数"]).abs().max()
d3 = (m.existing_stores - m["既存店の数"]).abs().max()
out = pd.DataFrame({"比べた月": [len(m)], "売上の前年比の差の最大": [d1], "客数の前年比の差の最大": [d2], "既存店の数の差の最大": [d3]})
out.to_csv(ROOT / "results" / "E_sql_check.csv", index=False, encoding="utf-8-sig")
q.to_csv(ROOT / "results" / "E_sql_kpi_monthly.csv", index=False, encoding="utf-8-sig")
print(out.to_string(index=False))
print(q.tail(3).round(4).to_string(index=False))
