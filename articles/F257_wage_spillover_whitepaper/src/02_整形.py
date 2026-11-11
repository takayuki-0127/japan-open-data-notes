import pandas as pd
from common import RAW, DATA, IND16

j = pd.read_csv(RAW / "maikin_jissu_cy2000.csv", dtype={"規模": str, "就業形態": str, "産業分類": str})
s = pd.read_csv(RAW / "maikin_shisu_cy2000.csv", dtype={"規模": str, "就業形態": str, "産業分類": str})
for d in (j, s):
    d["産業分類"] = d["産業分類"].str.strip()
g = s[s["種別"].str.startswith("伸び率")].copy()

# 産業別（16大産業）・一般労働者・5人以上：公表の前年比（指数ベース）と雇用者数
ind = g[(g["規模"] == "T") & (g["就業形態"] == "1") & (g["産業分類"].isin(IND16))][["年", "産業分類", "所定内給与", "所定内労働時間"]]
ind = ind.rename(columns={"所定内給与": "yoy_sched", "所定内労働時間": "yoy_hours"})
emp = j[(j["規模"] == "T") & (j["就業形態"] == "1") & (j["産業分類"].isin(IND16))][["年", "産業分類", "本月末労働者数", "所定内給与", "所定内労働時間"]]
emp = emp.rename(columns={"本月末労働者数": "workers", "所定内給与": "lvl_sched", "所定内労働時間": "lvl_hours"})
ind = ind.merge(emp, on=["年", "産業分類"], how="left")
ind.to_csv(DATA / "industry_general.csv", index=False)

# 規模別（500人以上・100〜499・30〜99・5〜29）・産業計：実数の水準（就業形態 0=計, 1=一般, 2=パート）
sz = j[(j["産業分類"] == "TL") & (j["規模"].isin(["4", "5", "7", "9"]))][["年", "規模", "就業形態", "所定内給与", "所定内労働時間", "本月末労働者数", "パートタイム労働者数"]]
sz.to_csv(DATA / "size_levels.csv", index=False)

# 全国（5人以上・産業計）：公表の前年比（計・一般・パート）と実数
nat = g[(g["規模"] == "T") & (g["産業分類"] == "TL")][["年", "就業形態", "所定内給与", "所定内労働時間"]].rename(columns={"所定内給与": "yoy_sched", "所定内労働時間": "yoy_hours"})
lv = j[(j["規模"] == "T") & (j["産業分類"] == "TL")][["年", "就業形態", "所定内給与", "所定内労働時間"]].rename(columns={"所定内給与": "lvl_sched", "所定内労働時間": "lvl_hours"})
nat = nat.merge(lv, on=["年", "就業形態"], how="left")
nat.to_csv(DATA / "national.csv", index=False)
print(len(ind), len(sz), len(nat))
