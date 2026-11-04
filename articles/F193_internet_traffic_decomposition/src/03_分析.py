"""分析：
A 長期の伸び（全国のダウンロード・アップロード推計、半年ごと）…協力ISP5社→9社をつなぎ、期間ごとの年率
B コロナ期の段差（半年ごと：ISP9社の全国推計／月次：国内主要IX）…トレンド＋季節＋段差の回帰と、トレンドの延長との比較
C 時間帯別の増え方（ISP9社 A1、2020年11月〜2026年5月）
頑健性：期間・指標（ダウン/アップ、ISP5/9、IX）・段差の扱い（段差のみ／段差＋傾き変化／2020年の点を除く）・時間帯の比較を同じ月どうしに"""
import json, numpy as np, pandas as pd, statsmodels.api as sm
from statsmodels.tsa.seasonal import STL
from common import DATA, RES, SEED
np.random.seed(SEED)
semi = pd.read_csv(DATA / "semiannual.csv"); ix = pd.read_csv(DATA / "ix_monthly.csv"); di = pd.read_csv(DATA / "diurnal.csv")
semi["t"] = pd.to_datetime(semi.date); semi["yr"] = semi.t.dt.year + (semi.t.dt.month - 1) / 12
S = {}

# ---------- A 長期 ----------
ov = semi.dropna(subset=["isp5_down", "isp9_down"])
ratio_d = float(np.exp(np.mean(np.log(ov.isp9_down / ov.isp5_down)))); ratio_u = float(np.exp(np.mean(np.log(ov.isp9_up / ov.isp5_up))))
S["splice"] = dict(overlap=list(ov.date), ratio_down=ratio_d, ratio_up=ratio_u,
                   ratio_down_each=[round(x, 3) for x in ov.isp9_down / ov.isp5_down], ratio_up_each=[round(x, 3) for x in ov.isp9_up / ov.isp5_up])
semi["down"] = semi.isp9_down.where(semi.isp9_down.notna(), semi.isp5_down * ratio_d)
semi["up"] = semi.isp9_up.where(semi.isp9_up.notna(), semi.isp5_up * ratio_u)
semi["down_raw"] = semi.isp9_down.where(semi.isp9_down.notna(), semi.isp5_down)  # つながない版
semi["up_raw"] = semi.isp9_up.where(semi.isp9_up.notna(), semi.isp5_up)
semi.to_csv(RES / "semiannual_spliced.csv", index=False)
def gr(col, a, b, d=semi):
    x = d[(d.yr >= a) & (d.yr < b + 0.99)].dropna(subset=[col])
    if len(x) < 4: return None
    X = sm.add_constant(np.c_[x.yr.values, (x.t.dt.month == 11).astype(float).values], has_constant="add"); m = sm.OLS(np.log(x[col].values), X).fit()
    pr = np.asarray(m.params); ci = np.asarray(m.conf_int())
    return dict(n=len(x), annual=float(np.exp(pr[1]) - 1), lo=float(np.exp(ci[1][0]) - 1), hi=float(np.exp(ci[1][1]) - 1), doubling=float(np.log(2) / pr[1]))
eras = [(2004, 2009), (2010, 2014), (2015, 2019), (2021, 2026)]
S["growth"] = {c: {f"{a}-{b}": gr(c, a, b) for a, b in eras} for c in ["down", "up", "down_raw", "up_raw", "ix_avg", "isp9_down_per"]}
f, l = semi.iloc[0], semi.iloc[-1]
S["level"] = dict(first=f.date, last=l.date, down_first=float(f.down), down_last=float(l.down), mult_down=float(l.down / f.down),
                  up_first=float(f.up), up_last=float(l.up), mult_up=float(l.up / f.up), updown_first=float(f.up / f.down), updown_last=float(l.up / l.down),
                  contracts_first=float(f.contracts_k), contracts_last=float(l.contracts_k),
                  per_contract_GB_day_last=float(l.down * 1e9 / 8 * 86400 / (l.contracts_k * 1e3) / 1e9))
semi["updown"] = semi.up / semi.down

