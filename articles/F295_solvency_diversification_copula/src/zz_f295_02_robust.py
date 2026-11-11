"""F295 02：頑健性 R1〜R5（PLAN どおり）と、仮説 H5（自然災害の ξ）。"""
import json, os
import numpy as np
from zz_f295_common import *
from zz_f295_01_main import run, KINDS, OUT

MAIN = ["独立", "ガウス", "t", "グンベル", "裏返しクレイトン"]
rows = []


def add(tag, val, res, fdb):
    for k, v in res.items():
        rows.append(dict(check=tag, value=val, kind=k, db_var=v["db_var"], db_var_se=v["db_var_se"],
                         db_tvar=v["db_tvar"], db_tvar_se=v["db_tvar_se"], formula_db=fdb))


base_marg, _ = build_marginals()
s100 = np.full(4, TARGET)

# R1：シード（周辺分布とコピュラの両方）を5通り、年数 20万 vs 100万
for i, sd in enumerate([11, 22, 33, 44, 55]):
    marg, _ = build_marginals(seed=3000 + sd)
    add("R1_seed", sd, run(marg, MAIN, seed=40000 + sd), formula_db(s100, equicorr(0.25)))
add("R1_n200k", 200000, run(base_marg, MAIN, nb=5, bn=40_000), formula_db(s100, equicorr(0.25)))

# R2：相関 0.10・0.50、組み合わせごとに違う表
for rho in [0.10, 0.50]:
    add("R2_rho", rho, run(base_marg, MAIN, rho=rho), formula_db(s100, equicorr(rho)))
Rm = np.array([[1, 0.0, 0.25, 0.25],
               [0.0, 1, 0.25, 0.25],
               [0.25, 0.25, 1, 0.5],
               [0.25, 0.25, 0.5, 1]])
add("R2_matrix", "表", run(base_marg, ["独立", "ガウス", "t"], R=Rm), formula_db(s100, Rm))

# R3 / H5：自然災害の ξ
for xi in [0.3, 0.5, 0.7]:
    marg, _ = build_marginals(xi_cat=xi)
    add("R3_xi", xi, run(marg, MAIN), formula_db(s100, equicorr(0.25)))

# R4：t の自由度
for nu in [3, 6, 10, 30]:
    add("R4_nu", nu, run(base_marg, ["t"], nu=nu), formula_db(s100, equicorr(0.25)))

# R5：自然災害を2倍
marg, _ = build_marginals(scale_override=[2, 1, 1, 1])
sa = np.array([capital(marg[:, k]) for k in range(4)])
add("R5_cat2x", "2倍", run(marg, MAIN), formula_db(sa, equicorr(0.25)))

import pandas as pd
df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, "B_robustness.csv"), index=False, float_format="%.5f")
pd.set_option("display.width", 200)
print(df.assign(db_var=(df.db_var * 100).round(1), db_tvar=(df.db_tvar * 100).round(1),
                formula_db=(df.formula_db * 100).round(1))[["check", "value", "kind", "db_var", "db_tvar", "formula_db"]].to_string())
