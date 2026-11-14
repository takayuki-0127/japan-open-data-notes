"""県×年のパネルを作る（data/panel.csv）。元データは data/raw/ にある（出典は README）。"""
import numpy as np
import pandas as pd
from common import DATA

p = pd.read_csv(DATA / "raw" / "f01_panel.csv")                 # 2008〜2025年、47県
w = pd.read_csv(DATA / "raw" / "f156_panel_wage.csv")[["code", "year", "wage"]]  # 2009〜2025年
p = p.merge(w, on=["code", "year"], how="left")
p["log_wage"] = 100 * np.log(p["wage"])                          # 100×log（%に近い単位）
p["log_pop15"] = 100 * np.log(p["pop15"])
p["post2016"] = (p["year"] >= 2016).astype(int)
p["treat_a"] = p["high_bite"]
p["did_a"] = p["treat_a"] * p["post2016"]

# 設計B：2016年度以降で初めて、上げ幅（円）がその年度の中央値より5円以上大きかった年度
m = pd.read_csv(DATA / "raw" / "minimum_wage_2002_2026.csv")
m = m[m["pref"] != "全国加重平均"].set_index("pref")
fy = [str(y) for y in range(2015, 2027)]
inc = m[fy].astype(float).diff(axis=1).drop(columns="2015")
over = inc.sub(inc.median(axis=0), axis=1) >= 5
first_fy = over.apply(lambda s: int(s.idxmax()) if s.any() else np.nan, axis=1)
cohort = pd.DataFrame({"pref": first_fy.index, "first_fy": first_fy.values})
cohort["g"] = cohort["first_fy"] + 1                             # 10月の改定なので、暦年では翌年から
inc_long = inc.reset_index().melt(id_vars="pref", var_name="fy", value_name="inc_yen")
inc_long.to_csv(DATA / "mw_increase_by_fy.csv", index=False)
p = p.merge(cohort[["pref", "first_fy", "g"]], on="pref", how="left")
p.to_csv(DATA / "panel.csv", index=False)

cnt = cohort.groupby("first_fy", dropna=False).size()
print("処置の年度ごとの県数", cnt.to_dict())
print(p.shape)
