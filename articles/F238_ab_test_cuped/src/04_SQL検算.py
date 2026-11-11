"""04 SQL の検算：src/04_CUPED.sql を DuckDB で流し、Python（03 の estimators）と比べる。"""
from pathlib import Path
import importlib.util, json
import duckdb, numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sim = pd.read_csv(ROOT / "data" / "sim_users.csv.gz")
con = duckdb.connect()
con.register("sim_users", sim)
q = (ROOT / "src" / "04_CUPED.sql").read_text(encoding="utf-8")
sql = con.execute(q).df().set_index("method")
y = sim.visits.to_numpy(float); x = sim.pre_visits.to_numpy(float); t = (sim.arm == "B").to_numpy().astype(int)
# Python 側（03 と同じ式）
def py(y, x, t):
    out = {}
    y1, y0 = y[t == 1], y[t == 0]
    out["naive"] = (y1.mean() - y0.mean(), np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0)))
    c = np.cov(y, x, ddof=1); th = c[0, 1] / c[1, 1]; ya = y - th * (x - x.mean())
    out["cuped"] = (ya[t == 1].mean() - ya[t == 0].mean(), np.sqrt(ya[t == 1].var(ddof=1) / len(y1) + ya[t == 0].var(ddof=1) / len(y0)))
    return out
p = py(y, x, t)
rows = []
for m in ["naive", "cuped"]:
    rows.append(dict(method=m, sql_est=sql.loc[m, "est"], py_est=p[m][0], sql_se=sql.loc[m, "se"], py_se=p[m][1],
                     max_abs_diff=max(abs(sql.loc[m, "est"] - p[m][0]), abs(sql.loc[m, "se"] - p[m][1]))))
df = pd.DataFrame(rows)
df.to_csv(ROOT / "results" / "D_sql_check.csv", index=False)
print(df.to_string())
