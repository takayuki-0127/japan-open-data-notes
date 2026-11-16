"""問い直し：規模の差は「大きい会社どうし」でもあるのか、どの規模がどれだけの速さで上がったのか。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "managers_by_size.csv")
SIX = ["5,000人以上", "1,000~4,999人", "300~999人", "100~299人", "30~99人", "10~29人"]
BIG = SIX[:4]
P = d[d.role == "kacho_up"].pivot_table(index="year", columns="size", values="pct").dropna(how="all")
out = {"question": "規模の差は、100人以上の会社どうしでもあるのか。どの規模が年あたりどれだけ上がったのか（課長相当職以上）"}
rows = []
for y in P.index:
    big = P.loc[y, BIG]
    rows.append({"year": int(y), "big4_min": round(float(big.min()), 2), "big4_max": round(float(big.max()), 2),
                 "big4_range": round(float(big.max() - big.min()), 2),
                 "s30_99_minus_big4_mean": round(float(P.loc[y, "30~99人"] - big.mean()), 2),
                 "s10_29_minus_big4_mean": round(float(P.loc[y, "10~29人"] - big.mean()), 2)})
sp = pd.DataFrame(rows); sp.to_csv(R / "requestion_spread.csv", index=False)
out["spread_2011"] = rows[0]; out["spread_2025"] = rows[-1]
out["big4_range_mean"] = round(float(sp.big4_range.mean()), 2)
out["s10_29_minus_big4_mean_mean"] = round(float(sp.s10_29_minus_big4_mean.mean()), 2)
# 年あたりの上がり方（2011〜2025年度の最小二乗の傾き）
x = P.index.values.astype(float)
slope = {s: round(float(np.polyfit(x, P[s].values, 1)[0]), 3) for s in SIX + ["10人以上"]}
out["slope_pt_per_year_2011_2025"] = slope
pd.Series(slope, name="pt_per_year").rename_axis("size").to_csv(R / "requestion_slope.csv")
# 役員と部長の差（小さい会社ほど役員の方が高いか）
Q = d[d.year == 2025].pivot_table(index="size", columns="role", values="pct")
out["yakuin_minus_bucho_2025"] = {s: round(float(Q.loc[s, "yakuin"] - Q.loc[s, "bucho"]), 2) for s in SIX}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print("requestion ok")
