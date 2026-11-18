"""問い直し（結果を見てから足した）：
2023年以降の値上げは、普通運賃と定期（通勤・通学）のどちらで大きかったのか。JR と JR以外で比べる。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
m = pd.read_csv(ROOT / "data" / "monthly.csv").set_index("period")
K = ["jr_regular", "jr_commuter", "jr_school", "pr_regular", "pr_commuter", "pr_school"]
mom = (m[K] / m[K].shift(1) - 1) * 100
rows = []
for p in [202304, 202404, 202504, 202604]:
    for k in K:
        rows.append({"period": p, "item": k, "mom": round(float(mom.loc[p, k]), 2)})
cum = {k: round(float((m.loc[202609, k] / m.loc[202302, k] - 1) * 100), 2) for k in K}
for k in K:
    rows.append({"period": "202302-202609", "item": k, "mom": cum[k]})
df = pd.DataFrame(rows); df.to_csv(R / "requestion_ticket_types.csv", index=False)
# 2023年2月以降で前月比が |0.5%| 以上の月（どの月に動いたか）
moves = {k: [int(p) for p, v in mom.loc[202303:, k].items() if abs(v) >= 0.5] for k in K}
out = {"april_mom": {str(p): {k: round(float(mom.loc[p, k]), 2) for k in K} for p in [202304, 202404, 202504, 202604]},
       "cum_202302_202609": cum, "months_moved_since_202303": moves,
       "march_mom_2023_2026": {str(p): {k: round(float(mom.loc[p, k]), 2) for k in K} for p in [202303, 202603]}}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
