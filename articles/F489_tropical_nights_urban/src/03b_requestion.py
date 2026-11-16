"""問い直し（結果を見てから足した）：近くの大都市と15地点を組にして、熱帯夜の日数と日最低気温の「差」がどう動いたかを見る。
組（地理的に近い地点）：東京–銚子、横浜–銚子、京都–彦根、大阪–彦根、神戸–多度津、広島–多度津、福岡–浜田、鹿児島–宮崎。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
a = pd.read_csv(ROOT / "data" / "annual.csv")
a = a[(a.year >= 1961) & (a.year <= 2025)].copy()
a.loc[a.days_tmin_ge25_flag == 1, "days_tmin_ge25"] = np.nan
a.loc[a.tmin_mean_flag == 1, "tmin_mean"] = np.nan
PAIRS = [("東京", "銚子"), ("横浜", "銚子"), ("京都", "彦根"), ("大阪", "彦根"), ("神戸", "多度津"), ("広島", "多度津"), ("福岡", "浜田"), ("鹿児島", "宮崎")]
tn = a.pivot(index="year", columns="station", values="days_tmin_ge25")
tm = a.pivot(index="year", columns="station", values="tmin_mean")
rows, series = [], {}
for c, r in PAIRS:
    d_tn = (tn[c] - tn[r]).dropna(); d_tm = (tm[c] - tm[r]).dropna()
    rows.append({"pair": f"{c}–{r}", "tn_diff_slope_per_decade": round(float(stats.theilslopes(d_tn, d_tn.index)[0] * 10), 2),
                 "tmin_diff_slope_per_decade": round(float(stats.theilslopes(d_tm, d_tm.index)[0] * 10), 3),
                 "tn_diff_1961_1990": round(float(d_tn.loc[:1990].mean()), 1), "tn_diff_1996_2025": round(float(d_tn.loc[1996:].mean()), 1),
                 "tmin_diff_1961_1990": round(float(d_tm.loc[:1990].mean()), 2), "tmin_diff_1996_2025": round(float(d_tm.loc[1996:].mean()), 2)})
    series[f"{c}–{r}"] = d_tn
t = pd.DataFrame(rows)
t.to_csv(R / "requestion_pairs.csv", index=False)
pd.DataFrame(series).round(2).to_csv(R / "requestion_pair_series.csv")
out = {"pairs": rows, "median_tn_diff_slope": round(float(t.tn_diff_slope_per_decade.median()), 2),
       "median_tmin_diff_slope": round(float(t.tmin_diff_slope_per_decade.median()), 3),
       "n_pairs_tn_diff_up": int((t.tn_diff_slope_per_decade > 0).sum()), "n_pairs": len(t)}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(t.to_string()); print({k: v for k, v in out.items() if k != "pairs"})
