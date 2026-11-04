"""円安（ドル円の上昇）と株高（日経平均の上昇）の依存を、ふつうの相関と裾の依存で比べる。"""
import json
import numpy as np
import pandas as pd
from scipy import stats, optimize
from common import DATA, RES, SEED, PERIODS, QS
import copulas as C

rng = np.random.default_rng(SEED)
d = pd.read_csv(DATA / "returns_daily.csv", parse_dates=["date"])
w = pd.read_csv(DATA / "returns_weekly.csv", parse_dates=["date"])

def pobs(x): return stats.rankdata(x) / (len(x) + 1)

def emp_tail(u, v, q):
    """経験的な裾の依存：両方が上位（下位）1−q に入る割合 ÷ (1−q)。"""
    up = np.mean((u > q) & (v > q)) / (1 - q); lo = np.mean((u <= 1 - q) & (v <= 1 - q)) / (1 - q)
    return up, lo

def block_boot(x, y, fn, B=400, L=20):
    n = len(x); res = []
    for _ in range(B):
        st = rng.integers(0, n - L, size=n // L + 1)
        idx = np.concatenate([np.arange(s, s + L) for s in st])[:n]
        res.append(fn(x[idx], y[idx]))
    return np.array(res)

def gauss_null(rho, n, q, S=400):
    """ふつうの相関だけ（ガウスコピュラ）のとき、同じ標本の大きさで出る経験的な裾の依存の分布。"""
    out = []
    for _ in range(S):
        z = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], n)
        out.append(emp_tail(pobs(z[:, 0]), pobs(z[:, 1]), q))
    return np.array(out)

def basic(x, y):
    return dict(n=len(x), pearson=stats.pearsonr(x, y)[0], spearman=stats.spearmanr(x, y)[0],
                kendall=stats.kendalltau(x, y)[0])

def garch_std(r):
    """GARCH(1,1)（正規）で標準化した残差。"""
    r = r - r.mean(); v0 = r.var()
    def nll(p):
        om, a, b = np.exp(p[0]), 1 / (1 + np.exp(-p[1])), 1 / (1 + np.exp(-p[2]))
        if a + b >= 0.999: return 1e10
        h = np.empty_like(r); h[0] = v0
        for t in range(1, len(r)): h[t] = om + a * r[t - 1]**2 + b * h[t - 1]
        return 0.5 * np.sum(np.log(h) + r**2 / h)
    p = optimize.minimize(nll, [np.log(v0 * 0.05), -2.5, 2.0], method="Nelder-Mead", options={"maxiter": 3000}).x
    om, a, b = np.exp(p[0]), 1 / (1 + np.exp(-p[1])), 1 / (1 + np.exp(-p[2]))
    h = np.empty_like(r); h[0] = v0
    for t in range(1, len(r)): h[t] = om + a * r[t - 1]**2 + b * h[t - 1]
    return r / np.sqrt(h), dict(omega=om, alpha=a, beta=b)

summary = {}
# 1) 全期間・日次：ふつうの相関
x, y = d.r_fx.values, d.r_nk.values
summary["daily_all"] = basic(x, y)
u, v = pobs(x), pobs(y)
rho_n = 2 * np.sin(np.pi * summary["daily_all"]["kendall"] / 6) * 0 + np.sin(np.pi * summary["daily_all"]["kendall"] / 2)

# 2) 経験的な裾の依存（観測・ブロックブートストラップ・ガウスなら）
rows = []
for q in QS:
    up, lo = emp_tail(u, v, q)
    bb = block_boot(x, y, lambda a, b: emp_tail(pobs(a), pobs(b), q))
    gn = gauss_null(rho_n, len(x), q)
    rows.append(dict(q=q, days_each=int(round(len(x) * (1 - q))), upper=up, upper_lo=np.quantile(bb[:, 0], .025),
                     upper_hi=np.quantile(bb[:, 0], .975), lower=lo, lower_lo=np.quantile(bb[:, 1], .025),
                     lower_hi=np.quantile(bb[:, 1], .975), diff_lower_minus_upper=lo - up,
                     diff_lo=np.quantile(bb[:, 1] - bb[:, 0], .025), diff_hi=np.quantile(bb[:, 1] - bb[:, 0], .975),
                     gauss_mean=gn.mean(), gauss_hi=np.quantile(gn, .975),
                     p_upper_vs_gauss=np.mean(gn[:, 0] >= up), p_lower_vs_gauss=np.mean(gn[:, 1] >= lo)))
emp = pd.DataFrame(rows); emp.to_csv(RES / "empirical_tail_dependence.csv", index=False)

# 3) コピュラの当てはめ（全期間・日次）
fits = pd.DataFrame(C.fit_all(u, v)).sort_values("aic"); fits["daic"] = fits.aic - fits.aic.min()
fits.to_csv(RES / "copula_fits_daily_all.csv", index=False)

