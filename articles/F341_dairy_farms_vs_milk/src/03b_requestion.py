"""問い直し（結果を見てから足した）。
Q：1985〜2024年の全体ではほぼ埋め合わせたのに、1996年の山からは生乳が減った。
   期間ごとに、戸数・規模・乳量のどれが変わったのか（5年ごとの年平均の対数変化）。
結果は results/requestion.json と results/requestion_periods.csv。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
idx = pd.read_csv(R / "index_series.csv").set_index("year")
periods = [(1985, 1990), (1990, 1996), (1996, 2000), (2000, 2005), (2005, 2010), (2010, 2015), (2015, 2020), (2020, 2024)]
rows = []
for a, b in periods:
    n = b - a
    f = 100 * np.log(idx.loc[b, "farms"] / idx.loc[a, "farms"]) / n
    s_ = 100 * np.log(idx.loc[b, "cows_per_farm"] / idx.loc[a, "cows_per_farm"]) / n
    y = 100 * np.log(idx.loc[b, "yield_kg"] / idx.loc[a, "yield_kg"]) / n
    m = 100 * np.log(idx.loc[b, "milk"] / idx.loc[a, "milk"]) / n
    rows.append({"period": f"{a}–{b}", "years": n, "farms": round(f, 2), "scale": round(s_, 2), "yield": round(y, 2),
                 "milk": round(m, 2), "check": round(f + s_ + y - m, 6)})
per = pd.DataFrame(rows)
per.to_csv(R / "requestion_periods.csv", index=False)
# 1996年までと1996年からの比較
def window(a, b):
    n = b - a
    return {k: round(100 * np.log(idx.loc[b, c] / idx.loc[a, c]) / n, 2) for k, c in
            [("farms", "farms"), ("scale", "cows_per_farm"), ("yield", "yield_kg"), ("milk", "milk")]}
out = {"periods": per.set_index("period").to_dict(orient="index"), "1985_1996": window(1985, 1996), "1996_2024": window(1996, 2024),
       "2022_2023": window(2022, 2023), "2023_2024": window(2023, 2024)}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(per.to_string()); print(json.dumps({k: v for k, v in out.items() if k != "periods"}, ensure_ascii=False))
