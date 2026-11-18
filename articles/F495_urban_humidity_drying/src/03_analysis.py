"""傾き・分解・仮説・頑健性。乱数は使わない。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy.stats import theilslopes

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
A = pd.read_csv(ROOT / "data" / "annual.csv")
ORDER = list(dict.fromkeys(A.station))
GROUP = A.drop_duplicates("station").set_index("station").group.to_dict()


def es(t):
    """Magnus の式（水面上、hPa）"""
    return 6.112 * np.exp(17.62 * t / (243.12 + t))


def slope(x, y, method):
    if method == "ols":
        return float(np.polyfit(x, y, 1)[0])
    return float(theilslopes(y, x)[0])


def station_table(y0=1961, y1=2025, method="ols", drop_flag=True, min_n=40):
    rows = []
    for s in ORDER:
        d = A[(A.station == s) & A.year.between(y0, y1)].dropna(subset=["rh", "vp", "tmean"])
        if drop_flag:
            d = d[(d.rh_flag == 0) & (d.vp_flag == 0) & (d.tmean_flag == 0)]
        if len(d) < min_n * (y1 - y0 + 1) / 65:
            continue
        x = d.year.values.astype(float)
        rh_bar = d.rh.mean()
        b_rh = slope(x, d.rh.values, method) * 10
        b_lnrh = slope(x, np.log(d.rh.values), method) * 10
        b_lne = slope(x, np.log(d.vp.values), method) * 10
        b_lnes = slope(x, np.log(es(d.tmean.values)), method) * 10
        rows.append({"station": s, "group": GROUP[s], "n": len(d), "rh_mean": rh_bar,
                     "rh_slope": b_rh, "vp_slope": slope(x, d.vp.values, method) * 10,
                     "t_slope": slope(x, d.tmean.values, method) * 10,
                     "temp_part": -b_lnes * rh_bar, "vapor_part": b_lne * rh_bar,
                     "lnrh_part": b_lnrh * rh_bar})
    t = pd.DataFrame(rows)
    t["resid"] = t.rh_slope - t.temp_part - t.vapor_part
    return t


def summ(t):
    g = t.groupby("group")
    m = {k: g[k].median().to_dict() for k in ["rh_slope", "vp_slope", "t_slope", "temp_part", "vapor_part"]}
    city = t[t.group == "city"]
    temp_share = float((city.temp_part / city.rh_slope).median())
    temp_share_of_median = m["temp_part"]["city"] / m["rh_slope"]["city"] if m["rh_slope"]["city"] != 0 else float("nan")
    return {"city_rh": m["rh_slope"]["city"], "rural_rh": m["rh_slope"]["rural"],
            "diff_rh": m["rh_slope"]["city"] - m["rh_slope"]["rural"],
            "city_vp": m["vp_slope"]["city"], "rural_vp": m["vp_slope"]["rural"],
            "city_t": m["t_slope"]["city"], "rural_t": m["t_slope"]["rural"],
            "city_temp_part": m["temp_part"]["city"], "city_vapor_part": m["vapor_part"]["city"],
            "rural_temp_part": m["temp_part"]["rural"], "rural_vapor_part": m["vapor_part"]["rural"],
            "city_temp_share_median_of_ratios": temp_share, "city_temp_share_of_medians": temp_share_of_median,
            "n_city": int((t.group == "city").sum()), "n_rural": int((t.group == "rural").sum())}


T = station_table()
T.round(4).to_csv(R / "station_slopes.csv", index=False)
S = summ(T)

# 区分の平均の系列（地点の値の平均、資料不足値の年は除く）
B = A[A.year.between(1961, 2025)].copy()
for k in ["rh", "vp", "tmean"]:
    B.loc[B[k + "_flag"] == 1, k] = np.nan
Y = B.groupby(["year", "group"])[["rh", "vp", "tmean"]].mean().unstack("group")
Y.columns = [f"{a}_{b}" for a, b in Y.columns]
Y = Y.reset_index()
Y.round(4).to_csv(R / "yearly_group_mean.csv", index=False)
p0 = Y[Y.year.between(1961, 1990)].mean(); p1 = Y[Y.year.between(1996, 2025)].mean()

main = {"period": "1961-2025", "method": "OLS", **{k: round(v, 4) if isinstance(v, float) else v for k, v in S.items()},
        "city_rh_1961_1990": round(p0.rh_city, 2), "city_rh_1996_2025": round(p1.rh_city, 2),
        "rural_rh_1961_1990": round(p0.rh_rural, 2), "rural_rh_1996_2025": round(p1.rh_rural, 2),
        "city_vp_1961_1990": round(p0.vp_city, 2), "city_vp_1996_2025": round(p1.vp_city, 2),
        "rural_vp_1961_1990": round(p0.vp_rural, 2), "rural_vp_1996_2025": round(p1.vp_rural, 2),
        "n_city_rh_down": int(((T.group == "city") & (T.rh_slope < 0)).sum()),
        "n_rural_rh_down": int(((T.group == "rural") & (T.rh_slope < 0)).sum()),
        "n_city_vp_down": int(((T.group == "city") & (T.vp_slope < 0)).sum()),
        "n_rural_vp_down": int(((T.group == "rural") & (T.vp_slope < 0)).sum()),
        "resid_abs_max": round(float(T.resid.abs().max()), 4), "resid_median": round(float(T.resid.median()), 4),
        "city_temp_share_le1": int(((T.group == "city") & (T.temp_part / T.rh_slope < 1)).sum())}
main["hypotheses"] = {
    "H1": {"rule": "大都市の下がり方が15地点より0.3ポイント/10年以上大きい", "value": round(-S["diff_rh"], 4),
           "verdict": "支持" if -S["diff_rh"] >= 0.3 else "外れ"},
    "H2": {"rule": "15地点でも下がっている（中央値<0）", "value": round(S["rural_rh"], 4),
           "verdict": "支持" if S["rural_rh"] < 0 else "外れ"},
    "H3": {"rule": "大都市の下がり方のうち気温の分は半分未満（中央値どうしの比）", "value": round(S["city_temp_share_of_medians"], 4),
           "verdict": "支持" if S["city_temp_share_of_medians"] < 0.5 else "外れ"},
    "H4": {"rule": "15地点の蒸気圧は増えている（中央値>0）", "value": round(S["rural_vp"], 4),
           "verdict": "支持" if S["rural_vp"] > 0 else "外れ"},
}

rob = [("本線：1961〜2025年、最小二乗法", S)]
rob.append(("1981〜2025年", summ(station_table(1981, 2025))))
rob.append(("1961〜2005年（戻りの前まで）", summ(station_table(1961, 2005))))
rob.append(("Theil–Sen（計画の手法）", summ(station_table(method="ts"))))
t3 = T[T.station != "東京"]; rob.append(("東京を除く", summ(t3)))
rob.append(("「]」の年も含める", summ(station_table(drop_flag=False))))
RB = pd.DataFrame([{"check": n, **{k: round(v, 4) if isinstance(v, float) else v for k, v in s.items()}} for n, s in rob])
RB.to_csv(R / "robustness.csv", index=False)
main["gap_temp_part"] = round(S["city_temp_part"] - S["rural_temp_part"], 4)
main["gap_vapor_part"] = round(S["city_vapor_part"] - S["rural_vapor_part"], 4)
main["robustness_same_sign_all"] = bool((RB.city_rh < RB.rural_rh).all())
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=False)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(T.round(3).to_string()); print(RB[["check","city_rh","rural_rh","diff_rh","city_temp_share_median_of_ratios","city_vp","rural_vp"]].to_string())
