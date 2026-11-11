"""03 分析：5つの分布の当てはめ、AIC、100年・200年に1度の損害、年間合計の99%・99.5%点、ブートストラップ、頑健性。"""
import json
import numpy as np, pandas as pd
from zz_f260_common import P, R, MODELS, NPAR, fit, return_level, aggregate_q, dwell, T_NOW, pr
R.mkdir(exist_ok=True)
A_all = pd.read_csv(P / "dataset_A.csv"); B_all = pd.read_csv(P / "dataset_B.csv")
YEARS_A, YEARS_B = 14, 35                     # A：FY2012〜2025、B：FY1991〜2025
U = {"小（約25件）": 300.0, "中（約15件、基準）": 650.0, "大（約10件）": 1300.0}
U_BASE = 650.0

def run(x, u, years, label, agg=True, seed=0):
    x = np.asarray(x, float); x = x[x > u]; n = len(x); lam = n / years
    out = []
    for i, m in enumerate(MODELS):
        par, ll = fit(m, x, u)
        r = dict(case=label, model=m, u=u, n=n, years=years, lam=lam, loglik=ll, aic=2 * NPAR[m] - 2 * ll, par=list(map(float, par)),
                 rl100=return_level(m, par, u, lam, 100), rl200=return_level(m, par, u, lam, 200))
        if agg:
            (q99, q995), mean = aggregate_q(m, par, u, lam, seed=seed + i)
            r.update(agg99=q99, agg995=q995, agg_mean=mean)
        out.append(r)
    d = pd.DataFrame(out); d["daic"] = d.aic - d.aic.min()
    return d

def A(defl="defl_house"): return A_all[A_all.deflator == defl]
def B(defl="defl_house"): return B_all[B_all.deflator == defl]
def uB(defl="defl_house"):
    c = B(defl).cutoff_yen_pd.iloc[0]
    return c * dwell(T_NOW) * pr.loc[2025, defl] / 100 / 1e8

res = []
base = run(A().loss_2025_oku, U_BASE, YEARS_A, "基準：A（2012〜2025年度、14年）u=650億円"); res.append(base)
for k, u in U.items():
    if u != U_BASE: res.append(run(A().loss_2025_oku, u, YEARS_A, f"しきい値{k} u={u:.0f}億円"))
res.append(run(A("cpi_all").loss_2025_oku, U_BASE * pr.loc[2025, "cpi_all"] / pr.loc[2025, "cpi_all"], YEARS_A, "物価をCPI総合に u=650億円"))
a = A(); res.append(run(a[a.name != "平成30年台風21号"].loss_2025_oku, U_BASE, YEARS_A, "最大の事故（2018年台風21号）を抜く u=650億円"))
res.append(run(a[a.peril == "台風"].loss_2025_oku, U_BASE, YEARS_A, "台風だけ u=650億円"))
ub = uB(); res.append(run(B().loss_2025_oku, ub, YEARS_B, f"B：取りこぼしのない大事故（1991〜2025年度、35年）u={ub:.0f}億円"))
ubc = uB("cpi_all"); res.append(run(B("cpi_all").loss_2025_oku, ubc, YEARS_B, f"B・CPI総合 u={ubc:.0f}億円"))
# H4 の比較相手：A を B と同じしきい値で当てはめる（同じ大きさ以上の事故だけで、記録の長さだけが違う）
res.append(run(A().loss_2025_oku, ub, YEARS_A, f"A を B と同じしきい値で u={ub:.0f}億円"))
allres = pd.concat(res, ignore_index=True)
allres.to_csv(R / "fits_all_cases.csv", index=False)
pd.set_option("display.width", 250)
print(allres[["case", "model", "n", "lam", "aic", "daic", "par", "rl100", "rl200", "agg99", "agg995"]].round(3).to_string())

