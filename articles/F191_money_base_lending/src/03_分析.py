"""お金の量（マネタリーベース・マネーストック）と貸出の関係を調べる。結果は results/ に保存。"""
import json, itertools
import numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from common import DATA, RES, SEED, EVENTS

rng = np.random.default_rng(SEED)
w = pd.read_csv(DATA / "monthly.csv", index_col=0)
w.index = pd.PeriodIndex(w.index, freq="M")
w["loan_banks_shinkin"] = w.loan_banks + w.loan_shinkin
yoy = 100 * np.log(w).diff(12)          # 前年比（対数、%）
out = {}

# ---- A. 倍率 ----
def mult(a, b, cols):
    return {c: round(w.loc[pd.Period(b), c] / w.loc[pd.Period(a), c], 3) for c in cols}
cols = ["mb", "m2", "loan_banks", "loan_dom_avg", "dep_banks"]
last = str(w.index[w[["mb", "m2", "loan_banks"]].notna().all(axis=1)][-1])
out["last"] = last
out["mult"] = {"2013-03→" + last: mult("2013-03", last, cols),
               "2001-02→2006-02": mult("2001-02", "2006-02", cols),
               "1998-04→" + last: mult("1998-04", last, cols),
               "2013-03→2019-12": mult("2013-03", "2019-12", cols)}
out["levels"] = {k: {c: round(w.loc[pd.Period(k), c] / 1e4, 1) for c in ["mb", "m2", "loan_banks"]} for k in ["1998-04", "2013-03", last]}  # 兆円
r = (w.m2 / w.mb).dropna(); out["m2_mb_ratio"] = {"1998-04": round(r["1998-04"], 2), "max": [str(r.idxmax()), round(r.max(), 2)], "min": [str(r.idxmin()), round(r.min(), 2)], last: round(r[last], 2)}
r2 = (w.loan_banks / w.mb).dropna(); out["loan_mb_ratio"] = {"1998-04": round(r2["1998-04"], 2), last: round(r2[last], 2), "min": [str(r2.idxmin()), round(r2.min(), 2)]}

# ---- B. 前年比の相関（ラグ0〜36か月） ----
def lagcorr(x, y, lags=range(0, 37), start="1999-04", end=None, excl=None):
    res = {}
    for k in lags:
        d = pd.concat([x.shift(k), y], axis=1).loc[start:end].dropna()
        if excl is not None: d = d[~d.index.isin(excl)]
        res[k] = round(d.corr().iloc[0, 1], 3)
    return res
lc_mb = lagcorr(yoy.mb, yoy.loan_banks); lc_m2 = lagcorr(yoy.m2, yoy.loan_banks); lc_mbm2 = lagcorr(yoy.mb, yoy.m2)
out["lagcorr"] = {"mb_to_loan": lc_mb, "m2_to_loan": lc_m2, "mb_to_m2": lc_mbm2}
for k, v in [("mb_to_loan", lc_mb), ("m2_to_loan", lc_m2), ("mb_to_m2", lc_mbm2)]:
    kk = max(v, key=lambda z: v[z]); out[k + "_best"] = [kk, v[kk], v[0]]

# ---- C. 回帰（HAC） ----
def reg(y, x, k, start="1999-04", end=None, excl=None):
    d = pd.concat([y, x.shift(k)], axis=1, keys=["y", "x"]).loc[start:end].dropna()
    if excl is not None: d = d[~d.index.isin(excl)]
    m = sm.OLS(d.y, sm.add_constant(d.x)).fit(cov_type="HAC", cov_kwds={"maxlags": 18})
    return {"b": round(m.params.x, 3), "se": round(m.bse.x, 3), "p": round(m.pvalues.x, 3), "r2": round(m.rsquared, 3), "n": int(m.nobs)}
