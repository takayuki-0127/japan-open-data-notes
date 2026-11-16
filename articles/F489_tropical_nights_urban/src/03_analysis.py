"""熱帯夜（日最低気温25℃以上の日数）の増え方：大都市と15地点。都市の上乗せの見込み。仮説・頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
a = pd.read_csv(ROOT / "data" / "annual.csv")
a = a[(a.year >= 1961) & (a.year <= 2025)]
ORDER = list(dict.fromkeys(a.station))


def clean(df, keep_flag=False):
    d = df.copy()
    if not keep_flag:
        d.loc[d.days_tmin_ge25_flag == 1, "days_tmin_ge25"] = np.nan
        d.loc[d.tmin_mean_flag == 1, "tmin_mean"] = np.nan
    return d


def slope(g, col, ols=False):
    g = g.dropna(subset=[col])
    if len(g) < 20:
        return np.nan
    if ols:
        return float(np.polyfit(g.year, g[col], 1)[0] * 10)
    return float(stats.theilslopes(g[col], g.year)[0] * 10)


def table(d, ols=False):
    rows = []
    for stn in ORDER:
        g = d[d.station == stn]
        if g.empty:
            continue
        rows.append({"station": stn, "group": g.group.iloc[0], "n_years": int(g.days_tmin_ge25.notna().sum()),
                     "tn_slope": slope(g, "days_tmin_ge25", ols), "tmin_slope": slope(g, "tmin_mean", ols),
                     "tn_1961_1990": float(g[g.year <= 1990].days_tmin_ge25.mean()), "tn_1996_2025": float(g[g.year >= 1996].days_tmin_ge25.mean())})
    return pd.DataFrame(rows)


D = clean(a)
T = table(D)
# H4：大都市ごとに、熱帯夜の日数を日最低気温の年平均で説明する（2次の式）。最低気温の上がり方を15地点の中央値に置き換えた見込み
rural_tmin = float(T[T.group == "rural"].tmin_slope.median())
share = []
for stn in [s for s in ORDER if (T.set_index("station").group.get(s) == "city")]:
    g = D[(D.station == stn)].dropna(subset=["days_tmin_ge25", "tmin_mean"])
    c = np.polyfit(g.tmin_mean, g.days_tmin_ge25, 2)
    t0 = float(g[g.year <= 1990].tmin_mean.mean())
    dt_city = float(T.set_index("station").loc[stn, "tmin_slope"]) * 6.4   # 1961〜2025年の64年分
    dt_rural = rural_tmin * 6.4
    pred_city = np.polyval(c, t0 + dt_city) - np.polyval(c, t0)
    pred_rural = np.polyval(c, t0 + dt_rural) - np.polyval(c, t0)
    share.append({"station": stn, "tmin_rise_city": round(dt_city, 2), "tmin_rise_rural": round(dt_rural, 2),
                  "tn_increase_with_city_rise": round(float(pred_city), 1), "tn_increase_with_rural_rise": round(float(pred_rural), 1),
                  "urban_extra_share_pct": round(float((pred_city - pred_rural) / pred_city * 100), 1) if pred_city > 0 else np.nan})
S = pd.DataFrame(share)
S.to_csv(R / "urban_share.csv", index=False)
T.round(3).to_csv(R / "station_slopes.csv", index=False)
# 年ごとの区分の平均（図用、両方の区分ですべての地点の値がそろう年）
yr = D.pivot_table(index="year", columns="station", values="days_tmin_ge25")
grp = T.set_index("station").group
ym = pd.DataFrame({"city_mean": yr[[s for s in yr.columns if grp[s] == "city"]].mean(axis=1),
                   "rural_mean": yr[[s for s in yr.columns if grp[s] == "rural"]].mean(axis=1)})
ym.round(3).to_csv(R / "yearly_group_mean.csv")

med = T.groupby("group")[["tn_slope", "tmin_slope"]].median()
rob = []
for name, d, kw, excl in [("本線：1961〜2025年、Theil–Sen", D, {}, []), ("1981〜2025年", D[D.year >= 1981], {}, []),
                          ("南の4地点（名瀬・石垣島・鹿児島・宮崎）を除く", D, {}, ["名瀬", "石垣島", "鹿児島", "宮崎"]),
                          ("普通の最小二乗法", D, {"ols": True}, []), ("「]」の年も含める", clean(a, keep_flag=True), {}, [])]:
    t = table(d[~d.station.isin(excl)], **kw)
    m = t.groupby("group")[["tn_slope", "tmin_slope"]].median()
    rob.append({"check": name, "city_tn_slope": round(float(m.loc["city", "tn_slope"]), 2), "rural_tn_slope": round(float(m.loc["rural", "tn_slope"]), 2),
                "ratio": round(float(m.loc["city", "tn_slope"] / m.loc["rural", "tn_slope"]), 2) if m.loc["rural", "tn_slope"] > 0 else np.nan,
                "city_tmin_slope": round(float(m.loc["city", "tmin_slope"]), 3), "rural_tmin_slope": round(float(m.loc["rural", "tmin_slope"]), 3)})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)

c_tn, r_tn = float(med.loc["city", "tn_slope"]), float(med.loc["rural", "tn_slope"])
c_tm, r_tm = float(med.loc["city", "tmin_slope"]), float(med.loc["rural", "tmin_slope"])
h4 = float(S.urban_extra_share_pct.median())
main = {
    "city_tn_slope_median": round(c_tn, 2), "rural_tn_slope_median": round(r_tn, 2), "ratio_city_rural": round(c_tn / r_tn, 2) if r_tn > 0 else None,
    "city_tmin_slope_median": round(c_tm, 3), "rural_tmin_slope_median": round(r_tm, 3), "tmin_diff": round(c_tm - r_tm, 3),
    "urban_extra_share_median_pct": round(h4, 1),
    "city_tn_1961_1990_mean": round(float(T[T.group == "city"].tn_1961_1990.mean()), 1), "city_tn_1996_2025_mean": round(float(T[T.group == "city"].tn_1996_2025.mean()), 1),
    "rural_tn_1961_1990_mean": round(float(T[T.group == "rural"].tn_1961_1990.mean()), 1), "rural_tn_1996_2025_mean": round(float(T[T.group == "rural"].tn_1996_2025.mean()), 1),
    "hypotheses": {
        "H1_city_ge_2x_rural": {"city": round(c_tn, 2), "rural": round(r_tn, 2), "result": "支持" if (r_tn > 0 and c_tn >= 2 * r_tn) or (r_tn <= 0 and c_tn > 0) else "外れ"},
        "H2_rural_gt_0": {"value": round(r_tn, 2), "result": "支持" if r_tn > 0 else "外れ"},
        "H3_tmin_diff_ge_0.1": {"value": round(c_tm - r_tm, 3), "result": "支持" if c_tm - r_tm >= 0.1 else "外れ"},
        "H4_urban_extra_ge_50pct": {"value": round(h4, 1), "result": "支持" if h4 >= 50 else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(T.round(2).to_string()); print(S.to_string()); print(rob.to_string())
