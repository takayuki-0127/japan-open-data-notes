"""T-SQL を DuckDB で動かし（FLOAT→DOUBLE に読み替え）、Python（common.zstat）の結果と照合する。
SQL Server はこの作業環境にないので、SQL Server では動かしていない。"""
import os, sys, json, re
import numpy as np, pandas as pd, duckdb
sys.path.insert(0, os.path.dirname(__file__))
from common import *
sql = open("sql/01_日ごとの累積とzと止める判定_tsql.sql", encoding="utf-8").read()
sql_duck = re.sub(r"\bFLOAT\b", "DOUBLE", sql)
b = pd.read_csv("results/C_bounds_4looks.csv")[["day", "obf"]].rename(columns={"obf": "bound"})
out = {}
for name in ["H0", "H1"]:
    d = pd.read_csv(f"data/example_test_{name}_daily.csv")
    con = duckdb.connect(); con.register("ab_daily", d); con.register("seq_bounds", b)
    r = con.execute(sql_duck).df()
    # Python 側
    w = d.pivot(index="day", columns="arm", values=["visitors", "conversions"]).cumsum()
    zp = zstat(w[("conversions", "A")].values, w[("conversions", "B")].values, w[("visitors", "A")].values)
    diff = float(np.max(np.abs(r["z"].values - zp)))
    naive_py = np.maximum.accumulate(np.abs(zp) >= norm.ppf(0.975)).astype(int)
    seqb = b.set_index("day")["bound"].reindex(range(1, 15)).values
    seq_py = np.maximum.accumulate(np.nan_to_num(np.abs(zp) >= np.where(np.isnan(seqb), np.inf, seqb))).astype(int)
    out[name] = dict(rows=len(r), max_abs_diff_z=diff, naive_match=bool((r["naive_stop"].values == naive_py).all()),
                     seq_match=bool((r["seq_stop"].values == seq_py).all()),
                     naive_first_day=int(r.loc[r.naive_stop == 1, "day"].min()) if (r.naive_stop == 1).any() else None,
                     seq_first_day=int(r.loc[r.seq_stop == 1, "day"].min()) if (r.seq_stop == 1).any() else None)
    r.to_csv(f"results/F_sql_output_{name}.csv", index=False)
json.dump(out, open("results/sql_check.json", "w"), ensure_ascii=False, indent=1)
print(out)