out["reg_mb_loan"] = {k: reg(yoy.loan_banks, yoy.mb, k) for k in [0, 6, 12, 18, 24]}
out["reg_m2_loan"] = {k: reg(yoy.loan_banks, yoy.m2, k) for k in [0, 6, 12]}
out["reg_mb_m2"] = {k: reg(yoy.m2, yoy.mb, k) for k in [0, 6, 12]}

# ---- D. グレンジャー（月次の対数差、月ダミー、1999/04〜） ----
def granger(cols, start="1998-05", end=None, maxlags=12):
    d = 100 * np.log(w[cols]).diff().loc[start:end].dropna()
    ex = pd.get_dummies(d.index.month, prefix="m", drop_first=True).astype(float); ex.index = d.index
    v = VAR(d, exog=ex).fit(maxlags=maxlags, ic="aic")
    lag = max(v.k_ar, 1)
    if v.k_ar == 0: v = VAR(d, exog=ex).fit(1)
    t1 = v.test_causality(cols[1], [cols[0]], kind="f"); t2 = v.test_causality(cols[0], [cols[1]], kind="f")
    return {"lags": int(v.k_ar), f"{cols[0]}→{cols[1]}": round(float(t1.pvalue), 3), f"{cols[1]}→{cols[0]}": round(float(t2.pvalue), 3)}
out["granger"] = {"全期間 MB-貸出": granger(["mb", "loan_banks"]), "2013- MB-貸出": granger(["mb", "loan_banks"], "2013-04"),
                  "全期間 M2-貸出": granger(["m2", "loan_banks"]), "全期間 MB-M2": granger(["mb", "m2"]),
                  "2013- MB-M2": granger(["mb", "m2"], "2013-04")}

# ---- E. 構造変化（Bai–Perron 型：区間ごとに 貸出前年比 = a + b×MB前年比、最小24か月、BIC で区切りの数） ----
def bai_perron(y, x, h=24, mmax=4):
    n = len(y); X = np.column_stack([np.ones(n), x])
    ssr = np.full((n, n + 1), np.inf)
    for i in range(n):
        for j in range(i + h, n + 1):
            Xi, yi = X[i:j], y[i:j]
            b, *_ = np.linalg.lstsq(Xi, yi, rcond=None); e = yi - Xi @ b; ssr[i, j] = e @ e
    best = {0: (ssr[0, n], [])}
    # 動的計画法
    cost = {(1, j): (ssr[0, j], [0]) for j in range(h, n + 1)}
    res = {0: (ssr[0, n], [])}
    prev = {j: (ssr[0, j], []) for j in range(h, n + 1)}
    for m in range(1, mmax + 1):
        cur = {}
        for j in range((m + 1) * h, n + 1):
            cands = [(prev[i][0] + ssr[i, j], prev[i][1] + [i]) for i in range(m * h, j - h + 1) if i in prev]
            if cands: cur[j] = min(cands, key=lambda z: z[0])
        prev = cur
        if n in cur: res[m] = cur[n]
    bic = {m: n * np.log(s / n) + (2 * (m + 1) + m) * np.log(n) for m, (s, _) in res.items()}
    mbest = min(bic, key=bic.get)
    return res, bic, mbest
def segfit(y, x, idx, brks):
    edges = [0] + brks + [len(y)]; segs = []
    for a, b in zip(edges[:-1], edges[1:]):
        d = pd.DataFrame({"y": y[a:b], "x": x[a:b]})
        m = sm.OLS(d.y, sm.add_constant(d.x)).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
        segs.append({"from": str(idx[a]), "to": str(idx[b - 1]), "b": round(m.params.x, 3), "p": round(m.pvalues.x, 3),
                     "mean_loan": round(d.y.mean(), 2), "mean_mb": round(d.x.mean(), 2), "r2": round(m.rsquared, 2)})
    return segs
