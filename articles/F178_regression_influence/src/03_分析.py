"""F178 回帰の外れ値は、どの点がどれだけ結論を動かしているか（影響度の診断）"""
import itertools, json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from common import DATA, RES, SEED, ols, influence_table

rng = np.random.default_rng(SEED)
RES.mkdir(exist_ok=True)
M = pd.read_csv(DATA / "pref_master.csv").set_index("pref")
DAG = ["did", "income", "univ_grad", "aged65", "temp", "unemp"]
SPECS = {
    "A_物価と所得": ("ln_price", ["ln_inc"], "ln_inc"),
    "B1_男性の寿命と医師（調整なし）": ("e0_m_2015", ["doctors"], "doctors"),
    "B2_男性の寿命と医師（DAG＋気温・失業）": ("e0_m_2015", ["doctors"] + DAG, "doctors"),
    "B3_女性の寿命と医師（調整なし）": ("e0_f_2015", ["doctors"], "doctors"),
    "B4_女性の寿命と医師（DAG＋気温・失業）": ("e0_f_2015", ["doctors"] + DAG, "doctors"),
}


def sig(p):
    return p < 0.05


def greedy_flip(y, X, focus, max_steps=10):
    """結論（p<0.05 か否か）が変わるまで、毎回いちばん効く1県を除く。変わったときの除いた数と県"""
    keep = np.ones(len(y), bool); base = sig(ols(y, X).pvalues[focus]); removed = []
    for step in range(1, max_steps + 1):
        best = None
        for i in np.where(keep)[0]:
            m = keep.copy(); m[i] = False
            p = ols(y[m], X[m]).pvalues[focus]
            score = p if base else -p          # 有意なら p を上げる県、有意でなければ p を下げる県
            if best is None or score > best[0]:
                best = (score, i, p)
        keep[best[1]] = False; removed.append(y.index[best[1]])
        if sig(best[2]) != base:
            return step, removed, best[2]
    return None, removed, best[2]


summary, tables, l2o_rows = [], [], []
for name, (yv, xv, focus) in SPECS.items():
    y, X = M[yv], M[xv]
    fit, t, n, k = influence_table(y, X, focus)
    t.insert(0, "model", name); tables.append(t)
    b, p = fit.params[focus], fit.pvalues[focus]
    # 2県ずつ除く（1,081通り）
    l2 = []
    for i, j in itertools.combinations(range(n), 2):
        m = np.ones(n, bool); m[[i, j]] = False
        f = ols(y[m], X[m]); l2.append((f.params[focus], f.pvalues[focus]))
    l2 = np.array(l2)
    l2o_rows += [{"model": name, "coef": c, "p": q} for c, q in l2]
    steps, removed, pend = greedy_flip(y, X, focus)
    hub = sm.RLM(y, sm.add_constant(X), M=sm.robust.norms.HuberT()).fit()
    hc3 = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HC3")
    bs = []
    for _ in range(2000):
        ii = rng.integers(0, n, n); bs.append(ols(y.iloc[ii], X.iloc[ii]).params[focus])
    bs = np.array(bs)
    qr = sm.QuantReg(y, sm.add_constant(X)).fit(q=0.5)
    fmed = stats.f.ppf(0.5, k, n - k)
    rank = stats.spearmanr(t.cook, t.dfbeta.abs()).statistic
    rank2 = stats.spearmanr(t.dfbeta.abs(), t.coef_change.abs()).statistic
    top_cook = t.loc[t.cook.idxmax()]; top_dfb = t.loc[t.dfbeta.abs().idxmax()]
    summary.append(dict(
        model=name, n=n, k=k, coef=b, se=fit.bse[focus], p=p, ci_lo=fit.conf_int().loc[focus, 0], ci_hi=fit.conf_int().loc[focus, 1],
        cook_over_4n=int((t.cook > 4 / n).sum()), cook_over_fmed=int((t.cook > fmed).sum()), cook_over_1=int((t.cook > 1).sum()),
        dfb_over_2rootn=int((t.dfbeta.abs() > 2 / np.sqrt(n)).sum()), dfb_over_1=int((t.dfbeta.abs() > 1).sum()),
        top_cook_pref=top_cook.pref, top_cook=top_cook.cook, top_dfb_pref=top_dfb.pref, top_dfb=top_dfb.dfbeta,
        top_dfb_coef_without=top_dfb.coef_without, top_dfb_p_without=top_dfb.p_without,
        loo_min=t.coef_without.min(), loo_max=t.coef_without.max(), loo_sig_flips=int((sig(t.p_without) != sig(p)).sum()),
        loo_sign_flips=int((np.sign(t.coef_without) != np.sign(b)).sum()),
        l2o_min=l2[:, 0].min(), l2o_max=l2[:, 0].max(), l2o_sig_flip_share=float((sig(l2[:, 1]) != sig(p)).mean()),
        greedy_steps=steps, greedy_removed="・".join(removed[:steps] if steps else removed), greedy_p_end=pend,
        hc3_p=hc3.pvalues[focus], boot_lo=np.percentile(bs, 2.5), boot_hi=np.percentile(bs, 97.5),
        huber_coef=hub.params[focus], huber_p=hub.pvalues[focus], lad_coef=qr.params[focus], lad_p=qr.pvalues[focus],
        spearman_cook_dfb=rank, spearman_dfb_loo=rank2))

