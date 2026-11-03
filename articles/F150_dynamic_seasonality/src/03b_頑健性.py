"""頑健性チェック
1. 季節の波の数（調和項 2・3・4・6）
2. 期間（出生 2010年〜、訪日 2019年まで、電力 2017年〜）
3. 系列の形（出生・訪日を1日あたりでなく月の合計で）
4. 電力：気温（冷房度日・暖房度日）を説明変数に入れる
5. 別の手法：5年の窓ごとの固定フーリエ回帰（最小二乗）
6. 訪日：国・地域の構成の変化と、各国・地域の季節の形の変化に分ける
"""
import numpy as np, pandas as pd
from scipy import stats
from ds import load, fit, seasonal, profile, rolling_ols_profile
from common import RES, DATA

WIN = {"births": [(2000, 2004), (2021, 2025)], "inbound": [(2005, 2009), (2024, 2025)], "power": [(2017, 2019), (2023, 2025)]}


def run(name, label, harmonics=6, start=None, end=None, col=None, use_exog=False, win=None):
    y, ex = load(name, start, end, col)
    r0 = fit(y, False, harmonics, ex if use_exog else None); r1 = fit(y, True, harmonics, ex if use_exog else None)
    lr = 2 * (r1.llf - r0.llf); s = seasonal(r1)
    w = win or WIN[name]
    a = [profile(s, ww) for ww in w]
    amp = [p.max() - p.min() for p in a]
    row = dict(series=name, check=label, lr=round(lr, 2), p=0.5 * stats.chi2.sf(max(lr, 0), 1),
               aic_diff=round(r1.aic - r0.aic, 2), amp_early=round(amp[0], 1), amp_late=round(amp[-1], 1),
               peak_early=int(a[0].idxmax()), peak_late=int(a[-1].idxmax()),
               early_window=f"{w[0][0]}-{w[0][1]}", late_window=f"{w[-1][0]}-{w[-1][1]}")
    for m in (1, 3, 7, 8):
        row[f"m{m:02d}_early"] = round(a[0][m], 1); row[f"m{m:02d}_late"] = round(a[-1][m], 1)
    print(row)
    return row, s

rows = []
for name in ["births", "inbound", "power"]:
    for h in (2, 3, 4, 6):
        rows.append(run(name, f"調和項{h}", harmonics=h)[0])
rows.append(run("births", "期間2010年〜", start="2010-01-01", win=[(2010, 2014), (2021, 2025)])[0])
rows.append(run("inbound", "期間2019年まで", end="2019-12-01", win=[(2005, 2009), (2015, 2019)])[0])
rows.append(run("power", "期間2017年〜", start="2017-01-01")[0])
rows.append(run("births", "月の合計", col="births")[0])
rows.append(run("inbound", "月の合計", col="inbound_raw")[0])
r, s_ex = run("power", "気温を入れる", use_exog=True); rows.append(r)
pd.DataFrame(rows).to_csv(RES / "robustness_models.csv", index=False)

# 電力：気温で説明した分を除いた季節（気温の効果の大きさも保存）
y, ex = load("power")
rex = fit(y, True, 6, ex)
coef = dict(zip(rex.model.param_names, rex.params))
pd.DataFrame([coef]).to_csv(RES / "power_temp_model_params.csv", index=False)
s_ex.to_frame("seasonal_tv_with_temp").to_csv(RES / "power_seasonal_with_temp.csv")
df = pd.read_csv(DATA / "monthly_series.csv", parse_dates=["date"]).dropna(subset=["power_gw"])
tt = df.assign(y=df.date.dt.year, m=df.date.dt.month)
tt = tt[tt.y.between(2017, 2025)].groupby(["y"]).apply(lambda g: pd.Series(dict(
    temp_jul_aug=g[g.m.isin([7, 8])].temp.mean(), cdd=g.cdd.sum(), hdd=g.hdd.sum(), temp_jan_feb=g[g.m.isin([1, 2])].temp.mean())))
tt.round(1).to_csv(RES / "power_temperature_by_year.csv"); print(tt.round(1))

# 5. 5年窓の固定フーリエ回帰
ols = []
for name in ["births", "inbound", "power"]:
    y, _ = load(name)
    win = 3 if name == "power" else 5
    o = rolling_ols_profile(y, win=win); o["series"] = name; o["window_years"] = win; ols.append(o)
ols = pd.concat(ols); ols.to_csv(RES / "rolling_ols_profiles.csv", index=False)
print(ols[["series", "start", "end", "amplitude", "peak", "trough"]].round(1).to_string())

# 6. 訪日：構成の変化と、各国・地域の形の変化
d = pd.read_csv(DATA / "monthly_series.csv", parse_dates=["date"]).set_index("date")
mk = ["inb_kr", "inb_cn", "inb_tw", "inb_hk", "inb_us", "inb_th", "inb_au"]
d = d[mk + ["inbound"]].dropna()
d["inb_rest"] = d.inbound - d[mk].sum(axis=1)
parts = mk + ["inb_rest"]
pd_ = d[parts].div(d.index.days_in_month, axis=0)


def prof_w(years):
    x = pd_[(pd_.index.year >= years[0]) & (pd_.index.year <= years[1])]
    # 国・地域ごとに、log(1日あたりの人数) = 定数 + 直線のトレンド + 月の効果 を当て、月の効果を季節の形とする
    t = np.arange(len(x)) / 12
    D = pd.get_dummies(x.index.month).astype(float).values
    X = np.column_stack([t, D])
    shape = {}
    for c in x.columns:
        beta = np.linalg.lstsq(X, np.log(x[c].values), rcond=None)[0]
        e = beta[1:]; shape[c] = np.exp(e - e.mean())
    shape = pd.DataFrame(shape, index=range(1, 13))
    shape = shape / shape.mean()
    tot = x.groupby(x.index.year).mean()
    w = (tot.div(tot.sum(axis=1), axis=0)).mean()    # 年間の構成比（各年の平均）
    return w, shape


def total_prof(w, shape):
    t = (shape * w).sum(axis=1)
    return 100 * (t / t.mean() - 1)

we, se = prof_w((2005, 2009)); wl, sl = prof_w((2024, 2025))
dec = pd.DataFrame({"early": total_prof(we, se), "late": total_prof(wl, sl),
                    "late_shape_early_mix": total_prof(we, sl), "early_shape_late_mix": total_prof(wl, se)})
dec.round(2).to_csv(RES / "inbound_mix_decomposition.csv")
sl_ = pd.concat({"2005_2009": se, "2024_2025": sl}, axis=1); (100 * (sl_ - 1)).round(1).to_csv(RES / "inbound_market_shapes.csv")
amp = dec.max() - dec.min(); print(dec.round(1)); print(amp.round(1))
pd.DataFrame({"share_2005_2009": we, "share_2024_2025": wl}).round(3).to_csv(RES / "inbound_market_shares.csv")
amp.round(2).to_frame("amplitude").to_csv(RES / "inbound_mix_amplitude.csv")
