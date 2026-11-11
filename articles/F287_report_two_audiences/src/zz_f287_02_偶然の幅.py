"""02 偶然の幅：本当の動きを入れない合成データを40通り作り、FY2025 の前年比の揺れから90%の半幅を測る。"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from zz_f287_common import gen, kpis, DEPTS, FY25
OUT = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(OUT, exist_ok=True)


def bands_for(n=12, reps=40, base_seed=10000):
    ds, dg, ss, sc = [], [], [], []
    for r in range(reps):
        g = kpis(gen(base_seed + r, n, with_events=False))
        co = g["co"]
        for m in FY25:
            ms, py = str(m), str(m - 12)
            cs = (co.loc[ms, "sales"] / co.loc[py, "sales"] - 1) * 100
            cc = (co.loc[ms, "cust"] / co.loc[py, "cust"] - 1) * 100
            cg = co.loc[ms, "gp"] / co.loc[ms, "sales"] * 100 - co.loc[py, "gp"] / co.loc[py, "sales"] * 100
            for d in DEPTS:
                x, xp = g["dept"].loc[(d, ms)], g["dept"].loc[(d, py)]
                ds.append((x.sales / xp.sales - 1) * 100 - cs)
                dg.append(x.gp / x.sales * 100 - xp.gp / xp.sales * 100)  # 粗利率は前年差そのもの（トレンドなし）
            for s in g["size"].index:
                x, xp = g["store"].loc[(s, ms)], g["store"].loc[(s, py)]
                ss.append((x.sales / xp.sales - 1) * 100 - cs)
                sc.append((x.cust / xp.cust - 1) * 100 - cc)
    # 全社の前年比からのずれ（絶対値）の90%点＝偶然の幅（両側90%）
    h = lambda a: float(np.percentile(np.abs(np.array(a)), 90))
    return dict(dept_sales=h(ds), dept_gpr=h(dg), store_sales=h(ss), store_cust=h(sc), n_obs=len(ss))


if __name__ == "__main__":
    out = {str(n): bands_for(n) for n in [6, 12, 24]}
    json.dump(out, open(os.path.join(OUT, "bands.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out["12"], ensure_ascii=False))
