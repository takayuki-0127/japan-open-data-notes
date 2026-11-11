# 05_集計.sql を SQLite で流し、pandas の結果（results/A_mape_by_h.csv）と一致するか確かめる
import sqlite3, re, pandas as pd, numpy as np
f = pd.read_csv("results/forecasts_main.csv.gz")
con = sqlite3.connect(":memory:"); f.to_sql("forecast", con, index=False)
sql = open("src/05_集計.sql", encoding="utf-8").read().replace("N'", "'")
stmts = [s for s in re.split(r";\s*\n", sql) if "SELECT" in s]
q = [pd.read_sql(re.sub(r"--[^\n]*", "", s), con) for s in stmts]
a = pd.read_csv("results/A_mape_by_h.csv", index_col=0)
p = q[0].pivot(index="h", columns="モデル", values="mape_pct")[a.columns]
diff = float(np.abs(p.values - a.values).max())
q[1].round(4).to_csv("results/E_sql_skill.csv", index=False)
open("results/E_sql_check.txt", "w").write(f"SQL と pandas の MAPE の差の最大：{diff:.6f}（四捨五入の差）\n行数：{int(q[2].n.sum())}\n")
print(diff, int(q[2].n.sum()))
