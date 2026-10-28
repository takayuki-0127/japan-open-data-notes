"""03 分析：一般化傾向スコア（Hirano–Imbens）と IPW で用量反応曲線を推定する"""
import json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy import stats
from patsy import dmatrix
from common import ROOT, SEED, T, Y, X, GRID, LO, HI

rng = np.random.default_rng(SEED)
D = pd.read_csv(ROOT / "data/analysis_2018_22.csv", dtype={"code": str, "pref": str})
D13 = pd.read_csv(ROOT / "data/analysis_2013_17.csv", dtype={"code": str, "pref": str})
GRID = np.array(GRID, float)

def design(d, xs, fe=True):
    Z = d[xs].astype(float)
    Z = (Z - Z.mean()) / Z.std()
    if fe:
        Z = pd.concat([Z, pd.get_dummies(d["pref"], prefix="p", drop_first=True).astype(float)], axis=1)
    return sm.add_constant(Z, has_constant="add").values

def tr(t, kind):
    if kind == "raw": return t
    if kind == "sqrt": return np.sqrt(t)
    raise ValueError

# ---------- 一般化傾向スコア（GPS） ----------
def gps_fit(d, xs=X, fe=True, kind="raw", outcome="quad"):
    Z = design(d, xs, fe)
    t = d[T].values.astype(float); y = d[Y].values.astype(float)
    tt = tr(t, kind)
    m = sm.OLS(tt, Z).fit()
    mu = Z @ m.params; s = np.sqrt(m.scale)
    def dens(tval):  # 処置の値 tval での GPS（処置の変換に合わせてヤコビアンは定数なので省略）
        return stats.norm.pdf(tr(np.asarray(tval, float), kind), mu, s)
    r = dens(t)
    def feat(tv, rv):
        cols = [np.ones_like(rv), tv, tv**2, rv, rv**2, tv*rv]
        if outcome == "cubic": cols += [tv**3, rv**3]
        return np.column_stack(cols)
    o = sm.OLS(y, feat(t, r)).fit()
    curve = np.array([o.predict(feat(np.full_like(r, g), dens(g))).mean() for g in GRID])
    return dict(curve=curve, resid=tt - mu, r=r, mu=mu, s=s, o=o, gps_model=m, dens=dens)

def gps_curve(d, **kw):
    return gps_fit(d, **kw)["curve"]

# ---------- IPW（安定化重み）＋スプライン ----------
def ipw_curve(d, xs=X, fe=True, trim=(0.01, 0.99), return_w=False):
    Z = design(d, xs, fe)
    t = d[T].values.astype(float); y = d[Y].values.astype(float)
    m = sm.OLS(t, Z).fit(); s = np.sqrt(m.scale)
    num = stats.norm.pdf(t, t.mean(), t.std()); den = stats.norm.pdf(t, Z @ m.params, s)
    w = num / den
    lo, hi = np.quantile(w, trim); w = np.clip(w, lo, hi)
    B = dmatrix("cr(t, df=4) - 1", {"t": t}, return_type="dataframe")
    o = sm.WLS(y, B, weights=w).fit()
    Bg = dmatrix(B.design_info, {"t": GRID}, return_type="dataframe")
    c = np.asarray(Bg @ o.params)
    return (c, w) if return_w else c

def naive_curve(d):
    t = d[T].values.astype(float); y = d[Y].values.astype(float)
    B = dmatrix("cr(t, df=4) - 1", {"t": t}, return_type="dataframe")
    o = sm.OLS(y, B).fit()
    return np.asarray(dmatrix(B.design_info, {"t": GRID}, return_type="dataframe") @ o.params)

def ols_curve(d, xs=X, fe=True):
    """回帰調整：Y ~ スプライン(T) + 条件。条件を全員の値に固定して平均（部分依存）"""
    t = d[T].values.astype(float); y = d[Y].values.astype(float)
    B = dmatrix("cr(t, df=4) - 1", {"t": t}, return_type="dataframe")
    Z = design(d, xs, fe)
    o = sm.OLS(y, np.column_stack([B.values, Z[:, 1:]])).fit()
    out = []
    for g in GRID:
        Bg = dmatrix(B.design_info, {"t": np.full(len(d), g)}, return_type="dataframe").values
        out.append(o.predict(np.column_stack([Bg, Z[:, 1:]])).mean())
    return np.array(out)

def diff(c):
    i, j = list(GRID).index(LO), list(GRID).index(HI)
    return c[j] - c[i]

def boot(d, fn, B=400, cluster=False, **kw):
    reps = []
    prefs = d["pref"].unique()
    for _ in range(B):
        if cluster:
            pick = rng.choice(prefs, len(prefs), replace=True)
            db = pd.concat([d[d["pref"] == p] for p in pick], ignore_index=True)
        else:
            db = d.iloc[rng.integers(0, len(d), len(d))].reset_index(drop=True)
        try:
            reps.append(fn(db, **kw))
        except Exception:
            pass
    return np.array(reps)

