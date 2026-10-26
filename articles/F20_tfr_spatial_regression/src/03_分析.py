"""03 分析：OLS → 残差の Moran's I → LM 検定 → 空間ラグ（SAR）・空間誤差（SEM）→ 直接・間接効果 → GWR → 頑健性"""
import json
import warnings
import numpy as np
import pandas as pd
import libpysal
from libpysal.weights import W, KNN, DistanceBand
from esda.moran import Moran
import spreg
from mgwr.gwr import GWR
from mgwr.sel_bw import Sel_BW
from common import DATA, RES, SEED, load_topo, to_km

warnings.filterwarnings("ignore")
np.random.seed(SEED)

X_MAIN = ["young_f", "income", "commute_out", "nursery", "tertiary", "density"]
LABEL = {"young_f": "15〜39歳女性の割合", "income": "納税者1人あたり所得（対数）", "commute_out": "市区町村外への通勤・通学の割合",
         "nursery": "0〜5歳千人あたり保育所数", "tertiary": "第3次産業就業者の割合", "density": "可住地の人口密度（対数）",
         "unmarried": "未婚者の割合", "owner": "持ち家の割合", "floor": "1住宅あたり延べ面積"}

rings, used = load_topo()
cent = {c: np.vstack(r).mean(axis=0) for c, r in rings.items()}


def sample(period, xs, drop_big=False):
    df = pd.read_csv(DATA / f"municipal_{period}.csv", dtype={"code": str, "pref": str}).set_index("code")
    df = df[(df["pop"] > 0)].replace([np.inf, -np.inf], np.nan).dropna(subset=["tfr"] + xs)
    df = df[df.index.isin(rings.keys())]
    if drop_big:
        ix = pd.Series(df.index, index=df.index)
        big = ix.str[2].eq("1") | ix.str.startswith("131")
        df = df[~big]
    return df


def queen(codes):
    codes = list(codes)
    owner = {}
    for c in codes:
        for a in used[c]:
            owner.setdefault(a, set()).add(c)
    nb = {c: set() for c in codes}
    for s in owner.values():
        for c in s:
            nb[c] |= s - {c}
    xy = np.array([cent[c] for c in codes])
    kx, ky = to_km(xy[:, 0], xy[:, 1])
    P = np.c_[kx, ky]
    n_island = 0
    for i, c in enumerate(codes):
        if not nb[c]:  # 島などで接する区域がない → いちばん近い1区域を隣とする
            dd = np.hypot(*(P - P[i]).T)
            dd[i] = np.inf
            nb[c] = {codes[int(np.argmin(dd))]}
            n_island += 1
    for c in codes:  # 対称にする
        for o in list(nb[c]):
            nb[o].add(c)
    w = W({c: sorted(nb[c]) for c in codes}, id_order=codes, silence_warnings=True)
    w.transform = "r"
    return w, P, n_island


def weights(codes, kind):
    w, P, n_island = queen(codes)
    if kind == "queen":
        return w, P, n_island
    if kind == "knn6":
        w2 = KNN(P, k=6, ids=list(codes))
    elif kind == "dist30":
        w2 = DistanceBand(P, threshold=30, binary=False, alpha=-1.0, ids=list(codes), silence_warnings=True)
        # 30km 以内に誰もいない区域は Queen の隣で補う
        neigh = {c: list(w2.neighbors[c]) or list(w.neighbors[c]) for c in codes}
        wts = {c: list(w2.weights[c]) if w2.neighbors[c] else [1.0] * len(w.neighbors[c]) for c in codes}
        w2 = W(neigh, wts, id_order=list(codes), silence_warnings=True)
    w2.transform = "r"
    return w2, P, n_island


def zscore(df, xs):
    Z = df[xs].copy()
    return (Z - Z.mean()) / Z.std(ddof=0)


def impacts(rho, beta, w):
    n = w.n
    Wd = w.full()[0]
    S = np.linalg.inv(np.eye(n) - rho * Wd)
    d_mult = np.trace(S) / n
    t_mult = 1 / (1 - rho)
    return {"direct": beta * d_mult, "indirect": beta * (t_mult - d_mult), "total": beta * t_mult}


