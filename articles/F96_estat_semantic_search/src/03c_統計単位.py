"""F96 03c 正解をゆるくした場合：上位10件に「正しい政府統計の表」が1つでも入るか（表題の条件は問わない）
03 の top50.npy を使う。出力：results/stat_level.csv
"""
import numpy as np, pandas as pd
from common import DATA, RES
from queries import NEEDS

tab = pd.read_csv(DATA / "tables.csv.gz", dtype={"id": str})
T = np.load(RES / "top50.npy", allow_pickle=True).item()
tk = {nd["id"]: nd["toukei"] for nd in NEEDS}
rows = []
for key, r in T.items():
    need, w, m = key.split("|")
    top = tab.toukei.values[r[:10]]
    rows.append(dict(need=need, wording=w, method=m, hit10_stat=float((top == tk[need]).any()),
                     n_stats_top10=len(set(top))))
df = pd.DataFrame(rows)
agg = df.groupby(["method", "wording"])[["hit10_stat", "n_stats_top10"]].mean().reset_index()
agg.to_csv(RES / "stat_level.csv", index=False)
print(agg.pivot_table(index="method", columns="wording", values=["hit10_stat", "n_stats_top10"]).round(3))
