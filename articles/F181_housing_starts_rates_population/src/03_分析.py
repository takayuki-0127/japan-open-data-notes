"""03 分析：住宅着工は、金利と人口のどちらで動いてきたか。
A. 年次（1966〜2024年）：差分の回帰と、長期の水準の関係
B. 四半期の VAR（1977〜2024年）：分散分解（コレスキー分解と、並べ順によらない一般化分散分解）
C. 都道府県パネル（2012〜2023年）：年の固定効果で全国共通の動き（金利を含む）を吸収し、人口の差だけの効きを見る
D. 頑健性：ラグ、利用関係（持家・貸家・分譲）、期間、金利の系列、並べ順、差分か水準か
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR

ROOT = Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
np.random.seed(181)
SUM = {}


# ---------- 共通 ----------
def quarterly(series="total_sa", rate="loan_lt_city_stock", start="1977Q1", end="2024Q4"):
    m = pd.read_csv(DATA / "monthly.csv")
    m["q"] = pd.PeriodIndex(m.month, freq="M").asfreq("Q")
    q = m.groupby("q").agg(st=(series, "sum"), n=(series, "count"), r=(rate, "mean"))
    q = q[q.n == 3]
    a = pd.read_csv(DATA / "annual.csv").set_index("year")
    # 人口は各年10月1日現在 → その年の第4四半期に置き、対数で線形補間
    lp = pd.Series(np.log(a.pop_25_44.dropna().values), index=pd.PeriodIndex([f"{y}Q4" for y in a.pop_25_44.dropna().index], freq="Q"))
    idx = pd.period_range(lp.index.min(), lp.index.max(), freq="Q")
    lp = lp.reindex(idx).interpolate()
    d = pd.DataFrame({"pop": lp}).join(q[["r"]], how="inner").join(np.log(q.st).rename("st"), how="inner")
    return d.loc[start:end].dropna()


def gfevd(res, h):
    """Pesaran–Shin の一般化分散分解（並べ順によらない）。行を合計1に正規化。"""
    S = res.sigma_u.values if hasattr(res.sigma_u, "values") else res.sigma_u
    ma = res.ma_rep(h - 1)  # (h, k, k)
    k = S.shape[0]
    num = np.zeros((k, k)); den = np.zeros(k)
    for A in ma:
        AS = A @ S
        num += AS ** 2 / np.diag(S)[None, :]
        den += np.diag(A @ S @ A.T)
    th = num / den[:, None]
    return th / th.sum(1, keepdims=True)


def var_shares(d, order=("pop", "r", "st"), lags=None, horizons=(4, 20, 40), trend="ct"):
    d = d[list(order)]
    mod = VAR(d)
    p = lags or max(1, mod.select_order(8, trend=trend).selected_orders["aic"])
    res = mod.fit(p, trend=trend)
    out = []
    k = list(order).index("st")
    for h in horizons:
        ch = res.fevd(h).decomp[k, h - 1, :]
        g = gfevd(res, h)[k]
        for j, v in enumerate(order):
            out.append({"h": h, "var": v, "chol": ch[j], "gen": g[j]})
    return res, p, pd.DataFrame(out)


# ---------- A. 年次 ----------
a = pd.read_csv(DATA / "annual.csv").set_index("year").loc[1966:2024]
A = pd.DataFrame({"dst": np.log(a.total).diff(), "dr": a.basic_rate.diff(), "dpop": np.log(a.pop_25_44).diff() * 100}).dropna()
rowsA = []
for name, X in {"金利だけ": ["dr"], "人口だけ": ["dpop"], "両方": ["dr", "dpop"]}.items():
    f = sm.OLS(A.dst, sm.add_constant(A[X])).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    rowsA.append({"model": name, "r2": f.rsquared, **{f"b_{x}": f.params[x] for x in X}, **{f"p_{x}": f.pvalues[x] for x in X}})
A_tab = pd.DataFrame(rowsA); A_tab.to_csv(RES / "annual_diff_regression.csv", index=False)
r2 = dict(zip(A_tab.model, A_tab.r2))
# 2変数のシャープレイ分解（R² の取り分）
sh_r = 0.5 * (r2["金利だけ"] + (r2["両方"] - r2["人口だけ"]))
sh_p = 0.5 * (r2["人口だけ"] + (r2["両方"] - r2["金利だけ"]))
SUM["annual_diff"] = {"n": len(A), "r2_both": r2["両方"], "share_rate": sh_r, "share_pop": sh_p,
                      "b_rate": A_tab.loc[2, "b_dr"], "p_rate": A_tab.loc[2, "p_dr"], "b_pop": A_tab.loc[2, "b_dpop"], "p_pop": A_tab.loc[2, "p_dpop"]}

# 10年単位の変化（長い目で見たとき）
L = pd.DataFrame({"st": np.log(a.total), "r": a.basic_rate, "pop": np.log(a.pop_25_44)})
L10 = (L - L.shift(10)).dropna()
f10 = sm.OLS(L10.st, sm.add_constant(L10[["r", "pop"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 10})
f10r = sm.OLS(L10.st, sm.add_constant(L10[["r"]])).fit(); f10p = sm.OLS(L10.st, sm.add_constant(L10[["pop"]])).fit()
SUM["annual_10y"] = {"n": len(L10), "r2_both": f10.rsquared, "r2_rate": f10r.rsquared, "r2_pop": f10p.rsquared,
                     "b_rate": f10.params["r"], "b_pop": f10.params["pop"], "p_rate": f10.pvalues["r"], "p_pop": f10.pvalues["pop"],
                     "share_rate": 0.5 * (f10r.rsquared + f10.rsquared - f10p.rsquared), "share_pop": 0.5 * (f10p.rsquared + f10.rsquared - f10r.rsquared)}

# 1973年（ピーク）→2024年の減少を、10年差の係数で割り振る（目安）
chg = L.loc[2024] - L.loc[1973]
SUM["peak_to_now"] = {"dlog_starts": chg.st, "pct": float(np.expm1(chg.st)), "d_rate": chg.r, "dlog_pop": chg["pop"],
                      "fit_rate": f10.params["r"] * chg.r, "fit_pop": f10.params["pop"] * chg["pop"]}
# 1996年→2024年（金利がほぼ0.5%前後に張り付いた時期）
chg2 = L.loc[2024] - L.loc[1996]
SUM["1996_to_now"] = {"dlog_starts": chg2.st, "pct": float(np.expm1(chg2.st)), "d_rate": chg2.r, "dlog_pop": chg2["pop"],
                      "fit_rate": f10.params["r"] * chg2.r, "fit_pop": f10.params["pop"] * chg2["pop"]}

# 人口に比例して減った場合（弾力性1）と比べる：25〜44歳1,000人あたりの着工
for y0 in (1973, 1996):
    pc0 = a.total[y0] / a.pop_25_44[y0]; pc1 = a.total[2024] / a.pop_25_44[2024]
    SUM[f"percap_{y0}"] = {"per1000_start": pc0, "per1000_2024": pc1, "pct_change_percap": pc1 / pc0 - 1,
                           "pop_pct": a.pop_25_44[2024] / a.pop_25_44[y0] - 1, "starts_pct": a.total[2024] / a.total[y0] - 1,
                           "share_of_logdecline_if_prop": np.log(a.pop_25_44[2024] / a.pop_25_44[y0]) / np.log(a.total[2024] / a.total[y0])}

# ---------- B. 四半期 VAR ----------
d = quarterly()
res, p, sh = var_shares(d)
sh.to_csv(RES / "var_main_shares.csv", index=False)
SUM["var_main"] = {"period": f"{d.index[0]}–{d.index[-1]}", "n": len(d), "lags": p, **{f"{r.var}_h{r.h}_{c}": getattr(r, c) for r in sh.itertuples() for c in ("chol", "gen")}}
irf = res.irf(40)
k = ["pop", "r", "st"]
irf_df = pd.DataFrame({"h": range(41), "st_to_r": irf.orth_irfs[:, 2, 1], "st_to_pop": irf.orth_irfs[:, 2, 0]})
# 信頼区間（漸近）
lo, hi = irf.errband_mc(orth=True, repl=300, signif=0.1, seed=181) if hasattr(irf, "errband_mc") else (None, None)
if lo is not None:
    irf_df["st_to_r_lo"], irf_df["st_to_r_hi"] = lo[:, 2, 1], hi[:, 2, 1]
    irf_df["st_to_pop_lo"], irf_df["st_to_pop_hi"] = lo[:, 2, 0], hi[:, 2, 0]
irf_df.to_csv(RES / "var_main_irf.csv", index=False)
SUM["irf"] = {"st_to_r_min": float(irf_df.st_to_r.min()), "st_to_r_argmin": int(irf_df.st_to_r.idxmin()),
              "sd_r": float(np.sqrt(res.sigma_u.loc["r", "r"])), "sd_pop": float(np.sqrt(res.sigma_u.loc["pop", "pop"]))}

# ---------- D. 頑健性 ----------
rob = []
def add(label, d_, **kw):
    try:
        _, pp, s = var_shares(d_, **kw)
        for h in (4, 20, 40):
            g = s[(s.h == h)].set_index("var")
            rob.append({"case": label, "lags": pp, "n": len(d_), "h": h,
                        "rate_chol": g.loc["r", "chol"], "pop_chol": g.loc["pop", "chol"], "own_chol": g.loc["st", "chol"],
                        "rate_gen": g.loc["r", "gen"], "pop_gen": g.loc["pop", "gen"], "own_gen": g.loc["st", "gen"]})
    except Exception as e:
        rob.append({"case": label, "err": str(e)[:80]})

add("基本（AIC）", d)
for L_ in (2, 4, 8):
    add(f"ラグ{L_}", d, lags=L_)
add("並べ順：着工→金利→人口", d, order=("st", "r", "pop"))
add("並べ順：金利→人口→着工", d, order=("r", "pop", "st"))
add("トレンドなし（定数のみ）", d, trend="c")
add("前半 1977–1999", d.loc[:"1999Q4"])
add("後半 2000–2024", d.loc["2000Q1":])
add("2007・2014・2020年を除く", d[~d.index.year.isin([2007, 2014, 2020])])
add("金利：新規・長期（1994–）", quarterly(rate="loan_lt_new", start="1994Q1"))
add("金利：基準割引率", quarterly(rate="basic_rate"))
for s_, lab in (("owner_sa", "持家"), ("rental_sa", "貸家"), ("sale_sa", "分譲")):
    add(f"利用関係：{lab}", quarterly(series=s_))
# 差分の VAR（水準でなく変化どうし）
dd = d.diff().dropna()
add("差分の VAR", dd, trend="c")
ROB = pd.DataFrame(rob); ROB.to_csv(RES / "var_robustness.csv", index=False)

# ---------- C. 都道府県パネル ----------
pn = pd.read_csv(DATA / "pref_panel.csv")
pn["lst"] = np.log(pn.units); pn["lpop"] = np.log(pn.pop_total); pn["lwork"] = np.log(pn.pop_15_64)
def fe_fit(y, xs, year_fe=True):
    X = pd.get_dummies(pn.pref, drop_first=True, dtype=float)
    if year_fe:
        X = X.join(pd.get_dummies(pn.year, prefix="y", drop_first=True, dtype=float))
    X = sm.add_constant(X.join(pn[xs]))
    return sm.OLS(pn[y], X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(pn.pref)[0]})
pr = []
for xs, fe in ((["lpop"], True), (["lwork"], True), (["lpop"], False)):
    f = fe_fit("lst", xs, fe)
    pr.append({"x": xs[0], "year_fe": fe, "b": f.params[xs[0]], "se": f.bse[xs[0]], "p": f.pvalues[xs[0]], "r2": f.rsquared})
# 年の固定効果だけ・県の固定効果だけ・両方の R²（県の中での動きのうち、全国共通の動きで説明できる割合）
w = pn.copy(); w["dm"] = w.lst - w.groupby("pref").lst.transform("mean")
w["yfe"] = w.groupby("year").dm.transform("mean")
r2_year = 1 - ((w.dm - w.yfe) ** 2).sum() / (w.dm ** 2).sum()
w["dp"] = w.lpop - w.groupby("pref").lpop.transform("mean"); w["dp"] -= w.groupby("year").dp.transform("mean")
resid = w.dm - w.yfe
b_ = (resid * w.dp).sum() / (w.dp ** 2).sum()
r2_pop_after = 1 - ((resid - b_ * w.dp) ** 2).sum() / (resid ** 2).sum()
PR = pd.DataFrame(pr); PR.to_csv(RES / "pref_panel.csv", index=False)
SUM["pref"] = {"n": len(pn), "years": f"{pn.year.min()}–{pn.year.max()}", "b_pop_fe": PR.b[0], "se_pop_fe": PR.se[0], "p_pop_fe": PR.p[0],
               "b_work_fe": PR.b[1], "p_work_fe": PR.p[1], "b_pop_noyear": PR.b[2], "p_pop_noyear": PR.p[2],
               "r2_within_year": r2_year, "r2_pop_after_year": r2_pop_after}
# 2012→2023 の県ごとの変化（散布図用）
ch = pn[pn.year.isin([2012, 2023])].pivot(index="pref", columns="year", values=["units", "pop_total"])
cc = pd.DataFrame({"dlst": np.log(ch[("units", 2023)] / ch[("units", 2012)]), "dlpop": np.log(ch[("pop_total", 2023)] / ch[("pop_total", 2012)])})
cc.to_csv(RES / "pref_change_2012_2023.csv")
fcc = sm.OLS(cc.dlst, sm.add_constant(cc.dlpop)).fit(cov_type="HC3")
SUM["pref_change"] = {"b": fcc.params["dlpop"], "se": fcc.bse["dlpop"], "r2": fcc.rsquared, "corr": cc.corr().iloc[0, 1],
                      "mean_dlst": cc.dlst.mean(), "sd_dlst": cc.dlst.std()}

json.dump(SUM, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(SUM, ensure_ascii=False, indent=1, default=float))
print(ROB.round(3).to_string())
