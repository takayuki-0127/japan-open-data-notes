"""婚姻を通じた分：前年の婚姻件数で出生数を説明する回帰（2001〜2019年）に、
実際の婚姻件数と「コロナがなかった場合」の婚姻件数（2010〜2019年の傾向の延長）を入れて差をとる"""
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import monthly, RES

d = monthly()
a = d.groupby("year").agg(births=("births", "sum"), marriages=("marriages", "sum"))
a["lb"], a["lm"] = np.log(a.births), np.log(a.marriages)
a["t"] = a.index - 2000
rows, chan = [], []
for lagname, mk in [("前年", lambda s: s.shift(1)), ("前年と前々年の平均", lambda s: np.log((np.exp(s).shift(1) + np.exp(s).shift(2)) / 2))]:
    a["x"] = mk(a.lm)
    tr = a.loc[2002:2019]
    X = sm.add_constant(tr[["x", "t"]])
    r = sm.OLS(tr.lb, X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    rows.append(dict(lag=lagname, elasticity=r.params["x"], se=r.bse["x"], lo95=r.conf_int().loc["x", 0],
                     hi95=r.conf_int().loc["x", 1], trend=r.params["t"], r2=r.rsquared, n=int(r.nobs)))
    # 婚姻の反実仮想：2010〜2019年の log 婚姻件数の直線を延長
    z = a.loc[2010:2019]
    cf = sm.OLS(z.lm, sm.add_constant(z.t)).fit()
    lm_cf = a.lm.copy()
    yrs = a.index[a.index >= 2020]
    lm_cf.loc[yrs] = cf.params["const"] + cf.params["t"] * a.loc[yrs, "t"]
    x_cf = mk(lm_cf)
    # 係数の不確実性をシミュレーションで区間に
    rng = np.random.default_rng(7)
    B = rng.multivariate_normal(r.params.values, r.cov_params().values, 4000)
    for y in range(2021, 2023):   # コロナ直後（2020〜21年の婚姻 → 2021〜22年の出生）に限る
        xa, xc = a.loc[y, "x"], x_cf.loc[y]
        pa = np.exp(B[:, 0] + B[:, 1] * xa + B[:, 2] * a.loc[y, "t"])
        pc = np.exp(B[:, 0] + B[:, 1] * xc + B[:, 2] * a.loc[y, "t"])
        ch = pa - pc
        chan.append(dict(lag=lagname, year=y, marriages_lag_actual=np.exp(xa), marriages_lag_cf=np.exp(xc),
                         births_actual=a.loc[y, "births"], pred_with_actual_marr=np.median(pa),
                         pred_with_cf_marr=np.median(pc), channel=np.median(ch),
                         channel_lo95=np.percentile(ch, 2.5), channel_hi95=np.percentile(ch, 97.5)))
# 婚姻件数そのものは傾向線から外れたか（2010〜2019年の log 直線、95%予測区間）
z = a.loc[2010:2019]
ols = sm.OLS(z.lm, sm.add_constant(z.t)).fit()
yrs = a.index[a.index >= 2020]
pr = ols.get_prediction(sm.add_constant(a.loc[yrs, "t"], has_constant="add")).summary_frame(alpha=0.05)
mg = pd.DataFrame({"year": yrs, "actual": a.loc[yrs, "marriages"].values, "trend": np.exp(pr["mean"].values),
                   "lo95": np.exp(pr["obs_ci_lower"].values), "hi95": np.exp(pr["obs_ci_upper"].values)})
mg["gap"] = mg.actual - mg.trend
mg.to_csv(RES / "marriage_vs_trend.csv", index=False)
print(mg.round(0).to_string())
# 参考：月次の ARIMAX（差分をとった SARIMA に 12か月婚姻件数の log を L か月ずらして入れる）
from statsmodels.tsa.statespace.sarimax import SARIMAX
ar = []
for L in (9, 10, 12, 15):
    xx = np.log(d.marriages_12m).shift(L).loc["2010":"2019"]
    mm = SARIMAX(np.log(d.births_per_day.loc["2010":"2019"]), exog=xx, order=(1, 1, 1), seasonal_order=(0, 1, 1, 12)).fit(disp=False)
    ar.append(dict(lag_months=L, coef=mm.params.iloc[0], se=mm.bse.iloc[0], aic=mm.aic))
pd.DataFrame(ar).to_csv(RES / "arimax_monthly.csv", index=False)
print(pd.DataFrame(ar).round(3))
pd.DataFrame(rows).to_csv(RES / "marriage_regression.csv", index=False)
c = pd.DataFrame(chan); c.to_csv(RES / "marriage_channel.csv", index=False)
a[["births", "marriages"]].to_csv(RES / "annual_births_marriages.csv")
print(pd.DataFrame(rows).round(3).to_string()); print(c.round(0).to_string())
print(c.groupby("lag")[["channel", "channel_lo95", "channel_hi95"]].sum().round(0))