def fit(period="2018_22", xs=X_MAIN, wkind="queen", drop_big=False, do_gwr=False, tag="main"):
    df = sample(period, xs, drop_big)
    codes = list(df.index)
    w, P, n_island = weights(codes, wkind)
    y = df[["tfr"]].values
    Z = zscore(df, xs)
    X = Z.values
    out = {"tag": tag, "period": period, "weights": wkind, "n": len(df), "islands_linked": n_island, "x": xs}
    mi_y = Moran(df["tfr"].values, w, permutations=999)
    out["moran_y"] = [float(mi_y.I), float(mi_y.p_sim)]
    ols = spreg.OLS(y, X, w=w, spat_diag=True, moran=True, name_y="tfr", name_x=xs)
    res = ols.u.flatten()
    mi_r = Moran(res, w, permutations=999)
    out["ols"] = {"beta": ols.betas.flatten().tolist(), "se": np.sqrt(np.diag(ols.vm)).tolist(), "r2": float(ols.r2), "aic": float(ols.aic)}
    out["moran_resid"] = [float(mi_r.I), float(mi_r.p_sim)]
    out["lm"] = {"lm_lag": list(map(float, ols.lm_lag)), "lm_error": list(map(float, ols.lm_error)),
                 "rlm_lag": list(map(float, ols.rlm_lag)), "rlm_error": list(map(float, ols.rlm_error))}
    lag = spreg.ML_Lag(y, X, w=w, name_y="tfr", name_x=xs)
    err = spreg.ML_Error(y, X, w=w, name_y="tfr", name_x=xs)
    out["sar"] = {"beta": lag.betas.flatten().tolist(), "se": np.sqrt(np.diag(lag.vm)).tolist(), "rho": float(lag.rho), "aic": float(lag.aic), "logll": float(lag.logll)}
    out["sem"] = {"beta": err.betas.flatten().tolist(), "se": np.sqrt(np.diag(err.vm)).tolist(), "lambda": float(err.lam), "aic": float(err.aic), "logll": float(err.logll)}
    out["moran_resid_sar"] = float(Moran(lag.u.flatten(), w, permutations=0).I)
    out["moran_resid_sem"] = float(Moran(err.e_filtered.flatten(), w, permutations=0).I)
    if wkind == "queen" and len(df) < 2500:
        b = np.array(lag.betas.flatten()[1:len(xs) + 1])
        im = impacts(lag.rho, b, w)
        out["impacts"] = {k: v.tolist() for k, v in im.items()}
        # 影響の不確かさ：係数と rho を推定の共分散から500回引いて分布を見る
        rng = np.random.default_rng(SEED)
        vm = lag.vm
        k = len(xs) + 1
        idx = list(range(1, k)) + [k]
        draws = rng.multivariate_normal(np.r_[lag.betas.flatten()[1:k], lag.rho], vm[np.ix_(idx, idx)], size=500)
        Wd = w.full()[0]
        ev = np.linalg.eigvals(Wd).real
        sims = []
        for dr in draws:
            r_ = dr[-1]
            dm = np.mean(1 / (1 - r_ * ev))
            tm = 1 / (1 - r_)
            sims.append(np.r_[dr[:-1] * dm, dr[:-1] * (tm - dm)])
        sims = np.array(sims)
        out["impacts_ci"] = {"direct": np.percentile(sims[:, :len(xs)], [2.5, 97.5], axis=0).tolist(),
                             "indirect": np.percentile(sims[:, len(xs):], [2.5, 97.5], axis=0).tolist()}
    if do_gwr:
        bw = Sel_BW(P, y, X, kernel="bisquare", fixed=False).search(criterion="AICc")
        g = GWR(P, y, X, bw, kernel="bisquare", fixed=False).fit()
        tv = g.filter_tvals()
        loc = pd.DataFrame(g.params, index=codes, columns=["const"] + xs)
        loc_t = pd.DataFrame(tv, index=codes, columns=["const"] + xs)
        loc.join(loc_t, rsuffix="_t_filtered").to_csv(RES / f"gwr_local_{tag}.csv", encoding="utf-8")
        sig = (loc_t != 0)
        out["gwr"] = {"bw": int(bw), "aicc": float(g.aicc), "r2": float(g.R2), "ols_aicc": float(spreg.OLS(y, X).aic),
                      "pos_share": {c: float((loc[c] > 0).mean()) for c in xs},
                      "sig_pos_share": {c: float(((loc_t[c] > 0)).mean()) for c in xs},
                      "sig_neg_share": {c: float(((loc_t[c] < 0)).mean()) for c in xs},
                      "q": {c: np.percentile(loc[c], [5, 25, 50, 75, 95]).round(4).tolist() for c in xs},
                      "moran_resid": float(Moran(g.resid_response.flatten(), w, permutations=0).I)}
        # Monte Carlo 的な目安：係数のばらつき（四分位範囲）を GWR の標準誤差の中央値と比べる
        out["gwr"]["iqr_over_se"] = {c: float((np.percentile(loc[c], 75) - np.percentile(loc[c], 25)) / np.median(g.bse[:, i + 1])) for i, c in enumerate(xs)}
    df.assign(ols_resid=res).to_csv(RES / f"data_{tag}.csv", encoding="utf-8")
    return out


if __name__ == "__main__":
    allres = {}
    allres["main"] = fit(do_gwr=True)
    print("main done", allres["main"]["n"])
    runs = [
        dict(wkind="knn6", tag="knn6"),
        dict(wkind="dist30", tag="dist30"),
        dict(period="2013_17", tag="p2013_17"),
        dict(drop_big=True, tag="no_big_city"),
        dict(xs=X_MAIN + ["unmarried"], tag="with_unmarried"),
        dict(xs=X_MAIN + ["owner", "floor"], wkind="knn6", tag="with_housing"),
    ]
    for r in runs:
        allres[r["tag"]] = fit(**r)
        print(r["tag"], allres[r["tag"]]["n"], round(allres[r["tag"]]["sar"]["rho"], 3), round(allres[r["tag"]]["sem"]["lambda"], 3))
    json.dump(allres, open(RES / "results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rows = []
    for tag, o in allres.items():
        for m in ("ols", "sar", "sem"):
            for i, x in enumerate(o["x"]):
                rows.append({"run": tag, "model": m, "x": x, "beta": o[m]["beta"][i + 1], "se": o[m]["se"][i + 1]})
    pd.DataFrame(rows).to_csv(RES / "coefficients.csv", index=False, encoding="utf-8")
