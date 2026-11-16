"""問い直し（結果を見てから足した）：2023→2025年に差が広がったのは、運転者の伸びが鈍ったからか、全体が速く伸びたからか。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
df = pd.read_csv(ROOT / "data" / "wage_long.csv")
t = df[df.age_class == "計"].set_index(["year", "who"])
t = t.assign(hourly_sched=t.shoteinai * 1000 / t.hours_sched)
out = {}
rows = []
for kind, who in [("large", "large_total"), ("other", "other_total")]:
    for y0, y1 in [(2020, 2023), (2023, 2025)]:
        d0, d1 = t.loc[(y0, who)], t.loc[(y1, who)]
        a0, a1 = t.loc[(y0, "all_total")], t.loc[(y1, "all_total")]
        r = dict(kind=kind, period=f"{y0}-{y1}",
                 drv_hourly_growth=(d1.hourly_sched / d0.hourly_sched - 1) * 100,
                 all_hourly_growth=(a1.hourly_sched / a0.hourly_sched - 1) * 100,
                 drv_shoteinai_growth=(d1.shoteinai / d0.shoteinai - 1) * 100,
                 drv_kimatte_growth=(d1.kimatte / d0.kimatte - 1) * 100,
                 all_kimatte_growth=(a1.kimatte / a0.kimatte - 1) * 100,
                 drv_ot_hours_change=d1.hours_ot - d0.hours_ot,
                 drv_sched_hours_change=d1.hours_sched - d0.hours_sched)
        r["gap_change_pt"] = ((1 + r["drv_hourly_growth"] / 100) / (1 + r["all_hourly_growth"] / 100) - 1) * 100
        rows.append(r)
q = pd.DataFrame(rows)
q.to_csv(R / "requestion_growth.csv", index=False, float_format="%.4f")
for r in rows:
    out[f"{r['kind']}_{r['period']}"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items() if k not in ("kind", "period")}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(q.round(1).to_string())
