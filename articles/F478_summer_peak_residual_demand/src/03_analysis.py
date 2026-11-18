"""夏の日ごとの需要の山と残余需要の山の時刻、夏ごとの集計、期間の比較、頑健性。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
AREAS = ["関西", "九州"]  # 北から南
P0, P1 = (2016, 2018), (2024, 2026)


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def daily(h):
    h = h.copy()
    h["resid"] = h.demand - h.pv - h.wind
    h["resid_pv_only"] = h.demand - h.pv
    h["resid_nocut"] = h.demand - (h.pv + h.pv_cut) - (h.wind + h.wind_cut)
    h["date"] = h.dt.str[:10]
    rows = []
    for (area, date), g in h.groupby(["area", "date"], sort=True):
        g = g.sort_values("hour")
        i_d = g.demand.values.argmax()
        rec = {"area": area, "date": date, "year": int(g.year.iloc[0]), "weekday": bool(g.weekday.iloc[0]),
               "demand_max": g.demand.values[i_d], "demand_peak_hour": int(g.hour.values[i_d]),
               "pv_at_demand_peak": g.pv.values[i_d], "pv_max": g.pv.max(), "pv_sum": g.pv.sum(), "demand_sum": g.demand.sum()}
        for col, key in [("resid", "resid"), ("resid_pv_only", "resid_pv_only"), ("resid_nocut", "resid_nocut")]:
            i = g[col].values.argmax()
            rec[f"{key}_max"] = g[col].values[i]; rec[f"{key}_peak_hour"] = int(g.hour.values[i])
        rows.append(rec)
    d = pd.DataFrame(rows)
    d["area"] = pd.Categorical(d.area, AREAS, ordered=True)
    return d.sort_values(["area", "date"]).reset_index(drop=True)


def summarize(d, key_hour, sel):
    return {"median": float(d.loc[sel, key_hour].median()), "mean": float(d.loc[sel, key_hour].mean()),
            "share_ge17_pct": float((d.loc[sel, key_hour] >= 17).mean() * 100), "n_days": int(sel.sum())}


def period_stats(d, area, period, days="weekday", resid="resid"):
    s = d[(d.area == area) & (d.year >= period[0]) & (d.year <= period[1])]
    if days == "weekday":
        s = s[s.weekday]
    elif days == "top10":
        s = s.sort_values(["year", "demand_max"], ascending=[True, False]).groupby("year", sort=True).head(10)
    dem = s.demand_peak_hour; res = s[f"{resid}_peak_hour"]
    return {"demand_median": float(dem.median()), "demand_mean": float(dem.mean()),
            "resid_median": float(res.median()), "resid_mean": float(res.mean()),
            "gap_median": float(res.median() - dem.median()), "gap_mean": float(res.mean() - dem.mean()),
            "demand_ge17_pct": float((dem >= 17).mean() * 100), "resid_ge17_pct": float((res >= 17).mean() * 100),
            "n_days": int(len(s))}


def main():
    h = pd.read_csv(DATA / "summer_hourly.csv")
    d = daily(h)
    d.to_csv(RES / "daily_peaks.csv", index=False, float_format="%.1f")
    main = {"note": "夏＝7〜9月。平日＝土日・祝日・8月13〜16日を除く。時刻はその1時間の始まり（14 は14時台）。残余需要＝エリア需要−太陽光実績−風力実績。"}

    # 夏ごと
    rows = []
    for area in AREAS:
        for y in range(2016, 2027):
            s = d[(d.area == area) & (d.year == y)]
            w = s[s.weekday]
            top = s.sort_values("demand_max", ascending=False).head(10)
            imx = s.demand_max.idxmax(); irx = s.resid_max.idxmax()
            rows.append({"area": area, "year": y,
                         "demand_peak_hour_median_wd": w.demand_peak_hour.median(), "resid_peak_hour_median_wd": w.resid_peak_hour.median(),
                         "demand_peak_hour_mean_wd": w.demand_peak_hour.mean(), "resid_peak_hour_mean_wd": w.resid_peak_hour.mean(),
                         "resid_ge17_pct_wd": (w.resid_peak_hour >= 17).mean() * 100, "demand_ge17_pct_wd": (w.demand_peak_hour >= 17).mean() * 100,
                         "top10_demand_hour_median": top.demand_peak_hour.median(), "top10_resid_hour_median": top.resid_peak_hour.median(),
                         "summer_demand_max": s.loc[imx, "demand_max"], "summer_demand_max_hour": s.loc[imx, "demand_peak_hour"], "summer_demand_max_date": s.loc[imx, "date"],
                         "summer_resid_max": s.loc[irx, "resid_max"], "summer_resid_max_hour": s.loc[irx, "resid_peak_hour"], "summer_resid_max_date": s.loc[irx, "date"],
                         "resid_to_demand_max_ratio": s.loc[irx, "resid_max"] / s.loc[imx, "demand_max"],
                         "pv_share_of_demand_pct": s.pv_sum.sum() / s.demand_sum.sum() * 100,
                         "pv_at_demand_peak_mean_wd": w.pv_at_demand_peak.mean(), "pv_max_mean_wd": w.pv_max.mean()})
    sm = pd.DataFrame(rows)
    sm.to_csv(RES / "summer_summary.csv", index=False, float_format="%.3f")
    main["summer"] = {area: {int(rr.year): {"demand_med": r(rr.demand_peak_hour_median_wd, 1), "resid_med": r(rr.resid_peak_hour_median_wd, 1),
                                            "resid_ge17": r(rr.resid_ge17_pct_wd, 1), "pv_share": r(rr.pv_share_of_demand_pct, 2),
                                            "max_demand": r(rr.summer_demand_max, 0), "max_demand_hour": int(rr.summer_demand_max_hour),
                                            "max_resid": r(rr.summer_resid_max, 0), "max_resid_hour": int(rr.summer_resid_max_hour),
                                            "ratio": r(rr.resid_to_demand_max_ratio, 4)}
                             for rr in sm[sm.area == area].itertuples()} for area in AREAS}

    for area in AREAS:
        x = sm[sm.area == area].set_index("year")
        main[f"{area}_period_means"] = {"ratio_p0": r(x.loc[2016:2018, "resid_to_demand_max_ratio"].mean(), 4), "ratio_p1": r(x.loc[2024:2026, "resid_to_demand_max_ratio"].mean(), 4),
                                        "pv_share_p0": r(x.loc[2016:2018, "pv_share_of_demand_pct"].mean(), 2), "pv_share_p1": r(x.loc[2024:2026, "pv_share_of_demand_pct"].mean(), 2),
                                        "pv_at_demand_peak_p0": r(x.loc[2016:2018, "pv_at_demand_peak_mean_wd"].mean(), 0), "pv_at_demand_peak_p1": r(x.loc[2024:2026, "pv_at_demand_peak_mean_wd"].mean(), 0)}

    # 期間の比較（基本：平日）
    comp = []
    for area in AREAS:
        for days in ["weekday", "all", "top10"]:
            for resid in ["resid", "resid_pv_only", "resid_nocut"]:
                if days != "weekday" and resid != "resid":
                    continue
                for per in [P0, P1, (2016, 2017), (2024, 2025)]:
                    st = period_stats(d, area, per, days, resid)
                    comp.append({"area": area, "days": days, "resid_def": resid, "period": f"{per[0]}-{per[1]}", **st})
    cp = pd.DataFrame(comp)
    cp.to_csv(RES / "period_comparison.csv", index=False, float_format="%.3f")
    get = lambda area, per, days="weekday", resid="resid": cp[(cp.area == area) & (cp.days == days) & (cp.resid_def == resid) & (cp.period == per)].iloc[0]
    for area in AREAS:
        a, b = get(area, "2016-2018"), get(area, "2024-2026")
        main[f"{area}_base"] = {"p0": {k: r(a[k], 3) for k in ["demand_median", "resid_median", "gap_median", "demand_mean", "resid_mean", "gap_mean", "demand_ge17_pct", "resid_ge17_pct", "n_days"]},
                                "p1": {k: r(b[k], 3) for k in ["demand_median", "resid_median", "gap_median", "demand_mean", "resid_mean", "gap_mean", "demand_ge17_pct", "resid_ge17_pct", "n_days"]},
                                "demand_shift_median": r(b.demand_median - a.demand_median, 2), "gap_widen_median": r(b.gap_median - a.gap_median, 2),
                                "demand_shift_mean": r(b.demand_mean - a.demand_mean, 3), "gap_widen_mean": r(b.gap_mean - a.gap_mean, 3)}
    k1, q1 = get("関西", "2024-2026"), get("九州", "2024-2026")
    main["H"] = {"H1_kansai_demand_shift_median_h": main["関西_base"]["demand_shift_median"],
                 "H2_kansai_gap_p1_median_h": r(k1.gap_median, 2),
                 "H3_kansai_gap_widen_median_h": main["関西_base"]["gap_widen_median"],
                 "H4_kyushu_gap_p1": r(q1.gap_median, 2), "H4_kansai_gap_p1": r(k1.gap_median, 2)}
    # 頑健性の表
    rob = []
    for area in AREAS:
        for days, resid, lab in [("weekday", "resid", "基本：平日、残余＝需要−太陽光−風力"), ("all", "resid", "全日"), ("top10", "resid", "需要の上位10日"),
                                 ("weekday", "resid_pv_only", "残余＝需要−太陽光（風力を引かない）"), ("weekday", "resid_nocut", "太陽光・風力の出力制御を足し戻す")]:
            for p0, p1 in [("2016-2018", "2024-2026"), ("2016-2017", "2024-2025")]:
                a, b = get(area, p0, days, resid), get(area, p1, days, resid)
                rob.append({"area": area, "check": lab, "periods": f"{p0}→{p1}", "demand_med0": a.demand_median, "demand_med1": b.demand_median,
                            "resid_med0": a.resid_median, "resid_med1": b.resid_median, "gap0": a.gap_median, "gap1": b.gap_median,
                            "demand_mean_shift": b.demand_mean - a.demand_mean, "resid_ge17_0": a.resid_ge17_pct, "resid_ge17_1": b.resid_ge17_pct})
    rb = pd.DataFrame(rob); rb.to_csv(RES / "robustness.csv", index=False, float_format="%.3f")
    main["robustness_rows"] = len(rb)
    (RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: main[k] for k in ["関西_base", "九州_base", "H"]}, ensure_ascii=False, indent=1))
    print(sm[["area", "year", "demand_peak_hour_median_wd", "resid_peak_hour_median_wd", "resid_ge17_pct_wd", "pv_share_of_demand_pct", "summer_demand_max", "summer_demand_max_hour", "summer_resid_max", "summer_resid_max_hour", "resid_to_demand_max_ratio"]].to_string())
    print(rb.to_string())


if __name__ == "__main__":
    main()
