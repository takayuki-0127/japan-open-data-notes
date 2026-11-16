"""問い直し（結果を見てから足した）：全体の3〜4月の割合がほぼ動かないのは、年齢ごとの集中が変わらないからか、
年齢の構成が変わって打ち消し合っているからか。2019年→2025年をシフトシェアで分ける（年齢7区分）。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
ag = pd.read_csv(R / "age_share_mar_apr.csv")
K = ["0-14", "15-19", "20-24", "25-29", "30-39", "40-64", "65+"]
a = ag[ag.age.isin(K)].pivot(index="age", columns="year", values="annual").loc[K]
s = ag[ag.age.isin(K)].pivot(index="age", columns="year", values="share_mar_apr").loc[K]
w = a / a.sum()
y0, y1 = 2019, 2025
mix = float(((w[y1] - w[y0]) * (s[y0] + s[y1]) / 2).sum())
within = float(((s[y1] - s[y0]) * (w[y0] + w[y1]) / 2).sum())
tab = pd.DataFrame({"weight_2019": w[y0] * 100, "weight_2025": w[y1] * 100, "share_2019": s[y0], "share_2025": s[y1]})
tab["within_contrib"] = (s[y1] - s[y0]) * (w[y0] + w[y1]) / 2
tab["mix_contrib"] = (w[y1] - w[y0]) * (s[y0] + s[y1]) / 2
tab.to_csv(R / "requestion_shift_share.csv", float_format="%.4f")
out = {"total_change": round(mix + within, 2), "mix": round(mix, 2), "within": round(within, 2),
       "weight_20_24_2019": round(float(w.loc["20-24", y0] * 100), 1), "weight_20_24_2025": round(float(w.loc["20-24", y1] * 100), 1),
       "weight_65p_2019": round(float(w.loc["65+", y0] * 100), 1), "weight_65p_2025": round(float(w.loc["65+", y1] * 100), 1),
       "within_15_24": round(float(tab.loc[["15-19", "20-24"], "within_contrib"].sum()), 2),
       "within_25_64": round(float(tab.loc[["25-29", "30-39", "40-64"], "within_contrib"].sum()), 2)}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(out); print(tab.round(2))
