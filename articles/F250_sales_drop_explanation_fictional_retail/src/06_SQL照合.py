"""06 SQL 照合：既存店の前年比と3つの要素を SQL（DuckDB で実行）でも計算し、03_分析.py（pandas）の結果と比べる。"""
import json, pathlib
import duckdb
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
MART = ROOT / "data" / "mart"
con = duckdb.connect()
con.execute(f"CREATE TABLE fact_store_day AS SELECT * FROM read_csv_auto('{MART / 'fact_store_day.csv.gz'}')")
con.execute(f"CREATE TABLE dim_store AS SELECT store_id, CAST(open_date AS DATE) AS open_date, CAST(close_date AS DATE) AS close_date FROM read_csv_auto('{MART / 'dim_store.csv'}')")
q = con.execute((ROOT / "sql" / "10_existing_store_yoy.sql").read_text()).df().set_index("ym")
a = pd.read_csv(ROOT / "results" / "A_monthly_decomposition_seed0.csv").set_index("ym")
cols = ["sales_yoy", "receipts_yoy", "items_per_receipt_yoy", "unit_price_yoy"]
diff = (q[cols] - a.loc[q.index, cols]).abs()
out = {"months": len(q), "n_stores_match": bool((q.n_stores == a.loc[q.index, "n_stores"]).all()), "max_abs_diff": float(diff.values.max())}
q.to_csv(ROOT / "results" / "H_sql_existing_yoy.csv")
json.dump(out, open(ROOT / "results" / "H_sql_check.json", "w"), indent=1)
print(out)
