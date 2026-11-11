"""本体のシミュレーション：9つの本当の分布 × 9つの件数 × 500回（種288）。R3 は種を変えて同じことをする。"""
import sys, time, numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from zz_f288_common import DISTS, draw, fit_all

NS = [10, 15, 20, 30, 50, 100, 200, 500, 1000]
REPS = 500


def run(seed, reps=REPS, dists=None, ns=None):
    rows = []
    for di, d in enumerate(dists or DISTS):
        for ni, n in enumerate(ns or NS):
            rng = np.random.default_rng([seed, di, ni])
            Y = draw(d, (reps, n), rng)
            r = fit_all(Y)
            df = pd.DataFrame(r)
            df.insert(0, "rep", np.arange(reps))
            df.insert(0, "n", n)
            df.insert(0, "dist", d)
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "results"
    t0 = time.time()
    main = run(288)
    main.to_csv(f"{out}/A_sims_seed288.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
    print("main", len(main), round(time.time() - t0, 1), "s")
    r3 = run(2881)
    r3.to_csv(f"{out}/B_sims_seed2881.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
    print("R3", len(r3), round(time.time() - t0, 1), "s")
