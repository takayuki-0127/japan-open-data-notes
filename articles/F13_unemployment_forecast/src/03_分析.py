"""03 分析：失業率（季節調整値）の1か月先・3か月先をローリングで予測して比べる

予測する時点 T は「T月の失業率が公表された日」（T+1 月の月末）。そのとき使える情報だけを使う。
- 失業率・有効求人倍率・新規求人数・消費者態度指数：T月まで（失業率と求人倍率は同じ日に公表）
- 景気動向指数（CI 先行・一致）・鉱工業生産・労働投入量：T-1月まで（T月分の公表はもう少しあと）
目的変数は変化幅 y_h = u(T+h) - u(T)。
モデルは毎月（ARIMA 系）／毎年1月（ElasticNet・LightGBM）に、その時点までのデータだけで学習し直す。
"""
import sys, warnings
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import ElasticNetCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
from statsmodels.tsa.statespace.sarimax import SARIMAX
from common import DATA, RES, SEED

warnings.filterwarnings("ignore")
np.random.seed(SEED)
H = (1, 3)
EVAL_START = pd.Timestamp("2005-01-01")      # 予測の対象月がここ以降
TRAIN_START = pd.Timestamp("1985-07-01")
COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-01"))

df = pd.read_csv(DATA / "monthly.csv", index_col=0, parse_dates=True)
df = df[df.index >= "1984-01-01"].copy()


def make_features(d, lag_ci=1, lag_job=0):
    """T月の行に、T月の公表時点で使える特徴量を並べる（lag_job=-1 は『まだ公表されていない T+1 月の求人』を使う＝リーク）"""
    f = pd.DataFrame(index=d.index)
    u = d["u_sa"]
    du = u.diff()
    for l in range(6):
        f[f"失業率の変化_{l+1}か月前"] = du.shift(l)
    f["失業率の水準"] = u
    f["失業率_12か月平均との差"] = u - u.rolling(12).mean()
    j = d["jobs_sa"].shift(lag_job)
    no = np.log(d["new_offers"]).shift(lag_job)
    f["有効求人倍率"] = j
    for k in (1, 3, 6):
        f[f"有効求人倍率の変化_{k}か月"] = j - j.shift(k)
    for k in (1, 3, 12):
        f[f"新規求人数の伸び_{k}か月"] = no - no.shift(k)
    cc = d["consumer_conf"].shift(lag_job)
    f["消費者態度指数の変化_3か月"] = cc - cc.shift(3)
    for col, name in (("ci_lead", "CI先行"), ("ci_coin", "CI一致")):
        s = d[col].shift(lag_ci)
        f[f"{name}の変化_1か月"] = s - s.shift(1)
        f[f"{name}の変化_3か月"] = s - s.shift(3)
    for col, name in (("iip", "鉱工業生産"), ("labor_input", "労働投入量")):
        s = np.log(d[col]).shift(lag_ci)
        f[f"{name}の伸び_3か月"] = s - s.shift(3)
    return f


def targets(u):
    return {h: u.shift(-h) - u for h in H}


def fit_ml(kind, X, y):
    if kind == "ElasticNet":
        m = make_pipeline(StandardScaler(), ElasticNetCV(l1_ratio=[.2, .5, .8, 1.0], cv=TimeSeriesSplit(5),
                                                         alphas=30, max_iter=20000, random_state=SEED))
    else:
        m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=20,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                              random_state=SEED, verbose=-1, n_jobs=2)
    return m.fit(X, y)


def arima_forecast(u, exog_cols, T, d):
    """ARIMA(2,1,0)。exog は1か月前の値（Δ求人倍率・Δ新規求人数）。3か月先の exog は『変化なし（0）』と置く"""
    hist = u[(u.index >= TRAIN_START) & (u.index <= T)]
    if exog_cols:
        ex = pd.DataFrame({"dj": d["jobs_sa"].diff().shift(1), "dn": np.log(d["new_offers"]).diff().shift(1)}).loc[hist.index]
        nxt = pd.DataFrame({"dj": [d["jobs_sa"].diff().loc[T], 0, 0], "dn": [np.log(d["new_offers"]).diff().loc[T], 0, 0]})
        m = SARIMAX(hist.values, exog=ex.values, order=(2, 1, 0), trend="n").fit(disp=False)
        fc = m.forecast(3, exog=nxt.values)
    else:
        m = SARIMAX(hist.values, order=(2, 1, 0), trend="n").fit(disp=False)
        fc = m.forecast(3)
    return {h: fc[h - 1] - hist.iloc[-1] for h in H}


def rolling(d, feats, u, refit_month=1, window=None, models=("AR", "SARIMAX", "ElasticNet", "LightGBM"), label="base"):
    Y = targets(u)
    rows, cache = [], {}
    last_T = u.dropna().index.max()
    origins = [t for t in u.index if t >= EVAL_START - pd.offsets.MonthBegin(1) and t <= last_T - pd.offsets.MonthBegin(1)]
    for T in origins:
        rec = {"origin": T, "u_T": u.loc[T]}
        for h in H:
            tgt = T + pd.DateOffset(months=h)
            rec[f"actual_{h}"] = u.loc[tgt] if tgt in u.index else np.nan
        if "AR" in models:
            a = arima_forecast(u, False, T, d)
            for h in H: rec[f"AR_{h}"] = a[h]
        if "SARIMAX" in models:
            a = arima_forecast(u, True, T, d)
            for h in H: rec[f"SARIMAX_{h}"] = a[h]
        for kind in [m for m in models if m in ("ElasticNet", "LightGBM")]:
            for h in H:
                key = (kind, h)
                if key not in cache or T.month == refit_month:
                    # 学習に使えるのは、目的変数（T'+h）が T までに分かっている行だけ
                    lo = TRAIN_START if window is None else T - pd.DateOffset(years=window)
                    idx = feats.index[(feats.index >= lo) & (feats.index <= T - pd.DateOffset(months=h))]
                    tr = pd.concat([feats.loc[idx], Y[h].loc[idx].rename("y")], axis=1).dropna()
                    cache[key] = fit_ml(kind, tr.drop(columns="y"), tr["y"])
                x = feats.loc[[T]]
                rec[f"{kind}_{h}"] = float(cache[key].predict(x)[0]) if x.notna().all(axis=None) else np.nan
        rows.append(rec)
    out = pd.DataFrame(rows).set_index("origin")
    for h in H:
        out[f"naive_{h}"] = 0.0
        out[f"actual_chg_{h}"] = out[f"actual_{h}"] - out["u_T"]
        ms = [m for m in ("SARIMAX", "ElasticNet", "LightGBM") if f"{m}_{h}" in out]
        if len(ms) == 3:
            out[f"ENS_{h}"] = out[[f"{m}_{h}" for m in ms]].mean(axis=1)
    out["label"] = label
    return out


