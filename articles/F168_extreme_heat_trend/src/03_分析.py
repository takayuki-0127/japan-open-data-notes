"""03 分析：年最高気温の非定常GEV（位置に時間トレンド）と、猛暑日の数の回数モデル"""
import json, warnings
import numpy as np, pandas as pd
from scipy import optimize, stats
import statsmodels.api as sm
from common import DATA, RES, SEED

warnings.filterwarnings("ignore")
rng = np.random.default_rng(SEED)
d = pd.read_csv(DATA / "annual_clean.csv")
G = dict(zip(d.station, d.group))

def nll(p, x, X):
    k = X.shape[1]; mu = X @ p[:k]; sig = np.exp(p[k]); xi = p[k + 1]
    z = (x - mu) / sig
    if abs(xi) < 1e-6:
        return np.sum(np.log(sig) + z + np.exp(-z))
    w = 1 + xi * z
    if np.any(w <= 0): return 1e10
    return np.sum(np.log(sig) + (1 + 1 / xi) * np.log(w) + w ** (-1 / xi))

def design(yr, shape):
    t = (yr - 2000) / 100
    if shape == "stat": return np.c_[np.ones_like(t)]
    if shape == "lin": return np.c_[np.ones_like(t), t]
    if shape == "quad": return np.c_[np.ones_like(t), t, t ** 2]
    if shape == "hinge": return np.c_[np.ones_like(t), t, np.maximum(0, yr - 1980) / 100]

def hess(f, p, h=1e-4):
    n = len(p); H = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            e = np.zeros(n); e[i] = h; g = np.zeros(n); g[j] = h
            H[i, j] = (f(p + e + g) - f(p + e - g) - f(p - e + g) + f(p - e - g)) / (4 * h * h)
    return H

def fit(x, yr, shape="lin", xi_fixed=None):
    X = design(yr, shape); k = X.shape[1]
    b0 = np.linalg.lstsq(X, x, rcond=None)[0]
    s0 = np.log(np.std(x - X @ b0) * 0.78)
    if xi_fixed is None:
        f = lambda p: nll(p, x, X)
        best = None
        for xi0 in (-0.2, -0.1, 0.05):
            r = optimize.minimize(f, np.r_[b0, s0, xi0], method="Nelder-Mead", options=dict(maxiter=20000, xatol=1e-7, fatol=1e-9))
            if best is None or r.fun < best.fun: best = r
        p = best.x
    else:
        f = lambda q: nll(np.r_[q, xi_fixed], x, X)
        r = optimize.minimize(f, np.r_[b0, s0], method="Nelder-Mead", options=dict(maxiter=20000, xatol=1e-7, fatol=1e-9))
        best = r; p = np.r_[r.x, xi_fixed]
    try:
        H = hess(f, best.x); cov = np.linalg.inv(H)
        if xi_fixed is not None:
            c = np.zeros((len(p), len(p))); c[:-1, :-1] = cov; cov = c
    except Exception:
        cov = np.full((len(p), len(p)), np.nan)
    return dict(p=p, cov=cov, nll=best.fun, k=len(best.x), X=X)

def gev_sf(v, mu, sig, xi):
    return stats.genextreme.sf(v, -xi, loc=mu, scale=sig)

def station_fits(start=1901, end=2025, xi_fixed=None):
    rows = []
    for s, g in d.groupby("station"):
        g = g[(g.year >= start) & (g.year <= end)].dropna(subset=["tmax_abs"])
        if len(g) < 30: continue
        x = g.tmax_abs.values.astype(float); yr = g.year.values.astype(float)
        f0 = fit(x, yr, "stat", xi_fixed); f1 = fit(x, yr, "lin", xi_fixed)
        se = np.sqrt(f1["cov"][1, 1]) if np.isfinite(f1["cov"][1, 1]) and f1["cov"][1, 1] > 0 else np.nan
        lr = 2 * (f0["nll"] - f1["nll"])
        rows.append(dict(station=s, group=G[s], n=len(g), first=int(yr.min()), mu1=f1["p"][1], se=se,
                         lo=f1["p"][1] - 1.96 * se, hi=f1["p"][1] + 1.96 * se, xi=f1["p"][-1], sigma=np.exp(f1["p"][-2]),
                         p_lr=stats.chi2.sf(lr, 1), f1=f1))
    return rows