def summ(c, reps):
    lo, hi = np.percentile(reps, [2.5, 97.5], axis=0)
    dd = np.array([diff(r) for r in reps])
    return dict(curve=c.round(4).tolist(), lo=lo.round(4).tolist(), hi=hi.round(4).tolist(),
                diff=round(float(diff(c)), 4),
                diff_ci=[round(float(x), 4) for x in np.percentile(dd, [2.5, 97.5])], n_boot=len(reps))

res = {"grid": GRID.tolist(), "n": int(len(D)),
       "T_desc": D[T].describe().round(2).to_dict(),
       "T_quantiles": {q: round(float(D[T].quantile(q)), 1) for q in [0.1, 0.25, 0.5, 0.75, 0.9]},
       "tfr_mean": round(float(D[Y].mean()), 3)}

# ---- 1. 4つの方法の曲線 ----
methods = {
    "naive": (naive_curve, {}),
    "ols": (ols_curve, {}),
    "gps": (gps_curve, {}),
    "ipw": (ipw_curve, {}),
}
curves = {}
for k, (fn, kw) in methods.items():
    c = fn(D, **kw); reps = boot(D, fn, B=400, **kw)
    curves[k] = summ(c, reps)
    print(k, curves[k]["diff"], curves[k]["diff_ci"])
res["curves"] = curves

# 県でまとめたブートストラップ（GPS）
reps = boot(D, gps_curve, B=300, cluster=True)
res["gps_cluster"] = summ(gps_curve(D), reps)

# ---- 2. GPS モデルの診断 ----
g = gps_fit(D)
res["gps_model"] = {"r2": round(float(g["gps_model"].rsquared), 3), "sigma": round(float(g["s"]), 2),
                    "resid_skew": round(float(stats.skew(g["resid"])), 3),
                    "resid_kurt": round(float(stats.kurtosis(g["resid"])), 3)}
gs = gps_fit(D, kind="sqrt")
res["gps_model_sqrt"] = {"r2": round(float(gs["gps_model"].rsquared), 3),
                         "resid_skew": round(float(stats.skew(gs["resid"])), 3),
                         "resid_kurt": round(float(stats.kurtosis(gs["resid"])), 3)}

# ---- 3. バランス：処置の3区分ごとに GPS の5分位でブロック（Hirano–Imbens の方法） ----
def balance(d, fe=True):
    t = d[T].values
    grp = pd.qcut(t, 3, labels=False)
    gfit = gps_fit(d, fe=fe)
    rows = []
    for gi in range(3):
        tg = np.median(t[grp == gi])
        rg = gfit["dens"](tg)
        cuts = np.quantile(rg[grp == gi], [0.2, 0.4, 0.6, 0.8])
        blk = np.digitize(rg, cuts)
        for x in X + ["unmarried"]:
            v = d[x].values.astype(float); sd = v.std()
            raw = (v[grp == gi].mean() - v[grp != gi].mean()) / sd
            num = 0; tot = 0
            for b in range(5):
                inb = blk == b; a = inb & (grp == gi); c = inb & (grp != gi)
                if a.sum() >= 2 and c.sum() >= 2:
                    nb = inb.sum(); num += nb * (v[a].mean() - v[c].mean()) / sd; tot += nb
            rows.append(dict(group=gi, var=x, smd_raw=raw, smd_adj=num / tot if tot else np.nan))
    return pd.DataFrame(rows)
bal = balance(D)
bal.to_csv(ROOT / "results/balance.csv", index=False)
bs = bal.groupby("var")[["smd_raw", "smd_adj"]].apply(lambda x: x.abs().max()).round(3)
res["balance_max_abs_smd"] = bs.to_dict(orient="index")

# IPW の重み付き相関（処置と条件）
_, w = ipw_curve(D, return_w=True)
def wcorr(a, b, w):
    ma = np.average(a, weights=w); mb = np.average(b, weights=w)
    return np.average((a-ma)*(b-mb), weights=w) / np.sqrt(np.average((a-ma)**2, weights=w)*np.average((b-mb)**2, weights=w))
res["ipw_corr"] = {x: {"raw": round(float(np.corrcoef(D[T], D[x])[0, 1]), 3),
                       "weighted": round(float(wcorr(D[T].values, D[x].values.astype(float), w)), 3)} for x in X + ["unmarried"]}
res["ipw_weights"] = {"min": round(float(w.min()), 3), "max": round(float(w.max()), 3), "mean": round(float(w.mean()), 3),
                      "ess": round(float(w.sum()**2 / (w**2).sum()), 1)}

