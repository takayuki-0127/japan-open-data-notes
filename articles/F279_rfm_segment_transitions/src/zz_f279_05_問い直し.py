"""05 問い直し（結果を見た後で足した）：区分ごとのもう一度買う割合は、水準は時点で動いたが、
区分の順番（どの区分が買いやすいか）と、全体に対する倍率は安定しているか。"""
import json, sys, pathlib, numpy as np, pandas as pd
from scipy.stats import spearmanr
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zz_f279_common import *
RES = ROOT / "results"
inv = load()
rows = []
for t in SNAPS:
    g = snapshot(inv, t)
    rate = g.groupby("seg")["rebuy"].mean().reindex(SEGS)
    rows.append(pd.DataFrame({"t": str(t.date()), "seg": SEGS, "rate": rate.values,
                              "lift": (rate / g["rebuy"].mean()).values, "overall": g["rebuy"].mean(),
                              "n": g.groupby("seg").size().reindex(SEGS).values}))
L = pd.concat(rows)
L.round(4).to_csv(RES / "E_reask_lift.csv", index=False)
P = L.pivot(index="seg", columns="t", values="rate").reindex(SEGS)
Q = L.pivot(index="seg", columns="t", values="lift").reindex(SEGS)
ts = list(P.columns)
rho = [spearmanr(P[ts[0]], P[c]).statistic for c in ts]
rho_adj = [spearmanr(P[a], P[b]).statistic for a, b in zip(ts[:-1], ts[1:])]
first, last = ts[0], ts[-1]
lift_diff = (Q[last] - Q[first])
out = dict(overall_rate={c: float(L[L.t == c]["overall"].iloc[0]) for c in ts},
           spearman_vs_first=[round(float(x), 3) for x in rho],
           spearman_adjacent_min=float(min(rho_adj)),
           rate_diff_first_last=(P[last] - P[first]).round(4).to_dict(),
           lift_first=Q[first].round(3).to_dict(), lift_last=Q[last].round(3).to_dict(),
           lift_within_0p15=int((lift_diff.abs() <= 0.15).sum()),
           rate_within_10pt=int(((P[last] - P[first]).abs() <= 0.10).sum()))
# 季節：結果の期間（6か月）に11月が入るか
out["nov_in_outcome"] = {c: any(((pd.Timestamp(c) + pd.DateOffset(months=k)).month == 11) for k in range(6)) for c in ts}
json.dump(out, open(RES / "F_reask.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