out = {}
# ---- 主分析：1901〜2025年、直線トレンド ----
main = station_fits()
tab = pd.DataFrame([{k: v for k, v in r.items() if k != "f1"} for r in main])
# 35℃・38℃を超える年の確率：1925年と2025年（パラメータの不確かさは多変量正規から2000回）
pr = []
for r in main:
    p, cov = r["f1"]["p"], r["f1"]["cov"]
    draws = rng.multivariate_normal(p, cov, 2000) if np.all(np.isfinite(cov)) else np.tile(p, (2000, 1))
    for thr in (35.0, 38.0):
        v = {}
        for y in (1925, 2025):
            t = (y - 2000) / 100
            v[y] = gev_sf(thr, p[0] + p[1] * t, np.exp(p[2]), p[3])
            v[f"{y}_d"] = gev_sf(thr, draws[:, 0] + draws[:, 1] * t, np.exp(draws[:, 2]), draws[:, 3])
        rp25 = 1 / max(v[1925], 1e-9); rp = 1 / max(v[2025], 1e-9)
        q = np.quantile(1 / np.maximum(v["2025_d"], 1e-9), [0.025, 0.975])
        pr.append(dict(station=r["station"], group=r["group"], thr=thr, p1925=v[1925], p2025=v[2025],
                       rp1925=rp25, rp2025=rp, rp2025_lo=q[0], rp2025_hi=q[1]))
pr = pd.DataFrame(pr)
tab = tab.merge(pr[pr.thr == 35].drop(columns=["group", "thr"]).add_suffix("_35").rename(columns={"station_35": "station"}), on="station")
tab.to_csv(RES / "gev_linear_1901_2025.csv", index=False)
pr.to_csv(RES / "exceed_prob_1925_2025.csv", index=False)
out["主分析"] = dict(
    地点数=len(tab), 上昇がはっきり=int((tab.lo > 0).sum()), 下降がはっきり=int((tab.hi < 0).sum()),
    中央値_100年あたり=round(float(tab.mu1.median()), 2),
    R平均=round(float(tab[tab.group == "R"].mu1.mean()), 2), U平均=round(float(tab[tab.group == "U"].mu1.mean()), 2),
    差_U_R=round(float(tab[tab.group == "U"].mu1.mean() - tab[tab.group == "R"].mu1.mean()), 2),
    差のp_Welch=round(float(stats.ttest_ind(tab[tab.group == "U"].mu1, tab[tab.group == "R"].mu1, equal_var=False).pvalue), 4),
    xi中央値=round(float(tab.xi.median()), 3))
# 並べ替え検定（区分ラベルを並べ替え）
obs = out["主分析"]["差_U_R"]; m = tab.mu1.values; gr = (tab.group == "U").values; perm = []
for _ in range(10000):
    q = rng.permutation(gr); perm.append(m[q].mean() - m[~q].mean())
out["主分析"]["差のp_並べ替え"] = round(float(np.mean(np.abs(perm) >= abs(obs))), 4)

# ---- 頑健性1：トレンドの形 ----
shp = []
for s, g in d.groupby("station"):
    g = g[(g.year >= 1901)].dropna(subset=["tmax_abs"]); x = g.tmax_abs.values.astype(float); yr = g.year.values.astype(float)
    fs = {k: fit(x, yr, k) for k in ("stat", "lin", "quad", "hinge")}
    aic = {k: 2 * f["nll"] + 2 * f["k"] for k, f in fs.items()}
    h = fs["hinge"]["p"]; hc = fs["hinge"]["cov"]
    shp.append(dict(station=s, group=G[s], best=min(aic, key=aic.get), **{f"aic_{k}": v for k, v in aic.items()},
                    hinge_pre=h[1], hinge_post=h[1] + h[2], hinge_extra=h[2],
                    hinge_extra_se=np.sqrt(hc[2, 2]) if np.isfinite(hc[2, 2]) and hc[2, 2] > 0 else np.nan))
