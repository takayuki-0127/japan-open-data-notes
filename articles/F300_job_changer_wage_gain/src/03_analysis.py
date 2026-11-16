"""H1〜H4 と頑健性。結果は results/ に書く（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
wc = pd.read_csv(ROOT / "data" / "wage_change_by_age.csv")
wa = pd.read_csv(ROOT / "data" / "age_weights.csv")
hr = pd.read_csv(ROOT / "data" / "jobs_ratio_annual.csv")
AGES = ["u19", "20_29", "30_44", "45_59", "60p"]
r3 = lambda x: round(float(x), 3)

def period_mean(df, years, col):
    return df[df.year.isin(years)].groupby("age", sort=True)[col].mean()

def shift_share(start, end, var="up10", wcol="w_movers", ages=AGES):
    s0, s1 = period_mean(wc, start, var)[ages], period_mean(wc, end, var)[ages]
    w0, w1 = period_mean(wa, start, wcol)[ages], period_mean(wa, end, wcol)[ages]
    w0, w1 = w0 / w0.sum(), w1 / w1.sum()
    tot0, tot1 = float((w0 * s0).sum()), float((w1 * s1).sum())
    within = float((w0 * (s1 - s0)).sum())        # 重みを始めに固定
    within_end = float((w1 * (s1 - s0)).sum())    # 重みを終わりに固定
    comp = float(((w1 - w0) * s0).sum())
    inter = float(((w1 - w0) * (s1 - s0)).sum())
    obs0 = float(wc[(wc.age == "all") & wc.year.isin(start)][var].mean())
    obs1 = float(wc[(wc.age == "all") & wc.year.isin(end)][var].mean())
    return dict(start=f"{start[0]}-{start[-1]}", end=f"{end[0]}-{end[-1]}", var=var, weights=wcol, ages="+".join(ages),
                observed_start=r3(obs0), observed_end=r3(obs1), observed_change=r3(obs1 - obs0),
                implied_start=r3(tot0), implied_end=r3(tot1), implied_change=r3(tot1 - tot0),
                within_fixed_start=r3(within), within_fixed_end=r3(within_end), composition=r3(comp), interaction=r3(inter),
                within_share_of_implied=r3(within / (tot1 - tot0)) if tot1 != tot0 else None)

S, E = [2007, 2008, 2009], [2023, 2024, 2025]
out = {}
# ---------- H1 ----------
h1 = shift_share(S, E)
out["H1"] = h1
out["H1_verdict"] = "支持" if h1["within_fixed_start"] >= 0.7 * h1["implied_change"] else "外れ"
# 年齢構成（重み）の変化
w0, w1 = period_mean(wa, S, "w_movers"), period_mean(wa, E, "w_movers")
out["weights_start"] = {a: r3(w0[a]) for a in AGES}; out["weights_end"] = {a: r3(w1[a]) for a in AGES}
# 近似の確かめ：重みから組み立てた全体の割合と、公表の「計」のずれ
chk = []
for y in range(1993, 2026):
    s = wc[(wc.year == y)].set_index("age")
    ww = wa[wa.year == y].set_index("age")
    chk.append(dict(year=y, observed=float(s.loc["all", "up10"]), implied=float((ww.w_movers * s.loc[AGES, "up10"]).sum())))
chk = pd.DataFrame(chk); chk["gap"] = chk.implied - chk.observed
chk.round(3).to_csv(RES / "weights_check.csv", index=False)
out["weights_check_mean_abs_gap_2007_2025"] = r3(chk[chk.year >= 2007].gap.abs().mean())
out["weights_check_max_abs_gap_2007_2025"] = r3(chk[chk.year >= 2007].gap.abs().max())

# ---------- H2 ----------
s0, s1 = period_mean(wc, S, "up10"), period_mean(wc, E, "up10")
h2 = {a: dict(start=r3(s0[a]), end=r3(s1[a]), change=r3(s1[a] - s0[a])) for a in AGES + ["all"]}
out["H2"] = h2
out["H2_verdict"] = "支持" if all(h2[a]["change"] >= 3 for a in ["20_29", "30_44", "45_59", "60p"]) else "外れ"
pd.DataFrame([{"age": a, **h2[a]} for a in AGES + ["all"]]).to_csv(RES / "h2_by_age.csv", index=False)

# ---------- H3：景気 ----------
ts = wc[wc.age == "all"].merge(hr, on="year").sort_values("year").reset_index(drop=True)
ts["net"] = ts.up10 - ts.down10
ts["jobs_ratio_lag1"] = ts.jobs_ratio.shift(1)
ts.to_csv(RES / "timeseries_all.csv", index=False, float_format="%.4f")
def tsreg(y, xs, y0=2007, y1=2025, diff=False):
    d = ts[(ts.year >= y0) & (ts.year <= y1)].copy()
    if diff:
        d = d[[y] + xs].diff().dropna()
        X = sm.add_constant(d[xs])
    else:
        d["trend"] = d.year - y0
        X = sm.add_constant(d[xs + ["trend"]])
        d = d.dropna(subset=xs)
        X = X.loc[d.index]
    m = sm.OLS(d[y], X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    x = xs[0]
    return dict(y=y, x=x, period=f"{y0}-{y1}", diff=diff, n=int(m.nobs), coef=r3(m.params[x]), se=r3(m.bse[x]), p=r3(m.pvalues[x]),
                trend=(r3(m.params["trend"]) if "trend" in m.params else None), r2=r3(m.rsquared))
h3 = tsreg("up10", ["jobs_ratio"])
out["H3"] = h3
out["H3_verdict"] = "支持" if (h3["coef"] > 0 and h3["p"] < 0.05) else "外れ"
d = ts[(ts.year >= 2007)]
out["corr_up10_jobsratio_2007_2025"] = r3(np.corrcoef(d.up10, d.jobs_ratio)[0, 1])
# 2020年の落ち込みの大きさ（参考）
out["up10_2019"], out["up10_2020"], out["up10_2025"] = r3(ts.set_index("year").up10[2019]), r3(ts.set_index("year").up10[2020]), r3(ts.set_index("year").up10[2025])
out["jobs_ratio_2019"], out["jobs_ratio_2020"], out["jobs_ratio_2025"] = r3(ts.set_index("year").jobs_ratio[2019]), r3(ts.set_index("year").jobs_ratio[2020]), r3(ts.set_index("year").jobs_ratio[2025])

# ---------- H4：差し引き ----------
net0 = float(ts[ts.year.isin(S)].net.mean()); net1 = float(ts[ts.year.isin(E)].net.mean())
out["H4"] = dict(net_start=r3(net0), net_end=r3(net1), change=r3(net1 - net0),
                 down10_start=r3(ts[ts.year.isin(S)].down10.mean()), down10_end=r3(ts[ts.year.isin(E)].down10.mean()),
                 within10_start=r3(ts[ts.year.isin(S)].within10.mean()), within10_end=r3(ts[ts.year.isin(E)].within10.mean()))
out["H4_verdict"] = "支持" if net1 - net0 >= 5 else "外れ"

# ---------- 頑健性 ----------
rob = []
def add(name, d, kind):
    rob.append({"spec": name, "kind": kind, **d})
add("主（H1）", h1, "H1")
add("R1 期間を1999年から（1999-2001 → 2023-2025）", shift_share([1999, 2000, 2001], E), "H1")
add("R2 重みを終わりに固定", {**h1, "within_fixed_start": h1["within_fixed_end"]}, "H1")
add("R3 重みを就業者数だけに", shift_share(S, E, wcol="w_employed"), "H1")
add("R4 19歳以下を除く", shift_share(S, E, ages=["20_29", "30_44", "45_59", "60p"]), "H1")
add("R6 2時点を 2010-2012 → 2023-2025", shift_share([2010, 2011, 2012], E), "H1")
add("R7 差し引き（増加−減少）で分解（追加）", {}, "H1")  # 下で差し引きの分解に置き換える
# R7 は差し引きの分解にする
net_wc = wc.copy(); net_wc["net"] = net_wc.up10 - net_wc.down10
wc_backup = wc
wc = net_wc
rob[-1] = {"spec": "R7 差し引き（増加−減少）で分解（追加）", "kind": "H1", **shift_share(S, E, var="net")}
wc = wc_backup
rob_df = pd.DataFrame(rob)
rob_df.to_csv(RES / "robustness_h1.csv", index=False)
out["robustness_h1"] = rob
h3r = [h3, tsreg("up10", ["jobs_ratio_lag1"]), tsreg("up10", ["jobs_ratio"], diff=True), tsreg("up10", ["jobs_ratio"], y0=1999),
       tsreg("net", ["jobs_ratio"])]
pd.DataFrame(h3r).to_csv(RES / "robustness_h3.csv", index=False)
out["robustness_h3"] = h3r
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("robustness_h1",)}, ensure_ascii=False, indent=0))
print(rob_df[["spec", "observed_change", "implied_change", "within_fixed_start", "composition", "interaction"]].to_string())
