# F259 05 SQL 検算：sql/f259_check.sql を DuckDB で流し、Python の結果と比べる
import duckdb, pandas as pd
def mi(s): y, m = map(int, s.split("-")); return y * 12 + m - 1
d = pd.read_csv("data/demand_scaled.csv"); d["月番号"] = d.ym.map(mi)
f = pd.read_csv("data/forecasts_scaled.csv.gz"); f["起点番号"] = f["起点"].map(mi)
demand = d[["業態", "月番号", "需要"]]; forecasts = f[["業態", "モデル", "起点番号", "h", "予測"]]
sim_log = pd.read_csv("results/sim_log_p9.csv.gz")
con = duckdb.connect(); [con.register(n, v) for n, v in [("demand", demand), ("forecasts", forecasts), ("sim_log", sim_log)]]
q1, q2 = [s.strip() for s in open("sql/f259_check.sql").read().split(";") if "SELECT" in s][:2]
c = con.execute(q1).df(); A = pd.read_csv("results/A_cost_main.csv"); A = A[A.p == 9]
m1 = c.merge(A[["業態", "モデル", "L", "決め方", "費用"]], on=["業態", "モデル", "L", "決め方"], suffixes=("_SQL", "_Python"))
r = con.execute(q2).df(); B = pd.read_csv("results/B_needed_ss_by_H.csv")
m2 = r.merge(B[["業態", "モデル", "H", "RMSE倍"]], on=["業態", "モデル", "H"], suffixes=("_SQL", "_Python"))
lines = [f"(1) 費用：{len(m1)}組を照合、最大の差 {(m1.費用_SQL - m1.費用_Python).abs().max():.2e}",
         f"(2) 合計の外れの RMSE 倍率：{len(m2)}組を照合、最大の差 {(m2.RMSE倍_SQL - m2.RMSE倍_Python).abs().max():.2e}"]
open("results/F_sql_check.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