S = pd.DataFrame(summary); S.to_csv(RES / "model_summary.csv", index=False)
pd.concat(tables).to_csv(RES / "influence_by_pref.csv", index=False)
pd.DataFrame(l2o_rows).to_csv(RES / "leave_two_out.csv", index=False)

# ---------- F80 の指標どうしの単回帰（全組み合わせ） ----------
ind = pd.read_csv(DATA / "f80_sweep_indicators.csv").set_index("pref_code")
pref_name = M.reset_index().set_index("pref_code").pref
codes = list(ind.columns); V = ind.values.astype(float); n = V.shape[0]


def biv(x, y):
    """単回帰の傾き・p・DFBETA（傾き）・Cook の距離を numpy で計算"""
    xc = x - x.mean(); sxx = (xc ** 2).sum(); bt = (xc * (y - y.mean())).sum() / sxx
    a = y.mean() - bt * x.mean(); e = y - a - bt * x; m = len(x)
    s2 = (e ** 2).sum() / (m - 2); se = np.sqrt(s2 / sxx); p = 2 * stats.t.sf(abs(bt / se), m - 2)
    h = 1 / m + xc ** 2 / sxx
    s2i = ((e ** 2).sum() - e ** 2 / (1 - h)) / (m - 3)              # i を除いた分散
    dfb = (xc / sxx) * e / (1 - h) / np.sqrt(s2i / sxx)               # 傾きの DFBETAS
    cook = e ** 2 / (2 * s2) * h / (1 - h) ** 2
    return bt, p, dfb, cook


def hc3_p(x, y):
    xc = x - x.mean(); sxx = (xc ** 2).sum(); bt = (xc * (y - y.mean())).sum() / sxx
    e = y - y.mean() - bt * xc; m = len(x); h = 1 / m + xc ** 2 / sxx
    se = np.sqrt((xc ** 2 * e ** 2 / (1 - h) ** 2).sum()) / sxx
    return 2 * stats.t.sf(abs(bt / se), m - 2)


def drop_p(x, y, i):
    m = np.ones(len(x), bool); m[i] = False
    return biv(x[m], y[m])[:2]


def greedy_biv(x, y, base, max_steps=5):
    keep = np.arange(len(x))
    for step in range(1, max_steps + 1):
        best = None
        for i in range(len(keep)):
            m = np.delete(keep, i); p = biv(x[m], y[m])[1]
            sc = p if base else -p
            if best is None or sc > best[0]:
                best = (sc, i, p)
        keep = np.delete(keep, best[1])
        if sig(best[2]) != base:
            return step
    return np.nan


