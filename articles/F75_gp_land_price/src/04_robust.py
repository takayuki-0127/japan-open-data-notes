"""頑健性：カーネルの形、ブロックの大きさ、商業地、ハイパーパラメータ推定の点数（首都圏）"""
import numpy as np, pandas as pd
from common import RES, load, score
import importlib
cv = importlib.import_module("02_cv")

rows = []
d = load("住宅地"); d = d[d["area"] == "首都圏"].reset_index(drop=True)
# 1) カーネルの形（20km ブロック）
for kn in ["matern05", "matern25", "rbf", "rq"]:
    for m in ["gp_map", "rk"]:
        if m == "rk" and kn in ("matern25", "rq"):
            continue
        p, s, k = cv.run(d, "首都圏", m, "blk20", tag=f"kern-{kn}", kern_name=kn)
        rows.append(dict(check=f"カーネル {kn}", model=m, cv="blk20", **score(d["y"].values, p, s)))
# 2) ブロックの大きさ
for b in ["blk10", "blk5"]:
    for m in ["knn10", "gp_map", "rk", "lgbm"]:
        p, s, k = cv.run(d, "首都圏", m, b, tag="blk")
        rows.append(dict(check=f"ブロック {b[3:]}km", model=m, cv=b, **score(d["y"].values, p, s)))
# 3) ハイパーパラメータの推定点数
p, s, k = cv.run(d, "首都圏", "gp_map", "blk20", tag="nhyper2000", n_hyper=2000)
rows.append(dict(check="推定点数 2000", model="gp_map", cv="blk20", **score(d["y"].values, p, s)))
# 4) 商業地
c = load("商業地"); c = c[c["area"] == "首都圏"].reset_index(drop=True)
for kind in ["random", "blk20"]:
    for m in ["knn10", "gp_map", "rk", "lgbm"]:
        p, s, k = cv.run(c, "首都圏商業", m, kind, tag="com")
        rows.append(dict(check="商業地", model=m, cv=kind, **score(c["y"].values, p, s)))
out = pd.DataFrame(rows)
out.to_csv(RES / "robustness.csv", index=False)
print(out[["check", "model", "cv", "median_ape", "r2", "cover90"]].round(3).to_string())
