"""T1：完全失業率の季節調整（STL）と SARIMA による予測（労働力調査 月次・原数値）"""
from common import *
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.statespace.sarimax import SARIMAX
import itertools, time

raw, sa = load()
y = raw.loc["2000-01":, "rate_calc"]; y.index = y.index.to_timestamp()
off = sa.loc["2000-01":, "rate_calc"]; off.index = off.index.to_timestamp()

# 1) STL で季節調整して、公表の季節調整値（X-12-ARIMA）と比べる
stl = STL(y, period=12, robust=True).fit()
my_sa = y - stl.seasonal
cmp = pd.DataFrame({"original": y, "official_sa": off, "stl_sa": my_sa}).dropna()
season = pd.Series(stl.seasonal.loc["2021-09":].values, index=stl.seasonal.loc["2021-09":].index.month).groupby(level=0).mean()
season.round(3).to_csv(RES / "t1_seasonal_by_month.csv", header=["seasonal_pt"])

# 2) SARIMA の次数を 2000〜2014年のデータの AIC で決める（後の評価に使う期間は見ない）
train0 = y.loc[:"2014-12"]
best = None
for p, q, P, Q in itertools.product([0, 1, 2], [0, 1, 2], [0, 1], [0, 1]):
    try:
        r = SARIMAX(train0, order=(p, 1, q), seasonal_order=(P, 1, Q, 12)).fit(disp=False)
        if best is None or r.aic < best[0]: best = (r.aic, (p, 1, q), (P, 1, Q, 12))
    except Exception:
        pass
ORDER, SORDER = best[1], best[2]; print("order", ORDER, SORDER, round(best[0], 1))

# 3) ローリング評価：2015年1月〜2025年8月の各月を起点に、1〜12か月先を予測（毎回その時点までのデータで学習し直す）
rows = []
t0 = time.time()
for origin in pd.date_range("2015-01-01", "2025-08-01", freq="MS"):
    tr = y.loc[:origin]
    fc = SARIMAX(tr, order=ORDER, seasonal_order=SORDER).fit(disp=False).get_forecast(12).predicted_mean
    for h, (t, v) in enumerate(fc.items(), start=1):
        if t not in y.index: continue
        snaive = y.loc[t - pd.DateOffset(years=1)] + (y.loc[origin] - y.loc[origin - pd.DateOffset(years=1)])   # 季節ナイーブ＋直近の前年差
        rows.append({"origin": origin, "h": h, "target": t, "actual": y.loc[t], "sarima": v, "naive_last": y.loc[origin],
                     "snaive_drift": snaive})
ev = pd.DataFrame(rows); ev.to_csv(RES / "t1_rolling_forecasts.csv", index=False)
print("rolling fits sec", round(time.time() - t0, 1))
ev["covid"] = ev.target.between("2020-03-01", "2021-12-01") | ev.origin.between("2020-01-01", "2021-12-01")
def mae(df):
    return pd.Series({m: (df[m] - df.actual).abs().mean() for m in ["sarima", "naive_last", "snaive_drift"]})
by_h = ev[~ev.covid].groupby("h").apply(mae); by_h.round(4).to_csv(RES / "t1_mae_by_h.csv")
by_h_all = ev.groupby("h").apply(mae)
print(by_h.round(3))

# 4) 2019年12月を起点にした予測（コロナ前）と、最新の起点からの1年先予測
r19 = SARIMAX(y.loc[:"2019-12"], order=ORDER, seasonal_order=SORDER).fit(disp=False).get_forecast(24)
f19 = pd.DataFrame({"mean": r19.predicted_mean, "lo": r19.conf_int(alpha=.2).iloc[:, 0], "hi": r19.conf_int(alpha=.2).iloc[:, 1]})
rl = SARIMAX(y, order=ORDER, seasonal_order=SORDER).fit(disp=False); fl = rl.get_forecast(12)
fnext = pd.DataFrame({"mean": fl.predicted_mean, "lo80": fl.conf_int(alpha=.2).iloc[:, 0], "hi80": fl.conf_int(alpha=.2).iloc[:, 1],
                      "lo95": fl.conf_int(alpha=.05).iloc[:, 0], "hi95": fl.conf_int(alpha=.05).iloc[:, 1]})