# 4) 大きく動いた日だけの相関（代替案）＋ ガウスなら同じ選び方でどう出るか
big = []
zx, zy = (x - x.mean()) / x.std(), (y - y.mean()) / y.std()
for lab, mask_fn in [("日経が上下10%の日", lambda a, b: np.abs(b) >= np.quantile(np.abs(b), .9)),
                     ("ドル円が上下10%の日", lambda a, b: np.abs(a) >= np.quantile(np.abs(a), .9)),
                     ("両方が同じ向きに上位10%", lambda a, b: (pobs(a) > .9) & (pobs(b) > .9)),
                     ("ふつうの日（両方とも上下10%に入らない）", lambda a, b: (np.abs(a) < np.quantile(np.abs(a), .9)) & (np.abs(b) < np.quantile(np.abs(b), .9)))]:
    m = mask_fn(zx, zy); obs = np.corrcoef(x[m], y[m])[0, 1]
    sims = []
    for _ in range(300):
        z = rng.multivariate_normal([0, 0], [[1, summary["daily_all"]["pearson"]], [summary["daily_all"]["pearson"], 1]], len(x))
        mm = mask_fn(z[:, 0], z[:, 1]); sims.append(np.corrcoef(z[mm, 0], z[mm, 1])[0, 1])
    big.append(dict(group=lab, n=int(m.sum()), corr=obs, gauss_mean=np.mean(sims), gauss_lo=np.quantile(sims, .025),
                    gauss_hi=np.quantile(sims, .975)))
pd.DataFrame(big).to_csv(RES / "big_move_correlation.csv", index=False)

# 5) 頑健性：期間・日次と週次・GARCH で標準化・裾の閾値
rob = []
def one(lab, x, y, fit=True):
    u, v = pobs(x), pobs(y); b = basic(x, y); r = dict(case=lab, **b)
    for q in (0.95, 0.975):
        up, lo = emp_tail(u, v, q); r[f"upper_{q}"] = up; r[f"lower_{q}"] = lo
    rn = np.sin(np.pi * b["kendall"] / 2); gn = gauss_null(rn, len(x), 0.95, S=200)
    r["gauss_mean_0.95"] = gn.mean(); r["gauss_hi_0.95"] = np.quantile(gn, .975)
    if fit:
        f = pd.DataFrame(C.fit_all(u, v)).sort_values("aic")
        r["best_family"] = f.family.iloc[0]
        g = f.set_index("family")
        r["daic_gauss"] = g.loc["ガウス", "aic"] - f.aic.min(); r["daic_t"] = g.loc["t", "aic"] - f.aic.min()
        r["t_lambda"] = g.loc["t", "lambda_upper"]; r["t_nu"] = 2 + np.exp(float(g.loc["t", "params"].split(";")[1]))
        r["sjc_upper"] = g.loc["対称化ジョー・クレイトン", "lambda_upper"]; r["sjc_lower"] = g.loc["対称化ジョー・クレイトン", "lambda_lower"]
    rob.append(r)

one("日次・全期間", x, y)
for lab, a, b in PERIODS:
    m = (d.date >= a) & (d.date <= b); one(f"日次・{lab}", d.r_fx[m].values, d.r_nk[m].values)
one("週次・全期間", w.r_fx.values, w.r_nk.values)
for lab, a, b in PERIODS:
    m = (w.date >= a) & (w.date <= b); one(f"週次・{lab}", w.r_fx[m].values, w.r_nk[m].values)
sx, gx = garch_std(x); sy, gy = garch_std(y)
one("日次・全期間・GARCHで標準化", sx, sy)
m = d.gap_days.values == 1; one("日次・前日が営業日の日だけ", x[m], y[m], fit=False)
one("日次・ドル円を1日ずらす（ドル円t−1・日経t）", x[:-1], y[1:], fit=False)
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)

# 6) 年ごとの順位相関（図用）
yr = d.groupby(d.date.dt.year).apply(lambda g: pd.Series(dict(n=len(g), kendall=stats.kendalltau(g.r_fx, g.r_nk)[0],
                                                               pearson=g.r_fx.corr(g.r_nk))), include_groups=False)
yr.to_csv(RES / "yearly_correlation.csv")

# 7) 極端な日の数（両方が上位/下位 2.5%）を期間ごとに
ext = []
for lab, a, b in [("全期間", "1998", "2027")] + PERIODS:
    m = (d.date >= a) & (d.date <= b) if lab != "全期間" else np.ones(len(d), bool)
    uu, vv = u[m], v[m]
    ext.append(dict(period=lab, n=int(m.sum()), both_up_2_5=int(((uu > .975) & (vv > .975)).sum()),
                    both_down_2_5=int(((uu <= .025) & (vv <= .025)).sum()),
                    yen_weak_stock_down=int(((uu > .975) & (vv <= .025)).sum()),
                    yen_strong_stock_up=int(((uu <= .025) & (vv > .975)).sum())))
pd.DataFrame(ext).to_csv(RES / "extreme_day_counts.csv", index=False)

summary.update(rho_normal_from_kendall=rho_n, garch_fx=gx, garch_nk=gy, n_daily=len(d), n_weekly=len(w),
               start=str(d.date.min().date()), end=str(d.date.max().date()))
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(summary, ensure_ascii=False, default=float, indent=0))
print(emp.round(3).to_string()); print(fits.round(3).to_string()); print(pd.DataFrame(big).round(3).to_string())
print(pd.DataFrame(rob).round(3).to_string()); print(pd.DataFrame(ext).to_string())
