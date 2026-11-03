"""評価指標：Harrell の C、Uno の C（τまで）、時点別 AUC、統合 Brier スコア、較正（十分位ごとの予測と KM の実績）。"""
import numpy as np, pandas as pd
from sksurv.metrics import concordance_index_censored, concordance_index_ipcw, cumulative_dynamic_auc, integrated_brier_score, brier_score
from sksurv.nonparametric import kaplan_meier_estimator
from sksurv.util import Surv
from models import G


def km_at(T, E, t):
    if len(T) == 0:
        return np.nan
    x, s = kaplan_meier_estimator(E.astype(bool), T)
    i = np.searchsorted(x, t, side="right") - 1
    return 1.0 if i < 0 else s[i]


def evaluate(S, Ttr, Etr, Tte, Ete, tau=8.0, t_auc=(1, 3, 5), t_cal=(3, 5)):
    ytr = Surv.from_arrays(Etr.astype(bool), Ttr); yte = Surv.from_arrays(Ete.astype(bool), Tte)
    gi = {round(g, 2): j for j, g in enumerate(G)}
    t_score = 5.0 if tau >= 5 else 3.0
    risk = 1 - S[:, gi[t_score]]
    res = {"C_harrell": concordance_index_censored(Ete.astype(bool), Tte, risk)[0],
           "C_uno": concordance_index_ipcw(ytr, yte, risk, tau=tau)[0]}
    ta = [t for t in t_auc if t < tau]
    auc, _ = cumulative_dynamic_auc(ytr, yte, np.column_stack([1 - S[:, gi[t]] for t in ta]), ta)
    for t, a in zip(ta, auc):
        res[f"AUC_{t}y"] = a
    gsel = [j for j, g in enumerate(G) if g <= min(tau, Tte.max() - 1e-6)]
    res["IBS"] = integrated_brier_score(ytr, yte, S[:, gsel], G[gsel])
    # 何も特徴量を使わない KM（全員同じ曲線）の IBS を基準に、改善率も出す
    S0 = np.tile([km_at(Ttr, Etr, g) for g in G[gsel]], (len(Tte), 1))
    res["IBS_KM"] = integrated_brier_score(ytr, yte, S0, G[gsel])
    cal_rows = []
    for t in t_cal:
        if t >= tau:
            continue
        F = 1 - S[:, gi[t]]
        q = pd.qcut(pd.Series(F).rank(method="first"), 10, labels=False).values
        obs = np.array([1 - km_at(Tte[q == k], Ete[q == k], t) for k in range(10)])
        pred = np.array([F[q == k].mean() for k in range(10)])
        res[f"ICI_{t}y"] = np.mean(np.abs(pred - obs))
        res[f"CITL_{t}y"] = F.mean() - (1 - km_at(Tte, Ete, t))
        res[f"top10_obs_{t}y"] = obs[9]; res[f"bottom10_obs_{t}y"] = obs[0]
        for k in range(10):
            cal_rows.append({"t": t, "decile": k + 1, "pred": pred[k], "obs": obs[k]})
    return res, cal_rows
