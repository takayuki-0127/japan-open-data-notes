"""再問い：パートの時給は、最低賃金に近い（水準が低い）ところほど速く上がったか。
2022年の「パート時給÷最低賃金（暦年換算）」と、2022→2025年のパート時給の伸びを、産業（5人以上）と規模で比べる。"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import RAW, RES, IND16, IND_NAME, SIZE_NAME

j = pd.read_csv(RAW / "maikin_jissu_cy2000.csv", dtype={"規模": str, "就業形態": str, "産業分類": str})
s = pd.read_csv(RAW / "maikin_shisu_cy2000.csv", dtype={"規模": str, "就業形態": str, "産業分類": str})
for d in (j, s): d["産業分類"] = d["産業分類"].str.strip()
g = s[s["種別"].str.startswith("伸び率") & (s.就業形態 == "2")]
mw = pd.read_csv(RAW / "mw_national.csv").set_index("fiscal_year")["mw_weighted_avg_yen"]
mwcy = {y: 0.75 * mw[y - 1] + 0.25 * mw[y] for y in range(2008, 2026)}
mw_growth = (mwcy[2025] / mwcy[2022] - 1) * 100
rows = []
# 産業（公表の前年比をつないだ伸び）
for c in IND16:
    lv = j[(j.規模 == "T") & (j.就業形態 == "2") & (j.産業分類 == c)].set_index("年")
    yy = g[(g.規模 == "T") & (g.産業分類 == c)].set_index("年")
    if 2022 not in lv.index or not set([2023, 2024, 2025]) <= set(yy.index): continue
    h22 = lv.loc[2022, "所定内給与"] / lv.loc[2022, "所定内労働時間"]
    gr = (np.prod([(1 + yy.loc[y, "所定内給与"] / 100) / (1 + yy.loc[y, "所定内労働時間"] / 100) for y in (2023, 2024, 2025)]) - 1) * 100
    rows.append({"区分": "産業", "名前": IND_NAME[c], "hourly_2022": h22, "bite_2022": h22 / mwcy[2022], "growth_22_25": gr,
                 "part_workers_2025": j[(j.規模 == "T") & (j.就業形態 == "2") & (j.産業分類 == c) & (j.年 == 2025)]["本月末労働者数"].sum()})
# 規模（実数からの伸び：段差を含む）
for k, nm in SIZE_NAME.items():
    lv = j[(j.規模 == k) & (j.就業形態 == "2") & (j.産業分類 == "TL")].set_index("年")
    h = lv["所定内給与"] / lv["所定内労働時間"]
    rows.append({"区分": "規模", "名前": nm, "hourly_2022": h[2022], "bite_2022": h[2022] / mwcy[2022], "growth_22_25": (h[2025] / h[2022] - 1) * 100,
                 "part_workers_2025": lv.loc[2025, "本月末労働者数"]})
df = pd.DataFrame(rows)
df.to_csv(RES / "reask_bite_growth.csv", index=False)
ind = df[df.区分 == "産業"]
r, p = stats.spearmanr(ind.bite_2022, ind.growth_22_25)
pr, pp = stats.pearsonr(ind.bite_2022, ind.growth_22_25)
low = ind[ind.bite_2022 <= ind.bite_2022.median()]; high = ind[ind.bite_2022 > ind.bite_2022.median()]
# 外れ値（鉱業など雇用が小さい産業）を除いた頑健性：パート労働者数が少ない下位3産業を除く
big = ind.sort_values("part_workers_2025").iloc[3:]
r2, p2 = stats.spearmanr(big.bite_2022, big.growth_22_25)
out = {"mw_growth_22_25": mw_growth, "n_ind": len(ind), "spearman": r, "spearman_p": p, "pearson": pr, "pearson_p": pp,
       "spearman_excl_small3": r2, "spearman_excl_small3_p": p2, "excluded": ind.sort_values("part_workers_2025").iloc[:3].名前.tolist(),
       "growth_low_bite_median": low.growth_22_25.median(), "growth_high_bite_median": high.growth_22_25.median(),
       "size_rows": df[df.区分 == "規模"].round(3).to_dict(orient="records")}
json.dump(out, open(RES / "reask.json", "w"), ensure_ascii=False, indent=1, default=float)
print(df.round(3).to_string()); print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda v: round(float(v), 3)))
