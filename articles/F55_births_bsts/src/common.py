"""F55 共通：パス・図の体裁・データ・ベイズ構造時系列（BSTS）と SARIMA の当てはめと将来シミュレーション

y は log(1日あたり出生数)。
BSTS：y_t = μ_t + γ_{m(t)} + ε_t
      μ_t = μ_{t-1} + δ_{t-1} + η_t   （水準）
      δ_t = δ_{t-1} + ζ_t             （傾き）
      γ は12か月の季節（合計0）。オプションで季節も少しずつ動く形にできる。
PyMC で事後分布を出し、各サンプルから将来を前向きにシミュレーションして予測分布を作る。
"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("pymc").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA, FIG, RES = ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, LORANGE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#f6c3ab"
SOURCE = "出典：厚生労働省「人口動態統計（確定数）」（e-Stat）をもとに作成者が加工して作成"
SEED = 55
NSIM = 4000

# 事前分布（標準偏差の HalfNormal の尺度）。単位は log(1日あたり出生数) の1か月あたり
PRIORS = {
    "base":  {"sig_level": 0.01,  "sig_slope": 0.001,  "sig_obs": 0.05},
    "tight": {"sig_level": 0.003, "sig_slope": 0.0002, "sig_obs": 0.05},
    "loose": {"sig_level": 0.03,  "sig_slope": 0.005,  "sig_obs": 0.05},
}


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def monthly():
    d = pd.read_csv(DATA / "monthly.csv", parse_dates=["date"]).set_index("date").asfreq("MS")
    d["y"] = np.log(d["births_per_day"])
    return d


def days_in(index):
    return np.asarray(pd.DatetimeIndex(index).days_in_month)


def future_index(last, h):
    return pd.date_range(last + pd.offsets.MonthBegin(), periods=h, freq="MS")


# ---------------- BSTS ----------------
def fit_bsts(y, prior="base", slope=True, seas_rw=False, draws=1000, tune=1000, chains=2, seed=SEED):
    """PyMC で BSTS を当てはめる。返り値は事後サンプルの dict（numpy）"""
    import pymc as pm
    p = PRIORS[prior] if isinstance(prior, str) else prior
    yv = np.asarray(y, float)
    T = len(yv)
    mon = np.asarray(pd.DatetimeIndex(y.index).month) - 1
    with pm.Model():
        s_lev = pm.HalfNormal("s_lev", p["sig_level"])
        s_obs = pm.HalfNormal("s_obs", p["sig_obs"])
        l0 = pm.Normal("l0", yv[:12].mean(), 0.3)
        z_l = pm.Normal("z_l", 0, 1, shape=T - 1)
        if slope:
            s_slp = pm.HalfNormal("s_slp", p["sig_slope"])
            d0 = pm.Normal("d0", 0, 0.01)
            z_s = pm.Normal("z_s", 0, 1, shape=T - 1)
            dlt = pm.math.concatenate([[d0], d0 + pm.math.cumsum(s_slp * z_s)])     # δ_0..δ_{T-1}
            steps = dlt[:-1] + s_lev * z_l
        else:
            steps = s_lev * z_l
        mu = pm.math.concatenate([[l0], l0 + pm.math.cumsum(steps)])
        g_raw = pm.Normal("g_raw", 0, 0.1, shape=11)
        g0 = pm.math.concatenate([g_raw, [-pm.math.sum(g_raw)]])                     # 合計0
        if seas_rw:
            # 季節を年ごとに少しずつ動かす（各月の効果が年単位のランダムウォーク）
            nyr = int(np.ceil(T / 12))
            s_sea = pm.HalfNormal("s_sea", 0.005)
            z_g = pm.Normal("z_g", 0, 1, shape=(nyr - 1, 12))
            zc = z_g - z_g.mean(axis=1, keepdims=True)
            G = pm.math.concatenate([g0[None, :], g0[None, :] + pm.math.cumsum(s_sea * zc, axis=0)], axis=0)
            yr = np.arange(T) // 12
            season = G[yr, mon]
        else:
            season = g0[mon]
        pm.Normal("obs", mu + season, s_obs, observed=yv)
        pm.Deterministic("mu", mu)
        if slope:
            pm.Deterministic("dlt", dlt)
        if seas_rw:
            pm.Deterministic("G_last", G[-1])
        else:
            pm.Deterministic("G_last", g0)
        try:
            idata = pm.sample(draws=draws, tune=tune, chains=chains, cores=chains, random_seed=seed,
                              nuts_sampler="nutpie", progressbar=False, target_accept=0.95)
        except Exception:
            idata = pm.sample(draws=draws, tune=tune, chains=chains, cores=chains, random_seed=seed,
                              progressbar=False, target_accept=0.95)
    post = idata.posterior
    out = {k: post[k].values.reshape(-1, *post[k].shape[2:]) for k in
           ["s_lev", "s_obs", "mu", "G_last"] + (["s_slp", "dlt"] if slope else []) + (["s_sea"] if seas_rw else [])}
    import arviz as az
    summ = az.summary(idata, var_names=["s_lev", "s_obs"] + (["s_slp"] if slope else []) + (["s_sea"] if seas_rw else []),
                      kind="diagnostics")
    out["rhat_max"] = float(summ["r_hat"].max())
    out["ess_min"] = float(summ["ess_bulk"].min())
    out["slope"], out["seas_rw"], out["T"], out["last_month"] = slope, seas_rw, T, int(mon[-1])
    return out


def sim_bsts(post, h, nsim=NSIM, seed=SEED, noise=True):
    """事後サンプルから h か月先までを前向きにシミュレーション。返り値 (h, nsim) の log(1日あたり)"""
    rng = np.random.default_rng(seed)
    n = len(post["s_lev"])
    idx = rng.integers(0, n, nsim)
    mu = post["mu"][idx, -1].copy()
    s_lev, s_obs = post["s_lev"][idx], post["s_obs"][idx]
    if post["slope"]:
        d = post["dlt"][idx, -1].copy(); s_slp = post["s_slp"][idx]
    G = post["G_last"][idx].copy()                      # (nsim, 12)
    if post["seas_rw"]:
        s_sea = post["s_sea"][idx]
    m0 = post["last_month"]
    out = np.empty((h, nsim))
    for k in range(h):
        m = (m0 + 1 + k) % 12
        if post["seas_rw"] and m == 0:
            z = rng.standard_normal((nsim, 12)); z -= z.mean(1, keepdims=True)
            G = G + s_sea[:, None] * z
        if post["slope"]:
            mu = mu + d + s_lev * rng.standard_normal(nsim)
            d = d + s_slp * rng.standard_normal(nsim)
        else:
            mu = mu + s_lev * rng.standard_normal(nsim)
        out[k] = mu + G[:, m] + (s_obs * rng.standard_normal(nsim) if noise else 0)
    return out


# ---------------- SARIMA（F02 と同じ形） ----------------
def sim_sarima(y, h, nsim=NSIM, seed=SEED):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    m = SARIMAX(y, order=(1, 1, 1), seasonal_order=(0, 1, 1, 12)).fit(disp=False)
    sims = np.asarray(m.simulate(h, repetitions=nsim, anchor="end", rng=np.random.default_rng(seed))).reshape(h, -1)
    return sims


# ---------------- 評価 ----------------
def crps_ens(sims, obs):
    """アンサンブルの CRPS（各行＝各月）。sims (h, n), obs (h,)"""
    s = np.sort(sims, axis=1)
    n = s.shape[1]
    t1 = np.mean(np.abs(s - obs[:, None]), axis=1)
    i = np.arange(1, n + 1)
    t2 = np.sum((2 * i - n - 1) * s, axis=1) / (n * n)
    return t1 - t2


def interval(sims, lev):
    a = (1 - lev) / 2
    return np.quantile(sims, a, axis=1), np.quantile(sims, 1 - a, axis=1)
