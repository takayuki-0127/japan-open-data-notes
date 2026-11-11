"""F295 01：本計算。6つの依存の形で、分散効果（VaR99.5・TVaR99.5）を計る。
100万年 = 20万年 × 5 ブロック（ブロックごとの値の散らばりでモンテカルロの誤差を測る）。
"""
import json, os
import numpy as np
from zz_f295_common import *

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(OUT, exist_ok=True)
KINDS = ["独立", "ガウス", "t", "グンベル", "裏返しクレイトン", "共単調"]
NB, BN = 5, 200_000
RHO = 0.25


def run(marg, kinds=KINDS, seed=29501, rho=RHO, nu=4, R=None, nb=NB, bn=BN):
    res = {}
    for j, k in enumerate(kinds):
        rng = np.random.default_rng([seed, j])
        Xs = [to_losses(sample_U(k, bn, rng, rho=rho, nu=nu, R=R), marg) for _ in range(nb)]
        X = np.vstack(Xs)
        m = measures(X)
        blocks = [measures(x) for x in Xs]
        for key in ["db_var", "db_tvar"]:
            v = np.array([b[key] for b in blocks])
            m[key + "_se"] = float(v.std(ddof=1) / np.sqrt(nb))
        res[k] = {a: float(b) for a, b in m.items()}
    return res


if __name__ == "__main__":
    marg, sc = build_marginals()
    sa = np.array([capital(marg[:, k]) for k in range(4)])
    sat = np.array([tvar_capital(marg[:, k]) for k in range(4)])
    R = equicorr(RHO)
    res = run(marg)
    # コピュラのケンドールの τ の確認
    rng = np.random.default_rng(777)
    taus = {k: float(kendall_check(sample_U(k, 40000, rng, rho=RHO))) for k in ["ガウス", "t", "グンベル", "裏返しクレイトン"]}
    # 上の裾の依存（2つのリスクが同時に上位0.5%に入る割合 ÷ 0.005）
    rng = np.random.default_rng(778)
    tail = {}
    for k in KINDS:
        U = sample_U(k, 400000, rng, rho=RHO)
        tail[k] = float(np.mean((U[:, 0] > Q) & (U[:, 1] > Q)) / (1 - Q))
    out = dict(
        modules=MODULES, scales=sc.tolist(), standalone_var=sa.tolist(), standalone_tvar=sat.tolist(),
        marg_mean=marg.mean(0).tolist(), marg_q995=np.quantile(marg, Q, axis=0).tolist(),
        rho=RHO, tau=float(tau_from_rho(RHO)), tau_check=taus, tail_joint=tail,
        formula_db=float(formula_db(sa, R)), formula_db_tvar=float(formula_db(sat, R)), res=res)
    json.dump(out, open(os.path.join(OUT, "A_main.json"), "w"), ensure_ascii=False, indent=1)
    for k, v in res.items():
        print(f"{k:8s} VaR分散効果 {v['db_var']*100:6.1f}±{v['db_var_se']*100:.1f}  TVaR分散効果 {v['db_tvar']*100:6.1f}±{v['db_tvar_se']*100:.1f}  合計資本 {v['agg_var']:.1f}")
    print("式の分散効果", round(out["formula_db"] * 100, 1), "単独", sa.round(1), "単独TVaR", sat.round(1))
    print("tau", taus, "同時に上位0.5%", tail)
