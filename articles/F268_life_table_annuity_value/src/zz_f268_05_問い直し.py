"""05 問い直し（結果を見た後に足した）：
その年の生命表（期間生命表）で出した a65 は、その年に65歳になった人が実際に生きた死亡率（コーホート）で出した a65 と比べて、どれだけ低かったのか。
- 過去：1975〜1990年に65歳になった人。2024年までの実績の死亡率をそのまま追う（1990年に65歳の人は2024年に99歳）。
- これから：2024年に65歳になった人。死亡率は将来推計人口の中位・高位・低位に合わせた Lee–Carter の見通し（03 と同じ）。"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, SEXES, AGE_MAX, RATE_BASE, RATES, survival_from, annuity_due, qx_from_mx, a_x_from_mx

jmd = pd.read_csv(DATA / "jmd_mx.csv")
MX = {(s, y): jmd[(jmd.sex == s) & (jmd.year == y)].sort_values("age").mx.to_numpy() for s in SEXES for y in sorted(jmd.year.unique())}
LC = json.loads((RES / "lc_params.json").read_text())
LAST = 2024


def mx_at(s, year, case=None):
    """その年の死亡率（0..99歳と100歳以上）。2024年より後は Lee–Carter の見通し（2070年より後は2070年のまま）。"""
    if year <= LAST:
        return MX[(s, year)]
    if case is None:
        # 過去のコーホートで2024年より先に残るのは100歳以上だけ。2024年の死亡率のまま置く
        return MX[(s, LAST)]
    p = LC[s]
    b = np.array(p["b"])
    y = min(year, 2070)
    k24, k45, k70 = p["k2024"], p["k2045"][case], p["k2070"][case]
    k = (k24 + (k45 - k24) * (y - 2024) / (2045 - 2024)) if y <= 2045 else (k45 + (k70 - k45) * (y - 2045) / (2070 - 2045))
    return MX[(s, LAST)] * np.exp(b * (k - p["k2024"]))


def cohort_a(s, y65, rate=RATE_BASE, case=None, start=65, horizon=60):
    """y65 年に start 歳になった人の a（各年齢の死亡率はその年のもの）"""
    qs = []
    for t in range(horizon):
        age, year = start + t, y65 + t
        mx = mx_at(s, year, case)
        if age <= AGE_MAX:
            q = qx_from_mx(mx[:-1])[age]
        else:
            q = 1 - np.exp(-mx[-1])
        qs.append(q)
    qs = np.array(qs)
    p = np.empty(horizon); p[0] = 1.0; p[1:] = np.cumprod(1 - qs[:-1])
    return annuity_due(p, rate)


rows = []
for s in SEXES:
    for y in range(1975, 1991):
        per = a_x_from_mx(MX[(s, y)], 65, RATE_BASE)
        coh = cohort_a(s, y)
        per5 = a_x_from_mx(MX[(s, y + 5)], 65, RATE_BASE)
        rows.append({"sex": s, "kind": "過去（実績）", "year65": y, "case": "実績", "period_a65": per, "cohort_a65": coh,
                     "period_short_pct": per / coh - 1, "period_plus5_short_pct": per5 / coh - 1})
    for case in ["死亡中位", "死亡高位", "死亡低位"]:
        per = a_x_from_mx(MX[(s, 2024)], 65, RATE_BASE)
        coh = cohort_a(s, 2024, case=case)
        rows.append({"sex": s, "kind": "これから（見通し）", "year65": 2024, "case": case, "period_a65": per, "cohort_a65": coh,
                     "period_short_pct": per / coh - 1, "period_plus5_short_pct": np.nan})
df = pd.DataFrame(rows)
df.to_csv(RES / "reask_cohort_vs_period.csv", index=False)

# 割引率を変えた場合（過去：1985〜1990年の平均、これから：中位）
rr = []
for s in SEXES:
    for rate in RATES:
        past = np.mean([a_x_from_mx(MX[(s, y)], 65, rate) / cohort_a(s, y, rate) - 1 for y in range(1985, 1991)])
        fut = a_x_from_mx(MX[(s, 2024)], 65, rate) / cohort_a(s, 2024, rate, case="死亡中位") - 1
        rr.append({"sex": s, "rate": rate, "past_1985_1990_mean": past, "future_2024_mid": fut})
rr = pd.DataFrame(rr)
rr.to_csv(RES / "reask_rate_robustness.csv", index=False)

summ = {}
for s in SEXES:
    t = df[(df.sex == s) & (df.kind == "過去（実績）")]
    f = df[(df.sex == s) & (df.kind == "これから（見通し）")].set_index("case")
    summ[s] = {"past_1975_1990_range": [float(t.period_short_pct.min()), float(t.period_short_pct.max())],
               "past_1985_1990_mean": float(t[t.year65 >= 1985].period_short_pct.mean()),
               "past_plus5_1985_1990_mean": float(t[t.year65 >= 1985].period_plus5_short_pct.mean()),
               "y1990": {"period": float(t[t.year65 == 1990].period_a65.iloc[0]), "cohort": float(t[t.year65 == 1990].cohort_a65.iloc[0])},
               "future_2024": {c: float(f.loc[c, "period_short_pct"]) for c in f.index},
               "future_2024_cohort": {c: float(f.loc[c, "cohort_a65"]) for c in f.index},
               "period_2024": float(f.period_a65.iloc[0])}
(RES / "reask_main.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1))
print(json.dumps(summ, ensure_ascii=False, indent=1))
print(rr.to_string())