rows = []
for i, j in itertools.combinations(range(len(codes)), 2):
    x, y = V[:, i], V[:, j]
    bt, p, dfb, cook = biv(x, y)
    it, ic = int(np.argmax(np.abs(dfb))), int(np.argmax(cook))
    bt1, p1 = drop_p(x, y, it); _, p2 = drop_p(x, y, ic)
    r = dict(x=codes[i], y=codes[j], slope=bt, p=p, top_dfb_pref=int(ind.index[it]), max_abs_dfb=abs(dfb[it]),
             p_drop_top_dfb=p1, slope_drop_top_dfb=bt1, top_cook_pref=int(ind.index[ic]), max_cook=cook[ic], p_drop_top_cook=p2,
             n_dfb_over_2rootn=int((np.abs(dfb) > 2 / np.sqrt(n)).sum()))
    # 逆向き（x を y で説明）でも、最も効く県を除いたときの判定
    _, _, dfb_r, _ = biv(y, x); ir = int(np.argmax(np.abs(dfb_r))); r["p_drop_top_dfb_reverse"] = drop_p(y, x, ir)[1]
    # 頑健回帰（Huber）と順位相関
    hub = sm.RLM(y, sm.add_constant(x), M=sm.robust.norms.HuberT()).fit(); r["huber_p"] = hub.pvalues[1]
    r["spearman_p"] = stats.spearmanr(x, y).pvalue
    r["hc3_p"] = hc3_p(x, y)
    # 対数（両方とも正のとき）
    if (x > 0).all() and (y > 0).all():
        r["log_p"] = biv(np.log(x), np.log(y))[1]
    rows.append(r)
P = pd.DataFrame(rows)
sigm = P.p < 0.05
for c in ["drop_top_dfb", "drop_top_cook", "drop_top_dfb_reverse"]:
    P["flip_" + c] = sig(P["p_" + c]) != sigm
# 1点で結論が変わる組のうち、何点で変わるかを貪欲法で（有意な組だけ、5点まで）
P["greedy_steps"] = np.nan
idx = P.index[sigm]
for k_ in idx:
    i, j = codes.index(P.at[k_, "x"]), codes.index(P.at[k_, "y"])
    P.at[k_, "greedy_steps"] = greedy_biv(V[:, i], V[:, j], True)
P.to_csv(RES / "f80_pairs.csv", index=False)

# ---------- 比べる基準：正規分布のデータなら、1点で結論が変わるのはどれくらいか ----------
sim = []
for dist in ["正規", "t分布（自由度3）"]:
    for rho in np.linspace(0.05, 0.75, 15):
        for _ in range(400):
            z = rng.standard_normal((n, 2)) if dist == "正規" else rng.standard_t(3, (n, 2))
            x = z[:, 0]; y = rho * x + np.sqrt(1 - rho ** 2) * z[:, 1]
            bt, p, dfb, cook = biv(x, y); it = int(np.argmax(np.abs(dfb)))
            sim.append(dict(dist=dist, rho=rho, p=p, p_drop=drop_p(x, y, it)[1], max_abs_dfb=abs(dfb[it]),
                            n_dfb_over_2rootn=int((np.abs(dfb) > 2 / np.sqrt(n)).sum())))
SIM = pd.DataFrame(sim); SIM["flip"] = sig(SIM.p) != sig(SIM.p_drop); SIM.to_csv(RES / "simulation_baseline.csv", index=False)

