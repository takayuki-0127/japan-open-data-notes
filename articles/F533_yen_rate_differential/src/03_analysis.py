"""月ごとの変化の回帰、期間別、移動相関、2021年以降の円安の分解、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
m = pd.read_csv(ROOT / "data" / "monthly.csv", index_col=0)
m["lfx"] = 100 * np.log(m.usdjpy_avg)
m["lfx_end"] = 100 * np.log(m.usdjpy_end)
d = m.diff().iloc[1:]   # 月ごとの変化（1990年2月〜）
LAGS = 6


def ols(y, x, lags=LAGS):
    ok = y.notna() & x.notna()
    X = sm.add_constant(x[ok].values)
    f = sm.OLS(y[ok].values, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"n": int(ok.sum()), "beta": float(f.params[1]), "se": float(f.bse[1]), "t": float(f.tvalues[1]),
            "r2": float(f.rsquared), "const": float(f.params[0]), "corr": float(np.corrcoef(y[ok], x[ok])[0, 1])}


def sub(df, a, b):
    return df[(df.index >= a) & (df.index <= b)]


PERIODS = [("1990〜1999", "1990-02", "1999-12"), ("2000〜2007", "2000-01", "2007-12"), ("2008〜2012", "2008-01", "2012-12"),
           ("2013〜2020", "2013-01", "2020-12"), ("2021〜2026", "2021-01", "2026-10"),
           ("1990〜2007", "1990-02", "2007-12"), ("2013〜2026", "2013-01", "2026-10"), ("全期間", "1990-02", "2026-10")]
rows = []
for name, a, b in PERIODS:
    s = sub(d, a, b)
    for sp in ["spread2", "spread10"]:
        r = ols(s.lfx, s[sp]); r.update({"period": name, "spread": sp}); rows.append(r)
per = pd.DataFrame(rows)[["period", "spread", "n", "beta", "se", "t", "r2", "corr", "const"]]
per.to_csv(R / "regression_by_period.csv", index=False, float_format="%.5f", lineterminator="\n")
g = lambda p, sp="spread2": per[(per.period == p) & (per.spread == sp)].iloc[0]

# 36か月の移動相関（変化どうし）
roll = pd.DataFrame({"corr36_spread2": d.lfx.rolling(36).corr(d.spread2), "corr36_spread10": d.lfx.rolling(36).corr(d.spread10)})
roll.to_csv(R / "rolling_corr36.csv", float_format="%.5f", lineterminator="\n")
neg = roll.corr36_spread2 < 0
# 負の区間（連続）をまとめる
spells, start = [], None
for ym, v in neg.items():
    if v and start is None: start = ym
    if not v and start is not None: spells.append((start, prev)); start = None
    prev = ym
if start is not None: spells.append((start, prev))

# 水準の相関（参考）
lev = {name: float(np.corrcoef(sub(m, a, b).lfx, sub(m, a, b).spread2)[0, 1]) for name, a, b in PERIODS}

# H4：2021年1月から2021年以降の最高の月まで
post = sub(m, "2021-01", "2026-10")
peak = post.usdjpy_avg.idxmax()
pre = ols(sub(d, "1990-02", "2020-12").lfx, sub(d, "1990-02", "2020-12").spread2)
pre00 = ols(sub(d, "2000-01", "2020-12").lfx, sub(d, "2000-01", "2020-12").spread2)
def episode(a, b, beta, col="lfx", sp="spread2"):
    act = m.loc[b, col] - m.loc[a, col]; dsp = m.loc[b, sp] - m.loc[a, sp]
    return {"from": a, "to": b, "fx_from": float(m.loc[a, "usdjpy_avg"]), "fx_to": float(m.loc[b, "usdjpy_avg"]),
            "actual_logpct": float(act), "spread_from": float(m.loc[a, sp]), "spread_to": float(m.loc[b, sp]),
            "d_spread": float(dsp), "fitted_logpct": float(beta * dsp), "share": float(beta * dsp / act) if act != 0 else None}
ep_main = episode("2021-01", peak, pre["beta"])
ep_after = episode(peak, "2026-10", pre["beta"])
ep_full = episode("2021-01", "2026-10", pre["beta"])

main = {
    "months": int(len(d)), "first": d.index[0], "last": d.index[-1],
    "full_2y": g("全期間").to_dict(), "full_10y": g("全期間", "spread10").to_dict(),
    "r2_1990_2007": float(g("1990〜2007").r2), "r2_2013_2026": float(g("2013〜2026").r2),
    "by_period_r2_2y": {p: float(g(p).r2) for p, _, _ in PERIODS},
    "by_period_beta_2y": {p: float(g(p).beta) for p, _, _ in PERIODS},
    "by_period_r2_10y": {p: float(g(p, "spread10").r2) for p, _, _ in PERIODS},
    "level_corr_2y": lev,
    "neg_corr36_spells": [list(s) for s in spells],
    "neg_corr36_months": int(neg.sum()), "corr36_months": int(roll.corr36_spread2.notna().sum()),
    "beta_pre2021": pre, "beta_2000_2020": pre00,
    "peak_month": peak, "episode_2021_peak": ep_main, "episode_peak_2026_10": ep_after, "episode_2021_2026_10": ep_full,
    "fx_1990_01": float(m.loc["1990-01", "usdjpy_avg"]), "fx_2020_12": float(m.loc["2020-12", "usdjpy_avg"]),
    "fx_2026_10": float(m.loc["2026-10", "usdjpy_avg"]),
    "spread2_2020_12": float(m.loc["2020-12", "spread2"]), "spread2_2026_10": float(m.loc["2026-10", "spread2"]),
}
fa = main["full_2y"]
main["H1"] = "支持" if (0.05 <= fa["r2"] < 0.3 and fa["beta"] > 0) else "外れ"
main["H2"] = "支持" if main["r2_2013_2026"] > main["r2_1990_2007"] else "外れ"
main["H3"] = "支持" if fa["r2"] > main["full_10y"]["r2"] else "外れ"
main["H4"] = "支持" if ep_main["share"] >= 0.5 else "外れ"

# 頑健性
rob = []
def add(name, r, extra=None):
    rob.append({"check": name, "n": r["n"], "beta": r["beta"], "se": r["se"], "r2": r["r2"], **(extra or {})})
add("本線：月中平均・2年・全期間", fa)
add("月末のドル円（1992年8月〜）", ols(d.lfx_end, d.spread2))
add("10年の金利差", main["full_10y"])
crisis = (d.index >= "2008-09") & (d.index <= "2009-03")
add("2008年9月〜2009年3月を除く", ols(d.lfx[~crisis], d.spread2[~crisis]))
q = m.iloc[::3].diff().iloc[1:]   # 3か月ごと（1990年1・4・7・10月の値の差）
add("3か月ごとの変化", ols(q.lfx, q.spread2, lags=2))
add("2013〜2026年・月末のドル円", ols(sub(d, "2013-01", "2026-10").lfx_end, sub(d, "2013-01", "2026-10").spread2))
ep00 = episode("2021-01", peak, pre00["beta"])
rob.append({"check": "H4：傾きを2000〜2020年で推定", "n": pre00["n"], "beta": pre00["beta"], "se": pre00["se"], "r2": pre00["r2"], "share": ep00["share"]})
ep10 = episode("2021-01", peak, ols(sub(d, "1990-02", "2020-12").lfx, sub(d, "1990-02", "2020-12").spread10)["beta"], sp="spread10")
rob.append({"check": "H4：10年の金利差で分解", "share": ep10["share"]})
rob[0]["share"] = ep_main["share"]
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False, float_format="%.5f", lineterminator="\n")
main["robustness"] = {k: {kk: (None if pd.isna(vv) else vv) for kk, vv in v.items()} for k, v in rob.set_index("check").round(5).to_dict(orient="index").items()}  # NaN は null に
main["episode_beta2000"] = ep00; main["episode_10y"] = ep10
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True, default=float)
print(per.round(3).to_string()); print(rob.round(3).to_string())
print({k: main[k] for k in ["H1", "H2", "H3", "H4", "peak_month", "neg_corr36_spells", "level_corr_2y"]})
print(ep_main, ep_after, ep_full, sep="\n")