# ---------- B 段差（半年ごと） ----------
def step_fit(d, col, start, end, step_at="2020-05", slope=False, drop2020=False):
    x = d[(d.t >= start) & (d.t <= end)].dropna(subset=[col]).copy()
    if drop2020: x = x[~x.date.isin(["2020-05", "2020-11"])]
    st = (x.t >= step_at).astype(float).values; tt = (x.yr - 2020.33).values
    cols = [tt, (x.t.dt.month == 11).astype(float).values, st] + ([st * tt] if slope else [])
    X = sm.add_constant(np.column_stack(cols), has_constant="add"); m = sm.OLS(np.log(x[col].values), X).fit(cov_type="HC1")
    k = 3
    res = dict(n=len(x), step=float(np.exp(m.params[k]) - 1), lo=float(np.exp(m.conf_int()[k][0]) - 1), hi=float(np.exp(m.conf_int()[k][1]) - 1),
               p=float(m.pvalues[k]), trend=float(np.exp(m.params[1]) - 1))
    if slope:
        res.update(slope_change=float(np.exp(m.params[4]) - 1), slope_p=float(m.pvalues[4]), trend_after=float(np.exp(m.params[1] + m.params[4]) - 1))
    return res
B = {}
for col in ["down", "up"]:
    for st in ["2015-05", "2017-05", "2010-05"]:
        for slope in [False, True]:
            for dr in [False, True]:
                B[f"{col}|{st}|{'step+slope' if slope else 'step'}|{'drop2020' if dr else 'all'}"] = step_fit(semi, col, st, "2026-05", slope=slope, drop2020=dr)
S["step_semi"] = B
# トレンドの延長との比較（2015-05〜2019-11 で推定 → 2020-05以降）
def cf(col, a="2015-05", b="2019-11"):
    x = semi[(semi.t >= a) & (semi.t <= b)]
    X = sm.add_constant(np.c_[x.yr.values, (x.t.dt.month == 11).astype(float).values]); m = sm.OLS(np.log(x[col].values), X).fit()
    y = semi[semi.t >= "2017-05"].copy(); Xa = sm.add_constant(np.c_[y.yr.values, (y.t.dt.month == 11).astype(float).values], has_constant="add")
    y["pred"] = np.exp(Xa @ np.asarray(m.params)); y["ratio"] = y[col] / y["pred"]; return y[["date", col, "pred", "ratio"]]
cfd = cf("down"); cfd.to_csv(RES / "counterfactual_down.csv", index=False)
S["cf_down"] = {r.date: round(float(r.ratio), 3) for r in cfd.itertuples()}
S["cf_up"] = {r.date: round(float(r.ratio), 3) for r in cf("up").itertuples()}
S["cf_down_2010"] = {r.date: round(float(r.ratio), 3) for r in cf("down", "2010-05").itertuples()}
S["cf_down_2017"] = {r.date: round(float(r.ratio), 3) for r in cf("down", "2017-05").itertuples()}
S["cf_up_2017"] = {r.date: round(float(r.ratio), 3) for r in cf("up", "2017-05").itertuples()}
cf("down", "2017-05").to_csv(RES / "counterfactual_down_2017.csv", index=False)
S["jump"] = dict(down=float(semi.set_index("date").down["2020-05"] / semi.set_index("date").down["2019-11"] - 1),
                 up=float(semi.set_index("date").up["2020-05"] / semi.set_index("date").up["2019-11"] - 1),
                 down_yoy_2020_05=float(semi.set_index("date").down["2020-05"] / semi.set_index("date").down["2019-05"] - 1),
                 typical_halfyear_2015_2019=float(np.exp(np.mean(np.diff(np.log(semi[(semi.t >= "2015-05") & (semi.t <= "2019-11")].down)))) - 1))