shp = pd.DataFrame(shp); shp.to_csv(RES / "trend_shape.csv", index=False)
out["形"] = dict(AIC最良=shp.best.value_counts().to_dict(),
                 傾き_1980年まで_中央値=round(float(shp.hinge_pre.median()), 2), 傾き_1980年以降_中央値=round(float(shp.hinge_post.median()), 2),
                 加速がはっきり=int(((shp.hinge_extra - 1.96 * shp.hinge_extra_se) > 0).sum()))

# ---- 頑健性2：期間 ----
per = []
for st in (1901, 1931, 1961, 1991):
    rs = station_fits(start=st)
    t2 = pd.DataFrame([{k: v for k, v in r.items() if k != "f1"} for r in rs]); t2["start"] = st; per.append(t2)
per = pd.concat(per); per.to_csv(RES / "period_sensitivity.csv", index=False)
out["期間"] = {str(k): dict(中央値=round(float(v.mu1.median()), 2), 上昇はっきり=int((v.lo > 0).sum()), 地点=len(v),
                           R=round(float(v[v.group == "R"].mu1.mean()), 2), U=round(float(v[v.group == "U"].mu1.mean()), 2),
                           差のp_Welch=round(float(stats.ttest_ind(v[v.group == "U"].mu1, v[v.group == "R"].mu1, equal_var=False).pvalue), 3))
              for k, v in per.groupby("start")}

# ---- 頑健性3：形の母数ξを0に固定（グンベル） ----
gm = station_fits(xi_fixed=0.0)
tg = pd.DataFrame([{k: v for k, v in r.items() if k != "f1"} for r in gm])
out["グンベル"] = dict(中央値=round(float(tg.mu1.median()), 2), 上昇はっきり=int((tg.lo > 0).sum()),
                      主分析との相関=round(float(np.corrcoef(tg.sort_values("station").mu1, tab.sort_values("station").mu1)[0, 1]), 3))

# ---- 頑健性4：地点の選び方（1地点ずつ抜く） ----
loo = []
for s in tab.station:
    t3 = tab[tab.station != s]; loo.append(t3[t3.group == "U"].mu1.mean() - t3[t3.group == "R"].mu1.mean())
out["地点抜き"] = dict(差の最小=round(float(min(loo)), 2), 差の最大=round(float(max(loo)), 2))
t4 = tab[tab.station != "東京"]
out["東京を除く差"] = round(float(t4[t4.group == "U"].mu1.mean() - t4[t4.group == "R"].mu1.mean()), 2)

# ---- 猛暑日の数：ポアソン回帰と負の二項回帰 ----
cnt = []
for s, g in d.groupby("station"):
    g = g[g.year >= 1901].dropna(subset=["d35"])
    tot = g.d35.sum()
    rec = dict(station=s, group=G[s], n=len(g), total_d35=int(tot),
               early=g[g.year.between(1901, 1930)].d35.mean(), late=g[g.year.between(1996, 2025)].d35.mean(),
               early30=g[g.year.between(1901, 1930)].d30.mean(), late30=g[g.year.between(1996, 2025)].d30.mean())
    X = sm.add_constant((g.year.values - 2000) / 10)
    for var in ("d35", "d30"):
        y = g[var].values
        if y.sum() < 20:
            continue
        po = sm.GLM(y, X, family=sm.families.Poisson()).fit()
        # 負の二項：αは最尤で推定
        nb = sm.NegativeBinomial(y, X).fit(disp=0, maxiter=200)
        b, se = nb.params[1], nb.bse[1]
        rec.update({f"{var}_po_rr": np.exp(po.params[1]), f"{var}_po_lo": np.exp(po.params[1] - 1.96 * po.bse[1]),
                    f"{var}_po_hi": np.exp(po.params[1] + 1.96 * po.bse[1]), f"{var}_po_disp": po.pearson_chi2 / po.df_resid,
                    f"{var}_nb_rr": np.exp(b), f"{var}_nb_lo": np.exp(b - 1.96 * se), f"{var}_nb_hi": np.exp(b + 1.96 * se),
                    f"{var}_nb_2025_vs_1925": np.exp(b * 10), f"{var}_nb_2025_vs_1925_lo": np.exp((b - 1.96 * se) * 10),
                    f"{var}_nb_2025_vs_1925_hi": np.exp((b + 1.96 * se) * 10)})
    cnt.append(rec)