# ---- ブートストラップ（基準・5分布）：事故を復元抽出、件数もポアソンで振る ----
x0 = A().loss_2025_oku.values; x0 = x0[x0 > U_BASE]; n0 = len(x0)
rng = np.random.default_rng(260)
NB = 2000
boot = {m: [] for m in MODELS}; nlist = []
for b in range(NB):
    nb = rng.poisson(n0)
    while nb < 3: nb = rng.poisson(n0)
    xb = rng.choice(x0, nb, replace=True); nlist.append(nb)
    for m in MODELS:
        par, _ = fit(m, xb, U_BASE)
        boot[m].append(return_level(m, par, U_BASE, nb / YEARS_A, 100))
bt = pd.DataFrame(boot); bt.to_csv(R / "bootstrap_rl100_base.csv", index=False)
ci = {m: dict(lo=float(np.nanquantile(bt[m], .05)), med=float(np.nanmedian(bt[m])), hi=float(np.nanquantile(bt[m], .95)),
              ratio=float(np.nanquantile(bt[m], .95) / np.nanquantile(bt[m], .05)), n_nan=int(bt[m].isna().sum())) for m in MODELS}
print(json.dumps(ci, ensure_ascii=False, indent=0))

# ---- 仮説の判定 ----
b = base.set_index("model")
best = b.daic.idxmin()
h1 = b.rl100.max() / b.rl100.min()
close = b[b.daic < 2]
h2_ratio = close.rl100.max() / close.rl100.min() if len(close) >= 2 else np.nan
h2_gap = float(b.daic.drop(best).min())
bB = allres[allres.case.str.startswith("B：")].set_index("model")
h4 = {m: float(bB.loc[m, "rl100"] / b.loc[m, "rl100"] - 1) for m in ["GPD", "パレート"]}
summ = dict(
    n_base=int(n0), lam_base=float(n0 / YEARS_A), u_base=U_BASE, uB=float(ub), nB=int(len(B())), lamB=float(len(B()) / YEARS_B),
    largest=float(x0.max()),
    base=b[["aic", "daic", "rl100", "rl200", "agg99", "agg995", "agg_mean", "par"]].to_dict(orient="index"),
    best=best,
    H1=dict(ratio=float(h1), max_model=b.rl100.idxmax(), min_model=b.rl100.idxmin(), verdict="支持" if h1 >= 2 else ("外れ" if h1 < 1.5 else "どちらでもない")),
    H2=dict(models_daic_lt2=list(close.index), ratio=float(h2_ratio), best=best, gap_to_second=h2_gap,
            verdict="支持" if (len(close) >= 2 and h2_ratio >= 1.5) else ("外れ" if h2_gap >= 4 else "どちらでもない")),
    H3=dict(model=best, **ci[best], verdict="支持" if ci[best]["ratio"] >= 3 else ("外れ" if ci[best]["ratio"] < 2 else "どちらでもない")),
    H4=dict(diff=h4, verdict="支持" if all(abs(v) >= .3 for v in h4.values()) else ("外れ" if all(abs(v) < .15 for v in h4.values()) else "どちらでもない")),
    boot_ci=ci, boot_mean_n=float(np.mean(nlist)),
)
# 頑健性の要約：ケースごとに 100年に1度の 最大÷最小 と AIC 最良
rob = []
for c, d in allres.groupby("case", sort=False):
    d = d.set_index("model")
    rob.append(dict(case=c, n=int(d.n.iloc[0]), best=d.daic.idxmin(), best_rl100=float(d.loc[d.daic.idxmin(), "rl100"]),
                    min_rl100=float(d.rl100.min()), max_rl100=float(d.rl100.max()), ratio=float(d.rl100.max() / d.rl100.min()),
                    n_daic_lt2=int((d.daic < 2).sum()), **{f"rl100_{m}": float(d.loc[m, "rl100"]) for m in MODELS}))
rob = pd.DataFrame(rob); rob.to_csv(R / "robustness.csv", index=False)
print(rob.round(2).to_string())
summ["robustness"] = rob.to_dict(orient="records")
json.dump(summ, open(R / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in summ.items() if k in ("H1", "H2", "H3", "H4", "best")}, ensure_ascii=False, indent=0, default=float))
