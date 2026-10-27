"""F55 分析：ベイズ構造時系列（BSTS）で出生数を予測し、予測の幅を SARIMA と比べる

A. コロナがなかった場合（2010〜19年で学習 → 2020〜25年）を F02 の SARIMA と比べる
B. バックテスト（2014〜18年末を起点に、12か月先と36か月先）で予測区間の当たり方を比べる
C. 2026〜30年の予測（2016〜25年で学習）
D. 傾き（1年あたりの減り方）の事後分布の推移（2005〜25年で学習）
E. 頑健性：事前分布・学習期間・モデルの成分
"""
import json
from common import *

d = monthly()
rows_fit = []


def fit(y, tag, **kw):
    p = fit_bsts(y, draws=2500, tune=2000, **kw)
    rows_fit.append({"fit": tag, "start": str(y.index[0].date())[:7], "end": str(y.index[-1].date())[:7],
                     "rhat_max": round(p["rhat_max"], 3), "ess_min": round(p["ess_min"], 0),
                     "s_lev_med": float(np.median(p["s_lev"])), "s_obs_med": float(np.median(p["s_obs"])),
                     "s_slp_med": float(np.median(p["s_slp"])) if p["slope"] else np.nan})
    pd.DataFrame(rows_fit).to_csv(RES / "fit_diagnostics.csv", index=False)
    return p


def counts(logpd, idx):
    return np.exp(logpd) * days_in(idx)[:, None]


def annual(sims_c, idx):
    yr = pd.DatetimeIndex(idx).year
    return pd.DataFrame(sims_c, index=yr).groupby(level=0).sum()       # 年 × シミュレーション


# ---------- A ----------
def part_a(y_train, tag, **kw):
    h = 72
    idx = future_index(y_train.index[-1], h)
    p = fit(y_train, tag, **kw)
    sb = counts(sim_bsts(p, h), idx)
    act = d.loc[idx, "births"].values
    return p, sb, idx, act


y_main = d.loc["2010":"2019", "y"]
p_main, sb, idx, act = part_a(y_main, "A_main")
ss = counts(sim_sarima(y_main, 72), idx)
np.save(RES / "_A_bsts.npy", sb.astype("float32")); np.save(RES / "_A_sarima.npy", ss.astype("float32"))

rows = []
for name, s in [("BSTS", sb), ("SARIMA", ss)]:
    lo, hi = interval(s, 0.95)
    lo8, hi8 = interval(s, 0.80)
    for i, t in enumerate(idx):
        rows.append({"model": name, "date": str(t.date())[:7], "h": i + 1, "actual": act[i], "median": np.median(s[i]),
                     "lo95": lo[i], "hi95": hi[i], "lo80": lo8[i], "hi80": hi8[i]})
monthA = pd.DataFrame(rows)
monthA.to_csv(RES / "A_monthly_forecast.csv", index=False)

annA = []
for name, s in [("BSTS", sb), ("SARIMA", ss)]:
    a = annual(s, idx)
    for yr in a.index:
        v = a.loc[yr].values
        annA.append({"model": name, "year": yr, "actual": int(d.loc[str(yr), "births"].sum()),
                     "median": np.median(v), "lo95": np.quantile(v, .025), "hi95": np.quantile(v, .975),
                     "lo80": np.quantile(v, .1), "hi80": np.quantile(v, .9)})
annA = pd.DataFrame(annA)
annA["width95"] = annA["hi95"] - annA["lo95"]
annA.to_csv(RES / "A_annual_forecast.csv", index=False)

# 2020〜22年の累積の差（実績 − 予測）と、月ごとに区間の外に出た数
summA = []
m2022 = np.asarray(pd.DatetimeIndex(idx).year <= 2022)
for name, s in [("BSTS", sb), ("SARIMA", ss)]:
    gap = act[m2022].sum() - s[m2022].sum(0)
    lo, hi = interval(s, 0.95)
    out = (act < lo) | (act > hi)
    w = (hi - lo) / np.median(s, 1)
    summA.append({"model": name, "gap2020_22_med": np.median(gap), "gap_lo95": np.quantile(gap, .025),
                  "gap_hi95": np.quantile(gap, .975), "months_out95_of72": int(out.sum()),
                  "months_below95": int((act < lo).sum()), "rel_width95_h12": w[11], "rel_width95_h36": w[35],
                  "rel_width95_h72": w[71]})
pd.DataFrame(summA).to_csv(RES / "A_summary.csv", index=False)

# ---------- B バックテスト ----------
bt = []
for org in [2014, 2015, 2016, 2017, 2018]:
    ytr = d.loc[str(org - 9):str(org), "y"]
    H = min(36, (2019 - org) * 12)
    idxb = future_index(ytr.index[-1], H)
    pb = fit(ytr, f"B_{org}")
    sims = {"BSTS": sim_bsts(pb, H), "SARIMA": sim_sarima(ytr, H)}
    yo = d.loc[idxb, "y"].values
    for name, s in sims.items():
        crps = crps_ens(s, yo)
        for lev in (0.8, 0.95):
            lo, hi = interval(s, lev)
            for i in range(H):
                bt.append({"origin": org, "model": name, "h": i + 1, "level": lev, "inside": int(lo[i] <= yo[i] <= hi[i]),
                           "width": hi[i] - lo[i], "crps": crps[i], "abs_err": abs(np.median(s[i]) - yo[i])})
