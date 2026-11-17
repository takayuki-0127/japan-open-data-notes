"""主な分析：時差の相関、グレンジャー因果、逐次の予測、構成指標の比較、月次での確かめ、頑健性。
結果は results/ に CSV と main.json で出す（ネットにはつながない）。"""
import json, sys, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import quarterly, add_lags, RES, DATA, COMP, SHOCKS

RES.mkdir(exist_ok=True)
DUM = ["D_" + k for k in SHOCKS]
OOS_START = (2005, 1)
out = {}


def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def fit(df, y, X, hac=False):
    z = df[[y] + X].dropna()
    X = [c for c in X if not (c.startswith("D_") and z[c].abs().sum() == 0)]   # その期間にないショックのダミーは外す
    m = sm.OLS(z[y], sm.add_constant(z[X], has_constant="add"))
    return (m.fit(cov_type="HAC", cov_kwds={"maxlags": 4}) if hac else m.fit()), z


def granger(df, y, x, p=2, dummies=True, hac=False, level=False):
    """y の自己ラグ p 個 + x のラグ p 個。x の係数がすべて0かの検定。"""
    d = add_lags(df, [y, x], range(1, p + 1))
    ylags = [f"{y}_L{L}" for L in range(1, p + 1)]
    xlags = [f"{x}_L{L}" for L in range(1, p + 1)]
    X = ylags + xlags + (DUM if dummies else [])
    res, z = fit(d, y, X, hac)
    test = res.f_test(" = 0, ".join(xlags) + " = 0") if not hac else res.wald_test(" = 0, ".join(xlags) + " = 0", scalar=True, use_f=True)
    pval = float(np.squeeze(test.pvalue))
    res0, _ = fit(z, y, [c for c in ylags + (DUM if dummies else []) if c in res.params.index])
    return {"p": pval, "n": int(res.nobs), "coef_L1": float(res.params[xlags[0]]), "t_L1": float(res.tvalues[xlags[0]]),
            "sum_coef": float(sum(res.params[c] for c in xlags)), "r2_gain": float(res.rsquared - res0.rsquared)}


def oos(df, y, x, p=2, start=OOS_START, drop_shock=True, xlag0=False):
    """逐次の1期先予測。ショックの四半期は推定にも評価にも使わない。xlag0=True は同じ期の x も入れる（同時点の推定）。"""
    d = add_lags(df, [y, x], range(1, p + 1))
    ylags = [f"{y}_L{L}" for L in range(1, p + 1)]
    xl = ([x] if xlag0 else []) + [f"{x}_L{L}" for L in range(1, p + 1)]
    d = d.dropna(subset=[y] + ylags + xl).reset_index(drop=True)
    if drop_shock:
        d = d[d["shock"] == 0].reset_index(drop=True)
    rows = []
    for i in range(len(d)):
        if (d.year[i], d.q[i]) < start or i < 24:
            continue
        tr = d.iloc[:i]
        m0 = sm.OLS(tr[y], sm.add_constant(tr[ylags], has_constant="add")).fit()
        m1 = sm.OLS(tr[y], sm.add_constant(tr[ylags + xl], has_constant="add")).fit()
        f0 = float(m0.params["const"] + (m0.params[ylags] * d.loc[i, ylags]).sum())
        f1 = float(m1.params["const"] + (m1.params[ylags + xl] * d.loc[i, ylags + xl]).sum())
        rows.append({"t": d.t[i], "year": int(d.year[i]), "q": int(d.q[i]), "y": float(d[y][i]), "f_ar": f0, "f_cci": f1})
    o = pd.DataFrame(rows)
    e0, e1 = o.y - o.f_ar, o.y - o.f_cci
    cw = e0 ** 2 - (e1 ** 2 - (o.f_ar - o.f_cci) ** 2)          # Clark-West（入れ子のモデル）
    cwt = float(cw.mean() / (cw.std(ddof=1) / np.sqrt(len(cw))))
    return o, {"n": int(len(o)), "rmse_ar": float(np.sqrt((e0 ** 2).mean())), "rmse_cci": float(np.sqrt((e1 ** 2).mean())),
               "ratio": float(np.sqrt((e1 ** 2).mean()) / np.sqrt((e0 ** 2).mean())), "cw_t": cwt, "cw_p_one_sided": float(1 - stats.norm.cdf(cwt))}


d = quarterly()
d.to_csv(DATA / "quarterly_panel.csv", index=False, float_format="%.6f")
Y, X = "g_hc_xrent", "d_cci"

