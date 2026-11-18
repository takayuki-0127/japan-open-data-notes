"""問い直し（結果を見てから足した）：
営業用普通車の積載効率が2024年度に41.4%へ上がり、2025年度に39.1%へ下がったのは、どの大きさの車の動きか。
全体の変化を「大きさごとの積載効率の変化」と「能力トンキロの構成（どの大きさの車が多く走ったか）の変化」に分ける。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
W = pd.read_csv(R / "fy_metrics.csv")
sizes = ["biz_lt3", "biz_3to6_5", "biz_6_5to11", "biz_11to16", "biz_16plus"]
S = W[W.group.isin(sizes)].pivot_table(index="fy", columns="group", values=["tonkm", "cap_tonkm", "lr", "load_when_loaded"])
eff = S["tonkm"] / S["cap_tonkm"] * 100
share = S["cap_tonkm"].div(S["cap_tonkm"].sum(axis=1), axis=0)
tot = (S["tonkm"].sum(axis=1) / S["cap_tonkm"].sum(axis=1)) * 100
rows = []; out = {}
for y0, y1 in [(2020, 2023), (2023, 2024), (2024, 2025), (2020, 2025)]:
    within = ((eff.loc[y1] - eff.loc[y0]) * (share.loc[y0] + share.loc[y1]) / 2)
    comp = ((share.loc[y1] - share.loc[y0]) * (eff.loc[y0] + eff.loc[y1]) / 2)
    for g in sizes:
        rows.append({"from": y0, "to": y1, "group": g, "eff0": eff.loc[y0, g], "eff1": eff.loc[y1, g], "share0": share.loc[y0, g] * 100, "share1": share.loc[y1, g] * 100,
                     "within": within[g], "composition": comp[g], "lr0": S["lr"].loc[y0, g], "lr1": S["lr"].loc[y1, g],
                     "lwl0": S["load_when_loaded"].loc[y0, g], "lwl1": S["load_when_loaded"].loc[y1, g]})
    out[f"{y0}-{y1}"] = {"total0": round(float(tot.loc[y0]), 2), "total1": round(float(tot.loc[y1]), 2), "change": round(float(tot.loc[y1] - tot.loc[y0]), 2),
                         "within_sum": round(float(within.sum()), 2), "composition_sum": round(float(comp.sum()), 2),
                         "within_by_size": {g: round(float(v), 2) for g, v in within.items()}, "eff_change_by_size": {g: round(float(eff.loc[y1, g] - eff.loc[y0, g]), 2) for g in sizes}}
pd.DataFrame(rows).round(4).to_csv(R / "requestion_size_shift_share.csv", index=False)
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
