"""03 分析：全国と地点の年降水量のばらつき（期間ごと）、平均の傾き、頑健性。
出力：results/main.json, results/national_rolling.csv, results/periods.csv, results/station_cv.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
P30 = [(1901, 1930), (1931, 1960), (1961, 1990), (1971, 2000), (1996, 2025)]


def iqr(x):
    return float(np.subtract(*np.percentile(x, [75, 25])))


def station_ratio(d, early, late, min_years, measure="cv", detrend=False):
    rows = []
    for st, g in d.groupby("st"):
        g = g[(g.year >= 1901) & (g.year <= 2025)].dropna(subset=["precip"])
        if len(g) < min_years:
            continue
        x = g.set_index("year").precip
        if detrend:
            b = np.polyfit(x.index, x.values, 1); x = pd.Series(x.values - np.polyval(b, x.index) + x.mean(), index=x.index)
        e = x.loc[early[0]:early[1]]; l = x.loc[late[0]:late[1]]
        if len(e) < 25 or len(l) < 25:
            continue
        f = (lambda s: s.std(ddof=1) / s.mean()) if measure == "cv" else (lambda s: iqr(s) / s.median())
        rows.append((st, f(e), f(l)))
    t = pd.DataFrame(rows, columns=["st", "early", "late"])
    return t, dict(n=len(t), share_larger=float((t.late > t.early).mean() * 100), median_ratio=float((t.late / t.early).median()))


def main():
    nat = pd.read_csv(D / "national.csv").set_index("year").anom_mm
    d = pd.read_csv(D / "station_annual.csv")
    d = d[d.year <= 2025]
    roll = pd.DataFrame({"sd30": nat.rolling(30, center=True, min_periods=30).std(), "mean30": nat.rolling(30, center=True, min_periods=30).mean()})
    roll.round(3).to_csv(R / "national_rolling.csv")
    rows = []
    for a, b in P30 + [(1898, 1930)]:
        x = nat.loc[a:b]
        rows.append(dict(period=f"{a}-{b}", sd=float(x.std(ddof=1)), iqr=iqr(x), mean=float(x.mean()), n=len(x)))
    per = pd.DataFrame(rows); per.round(3).to_csv(R / "periods.csv", index=False)
    pv = lambda a, b: per.set_index("period").loc[f"{a}-{b}"]
    e, m_, l = nat.loc[1901:1930], nat.loc[1971:2000], nat.loc[1996:2025]
    lev1 = stats.levene(e, m_); lev2 = stats.levene(m_, l)
    x = nat.loc[1901:2025]
    lr = stats.linregress(x.index, x.values)
    st, cs = station_ratio(d, (1901, 1930), (1971, 2000), 110)
    st.round(4).to_csv(R / "station_cv.csv", index=False)
    st2, cs2 = station_ratio(d, (1971, 2000), (1996, 2025), 110)
    sd_max_year = int(roll.sd30.idxmax())
    main = dict(sd_1901_1930=float(pv(1901, 1930).sd), sd_1931_1960=float(pv(1931, 1960).sd), sd_1961_1990=float(pv(1961, 1990).sd),
                sd_1971_2000=float(pv(1971, 2000).sd), sd_1996_2025=float(pv(1996, 2025).sd),
                levene_p_early_vs_7100=float(lev1.pvalue), levene_p_7100_vs_recent=float(lev2.pvalue),
                ratio_7100_over_0130=float(pv(1971, 2000).sd / pv(1901, 1930).sd), ratio_recent_over_7100=float(pv(1996, 2025).sd / pv(1971, 2000).sd),
                rolling_sd_max_center_year=sd_max_year, rolling_sd_max=float(roll.sd30.max()),
                rolling_sd_min_center_year=int(roll.sd30.idxmin()), rolling_sd_min=float(roll.sd30.min()),
                rolling_sd_last=float(roll.sd30.dropna().iloc[-1]), rolling_sd_last_center=int(roll.sd30.dropna().index[-1]),
                trend_mm_per_decade=float(lr.slope * 10), trend_p=float(lr.pvalue),
                station_n=cs["n"], station_share_larger_0130_to_7100=cs["share_larger"], station_median_ratio_0130_to_7100=cs["median_ratio"],
                station_n_recent=cs2["n"], station_share_larger_7100_to_recent=cs2["share_larger"], station_median_ratio_7100_to_recent=cs2["median_ratio"],
                mean_1996_2025=float(pv(1996, 2025)["mean"]), mean_1971_2000=float(pv(1971, 2000)["mean"]),
                max_dry=float(nat.min()), max_dry_year=int(nat.idxmin()), max_wet=float(nat.max()), max_wet_year=int(nat.idxmax()))
    main["H1"] = "支持" if main["sd_1971_2000"] > main["sd_1901_1930"] else "外れ"
    main["H2"] = "支持" if main["sd_1996_2025"] < main["sd_1971_2000"] else "外れ"
    main["H3"] = "支持" if cs["share_larger"] > 50 else "外れ"
    main["H4"] = "支持" if lr.pvalue >= 0.05 else "外れ"
    rob = []
    for lab, (a1, b1), (a2, b2) in [("20年：1901〜20 対 1971〜90", (1901, 1920), (1971, 1990)), ("20年：1971〜90 対 2006〜25", (1971, 1990), (2006, 2025)),
                                    ("40年：1901〜40 対 1961〜2000", (1901, 1940), (1961, 2000)), ("40年：1961〜2000 対 1986〜2025", (1961, 2000), (1986, 2025))]:
        rob.append(dict(check="全国の標準偏差の比 " + lab, value=float(nat.loc[a2:b2].std() / nat.loc[a1:b1].std())))
    rob.append(dict(check="全国の四分位範囲の比 1971〜2000 / 1901〜30", value=float(pv(1971, 2000).iqr / pv(1901, 1930).iqr)))
    rob.append(dict(check="全国の四分位範囲の比 1996〜2025 / 1971〜2000", value=float(pv(1996, 2025).iqr / pv(1971, 2000).iqr)))
    _, c3 = station_ratio(d, (1901, 1930), (1971, 2000), 100)
    rob.append(dict(check=f"地点（100年以上、{c3['n']}地点）：1901〜30→1971〜2000 で変動係数が大きくなった割合（%）", value=c3["share_larger"]))
    _, c4 = station_ratio(d, (1901, 1930), (1971, 2000), 110, measure="iqr")
    rob.append(dict(check="地点（110年以上）：四分位範囲÷中央値で大きくなった割合（%）", value=c4["share_larger"]))
    _, c5 = station_ratio(d, (1901, 1930), (1971, 2000), 110, detrend=True)
    rob.append(dict(check="地点（110年以上）：傾きを除いてから変動係数が大きくなった割合（%）", value=c5["share_larger"]))
    pd.DataFrame(rob).round(4).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(per.round(1)); print(pd.read_csv(R / "robustness.csv").to_string())


if __name__ == "__main__":
    main()