# 1) 時差の相関（ショックの四半期の消費は除く）
cc = []
for k in range(-4, 5):
    yk = d[Y].shift(-k)
    sk = d["shock"].shift(-k)
    m = d[X].notna() & yk.notna() & (sk == 0)
    r, n = float(np.corrcoef(d.loc[m, X], yk[m])[0, 1]), int(m.sum())
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    cc.append({"k": k, "r": r, "n": n, "lo95": float(np.tanh(z - 1.96 * se)), "hi95": float(np.tanh(z + 1.96 * se))})
cc = pd.DataFrame(cc)
cc.to_csv(RES / "crosscorr_quarterly.csv", index=False, float_format="%.4f")
r0, r1, r2 = (float(cc.loc[cc.k == k, "r"].iloc[0]) for k in (0, 1, 2))
out["crosscorr"] = {"r_same": r4(r0), "r_lead1": r4(r1), "r_lead2": r4(r2), "r_lag1": r4(float(cc.loc[cc.k == -1, "r"].iloc[0])),
                    "n_same": int(cc.loc[cc.k == 0, "n"].iloc[0]), "best_k": int(cc.loc[cc.r.idxmax(), "k"]),
                    "lo_same": r4(float(cc.loc[cc.k == 0, "lo95"].iloc[0])), "hi_same": r4(float(cc.loc[cc.k == 0, "hi95"].iloc[0])),
                    "lo_lead1": r4(float(cc.loc[cc.k == 1, "lo95"].iloc[0])), "hi_lead1": r4(float(cc.loc[cc.k == 1, "hi95"].iloc[0]))}
out["H2"] = "支持" if (r0 > 0 and r0 >= 2 * r1 and r1 < r0 and r2 < r0) else ("外れ" if (r1 >= r0 or r2 >= r0) else "判定できず")

# 2) グレンジャー因果と逐次の予測（主な結果）
g = granger(d, Y, X)
o, s = oos(d, Y, X)
o.to_csv(RES / "oos_forecasts.csv", index=False, float_format="%.4f")
out["granger_main"] = {k: r4(v) if isinstance(v, float) else v for k, v in g.items()}
out["oos_main"] = {k: r4(v) if isinstance(v, float) else v for k, v in s.items()}
out["oos_main"]["improve_pct"] = r4(100 * (1 - s["ratio"]))
if g["p"] < 0.05 and s["ratio"] <= 0.95:
    out["H1"] = "支持"
elif g["p"] >= 0.05 or s["ratio"] > 0.98:
    out["H1"] = "外れ"
else:
    out["H1"] = "判定できず"

# 3) 構成指標の比較（家計消費・耐久財）
comp = []
for yv, ylab in [("g_hc_xrent", "家計消費（帰属家賃を除く）"), ("g_durable", "耐久財"), ("g_services", "サービス")]:
    for c, lab in [("cci", "消費者態度指数")] + list(COMP.items()):
        gg = granger(d, yv, "d_" + c, p=2)
        g1 = granger(d, yv, "d_" + c, p=1, hac=True)
        oo, ss = oos(d, yv, "d_" + c)
        comp.append({"y": yv, "y_label": ylab, "x": c, "x_label": lab, "granger_p": gg["p"], "t_L1_p1_hac": g1["t_L1"],
                     "coef_L1_p1": g1["coef_L1"], "rmse_ratio": ss["ratio"], "cw_p": ss["cw_p_one_sided"], "n": gg["n"]})
comp = pd.DataFrame(comp)
comp.to_csv(RES / "components.csv", index=False, float_format="%.4f")
dur = comp[(comp.y == "g_durable") & (comp.x != "cci")].reset_index(drop=True)
best = dur.loc[dur.t_L1_p1_hac.abs().idxmax()]
out["H3_detail"] = {"best_component": best.x, "best_t": r4(best.t_L1_p1_hac),
                    "kaidoki_t": r4(float(dur.loc[dur.x == "kaidoki", "t_L1_p1_hac"].iloc[0])),
                    "kaidoki_rmse_ratio": r4(float(dur.loc[dur.x == "kaidoki", "rmse_ratio"].iloc[0]))}
out["H3"] = "支持" if (best.x == "kaidoki" and abs(best.t_L1_p1_hac) >= 2) else "外れ"

# 4) H4：2013年の断層を除く
g4 = granger(d, Y, "d_cci_brk")
o4, s4 = oos(d, Y, "d_cci_brk")
out["H4_detail"] = {"p": r4(g4["p"]), "ratio": r4(s4["ratio"])}
same = ((g4["p"] < 0.05) == (g["p"] < 0.05)) and ((s4["ratio"] <= 0.95) == (s["ratio"] <= 0.95)) and ((s4["ratio"] > 0.98) == (s["ratio"] > 0.98))
out["H4"] = "支持" if same else "外れ"

# 5) 頑健性
rob = []


def add(name, df=d, y=Y, x=X, p=2, dummies=True, hac=False, drop_shock=True):
    gg = granger(df, y, x, p=p, dummies=dummies, hac=hac)
    _, ss = oos(df, y, x, p=p, drop_shock=drop_shock)
    rob.append({"case": name, "granger_p": gg["p"], "coef_L1": gg["coef_L1"], "n": gg["n"], "oos_n": ss["n"],
                "rmse_ratio": ss["ratio"], "cw_p": ss["cw_p_one_sided"]})


