"""F295 05：レビューを受けて足した確認。
相関の表の式に、コピュラの ρ=0.25 ではなく「損失で測ったピアソン相関」を入れると、分散効果はいくつになるか。
（6組の平均を全組に入れる場合と、組ごとのピアソン相関の表をそのまま入れる場合）
"""
import json, os
import numpy as np
from zz_f295_common import *
from zz_f295_01_main import OUT

KINDS = ["独立", "ガウス", "t", "グンベル", "裏返しクレイトン"]
marg, _ = build_marginals()
sa = np.array([capital(marg[:, k]) for k in range(4)])
A = json.load(open(os.path.join(OUT, "A_main.json")))
C = json.load(open(os.path.join(OUT, "C_reask.json")))
rng = np.random.default_rng(55000)
out = {}
for k in KINDS:
    X = to_losses(sample_U(k, 1_000_000, rng, rho=0.25), marg)
    P = np.corrcoef(X.T)
    iu = np.triu_indices(4, 1)
    pm = float(P[iu].mean())
    Pc = np.clip(P, -1, 1)
    # 組ごとの表が正定値でないときは固有値を0で切る（今回は不要だった場合も記録）
    w = np.linalg.eigvalsh(Pc)
    out[k] = dict(pearson_pairs=[float(x) for x in P[iu]], pearson_mean=pm, min_eig=float(w.min()),
                  formula_db_pearson_mean=float(formula_db(sa, equicorr(pm))),
                  formula_db_pearson_matrix=float(formula_db(sa, Pc)),
                  sim_db_var=A["res"][k]["db_var"], implied_rho_var=C["implied"]["0.25"][k]["implied_rho_var"])
json.dump(out, open(os.path.join(OUT, "D_review.json"), "w"), ensure_ascii=False, indent=1)
for k, v in out.items():
    print(f"{k:8s} ピアソン平均 {v['pearson_mean']:.3f}  式(平均) {v['formula_db_pearson_mean']*100:5.1f}%  式(組ごと) {v['formula_db_pearson_matrix']*100:5.1f}%  シミュレーション {v['sim_db_var']*100:5.1f}%  逆算ρ {v['implied_rho_var']:.2f}")
