"""問い直し（結果を見てから足した）：値下げの前（2015〜2019年）の動きが続いていたら、2025年の支出はいくらだったか。
年齢別に、2015〜2019年の直線を2025年まで延ばし、実際の値との差を見る。年齢の構成は各年の実際の構成を使う。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
age = pd.read_csv(ROOT / "data" / "kakei_age.csv")
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
M = age[age.item == "mobile"].pivot(index="year", columns="age", values="value")
D = age[age.item == "dist"].pivot(index="year", columns="age", values="value")[AGES]
D = D.div(D.sum(axis=1), axis=0)
yrs = np.arange(2015, 2026)
rows = []
for a in AGES + ["平均"]:
    y = M.loc[2015:2019, a].values
    k, c0 = np.polyfit(np.arange(2015, 2020) - 2015, y, 1)
    trend = c0 + k * (yrs - 2015)
    for yr, tv in zip(yrs, trend):
        rows.append({"age": a, "year": int(yr), "actual": float(M.loc[yr, a]), "trend_2015_2019": round(float(tv), 1)})
T = pd.DataFrame(rows)
T.to_csv(R / "requestion_trend.csv", index=False)
p = T.pivot(index="year", columns="age", values="trend_2015_2019")
# 年齢別の延長を、各年の実際の年齢構成で重みづけした平均
cf = (p[AGES] * D).sum(axis=1)
act = M["平均"]
out = {
    "trend_slope_avg_yen_per_year": round(float(np.polyfit(np.arange(5), M.loc[2015:2019, "平均"].values, 1)[0]), 0),
    "cf_2025_weighted": round(float(cf.loc[2025]), 0), "cf_2025_avg_direct": round(float(p.loc[2025, "平均"]), 0),
    "actual_2025": float(act.loc[2025]),
    "gap_2025_weighted_yen": round(float(act.loc[2025] - cf.loc[2025]), 0),
    "gap_2025_weighted_pct": round(float((act.loc[2025] / cf.loc[2025] - 1) * 100), 1),
    "gap_2025_by_age_pct": {a: round(float((M.loc[2025, a] / p.loc[2025, a] - 1) * 100), 1) for a in AGES},
    "cum_gap_2021_2025_weighted_yen": round(float((act.loc[2021:2025] - cf.loc[2021:2025]).sum()), 0),
}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