add("主な結果（1994〜2026年、ショックのダミーあり、ラグ2）")
add("2004年4月以降（毎月の調査）だけ", df=d[(d.year > 2004) | ((d.year == 2004) & (d.q >= 2))].reset_index(drop=True))
nocovid = d[~d.year.isin([2020]) & ~((d.year == 2021) & (d.q == 1))].reset_index(drop=True)
nocovid["D_covid"] = 0.0
add("2020年〜2021年1-3月期を標本から外す", df=nocovid)
add("態度指数を水準で入れる", x="cci")
add("家計最終消費支出（帰属家賃を含む）", y="g_hc")
add("民間最終消費支出", y="g_pc")
add("HAC 標準誤差（Newey-West、ラグ4）", hac=True)
add("ラグ1期", p=1)
add("ラグ4期", p=4)
add("ショックのダミーなし", dummies=False, drop_shock=False)
add("2013年4-6月期の変化を除く（H4）", x="d_cci_brk")
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False, float_format="%.4f")

# 6) 月次：家計調査の実質増減率（前年同月比）と態度指数の前年同月差
k = pd.read_csv(DATA / "kakei_monthly.csv")
c = pd.read_csv(DATA / "cci_monthly.csv")
c = c[(c.year > 2004) | ((c.year == 2004) & (c.month >= 4))].reset_index(drop=True)
c["cci_yoy"] = c["cci"] - c["cci"].shift(12)
m = k.merge(c[["year", "month", "cci_yoy"]], on=["year", "month"], how="inner").sort_values(["year", "month"]).reset_index(drop=True)
ym = m.year * 100 + m.month
excl = ((ym >= 201403) & (ym <= 201504)) | ((ym >= 201909) & (ym <= 202106))
m["excl"] = excl.astype(int)
mc = []
for L in range(-12, 13):
    yk, ek = m["cons"].shift(-L), m["excl"].shift(-L)
    ok = m.cci_yoy.notna() & yk.notna() & (ek == 0) & (m.excl == 0)
    mc.append({"lead_months": L, "r": float(np.corrcoef(m.loc[ok, "cci_yoy"], yk[ok])[0, 1]), "n": int(ok.sum())})
mc = pd.DataFrame(mc)
mc.to_csv(RES / "crosscorr_monthly.csv", index=False, float_format="%.4f")
out["monthly"] = {"r_same": r4(float(mc.loc[mc.lead_months == 0, "r"].iloc[0])), "best_lead": int(mc.loc[mc.r.idxmax(), "lead_months"]),
                  "r_best": r4(float(mc.r.max())), "r_lead3": r4(float(mc.loc[mc.lead_months == 3, "r"].iloc[0])),
                  "r_lead6": r4(float(mc.loc[mc.lead_months == 6, "r"].iloc[0])), "n_same": int(mc.loc[mc.lead_months == 0, "n"].iloc[0]),
                  "period": f"{int(m.year.iloc[m.cci_yoy.first_valid_index()])}-{int(m.month.iloc[m.cci_yoy.first_valid_index()]):02d}〜{int(m.year.iloc[-1])}-{int(m.month.iloc[-1]):02d}"}

# 大きく動いた四半期（|前期差|≥4）の次の期の消費の向き
bm = d.assign(y_next=d[Y].shift(-1))
bm = bm[bm[X].abs() >= 4].dropna(subset=["y_next"])
bm[["t", X, "y_next"]].to_csv(RES / "big_moves.csv", index=False, float_format="%.4f")
out["big_moves"] = {"n": int(len(bm)), "same_sign": int((np.sign(bm[X]) == np.sign(bm.y_next)).sum())}

# 要約の数字
dl = add_lags(d, [Y, X], [1, 2]).dropna(subset=[Y, Y + "_L2", X + "_L2"])
out["sample"] = {"q_first": dl.t.iloc[0], "q_last": d.t.iloc[-1], "cci_last_month": f"{int(c.year.iloc[-1])}-{int(c.month.iloc[-1]):02d}",
                 "cci_last": r4(float(c.cci.iloc[-1])), "oos_start": f"{OOS_START[0]}Q{OOS_START[1]}"}
out["robust_summary"] = {"n_cases": int(len(rob)), "n_p_lt_005": int((rob.granger_p < 0.05).sum()),
                         "n_ratio_le_095": int((rob.rmse_ratio <= 0.95).sum()),
                         "ratio_min": r4(float(rob.rmse_ratio.min())), "ratio_max": r4(float(rob.rmse_ratio.max()))}
json.dump(out, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
print(rob.to_string())
print(comp.to_string())
