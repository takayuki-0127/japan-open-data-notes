"""03 当てはめ：帰無モデル・共変量つき・診療種別・頑健性。結果は results/ に保存"""
import json, sys, time
import numpy as np, pandas as pd, arviz as az, pymc as pm
import statsmodels.formula.api as smf
from common import RES, SEED
from importlib import import_module
M = import_module("02_model")

out = {}
def run(name, scheme="kokuho", col="idx_total", years=(2021, 2022, 2023), save=False, **kw):
    t = time.time()
    d, prefs, munis = M.prep(scheme, col, years)
    m = M.build(d, len(prefs), len(munis), **kw)
    idata = M.fit(m)
    r = M.shares(idata); r["rhat_max"], r["ess_min"] = M.diag(idata); r["n_obs"] = len(d); r["n_muni"] = len(munis)
    out[name] = r
    print(name, {k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()}, f"{time.time()-t:.0f}s", flush=True)
    if save:
        idata.to_netcdf(RES / f"idata_{name}.nc")
    return d, prefs, munis, idata

# 1. 帰無モデル（県と市区町村の差だけ）
d, prefs, munis, idn = run("null", save=True)
# 2. 共変量つき
d2, _, _, idf = run("full", covariates=True, save=True)
p = idf.posterior
for k, nm in enumerate(["病床数（県、人口10万対）", "65歳以上割合（県）"]):
    v = p["beta_pref"][..., k].values.ravel(); out.setdefault("beta", {})[nm] = [float(v.mean()), float(np.quantile(v, .025)), float(np.quantile(v, .975))]
for k, nm in enumerate(["人口（log）", "人口密度（log）", "人口増減率"]):
    v = p["beta_muni"][..., k].values.ravel(); out["beta"][nm] = [float(v.mean()), float(np.quantile(v, .025)), float(np.quantile(v, .975))]
# 事後予測
with M.build(d, len(prefs), len(munis)):
    ppc = pm.sample_posterior_predictive(idn, random_seed=SEED, progressbar=False)
yrep = ppc.posterior_predictive["y"].values.reshape(-1, len(d))
np.save(RES / "ppc_null_sub.npy", yrep[::20])
# 3. 診療種別（入院・入院外・歯科）
for col in ["idx_in", "idx_out", "idx_dental"]:
    run(f"null_{col}", col=col)
# 4. 頑健性
run("prior_halfcauchy", prior="halfcauchy")
run("prior_exponential", prior="exponential")
run("year2023_only", years=(2023,))
run("year2021_only", years=(2021,))
run("homoscedastic", hetero=False)
run("kouki", scheme="kouki", save=True)
# 5. 頻度論の混合モデル（参考）：県のランダム切片＋市区町村の分散成分、年は固定効果
dd = d.copy(); dd["year"] = dd["fy"].astype(str); dd["code"] = dd["code"].astype(str)
mm = smf.mixedlm("y ~ year", dd, groups="pref", re_formula="1", vc_formula={"muni": "0 + C(code)"}).fit(reml=True)
va, vb = float(mm.cov_re.iloc[0, 0]), float(mm.vcomp[0])
out["mixedlm"] = {"note": "ぶれを人口で調整しない（等分散）","var_pref": va, "var_muni": vb, "pref_share": va / (va + vb), "resid_var": float(mm.scale)}
print("mixedlm", out["mixedlm"])
json.dump(out, open(RES / "fit_summary.json", "w"), ensure_ascii=False, indent=1)
