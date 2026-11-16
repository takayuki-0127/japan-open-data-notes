"""03 分析：日本付近の台風の動く速さと、とどまる時間"""
import json, pathlib
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import theilslopes

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
BOX = dict(base=(30, 45, 128, 148), wide=(25, 45, 120, 150), narrow=(30, 40, 128, 145))


def load(box="base", y0=1977, y1=2025, extra=False):
    d = pd.read_csv(ROOT / "data" / "segments.csv")
    la0, la1, lo0, lo1 = BOX[box]
    d = d[(d.latm >= la0) & (d.latm < la1) & (d.lonm >= lo0) & (d.lonm < lo1)]
    d = d[(d.year >= y0) & (d.year <= y1)]
    if not extra:
        d = d[d.extra == 0]
    return d.copy()


def yearly(d, stat="mean"):
    return d.groupby("year").speed.agg(stat)


def hac_trend(y):
    X = sm.add_constant(np.asarray(y.index, float))
    m = sm.OLS(y.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    return m.params[1] * 10, m.bse[1] * 10, m.pvalues[1]


def fe_trend(d):
    x = d.assign(latb=(d.latm // 5).astype(int))
    m = smf.ols("speed ~ year + C(month) + C(latb)", data=x).fit(cov_type="cluster", cov_kwds={"groups": x.year})
    return m.params["year"] * 10, m.bse["year"] * 10, m.pvalues["year"]


def hours(d, a, b):
    h = d.groupby(["sid", "year"]).size().reset_index(name="n")
    h["hours"] = 6 * h.n
    return h[h.year.between(*a)].hours.mean(), h[h.year.between(*b)].hours.mean(), h


def summarize(d, label, stat="mean", a=(1977, 2000), b=(2001, 2025)):
    y = yearly(d, stat)
    s0 = d[d.year.between(*a)].speed.agg(stat)
    s1 = d[d.year.between(*b)].speed.agg(stat)
    tr, se, p = hac_trend(y)
    ts = theilslopes(y.values, y.index)[0] * 10
    fb, fse, fp = fe_trend(d)
    h0, h1, _ = hours(d, a, b)
    return dict(label=label, n_seg=int(len(d)), n_storm=int(d.sid.nunique()), speed0=float(s0), speed1=float(s1),
                chg_pct=float(100 * (s1 / s0 - 1)), trend_decade=float(tr), trend_se=float(se), trend_p=float(p),
                theil_decade=float(ts), fe_decade=float(fb), fe_se=float(fse), fe_p=float(fp),
                hours0=float(h0), hours1=float(h1))


def main():
    d = load()
    main_ = summarize(d, "基本（北緯30〜45度・東経128〜148度、1977〜2025年、温帯低気圧化の後を除く）")
    y = d.groupby("year").agg(speed=("speed", "mean"), n_seg=("speed", "size"), n_storm=("sid", "nunique")).reset_index()
    y.round(4).to_csv(RES / "yearly.csv", index=False)
    _, _, h = hours(d, (1977, 2000), (2001, 2025))
    h.to_csv(RES / "storm_hours.csv", index=False)

    # 緯度帯ごとの速さ（期間別）
    x = d.assign(latb=(d.latm // 2.5) * 2.5, per=np.where(d.year <= 2000, "1977-2000", "2001-2025"))
    lb = x.groupby(["latb", "per"]).speed.mean().unstack().round(3)
    lb.to_csv(RES / "speed_by_lat.csv")
    # 月ごと
    mb = x.groupby(["month", "per"]).speed.agg(["mean", "size"]).unstack().round(3)
    mb.columns = [f"{a}_{b}" for a, b in mb.columns]
    mb.to_csv(RES / "speed_by_month.csv")

    rob = [main_]
    rob.append(summarize(load("wide"), "箱を広げる（北緯25〜45度・東経120〜150度）"))
    rob.append(summarize(load("narrow"), "箱を狭める（北緯30〜40度・東経128〜145度）"))
    rob.append(summarize(load(extra=True), "温帯低気圧化の後も含める"))
    rob.append(summarize(load(y0=1951), "1951年から", a=(1951, 1988), b=(1989, 2025)))
    rob.append(summarize(d, "速さの中央値", stat="median"))
    R = pd.DataFrame(rob)
    R.round(6).to_csv(RES / "robustness.csv", index=False)

    # 問い直し：遅い区間（時速15km未満）の割合
    slow0 = (d[d.year <= 2000].speed < 15).mean()
    slow1 = (d[d.year >= 2001].speed < 15).mean()
    # 月の構成の変化：区間の月の分布
    mshare = x.groupby(["per", "month"]).size().groupby(level=0).transform(lambda s: s / s.sum()).unstack().round(4)
    mshare.to_csv(RES / "month_share.csv")
    south = d[d.latm < 35]; north = d[d.latm >= 35]
    fs, fn = fe_trend(south), fe_trend(north)
    lat_split = dict(south_speed0=float(south[south.year <= 2000].speed.mean()), south_speed1=float(south[south.year >= 2001].speed.mean()),
                     north_speed0=float(north[north.year <= 2000].speed.mean()), north_speed1=float(north[north.year >= 2001].speed.mean()),
                     south_fe=fs[0], south_fe_p=float(fs[2]), north_fe=fn[0], north_fe_p=float(fn[2]),
                     south_n=int(len(south)), north_n=int(len(north)))
    out = dict(main=main_, lat_split=lat_split, slow_share0=float(slow0), slow_share1=float(slow1),
               storms_per_year0=float(y[y.year <= 2000].n_storm.mean()), storms_per_year1=float(y[y.year >= 2001].n_storm.mean()),
               aug_sep_share0=float(mshare.loc["1977-2000", [8, 9]].sum()), aug_sep_share1=float(mshare.loc["2001-2025", [8, 9]].sum()))
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(R.round(3).to_string())
    print(lb); print(mb)


if __name__ == "__main__":
    main()
