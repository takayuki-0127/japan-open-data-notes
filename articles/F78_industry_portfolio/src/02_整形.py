"""02 整形：市区町村×産業（2014・2016・2021）と、都道府県の就業者（2002〜2025）を分析用の表にする"""
import numpy as np
import pandas as pd
from common import RAW, DATA

ind = pd.read_csv(RAW / "industries.csv", index_col=0)["industry"]
codes = list(ind.index)

m = pd.read_csv(RAW / "municipal_industry_emp.csv", dtype={"code": str, "pref": str})
# 18産業の合計を「民営の従業者」とする（公務は含まない）
for y in (2014, 2016, 2021):
    m[f"tot{y}"] = m[[f"{c}_{y}" for c in codes]].sum(axis=1, min_count=1)
m = m[(m["tot2016"] > 0) & (m["tot2021"] > 0) & (m["tot2014"] > 0) & m["pop2015"].notna()].copy()
m.to_csv(DATA / "municipal.csv", index=False)

# 都道府県：モデル推計値の就業者（千人）
rows, cur = {}, None
for line in open(RAW / "lfs_pref_model_estimates.txt", encoding="utf-8"):
    line = line.strip()
    if line.startswith("#T"):
        cur = line.split()[0][1:]
        continue
    if not line or line.startswith("#"):
        continue
    if cur == "T3":
        v = line.split(",")
        rows[int(v[0])] = [float(x) for x in v[1:48]]
emp = pd.DataFrame(rows).T.sort_index()
emp.columns = [f"{i:02d}" for i in range(1, 48)]
emp.index.name = "year"
emp.to_csv(DATA / "pref_employment_lfs.csv")
print(m.shape, emp.shape, emp.index.min(), emp.index.max())
