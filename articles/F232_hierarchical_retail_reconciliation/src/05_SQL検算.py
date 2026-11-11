# F232 05 SQL 検算：sql/ の SQL Server 互換のクエリを DuckDB で動かし、Python の結果と照合する
import duckdb, pandas as pd, pathlib, re
B = pathlib.Path(__file__).resolve().parents[1]
con = duckdb.connect()
def tsql(s):  # DuckDB で動かすための最小の読み替え（型名と N'' だけ）
    return re.sub(r"NVARCHAR\(\d+\)", "VARCHAR", s).replace("N'", "'")
con.execute(tsql((B / "sql/01_schema.sql").read_text()))
fc = pd.read_csv(B / "data/forecast_2025_08_long.csv")
con.execute("INSERT INTO forecast_long SELECT method, node, NULLIF(parent,''), level, ym, forecast FROM fc")
ape = pd.read_csv(B / "results/A_ape_main.csv.gz")
ape.columns = ["cond", "origin", "method", "node", "level", "horizon", "ape", "actual"]
con.execute("INSERT INTO ape_long SELECT * FROM ape")
coh = con.execute(tsql((B / "sql/02_coherence_check.sql").read_text())).df()
acc = con.execute(tsql((B / "sql/03_accuracy_by_level.sql").read_text())).df()
coh.to_csv(B / "results/H_sql_coherence_check.csv", index=False)
acc.to_csv(B / "results/H_sql_accuracy_by_level.csv", index=False)
# Python 側（C_mape_by_level_horizon.csv）との照合
py = pd.read_csv(B / "results/C_mape_by_level_horizon.csv")
py = py[py.条件.str.startswith("主")].copy()
py["hbucket"] = py.hb.map({"1〜3か月": "1-3", "4〜6か月": "4-6", "7〜12か月": "7-12"})
m = acc.merge(py, left_on=["method", "level", "hbucket"], right_on=["方法", "階層", "hbucket"])
print(coh.round(4).to_string())
print("rows", len(m), "max abs diff", float((m.mape - m.MAPE).abs().max()))
