"""問い直し（結果を見てから足した）：
2段目（CPI 帰属家賃除く − 家計消費デフレーター除く帰属家賃）は、CPI の基準改定（5年ごと）から年がたつほど大きくなるのか。
あわせて、2段目がマイナスになった2020〜2022年の CPI の通信の動きを見る。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(R / "annual_gap_decomposition.csv", index_col=0)
d["k"] = d.index - (d.index // 5) * 5      # 0 は基準年（前の基準とつなぐ年）、4 は基準から4年目
tab = d.groupby("k")["s2_formula"].agg(["mean", "median", "count"]).reset_index()
tab.round(4).to_csv(R / "requestion_years_since_base.csv", index=False)
# 2020年以降を除いた形でも
tab2 = d.loc[:2019].groupby("k")["s2_formula"].mean()
rho, p = stats.spearmanr(d.loc[:2019, "k"], d.loc[:2019, "s2_formula"])
slope = np.polyfit(d.loc[:2019, "k"], d.loc[:2019, "s2_formula"], 1)[0]

c = pd.read_csv(ROOT / "data" / "raw" / "cpi2025_middle_annual_cy.csv", encoding="cp932", header=None, dtype=str)
name = c.iloc[0].tolist(); yrs = c.iloc[6:, 0].str.strip().astype(int).values
comm = pd.Series(c.iloc[6:, name.index("通信")].astype(float).values, index=yrs)
w = float(c.iloc[5, name.index("通信")]) / 10000   # 2025年基準のウエイト（近似の寄与にだけ使う）
gc = (comm / comm.shift(1) - 1) * 100
out = {
    "mean_by_k": {int(r.k): round(float(r["mean"]), 3) for _, r in tab.iterrows()},
    "count_by_k": {int(r.k): int(r["count"]) for _, r in tab.iterrows()},
    "mean_by_k_1995_2019": {int(k): round(float(v), 3) for k, v in tab2.items()},
    "spearman_k_1995_2019": round(float(rho), 3), "spearman_p": round(float(p), 3), "slope_per_year_1995_2019": round(float(slope), 3),
    "s2_mean_1995_2019": round(float(d.loc[:2019, "s2_formula"].mean()), 3),
    "s2_mean_2020_2025": round(float(d.loc[2020:, "s2_formula"].mean()), 3),
    "communication_growth": {int(y): round(float(gc.loc[y]), 2) for y in [2019, 2020, 2021, 2022, 2023]},
    "communication_weight_2025base": round(w, 4),
    "communication_contrib_2021_approx": round(float(gc.loc[2021] * w), 2),
}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
