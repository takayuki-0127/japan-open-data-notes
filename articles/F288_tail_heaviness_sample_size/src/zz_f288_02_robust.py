"""頑健性 R4（対数正規の損害の上位を超過額として使う）と R5（要の組み合わせを2,000回）。"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from zz_f288_common import draw_ln_exceed, fit_all
from zz_f288_01_sim import run, NS

out = sys.argv[1] if len(sys.argv) > 1 else "results"
rows = []
for qi, q in enumerate([0.80, 0.90, 0.95]):
    for ni, n in enumerate(NS):
        rng = np.random.default_rng([2884, qi, ni])
        Y = draw_ln_exceed(1.5, q, (500, n), rng)
        df = pd.DataFrame(fit_all(Y))
        df.insert(0, "rep", np.arange(500)); df.insert(0, "n", n); df.insert(0, "q", q)
        rows.append(df)
pd.concat(rows).to_csv(f"{out}/C_r4_ln15_threshold.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
r5 = run(2885, reps=2000, dists=["exp", "ln1.5", "gpd0.4", "gpd0.5"], ns=[15, 30, 50, 100])
r5.to_csv(f"{out}/D_r5_2000reps.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
print("ok", len(r5))
