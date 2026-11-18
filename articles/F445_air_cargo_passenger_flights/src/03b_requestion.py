"""問い直し（結果を見てから足した）：国内の貨物が2025年に2019年より22%少ないのは、コロナ前からの減り方の延長でどこまで説明できるか。
2014〜2019年の年の貨物重量に対数の直線を当てはめて2025年まで延ばし、実際と比べる。座席キロ1,000あたりの貨物（kg）も出す。
出力：results/requestion.json、results/trend_domestic.csv"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
ann = pd.read_csv(R / "annual.csv")
out, rows = {}, []
for seg in ("total", "trunk", "local"):
    a = ann[ann.segment == seg].set_index("year")
    for base, (y0, y1) in (("2014-2019", (2014, 2019)), ("2016-2019", (2016, 2019))):
        yy = np.arange(y0, y1 + 1)
        b, c = np.polyfit(yy, np.log(a.loc[yy, "cargo_kg"].values), 1)
        for y in range(2014, 2026):
            rows.append({"segment": seg, "fit": base, "year": y, "actual_t": a.loc[y, "cargo_kg"] / 1000,
                         "trend_t": float(np.exp(c + b * y)) / 1000})
        pred25 = float(np.exp(c + b * 2025))
        act25, act19 = a.loc[2025, "cargo_kg"], a.loc[2019, "cargo_kg"]
        gap_total = act19 - act25
        gap_trend = act19 - pred25
        out[f"{seg}_{base}_trend_pct_per_year"] = round(100 * (np.exp(b) - 1), 2)
        out[f"{seg}_{base}_pred2025_t"] = round(pred25 / 1000)
        out[f"{seg}_{base}_actual_vs_trend_pct"] = round(100 * (act25 / pred25 - 1), 2)
        out[f"{seg}_{base}_share_of_gap_explained_by_trend_pct"] = round(100 * gap_trend / gap_total, 1)
    for y in (2014, 2019, 2020, 2022, 2025):
        out[f"{seg}_kg_per_1000seatkm_{y}"] = round(1000 * a.loc[y, "cargo_kg"] / a.loc[y, "seat_km"], 2)
pd.DataFrame(rows).round(1).to_csv(R / "trend_domestic.csv", index=False)
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
for k, v in out.items():
    print(k, v)
