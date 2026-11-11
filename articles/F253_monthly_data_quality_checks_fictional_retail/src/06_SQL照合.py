"""06 SQL 照合：sql/dq_checks.sql（Q01〜Q05・Q08、Q06 は参照 a だけ）を DuckDB で流し、pandas（src/dq_check.py）と同じ店×日×チェックが出るかを確かめる。
汚れを入れた月（seed 0〜4 の FY2025 の12か月、10種類ずつ）で比べる。会社・数字はすべて架空（合成データ）。"""
import json, pathlib, sys, warnings
import numpy as np
import pandas as pd
import duckdb
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dq_check as q
import sim_common as S
warnings.filterwarnings("ignore")
ROOT = S.ROOT
SQL = (ROOT / "sql" / "dq_checks.sql").read_text(encoding="utf-8")
g = S.load_gen()
st = pd.read_csv(ROOT / "data" / "in" / "dim_store.csv", parse_dates=["open_date", "close_date"], encoding="utf-8-sig")
recs, mism = [], []
for seed in range(5):
    fsd, cat = S.gen_mart(g, seed); rng = np.random.default_rng(500 + seed)
    for m in S.MONTHS[12:]:
        m0 = pd.Period(m, "M").start_time
        cur, cc, h, hc = q.split_month(fsd, cat, m)
        cur, cc, _ = S.inject(cur, cc, rng, S.eligible_stores(h, cur, m0))
        fp, _ = q.run_checks(cur, cc, h, hc, st, m, ref_mode="a")
        fp = fp[fp.check.isin(["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q08"])]
        con = duckdb.connect()
        for n, d in [("cur", cur), ("cat", cc), ("hist", h), ("expected", q.expected_rows(st, m))]:
            con.register("v", d); con.execute(f"CREATE TABLE {n} AS SELECT * FROM v"); con.unregister("v")
        con.execute(f"CREATE TABLE param AS SELECT DATE '{m0.date()}' AS m0, 1.5 AS t_pos, 2.0 AS t_waste")
        con.execute(SQL)
        fs = con.execute("SELECT chk, store_id, CAST(biz_date AS DATE) AS biz_date, metric FROM dq_flags").df()
        a = set(zip(fp.check, fp.store_id.astype(int), pd.to_datetime(fp.biz_date).dt.date, fp.metric))
        b = set(zip(fs.chk, fs.store_id.astype(int), pd.to_datetime(fs.biz_date).dt.date, fs.metric))
        recs.append(dict(seed=seed, month=m, pandas=len(a), sql=len(b), both=len(a & b), only_pandas=len(a - b), only_sql=len(b - a)))
        mism += [dict(seed=seed, month=m, side="pandas", item=str(x)) for x in a - b] + [dict(seed=seed, month=m, side="sql", item=str(x)) for x in b - a]
        con.close()
R = pd.DataFrame(recs)
R.to_csv(ROOT / "results" / "H_sql_vs_pandas.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(mism, columns=["seed", "month", "side", "item"]).to_csv(ROOT / "results" / "H_sql_vs_pandas_mismatch.csv", index=False, encoding="utf-8-sig")
print(R.sum(numeric_only=True).to_dict())
