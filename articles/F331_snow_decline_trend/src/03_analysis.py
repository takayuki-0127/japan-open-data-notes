"""03 分析：最深積雪・降雪合計の傾向、期間比較、雪の多さ別、極端な大雪、冬の気温との関係"""
import json, pathlib
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import theilslopes, kendalltau

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
Y0, Y1 = 1962, 2025


def prep(var="maxdepth", nmin=50, base_min=5.0):
    d = pd.read_csv(ROOT / "data" / "panel.csv", dtype={"st": str})
    d = d[(d.year >= Y0) & (d.year <= Y1)].dropna(subset=[var]).copy()
    d["v"] = d[var]
    cnt = d.groupby("st").v.transform("size")
    base = d[d.year <= 1991].groupby("st").v.mean()
    d["base"] = d.st.map(base)
    d = d[(cnt >= nmin) & (d.base >= base_min)].copy()
    ref = d[d.year.between(1991, 2020)].groupby("st").v.mean()
    d["ref"] = d.st.map(ref)
    return d


def stations(d):
    rows = []
    for st, g in d.groupby("st"):
        s = theilslopes(g.v, g.year)[0] * 10
        tau, p = kendalltau(g.year, g.v)
        rows.append(dict(st=st, name=g.name.iloc[0], pref=g.pref.iloc[0], n=len(g), base=g.base.iloc[0],
                         ref=g.ref.iloc[0], slope=s, slope_pct=100 * s / g.ref.iloc[0], tau=tau, p=p))
    return pd.DataFrame(rows)


def period_change(d, a=(1962, 1991), b=(1996, 2025)):
    m0 = d[d.year.between(*a)].groupby("st").v.agg(["mean", "size"])
    m1 = d[d.year.between(*b)].groupby("st").v.agg(["mean", "size"])
    m = m0.join(m1, lsuffix="0", rsuffix="1")
    m = m[(m.size0 >= 15) & (m.size1 >= 15)]
    m["chg_pct"] = 100 * (m.mean1 / m.mean0 - 1)
    return m


def extremes(d, q=0.9):
    thr = d[d.year <= 1991].groupby("st").v.quantile(q)
    e = d.assign(thr=d.st.map(thr))
    e["ext"] = (e.v > e.thr).astype(int)
    e["dec"] = ((e.year - 1966) // 10) * 10 + 1966          # 1966〜1975 …（最初の4年は1962〜1965）
    e.loc[e.year < 1966, "dec"] = 1962
    by = e.groupby("dec").ext.mean()
    p0 = e[e.year.between(1962, 1991)].ext.mean()
    p1 = e[e.year.between(1996, 2025)].ext.mean()
    return by, p0, p1


def fe(d):
    x = d.copy()
    x["y"] = np.log((x.v + 1) / (x.ref + 1))
    m = smf.ols("y ~ djf + C(st)", data=x).fit(cov_type="cluster", cov_kwds={"groups": x.year})
    return m.params["djf"], m.bse["djf"]


def summarize(d, label, q=0.9, a=(1962, 1991), b=(1996, 2025)):
    s = stations(d)
    pc = period_change(d, a, b)
    _, p0, p1 = extremes(d, q)
    bb, se = fe(d)
    terc = pd.qcut(s.set_index("st").base, 3, labels=["少", "中", "多"])
    pct = pc.chg_pct
    by_t = pct.groupby(terc.reindex(pct.index), observed=False).median()
    return dict(label=label, n_st=int(s.shape[0]), chg_median=float(pct.median()), n_chg=int(len(pct)),
                share_down_sig=float(((s.slope < 0) & (s.p < 0.05)).mean()),
                share_down=float((s.slope < 0).mean()), slope_pct_median=float(s.slope_pct.median()),
                chg_low=float(by_t["少"]), chg_mid=float(by_t["中"]), chg_high=float(by_t["多"]),
                ext_p0=float(p0), ext_p1=float(p1), b_djf=float(bb), se_djf=float(se),
                pct_per_deg=float(100 * (np.exp(bb) - 1)))


def main():
    d = prep()
    main_ = summarize(d, "基本（最深積雪、50冬以上、平均5cm以上）")
    s = stations(d)
    pc = period_change(d)
    s = s.merge(pc.chg_pct.rename("chg_pct"), left_on="st", right_index=True, how="left")
    s.round(4).to_csv(RES / "station_trends.csv", index=False)
    by, _, _ = extremes(d)
    by.rename("ext_share").round(4).to_csv(RES / "extremes_by_decade.csv")

    # 全体の推移：地点ごとに1962〜1991年平均を100とした指数の、地点の中央値
    x = d.assign(idx=100 * d.v / d.base)
    yr = x.groupby("year").agg(idx_median=("idx", "median"), n=("st", "size"), djf=("djf", "first")).reset_index()
    yr.round(4).to_csv(RES / "yearly.csv", index=False)

    rob = [main_]
    rob.append(summarize(prep(var="snowfall"), "降雪の深さの合計"))
    rob.append(summarize(prep(nmin=40), "40冬以上の地点"))
    rob.append(summarize(prep(nmin=55), "55冬以上の地点"))
    rob.append(summarize(prep(base_min=2), "平均2cm以上の地点"))
    rob.append(summarize(prep(base_min=20), "平均20cm以上の地点"))
    rob.append(summarize(d, "期間を1962〜1981年 → 2006〜2025年", a=(1962, 1981), b=(2006, 2025)))
    rob.append(summarize(d, "大雪の基準を上位5%", q=0.95))
    R = pd.DataFrame(rob)
    R.round(4).to_csv(RES / "robustness.csv", index=False)

    # 問い直し：ほとんど積もらなかった冬（1962〜1991年平均の10%未満）の割合
    x["low"] = (x.v < 0.1 * x.base).astype(int)
    low = x.groupby(np.where(x.year <= 1991, "1962-1991", np.where(x.year >= 1996, "1996-2025", "other"))).low.mean()
    lowdec = x.assign(dec=np.where(x.year < 1966, 1962, ((x.year - 1966) // 10) * 10 + 1966)).groupby("dec").low.mean()
    lowdec.rename("low_share").round(4).to_csv(RES / "low_by_decade.csv")
    tdj = theilslopes(yr.djf, yr.year)[0] * 10

    out = dict(main=main_, djf_trend_decade=float(tdj),
               low_share_p0=float(low["1962-1991"]), low_share_p1=float(low["1996-2025"]),
               idx_median_1962_1991=float(yr[yr.year <= 1991].idx_median.mean()),
               idx_median_1996_2025=float(yr[yr.year >= 1996].idx_median.mean()),
               n_up_sig=int(((s.slope > 0) & (s.p < 0.05)).sum()),
               n_down_sig=int(((s.slope < 0) & (s.p < 0.05)).sum()),
               top_base=s.sort_values("base", ascending=False).head(6)[["name", "base", "chg_pct"]].round(1).values.tolist())
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(R.round(3).to_string())


if __name__ == "__main__":
    main()
