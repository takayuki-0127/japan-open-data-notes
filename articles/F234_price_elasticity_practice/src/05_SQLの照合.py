"""T-SQL と同じ計算を DuckDB で動かし、Python の結果と照合する"""
import duckdb, json
import numpy as np, pandas as pd
from common import *
d = load_panel()
con = duckdb.connect()
raw = pd.read_csv(RAW / "kakei_items_panel_f113.csv").rename(columns={"group": "grp"})
con.register("kakei_items", raw)
sql = (ROOT / "sql" / "01_前年差と区分変更の判定_tsql.sql").read_text()
q1 = sql.split("SELECT name, grp, year, dlp, dlq,")[0]  # CTE 部分
q1 = q1.replace("dbo.kakei_items", "kakei_items").replace("LOG(", "LN(")
q1 += """SELECT name, grp, year, dlp, dlq,
       CASE WHEN ABS(dlq) > 0.7 OR ABS(dlp) > 0.5 THEN 1 ELSE 0 END AS break_flag
FROM d WHERE dlp IS NOT NULL"""
s = con.execute(q1).df()
py = d.dropna(subset=["dlp_raw"])
res = dict(sql_rows=len(s), py_rows=len(py), sql_breaks=int(s.break_flag.sum()), py_breaks=int(d["break"].sum()),
           max_abs_diff_dlq=float((s.set_index(["name", "year"]).dlq - py.set_index(["name", "year"]).dlq_raw).abs().max()))
q2 = (ROOT / "sql" / "02_値上げの分かれ目_tsql.sql").read_text().replace("LOG(", "LN(")
b = con.execute(q2).df()
D = pd.read_csv(RES / "D_decision_table.csv")
res["max_abs_diff_breakeven"] = float(np.abs(b.breakeven_elasticity.values - D.breakeven_eps.values).max())
json.dump(res, open(RES / "sql_check.json", "w"), ensure_ascii=False, indent=1)
print(res)