def bp_run(ycol, xcol, k, start="1999-04", end=None):
    d = pd.concat([yoy[ycol], yoy[xcol].shift(k)], axis=1, keys=["y", "x"]).loc[start:end].dropna()
    res, bic, mb_ = bp_run.cache = bai_perron(d.y.values, d.x.values)
    brks = res[mb_][1][1:] if res[mb_][1] and res[mb_][1][0] == 0 else res[mb_][1]
    brks = [b for b in brks if b > 0]
    return {"k": k, "n_breaks": int(mb_), "bic": {int(m): round(v, 1) for m, v in bic.items()},
            "breaks": [str(d.index[b]) for b in brks], "segments": segfit(d.y.values, d.x.values, d.index, brks)}
out["breaks_main"] = bp_run("loan_banks", "mb", 12)
out["breaks_lag0"] = bp_run("loan_banks", "mb", 0)
out["breaks_m2"] = bp_run("loan_banks", "m2", 0)

# ---- F. 緩和の出来事の前後24か月 ----
ev = []
for e, lab in EVENTS:
    p = pd.Period(e)
    def g(c, a, b):
        try: return round(100 * (w.loc[p + b, c] / w.loc[p + a, c] - 1), 1)
        except KeyError: return None
    ev.append({"event": lab, "month": e, "mb_before": g("mb", -24, 0), "mb_after": g("mb", 0, 24),
               "m2_before": g("m2", -24, 0), "m2_after": g("m2", 0, 24),
               "loan_before": g("loan_banks", -24, 0), "loan_after": g("loan_banks", 0, 24)})
out["events"] = ev

# ---- G. 年次の伸び率（代替案）----
ann = w[["mb", "m2", "loan_banks"]].loc["1999-01":"2025-12"]
ann = ann.groupby(ann.index.year).mean(); ag = 100 * np.log(ann).diff().dropna()
out["annual"] = {"n": len(ag), "corr_mb_loan": round(ag.corr().loc["mb", "loan_banks"], 3),
                 "corr_mb_loan_lag1": round(ag.mb.shift(1).corr(ag.loan_banks), 3),
                 "corr_m2_loan": round(ag.corr().loc["m2", "loan_banks"], 3),
                 "corr_mb_m2": round(ag.corr().loc["mb", "m2"], 3)}
# 年ごとに MB が大きく伸びた年（上位1/3）と、そうでない年の貸出の伸び
q = ag.mb.quantile(2 / 3); hi = ag[ag.mb >= q]; lo = ag[ag.mb < q]
out["annual"]["loan_growth_mb_high"] = round(hi.loan_banks.mean(), 2); out["annual"]["loan_growth_mb_low"] = round(lo.loan_banks.mean(), 2)
out["annual"]["mb_high_years"] = [int(y) for y in hi.index]
# 置換検定（年の並べ替え 10,000回）：MB の伸びと貸出の伸びの相関
obs = ag.mb.corr(ag.loan_banks); perm = np.array([np.corrcoef(rng.permutation(ag.mb.values), ag.loan_banks.values)[0, 1] for _ in range(10000)])
out["annual"]["perm_p_two_sided"] = round(float((np.abs(perm) >= abs(obs)).mean()), 4)
ag.round(2).to_csv(RES / "annual_growth.csv")

# ---- H. 頑健性の表：期間 × 系列 × ラグ ----
covid = pd.period_range("2020-03", "2021-12", freq="M")
periods = {"1999-2026": ("1999-04", None, None), "2003-2026": ("2003-04", None, None), "2013-2026": ("2013-04", None, None),
           "1999-2012": ("1999-04", "2012-12", None), "コロナ期を除く": ("1999-04", None, covid)}
money = {"MB": "mb", "日銀当座預金": "mb_current", "銀行券": "mb_notes", "M2": "m2", "M3": "m3"}
loans = {"銀行（平残）": "loan_banks", "国内銀行（平残）": "loan_dom_avg", "国内銀行（月末）": "loan_dom_end", "銀行＋信金（平残）": "loan_banks_shinkin"}
rows = []
for (pn, (s, e, ex)), (mn, mc), (ln, lcn), k in itertools.product(periods.items(), money.items(), loans.items(), [0, 6, 12, 24]):
    rr = reg(yoy[lcn], yoy[mc], k, s, e, ex)
    rows.append({"period": pn, "money": mn, "loan": ln, "lag": k, **rr})