cnt = pd.DataFrame(cnt); cnt.to_csv(RES / "count_models.csv", index=False)
c35 = cnt.dropna(subset=["d35_nb_rr"])
out["猛暑日"] = dict(モデルを当てた地点=len(c35), 地点名=list(c35.station),
                    合計20日未満で当てられない地点=list(cnt[cnt.d35_nb_rr.isna()].station),
                    NB_10年あたり倍率_中央値=round(float(c35.d35_nb_rr.median()), 3),
                    NBで増加はっきり=int((c35.d35_nb_lo > 1).sum()),
                    ポアソンの過分散_中央値=round(float(c35.d35_po_disp.median()), 2),
                    ポアソンの区間幅_中央値=round(float((np.log(c35.d35_po_hi) - np.log(c35.d35_po_lo)).median()), 3),
                    NBの区間幅_中央値=round(float((np.log(c35.d35_nb_hi) - np.log(c35.d35_nb_lo)).median()), 3),
                    百年での倍率_中央値=round(float(c35.d35_nb_2025_vs_1925.median()), 2),
                    百年での倍率_下限の中央値=round(float(c35.d35_nb_2025_vs_1925_lo.median()), 2))
e = cnt[(cnt.early > 0) & (cnt.total_d35 >= 20)]
out["猛暑日_30年平均"] = dict(地点=len(e), 最初30年_中央値=round(float(e.early.median()), 2), 最近30年_中央値=round(float(e.late.median()), 2),
                         倍率_中央値=round(float((e.late / e.early).median()), 2), 倍率_最小=round(float((e.late / e.early).min()), 2),
                         倍率_最大=round(float((e.late / e.early).max()), 2),
                         最初30年が0の地点=list(cnt[(cnt.early == 0) & (cnt.late > 0)].station))
c30 = cnt.dropna(subset=["d30_nb_rr"])
out["真夏日"] = dict(地点=len(c30), NB_10年あたり倍率_中央値=round(float(c30.d30_nb_rr.median()), 3),
                    増加はっきり=int((c30.d30_nb_lo > 1).sum()),
                    R=round(float(c30[c30.group == "R"].d30_nb_rr.median()), 3), U=round(float(c30[c30.group == "U"].d30_nb_rr.median()), 3))

# ---- 検出力：直線トレンドの標準誤差から、125年・65年・35年で見分けられる大きさ ----
out["検出の目安"] = {str(k): round(float(2.8 * per[per.start == k].se.median()), 2) for k in (1901, 1961, 1991)}
# モデルを使わない数え方：年最高気温が38℃・37℃以上だった「地点×年」の数（1901〜1950年と1976〜2025年）
emp = []
for th in (37, 38):
    a = d[d.year.between(1901, 1950)]; b = d[d.year.between(1976, 2025)]
    for s_, ga in a.groupby("station"):
        gb = b[b.station == s_]
        emp.append(dict(thr=th, station=s_, group=G[s_], early=int((ga.tmax_abs >= th).sum()), n_early=len(ga),
                        late=int((gb.tmax_abs >= th).sum()), n_late=len(gb)))
emp = pd.DataFrame(emp); emp.to_csv(RES / "empirical_exceed_counts.csv", index=False)
out["数えるだけ"] = {f"{th}度": dict(前50年=int(g.early.sum()), 後50年=int(g.late.sum()), 地点年_前=int(g.n_early.sum()), 地点年_後=int(g.n_late.sum()),
                                   倍率=round(float(g.late.sum() / g.early.sum()), 1)) for th, g in emp.groupby("thr")}
p38 = pr[pr.thr == 38]
out["38度"] = {r.station: {"1925年": round(float(r.rp1925), 1), "2025年": round(float(r.rp2025), 1), "2025年_下": round(float(r.rp2025_lo), 1), "2025年_上": round(float(r.rp2025_hi), 1)}
              for r in p38.itertuples() if r.station in ("東京", "熊谷", "大阪", "名古屋", "京都", "岐阜", "甲府", "福岡", "境", "伏木", "山形", "多度津")}
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
