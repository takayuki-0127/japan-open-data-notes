"""sql/ の2本を DuckDB で流し、Python（03_分析.py）の結果と照合する。"""
import duckdb, pandas as pd, pathlib, json
B = pathlib.Path(__file__).resolve().parents[1]
con = duckdb.connect()
con.register("telco", pd.read_csv(B / "data/telco_clean.csv")[["customerID", "duration", "event"]])
con.register("houjin", pd.read_csv(B / "data/houjin_cohort.csv.gz"))
a = con.execute((B / "sql/01_life_table.sql").read_text()).df()
b = pd.read_csv(B / "results/A_life_table.csv").merge(a, on="month", suffixes=("_py", "_sql"))
c = con.execute((B / "sql/02_cohort_retention.sql").read_text()).df()
d = pd.read_csv(B / "results/D_cohort_retention.csv").merge(c, left_on=["kind", "cohort", "year"], right_on=["kind_j", "cohort", "year"], suffixes=("_py", "_sql"))
r = {"life_rows": len(b), "life_maxdiff": float((b.hazard_py - b.hazard_sql).abs().max()),
     "cohort_rows_py": int(len(pd.read_csv(B / "results/D_cohort_retention.csv"))), "cohort_rows_sql": len(c),
     "cohort_matched": len(d), "cohort_maxdiff": float((d.retention_py - d.retention_sql).abs().max())}
json.dump(r, open(B / "results/F_sql_check.json", "w"), indent=1); print(r)
