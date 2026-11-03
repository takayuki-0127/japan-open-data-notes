"""動的調和回帰（状態空間・時変の季節成分）の共通関数"""
import numpy as np, pandas as pd, warnings
from statsmodels.tsa.statespace.structural import UnobservedComponents
from common import DATA

warnings.filterwarnings("ignore")
COVID = (pd.Timestamp("2020-02-01"), pd.Timestamp("2022-12-01"))


def load(name, start=None, end=None, col=None):
    df = pd.read_csv(DATA / "monthly_series.csv", parse_dates=["date"]).set_index("date")
    col = col or {"power": "power_gw", "inbound": "inbound", "births": "births_per_day"}[name]
    s = df[col.replace("_raw", "")].dropna()
    exog = df.loc[s.index, ["cdd", "hdd"]] if name == "power" else None
    s = s.asfreq("MS")
    if name == "inbound" and not (col or "").endswith("_raw"):
        s = s / s.index.days_in_month  # 1日あたりにそろえる（2月の日数の少なさを消す）
    if start: s = s[start:]
    if end: s = s[:end]
    y = np.log(s)
    if name == "inbound" or (col or "").startswith("inb"):
        y[(y.index >= COVID[0]) & (y.index <= COVID[1])] = np.nan
    if exog is not None:
        exog = exog.reindex(y.index) / 100
    return y, exog


def fit(y, stochastic=True, harmonics=6, exog=None, trend="local linear trend"):
    m = UnobservedComponents(y, level=trend, freq_seasonal=[{"period": 12, "harmonics": harmonics}],
                             stochastic_freq_seasonal=[stochastic], irregular=True, exog=exog)
    best = None
    for k in range(3):
        try:
            r = m.fit(disp=False, method="lbfgs", maxiter=500,
                      start_params=None if k == 0 else m.start_params * (0.3 ** k))
        except Exception:
            continue
        if best is None or r.llf > best.llf:
            best = r
    return best


def seasonal(res):
    """平滑化した季節成分（対数）"""
    s = res.freq_seasonal[0]["smoothed"]
    return pd.Series(s, index=res.model.data.row_labels)


def profile(s, years):
    """指定した年の各月の季節成分の平均（%）"""
    x = s[(s.index.year >= years[0]) & (s.index.year <= years[1])]
    p = x.groupby(x.index.month).mean()
    p = p - p.mean()
    return 100 * (np.exp(p) - 1)


def yearly(s):
    out = []
    for yv, x in s.groupby(s.index.year):
        if len(x) < 12: continue
        x = x - x.mean()
        out.append(dict(year=yv, amplitude=100 * (np.exp(x.max()) - np.exp(x.min())),
                        peak=int(x.idxmax().month), trough=int(x.idxmin().month)))
    return pd.DataFrame(out)


def sigma_share(res):
    p = dict(zip(res.model.param_names, res.params))
    return {k: v for k, v in p.items() if k.startswith("sigma2")}


def rolling_ols_profile(y, win=5, harmonics=6):
    """比較用：5年の窓ごとに、トレンド（3次）＋固定のフーリエ項を最小二乗で当てた季節の形"""
    rows = []
    years = sorted(set(y.dropna().index.year))
    for y0 in years:
        yy = y[(y.index.year >= y0) & (y.index.year < y0 + win)].dropna()
        if len(yy) < 12 * win - 2 or yy.index.year.nunique() < win: continue
        t = np.arange(len(y[(y.index.year >= y0) & (y.index.year < y0 + win)]))
        tt = pd.Series(t, index=y[(y.index.year >= y0) & (y.index.year < y0 + win)].index).loc[yy.index].values / 12
        X = [np.ones_like(tt), tt, tt ** 2, tt ** 3]
        mth = yy.index.month.values
        for k in range(1, harmonics + 1):
            X += [np.cos(2 * np.pi * k * mth / 12), np.sin(2 * np.pi * k * mth / 12)]
        X = np.column_stack(X)
        if harmonics == 6: X = X[:, :-1]  # sin(π m) は0
        beta = np.linalg.lstsq(X, yy.values, rcond=None)[0]
        mm = np.arange(1, 13)
        S = np.zeros(12)
        for k in range(1, harmonics + 1):
            i = 4 + 2 * (k - 1)
            S += beta[i] * np.cos(2 * np.pi * k * mm / 12)
            if i + 1 < len(beta): S += beta[i + 1] * np.sin(2 * np.pi * k * mm / 12)
        S = S - S.mean()
        rows.append(dict(start=y0, end=y0 + win - 1, amplitude=100 * (np.exp(S.max()) - np.exp(S.min())),
                         peak=int(S.argmax() + 1), trough=int(S.argmin() + 1),
                         **{f"m{m:02d}": 100 * (np.exp(S[m - 1]) - 1) for m in mm}))
    return pd.DataFrame(rows)
