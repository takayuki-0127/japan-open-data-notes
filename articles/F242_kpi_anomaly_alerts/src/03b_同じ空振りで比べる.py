"""03b 同じ空振りの回数で比べる：閾値を細かく変え、「1年に4回だけ空振りしてよい」ときに、
それぞれのルールで異常をどれだけ見つけられるかを比べる（乱数の種20通り）。"""
import importlib.util, numpy as np, pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(__file__))
spec = importlib.util.spec_from_file_location("ana", os.path.join(os.path.dirname(__file__), "03_分析.py"))
src = open(spec.origin).read().split("# ---- A. シミュレーション ----")[0]
ns = {"__file__": spec.origin}; exec(src, ns)
from detectors import d1_prev_day, d2_moving, d3_same_weekday, d4_stl, d5_calendar
simulate, score, SP, WD, NSEED = ns["simulate"], ns["score"], ns["SP"], ns["WD"], ns["NSEED"]
K = np.round(np.arange(2.0, 8.01, 0.25), 2)
rows = []
for seed in range(NSEED):
    ly, lab, inc = simulate(seed)
    zs = {"D2 28日平均": d2_moving(ly)[0], "D3 同じ曜日の中央値": d3_same_weekday(ly)[0],
          "D4b STL＋外れで尺度": d4_stl(ly)[2], "D5 D3＋暦": d5_calendar(ly, SP, WD)[0]}
    e1 = np.abs(d1_prev_day(ly)[0])
    for thr in np.arange(0.05, 0.61, 0.025):
        fa, df = score(e1 > np.log(1 + thr), lab, inc); nd = df[df.special == 0]
        rows.append(dict(seed=seed, method="D1 前日比", k=round(thr, 3), fa=fa, recall=nd.found.mean()))
    for m, z in zs.items():
        for k in K:
            a = np.abs(z) > (np.where(SP == 2, max(k, 6.0), k) if m.startswith("D5") else k)
            fa, df = score(a, lab, inc); nd = df[df.special == 0]
            rows.append(dict(seed=seed, method=m, k=k, fa=fa, recall=nd.found.mean()))
D = pd.DataFrame(rows)
D.groupby(["method", "k"])[["fa", "recall"]].mean().round(3).to_csv("results/A_frontier.csv")
out = []
for m, g in D.groupby("method"):
    gg = g.groupby("k")[["fa", "recall"]].mean().sort_values("fa")
    for budget in [2, 4, 12, 52]:
        ok = gg[gg.fa <= budget]
        out.append(dict(method=m, fa_budget_per_year=budget, recall=round(ok.recall.max(), 3) if len(ok) else np.nan,
                        k=ok.recall.idxmax() if len(ok) else np.nan))
O = pd.DataFrame(out); O.to_csv("results/A_recall_at_budget.csv", index=False); print(O.pivot(index="method", columns="fa_budget_per_year", values="recall"))
