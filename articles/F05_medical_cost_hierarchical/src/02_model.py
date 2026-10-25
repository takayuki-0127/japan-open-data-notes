"""02 階層ベイズモデルの定義（PyMC）と、当てはめの共通関数

y[i,t] = 100 × (地域差指数 − 1)  … 全国平均を0とした「年齢をそろえた医療費の高さ（%）」
y[i,t] = mu + g[t] + a[県] + b[市区町村] + (共変量) + e[i,t]
  a ~ N(0, sigma_pref)、b ~ N(0, sigma_muni)：県の差と、同じ県の中の市区町村の差（毎年続く差）
  e ~ N(0, sigma_noise × sqrt(人口の中央値 / 人口))：年ごとのぶれ。人口が小さい町ほど大きい
"""
import numpy as np, pandas as pd, pymc as pm, arviz as az
from common import DATA, SEED


def prep(scheme="kokuho", col="idx_total", years=(2021, 2022, 2023)):
    d = pd.read_csv(DATA / "panel.csv")
    d = d[(d["scheme"] == scheme) & d["fy"].isin(years)].dropna(subset=[col, "pop2020", "density", "chg_rate"]).copy()
    d["y"] = 100 * (d[col] - 1)
    d["pref_i"], prefs = pd.factorize(d["pref"], sort=True)
    d["muni_i"], munis = pd.factorize(d["code"], sort=True)
    d["year_i"] = d["fy"].map({y: k for k, y in enumerate(sorted(years))})
    d["w"] = np.sqrt(d["pop2020"].median() / d["pop2020"])
    return d, list(prefs), list(munis)


def zs(x):
    return (x - x.mean()) / x.std()


def build(d, n_pref, n_muni, covariates=False, prior="halfnormal", hetero=True):
    years = d["year_i"].nunique()
    with pm.Model() as m:
        mu = pm.Normal("mu", 0, 10)
        g = pm.Normal("g_raw", 0, 5, shape=years - 1) if years > 1 else None
        if prior == "halfnormal":
            sa, sb, se = (pm.HalfNormal(n, 10) for n in ("sigma_pref", "sigma_muni", "sigma_noise"))
        elif prior == "halfcauchy":
            sa, sb, se = (pm.HalfCauchy(n, 2) for n in ("sigma_pref", "sigma_muni", "sigma_noise"))
        else:  # exponential
            sa, sb, se = (pm.Exponential(n, 0.2) for n in ("sigma_pref", "sigma_muni", "sigma_noise"))
        a_mean = 0
        mu_i = 0
        if covariates:
            pc = d.groupby("pref_i")[["beds_per100k", "aged65_share_2023"]].first().sort_index()
            Xp = np.column_stack([zs(pc[c]).values for c in pc.columns])
            bp = pm.Normal("beta_pref", 0, 5, shape=Xp.shape[1])
            a_mean = pm.math.dot(Xp, bp)
            mc = d.groupby("muni_i")[["pop2020", "density", "chg_rate"]].first().sort_index()
            Xm = np.column_stack([zs(np.log(mc["pop2020"])), zs(np.log1p(mc["density"])), zs(mc["chg_rate"].clip(-40, 40))])
            bm = pm.Normal("beta_muni", 0, 5, shape=Xm.shape[1])
            mu_i = pm.math.dot(Xm, bm)
        # 切片 mu と a・b の平均が入れ替わらないよう、a と b は合計0の正規分布（ZeroSumNormal）で置く
        a = pm.Deterministic("a", a_mean + pm.ZeroSumNormal("a_dev", sigma=sa, shape=n_pref))
        b = pm.Deterministic("b", mu_i + pm.ZeroSumNormal("b_dev", sigma=sb, shape=n_muni))
        eta = mu + a[d["pref_i"].values] + b[d["muni_i"].values]
        if g is not None:
            gfull = pm.math.concatenate([[0.0], g])
            eta = eta + gfull[d["year_i"].values]
        sd = se * (d["w"].values if hetero else 1.0)
        pm.Normal("y", eta, sd, observed=d["y"].values)
    return m


def fit(m, draws=1500, tune=1000, chains=2):
    with m:
        idata = pm.sample(draws=draws, tune=tune, chains=chains, cores=2, random_seed=SEED, target_accept=0.9, progressbar=False)
    return idata


def shares(idata):
    p = idata.posterior
    va, vb = p["sigma_pref"] ** 2, p["sigma_muni"] ** 2
    s = (va / (va + vb)).values.ravel()
    return {"sigma_pref": float(p["sigma_pref"].mean()), "sigma_muni": float(p["sigma_muni"].mean()),
            "sigma_noise": float(p["sigma_noise"].mean()),
            "pref_share": float(s.mean()), "pref_share_lo": float(np.quantile(s, .025)), "pref_share_hi": float(np.quantile(s, .975))}


def diag(idata):
    s = az.summary(idata, var_names=["mu", "sigma_pref", "sigma_muni", "sigma_noise"])
    return float(s["r_hat"].max()), float(s["ess_bulk"].min())
