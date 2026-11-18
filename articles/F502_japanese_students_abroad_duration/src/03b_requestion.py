"""問い直し（結果を見てから足した）：3か月以上の留学の行き先は、北米から欧州・大洋州へ移ったのか。
地域ごとの3か月以上の留学者と、その割合（2009〜2024年度）を出す。"""
import json
import pandas as pd
from common import ROOT

D, R = ROOT / "data", ROOT / "results"
REG = ["アジア", "中東", "アフリカ", "大洋州", "北米", "中南米", "欧州", "その他・無記入"]
p = pd.read_csv(D / "panel_region_period.csv")
p = p[p.region != "計"].copy()
p["m3plus"] = p.m3_6 + p.m6_12 + p.y1plus
w = p.pivot(index="year", columns="region", values="m3plus").reindex(columns=REG).fillna(0).astype(int)
sh = (100 * w.div(w.sum(axis=1), axis=0)).round(2)
out = w.add_suffix("_n").join(sh.add_suffix("_share_pct"))
out.to_csv(R / "m3plus_by_region.csv")
yrs = [2009, 2014, 2018, 2019, 2022, 2023, 2024]
res = {
    "m3plus_share_pct": {g: {y: float(sh.loc[y, g]) for y in yrs} for g in ["アジア", "大洋州", "北米", "欧州"]},
    "m3plus_n": {g: {y: int(w.loc[y, g]) for y in yrs} for g in ["アジア", "大洋州", "北米", "欧州"]},
    "na_share_peak_year": int(sh["北米"].idxmax()), "na_share_peak": float(sh["北米"].max()),
    "eu_over_na_years": [int(y) for y in sh.index if sh.loc[y, "欧州"] > sh.loc[y, "北米"]],
    "m3plus_total": {y: int(w.loc[y].sum()) for y in yrs},
}
json.dump(res, open(R / "requestion.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
