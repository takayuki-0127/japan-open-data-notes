"""03 分析：開花の早まりを、全国並みの温暖化（N）と地点の上乗せ（U）に分ける"""
import json, pathlib
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import theilslopes, spearmanr

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
P0, P1 = (1961, 1990), (1996, 2025)


def prep(months=(2, 3), y0=1961, y1=2025, nmin=50):
    d = pd.read_csv(ROOT / "data" / "panel.csv", dtype={"st": str})
    d = d[(d.year >= y0) & (d.year <= y1)].copy()
    d["T"] = d[[f"t{m}" for m in months]].mean(axis=1, skipna=False)
    d["N"] = d[[f"n{m}" for m in months]].mean(axis=1)
    d = d.dropna(subset=["T"])
    cnt = d.groupby("st").year.transform("size")
    d = d[cnt >= nmin].copy()
    d["R"] = d["T"] - d["N"]                       # 地点の気温のうち、全国の偏差で説明されない部分
    d["U"] = d.R - d.groupby("st").R.transform("mean")
    return d


def fe(d, trend=False):
    f = "doy ~ N + U + C(st)" + (" + year" if trend else "")
    m = smf.ols(f, data=d).fit(cov_type="cluster", cov_kwds={"groups": d.year})
    out = {k: (m.params[k], m.bse[k]) for k in ["N", "U"]}
    if trend:
        out["year"] = (m.params["year"], m.bse["year"])
    return out


def change(d, b):
    """地点ごとに、1961〜1990年平均 → 1996〜2025年平均の変化を、N・U の分と残りに分ける"""
    rows = []
    for st, g in d.groupby("st"):
        a = g[g.year.between(*P0)]
        c = g[g.year.between(*P1)]
        if len(a) < 20 or len(c) < 20:
            continue
        dd, dn, du = c.doy.mean() - a.doy.mean(), c.N.mean() - a.N.mean(), c.U.mean() - a.U.mean()
        rows.append(dict(st=st, name=g.name.iloc[0], d_doy=dd, d_N=dn, d_U=du,
                         by_N=b["N"][0] * dn, by_U=b["U"][0] * du, base_T=a["T"].mean()))
    r = pd.DataFrame(rows)
    r["rest"] = r.d_doy - r.by_N - r.by_U
    return r


def station_stats(d):
    rows = []
    for st, g in d.groupby("st"):
        s_doy = theilslopes(g.doy, g.year)[0] * 10
        s_u = theilslopes(g.U, g.year)[0] * 10
        s_t = theilslopes(g["T"], g.year)[0] * 10
        x = g["T"] - g["T"].mean()
        sens = float((x * (g.doy - g.doy.mean())).sum() / (x ** 2).sum())
        rows.append(dict(st=st, name=g.name.iloc[0], n=len(g), trend_doy=s_doy, trend_U=s_u, trend_T=s_t,
                         sens=sens, mean_T=g["T"].mean(), mean_doy=g.doy.mean()))
    return pd.DataFrame(rows)


def summarize(d, label):
    b = fe(d)
    c = change(d, b)
    s = station_stats(d)
    rho = spearmanr(s.trend_U, s.trend_doy)[0]
    tot = c.d_doy.mean()
    return dict(label=label, n_st=int(d.st.nunique()), n_obs=int(len(d)),
                b_N=b["N"][0], se_N=b["N"][1], b_U=b["U"][0], se_U=b["U"][1],
                d_doy_median=float(c.d_doy.median()), d_doy_mean=float(tot),
                by_N_mean=float(c.by_N.mean()), by_U_mean=float(c.by_U.mean()), rest_mean=float(c.rest.mean()),
                share_U=float(c.by_U.mean() / tot), rho_U_doy=float(rho), n_change=int(len(c)))


def main():
    d = prep()
    main_ = summarize(d, "基本（2〜3月、50年以上、1961〜2025年）")
    b = fe(d)
    c = change(d, b)
    s = station_stats(d)
    c.round(4).to_csv(RES / "station_change.csv", index=False)
    s.round(4).to_csv(RES / "station_trends.csv", index=False)

    # 全国平均の開花日（地点の平年差の平均）と全国の気温
    d["anom"] = d.doy - d.groupby("st").doy.transform("mean")
    yr = d.groupby("year").agg(anom=("anom", "mean"), N=("N", "first"), U=("U", "mean"), n=("st", "size")).reset_index()
    yr.round(4).to_csv(RES / "yearly.csv", index=False)

    # H5：もともと暖かい地点（上位4分の1）の、気温1℃あたりの早まり
    q = s.mean_T.quantile(0.75)
    warm, other = s[s.mean_T >= q], s[s.mean_T < q]
    h5 = dict(q75_T=float(q), sens_warm_median=float(warm.sens.median()), sens_other_median=float(other.sens.median()),
              warm_names=warm.sort_values("mean_T").name.tolist())

    # 頑健性
    rob = [main_]
    rob.append(summarize(prep(months=(3,)), "気温を3月だけ"))
    rob.append(summarize(prep(months=(1, 2, 3)), "気温を1〜3月"))
    rob.append(summarize(prep(nmin=40), "40年以上の地点"))
    rob.append(summarize(prep(nmin=60), "60年以上の地点"))
    d20 = prep(y1=2020, nmin=45)
    rob.append(summarize(d20, "1961〜2020年（45年以上）"))
    bt = fe(d, trend=True)
    rob.append(dict(label="年トレンドを入れた回帰", b_N=bt["N"][0], se_N=bt["N"][1], b_U=bt["U"][0], se_U=bt["U"][1],
                    b_year_decade=bt["year"][0] * 10, se_year_decade=bt["year"][1] * 10))
    pd.DataFrame(rob).round(4).to_csv(RES / "robustness.csv", index=False)

    # 問い直し：上乗せの傾向が大きい地点と小さい地点
    top = s.sort_values("trend_U", ascending=False)
    out = dict(main=main_, h5=h5,
               trend_doy_median=float(s.trend_doy.median()), share_earlier=float((s.trend_doy < 0).mean()),
               trend_U_median=float(s.trend_U.median()), trend_T_median=float(s.trend_T.median()),
               trend_N_decade=float(theilslopes(yr.N, yr.year)[0] * 10),
               corr_year_anom_N=float(np.corrcoef(yr.anom, yr.N)[0, 1]),
               top_U=top.head(8)[["name", "trend_U", "trend_doy"]].round(3).values.tolist(),
               bottom_U=top.tail(8)[["name", "trend_U", "trend_doy"]].round(3).values.tolist(),
               d_N_mean=float(c.d_N.mean()), d_U_mean=float(c.d_U.mean()),
               share_U_pos=float((c.d_U > 0).mean()))
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(pd.DataFrame(rob).round(3).to_string())


if __name__ == "__main__":
    main()