bins = [0, 1e-6, 1e-4, 1e-3, 0.01, 0.05, 0.2, 1]
lab = ["<1e-6", "1e-6〜1e-4", "1e-4〜0.001", "0.001〜0.01", "0.01〜0.05", "0.05〜0.2", "0.2〜1"]
P["pbin"] = pd.cut(P.p, bins, labels=lab); SIM["pbin"] = pd.cut(SIM.p, bins, labels=lab)
byp = P.groupby("pbin", observed=False).agg(n_pairs=("p", "size"), flip_real=("flip_drop_top_dfb", "mean"),
                                            maxdfb_real=("max_abs_dfb", "median"))
for d in SIM.dist.unique():
    g = SIM[SIM.dist == d].groupby("pbin", observed=False).agg(flip=("flip", "mean"), maxdfb=("max_abs_dfb", "median"), ns=("flip", "size"))
    byp["flip_sim_" + d] = g.flip; byp["maxdfb_sim_" + d] = g.maxdfb; byp["n_sim_" + d] = g.ns
byp.to_csv(RES / "flip_by_pbin.csv")

# 最も効く県がどこか（集計のみ。評価ではなく、値が分布の端にあるかどうか）
top = P.loc[sigm, "top_dfb_pref"].map(pref_name).value_counts()
top.rename("n_pairs").to_csv(RES / "top_influential_pref_counts.csv")

sp = P[sigm]
out = dict(
    n_indicators=len(codes), n_pairs=len(P), n_sig=int(sigm.sum()),
    flip_drop_top_dfb=float(sp.flip_drop_top_dfb.mean()), flip_drop_top_cook=float(sp.flip_drop_top_cook.mean()),
    flip_reverse=float(sp.flip_drop_top_dfb_reverse.mean()),
    flip_either_direction=float((sp.flip_drop_top_dfb | sp.flip_drop_top_dfb_reverse).mean()),
    sign_flip_drop_top=float((np.sign(sp.slope_drop_top_dfb) != np.sign(sp.slope)).mean()),
    nonsig_to_sig=float(P.loc[~sigm, "flip_drop_top_dfb"].mean()),
    hc3_disagree=float((sig(sp.hc3_p) == False).mean()),
    huber_disagree=float((sig(sp.huber_p) == False).mean()), spearman_disagree=float((sig(sp.spearman_p) == False).mean()),
    log_disagree=float((sig(sp.log_p.dropna()) == False).mean()), n_log=int(sp.log_p.notna().sum()),
    greedy_steps_dist=sp.greedy_steps.value_counts(dropna=False).sort_index().to_dict(),
    near_sig_share=float(((sp.p > 0.01)).mean()),
    flip_given_p_lt_001=float(sp[sp.p < 0.001].flip_drop_top_dfb.mean()),
    flip_given_p_001_005=float(sp[sp.p >= 0.01].flip_drop_top_dfb.mean()),
    tokyo_top_share=float((sp.top_dfb_pref == 13).mean()),
    top_pref_concentration_top3=float(top.head(3).sum() / top.sum()),
    sim_normal_flip_sig=float(SIM[(SIM.dist == "正規") & (SIM.p < 0.05)].flip.mean()),
    sim_t3_flip_sig=float(SIM[(SIM.dist != "正規") & (SIM.p < 0.05)].flip.mean()),
    real_maxdfb_median=float(P.max_abs_dfb.median()), sim_normal_maxdfb_median=float(SIM[SIM.dist == "正規"].max_abs_dfb.median()),
    sim_t3_maxdfb_median=float(SIM[SIM.dist != "正規"].max_abs_dfb.median()),
    threshold_2rootn=2 / np.sqrt(n), real_n_over=float(P.n_dfb_over_2rootn.mean()),
    sim_normal_n_over=float(SIM[SIM.dist == "正規"].n_dfb_over_2rootn.mean()))
json.dump(out, open(RES / "f80_sweep_summary.json", "w"), ensure_ascii=False, indent=1, default=float)
pd.set_option("display.width", 250)
print(S.T.to_string())
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
print(byp.to_string())
print(top.head(8).to_string())
