"""03 分析：地点ごとの開花日の傾き（10年あたり日数）、うめとさくらの比較、ばらつき、間隔と緯度、頑健性。
出力：results/main.json, results/station_trends.csv, results/robustness.csv, results/yearly_mean.csv
"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
MIN_N = 40


def region(lat, pref):
    return pref


def theil(x, y):
    return stats.theilslopes(y, x)[0]


def trends(d, y0, y1, regular_only=True, method="ols", min_n=MIN_N):
    s = d[(d.year >= y0) & (d.year <= y1)]
    if regular_only:
        s = s[s.regular == 1]
    out = []
    for (k, st), g in s.groupby(["kind", "st"], sort=True):
        if len(g) < min_n:
            continue
        x, y = g.year.to_numpy(float), g.doy.to_numpy(float)
        b = theil(x, y) if method == "theil" else np.polyfit(x, y, 1)[0]
        resid = y - np.polyval(np.polyfit(x, y, 1), x)
        out.append((k, st, len(g), b * 10, resid.std(ddof=2), y.mean()))
    return pd.DataFrame(out, columns=["kind", "st", "n", "slope10", "resid_sd", "mean_doy"])


def compare(t):
    w = t.pivot(index="st", columns="kind", values="slope10").dropna()
    diff = w.ume - w.sakura
    k = int((diff < 0).sum()); n = len(diff)
    p = stats.binomtest(k, n, 0.5).pvalue if n else np.nan
    return dict(n_pair=n, ume_med=float(w.ume.median()), sakura_med=float(w.sakura.median()),
                diff_med=float(diff.median()), share_ume_faster=k / n if n else np.nan, sign_p=float(p))


def main():
    d = pd.read_csv(D / "bloom_long.csv")
    st = pd.read_csv(D / "stations.csv").set_index("st")
    t = trends(d, 1961, 2025)
    t = t.join(st, on="st")
    t.round(4).to_csv(R / "station_trends.csv", index=False)
    c = compare(t)
    sd = t.pivot(index="st", columns="kind", values="resid_sd").dropna()
    mean = t.pivot(index="st", columns="kind", values="mean_doy").dropna()
    gap = (mean.sakura - mean.ume)
    lat = st.loc[gap.index, "lat"]
    r_gap = stats.spearmanr(lat, gap)
    # 地点固定効果つきの全地点まとめ（両方そろう地点）
    pair = set(sd.index)
    dd = d[(d.regular == 1) & (d.year.between(1961, 2025)) & d.st.isin(pair)].copy()
    fe = {}
    for k in ["ume", "sakura"]:
        m = smf.ols("doy ~ year + C(st)", data=dd[dd.kind == k]).fit()
        fe[k] = float(m.params["year"] * 10)
    # 年ごとの平均（両方そろう地点、地点平均からの偏差の平均）
    dd["anom"] = dd.doy - dd.groupby(["kind", "st"]).doy.transform("mean")
    ym = dd.groupby(["kind", "year"]).anom.agg(["mean", "count"]).reset_index()
    ym.round(4).to_csv(R / "yearly_mean.csv", index=False)
    # 10年ごとの平均の差（最初の10年と最後の10年）
    first = ym[ym.year.between(1961, 1970)].groupby("kind")["mean"].mean()
    last = ym[ym.year.between(2016, 2025)].groupby("kind")["mean"].mean()
    # 北と南で分ける（北緯36度で区切る）
    w = t.pivot(index="st", columns="kind", values="slope10").dropna()
    wl = st.loc[w.index, "lat"]
    north = w[wl >= 36]; south = w[wl < 36]
    main = dict(
        period="1961-2025", min_years=MIN_N,
        n_ume=int((t.kind == "ume").sum()), n_sakura=int((t.kind == "sakura").sum()),
        ume_slope_med=float(t[t.kind == "ume"].slope10.median()),
        sakura_slope_med=float(t[t.kind == "sakura"].slope10.median()),
        share_ume_negative=float((t[t.kind == "ume"].slope10 < 0).mean()),
        share_sakura_negative=float((t[t.kind == "sakura"].slope10 < 0).mean()),
        **{"pair_" + k: v for k, v in c.items()},
        ume_resid_sd_med=float(sd.ume.median()), sakura_resid_sd_med=float(sd.sakura.median()),
        share_ume_sd_larger=float((sd.ume > sd.sakura).mean()),
        gap_med=float(gap.median()), gap_lat_spearman=float(r_gap.statistic), gap_lat_p=float(r_gap.pvalue),
        gap_north_med=float(gap[lat >= 36].median()), gap_south_med=float(gap[lat < 36].median()),
        fe_ume=fe["ume"], fe_sakura=fe["sakura"],
        shift_1960s_to_2016_25_ume=float(last["ume"] - first["ume"]),
        shift_1960s_to_2016_25_sakura=float(last["sakura"] - first["sakura"]),
        north_n=int(len(north)), north_ume_med=float(north.ume.median()), north_sakura_med=float(north.sakura.median()),
        south_n=int(len(south)), south_ume_med=float(south.ume.median()), south_sakura_med=float(south.sakura.median()),
    )
    main["H1"] = "支持" if main["ume_slope_med"] < 0 and main["sakura_slope_med"] < 0 else "外れ"
    main["H2"] = "支持" if main["pair_share_ume_faster"] > 0.5 else "外れ"
    main["H3"] = "支持" if main["ume_resid_sd_med"] > main["sakura_resid_sd_med"] else "外れ"
    main["H4"] = "支持" if main["gap_lat_spearman"] < 0 else "外れ"
    # 頑健性
    rob = []
    for lab, y0, y1, reg, meth in [("本線 1961〜2025年 OLS 正規の種目", 1961, 2025, True, "ols"),
                                   ("1971〜2025年", 1971, 2025, True, "ols"),
                                   ("1991〜2025年（30年以上）", 1991, 2025, True, "ols"),
                                   ("Theil-Sen の傾き", 1961, 2025, True, "theil"),
                                   ("代わりの種目も含める", 1961, 2025, False, "ols")]:
        mn = 30 if y0 == 1991 else MIN_N
        tt = trends(d, y0, y1, reg, meth, mn)
        cc = compare(tt)
        rob.append(dict(check=lab, n_pair=cc["n_pair"], ume_med=cc["ume_med"], sakura_med=cc["sakura_med"],
                        diff_med=cc["diff_med"], share_ume_faster=cc["share_ume_faster"], sign_p=cc["sign_p"]))
    rob.append(dict(check="地点の固定効果つき回帰（全地点まとめ）", n_pair=len(pair), ume_med=fe["ume"], sakura_med=fe["sakura"],
                    diff_med=fe["ume"] - fe["sakura"], share_ume_faster=np.nan, sign_p=np.nan))
    pd.DataFrame(rob).round(4).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()},
              open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.DataFrame(rob))


if __name__ == "__main__":
    main()
