"""04 の SQL を DuckDB で流し、pandas の同じ計算と照合する"""
from pathlib import Path
import duckdb, pandas as pd, numpy as np
B = Path(__file__).resolve().parents[1]
d = pd.read_csv(B / "data/lodging_pref_monthly_2011_2025.csv", parse_dates=["date"])
d["ym"] = d.date.dt.year * 12 + d.date.dt.month
lodging = d[["pref", "ym", "japanese"]]
sql = (B / "src/04_前年比とベースライン.sql").read_text().replace("N'", "'").replace("NVARCHAR", "VARCHAR")
q = duckdb.sql(sql).df()
# pandas
K = ['27大阪府', '25滋賀県', '26京都府', '28兵庫県', '29奈良県', '30和歌山県']
o = d[d.pref == '27大阪府'].set_index('ym')['japanese'].astype(float)
t = d[~d.pref.isin(K)].groupby('ym')['japanese'].sum().astype(float)
rows = []
for ym in range(24304, 24311):
    base = o[ym - 12] * t[ym] / t[ym - 12]
    rows.append(dict(ym=ym, osaka_now=o[ym], baseline=base, eff_vs_baseline=o[ym] / base - 1))
p = pd.DataFrame(rows)
tot = dict(ym=99999, osaka_now=p.osaka_now.sum(), baseline=p.baseline.sum())
tot["eff_vs_baseline"] = tot["osaka_now"] / tot["baseline"] - 1
p = pd.concat([p, pd.DataFrame([tot])], ignore_index=True)
m = q.merge(p, on="ym", suffixes=("_sql", "_py"))
m["diff"] = (m.eff_vs_baseline_sql - m.eff_vs_baseline_py).abs()
m.to_csv(B / "results/H_sql_check.csv", index=False)
print(q.round(4).to_string()); print("max diff", m["diff"].max(), "rows", len(m))
