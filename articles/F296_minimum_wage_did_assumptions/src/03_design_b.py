"""設計B：上げ幅が中央値より5円以上大きかった県（ずれて始まる）。TWFE と、ずれに強い推定、TWFE の中身。"""
import numpy as np
import pandas as pd
from scipy import stats

from common import DATA, SEED, fe_reg, r, save_json, wild_cluster_p

p = pd.read_csv(DATA / "panel.csv")
Y0, Y1 = 2015, 2025
B = p[p.year.between(Y0, Y1)].copy()
B["g_in"] = np.where(B["g"] <= Y1, B["g"], np.inf)               # 期間内に処置が始まらない県は inf
B["D"] = (B.year >= B.g_in).astype(int)
units = B.drop_duplicates("code")[["code", "pref", "g_in", "first_fy"]]
cohorts = sorted(units.loc[np.isfinite(units.g_in), "g_in"].unique().astype(int))
n_by = units.groupby("g_in").size()
print("暦年の処置開始ごとの県数", n_by.to_dict())
YS = ["emp_rate", "unemp_rate", "log_wage"]
out = {"cohorts": {str(int(k)) if np.isfinite(k) else "期間内なし": int(v) for k, v in n_by.items()}}

# ---- 1. TWFE（処置ダミー）と wild cluster bootstrap
tw = {}
for y in YS:
    f = fe_reg(B, y, ["D"])
    pw, _ = wild_cluster_p(B, y, "D", B=9999, weights="webb")
    tw[y] = {"b": r(f["b"][0]), "se": r(f["se"][0]), "p_cluster": r(2 * stats.t.sf(abs(f["b"][0] / f["se"][0]), 46)), "p_wild_webb": r(pw)}
out["twfe"] = tw

# ---- 2. Callaway–Sant'Anna 型（共変量なし、平均の差で計算）。比較＝期間内なし（never）／まだ処置されていない（notyet）
YEARS = list(range(Y0, Y1 + 1))

def att_gt_arr(W, G, ctrl):
    """W: 県×年の行列（列は YEARS）、G: 県ごとの処置開始（期間内なしは inf）。"""
    col = {t: j for j, t in enumerate(YEARS)}
    res = []
    for g in cohorts:
        tr = G == g
        if tr.sum() == 0:
            continue
        for t in range(Y0 + 1, Y1 + 1):
            base = g - 1 if t >= g else t - 1                    # 処置前は1年前と比べる（varying base）
            c = ~np.isfinite(G) if ctrl == "never" else ((G > max(t, base)) & ~tr)
            if c.sum() == 0:
                continue
            dt = W[tr, col[t]] - W[tr, col[base]]
            dc = W[c, col[t]] - W[c, col[base]]
            if np.isnan(dt).all() or np.isnan(dc).all():
                continue
            res.append({"g": g, "t": t, "e": t - g, "att": np.nanmean(dt) - np.nanmean(dc), "n_t": int(tr.sum()), "n_c": int(c.sum())})
    return pd.DataFrame(res)

def aggregate(a):
    post = a[a.e >= 0]
    w = post.n_t / post.n_t.sum()
    simple = float((post.att * w).sum())
    ev = a.groupby("e").apply(lambda d: np.average(d.att, weights=d.n_t), include_groups=False)
    return simple, ev

def wide_of(df, y):
    w = df.pivot(index="code", columns="year", values=y).reindex(columns=YEARS)
    G = df.drop_duplicates("code").set_index("code")["g_in"].reindex(w.index).to_numpy(float)
    return w.to_numpy(float), G

def boot_cs(W, G, ctrl, Bn=999):
    rng = np.random.default_rng(SEED)
    sims, evs = [], []
    for _ in range(Bn):
        i = rng.integers(0, len(G), len(G))
        a = att_gt_arr(W[i], G[i], ctrl)
        if a.empty or (a.e >= 0).sum() == 0:
            continue
        s, ev = aggregate(a)
        sims.append(s)
        evs.append(ev)
    return np.array(sims), pd.DataFrame(evs)

cs_rows, cs_ev_rows = [], []
for y in YS:
    W, G = wide_of(B, y)
    for ctrl in ["never", "notyet"]:
        a = att_gt_arr(W, G, ctrl)
        s, ev = aggregate(a)
        sims, evb = boot_cs(W, G, ctrl)
        se = float(np.nanstd(sims, ddof=1))
        pre_e = [e for e in ev.index if e < 0 and e in evb.columns]
        bp = ev[pre_e].to_numpy(float)
        Sp = np.cov(evb[pre_e].dropna().to_numpy(float), rowvar=False)
        Wpre = float(bp @ np.linalg.solve(Sp, bp))
        cs_rows.append({"y": y, "比較": ctrl, "ATT": r(s), "se_boot": r(se), "lo95": r(s - 1.96 * se), "hi95": r(s + 1.96 * se),
                        "最小検出効果80": r(2.8 * se), "事前_e-1": r(ev.get(-1, np.nan)),
                        "事前_同時検定p": r(float(stats.chi2.sf(Wpre, len(pre_e))))})
        for e, v in ev.items():
            se_e = float(np.nanstd(evb[e], ddof=1)) if e in evb else np.nan
            cs_ev_rows.append({"y": y, "比較": ctrl, "e": int(e), "att": r(v), "se": r(se_e)})
cs = pd.DataFrame(cs_rows)
cs.to_csv(DATA.parent / "results" / "b_callaway_santanna.csv", index=False)
pd.DataFrame(cs_ev_rows).to_csv(DATA.parent / "results" / "b_cs_event.csv", index=False)
print(cs)

