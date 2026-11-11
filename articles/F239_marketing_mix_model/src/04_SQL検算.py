# 04_SQL検算：T-SQL のアドストック計算を DuckDB で動かし、Python の結果と比べる
# DuckDB では WITH を WITH RECURSIVE に、OPTION (MAXRECURSION 0) を外し、FLOAT（DuckDB では32ビット）を DOUBLE にして流す（T-SQL の FLOAT は64ビットなので中身は同じ）
import numpy as np, pandas as pd, duckdb, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
src = open(ROOT / "src" / "03_分析.py", encoding="utf-8").read()
head = "import json\nimport numpy as np\nimport pandas as pd\nfrom pathlib import Path\n"
part = src.split("# ---------------------------------------------------------------- B. 架空の会社のシミュレーション")[1].split("rng0 = np.random.default_rng(239)")[0]
g = {}
exec(head + part, g)
wk, S, sales, C, scale = g["simulate"](np.random.default_rng(0), "ばらばら")
df = pd.DataFrame({"週": wk, "テレビ": S[:, 0].round(4), "Web": S[:, 1].round(4), "チラシ": S[:, 2].round(4), "売上": sales.round(4)})
df.to_csv(ROOT / "data" / "sim_weekly_midorihome.csv", index=False)
sql = open(ROOT / "src" / "04_アドストック.sql", encoding="utf-8").read()
q1, q2 = [x.strip() for x in sql.split(";")[:2]]
q1 = q1.replace("WITH ad AS", "WITH RECURSIVE ad AS").replace("OPTION (MAXRECURSION 0)", "").replace("AS FLOAT", "AS DOUBLE")
con = duckdb.connect()
con.register("sim_weekly", df)
r1 = con.execute(q1).fetchone()
a = g["adstock"](df["テレビ"].to_numpy(), 0.6)
py = (len(a), a.sum(), a.max(), a.mean())
r2 = con.execute(q2).df()
py2 = df[["テレビ", "Web", "チラシ"]].sum(1).rolling(4, min_periods=1).sum()
out = {"SQL": [float(x) for x in r1], "Python": [float(x) for x in py], "最大の差": float(max(abs(x - y) for x, y in zip(r1, py))),
       "4週計の最大の差": float((r2["広告費_4週計"].to_numpy() - py2.to_numpy()).__abs__().max())}
json.dump(out, open(ROOT / "results" / "D_sql_check.json", "w"), ensure_ascii=False, indent=1)
print(out)
