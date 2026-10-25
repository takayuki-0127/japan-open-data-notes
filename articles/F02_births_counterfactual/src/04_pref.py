"""都道府県版：年次の出生数（2010・2014〜2019年）に log の直線をあてはめ、2020〜2022年を予測して実際と比べる
（県別の月次確定数は使っていないため、年単位の簡易版）"""
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import DATA, RES, PREFS

p = pd.read_csv(DATA / "pref_annual.csv", dtype={"code": str})
WINDOWS = {"2014-2019": [2014, 2015, 2016, 2017, 2018, 2019],          # 基本
           "2010,2014-2019": [2010, 2014, 2015, 2016, 2017, 2018, 2019]}  # 頑健性（表にある古い年も入れる）
rows = []
for (wname, train_years), (code, g) in [(w, cg) for w in WINDOWS.items() for cg in p.groupby("code")]:
    g = g.set_index("year").births
    tr = g.loc[train_years]
    X = sm.add_constant(np.array(train_years) - 2019.0)
    r = sm.OLS(np.log(tr.values), X).fit()
    for per, yrs in [("2020", [2020]), ("2021", [2021]), ("2022", [2022]), ("2020-2022", [2020, 2021, 2022])]:
        Xf = sm.add_constant(np.array(yrs) - 2019.0, has_constant="add")
        pr = r.get_prediction(Xf)
        # 予測区間：係数の不確実性＋残差を正規近似でシミュレーション（年ごとの残差は独立と仮定）
        rng = np.random.default_rng(int(code))
        B = rng.multivariate_normal(r.params, r.cov_params(), 4000)
        eps = rng.standard_t(r.df_resid, (4000, len(yrs))) * np.sqrt(r.scale)
        sims = np.exp(B @ Xf.T + eps).sum(1)
        cf = np.exp(pr.predicted_mean).sum()
        act = g.loc[yrs].sum()
        lo, hi = np.percentile(sims, [2.5, 97.5])
        rows.append(dict(window=wname, code=code, pref=PREFS[int(code) - 1], period=per, actual=act, cf=cf, lo95=lo, hi95=hi,
                         gap=act - cf, gap_pct=(act / cf - 1) * 100, outside_low=act < lo, outside_high=act > hi,
                         trend_pct_per_year=(np.exp(r.params[1]) - 1) * 100))
res = pd.DataFrame(rows); res.to_csv(RES / "pref_gap.csv", index=False)
for w, per in [(w, per) for w in WINDOWS for per in ["2020", "2021", "2022", "2020-2022"]]:
    x = res[(res.period == per) & (res.window == w)]
    print(w, per, "national", round((x.actual.sum() / x.cf.sum() - 1) * 100, 2), "gap_pct median", round(x.gap_pct.median(), 2), "below", int(x.outside_low.sum()), "above", int(x.outside_high.sum()),
          "sum gap", round(x.gap.sum()))
a = res[(res.period == "2020-2022")].pivot(index="pref", columns="window", values="gap_pct")
print("spearman between windows", round(a.corr(method="spearman").iloc[0, 1], 2))
x = res[(res.period == "2020-2022") & (res.window == "2014-2019")].sort_values("gap_pct")
print(x[["pref", "actual", "cf", "gap_pct", "outside_low", "outside_high", "trend_pct_per_year"]].round(1).head(6).to_string())
print(x[["pref", "actual", "cf", "gap_pct", "outside_low", "outside_high", "trend_pct_per_year"]].round(1).tail(6).to_string())
