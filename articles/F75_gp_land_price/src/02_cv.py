"""3大都市圏の住宅地で、6つのモデルをランダム CV と 20km ブロック CV で比べる（途中結果は results/_parts に保存して再開できる）"""
import sys, time, json
import numpy as np, pandas as pd
from common import RES, AREAS, load, score
from gplib import oof

MODELS = ["knn10", "gp_map", "ridge", "rk", "gp_ard", "lgbm"]
CVS = ["random", "blk20"]
PART = RES / "_parts"; PART.mkdir(exist_ok=True)


def run(d, area, model, cv, tag="main", **kw):
    f = PART / f"{tag}_{area}_{model}_{cv}.npz"
    if f.exists():
        z = np.load(f, allow_pickle=True)
        return z["p"], (z["s"] if z["s"].size else None), list(z["k"])
    t = time.time()
    p, s, k = oof(d, model, cv, **kw)
    np.savez(f, p=p, s=(s if s is not None else np.array([])), k=np.array(k, dtype=object))
    print(f"{tag} {area} {model} {cv} {time.time() - t:.0f}s", flush=True)
    return p, s, k


if __name__ == "__main__":
    d0 = load("住宅地")
    rows, oofs, kern = [], [], []
    for area in AREAS:
        d = d0[d0["area"] == area].reset_index(drop=True)
        o = d[["code", "area", "x_km", "y_km", "y"]].copy()
        for cv in CVS:
            for m in MODELS:
                p, s, k = run(d, area, m, cv)
                rows.append(dict(area=area, model=m, cv=cv, **score(d["y"].values, p, s)))
                o[f"{m}_{cv}"] = p
                if s is not None:
                    o[f"{m}_{cv}_sd"] = s
                    kern += [dict(area=area, model=m, cv=cv, fold=i, kernel=kk) for i, kk in enumerate(k)]
        oofs.append(o)
    pd.DataFrame(rows).to_csv(RES / "cv_scores.csv", index=False)
    pd.concat(oofs).to_csv(RES / "oof_predictions.csv", index=False)
    pd.DataFrame(kern).to_csv(RES / "fold_kernels.csv", index=False)
    print(pd.DataFrame(rows).pivot_table(index=["area", "cv"], columns="model", values="median_ape").round(3))
