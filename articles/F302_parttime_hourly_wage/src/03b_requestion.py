"""問い直し（結果を見てから足した）：
月給で比べると差は小さい。時給の差のうち、月給の伸びの差と、働く時間の縮み方の差は、それぞれどれだけか。
（log 時給 ＝ log 月給 − log 時間 なので、時給の伸び ＝ 月給の伸び ＋ 時間の縮み）"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "maikin_annual_by_type.csv", dtype={"size": str})
d = d[d["size"] == "T"]
r3 = lambda x: round(float(x), 3)
def g(typ, ind, col, a=2015, b=2025):
    s = d[(d.type == typ) & (d.ind == ind)].set_index("year")[col]
    return 100 * (np.log(s[b]) - np.log(s[a]))
out = {}
for typ in ("part", "general"):
    pay, hrs = g(typ, "TL", "sched_pay"), g(typ, "TL", "sched_hours")
    out[typ] = dict(monthly_pay_growth=r3(pay), hours_shrink=r3(-hrs), hourly_growth=r3(pay - hrs))
out["gap_hourly"] = r3(out["part"]["hourly_growth"] - out["general"]["hourly_growth"])
out["gap_from_monthly_pay"] = r3(out["part"]["monthly_pay_growth"] - out["general"]["monthly_pay_growth"])
out["gap_from_hours"] = r3(out["part"]["hours_shrink"] - out["general"]["hours_shrink"])
out["share_gap_from_hours"] = r3(out["gap_from_hours"] / out["gap_hourly"])
# 産業ごと：パートの時間の縮みと時給の伸び
rows = []
for i in list("CDEFGHIJKLMNOPQR"):
    rows.append(dict(ind=i, part_hourly=g("part", i, "sched_pay") - g("part", i, "sched_hours"), part_hours_shrink=-g("part", i, "sched_hours"),
                     part_monthly=g("part", i, "sched_pay")))
r = pd.DataFrame(rows); r.round(3).to_csv(RES / "requestion_by_industry.csv", index=False)
rho, p = stats.spearmanr(r.part_hours_shrink, r.part_hourly)
out["ind_spearman_hours_shrink_vs_hourly"] = r3(rho); out["ind_spearman_p"] = r3(p)
r2 = r[r.ind != "C"]
rho2, p2 = stats.spearmanr(r2.part_hours_shrink, r2.part_hourly)
out["ind_spearman_excl_mining"] = r3(rho2); out["ind_spearman_excl_mining_p"] = r3(p2)
# 年ごとのパートの所定内労働時間
hh = d[(d.ind == "TL")].pivot(index="year", columns="type", values="sched_hours")
hh.to_csv(RES / "requestion_hours_by_year.csv")
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(r.round(2).to_string())