rob = pd.DataFrame(rows); rob.to_csv(RES / "robustness_grid.csv", index=False)
def summ(df):
    return {"n": len(df), "pos_sig": int(((df.b > 0) & (df.p < 0.05)).sum()), "neg_sig": int(((df.b < 0) & (df.p < 0.05)).sum()),
            "b_min": round(df.b.min(), 3), "b_max": round(df.b.max(), 3), "r2_max": round(df.r2.max(), 3)}
out["rob_all"] = summ(rob)
out["rob_by_money"] = {m: summ(rob[rob.money == m]) for m in money}
out["rob_by_period_MB"] = {p: summ(rob[(rob.period == p) & (rob.money == "MB")]) for p in periods}
out["rob_by_lag_MB"] = {str(k): summ(rob[(rob.lag == k) & (rob.money == "MB")]) for k in [0, 6, 12, 24]}
out["rob_m2_by_period"] = {p: summ(rob[(rob.period == p) & (rob.money == "M2")]) for p in periods}

# ---- I. 見せかけの相関の確認：前年比どうしの相関を、ブロックを入れ替えた MB で（ブロック24か月、2,000回）----
d = pd.concat([yoy.mb, yoy.loan_banks], axis=1).loc["1999-04":].dropna(); x = d.mb.values; y = d.loan_banks.values
B = 24; nb = len(x) // B
obs0 = np.corrcoef(x, y)[0, 1]
sims = []
for _ in range(2000):
    order = rng.permutation(nb); xs = np.concatenate([x[i * B:(i + 1) * B] for i in order]); sims.append(np.corrcoef(xs, y[:len(xs)])[0, 1])
sims = np.array(sims)
out["block_perm"] = {"obs": round(obs0, 3), "p_two_sided": round(float((np.abs(sims) >= abs(obs0)).mean()), 4), "q025": round(np.quantile(sims, .025), 3), "q975": round(np.quantile(sims, .975), 3)}

# ---- J. 貸出の伸びが大きかった月 ----
lb = yoy.loan_banks.loc["1999-04":].dropna()
out["loan_yoy"] = {"max": [str(lb.idxmax()), round(lb.max(), 2)], "min": [str(lb.idxmin()), round(lb.min(), 2)],
                   "mean_2013_2019": round(lb.loc["2013-04":"2019-12"].mean(), 2), "mean_2003_2006": round(lb.loc["2003-01":"2006-12"].mean(), 2),
                   "mean_2021_2026": round(lb.loc["2021-01":].mean(), 2), "last": round(lb.iloc[-1], 2), "share_negative_1999_2005": round((lb.loc["1999-04":"2005-12"] < 0).mean(), 2)}
mbg = yoy.mb.loc["1999-04":].dropna()
out["mb_yoy"] = {"max": [str(mbg.idxmax()), round(mbg.max(), 2)], "min": [str(mbg.idxmin()), round(mbg.min(), 2)], "last": round(mbg.iloc[-1], 2),
                 "mean_2013_2019": round(mbg.loc["2013-04":"2019-12"].mean(), 2)}
m2g = yoy.m2.loc["1999-04":].dropna()
out["m2_yoy"] = {"mean_2013_2019": round(m2g.loc["2013-04":"2019-12"].mean(), 2), "mean_1999_2012": round(m2g.loc["1999-04":"2012-12"].mean(), 2), "max": [str(m2g.idxmax()), round(m2g.max(), 2)], "last": round(m2g.iloc[-1], 2)}
yoy.loc["1998-04":].round(3).to_csv(RES / "yoy_growth.csv")
json.dump(out, open(RES / "results.json", "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, default=str)[:200])
