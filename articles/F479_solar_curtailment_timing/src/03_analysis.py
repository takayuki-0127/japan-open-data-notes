"""年度・月・時刻・休日ごとの集計、仮説の判定、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
h = pd.read_csv(ROOT / "data" / "hourly.csv")
h["date"] = h.dt.str[:10]
h["re_cut"] = h.pv_cut + h.wind_cut
CUT = h[h.fy >= 2018]  # 出力制御は2018年10月に始まった

# 公表されている九州の出力制御率（資源エネルギー庁 系統WG 2024-09-18 資料。2024年度は見通し）
OFFICIAL = {2018: 0.9, 2019: 4.0, 2020: 2.9, 2021: 3.9, 2022: 3.0, 2023: 8.3}

# ---- 年度ごと ------------------------------------------------------------------------------
g = h.groupby("fy", sort=True)
fy = pd.DataFrame({
    "pv_gwh": g.pv.sum() / 1000,
    "pv_cut_gwh": g.pv_cut.sum() / 1000,
    "wind_cut_gwh": g.wind_cut.sum() / 1000,
})
fy["pv_cut_rate_pct"] = fy.pv_cut_gwh / (fy.pv_gwh + fy.pv_cut_gwh) * 100
fy["re_cut_rate_pct"] = (fy.pv_cut_gwh + fy.wind_cut_gwh) / (fy.pv_gwh + fy.pv_cut_gwh + g.wind.sum() / 1000 + fy.wind_cut_gwh) * 100
d = h.groupby(["fy", "date"], sort=True).pv_cut.sum().reset_index()
fy["cut_days"] = d[d.pv_cut > 0].groupby("fy").size().reindex(fy.index, fill_value=0)
fy["cut_hours"] = h[h.pv_cut > 0].groupby("fy").size().reindex(fy.index, fill_value=0)
fy["official_rate_pct"] = pd.Series(OFFICIAL).reindex(fy.index)
fy = fy.round(3)
fy.to_csv(R / "fy_summary.csv")


def shares(df, col="pv_cut", unit="sum"):
    """月・時刻・休日の割合（%）。unit='hours' なら抑制のあった時間の数で数える。"""
    x = df.assign(v=(df[col] > 0).astype(float) if unit == "hours" else df[col])
    tot = x.v.sum()
    m = x.groupby("month").v.sum() / tot * 100
    hr = x.groupby("hour").v.sum() / tot * 100
    spring = m.loc[[3, 4, 5]].sum()
    autumn = m.loc[[9, 10, 11]].sum()
    noon = hr.loc[[11, 12, 13]].sum()
    peak = int(hr.idxmax())
    days = x.groupby(["date", "holiday"]).v.sum().reset_index()
    per_day = days.groupby("holiday").v.mean()
    ratio = per_day.loc[1] / per_day.loc[0]
    return dict(spring=spring, autumn=autumn, noon=noon, peak_hour=peak, holiday_ratio=ratio), m, hr


base, m_share, hr_share = shares(CUT)
pd.DataFrame({"share_pct": m_share.round(3)}).to_csv(R / "month_share.csv")
pd.DataFrame({"share_pct": hr_share.round(3)}).to_csv(R / "hour_share.csv")
# 年度×月の抑制量（GWh）
fm = (CUT.groupby(["fy", "month"]).pv_cut.sum() / 1000).unstack("month").reindex(columns=range(1, 13)).fillna(0).round(3)
fm.to_csv(R / "fy_month_gwh.csv")
# 時刻×期間の割合
early = CUT[CUT.fy <= 2022]; late = CUT[CUT.fy >= 2023]
_, _, hr_e = shares(early); _, _, hr_l = shares(late)
pd.DataFrame({"fy2018_2022": hr_e.round(3), "fy2023_2025": hr_l.round(3)}).to_csv(R / "hour_share_by_period.csv")

# 休日・平日の1日あたり（MWh）
dd = CUT.groupby(["fy", "date", "holiday"]).pv_cut.sum().reset_index()
hol_tab = dd.groupby("holiday").pv_cut.agg(["mean", "size"])
avg_early = fy.loc[2018:2022, "pv_cut_gwh"].mean()
avg_late = fy.loc[2023:2025, "pv_cut_gwh"].mean()

# ---- 頑健性 -------------------------------------------------------------------------------
rows = []
for name, df, col, unit in [
    ("本線：2018〜2025年度、太陽光の抑制量", CUT, "pv_cut", "sum"),
    ("期間：2018〜2022年度", early, "pv_cut", "sum"),
    ("期間：2023〜2025年度", late, "pv_cut", "sum"),
    ("定義：抑制のあった時間の数", CUT, "pv_cut", "hours"),
    ("定義：太陽光＋風力の抑制量", CUT, "re_cut", "sum"),
    ("最大の年度（2023）を除く", CUT[CUT.fy != 2023], "pv_cut", "sum"),
]:
    s, _, _ = shares(df, col, unit)
    rows.append({"check": name, "spring_pct": round(s["spring"], 1), "autumn_pct": round(s["autumn"], 1),
                 "noon_11_13_pct": round(s["noon"], 1), "peak_hour": s["peak_hour"], "holiday_per_day_ratio": round(s["holiday_ratio"], 2)})
rob = pd.DataFrame(rows)
rob.to_csv(R / "robustness.csv", index=False)

# 公表値との照合（2018〜2023年度、差の最大）
comp = fy.loc[2018:2023, ["re_cut_rate_pct", "official_rate_pct"]]
max_gap = float((comp.re_cut_rate_pct - comp.official_rate_pct).abs().max())

main = {
    "period": "2018〜2025年度（九州本土）",
    "total_pv_cut_gwh_2018_2025": round(float(fy.loc[2018:2025, "pv_cut_gwh"].sum()), 1),
    "fy_pv_cut_gwh": {int(k): round(float(v), 1) for k, v in fy.pv_cut_gwh.items()},
    "fy_pv_cut_rate_pct": {int(k): round(float(v), 2) for k, v in fy.pv_cut_rate_pct.items()},
    "fy_cut_days": {int(k): int(v) for k, v in fy.cut_days.items()},
    "spring_share_pct": round(base["spring"], 1),
    "autumn_share_pct": round(base["autumn"], 1),
    "jun_aug_share_pct": round(float(m_share.loc[[6, 7, 8]].sum()), 1),
    "dec_feb_share_pct": round(float(m_share.loc[[12, 1, 2]].sum()), 1),
    "top_month": int(m_share.idxmax()), "top_month_share_pct": round(float(m_share.max()), 1),
    "noon_11_13_share_pct": round(base["noon"], 1),
    "peak_hour": base["peak_hour"], "peak_hour_share_pct": round(float(hr_share.max()), 1),
    "hours_with_cut_range": [int(hr_share[hr_share > 0.05].index.min()), int(hr_share[hr_share > 0.05].index.max())],
    "holiday_mwh_per_day": round(float(hol_tab.loc[1, "mean"]), 1),
    "weekday_mwh_per_day": round(float(hol_tab.loc[0, "mean"]), 1),
    "holiday_ratio": round(base["holiday_ratio"], 2),
    "holiday_share_of_days_pct": round(float(hol_tab.loc[1, "size"] / hol_tab["size"].sum() * 100), 1),
    "holiday_share_of_cut_pct": round(float(dd[dd.holiday == 1].pv_cut.sum() / dd.pv_cut.sum() * 100), 1),
    "avg_gwh_2018_2022": round(float(avg_early), 1),
    "avg_gwh_2023_2025": round(float(avg_late), 1),
    "late_vs_early_ratio": round(float(avg_late / avg_early), 2),
    "max_gap_vs_official_pt": round(max_gap, 2),
    "hypotheses": {
        "H1_spring_ge_50": {"value": round(base["spring"], 1), "result": "支持" if base["spring"] >= 50 else "外れ"},
        "H2_noon_ge_50_and_peak_in_11_13": {"value": round(base["noon"], 1), "peak_hour": base["peak_hour"],
                                             "result": "支持" if (base["noon"] >= 50 and 11 <= base["peak_hour"] <= 13) else "外れ"},
        "H3_holiday_ratio_ge_1_5": {"value": round(base["holiday_ratio"], 2), "result": "支持" if base["holiday_ratio"] >= 1.5 else "外れ"},
        "H4_late_ge_2x_early": {"value": round(float(avg_late / avg_early), 2), "result": "支持" if avg_late / avg_early >= 2 else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(rob.to_string())
print(fy.to_string())
