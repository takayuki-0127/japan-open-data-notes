"""03 分析：日照時間・全天日射量の指数、折れ線の折れ目、日照計の切り替えの前後"""
import json, pathlib
import numpy as np, pandas as pd
from scipy.stats import theilslopes

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)


def load():
    d = pd.read_csv(ROOT / "data" / "panel.csv", dtype={"st": str})
    return d[(d.year >= 1961) & (d.year <= 2025)].copy()


def index(d, var, nmin, agg="median"):
    x = d.dropna(subset=[var])
    ok = x.groupby("st")[var].transform("size") >= nmin
    x = x[ok].copy()
    ref = x[x.year.between(1991, 2020)].groupby("st")[var].mean()
    x["idx"] = 100 * x[var] / x.st.map(ref)
    x = x.dropna(subset=["idx"])
    return x.groupby("year").idx.agg(agg), x


def broken(y, lo=1970, hi=2010, drop=None):
    """2本の直線を折れ目でつなぐ（連続）。折れ目の年は残差の二乗和が最小の年"""
    t = y.index.values.astype(float); v = y.values
    keep = np.ones_like(t, bool) if drop is None else ~np.isin(t, drop)
    best = None
    for k in range(lo, hi + 1):
        X = np.column_stack([np.ones_like(t), t - k, np.maximum(t - k, 0)])
        b, *_ = np.linalg.lstsq(X[keep], v[keep], rcond=None)
        sse = float(((X[keep] @ b - v[keep]) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, k, b)
    sse, k, b = best
    return dict(k=int(k), before=float(b[1] * 10), after=float((b[1] + b[2]) * 10), sse=sse)


def summarize(d, label, nmin_s=60, nmin_r=50, agg="median", lo=1970, hi=2010, drop=None):
    s, xs = index(d, "sun", nmin_s, agg)
    r, xr = index(d, "rad", nmin_r, agg)
    bs = broken(s, lo, hi, drop)
    k = bs["k"]
    rb = r[r.index < k]; ra = r[r.index >= k]
    if drop is not None:
        rb = rb[~rb.index.isin(drop)]; ra = ra[~ra.index.isin(drop)]
    rad_before = theilslopes(rb.values, rb.index)[0] * 10
    rad_after = theilslopes(ra.values, ra.index)[0] * 10
    both = pd.concat([s, r], axis=1, keys=["s", "r"]).dropna()
    return dict(label=label, n_sun=int(xs.st.nunique()), n_rad=int(xr.st.nunique()), k=k,
                sun_before=bs["before"], sun_after=bs["after"],
                rad_before=float(rad_before), rad_after=float(rad_after),
                corr=float(np.corrcoef(both.s, both.r)[0, 1])), s, r


def ratio_shift(d):
    """同じ地点の日照時間÷全天日射量の比：1981〜1985年平均と1987〜1991年平均"""
    x = d.dropna(subset=["sun", "rad"]).copy()
    x["q"] = x.sun / x.rad
    a = x[x.year.between(1981, 1985)].groupby("st").q.mean()
    b = x[x.year.between(1987, 1991)].groupby("st").q.mean()
    m = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
    m["chg"] = 100 * (m.b / m.a - 1)
    # 比の年ごとの推移（地点の比を1991〜2020年平均で割った指数の中央値）
    ref = x[x.year.between(1991, 2020)].groupby("st").q.mean()
    x["qi"] = 100 * x.q / x.st.map(ref)
    qy = x.dropna(subset=["qi"]).groupby("year").qi.median()
    return m, qy


def main():
    d = load()
    m, s, r = summarize(d, "基本（日照60年以上・日射50年以上、中央値、折れ目1970〜2010年）")
    rs, qy = ratio_shift(d)
    rs.round(4).to_csv(RES / "ratio_shift.csv")
    qy.rename("ratio_idx").round(3).to_csv(RES / "ratio_yearly.csv")

    # 折れ目の年ごとの残差（どのくらい折れ目の年が決まっているか）
    sse = []
    for k in range(1970, 2011):
        sse.append((k, broken(s, k, k)["sse"]))
    pd.DataFrame(sse, columns=["k", "sse"]).round(3).to_csv(RES / "breakpoint_sse.csv", index=False)

    rob = [m]
    rob.append(summarize(d, "日照50年以上の地点", nmin_s=50)[0])
    rob.append(summarize(d, "平均で", agg="mean")[0])
    rob.append(summarize(d, "折れ目を1975〜2005年で探す", lo=1975, hi=2005)[0])
    rob.append(summarize(d, "1985〜1988年を除く", drop=[1985, 1986, 1987, 1988])[0])
    R = pd.DataFrame(rob)
    R.round(4).to_csv(RES / "robustness.csv", index=False)

    # 問い直し：1986年の段差をそろえる
    fac = 1 + rs.chg.median() / 100                     # 1986年以降の値 ÷ 以前の値（比の変化、地点の中央値）
    d2 = d.copy()
    d2.loc[d2.year <= 1985, "sun"] = d2.loc[d2.year <= 1985, "sun"] * fac
    s_adj, _ = index(d2, "sun", 60)
    ba = broken(s_adj)
    br = broken(r)
    both_adj = pd.concat([s_adj, r], axis=1, keys=["s", "r"]).dropna()
    # 段差のダミーを入れた折れ線（調整なしの指数で）
    t = s.index.values.astype(float); v = s.values
    best = None
    for k in range(1970, 2011):
        X = np.column_stack([np.ones_like(t), t - k, np.maximum(t - k, 0), (t >= 1986).astype(float)])
        b, *_ = np.linalg.lstsq(X, v, rcond=None)
        e = float(((X @ b - v) ** 2).sum())
        if best is None or e < best[0]:
            best = (e, k, b)
    adj = dict(factor=float(fac), k_adj=ba["k"], before_adj=ba["before"], after_adj=ba["after"],
               corr_adj=float(np.corrcoef(both_adj.s, both_adj.r)[0, 1]),
               k_rad=br["k"], rad_before_bl=br["before"], rad_after_bl=br["after"],
               k_dummy=int(best[1]), before_dummy=float(best[2][1] * 10), after_dummy=float((best[2][1] + best[2][2]) * 10),
               step_dummy=float(best[2][3]),
               adj_1961_1965=float(s_adj.loc[1961:1965].mean()), adj_min5=float(s_adj.rolling(5, center=True).mean().min()),
               adj_min5_year=int(s_adj.rolling(5, center=True).mean().idxmin()), adj_2021_2025=float(s_adj.loc[2021:2025].mean()))
    pd.DataFrame({"sun_idx": s, "sun_adj_idx": s_adj, "rad_idx": r}).round(3).to_csv(RES / "yearly.csv")

    # 問い直し：期間の平均の比較（1961〜1985年の最小の5年平均と、最近の5年平均）
    roll = s.rolling(5, center=True).mean()
    out = dict(main=m, adjusted=adj, ratio_shift_median=float(rs.chg.median()), ratio_shift_n=int(len(rs)),
               ratio_shift_share_up=float((rs.chg > 0).mean()),
               sun_idx_1961_1965=float(s.loc[1961:1965].mean()), sun_idx_min5=float(roll.min()),
               sun_idx_min5_year=int(roll.idxmin()), sun_idx_2021_2025=float(s.loc[2021:2025].mean()),
               rad_idx_1961_1965=float(r.loc[1961:1965].mean()), rad_idx_min5=float(r.rolling(5, center=True).mean().min()),
               rad_idx_min5_year=int(r.rolling(5, center=True).mean().idxmin()), rad_idx_2021_2025=float(r.loc[2021:2025].mean()),
               ratio_idx_1981_1985=float(qy.loc[1981:1985].mean()), ratio_idx_1987_1991=float(qy.loc[1987:1991].mean()))
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(R.round(3).to_string())


if __name__ == "__main__":
    main()
