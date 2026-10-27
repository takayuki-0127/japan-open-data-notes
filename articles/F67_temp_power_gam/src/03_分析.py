"""03 分析：日平均気温と電力需要（日量）の非線形の関係を、スプライン回帰と GAM で推定する。
主な指標は「気温が1℃上がったときの需要の変化率（%）」＝ log(需要) の気温による微分×100。"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from patsy import dmatrix, build_design_matrices
from pygam import LinearGAM, s, f, l
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
GRID = np.round(np.arange(2, 31.01, 0.5), 1)
FE = "C(dow) + holiday + obon + nenmatsu + gw + covid + C(fy)"


def fit(d, temp="temp_mean", df=8, extra="", fe=FE):
    form = f"log_d ~ cr({temp}, df={df}, constraints='center') + {fe}{extra}"
    m = smf.ols(form, data=d).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
    return m


def marg(m, d, temp="temp_mean", grid=GRID, h=0.05):
    """各気温での 1℃あたりの変化率（%）と95%区間（デルタ法）、水準（基準日の予測 GWh）"""
    base = d.iloc[[0]].copy()
    for c in ["dow", "holiday", "obon", "nenmatsu", "gw", "covid"]:
        if c in base:
            base[c] = 0
    base["dow"] = 2
    base["fy"] = d.fy.max()
    rows = []
    di = m.model.data.model_spec
    b, V = m.params.values, m.cov_params().values
    for t in grid:
        up, dn, mid = base.copy(), base.copy(), base.copy()
        up[temp], dn[temp], mid[temp] = t + h, t - h, t
        Xu = np.asarray(build_design_matrices([di], up)[0])[0]
        Xd = np.asarray(build_design_matrices([di], dn)[0])[0]
        Xm = np.asarray(build_design_matrices([di], mid)[0])[0]
        g = (Xu - Xd) / (2 * h)
        eff, se = g @ b * 100, np.sqrt(g @ V @ g) * 100
        rows.append(dict(temp=t, pct_per_deg=eff, lo=eff - 1.96 * se, hi=eff + 1.96 * se,
                         level_gwh=np.exp(Xm @ b)))
    return pd.DataFrame(rows)


def trough(m, d, temp="temp_mean", ndraw=1000):
    """需要がいちばん少なくなる気温（係数の分布から引いて区間を出す）"""
    base = d.iloc[[0]].copy(); base["dow"] = 2; base["fy"] = d.fy.max()
    for c in ["holiday", "obon", "nenmatsu", "gw", "covid"]:
        base[c] = 0
    g2 = np.round(np.arange(8, 26.01, 0.1), 1)
    X = np.vstack([np.asarray(build_design_matrices([m.model.data.model_spec],
                   base.assign(**{temp: t}))[0])[0] for t in g2])
    pt = g2[np.argmin(X @ m.params.values)]
    draws = rng.multivariate_normal(m.params.values, m.cov_params().values, size=ndraw)
    tt = g2[np.argmin(X @ draws.T, axis=0)]
    return pt, np.percentile(tt, 2.5), np.percentile(tt, 97.5)


def summary(m, d, label, temp="temp_mean"):
    mm = marg(m, d, temp)
    pt, lo, hi = trough(m, d, temp)
    # 夏の日・冬の日の平均の限界効果（実際の気温で平均）
    def ame(sub):
        mg = marg(m, d, temp, grid=np.round(sub[temp].values, 1))
        return mg.pct_per_deg.mean()
    hot, cold = d[d[temp] >= 26], d[d[temp] <= 8]
    r = dict(model=label, n=len(d), r2=m.rsquared, trough=pt, trough_lo=lo, trough_hi=hi,
             pct_at5=mm.set_index("temp").pct_per_deg.get(5.0), pct_at10=mm.set_index("temp").pct_per_deg.get(10.0),
             pct_at25=mm.set_index("temp").pct_per_deg.get(25.0), pct_at28=mm.set_index("temp").pct_per_deg.get(28.0),
             pct_at30=mm.set_index("temp").pct_per_deg.get(30.0),
             ame_hot=ame(hot) if len(hot) else np.nan, ame_cold=ame(cold) if len(cold) else np.nan,
             n_hot=len(hot), n_cold=len(cold))
    return r, mm


def cv_compare(d):
    """年度で分けた交差検証で、気温の入れ方を比べる（log の RMSE）。
    コロナ期ダミーは年度の効果と重なって外挿が不安定になるため、ここでは入れない"""
    FEc = FE.replace(" + covid", "")
    forms = {
        "直線": "log_d ~ temp_mean + " + FEc,
        "2次式": "log_d ~ temp_mean + I(temp_mean**2) + " + FEc,
        "冷暖房度日（18℃で折れる直線）": "log_d ~ np.maximum(18-temp_mean,0) + np.maximum(temp_mean-18,0) + " + FEc,
        "スプライン（自由度8）": "log_d ~ cr(temp_mean, df=8, constraints='center') + " + FEc,
    }
    out = []
    fys = sorted(d.fy.unique())
    for name, fm in forms.items():
        err = []
        for k in fys[1:]:  # 1年度目は FE が推定できないので除く
            tr, te = d[d.fy != k], d[d.fy == k]
            # 評価年度の水準は学習できないので、年度の効果は前年度の値で代用
            te2 = te.assign(fy=k - 1)
            mm = smf.ols(fm, data=tr).fit()
            p = mm.predict(te2)
            err.append(((te.log_d - p) ** 2).values)
        e = np.concatenate(err)
        out.append(dict(model=name, rmse_log=np.sqrt(e.mean())))
    # pyGAM
    X = d[["temp_mean", "dow", "holiday", "obon", "nenmatsu", "gw", "fy"]].values.astype(float)
    err = []
    for k in fys[1:]:
        tr, te = d.fy != k, d.fy == k
        Xte = X[te].copy(); Xte[:, 6] = k - 1
        g = LinearGAM(s(0, n_splines=20) + f(1) + l(2) + l(3) + l(4) + l(5) + f(6)).gridsearch(
            X[tr], d.log_d.values[tr], progress=False)
        err.append((d.log_d.values[te] - g.predict(Xte)) ** 2)
    out.append(dict(model="GAM（pyGAM、平滑化は自動）", rmse_log=np.sqrt(np.concatenate(err).mean())))
    return pd.DataFrame(out)


def gam_curve(d):
    X = d[["temp_mean", "dow", "holiday", "obon", "nenmatsu", "gw", "covid", "fy"]].values.astype(float)
    g = LinearGAM(s(0, n_splines=20) + f(1) + l(2) + l(3) + l(4) + l(5) + l(6) + f(7)).gridsearch(
        X, d.log_d.values, progress=False)
    XX = g.generate_X_grid(term=0, meshgrid=False)
    XX = np.repeat(X[[0]], len(GRID), axis=0); XX[:, 0] = GRID
    pdep, ci = g.partial_dependence(term=0, X=XX, width=0.95)
    slope = np.gradient(pdep, GRID) * 100
    return pd.DataFrame(dict(temp=GRID, gam_partial=pdep, gam_lo=ci[:, 0], gam_hi=ci[:, 1], gam_pct_per_deg=slope)), g


def by_hour(path):
    h = pd.read_csv(path, parse_dates=["ts", "date"])
    dd = pd.read_csv(DATA / "daily_tokyo.csv", parse_dates=["date"])[["date", "dow", "obon", "nenmatsu", "gw", "covid", "fy"]]
    h = h.merge(dd, on="date")
    h["log_d"] = np.log(h.demand)
    rows = []
    for hr in range(24):
        x = h[h.hour == hr].reset_index(drop=True)
        m = fit(x)
        mm = marg(m, x, grid=np.array([5.0, 10.0, 25.0, 28.0, 30.0])).set_index("temp")
        rows.append(dict(hour=hr, **{f"pct_at{int(t)}": mm.loc[t, "pct_per_deg"] for t in mm.index},
                         **{f"lo{int(t)}": mm.loc[t, "lo"] for t in mm.index},
                         **{f"hi{int(t)}": mm.loc[t, "hi"] for t in mm.index}))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    t = pd.read_csv(DATA / "daily_tokyo.csv", parse_dates=["date"])
    k = pd.read_csv(DATA / "daily_kansai.csv", parse_dates=["date"])

    # 本体
    m = fit(t)
    r0, mm0 = summary(m, t, "本体（東京、2016〜2026年度、日平均気温）")
    mm0.to_csv(RES / "marginal_main.csv", index=False)
    gc, g = gam_curve(t)
    gc.to_csv(RES / "gam_curve.csv", index=False)

    # 期間別
    rows, curves = [r0], []
    for lab, a, b in [("2016〜2019年度", 2016, 2019), ("2020〜2022年度", 2020, 2022), ("2023〜2026年度", 2023, 2026)]:
        dd = t[(t.fy >= a) & (t.fy <= b)].reset_index(drop=True)
        mp = fit(dd)
        r, mm = summary(mp, dd, "期間：" + lab)
        rows.append(r); curves.append(mm.assign(period=lab))
    pd.concat(curves).to_csv(RES / "marginal_by_period.csv", index=False)

    # 東京と関西（同じ期間 2024年4月〜）
    t2 = t[t.date >= "2024-04-02"].reset_index(drop=True)
    for lab, dd in [("東京（2024年4月〜）", t2), ("関西（2024年4月〜）", k)]:
        mp = fit(dd, fe=FE.replace(" + covid", ""))
        r, mm = summary(mp, dd, "地域：" + lab)
        rows.append(r); mm.assign(area=lab).to_csv(RES / f"marginal_{'tokyo24' if '東京' in lab else 'kansai'}.csv", index=False)

    # 頑健性
    rob = [
        ("最高気温で見る", dict(temp="temp_max")),
        ("自由度を5にする", dict(df=5)),
        ("自由度を12にする", dict(df=12)),
        ("湿度を加える", dict(extra=" + humid")),
        ("前日の気温も加える", dict(extra=" + cr(temp_lag1, df=5, constraints='center')")),
        ("月の違いも除く", dict(extra=" + C(month)")),
    ]
    for lab, kw in rob:
        tmp = kw.get("temp", "temp_mean")
        mp = fit(t, **kw)
        r, _ = summary(mp, t, "頑健性：" + lab, temp=tmp)
        rows.append(r)
    for lab, dd in [("平日だけ", t[t.offday == 0]), ("コロナ期（2020年4月〜2021年9月）を除く", t[t.covid == 0])]:
        dd = dd.reset_index(drop=True)
        mp = fit(dd, fe=FE.replace(" + covid", "") if "コロナ" in lab else FE)
        r, _ = summary(mp, dd, "頑健性：" + lab)
        rows.append(r)
    res = pd.DataFrame(rows)
    res.to_csv(RES / "summary.csv", index=False)

    # 気温の入れ方の比較
    cv = cv_compare(t)
    cv.to_csv(RES / "cv_compare.csv", index=False)

    # 時刻別
    bh = by_hour(DATA / "raw" / "hourly_tokyo.csv")
    bh.to_csv(RES / "by_hour.csv", index=False)

    pd.set_option("display.width", 250)
    print(res[["model", "n", "r2", "trough", "trough_lo", "trough_hi", "pct_at5", "pct_at10", "pct_at25",
               "pct_at28", "pct_at30", "ame_hot", "ame_cold", "n_hot", "n_cold"]].round(2).to_string())
    print(cv.round(4).to_string())
    print(bh[["hour", "pct_at5", "pct_at30"]].round(2).to_string())
    print(gc.iloc[::6].round(3).to_string())
