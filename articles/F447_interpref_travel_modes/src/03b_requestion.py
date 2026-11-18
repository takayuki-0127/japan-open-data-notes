"""問い直し（結果を見てから足した）：コロナのあと戻りが遅いバスは、乗合バス（高速バスなど）と貸切バスのどちらか。
県間の人数を、乗合・貸切に分けて2000〜2024年度で見る。距離帯別の2024/2019も。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
od = pd.read_csv(ROOT / "data" / "od_wide.csv").merge(pd.read_csv(ROOT / "data" / "pref_distance.csv"), on=["orig", "dest"])
ts = od.groupby("fy", sort=True)[["bus_route", "bus_charter"]].sum() / 1e3
ts["route_idx_2019"] = ts["bus_route"] / ts.loc[2019, "bus_route"] * 100
ts["charter_idx_2019"] = ts["bus_charter"] / ts.loc[2019, "bus_charter"] * 100
ts.round(3).to_csv(R / "requestion_bus_route_charter.csv", encoding="utf-8")
od["b"] = pd.cut(od["km"], [0, 100, 300, 99999], right=False, labels=["100km未満", "100〜300km", "300km以上"])
s = od[od.fy.isin([2019, 2024])].groupby(["fy", "b"], observed=False)[["bus_route", "bus_charter"]].sum()
rb = (s.loc[2024] / s.loc[2019] * 100)
rb.round(2).to_csv(R / "requestion_bus_by_band.csv", encoding="utf-8")
m = json.load(open(R / "main.json", encoding="utf-8"))
r = lambda x, n=1: round(float(x), n)
m["requestion"] = {
    "route_million": {str(y): r(ts.loc[y, "bus_route"]) for y in (2000, 2010, 2019, 2020, 2024)},
    "charter_million": {str(y): r(ts.loc[y, "bus_charter"]) for y in (2000, 2010, 2019, 2020, 2024)},
    "route_2024_vs_2019": r(ts.loc[2024, "route_idx_2019"]), "charter_2024_vs_2019": r(ts.loc[2024, "charter_idx_2019"]),
    "route_2019_vs_2000": r(ts.loc[2019, "bus_route"] / ts.loc[2000, "bus_route"] * 100),
    "charter_2019_vs_2000": r(ts.loc[2019, "bus_charter"] / ts.loc[2000, "bus_charter"] * 100),
    "by_band_2024_vs_2019": {k: {"乗合": r(v["bus_route"]), "貸切": r(v["bus_charter"])} for k, v in rb.iterrows()},
}
json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(ts.round(1).to_string()); print(m["requestion"])
