"""問い直し（結果を見てから足した）：式場の件数が結婚より速く減るなかで、式の多い季節（春・秋）への集中は変わったのか。
月の実数から、その年の件数に占める月ごとの割合を出す。年の途中で調査対象が変わった年（2014年・2020年）と、
感染症の影響の大きい2021年は除く。割合は同じ年の中の比なので、年をまたぐ断層の影響を受けにくい。ネットにはつながない。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
mo = pd.read_csv(DATA / "wedding_monthly.csv")
mo = mo[~mo.year.isin([2014, 2020, 2021])].copy()
mo["share"] = 100 * mo.count_level / mo.groupby("year").count_level.transform("sum")
mo["unit_man"] = 100 * mo.sales_level / mo.count_level
PEAK = [4, 5, 10, 11]           # 春（4・5月）と秋（10・11月）
yr = mo.groupby("year", sort=True).apply(lambda g: pd.Series({
    "peak_share": g.loc[g.month.isin(PEAK), "share"].sum(),
    "summer_winter_share": g.loc[g.month.isin([1, 2, 7, 8, 12]), "share"].sum(),
    "hhi": float((g.share ** 2).sum()),
    "unit_peak_man": 100 * g.loc[g.month.isin(PEAK), "sales_level"].sum() / g.loc[g.month.isin(PEAK), "count_level"].sum(),
    "unit_off_man": 100 * g.loc[~g.month.isin(PEAK), "sales_level"].sum() / g.loc[~g.month.isin(PEAK), "count_level"].sum()}),
    include_groups=False).reset_index()
yr.to_csv(RES / "requestion_season_by_year.csv", index=False, float_format="%.4f")
G = {"2000_2004": (2000, 2004), "2009_2013": (2009, 2013), "2015_2019": (2015, 2019), "2022_2024": (2022, 2024)}
ms = []
for k, (a, b) in G.items():
    s = mo[(mo.year >= a) & (mo.year <= b)].groupby("month", sort=True).share.mean()
    for mth, v in s.items():
        ms.append({"group": k, "month": int(mth), "share": float(v)})
pd.DataFrame(ms).to_csv(RES / "requestion_month_share.csv", index=False, float_format="%.4f")
out = {}
for k, (a, b) in G.items():
    z = yr[(yr.year >= a) & (yr.year <= b)]
    out[k] = {kk: round(float(z[kk].mean()), 3) for kk in ["peak_share", "summer_winter_share", "hhi", "unit_peak_man", "unit_off_man"]}
    out[k]["n_years"] = int(len(z))
slope = np.polyfit(yr.year, yr.peak_share, 1)[0]
out["peak_share_trend_pt_per_10y"] = round(float(10 * slope), 3)
json.dump(out, open(RES / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