NAMES = {"naive": "前月の値（ナイーブ）", "AR": "AR（失業率だけ）", "SARIMAX": "SARIMAX",
         "ElasticNet": "ElasticNet", "LightGBM": "LightGBM", "ENS": "平均（3モデル）"}


def cls(x):
    return np.where(x >= 0.05, 1, np.where(x <= -0.05, -1, 0))


def dm_test(e1, e2, h):
    """Diebold–Mariano（絶対誤差、HAC、Harvey らの小標本補正）。e1 が e2 より良ければ統計量は負"""
    dlt = np.abs(e1) - np.abs(e2)
    dlt = dlt[~np.isnan(dlt)]
    n = len(dlt)
    g = [np.mean((dlt[k:] - dlt.mean()) * (dlt[:n - k] - dlt.mean())) for k in range(h)]
    v = (g[0] + 2 * sum(g[1:])) / n
    stat = dlt.mean() / np.sqrt(v)
    stat *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    p = 2 * stats.t.sf(abs(stat), n - 1)
    return stat, p


def metrics(fc, mask=None, models=NAMES):
    rows = []
    for h in H:
        sub = fc if mask is None else fc[mask]
        sub = sub.dropna(subset=[f"actual_chg_{h}"])
        act = sub[f"actual_chg_{h}"].values
        for m in models:
            col = f"{m}_{h}"
            if col not in sub:
                continue
            e = sub[col].values - act
            ok = ~np.isnan(e)
            dm, p = dm_test(e, sub[f"naive_{h}"].values - act, h) if m != "naive" else (np.nan, np.nan)
            rows.append({"h": h, "model": NAMES[m], "n": int(ok.sum()), "MAE": np.mean(np.abs(e[ok])),
                         "RMSE": np.sqrt(np.mean(e[ok] ** 2)),
                         "方向一致率": np.mean(cls(sub[col].values[ok]) == cls(act[ok])),
                         "MAE_ナイーブ比": np.mean(np.abs(e[ok])) / np.mean(np.abs(act[ok])),
                         "DM統計量": dm, "DM_p値": p})
    return pd.DataFrame(rows)


def period_of(t):
    if t < pd.Timestamp("2010-01-01"): return "2005〜09年"
    if t < pd.Timestamp("2020-03-01"): return "2010〜20年2月"
    if t <= pd.Timestamp("2021-12-01"): return "コロナ期（20年3月〜21年）"
    return "2022年〜"


if __name__ == "__main__":
    RES.mkdir(exist_ok=True)
    feats = make_features(df)
    u = df["u_sa"]
    fc = rolling(df, feats, u)
    fc.to_csv(RES / "forecasts.csv", float_format="%.4f")

    # 全期間・コロナ期を除く
    tab = []
    for lab, mask in (("全期間（2005/1〜2026/8）", None),):
        tab.append(metrics(fc).assign(期間=lab))
    for h in H:
        tgt = fc.index + pd.DateOffset(months=h)
        m = ~((tgt >= COVID[0]) & (tgt <= COVID[1]))
        tab.append(metrics(fc[m]).query("h==@h").assign(期間="コロナ期を除く"))
    # 期間別（予測の対象月で分ける）
    for h in H:
        tgt = pd.Series(fc.index + pd.DateOffset(months=h), index=fc.index)
        per = tgt.map(period_of)
        for p in per.unique():
            tab.append(metrics(fc[per == p]).query("h==@h").assign(期間=p))
    met = pd.concat(tab, ignore_index=True)
    met.to_csv(RES / "metrics.csv", index=False, float_format="%.4f")
    print(met[met["期間"].str.startswith("全期間")].round(3).to_string())
    print(met[met["期間"] == "コロナ期を除く"].round(3).to_string())

    # 最終モデル（直近まで学習）での重要度
    imp = {}
    for h in H:
        Y = targets(u)[h]
        tr = pd.concat([feats, Y.rename("y")], axis=1).loc[TRAIN_START:].dropna()
        g = fit_ml("LightGBM", tr.drop(columns="y"), tr["y"])
        import shap
        sv = shap.TreeExplainer(g).shap_values(tr.drop(columns="y"))
        imp[f"LightGBM_SHAP_{h}"] = pd.Series(np.abs(sv).mean(0), index=tr.columns[:-1])
        e = fit_ml("ElasticNet", tr.drop(columns="y"), tr["y"])
        imp[f"ElasticNet_coef_{h}"] = pd.Series(e[-1].coef_, index=tr.columns[:-1])
    pd.DataFrame(imp).to_csv(RES / "importance.csv", float_format="%.5f")
    print(pd.DataFrame(imp).round(4).sort_values("LightGBM_SHAP_1", ascending=False).head(10))
