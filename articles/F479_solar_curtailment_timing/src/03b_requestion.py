"""問い直し（結果を見てから足した）：休日に抑制が多いのは「休日だから」か「昼の需要が低いから」か。
日ごとの抑制量を、休日かどうか・昼（11〜13時台）の平均需要・昼の太陽光の出力（実績＋抑制量）で説明する回帰。
年度×月の固定効果を入れる。対象は2018年10月〜2026年3月の日。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
h = pd.read_csv(ROOT / "data" / "hourly.csv")
h = h[h.dt >= "2018-10-01"].copy()
h["date"] = h.dt.str[:10]
noon = h[h.hour.isin([11, 12, 13])]
d = pd.DataFrame({
    "cut_gwh": h.groupby("date").pv_cut.sum() / 1000,
    "holiday": h.groupby("date").holiday.first(),
    "fy": h.groupby("date").fy.first(),
    "month": h.groupby("date").month.first(),
    "noon_demand_gw": noon.groupby("date").demand.mean() / 1000,
    "noon_pv_gw": (noon.pv + noon.pv_cut).groupby(noon.date).mean() / 1000,
})
d["fym"] = d.fy.astype(str) + "_" + d.month.astype(str)
d = d.sort_index()

m0 = smf.ols("cut_gwh ~ holiday + C(fym)", d).fit(cov_type="HC1")
m1 = smf.ols("cut_gwh ~ holiday + noon_demand_gw + noon_pv_gw + C(fym)", d).fit(cov_type="HC1")
spring = d[d.month.isin([3, 4, 5])]
m2 = smf.ols("cut_gwh ~ holiday + noon_demand_gw + noon_pv_gw + C(fym)", spring).fit(cov_type="HC1")

# 需要でそろえた比べ方：春の日を昼の需要 0.5GW 刻みに分け、同じ刻みの中で休日−平日の差を平均（休日の日数で重みづけ）
sp = spring.copy()
sp["bin"] = (sp.noon_demand_gw // 0.5) * 0.5
rows = []
for b, g in sp.groupby("bin", sort=True):
    if g.holiday.nunique() == 2:
        rows.append({"noon_demand_bin_gw": float(b), "n_holiday": int(g.holiday.sum()), "n_weekday": int((g.holiday == 0).sum()),
                     "holiday_mean_gwh": round(float(g[g.holiday == 1].cut_gwh.mean()), 3),
                     "weekday_mean_gwh": round(float(g[g.holiday == 0].cut_gwh.mean()), 3)})
bins = pd.DataFrame(rows)
bins["diff_gwh"] = (bins.holiday_mean_gwh - bins.weekday_mean_gwh).round(3)
bins.to_csv(R / "requestion_demand_bins.csv", index=False)
matched = float(np.average(bins.diff_gwh, weights=bins.n_holiday))

hol_dem = d.groupby("holiday").noon_demand_gw.mean()
out = {
    "n_days": int(len(d)),
    "noon_demand_gw_weekday": round(float(hol_dem.loc[0]), 2),
    "noon_demand_gw_holiday": round(float(hol_dem.loc[1]), 2),
    "holiday_coef_no_control_gwh": round(float(m0.params["holiday"]), 3),
    "holiday_coef_no_control_se": round(float(m0.bse["holiday"]), 3),
    "holiday_coef_with_demand_gwh": round(float(m1.params["holiday"]), 3),
    "holiday_coef_with_demand_se": round(float(m1.bse["holiday"]), 3),
    "demand_coef_gwh_per_gw": round(float(m1.params["noon_demand_gw"]), 3),
    "pv_coef_gwh_per_gw": round(float(m1.params["noon_pv_gw"]), 3),
    "share_of_holiday_gap_left_pct": round(float(m1.params["holiday"] / m0.params["holiday"] * 100), 1),
    "spring_holiday_coef_with_demand_gwh": round(float(m2.params["holiday"]), 3),
    "spring_holiday_coef_with_demand_se": round(float(m2.bse["holiday"]), 3),
    "spring_raw_diff_gwh": round(float(spring[spring.holiday == 1].cut_gwh.mean() - spring[spring.holiday == 0].cut_gwh.mean()), 3),
    "spring_matched_diff_gwh": round(matched, 3),
    "r2_no_control": round(float(m0.rsquared), 3),
    "r2_with_demand": round(float(m1.rsquared), 3),
}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
d.reset_index().to_csv(R / "daily.csv", index=False, float_format="%.4f")
print(json.dumps(out, ensure_ascii=False, indent=1))
print(bins.to_string())
