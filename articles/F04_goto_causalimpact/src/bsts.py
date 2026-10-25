"""ベイズ構造時系列（CausalImpact型）を PyMC で：
y_t = level_t + season_m(t) + X_t·β + ε_t,  level_t = level_{t-1} + η_t（ランダムウォーク）
学習月だけで尤度をとり、対象月（2020年7〜12月）は level・季節・共変量から事後予測分布を作る。"""
import numpy as np, pandas as pd, pymc as pm
from common import SEED


def fit_bsts(s, train, target, covars=("x_cases", "emerg"), draws=1000, tune=3000, chains=4, seed=SEED):
    """s: 月次 DataFrame（index=date, 列 y と共変量）。train/target：日付のリスト。
    戻り値：対象月の反実仮想 y のサンプル（draws*chains × len(target)）と要約"""
    idx = pd.date_range(min(train.min(), target.min()), max(train.max(), target.max()), freq="MS")
    s = s.reindex(idx)
    T = len(idx)
    obs = np.isin(idx, train)
    tpos = np.searchsorted(idx, target)
    m = idx.month.values - 1
    X = s[list(covars)].fillna(0).values if covars else np.zeros((T, 0))
    y = s.y.values
    with pm.Model() as model:
        sd_level = pm.HalfNormal("sd_level", 0.05)
        sd_obs = pm.HalfNormal("sd_obs", 0.05)
        lvl0 = pm.Normal("lvl0", y[obs][:12].mean(), 0.5)
        z = pm.Normal("z", 0, 1, shape=T - 1)
        level = pm.Deterministic("level", lvl0 + pm.math.concatenate([[0.0], pm.math.cumsum(z * sd_level)]))
        s_raw = pm.Normal("s_raw", 0, 0.3, shape=11)
        season = pm.Deterministic("season", pm.math.concatenate([s_raw, [-s_raw.sum()]]))
        mu = level + season[m]
        if X.shape[1]:
            beta = pm.Normal("beta", 0, 0.5, shape=X.shape[1])
            mu = mu + pm.math.dot(X, beta)
        mu = pm.Deterministic("mu", mu)
        pm.Normal("y_obs", mu[obs], sd_obs, observed=y[obs])
        tr = pm.sample(draws=draws, tune=tune, chains=chains, target_accept=0.995, random_seed=seed, progressbar=False, nuts_sampler="nutpie")
    post = tr.posterior
    mu_t = post["mu"].values.reshape(-1, T)[:, tpos]
    sd = post["sd_obs"].values.reshape(-1)
    rng = np.random.default_rng(seed)
    ycf = mu_t + rng.normal(0, 1, mu_t.shape) * sd[:, None]
    div = int(tr.sample_stats["diverging"].values.sum())
    import arviz as az
    rh = az.rhat(tr, var_names=["sd_level", "sd_obs", "s_raw"] + (["beta"] if X.shape[1] else []))
    rhat = float(max(np.nanmax(np.asarray(rh[v])) for v in rh.data_vars)) if hasattr(rh, "data_vars") else float(np.nanmax([np.nanmax(np.asarray(rh[v])) for v in ["sd_level", "sd_obs", "s_raw"]]))
    beta = post["beta"].values.reshape(-1, X.shape[1]) if X.shape[1] else np.zeros((len(sd), 0))
    return ycf, dict(divergences=div, rhat_max=rhat), beta


def summarize(ycf, actual_y, days, target):
    """1日あたり log → 月の延べ宿泊者数へ戻して、実績との差を要約"""
    cf = np.exp(ycf) * days[None, :]
    act = np.exp(actual_y) * days
    eff = act[None, :] - cf
    rows = []
    for j, d in enumerate(target):
        rows.append(dict(date=d.strftime("%Y-%m"), actual=act[j], cf_med=np.median(cf[:, j]), cf_lo=np.quantile(cf[:, j], .025),
                         cf_hi=np.quantile(cf[:, j], .975), eff_med=np.median(eff[:, j]), eff_lo=np.quantile(eff[:, j], .025),
                         eff_hi=np.quantile(eff[:, j], .975), eff_pct_med=np.median(act[j] / cf[:, j] - 1) * 100,
                         eff_pct_lo=np.quantile(act[j] / cf[:, j] - 1, .025) * 100, eff_pct_hi=np.quantile(act[j] / cf[:, j] - 1, .975) * 100,
                         p_pos=(eff[:, j] > 0).mean()))
    return pd.DataFrame(rows), cf, eff


def cum(eff, cf, act, mask):
    e = eff[:, mask].sum(1); c = cf[:, mask].sum(1); a = act[mask].sum()
    return dict(actual=a, cf_med=np.median(c), eff_med=np.median(e), eff_lo=np.quantile(e, .025), eff_hi=np.quantile(e, .975),
                pct_med=np.median(a / c - 1) * 100, pct_lo=np.quantile(a / c - 1, .025) * 100, pct_hi=np.quantile(a / c - 1, .975) * 100,
                p_pos=(e > 0).mean())
