"""問い直し（結果を見てから足した）：山の時刻はほとんど動かなかった。では、1日の形（昼と夕方の差）は変わったか。
平日の時刻ごとの平均（需要・太陽光・残余需要）を期間ごとに作り、「夕方18時台の残余需要−昼14時台の残余需要」を比べる。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
AREAS = ["関西", "九州"]


def main():
    h = pd.read_csv(DATA / "summer_hourly.csv")
    h = h[h.weekday].copy()
    h["resid"] = h.demand - h.pv - h.wind
    prof = h.groupby(["area", "year", "hour"], sort=True)[["demand", "pv", "resid"]].mean().reset_index()
    prof["area"] = pd.Categorical(prof.area, AREAS, ordered=True)
    prof = prof.sort_values(["area", "year", "hour"])
    prof.to_csv(RES / "requestion_hourly_profile_by_year.csv", index=False, float_format="%.1f")
    out = {"note": "平日の時刻ごとの平均（MW）。14は14時台、18は18時台。"}
    rows = []
    for area in AREAS:
        for y in range(2016, 2027):
            p = prof[(prof.area == area) & (prof.year == y)].set_index("hour")
            rows.append({"area": area, "year": y, "demand14": p.loc[14, "demand"], "demand18": p.loc[18, "demand"],
                         "pv14": p.loc[14, "pv"], "pv18": p.loc[18, "pv"], "resid14": p.loc[14, "resid"], "resid18": p.loc[18, "resid"],
                         "evening_minus_midday_resid": p.loc[18, "resid"] - p.loc[14, "resid"],
                         "evening_minus_midday_pct_of_demand14": (p.loc[18, "resid"] - p.loc[14, "resid"]) / p.loc[14, "demand"] * 100,
                         "resid_peak_hour_of_mean_profile": int(p.resid.idxmax()), "demand_peak_hour_of_mean_profile": int(p.demand.idxmax())})
    t = pd.DataFrame(rows)
    t.to_csv(RES / "requestion_evening_vs_midday.csv", index=False, float_format="%.2f")
    for area in AREAS:
        s = t[t.area == area].set_index("year")
        a, b = s.loc[2016:2018].mean(numeric_only=True), s.loc[2024:2026].mean(numeric_only=True)
        out[area] = {"p0": {k: round(float(a[k]), 1) for k in ["demand14", "demand18", "pv14", "pv18", "resid14", "resid18", "evening_minus_midday_resid", "evening_minus_midday_pct_of_demand14"]},
                     "p1": {k: round(float(b[k]), 1) for k in ["demand14", "demand18", "pv14", "pv18", "resid14", "resid18", "evening_minus_midday_resid", "evening_minus_midday_pct_of_demand14"]},
                     "by_year_gap_mw": {int(y): round(float(v), 0) for y, v in s.evening_minus_midday_resid.items()},
                     "first_year_resid18_gt_resid14": next((int(y) for y, v in s.evening_minus_midday_resid.items() if v > 0), None)}
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