# ---------- B 月次（IX） ----------
ix["t"] = pd.to_datetime(ix.date); ix = ix[ix.ix_avg.notna()].copy()
ix["yr"] = ix.t.dt.year + (ix.t.dt.month - 1) / 12; ix["ly"] = np.log(ix.ix_avg)
ix["brk2011"] = (ix.t >= "2011-01").astype(float)
def ix_fit(start, end="2026-05", step_at="2020-03", slope=False, brk=True, knots=(2010, 2015)):
    x = ix[(ix.t >= start) & (ix.t <= end)].copy(); tt = (x.yr - 2020.17).values
    cols = [tt] + [np.maximum(x.yr.values - k, 0) for k in knots if x.yr.min() < k]
    md = pd.get_dummies(x.t.dt.month, prefix="m", drop_first=True).astype(float).values
    st = (x.t >= step_at).astype(float).values
    Xl = cols + [md] + ([x.brk2011.values] if brk and x.brk2011.nunique() > 1 else []) + [st] + ([st * tt] if slope else [])
    X = sm.add_constant(np.column_stack(Xl)); m = sm.OLS(x.ly.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    k = X.shape[1] - (2 if slope else 1)
    r = dict(n=len(x), step=float(np.exp(m.params[k]) - 1), lo=float(np.exp(m.conf_int()[k][0]) - 1), hi=float(np.exp(m.conf_int()[k][1]) - 1), p=float(m.pvalues[k]))
    if slope: r.update(slope_change=float(np.exp(m.params[k + 1]) - 1), slope_p=float(m.pvalues[k + 1]))
    return r
IXB = {}
for st in ["2011-01", "2015-01", "2017-01"]:
    for slope in [False, True]:
        for sa in ["2020-03", "2020-04"]:
            IXB[f"{st}|{'step+slope' if slope else 'step'}|{sa}"] = ix_fit(st, step_at=sa, slope=slope, knots=(2015,) if st < "2015" else ())
S["step_ix"] = IXB
# STL（2011-01以降、対数）
x = ix[ix.t >= "2011-01"].set_index("t").ly; x = x.asfreq("MS").interpolate()
stl = STL(x, period=12, robust=True, seasonal=13).fit()
dfstl = pd.DataFrame(dict(date=x.index.strftime("%Y-%m"), log=x.values, trend=stl.trend.values, seasonal=stl.seasonal.values, resid=stl.resid.values))
dfstl.to_csv(RES / "ix_stl.csv", index=False)
seas = dfstl.assign(m=pd.to_datetime(dfstl.date).dt.month).groupby("m").seasonal.mean()
S["stl"] = dict(seasonal_by_month={int(k): round(float(np.exp(v) - 1), 4) for k, v in seas.items()},
                seasonal_range=float(np.exp(seas.max()) - np.exp(seas.min())),
                var_share=dict(trend_diff=float(np.var(np.diff(stl.trend))), seasonal=float(np.var(stl.seasonal)), resid=float(np.var(stl.resid))),
                resid_2020_03_06={d: round(float(np.exp(v) - 1), 4) for d, v in zip(dfstl.date, dfstl.resid) if d in ("2020-02", "2020-03", "2020-04", "2020-05", "2020-06")},
                trend_growth_yoy={y: round(float(np.exp(dfstl.trend[dfstl.date == f"{y}-06"].values[0] - dfstl.trend[dfstl.date == f"{y-1}-06"].values[0]) - 1), 3) for y in range(2012, 2026)})
ix["yoy"] = ix.ix_avg / ix.ix_avg.shift(12) - 1
S["ix_yoy"] = {d: round(float(v), 3) for d, v in zip(ix.date, ix.yoy) if d[:4] in ("2019", "2020", "2021") and d[5:] in ("01", "03", "04", "05", "06", "12")}
S["ix_2011_jump"] = float(ix.set_index("date").ix_avg["2011-01"] / ix.set_index("date").ix_avg["2010-12"] - 1)

# ---------- C 時間帯 ----------
DAYS = "日月火水木金土"
di["d0"] = di.day.str[0]; di["wk"] = np.where(di.d0.isin(["土", "日"]), "週末", "平日"); di["hour"] = di.start.str[:2].astype(int)
per = sorted(di.period.unique())
def prof(p, col="down", wk=None):
    x = di[di.period == p]; x = x if wk is None else x[x.wk == wk]
    return x.groupby("hour")[col].mean()
C = {}
for col in ["down", "up"]:
    tot = di.groupby("period")[col].mean()
    C[col] = dict(mean_by_period={p: round(float(v), 1) for p, v in tot.items()})
    for a, b, lab in [("2020-11", "2026-05", "main"), ("2020-11", "2025-11", "nov"), ("2021-05", "2026-05", "may")]:
        g = {}
        for wk in ["平日", "週末"]:
            pa, pb = prof(a, col, wk), prof(b, col, wk)
            g[wk] = {int(h): round(float(pb[h] / pa[h] - 1), 4) for h in pa.index}
        ta, tb = tot[a], tot[b]
        g["total"] = float(tb / ta - 1)
        # 増えた量（Gbps）が一番多い時間帯、伸び率の時間帯差
        pa, pb = prof(a, col), prof(b, col)
        g["abs_add_by_hour"] = {int(h): round(float(pb[h] - pa[h]), 1) for h in pa.index}
        g["growth_by_hour_all"] = {int(h): round(float(pb[h] / pa[h] - 1), 4) for h in pa.index}
        C[col][lab] = g
    # 形の指標
    shape = {}
    for p in per:
        pa = prof(p, col); w = prof(p, col, "平日"); e = prof(p, col, "週末")
        shape[p] = dict(peak_hour=int(pa.idxmax()), peak_to_trough=float(pa.max() / pa.min()), peak_to_mean=float(pa.max() / pa.mean()),
                        night_share=float(pa.loc[[19, 21, 23]].sum() / pa.sum()), day_share=float(pa.loc[[9, 11, 13, 15]].sum() / pa.sum()),
                        weekday_day_vs_night=float(w.loc[[9, 11, 13, 15]].mean() / w.loc[[19, 21]].mean()),
                        weekend_over_weekday=float(e.mean() / w.mean()), weekend_day_over_weekday_day=float(e.loc[[9, 11, 13, 15]].mean() / w.loc[[9, 11, 13, 15]].mean()))
    C[col]["shape"] = shape
    # 半年ごと全国推計との整合（A1の平均＝全国推計×シェア）
S["diurnal"] = C
chk = []
for p in per:
    r = semi[semi.date == p]
    if len(r): chk.append(dict(period=p, diurnal_mean=float(di[di.period == p].down.mean()), a1_down=float(r.isp9_a1_down.iloc[0]) if pd.notna(r.isp9_a1_down.iloc[0]) else None))
S["diurnal_check"] = chk
# 時間帯ごとの伸びのばらつき（時間帯間の差が半年ごとの揺れより大きいか）：12期間の各時間帯の年率を回帰で
rates = {}
for h in sorted(di.hour.unique()):
    for wk in ["平日", "週末"]:
        x = di[(di.hour == h) & (di.wk == wk)].groupby("period").down.mean().reset_index()
        x["yr"] = pd.to_datetime(x.period).dt.year + (pd.to_datetime(x.period).dt.month - 1) / 12
        X = sm.add_constant(np.c_[x.yr.values, (pd.to_datetime(x.period).dt.month == 11).astype(float).values]); m = sm.OLS(np.log(x.down.values), X).fit()
        rates[f"{wk}{h:02d}"] = dict(rate=float(np.exp(m.params[1]) - 1), lo=float(np.exp(m.conf_int()[1][0]) - 1), hi=float(np.exp(m.conf_int()[1][1]) - 1))
S["hour_rates"] = rates
pd.DataFrame([dict(key=k, **v) for k, v in rates.items()]).to_csv(RES / "hour_rates.csv", index=False)
json.dump(S, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
# 頑健性一覧
rob = []
for k, v in B.items(): rob.append(dict(kind="semi", spec=k, **{kk: v[kk] for kk in ("n", "step", "lo", "hi", "p")}))
for k, v in IXB.items(): rob.append(dict(kind="ix", spec=k, **{kk: v[kk] for kk in ("n", "step", "lo", "hi", "p")}))
pd.DataFrame(rob).to_csv(RES / "robustness_step.csv", index=False)
print(json.dumps({k: S[k] for k in ["splice", "level", "jump"]}, ensure_ascii=False, indent=0))