# ---- 4. 3区分の傾向スコア（設計の代替案） ----
def three_group(d, fe=True):
    t = d[T].values; grp = pd.qcut(t, 3, labels=False).astype(int)
    Z = design(d, X, fe=False)  # 多項ロジットは県ダミーを入れると収束しにくいので地方ブロックで代用
    reg = pd.get_dummies(d["pref"].astype(int).map(lambda p: 0 if p == 1 else 1 if p <= 7 else 2 if p <= 14 else 3 if p <= 23 else 4 if p <= 30 else 5 if p <= 39 else 6), prefix="r", drop_first=True).astype(float).values
    Zr = np.column_stack([Z, reg]) if fe else Z
    m = sm.MNLogit(grp, Zr).fit(disp=0, maxiter=200)
    p = m.predict(Zr)
    pg = p[np.arange(len(d)), grp]
    w = 1 / pg; w = np.clip(w, None, np.quantile(w, 0.99))
    y = d[Y].values
    means = [np.average(y[grp == k], weights=w[grp == k]) for k in range(3)]
    raw = [y[grp == k].mean() for k in range(3)]
    return np.array(means + raw)
tg = three_group(D); reps = boot(D, three_group, B=300)
cuts = D[T].quantile([1/3, 2/3]).round(1).tolist()
res["three_group"] = {"cuts": cuts, "ipw_means": tg[:3].round(3).tolist(), "raw_means": tg[3:].round(3).tolist(),
                      "ipw_top_minus_bottom": round(float(tg[2]-tg[0]), 4),
                      "ci": [round(float(x), 4) for x in np.percentile(reps[:, 2]-reps[:, 0], [2.5, 97.5])],
                      "raw_top_minus_bottom": round(float(tg[5]-tg[3]), 4)}
print("three", res["three_group"])

# ---- 5. 頑健性（GPS、20%→50% の差） ----
def common_support(d):
    t = d[T].values; grp = pd.qcut(t, 3, labels=False)
    gfit = gps_fit(d); keep = np.ones(len(d), bool)
    for gi in range(3):
        rg = gfit["dens"](np.median(t[grp == gi]))
        lo_ = max(rg[grp == gi].min(), rg[grp != gi].min()); hi_ = min(rg[grp == gi].max(), rg[grp != gi].max())
        keep &= (rg >= lo_) & (rg <= hi_)
    return d[keep].reset_index(drop=True)
DX = D[(D["ward"] == 0) & (~D["tokyo23"])].reset_index(drop=True)
D10 = D[D["pop"] >= 10000].reset_index(drop=True)
DCS = common_support(D)
rob = [
    ("基本", D, dict()),
    ("県ダミーなし", D, dict(fe=False)),
    ("未婚者の割合を条件に足す", D, dict(xs=X + ["unmarried"])),
    ("処置を平方根に変換", D, dict(kind="sqrt")),
    ("結果モデルを3次に", D, dict(outcome="cubic")),
    ("共通サポートに絞る", DCS, dict()),
    ("政令市の区・23区を除く", DX, dict()),
    ("人口1万人以上", D10, dict()),
    ("2013〜17年（2015年の値）", D13, dict()),
]
rows = []
for name, d, kw in rob:
    c = gps_curve(d, **kw); reps = boot(d, gps_curve, B=200, **kw)
    dd = np.array([diff(r) for r in reps])
    ci = np.percentile(dd, [2.5, 97.5])
    ci_ipw = None
    if "kind" not in kw and "outcome" not in kw:
        kw2 = {k: v for k, v in kw.items()}
        ci2 = boot(d, ipw_curve, B=200, **kw2); di = diff(ipw_curve(d, **kw2))
        ci_ipw = [di] + list(np.percentile([diff(r) for r in ci2], [2.5, 97.5]))
    rows.append(dict(setting=name, n=len(d), gps_diff=diff(c), gps_lo=ci[0], gps_hi=ci[1],
                     ipw_diff=ci_ipw[0] if ci_ipw else np.nan, ipw_lo=ci_ipw[1] if ci_ipw else np.nan,
                     ipw_hi=ci_ipw[2] if ci_ipw else np.nan))
    print(rows[-1])
rb = pd.DataFrame(rows).round(4)
rb.to_csv(ROOT / "results/robustness.csv", index=False)
res["robustness"] = rb.to_dict(orient="records")
res["n_common_support"] = int(len(DCS))

pd.DataFrame({"t": GRID, **{f"{k}": v["curve"] for k, v in curves.items()},
              **{f"{k}_lo": v["lo"] for k, v in curves.items()}, **{f"{k}_hi": v["hi"] for k, v in curves.items()}}
             ).to_csv(ROOT / "results/curves.csv", index=False)
json.dump(res, open(ROOT / "results/results.json", "w"), ensure_ascii=False, indent=1, default=float)
print("done")
