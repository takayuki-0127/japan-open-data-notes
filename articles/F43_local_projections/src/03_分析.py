"""VAR と局所射影（Local Projections）で、金利ショックの動学効果を比べる

識別：再帰的（コレスキー）。順番は「生産・物価・失業率（遅い変数）→ 金利 → ドル円（速い変数）」。
     遅い変数は金利ショックに当月は反応しない、金利は同じ月の遅い変数を見て決まる、と仮定する。
局所射影では、同じ仮定を「当月の遅い変数と、全変数の過去 p か月を制御して、金利の動きの係数を見る」形で入れる
（Plagborg-Møller & Wolf 2021：同じ情報・同じ識別なら、VAR と局所射影は母集団で同じものを推定する）。
ショックの大きさ：金利が当月に 0.25%ポイント（25bp）上がる大きさにそろえる。
応答：生産・物価・ドル円は「t−1 月からの変化（対数×100＝%）」、失業率・金利は「%ポイント」。
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from common import DATA, RES, H, SHOCK, SEED

P = pd.read_csv(DATA / "panel.csv", parse_dates=["month"], index_col=0)
RESP = ["ip", "cpi", "unemp", "fx"]


def var_irf(df, order, shock, p, repl=400):
    """VAR（水準、定数あり）のインパルス応答。区間は残差ブートストラップ（各回で金利の当月の応答を 25bp にそろえ直す、90%区間）"""
    X = df[order].dropna()
    res = VAR(X).fit(p, trend="c")
    k = order.index(shock)

    def norm_irf(r):
        o = r.irf(H).orth_irfs
        return o[:, :, k] * (SHOCK / o[0, k, k])

    est = norm_irf(res)
    rng = np.random.default_rng(SEED)
    Y = X.values; T, K = Y.shape
    A = res.coefs; c = res.intercept; U = res.resid.values
    U = U - U.mean(0)
    draws = []
    for _ in range(repl):
        e = U[rng.integers(0, len(U), len(U))]
        Yb = np.zeros_like(Y); Yb[:p] = Y[:p]
        for t in range(p, T):
            Yb[t] = c + sum(A[i] @ Yb[t - 1 - i] for i in range(p)) + e[t - p]
        try:
            rb = VAR(pd.DataFrame(Yb, columns=order)).fit(p, trend="c")
            draws.append(norm_irf(rb))
        except Exception:
            pass
    D = np.array(draws)
    lo, hi = np.percentile(D, 5, axis=0), np.percentile(D, 95, axis=0)
    rows = []
    for j, v in enumerate(order):
        for h in range(H + 1):
            rows.append({"h": h, "var": v, "est": est[h, j], "lo": lo[h, j], "hi": hi[h, j]})
    return pd.DataFrame(rows), res


def lp_irf(df, order, shock, p, controls_contemp=True, hac=True):
    X = df[order].dropna()
    k = order.index(shock)
    slow = order[:k]
    lags = pd.concat({f"{v}_l{l}": X[v].shift(l) for v in order for l in range(1, p + 1)}, axis=1)
    base = [X[shock].rename("shock")]
    if controls_contemp:
        base += [X[v].rename(f"{v}_c") for v in slow]
    Z = pd.concat(base + [lags], axis=1)
    rows = []
    for v in order:
        for h in range(H + 1):
            y = X[v].shift(-h) - X[v].shift(1) if v not in ("unemp", "call", "long") else X[v].shift(-h) - X[v].shift(1)
            d = pd.concat([y.rename("y"), Z], axis=1).dropna()
            m = sm.OLS(d.y, sm.add_constant(d.drop(columns="y")))
            r = m.fit(cov_type="HAC", cov_kwds={"maxlags": h + 1}) if hac else m.fit()
            b, se = r.params["shock"], r.bse["shock"]
            rows.append({"h": h, "var": v, "est": b * SHOCK, "lo": (b - 1.645 * se) * SHOCK, "hi": (b + 1.645 * se) * SHOCK, "n": int(r.nobs)})
    out = pd.DataFrame(rows)
    # 金利自身の当月の応答は 0.25 になるように（金利の当月の係数は1）
    return out


def cum_var(irf_df):
    """VAR の応答は水準の応答（t−1 からの変化と同じ。水準の VAR なので）"""
    return irf_df


MAIN = ["ip", "cpi", "unemp", "call", "fx"]
A = P.loc["1985-07-01":"2008-12-01"]
p = 12
var_main, res_main = var_irf(A, MAIN, "call", p)
lp_main = lp_irf(A, MAIN, "call", p)
var_main.round(4).to_csv(RES / "irf_var_main.csv", index=False, encoding="utf-8-sig")
lp_main.round(4).to_csv(RES / "irf_lp_main.csv", index=False, encoding="utf-8-sig")
print("VAR obs", res_main.nobs, "LP n(h=0)", lp_main.n.iloc[0])

# ラグの数（情報量規準）
sel = VAR(A[MAIN]).select_order(18)
lag_sel = {"aic": int(sel.aic), "bic": int(sel.bic), "hqic": int(sel.hqic)}
print(lag_sel)


def pick(df, v, h):
    r = df[(df["var"] == v) & (df.h == h)].iloc[0]
    return r.est, r.lo, r.hi


# 頑健性
cases = []


def add(name, vdf, ldf):
    for v in ["ip", "cpi", "fx", "unemp"]:
        if v not in set(vdf["var"]):
            continue
        for h in [6, 12, 24]:
            e1, l1, h1 = pick(vdf, v, h)
            e2, l2, h2 = pick(ldf, v, h)
            cases.append({"case": name, "var": v, "h": h, "var_est": e1, "var_lo": l1, "var_hi": h1,
                          "lp_est": e2, "lp_lo": l2, "lp_hi": h2})


add("基本（1985〜2008年、短期金利、ラグ12）", var_main, lp_main)
for pp in [6, 18]:
    v_, _ = var_irf(A, MAIN, "call", pp, repl=200); l_ = lp_irf(A, MAIN, "call", pp)
    add(f"ラグ{pp}", v_, l_)
ORD_IMP = ["imp", "ip", "cpi", "unemp", "call", "fx"]
v_, _ = var_irf(A, ORD_IMP, "call", p, repl=200); l_ = lp_irf(A, ORD_IMP, "call", p)
add("輸入物価（資源価格）を先頭に足す", v_, l_)
B = P.loc["1985-07-01":"1995-12-01"]
v_, _ = var_irf(B, MAIN, "call", 6, repl=200); l_ = lp_irf(B, MAIN, "call", 6)
add("1985〜1995年だけ（ラグ6）", v_, l_)
FULL = P.loc["1985-07-01":"2026-08-01"]
v_, _ = var_irf(FULL, MAIN, "call", p, repl=200); l_ = lp_irf(FULL, MAIN, "call", p)
add("1985〜2026年（ゼロ金利期も含める）", v_, l_)
LONG = ["ip", "cpi", "unemp", "long", "fx"]
L1 = P.loc["1994-01-01":"2026-08-01"]
var_long, _ = var_irf(L1, LONG, "long", p, repl=400); lp_long = lp_irf(L1, LONG, "long", p)
var_long.round(4).to_csv(RES / "irf_var_long.csv", index=False, encoding="utf-8-sig")
lp_long.round(4).to_csv(RES / "irf_lp_long.csv", index=False, encoding="utf-8-sig")
add("長期金利のショック（1995〜2026年）", var_long, lp_long)
L2 = P.loc["2008-01-01":"2026-08-01"]
v_, _ = var_irf(L2, LONG, "long", 6, repl=200); l_ = lp_irf(L2, LONG, "long", 6)
var_long_low, lp_long_low = v_, l_
add("長期金利のショック（2009〜2026年、ラグ6）", v_, l_)
l_ = lp_irf(A, MAIN, "call", p, controls_contemp=False)
add("局所射影：当月の遅い変数を制御しない", var_main, l_)
rob = pd.DataFrame(cases)
rob.round(4).to_csv(RES / "robustness.csv", index=False, encoding="utf-8-sig")

# 区間の幅の比（局所射影 ÷ VAR）
wid = []
for v in RESP:
    for h in range(1, H + 1):
        _, a, b = pick(var_main, v, h); _, c, d = pick(lp_main, v, h)
        wid.append({"var": v, "h": h, "ratio": (d - c) / (b - a)})
wid = pd.DataFrame(wid)
wid.round(3).to_csv(RES / "ci_width_ratio.csv", index=False, encoding="utf-8-sig")

# 金利の動きの大きさ（時代別）
dc = P[["call", "long"]].diff()
vol = pd.DataFrame({
    "1986-2008": dc.loc["1986":"2008"].std(), "1995-2008": dc.loc["1995":"2008"].std(), "2009-2026": dc.loc["2009":"2026"].std()}).T
vol.round(4).to_csv(RES / "rate_volatility.csv", encoding="utf-8-sig")

# 結果のまとめ
S = {"var_nobs": int(res_main.nobs), "lag_sel": lag_sel, "rate_vol": vol.round(4).to_dict()}
for name, df in [("var", var_main), ("lp", lp_main), ("var_long", var_long), ("lp_long", lp_long), ("var_long_low", var_long_low), ("lp_long_low", lp_long_low)]:
    for v in RESP:
        for h in [0, 3, 6, 12, 18, 24, 36]:
            e, lo, hi = pick(df, v, h)
            S[f"{name}_{v}_h{h}"] = [round(e, 3), round(lo, 3), round(hi, 3)]
    sub = df[df["var"].isin(RESP)]
    for v in ["ip", "cpi"]:
        s = sub[sub["var"] == v]
        i = s.est.idxmin()
        S[f"{name}_{v}_min"] = [int(s.loc[i, "h"]), round(s.loc[i, "est"], 3)]
        sig = s[(s.hi < 0)]
        S[f"{name}_{v}_sig_neg_h"] = sig.h.tolist()
        sigp = s[(s.lo > 0)]
        S[f"{name}_{v}_sig_pos_h"] = sigp.h.tolist()
S["ci_ratio_median"] = wid.groupby("var").ratio.median().round(2).to_dict()
S["ci_ratio_h1_12"] = wid[wid.h <= 12].groupby("var").ratio.median().round(2).to_dict()
S["ci_ratio_h13_36"] = wid[wid.h > 12].groupby("var").ratio.median().round(2).to_dict()
corr = {}
for v in RESP:
    a = var_main[var_main["var"] == v].est.values; b = lp_main[lp_main["var"] == v].est.values
    corr[v] = round(float(np.corrcoef(a, b)[0, 1]), 2)
S["var_lp_corr"] = corr
json.dump(S, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(S, ensure_ascii=False)[:4000])
