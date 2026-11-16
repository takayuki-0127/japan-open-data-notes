"""冬日・真冬日・年の最低気温の変化。区分（15地点・大都市・寒い地域）ごとの中央値。仮説・頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
A = pd.read_csv(ROOT / "data" / "annual.csv")
A = A[(A.year >= 1961) & (A.year <= 2025)]
ORDER = list(dict.fromkeys(A.station))
VARS = ["days_tmin_lt0", "days_tmax_lt0", "tmin_lowest", "tmin_mean"]


def clean(d, keep=False):
    d = d.copy()
    if not keep:
        for v in VARS:
            d.loc[d[v + "_flag"] == 1, v] = np.nan
    return d


def slope(g, col, ols=False):
    g = g.dropna(subset=[col])
    if len(g) < 20:
        return np.nan
    return float(np.polyfit(g.year, g[col], 1)[0] * 10) if ols else float(stats.theilslopes(g[col], g.year)[0] * 10)


def table(d, ols=False):
    rows = []
    for stn in ORDER:
        g = d[d.station == stn]
        if g.empty:
            continue
        r = {"station": stn, "group": g.group.iloc[0]}
        for v in VARS:
            r[v + "_slope"] = slope(g, v, ols)
            r[v + "_a"] = float(g[g.year <= 1990][v].mean()); r[v + "_b"] = float(g[g.year >= 1996][v].mean())
        rows.append(r)
    t = pd.DataFrame(rows)
    for v in ["days_tmin_lt0", "days_tmax_lt0"]:
        t[v + "_pct"] = (t[v + "_b"] / t[v + "_a"] - 1) * 100
    return t


D = clean(A)
T = table(D)
T.round(3).to_csv(R / "station_table.csv", index=False)
rural10 = T[(T.group == "rural") & (T.days_tmin_lt0_a >= 10)]
city10 = T[(T.group == "city") & (T.days_tmin_lt0_a >= 10)]
h1 = float(rural10.days_tmin_lt0_slope.median())
h2 = float(city10.days_tmin_lt0_slope.median())
mf = T[T.days_tmax_lt0_a >= 5]
h3_mf, h3_f = float(mf.days_tmax_lt0_pct.median()), float(mf.days_tmin_lt0_pct.median())
ru = T[T.group == "rural"]
h4_low, h4_mean = float(ru.tmin_lowest_slope.median()), float(ru.tmin_mean_slope.median())

# 年ごとの区分の平均（図用）：冬日が年10日以上の15地点・大都市
yr = D.pivot_table(index="year", columns="station", values="days_tmin_lt0")
ym = pd.DataFrame({"rural10_mean": yr[list(rural10.station)].mean(axis=1), "city10_mean": yr[list(city10.station)].mean(axis=1)})
mfy = D.pivot_table(index="year", columns="station", values="days_tmax_lt0")[list(mf.station)]
ym = ym.join(mfy.add_prefix("mafuyu_"))
ym.round(3).to_csv(R / "yearly.csv")

rob = []
for name, d, kw, thr in [("本線：1961〜2025年、Theil–Sen、冬日10日以上の地点", D, {}, 10), ("1981〜2025年", D[D.year >= 1981], {}, 10),
                         ("普通の最小二乗法", D, {"ols": True}, 10), ("冬日30日以上の地点", D, {}, 30), ("「]」の年も含める", clean(A, keep=True), {}, 10)]:
    t = table(d, **kw)
    r_ = t[(t.group == "rural") & (t.days_tmin_lt0_a >= thr)]; c_ = t[(t.group == "city") & (t.days_tmin_lt0_a >= thr)]
    rob.append({"check": name, "n_rural": len(r_), "rural_fuyubi_slope": round(float(r_.days_tmin_lt0_slope.median()), 2),
                "n_city": len(c_), "city_fuyubi_slope": round(float(c_.days_tmin_lt0_slope.median()), 2),
                "rural_lowest_slope": round(float(t[t.group == "rural"].tmin_lowest_slope.median()), 3),
                "rural_tminmean_slope": round(float(t[t.group == "rural"].tmin_mean_slope.median()), 3)})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)

main = {
    "rural10_stations": list(rural10.station), "city10_stations": list(city10.station), "mafuyu5_stations": list(mf.station),
    "rural10_fuyubi_slope_median": round(h1, 2), "city10_fuyubi_slope_median": round(h2, 2),
    "rural10_fuyubi_a_mean": round(float(rural10.days_tmin_lt0_a.mean()), 1), "rural10_fuyubi_b_mean": round(float(rural10.days_tmin_lt0_b.mean()), 1),
    "rural10_fuyubi_pct_median": round(float(rural10.days_tmin_lt0_pct.median()), 1),
    "city10_fuyubi_a_mean": round(float(city10.days_tmin_lt0_a.mean()), 1), "city10_fuyubi_b_mean": round(float(city10.days_tmin_lt0_b.mean()), 1),
    "city10_fuyubi_pct_median": round(float(city10.days_tmin_lt0_pct.median()), 1),
    "mafuyu_pct_median": round(h3_mf, 1), "fuyubi_pct_median_same_stations": round(h3_f, 1),
    "rural_lowest_slope_median": round(h4_low, 3), "rural_tminmean_slope_median": round(h4_mean, 3),
    "hypotheses": {
        "H1_rural_fuyubi_le_-2": {"value": round(h1, 2), "result": "支持" if h1 <= -2 else "外れ"},
        "H2_city_faster_by_1.5": {"city": round(h2, 2), "rural": round(h1, 2), "result": "支持" if h2 <= h1 - 1.5 else "外れ"},
        "H3_mafuyu_pct_gt_fuyubi_pct": {"mafuyu": round(h3_mf, 1), "fuyubi": round(h3_f, 1), "result": "支持" if h3_mf < h3_f else "外れ"},
        "H4_lowest_faster": {"lowest": round(h4_low, 3), "mean": round(h4_mean, 3), "result": "支持" if h4_low > h4_mean else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(T[["station", "group", "days_tmin_lt0_a", "days_tmin_lt0_b", "days_tmin_lt0_slope", "days_tmax_lt0_a", "days_tmax_lt0_b", "days_tmax_lt0_pct", "tmin_lowest_slope", "tmin_mean_slope"]].round(2).to_string())
print(rob.to_string())
