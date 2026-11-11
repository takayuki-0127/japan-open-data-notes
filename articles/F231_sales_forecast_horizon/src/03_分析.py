# F231 売上の予測は、何か月先まで役に立つのか？
# 業態別の月次販売額（商業動態統計、6業態、2014-01〜2026-08）で、
# 予測の起点を1か月ずつずらしながら（ローリング・オリジン）1〜24か月先を予測し、
# 先の長さ（予測の地平）ごとに外れを比べる。
import warnings, json, sys
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
import lightgbm as lgb

np.random.seed(231)
H = 24
COVID = (pd.Period("2020-03", "M"), pd.Period("2021-12", "M"))  # 採点から外す期間（主の評価）

d = pd.read_csv("data/sales_monthly_6types.csv")
d["ym"] = pd.PeriodIndex(d.ym, freq="M")
S = {k: g.set_index("ym")["販売額_百万円"].sort_index() for k, g in d.groupby("業態")}
TYPES = ["百貨店", "スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "家電大型専門店"]


def impute_covid(y):
    """2020-03〜2021-12 を、2019年の同じ月×（2022年同月/2019年同月）の幾何平均でならした値に置き換える（頑健性用）"""
    y = y.copy()
    for p in y.index:
        if COVID[0] <= p <= COVID[1]:
            a = y.get(pd.Period(year=2019, month=p.month, freq="M"))
            b = y.get(pd.Period(year=2022, month=p.month, freq="M"))
            frac = (p.year - 2019 + (p.month - 1) / 12) / 3
            y[p] = a * (b / a) ** frac
    return y


def f_snaive(y, h):
    last = y.iloc[-12:].values
    return np.array([last[i % 12] for i in range(h)])


def f_snaive_drift(y, h):
    g = y.iloc[-12:].sum() / y.iloc[-24:-12].sum()  # 直近12か月の前年比
    base = f_snaive(y, h)
    k = np.array([1 + i // 12 for i in range(h)])
    return base * g ** k


def f_ets(y, h, ret_int=False):
    m = ExponentialSmoothing(np.log(y.values), trend="add", damped_trend=True,
                             seasonal="add", seasonal_periods=12,
                             initialization_method="estimated").fit()
    return np.exp(m.forecast(h))


def f_sarima(y, h, ret_int=False):
    m = SARIMAX(np.log(y.values), order=(0, 1, 1), seasonal_order=(0, 1, 1, 12),
                enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=60)
    fc = m.get_forecast(h)
    mu = np.exp(fc.predicted_mean)
    if ret_int:
        ci = np.exp(fc.conf_int(alpha=0.2))
        return mu, ci[:, 0], ci[:, 1]
    return mu


def lgb_feats(logy, idx):
    # idx: 予測したい位置。ラグ1〜13と月
    X = [logy[idx - L] for L in (1, 2, 3, 12, 13)] + [idx % 12]
    return X


def f_lgb_global(train_dict, h):
    """6業態をまとめて1つのモデルで学習（前年同月比の対数を目的変数に）、再帰で h か月先まで"""
    Xs, ys = [], []
    for k, y in train_dict.items():
        ly = np.log(y.values)
        for t in range(13, len(ly)):
            Xs.append([ly[t - 1] - ly[t - 13], ly[t - 2] - ly[t - 14] if t >= 14 else 0,
                       ly[t - 12] - ly[t - 24] if t >= 24 else 0, (y.index[t].month), TYPES.index(k)])
            ys.append(ly[t] - ly[t - 12])
    mdl = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.05, num_leaves=15,
                            min_child_samples=10, verbose=-1, random_state=231)
    mdl.fit(np.array(Xs), np.array(ys))
    out = {}
    for k, y in train_dict.items():
        ly = list(np.log(y.values))
        last = y.index[-1]
        for i in range(h):
            t = len(ly)
            x = [ly[t - 1] - ly[t - 13], ly[t - 2] - ly[t - 14], ly[t - 12] - ly[t - 24],
                 (last + i + 1).month, TYPES.index(k)]
            ly.append(ly[t - 12] + mdl.predict(np.array([x]))[0])
        out[k] = np.exp(np.array(ly[-h:]))
    return out


def run(series, origins, tag, with_lgb=True, with_int=True):
    recs = []
    for o in origins:
        train = {k: s[s.index <= o] for k, s in series.items()}
        lg = f_lgb_global(train, H) if with_lgb else None
        for k in TYPES:
            y = train[k]
            fut = S[k][(S[k].index > o)].iloc[:H]  # 実績は常に元の系列
            if len(fut) < H:
                continue
            fc = {"季節ナイーブ": f_snaive(y, H), "季節ナイーブ＋伸び": f_snaive_drift(y, H),
                  "ETS": f_ets(y, H)}
            if with_int:
                mu, lo, hi = f_sarima(y, H, True)
            else:
                mu = f_sarima(y, H); lo = hi = np.full(H, np.nan)
            fc["SARIMA"] = mu
            if with_lgb:
                fc["LightGBM"] = lg[k]
            for m, v in fc.items():
                for i in range(H):
                    recs.append((tag, k, str(o), str(fut.index[i]), i + 1, m, fut.values[i], v[i],
                                 lo[i] if m == "SARIMA" else np.nan, hi[i] if m == "SARIMA" else np.nan))
        print(tag, o, file=sys.stderr, flush=True)
    return pd.DataFrame(recs, columns=["実験", "業態", "起点", "対象月", "h", "モデル", "実績", "予測", "下80", "上80"])


origins = list(pd.period_range("2016-12", "2024-08", freq="M"))[::2]  # 2か月ごとの起点（計算量を抑える）
main = run(S, origins, "主")
main.to_csv("results/forecasts_main.csv.gz", index=False, compression="gzip")

# 頑健性：コロナ期をならした系列で学習（起点は3か月ごと、LightGBM と区間は省く）
Simp = {k: impute_covid(v) for k, v in S.items()}
rob = run(Simp, origins[::2], "コロナ期をならして学習", with_lgb=False, with_int=False)
rob.to_csv("results/forecasts_covid_imputed.csv.gz", index=False, compression="gzip")
print("done", len(main), len(rob))
