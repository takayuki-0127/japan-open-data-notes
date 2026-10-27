"""需要の価格弾力性：最小二乗法・操作変数（原油の円建て価格）・部分調整モデル・補助金期間"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.iv import IV2SLS
from statsmodels.tsa.seasonal import STL
from common import DATA, RES, SUBSIDY_START, COVID, TAX_END

RES.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "monthly.csv", index_col=0)
d.index = pd.PeriodIndex(d.index, freq="M")
d["lq"] = np.log(d.gas_kl / d.days)          # 1日当たり販売量
d["lp"] = np.log(d.rprice)                   # 実質価格
d["lpn"] = np.log(d.price)                   # 名目価格
d["lo"] = np.log(d.oil_yen_l)                # 原油の円建て価格
d["lo_usd"] = np.log(d.oil_usd)
d["lh"] = np.log(d.hh_l / d.days)            # 家計調査からの購入量の目安
for v in ["lq", "lp", "lpn", "lo", "lo_usd", "lh"]:
    d["d" + v] = d[v] - d[v].shift(12)       # 前年同月差（季節をそろえる）
for k in (1, 2):
    d[f"dlo_l{k}"] = d["dlo"].shift(k)
    d[f"dlo_usd_l{k}"] = d["dlo_usd"].shift(k)
    d[f"lo_l{k}"] = d["lo"].shift(k)
covid = (d.index >= pd.Period(COVID[0], "M")) & (d.index <= pd.Period(COVID[1], "M"))
d["covid"] = covid.astype(int)
d["sub"] = (d.index >= pd.Period(SUBSIDY_START, "M")).astype(int)
d.to_csv(DATA / "panel.csv")

HAC = dict(cov_type="kernel", kernel="bartlett", bandwidth=12)
def ols(df, y, x):
    m = sm.OLS(df[y], sm.add_constant(df[x])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    return m
def iv(df, y, endog, instr, exog=None):
    ex = sm.add_constant(df[exog]) if exog else pd.Series(1.0, index=df.index, name="const").to_frame()
    return IV2SLS(df[y], ex, df[[endog]], df[instr]).fit(**HAC)
def ci(m, name):
    p = m.params[name]; s = m.std_errors[name] if hasattr(m, "std_errors") else m.bse[name]
    return [float(p), float(p - 1.96 * s), float(p + 1.96 * s)]

INS = ["dlo", "dlo_l1", "dlo_l2"]
main = d.loc["2018-01":"2026-08"].dropna(subset=["dlq", "dlp"] + INS)
main = main[main.covid == 0]
out = {"n_main": int(len(main)), "period_main": f"{main.index.min()}〜{main.index.max()}（{COVID[0]}〜{COVID[1]}を除く）"}

# 1) 最小二乗法と操作変数（前年同月差）
m_ols = ols(main, "dlq", ["dlp"])
m_iv = iv(main, "dlq", "dlp", INS)
fs = sm.OLS(main["dlp"], sm.add_constant(main[INS])).fit()
fs_h = sm.OLS(main["dlp"], sm.add_constant(main[INS])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
out["ols"] = ci(m_ols, "dlp")
out["iv"] = ci(m_iv, "dlp")
out["first_stage_F"] = float(fs.fvalue)
out["first_stage_F_hac"] = float(fs_h.f_test(np.eye(4)[1:]).fvalue)
out["first_stage_R2"] = float(fs.rsquared)
out["corr_dlp_dlo"] = float(main[["dlp", "dlo"]].corr().iloc[0, 1])

# 補助金の前と後で、原油→店頭価格の通り方（パススルー）
for nm, sub in [("pre", main[main["sub"] == 0]), ("post", main[main["sub"] == 1])]:
    f = sm.OLS(sub["dlp"], sm.add_constant(sub[INS])).fit()
    out[f"passthrough_{nm}"] = {"sum": float(f.params[INS].sum()), "R2": float(f.rsquared), "n": int(len(sub)),
                                 "F": float(f.fvalue)}
    out[f"iv_{nm}"] = ci(iv(sub, "dlq", "dlp", INS), "dlp") if len(sub) > 20 else None
    out[f"ols_{nm}"] = ci(ols(sub, "dlq", ["dlp"]), "dlp")

# 2) 部分調整モデル（水準・月ダミー・トレンド）：lq_t = a + b lp_t + c lq_{t-1} + ...
lv = d.loc["2017-02":"2026-08"].copy()
lv["lq_l1"] = lv["lq"].shift(1)
lv["trend"] = np.arange(len(lv)) / 12
md = pd.get_dummies(lv.index.month, prefix="m", drop_first=True).astype(float)
md.index = lv.index
lv = pd.concat([lv, md], axis=1)
lv["covid_m"] = lv["covid"]
lv = lv.dropna(subset=["lq", "lq_l1", "lp", "lo", "lo_l1", "lo_l2"])
X = ["lp", "lq_l1", "trend", "covid_m"] + list(md.columns)
pa = sm.OLS(lv["lq"], sm.add_constant(lv[X])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
b, c = pa.params["lp"], pa.params["lq_l1"]
pa_iv = IV2SLS(lv["lq"], sm.add_constant(lv[["lq_l1", "trend", "covid_m"] + list(md.columns)]), lv[["lp"]],
               lv[["lo", "lo_l1", "lo_l2"]]).fit(**HAC)
b2, c2 = pa_iv.params["lp"], pa_iv.params["lq_l1"]
def lr_ci(model, bn="lp", cn="lq_l1", nsim=4000, seed=42):
    rng = np.random.default_rng(seed)
    cov = model.cov.loc[[bn, cn], [bn, cn]].values if hasattr(model, "cov") else model.cov_params().loc[[bn, cn], [bn, cn]].values
    mu = np.array([model.params[bn], model.params[cn]])
    s = rng.multivariate_normal(mu, cov, nsim)
    s = s[s[:, 1] < 0.99]
    lr = s[:, 0] / (1 - s[:, 1])
    return [float(np.percentile(lr, 2.5)), float(np.percentile(lr, 97.5))]
out["pa_ols"] = {"short": ci(pa, "lp"), "c": float(c), "long": float(b / (1 - c)), "long_ci": lr_ci(pa), "n": int(len(lv))}
out["pa_iv"] = {"short": ci(pa_iv, "lp"), "c": float(c2), "long": float(b2 / (1 - c2)), "long_ci": lr_ci(pa_iv), "n": int(len(lv))}
out["trend_per_year"] = float(pa.params["trend"])

# 3) 補助金の期間：原油→店頭価格の連動の弱まりと、暫定税率廃止の前後
# (a) 月ごとの連動：前年同月差の店頭価格を原油の前年同月差に回帰（12か月の移動窓）
roll = []
z = d.loc["2017-01":"2026-08"].dropna(subset=["dlp", "dlo"])
for i in range(24, len(z) + 1):
    w = z.iloc[i - 24:i]
    if w.covid.sum() > 12:
        continue
    f = sm.OLS(w["dlpn"], sm.add_constant(w[["dlo"]])).fit()
    roll.append({"month": str(z.index[i - 1]), "beta": float(f.params["dlo"]), "R2": float(f.rsquared)})
pd.DataFrame(roll).to_csv(RES / "passthrough_rolling.csv", index=False)
# (b) 暫定税率の廃止（2025年12月31日）とその前の補助金の拡充：2025年12月〜2026年2月
trend = float(d.loc["2023-01":"2025-11", "dlq"].mean())   # 直前3年の前年同月差の平均（減り続けるトレンド）
ev = d.loc["2025-12":"2026-02", ["dlq", "dlp", "dlpn", "price"]].copy()
ev["dq_vs_trend"] = ev["dlq"] - trend
out["tax_event"] = {"trend_dlq": trend,
                    "months": {str(k): {"dlpn": float(v.dlpn), "dlq": float(v.dlq), "dq_vs_trend": float(v.dq_vs_trend), "price": float(v.price)} for k, v in ev.iterrows()},
                    "avg_dlpn": float(ev.dlpn.mean()), "avg_dq_vs_trend": float(ev.dq_vs_trend.mean()),
                    "implied_eps": float(ev.dq_vs_trend.mean() / ev.dlpn.mean())}
ev.to_csv(RES / "tax_event.csv")

# 4) 頑健性
rob = []
def add(name, df, y="dlq", x="dlp", ins=INS):
    df = df.dropna(subset=[y, x] + ins)
    o = ci(ols(df, y, [x]), x); v = ci(iv(df, y, x, ins), x)
    f = sm.OLS(df[x], sm.add_constant(df[ins])).fit().fvalue
    rob.append({"設定": name, "n": len(df), "OLS": o[0], "OLS_lo": o[1], "OLS_hi": o[2], "IV": v[0], "IV_lo": v[1], "IV_hi": v[2], "第1段階F": float(f)})
base = d.loc["2018-01":"2026-08"]
add("基本（前年同月差・実質・コロナ期を除く）", base[base.covid == 0])
add("補助金の前だけ（2018年1月〜2020年2月）", base.loc[:"2021-12"][base.loc[:"2021-12"].covid == 0])
add("補助金の後だけ（2022年〜）", base.loc["2022-01":])
dd = base.copy(); add("コロナ期も含める", dd)
add("名目価格", base[base.covid == 0], x="dlpn")
add("操作変数＝原油のドル建て価格", base[base.covid == 0], ins=["dlo_usd", "dlo_usd_l1", "dlo_usd_l2"])
add("操作変数＝当月の原油だけ", base[base.covid == 0], ins=["dlo"])
# STL で季節を除いた前月差
s = d.loc["2017-01":"2026-08"].copy()
for v in ["lq", "lp", "lo"]:
    s[v + "_sa"] = s[v] - STL(s[v], period=12, robust=True).fit().seasonal
    s["m" + v] = s[v + "_sa"].diff()
s["mlo_l1"] = s["mlo"].shift(1); s["mlo_l2"] = s["mlo"].shift(2)
s = s[s.covid == 0]
add("季節調整（STL）して前月差", s, y="mlq", x="mlp", ins=["mlo", "mlo_l1", "mlo_l2"])
# 家計調査からの購入量
h = d.loc["2016-01":"2026-08"]
add("家計調査の購入量（支出÷名目価格）", h[h.covid == 0], y="dlh", x="dlpn")
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
out["robust"] = rob.round(3).to_dict(orient="records")

# 記述
y = d.loc["2017-01":"2025-12"]
ann = y.groupby(y.index.year).agg(gas_kl=("gas_kl", "sum"), price=("price", "mean"))
out["annual"] = {int(k): {"gas_mkl": float(v.gas_kl / 1e6), "price": float(v.price)} for k, v in ann.iterrows()}
out["sales_change_2017_2025"] = float(ann.gas_kl.loc[2025] / ann.gas_kl.loc[2017] - 1)
json.dump(out, open(RES / "results.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"model": ["OLS", "IV"], "est": [out["ols"][0], out["iv"][0]], "lo": [out["ols"][1], out["iv"][1]], "hi": [out["ols"][2], out["iv"][2]]}).to_csv(RES / "main_estimates.csv", index=False)
print(json.dumps({k: v for k, v in out.items() if k not in ("robust", "annual")}, ensure_ascii=False, indent=1))
print(rob.round(3).to_string())
print(out["annual"])
