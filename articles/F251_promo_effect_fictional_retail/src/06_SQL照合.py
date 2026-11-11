"""06 SQL 照合：簡単な3つの測り方（前後比較・前年比・前年比の差）を SQL（DuckDB で実行）でも計算し、03_分析.py（pandas）と比べる。"""
import json, pathlib
import duckdb
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
con = duckdb.connect()
con.execute(f"CREATE TABLE store_week AS SELECT * FROM read_csv_auto('{ROOT / 'results' / 'A_store_week_seed0.csv.gz'}')")
q = con.execute((ROOT / "sql" / "10_promo_simple_estimates.sql").read_text()).df().iloc[0]
a = pd.read_csv(ROOT / "results" / "A_estimates_seed0.csv").set_index("method").promo_lift
pairs = {"m1_before_after": "M1_前後", "m2_yoy": "M2_前年比", "m3_yoy_diff": "M3_前年比の差"}
out = {k: {"sql": float(q[k]), "pandas": float(a[v]), "abs_diff": abs(float(q[k]) - float(a[v]))} for k, v in pairs.items()}
out["max_abs_diff"] = max(v["abs_diff"] for v in out.values())
json.dump(out, open(ROOT / "results" / "D_sql_check.json", "w"), ensure_ascii=False, indent=1)
print(out)
