"""F243 05 SQL 検算：sql/decomp_tsql.sql（T-SQL の書き方）を DuckDB で流し、pandas の結果と比べる。
SQL Server では動かしていない（N'..' と OVER(PARTITION BY) は DuckDB でもそのまま動く）。"""
import os, duckdb, pandas as pd, numpy as np
B = os.path.join(os.path.dirname(__file__), "..")
k = pd.read_csv(f"{B}/data/kakei_items.csv").rename(columns={"group": "grp"})
k = k[k.grp != "光熱"]
con = duckdb.connect(); con.register("kakei_items", k)
q1, q2 = [x.strip() for x in open(f"{B}/sql/decomp_tsql.sql").read().split(";") if "SELECT" in x]
g = con.execute(q1).df().set_index("grp").sort_index()
m = con.execute(q2).df().set_index("grp").sort_index()
G = pd.read_csv(f"{B}/results/B_group_2019_2024.csv").set_index("group").sort_index()
MX = pd.read_csv(f"{B}/results/B_mix_rate_by_group.csv"); MX = MX[MX["期間"] == "2019→2024"].set_index("群").sort_index()
d1 = max(abs(g.price_eff - G["価格_S"]).max(), abs(g.qty_eff - G["量_S"]).max())
d2 = max(abs(m.rate_eff - MX["値段の効果"]).max(), abs(m.mix_eff - MX["構成の効果"]).max())
r = pd.DataFrame({"検算": ["群別の値段・量", "100gあたり平均価格の率・構成"], "最大の差": [d1, d2], "行数": [len(g), len(m)]})
r.to_csv(f"{B}/results/E_sql_check.csv", index=False); print(r)