fnext.round(3).to_csv(RES / "t1_forecast_next12.csv")
cover = ev[~ev.covid]
s = {"n_months": len(y), "start": str(y.index[0].date()), "end": str(y.index[-1].date()), "order": str(ORDER), "seasonal_order": str(SORDER),
     "stl_vs_official_mae_pt": (cmp.stl_sa - cmp.official_sa).abs().mean(), "stl_vs_official_corr": cmp[["stl_sa", "official_sa"]].corr().iloc[0, 1],
     "orig_vs_official_mae_pt": (cmp.original - cmp.official_sa).abs().mean(),
     "mae_h1_sarima": by_h.loc[1, "sarima"], "mae_h1_naive": by_h.loc[1, "naive_last"], "mae_h1_snaive": by_h.loc[1, "snaive_drift"],
     "mae_h12_sarima": by_h.loc[12, "sarima"], "mae_h12_naive": by_h.loc[12, "naive_last"], "mae_h12_snaive": by_h.loc[12, "snaive_drift"],
     "n_origins": ev.origin.nunique(), "f19_2020_05_mean": f19.loc["2020-05-01", "mean"], "actual_2020_05": y.loc["2020-05-01"],
     "actual_2020_10": y.loc["2020-10-01"], "f19_2020_10_mean": f19.loc["2020-10-01", "mean"],
     "next12_mean_avg": fnext["mean"].mean(), "last_actual": y.iloc[-1], "season_max_month": int(season.idxmax()), "season_min_month": int(season.idxmin()),
     "season_range_pt": season.max() - season.min()}
pd.Series(s).to_csv(RES / "t1_summary.csv", header=["value"]); print(pd.Series(s))

# 図1：原数値と季節調整値
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(cmp.index, cmp.original, color=GRAY, lw=0.9, label="原数値（季節の動きを含む）")
ax.plot(cmp.index, cmp.official_sa, color=BLUE, lw=1.6, label="公表の季節調整値（X-12-ARIMA）")
ax.plot(cmp.index, cmp.stl_sa, color=ORANGE, lw=1, ls="--", label="自分で STL にかけた値")
ax.set_ylabel("完全失業率（%）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title(f"STL で自分で季節調整しても、公表値とほぼ同じ（平均の差 {s['stl_vs_official_mae_pt']:.2f}ポイント）", loc="left")
fig.text(0.01, -0.03, SOURCE + "（完全失業者 ÷ 労働力人口で計算し直した値）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "t1_sa.png"); plt.close(fig)

# 図2：月ごとの季節の動き
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.bar(season.index, season.values, color=[ORANGE if v > 0 else BLUE for v in season.values])
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(range(1, 13), [f"{m}月" for m in range(1, 13)]); ax.set_ylabel("季節の動き（ポイント）")
ax.set_title("失業率は春に高く、年末に低い（直近5年の STL の季節成分の平均）", loc="left")
fig.text(0.01, -0.06, SOURCE, fontsize=8, color="#8a8984"); fig.savefig(FIG / "t1_season.png"); plt.close(fig)

# 図3：何か月先まで当たるか
fig, ax = plt.subplots(figsize=(8, 3.8))
for m, lab, c in [("sarima", f"SARIMA{ORDER}{SORDER[:3]}", BLUE), ("snaive_drift", "前年同月＋直近の前年差", ORANGE), ("naive_last", "最新の値のまま", GRAY)]:
    ax.plot(by_h.index, by_h[m], marker="o", ms=4, color=c, label=lab)
ax.set_xticks(range(1, 13)); ax.set_xlabel("何か月先の予測か"); ax.set_ylabel("平均絶対誤差（ポイント）"); ax.set_ylim(0, None)
ax.legend(frameon=False, fontsize=9); ax.set_title("1〜12か月先のどこでも、SARIMA が単純な予測より誤差が小さかった", loc="left")
fig.text(0.01, -0.05, SOURCE + f"（2015年1月〜2025年8月の{s['n_origins']}か月を起点にしたローリング評価。コロナ期を除く）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "t1_mae_h.png"); plt.close(fig)

# 図4：コロナ前に作った予測と、実際
fig, ax = plt.subplots(figsize=(8, 3.8))
win = y.loc["2018-01":"2021-12"]
ax.plot(win.index, win.values, color=INK, lw=1.4, label="実際（原数値）")
ax.plot(f19.index, f19["mean"], color=BLUE, lw=1.4, label="2019年12月までのデータで作った予測")
ax.fill_between(f19.index, f19.lo, f19.hi, color=LIGHT, alpha=0.6, label="80%予測区間")
ax.set_ylabel("完全失業率（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("過去のパターンから外れる出来事は、予測できない", loc="left")
fig.text(0.01, -0.04, SOURCE, fontsize=8, color="#8a8984"); fig.savefig(FIG / "t1_covid.png"); plt.close(fig)
