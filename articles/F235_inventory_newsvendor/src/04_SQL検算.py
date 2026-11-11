# 04 SQL 検算：04_在庫の判断.sql を DuckDB で流し、Python（03_分析.py の results/E_fixed_split_q90.csv）と比べる
# DuckDB には SQL Server の PERCENTILE_CONT(p) WITHIN GROUP (ORDER BY x) OVER (...) と同じ計算（線形補間）の
# quantile_cont(x, p) OVER (...) があるので、そこだけ書き換えて流す
import re, duckdb, pandas as pd
sql = open("src/04_在庫の判断.sql", encoding="utf-8").read()
sql = re.sub(r"PERCENTILE_CONT\(([0-9.]+)\) WITHIN GROUP \(ORDER BY (\w+)\) OVER", r"quantile_cont(\2, \1) OVER", sql)
con = duckdb.connect()
con.execute("CREATE TABLE forecast AS SELECT * EXCLUDE (コロナ期), CAST(コロナ期 AS VARCHAR) AS コロナ期 FROM read_csv_auto('data/forecasts_h1to3.csv')")
con.execute("UPDATE forecast SET コロナ期 = CASE WHEN lower(コロナ期)='true' THEN 'True' ELSE 'False' END")
q = con.execute(sql.split("\n", 1)[1]).df()
p = pd.read_csv("results/E_fixed_split_q90.csv")
m = q.merge(p, on=["モデル", "業態"], suffixes=("_sql", "_py"))
d = {c: float((m[c + "_sql"] - m[c + "_py"]).abs().max()) for c in ["倍率q90", "損", "サービス率"]}
msg = f"行数 SQL {len(q)} / Python {len(p)}、最大の差 " + "、".join(f"{k} {v:.2e}" for k, v in d.items())
open("results/F_sql_check.txt", "w").write(msg + "\n"); q.to_csv("results/F_sql_result.csv", index=False); print(msg)
