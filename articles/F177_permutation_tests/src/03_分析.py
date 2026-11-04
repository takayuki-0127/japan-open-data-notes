"""F177 の分析：「差がある」を、並べ替えで確かめるとどうなるか

例1（F168）：都市15地点と、都市化の影響が少ない15地点で、年最高気温の上がり方の差
例2（F80）：東日本17都道県と西日本30府県で、100指標の差
例3（F98）：災害のあと6か月の宿泊者数の差（被災県 − 対照の県）
人工データ：小さな標本・外れ値・ばらつきの違いで、t 検定と並べ替え検定の「誤って差ありと言う確率」と検出力

頑健性：並べ替えの単位（県をばらばら／つながった塊、月／時期／県）、並べ替えの回数、検定統計量（平均の差・t・中央値・刈り込み平均・順位）、1地点ずつ抜く
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from common import DATA, RES, SEED, welch, student, stat_matrix, random_splits, perm_p

rng = np.random.default_rng(SEED)
out = {}

# ---------------------------------------------------------------- 例1
e1 = pd.read_csv(DATA / "ex1_heat_trend.csv")
x = e1.mu1.values
g = (e1.group == "U").values
N, k = len(x), g.sum()
B1 = 100_000
G = random_splits(N, k, B1, rng)
rows = []
for kind in ["mean", "t", "median", "trim", "rank"]:
    null = stat_matrix(x, G if kind != "median" and kind != "trim" else G[:20_000], kind)
    obs = stat_matrix(x, g[None, :], kind)[0]
    center = k * (N + 1) / 2 if kind == "rank" else None
    rows.append(dict(statistic=kind, observed=obs, B=len(null), p_perm=perm_p(obs, null, center)))
tw, pw = welch(x[g], x[~g]); ts, ps = student(x[g], x[~g])
pm = stats.mannwhitneyu(x[g], x[~g], alternative="two-sided", method="exact").pvalue
ex1 = pd.DataFrame(rows)
ex1["p_welch"], ex1["p_student"], ex1["p_mannwhitney_exact"] = pw, ps, pm
ex1.to_csv(RES / "ex1_statistics.csv", index=False)
null_mean = stat_matrix(x, G, "mean")
np.save(RES / "_ex1_null_mean.npy", null_mean[:20000].astype(np.float32))

# 並べ替えの回数：同じ計算を種を変えて20回
conv = []
for B in [100, 1000, 10000, 100000]:
    ps_ = []
    for r in range(20):
        rr = np.random.default_rng(SEED * 1000 + r)
        Gb = random_splits(N, k, B, rr)
        ps_.append(perm_p(x[g].mean() - x[~g].mean(), stat_matrix(x, Gb, "mean")))
    conv.append(dict(B=B, p_min=min(ps_), p_median=float(np.median(ps_)), p_max=max(ps_),
                     share_below_005=float(np.mean(np.array(ps_) < 0.05))))
pd.DataFrame(conv).to_csv(RES / "ex1_number_of_permutations.csv", index=False)

# 1地点ずつ抜く
loo = []
for i in range(N):
    keep = np.arange(N) != i
    xi, gi = x[keep], g[keep]
    Gi = random_splits(N - 1, gi.sum(), 20000, np.random.default_rng(SEED + i))
    obs = xi[gi].mean() - xi[~gi].mean()
    loo.append(dict(dropped=e1.station[i], group=e1.group[i], diff=obs,
                    p_welch=welch(xi[gi], xi[~gi])[1], p_perm=perm_p(obs, stat_matrix(xi, Gi, "mean"))))
loo = pd.DataFrame(loo)
loo.to_csv(RES / "ex1_leave_one_out.csv", index=False)
out["ex1"] = dict(n_u=int(k), n_r=int(N - k), diff=float(x[g].mean() - x[~g].mean()),
                  p_welch=float(pw), p_student=float(ps), p_mw=float(pm),
                  p_perm={r.statistic: float(r.p_perm) for r in ex1.itertuples()},
                  loo_share_welch_below_005=float((loo.p_welch < 0.05).mean()),
                  loo_share_perm_below_005=float((loo.p_perm < 0.05).mean()),
                  loo_p_range=[float(loo.p_perm.min()), float(loo.p_perm.max())],
                  conv=conv)

# ---------------------------------------------------------------- 例2
E = pd.read_csv(DATA / "ex2_east_west.csv", index_col=0)
meta = pd.read_csv(DATA / "ex2_meta.csv", index_col=0)
gE = E.east.values.astype(bool)
M = E.drop(columns="east").values
codes = E.columns[1:]
B2 = 10000
GR = random_splits(47, gE.sum(), B2, rng)

adj = pd.read_csv(DATA / "raw/f80_adjacency.csv")
nb = {i: set() for i in range(1, 48)}
for o, dd in adj[["o", "d"]].values:
    nb[o].add(dd); nb[dd].add(o)
def contig(kk, r):
    start = int(r.integers(1, 48)); S = {start}; front = set(nb[start])
    while len(S) < kk:
        nxt = int(r.choice(sorted(front))); S.add(nxt); front |= nb[nxt]; front -= S
    gg = np.zeros(47, bool); gg[np.array(sorted(S)) - 1] = True
    return gg
GC = np.array([contig(int(gE.sum()), rng) for _ in range(5000)])

rows = []
for j, c in enumerate(codes):
    v = M[:, j]
    tw, pw = welch(v[gE], v[~gE]); ts, ps = student(v[gE], v[~gE])
    pmw = stats.mannwhitneyu(v[gE], v[~gE], alternative="two-sided").pvalue
    dobs = v[gE].mean() - v[~gE].mean()
    p_rm = perm_p(dobs, stat_matrix(v, GR, "mean"))
    p_rt = perm_p(tw, stat_matrix(v, GR, "t"))
    p_cm = perm_p(dobs, stat_matrix(v, GC, "mean"))
    z = (v - v.mean()) / v.std(ddof=1)
    rows.append(dict(code=c, name=meta.loc[c, "name"], unit=meta.loc[c, "unit"], diff=dobs, t=tw,
                     p_welch=pw, p_student=ps, p_mannwhitney=pmw,
                     p_perm_mean=p_rm, p_perm_t=p_rt, p_contig_mean=p_cm,
                     skew=stats.skew(v), max_abs_z=np.abs(z).max(),
                     tokyo_z=z[12]))
ex2 = pd.DataFrame(rows)
ex2.to_csv(RES / "ex2_per_indicator.csv", index=False)
cnt = {c: int((ex2[c] < 0.05).sum()) for c in ["p_welch", "p_student", "p_mannwhitney", "p_perm_mean", "p_perm_t", "p_contig_mean"]}
disagree = ex2[(ex2.p_welch < 0.05) != (ex2.p_perm_mean < 0.05)]
lr = np.log10(ex2.p_perm_mean / ex2.p_welch)
hi_skew = ex2.max_abs_z >= 4
out["ex2"] = dict(n_east=int(gE.sum()), n_sig=cnt,
                  disagree_welch_vs_perm_mean=int(len(disagree)),
                  disagree_list=disagree[["name", "p_welch", "p_perm_mean", "max_abs_z"]].round(4).to_dict("records"),
                  spearman_welch_perm_mean=float(stats.spearmanr(ex2.p_welch, ex2.p_perm_mean)[0]),
                  median_ratio_perm_over_welch=float(10 ** np.median(lr)),
                  median_ratio_hi_outlier=float(10 ** np.median(lr[hi_skew])), n_hi_outlier=int(hi_skew.sum()),
                  median_ratio_lo_outlier=float(10 ** np.median(lr[~hi_skew])),
                  corr_logratio_maxz=float(stats.spearmanr(lr, ex2.max_abs_z)[0]),
                  sig_welch_and_contig=int(((ex2.p_welch < 0.05) & (ex2.p_contig_mean < 0.05)).sum()),
                  sig_welch_but_not_contig=int(((ex2.p_welch < 0.05) & (ex2.p_contig_mean >= 0.05)).sum()))

# ---------------------------------------------------------------- 例3
L = pd.read_csv(DATA / "ex3_lodging_gap.csv")
POST = range(0, 6)
rows, plc = [], []
for eid, d in L.groupby("event"):
    W = d.pivot(index="k", columns="pref", values="s")
    tr = sorted(d[d.role == "treated"].pref.unique()); dn = sorted(d[d.role == "donor"].pref.unique())
    def gap(trs, dns):
        gg = W[trs].mean(1) - W[dns].mean(1)
        return gg - gg[gg.index < 0].mean()
    gp = gap(tr, dn)
    post, pre = gp.loc[list(POST)], gp[gp.index < 0]
    stat = post.mean()
    # (a) 月をばらばらの標本とみなす t 検定（事後6か月 vs 事前24か月）
    p_t_months = welch(post.values, pre.values)[1]
    p_t_one = stats.ttest_1samp(post.values, 0).pvalue
    # (b) 時期をずらす：事前の期間に「にせの開始月」を置く（6か月の窓が事前に収まるもの）
    fake = [gp.loc[s:s + 5].mean() for s in range(-24, -5)]
    p_time = perm_p(stat, np.array(fake))
    # (c) 県をずらす：対照の県から同じ数を選んで「被災した」とみなす
    ntr = len(tr)
    r = np.random.default_rng(SEED + int(eid[1:]))
    if ntr == 1:
        sets = [[c] for c in dn]
    else:
        sets = [list(r.choice(dn, ntr, replace=False)) for _ in range(2000)]
    vals = np.array([gap(s_, [c for c in dn if c not in s_]).loc[list(POST)].mean() for s_ in sets])
    p_pref = perm_p(stat, vals)
    rows.append(dict(event=eid, name=d.name.iloc[0], n_treated=ntr, n_donors=len(dn), effect_0_5=stat,
                     effect_pct=(np.exp(stat) - 1) * 100,
                     p_t_months=p_t_months, p_t_onesample=p_t_one, p_time_placebo=p_time,
                     n_time_placebo=len(fake), p_pref_placebo=p_pref, n_pref_placebo=len(vals),
                     min_possible_p_pref=1 / (len(vals) + 1),
                     lag1_autocorr_pre=float(pd.Series(pre.values).autocorr(1))))
    for v in vals:
        plc.append(dict(event=eid, value=v))
ex3 = pd.DataFrame(rows)
ex3.to_csv(RES / "ex3_disaster_units.csv", index=False)
pd.DataFrame(plc).to_csv(RES / "_ex3_pref_placebo.csv", index=False)
out["ex3"] = ex3.round(4).to_dict("records")

# ---------------------------------------------------------------- 人工データ
REPS, BP = 2000, 999
def draw(dist, n, r):
    na, nb_ = n, n
    if dist == "normal":
        a, b = r.normal(0, 1, na), r.normal(0, 1, nb_); sh = 1.0
    elif dist == "lognormal":
        a, b = r.lognormal(0, 1, na), r.lognormal(0, 1, nb_); sh = 1.0
    elif dist == "outlier":
        a, b = r.normal(0, 1, na), r.normal(0, 1, nb_); a[0] += 6; sh = 1.0
    elif dist == "unequal":
        a, b = r.normal(0, 3, na), r.normal(0, 1, 2 * n); sh = 1.5
    return a, b, sh
sim = []
for dist in ["normal", "lognormal", "outlier", "unequal"]:
    for n in [5, 10, 15]:
        for eff in [0, 1]:
            r = np.random.default_rng([SEED, ["normal", "lognormal", "outlier", "unequal"].index(dist), n, eff])
            rej = {m: 0 for m in ["welch", "student", "perm_mean", "perm_t", "mannwhitney"]}
            for _ in range(REPS):
                a, b, sh = draw(dist, n, r)
                a = a + eff * sh
                xx = np.r_[a, b]; gg = np.r_[np.ones(len(a), bool), np.zeros(len(b), bool)]
                Gp = random_splits(len(xx), len(a), BP, r)
                dm = a.mean() - b.mean(); tw, pw = welch(a, b)
                rej["welch"] += pw < 0.05
                rej["student"] += student(a, b)[1] < 0.05
                rej["perm_mean"] += perm_p(dm, stat_matrix(xx, Gp, "mean")) < 0.05
                rej["perm_t"] += perm_p(tw, stat_matrix(xx, Gp, "t")) < 0.05
                rej["mannwhitney"] += stats.mannwhitneyu(a, b, alternative="two-sided").pvalue < 0.05
            for m, v in rej.items():
                sim.append(dict(dist=dist, n=n, effect=eff, method=m, reject=v / REPS))
sim = pd.DataFrame(sim)
sim.to_csv(RES / "simulation.csv", index=False)
out["simulation_reps"] = REPS
out["simulation_B"] = BP

json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["ex1", "ex2"]}, ensure_ascii=False, indent=1, default=float)[:6000])
print(ex3.round(4).to_string())
print(sim.pivot_table(index=["dist", "n", "effect"], columns="method", values="reject").round(3).to_string())
