"""03 分析：夏の始まり・終わり・長さの変化（PLAN.md の H1〜H4 と頑健性）。
出力：results/station_table.csv, results/yearly.csv, results/robustness.csv, results/a2_check.csv, results/main.json
"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
P1, P2 = (1901, 1930), (1996, 2025)
NORTH3 = ["網走", "根室", "寿都"]


def load():
    d = pd.read_csv(DATA / "daily_summary.csv")
    return d[d["missing_apr_nov"] <= 5].copy()


def eligible(d, key, group):
    """1961〜1990年の9割以上の年でしきい値に届く地点（北から南の順）。"""
    b = d[(d.group == group) & d.year.between(1961, 1990)]
    share = b.groupby("station", sort=False)[f"{key}_len"].apply(lambda x: float((x > 0).mean()))
    return [s for s, v in share.items() if v >= 0.9]


def slope(x, y):
    m = np.isfinite(y)
    if m.sum() < 10:
        return np.nan
    return float(np.polyfit(x[m], y[m], 1)[0] * 10)


def sen(x, y):
    m = np.isfinite(y)
    return float(stats.theilslopes(y[m], x[m])[0] * 10)


def per_station(d, key, stations, p1=P1, p2=P2):
    out = []
    for s in stations:
        x = d[d.station == s].sort_values("year")
        a, b = x[x.year.between(*p1)], x[x.year.between(*p2)]
        yr = x.year.values.astype(float)
        L = x[f"{key}_len"].values.astype(float)
        e1, e2 = x.year.between(1901, 1960).values, x.year.between(1961, 2025).values
        out.append({
            "station": s, "group": x.group.iloc[0], "n_years": len(x),
            "start_p1": a[f"{key}_start"].mean(), "start_p2": b[f"{key}_start"].mean(),
            "end_p1": a[f"{key}_end"].mean(), "end_p2": b[f"{key}_end"].mean(),
            "len_p1": a[f"{key}_len"].mean(), "len_p2": b[f"{key}_len"].mean(),
            "slope_len_ols_1901_2025": slope(yr, L), "slope_len_sen_1901_2025": sen(yr, L),
            "slope_len_1901_1960": slope(yr[e1], L[e1]), "slope_len_1961_2025": slope(yr[e2], L[e2]),
            "slope_len_1931_2025": slope(yr[yr >= 1931], L[yr >= 1931]),
        })
    t = pd.DataFrame(out)
    t["start_diff"] = t.start_p2 - t.start_p1
    t["end_diff"] = t.end_p2 - t.end_p1
    t["len_diff"] = t.len_p2 - t.len_p1
    return t


def doy_to_md(v):
    if not np.isfinite(v):
        return ""
    d = pd.Timestamp("2025-01-01") + pd.Timedelta(int(round(float(v))) - 1, unit="D")
    return f"{d.month}月{d.day}日"


def main():
    d = load()
    main_st = eligible(d, "abs25_w7", "rural")
    all_rural = list(d[d.group == "rural"].station.drop_duplicates())
    t = per_station(d, "abs25_w7", main_st)
    t.insert(1, "definition", "abs25_w7")
    tp = per_station(d, "p75_w7", all_rural)
    tp.insert(1, "definition", "p75_w7")
    st_tab = pd.concat([t, tp], ignore_index=True)
    st_tab.round(3).to_csv(RES / "station_table.csv", index=False)

    # 年ごとの平均（本線の地点がそろう年）：長さ・始まり・終わり
    y = d[d.station.isin(main_st)].pivot_table(index="year", columns="station", values=["abs25_w7_len", "abs25_w7_start", "abs25_w7_end"])
    yearly = pd.DataFrame({
        "n_stations": y["abs25_w7_len"].notna().sum(axis=1),
        "len_mean": y["abs25_w7_len"].mean(axis=1),
        "start_mean": y["abs25_w7_start"].mean(axis=1),
        "end_mean": y["abs25_w7_end"].mean(axis=1),
    })
    yearly["len_mean_11yr"] = yearly["len_mean"].rolling(11, center=True, min_periods=6).mean()
    yearly["start_mean_11yr"] = yearly["start_mean"].rolling(11, center=True, min_periods=6).mean()
    yearly["end_mean_11yr"] = yearly["end_mean"].rolling(11, center=True, min_periods=6).mean()
    yearly.round(3).to_csv(RES / "yearly.csv")

    med = lambda s: float(np.round(np.nanmedian(s), 2))
    h1 = med(t.len_diff)
    h2_start, h2_end = med(t.start_diff), med(t.end_diff)
    h3_all = med(tp.len_diff)
    h3_north = med(tp[tp.station.isin(NORTH3)].len_diff)
    e_sl, l_sl = med(t.slope_len_1901_1960), med(t.slope_len_1961_2025)
    h4_ok = (l_sl >= 2 * e_sl) if e_sl > 0 else (l_sl > 0)

    # 頑健性
    rob = []
    def add(name, tab, note=""):
        rob.append({"check": name, "n_stations": len(tab), "len_diff_median": med(tab.len_diff),
                    "start_diff_median": med(tab.start_diff), "end_diff_median": med(tab.end_diff),
                    "slope_len_ols_median": med(tab.slope_len_ols_1901_2025), "note": note})
    add("本線（7日移動平均・25℃、都市化の影響が小さい地点）", t)
    add("移動平均を15日", per_station(d, "abs25_w15", eligible(d, "abs25_w15", "rural")))
    add("しきい値24℃", per_station(d, "abs24_w7", eligible(d, "abs24_w7", "rural")))
    add("しきい値26℃", per_station(d, "abs26_w7", eligible(d, "abs26_w7", "rural")))
    add("地点ごとの基準（上位25%）・15地点", tp)
    add("地点ごとの基準・15日移動平均", per_station(d, "p75_w15", all_rural))
    t31 = per_station(d, "abs25_w7", main_st, p1=(1931, 1960))
    add("比べる前の期間を1931〜1960年", t31)
    t61 = per_station(d, "abs25_w7", main_st, p1=(1961, 1990))
    add("比べる前の期間を1961〜1990年", t61)
    cities = eligible(d, "abs25_w7", "city")
    tc = per_station(d, "abs25_w7", cities)
    add("大都市（比べ用）", tc)
    rob = pd.DataFrame(rob)
    rob["slope_1931_2025_median"] = [np.nan] * len(rob)
    rob.loc[0, "slope_1931_2025_median"] = med(t.slope_len_1931_2025)
    rob.loc[0, "slope_1961_2025_median"] = l_sl
    rob.to_csv(RES / "robustness.csv", index=False)
    tc.insert(1, "definition", "abs25_w7_city")
    tc.round(3).to_csv(RES / "station_table_city.csv", index=False)

    # 照合：日別値から数えた25℃以上の日数 vs 年ごとの値のページ
    a2 = pd.read_csv(DATA / "a2_counts.csv").dropna(subset=["a2_days_ge25"])
    full = pd.read_csv(DATA / "daily_summary.csv")
    m = a2.merge(full[["station", "year", "days_ge25", "missing_apr_nov"]], on=["station", "year"])
    m = m[m.missing_apr_nov == 0]
    m["diff"] = m.days_ge25 - m.a2_days_ge25
    m.to_csv(RES / "a2_check.csv", index=False)

    res = {
        "stations_main": main_st, "n_main": len(main_st),
        "stations_excluded_abs25": [s for s in all_rural if s not in main_st],
        "H1_len_diff_median_days": h1, "H1_support": bool(h1 >= 10),
        "H1_len_p1_median": med(t.len_p1), "H1_len_p2_median": med(t.len_p2),
        "H1_n_stations_longer": int((t.len_diff > 0).sum()),
        "H2_start_diff_median_days": h2_start, "H2_end_diff_median_days": h2_end,
        "H2_start_p1_md": doy_to_md(np.nanmedian(t.start_p1)), "H2_start_p2_md": doy_to_md(np.nanmedian(t.start_p2)),
        "H2_end_p1_md": doy_to_md(np.nanmedian(t.end_p1)), "H2_end_p2_md": doy_to_md(np.nanmedian(t.end_p2)),
        "H2_support": bool(h2_end > -h2_start),
        "H3_len_diff_median_all15": h3_all, "H3_len_diff_median_north3": h3_north,
        "H3_north3_each": {r.station: round(float(r.len_diff), 1) for r in tp[tp.station.isin(NORTH3)].itertuples()},
        "H3_n_longer_of15": int((tp.len_diff > 0).sum()),
        "H3_support": bool(h3_all >= 7 and h3_north > 0),
        "H4_slope_1901_1960_median": e_sl, "H4_slope_1961_2025_median": l_sl, "H4_support": bool(h4_ok),
        "slope_len_ols_1901_2025_median": med(t.slope_len_ols_1901_2025),
        "slope_len_sen_1901_2025_median": med(t.slope_len_sen_1901_2025),
        "yearly_len_mean_1901_1930": float(np.round(yearly.loc[1901:1930, "len_mean"].mean(), 1)),
        "yearly_len_mean_1996_2025": float(np.round(yearly.loc[1996:2025, "len_mean"].mean(), 1)),
        "top5_years_len": [int(v) for v in yearly[yearly.n_stations >= len(main_st) - 1].sort_values("len_mean", ascending=False, kind="mergesort").index[:5]],
        "len_mean_2025": float(np.round(yearly.loc[2025, "len_mean"], 1)),
        "city_len_diff_median": med(tc.len_diff), "city_start_diff_median": med(tc.start_diff), "city_end_diff_median": med(tc.end_diff),
        "city_n": len(cities),
        "a2_check_n": int(len(m)), "a2_check_exact_share": float(np.round((m["diff"] == 0).mean(), 4)),
        "a2_check_max_absdiff": int(m["diff"].abs().max()),
        "rob_len_diff_min": float(rob.loc[rob.check != "大都市（比べ用）", "len_diff_median"].min()),
        "rob_len_diff_max": float(rob.loc[rob.check != "大都市（比べ用）", "len_diff_median"].max()),
    }
    (RES / "main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(rob.to_string())


if __name__ == "__main__":
    main()
