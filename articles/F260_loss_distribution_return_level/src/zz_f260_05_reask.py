"""05 問い直し：記録が何年あれば、分布を見分けられ、100年に1度の額が絞れるのか。
基準ケース（u=650億円、年1.07件）で当てはめた分布を「本当の分布」とみなし、14・35・70・140年分の記録をつくって当てはめ直す。
推定のしかたは2通り：(a) 本当の分布の形を知っている（同じ分布で当てはめる）、(b) 実務のように5つから AIC 最良を選ぶ。"""
import json
import numpy as np, pandas as pd
from zz_f260_common import R, MODELS, NPAR, fit, isf, return_level
S = json.load(open(R / "summary.json"))
U, LAM = S["u_base"], S["lam_base"]
TRUTHS = ["対数正規", "GPD"]
YEARS = [14, 35, 70, 140]
NREP = 300
rows = []
for ti, t in enumerate(TRUTHS):
    par_t = S["base"][t]["par"]; true_rl = return_level(t, par_t, U, LAM, 100)
    for Y in YEARS:
        rng = np.random.default_rng(1000 * ti + Y)
        for rep in range(NREP):
            n = rng.poisson(LAM * Y)
            while n < 5: n = rng.poisson(LAM * Y)
            x = isf(t, par_t, U, 1 - rng.random(n))
            fits = {m: fit(m, x, U) for m in MODELS}
            aic = {m: 2 * NPAR[m] - 2 * fits[m][1] for m in MODELS}
            sel = min(aic, key=aic.get)
            rows.append(dict(truth=t, years=Y, rep=rep, n=n, true_rl100=true_rl, sel=sel,
                             rl_same=return_level(t, fits[t][0], U, n / Y, 100), rl_aic=return_level(sel, fits[sel][0], U, n / Y, 100)))
d = pd.DataFrame(rows); d.to_csv(R / "reask_record_length.csv", index=False)
out = []
for (t, Y), g in d.groupby(["truth", "years"]):
    r = dict(truth=t, years=Y, true_rl100=g.true_rl100.iloc[0], pick_true=float((g.sel == t).mean()))
    for k in ("same", "aic"):
        lo, med, hi = np.nanquantile(g[f"rl_{k}"], [.05, .5, .95])
        r.update({f"{k}_lo": lo, f"{k}_med": med, f"{k}_hi": hi, f"{k}_ratio": hi / lo,
                  f"{k}_within30": float((abs(g[f"rl_{k}"] / g.true_rl100 - 1) <= .3).mean())})
    out.append(r)
o = pd.DataFrame(out); o.to_csv(R / "reask_summary.csv", index=False)
print(o.round(3).to_string())
