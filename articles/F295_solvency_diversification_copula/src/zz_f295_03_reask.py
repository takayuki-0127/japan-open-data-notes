"""F295 03：問い直し（結果を見た後に足した）。
「相関の表の式で、裾が一緒に動く場合の資本を再現するには、表にいくつの相関を入れればよいか（逆算した相関）」と、
それが損失データで測る相関（ピアソン・スピアマン）とどれだけ違うか。
"""
import json, os
import numpy as np
from scipy import stats
from zz_f295_common import *
from zz_f295_01_main import run, OUT

KINDS = ["独立", "ガウス", "t", "グンベル", "裏返しクレイトン", "共単調"]
marg, _ = build_marginals()
sa = np.array([capital(marg[:, k]) for k in range(4)])
sat = np.array([tvar_capital(marg[:, k]) for k in range(4)])


def implied_rho(agg, s):
    """sqrt(s' R(rho) s) = agg を満たす、すべて同じ相関 rho。"""
    s = np.asarray(s, float)
    off = s.sum() ** 2 - (s ** 2).sum()
    return float((agg ** 2 - (s ** 2).sum()) / off)


out = {}
for rho in [0.10, 0.25, 0.50]:
    res = run(marg, KINDS, rho=rho, seed=52000)
    for k, v in res.items():
        out.setdefault(str(rho), {})[k] = dict(
            db_var=v["db_var"], db_tvar=v["db_tvar"],
            implied_rho_var=implied_rho(v["agg_var"], sa), implied_rho_tvar=implied_rho(v["agg_tvar"], sat))

# 損失データで測る相関（ρ=0.25、20万年、6組の平均）
rng = np.random.default_rng(53000)
corr = {}
for k in KINDS:
    X = to_losses(sample_U(k, 200000, rng, rho=0.25), marg)
    P = np.corrcoef(X.T)[np.triu_indices(4, 1)].mean()
    Sp = stats.spearmanr(X).statistic[np.triu_indices(4, 1)].mean()
    corr[k] = dict(pearson=float(P), spearman=float(Sp))
json.dump(dict(implied=out, data_corr=corr), open(os.path.join(OUT, "C_reask.json"), "w"), ensure_ascii=False, indent=1)
for rho, d in out.items():
    print("rho", rho, {k: (round(v["implied_rho_var"], 3), round(v["implied_rho_tvar"], 3)) for k, v in d.items()})
print({k: (round(v["pearson"], 3), round(v["spearman"], 3)) for k, v in corr.items()})