bt = pd.DataFrame(bt)
bt.to_csv(RES / "B_backtest_detail.csv", index=False)
bt["hgrp"] = pd.cut(bt["h"], [0, 12, 24, 36], labels=["1-12", "13-24", "25-36"])
btsum = bt.groupby(["model", "level", "hgrp"], observed=True).agg(
    n=("inside", "size"), coverage=("inside", "mean"), width=("width", "mean"), crps=("crps", "mean"),
    mae=("abs_err", "mean")).reset_index()
btsum.to_csv(RES / "B_backtest_summary.csv", index=False)

# ---------- C 2026〜30年 ----------
def future(y_train, tag, **kw):
    h = 60
    idxf = future_index(y_train.index[-1], h)
    p = fit(y_train, tag, **kw)
    s = counts(sim_bsts(p, h), idxf)
    a = annual(s, idxf)
    return p, s, a, idxf


pC, sC, aC, idxC = future(d.loc["2016":"2025", "y"], "C_main")
sCs = counts(sim_sarima(d.loc["2016":"2025", "y"], 60), idxC)
aCs = annual(sCs, idxC)
np.save(RES / "_C_bsts_annual.npy", aC.values.astype("float32"))
rowsC = []
for name, a in [("BSTS", aC), ("SARIMA", aCs)]:
    for yr in a.index:
        v = a.loc[yr].values
        rowsC.append({"model": name, "year": yr, "median": np.median(v), "lo95": np.quantile(v, .025),
                      "hi95": np.quantile(v, .975), "lo80": np.quantile(v, .1), "hi80": np.quantile(v, .9),
                      "p_below_600k": float((v < 600000).mean()), "p_below_550k": float((v < 550000).mean()),
                      "p_below_500k": float((v < 500000).mean())})
pd.DataFrame(rowsC).to_csv(RES / "C_future_annual.csv", index=False)

# ---------- D 傾きの推移（2005〜25年） ----------
pD = fit(d.loc["2005":"2025", "y"], "D_slope")
dl = pD["dlt"] * 12                                   # 1年あたりの log 変化
idxD = d.loc["2005":"2025"].index
slope = pd.DataFrame({"date": [str(t.date())[:7] for t in idxD],
                      "med": np.median(dl, 0), "lo90": np.quantile(dl, .05, 0), "hi90": np.quantile(dl, .95, 0),
                      "p_neg": (dl < 0).mean(0)})
slope["pct_per_year_med"] = (np.exp(slope["med"]) - 1) * 100
slope.to_csv(RES / "D_slope_path.csv", index=False)

# ---------- E 頑健性 ----------
rob = []
variants = [("基本（2010〜19年・事前分布 base）", d.loc["2010":"2019", "y"], {}),
            ("事前分布 tight", d.loc["2010":"2019", "y"], {"prior": "tight"}),
            ("事前分布 loose", d.loc["2010":"2019", "y"], {"prior": "loose"}),
            ("学習 2005〜19年", d.loc["2005":"2019", "y"], {}),
            ("学習 2014〜19年", d.loc["2014":"2019", "y"], {}),
            ("傾きなし（ローカルレベル）", d.loc["2010":"2019", "y"], {"slope": False}),
            ("季節も動かす", d.loc["2010":"2019", "y"], {"seas_rw": True})]
for name, ytr, kw in variants:
    if name.startswith("基本"):
        p, s = p_main, sb
    else:
        p = fit(ytr, "E_" + name, **kw)
        s = counts(sim_bsts(p, 72), idx)
    gap = act[m2022].sum() - s[m2022].sum(0)
    lo, hi = interval(s, 0.95)
    a = annual(s, idx)
    v19 = a.loc[2022].values
    rob.append({"variant": name, "gap2020_22_med": np.median(gap), "gap_lo95": np.quantile(gap, .025),
                "gap_hi95": np.quantile(gap, .975), "months_below95": int((act < lo).sum()),
                "pred2022_med": np.median(v19), "pred2022_lo95": np.quantile(v19, .025), "pred2022_hi95": np.quantile(v19, .975),
                "rel_width95_h36": ((hi - lo) / np.median(s, 1))[35]})
    pd.DataFrame(rob).to_csv(RES / "E_robustness_counterfactual.csv", index=False)

robC = []
for name, ytr, kw in [("基本（2016〜25年・base）", None, {}), ("事前分布 tight", d.loc["2016":"2025", "y"], {"prior": "tight"}),
                      ("事前分布 loose", d.loc["2016":"2025", "y"], {"prior": "loose"}),
                      ("学習 2010〜25年", d.loc["2010":"2025", "y"], {}),
                      ("傾きなし（ローカルレベル）", d.loc["2016":"2025", "y"], {"slope": False})]:
    if ytr is None:
        a = aC
    else:
        _, _, a, _ = future(ytr, "EC_" + name, **kw)
    v = a.loc[2030].values; v26 = a.loc[2026].values
    robC.append({"variant": name, "y2026_med": np.median(v26), "y2026_lo95": np.quantile(v26, .025),
                 "y2026_hi95": np.quantile(v26, .975), "y2030_med": np.median(v), "y2030_lo95": np.quantile(v, .025),
                 "y2030_hi95": np.quantile(v, .975)})
    pd.DataFrame(robC).to_csv(RES / "E_robustness_future.csv", index=False)
print("done")