# ---- 3. Sun–Abraham 型：処置の年×相対年のダミー（比較＝期間内なし）、相対年 −1 を基準。県の数で重みをつけて平均
sa_rows = []
for y in YS:
    d = B.dropna(subset=[y]).copy()
    cols, meta = [], []
    for g in cohorts:
        for e in range(Y0 - g, Y1 - g + 1):
            if e == -1:
                continue
            c = f"sa_{g}_{e}"
            d[c] = ((d.g_in == g) & (d.year - g == e)).astype(int)
            if d[c].sum() == 0:
                d.drop(columns=c, inplace=True)
                continue
            cols.append(c)
            meta.append((g, e))
    f = fe_reg(d, y, cols)
    post = [i for i, (g, e) in enumerate(meta) if e >= 0]
    wts = np.array([n_by[float(meta[i][0])] for i in post], float)
    wts = wts / wts.sum()
    est = float(wts @ f["b"][post])
    se = float(np.sqrt(wts @ f["V"][np.ix_(post, post)] @ wts))
    sa_rows.append({"y": y, "ATT": r(est), "se": r(se), "lo95": r(est - 1.96 * se), "hi95": r(est + 1.96 * se)})
sa = pd.DataFrame(sa_rows)
sa.to_csv(DATA.parent / "results" / "b_sun_abraham.csv", index=False)
print(sa)

# ---- 4. TWFE の中身：Goodman-Bacon の分解（就業率）
def twoway_demean(x, df):
    s = pd.Series(np.asarray(x, float), index=df.index)
    for _ in range(200):
        s = s - s.groupby(df.code).transform("mean")
        s = s - s.groupby(df.year).transform("mean")
    return s

def did22(df, y, treat_codes, ctrl_codes, pre, post):
    w = df.pivot(index="code", columns="year", values=y)
    tr = w.loc[treat_codes, post].mean(axis=1).mean() - w.loc[treat_codes, pre].mean(axis=1).mean()
    cc = w.loc[ctrl_codes, post].mean(axis=1).mean() - w.loc[ctrl_codes, pre].mean(axis=1).mean()
    return tr - cc

d = B.copy()
y = "emp_rate"
T = Y1 - Y0 + 1
years = list(range(Y0, Y1 + 1))
gmap = d.drop_duplicates("code").set_index("code")["g_in"]
N = len(gmap)
Dres = twoway_demean(d.D, d)
VD = float((Dres ** 2).mean())
groups = {g: gmap.index[gmap == g] for g in cohorts}
U = gmap.index[~np.isfinite(gmap)]
n = {g: len(v) / N for g, v in groups.items()}
nU = len(U) / N
Dbar = {g: np.mean([yr >= g for yr in years]) for g in cohorts}
bacon = []
for g in cohorts:
    nkU = n[g] / (n[g] + nU)
    s = (n[g] + nU) ** 2 * nkU * (1 - nkU) * Dbar[g] * (1 - Dbar[g]) / VD
    est = did22(d, y, groups[g], U, [t for t in years if t < g], [t for t in years if t >= g])
    bacon.append({"比較": f"{g}年開始 vs 期間内なし", "種類": "処置 vs 未処置", "重み": s, "2x2": est})
for i, k in enumerate(cohorts):
    for l in cohorts[i + 1:]:
        nkl = n[k] / (n[k] + n[l])
        s_k = ((n[k] + n[l]) * (1 - Dbar[l])) ** 2 * nkl * (1 - nkl) * ((Dbar[k] - Dbar[l]) / (1 - Dbar[l])) * ((1 - Dbar[k]) / (1 - Dbar[l])) / VD
        s_l = ((n[k] + n[l]) * Dbar[k]) ** 2 * nkl * (1 - nkl) * (Dbar[l] / Dbar[k]) * ((Dbar[k] - Dbar[l]) / Dbar[k]) / VD
        e_k = did22(d, y, groups[k], groups[l], [t for t in years if t < k], [t for t in years if k <= t < l])
        e_l = did22(d, y, groups[l], groups[k], [t for t in years if k <= t < l], [t for t in years if t >= l])
        bacon.append({"比較": f"{k}年開始 vs {l}年開始（後の県が比較）", "種類": "早い vs まだ", "重み": s_k, "2x2": e_k})
        bacon.append({"比較": f"{l}年開始 vs {k}年開始（先に処置された県が比較）", "種類": "遅い vs すでに処置（禁じ手）", "重み": s_l, "2x2": e_l})
bacon = pd.DataFrame(bacon)
bacon["重み×2x2"] = bacon["重み"] * bacon["2x2"]
bacon = bacon.round(4)
bacon.to_csv(DATA.parent / "results" / "b_bacon.csv", index=False)
print(bacon, "重みの合計", bacon["重み"].sum(), "重み付き平均", bacon["重み×2x2"].sum(), "TWFE", tw[y]["b"])

# ---- 5. de Chaisemartin–D'Haultfœuille の重み（処置された県×年ごとの重み）
treated = d.D == 1
wcell = Dres[treated] / Dres[treated].sum()
dcdh = {"n_cells": int(treated.sum()), "n_negative": int((wcell < 0).sum()), "sum_negative": r(float(wcell[wcell < 0].sum())),
        "min_weight": r(float(wcell.min())), "max_weight": r(float(wcell.max()))}
neg = d.loc[treated].assign(w=wcell.values)[["pref", "year", "g_in", "w"]]
neg.round(4).to_csv(DATA.parent / "results" / "b_dcdh_weights.csv", index=False)

out.update({"callaway_santanna": cs.to_dict(orient="records"), "sun_abraham": sa.to_dict(orient="records"),
            "bacon_sum_weights": r(float(bacon["重み"].sum())), "bacon_weighted": r(float(bacon["重み×2x2"].sum())),
            "dcdh": dcdh, "treated_units": int(np.isfinite(units.g_in).sum())})
save_json(out, "b_main.json")
print(out)
