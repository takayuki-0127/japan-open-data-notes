"""各地域の住宅地すべてで地図のガウス過程を推定し、格子で予測（平均と不確実性）を出す"""
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
from common import RES, AREAS, load
from gplib import gp_fit_predict, kernel, model_fit_predict

d0 = load("住宅地")
rows = []
for area in AREAS:
    d = d0[d0["area"] == area].reset_index(drop=True)
    XY, y = d[["x_km", "y_km"]].values, d["y"].values
    x0, x1 = np.percentile(XY[:, 0], [0.5, 99.5]); y0, y1 = np.percentile(XY[:, 1], [0.5, 99.5])
    gx, gy = np.meshgrid(np.arange(x0, x1, 1.0), np.arange(y0, y1, 1.0))
    G = np.c_[gx.ravel(), gy.ravel()]
    dist, _ = cKDTree(XY).query(G)
    mu, sd, k = gp_fit_predict(XY, y, G, kernel("matern15"), n_hyper=1500)
    np.savez(RES / f"grid_{area}.npz", gx=gx, gy=gy, mu=mu.reshape(gx.shape), sd=sd.reshape(gx.shape),
             dist=dist.reshape(gx.shape))
    p = k.get_params()
    amp, ls, noise = p["k1__k1__constant_value"], p["k1__k2__length_scale"], p["k2__noise_level"]
    var_y = np.var(y)
    rows.append(dict(area=area, n=len(d), kernel=str(k), amplitude=amp, length_scale_km=ls, nugget=noise,
                     # normalize_y=True なので分散の比で「空間でなめらかに説明できる割合」を出す
                     spatial_share=amp / (amp + noise), sd_y=np.sqrt(var_y),
                     corr_at_1km=None, corr_at_5km=None))
    from sklearn.gaussian_process.kernels import Matern
    m = Matern(length_scale=ls, nu=1.5)
    for r in (1, 5):
        rows[-1][f"corr_at_{r}km"] = float(m(np.array([[0, 0]]), np.array([[r, 0]]))[0, 0])
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(RES / "kernel_full.csv", index=False)
