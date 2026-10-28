"""多重比較の分析。

問い：47都道府県を2つに分けて100の指標を比べると、「有意な差」はいくつ出て、そのうちいくつが偶然か。
1. 東日本（北海道・東北・関東・新潟・山梨・長野の17都道県）と西日本（30府県）を100指標で比べる（Welch の t 検定）
2. 補正なし・Bonferroni・Holm・BH（FDR）・BY で、有意の数がどう変わるか
3. 「ただの偶然」の分布：県をでたらめに17と30に分ける（10,000回）／隣どうしがつながるように17県を選ぶ（5,000回）
4. 正解のわかる人工データ（実データの行を並べ替え、20指標にだけ本当の差を足す）で、各補正の誤検出と見落としを測る
5. 頑健性：指標の数、別の分け方（三大都市圏）、順位の検定、2015年版のデータ、指標の選び方の乱数
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
X_all = pd.read_csv(DATA / "indicators_2026.csv", index_col=0)
meta = pd.read_csv(DATA / "indicator_meta.csv", index_col=0)
adj = pd.read_csv(DATA / "adjacency.csv")
N_IND = 100
cols = list(rng.choice(X_all.columns, N_IND, replace=False))
X = X_all[cols]
pd.Series(cols, name="code").to_csv(RES / "chosen_100.csv", index=False)

EAST = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 19, 20]
METRO = [11, 12, 13, 14, 23, 26, 27, 28]
METHODS = {"補正なし": None, "Bonferroni": "bonferroni", "Holm": "holm", "BH (FDR)": "fdr_bh", "BY": "fdr_by"}

def welch_p(M, g):
    """M: 47×k の配列、g: 長さ47の真偽。各列の Welch t 検定の p 値"""
    a, b = M[g], M[~g]
    na, nb = len(a), len(b)
    va, vb = a.var(0, ddof=1), b.var(0, ddof=1)
    se = np.sqrt(va / na + vb / nb)
    t = (a.mean(0) - b.mean(0)) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    return 2 * stats.t.sf(np.abs(t), df), t

def adjust(p, method):
    """多重比較の補正（statsmodels の multipletests と同じ結果になる速い実装）。棄却する指標の真偽を返す"""
    m = len(p); o = np.argsort(p); ps = p[o]; i = np.arange(1, m + 1)
    if method is None:
        return p < 0.05
    if method == "bonferroni":
        return p < 0.05 / m
    rej_s = np.zeros(m, bool)
    if method == "holm":
        ok = ps <= 0.05 / (m - i + 1)
        k = m if ok.all() else int(np.argmin(ok))
        rej_s[:k] = True
    else:
        c = 1.0 if method == "fdr_bh" else np.sum(1.0 / i)
        ok = np.nonzero(ps <= i * 0.05 / (m * c))[0]
        if len(ok): rej_s[:ok.max() + 1] = True
    rej = np.zeros(m, bool); rej[o] = rej_s
    return rej

def n_sig(p, alpha=0.05):
    return {k: int(adjust(p, m).sum()) for k, m in METHODS.items()}

def group(lst):
    return np.isin(np.arange(1, 48), lst)

M = X.values
gE = group(EAST)
p_e, t_e = welch_p(M, gE)
res = {"n_indicators": N_IND, "east_n": int(gE.sum())}
res["east_west"] = n_sig(p_e)
mean_e, mean_w = M[gE].mean(0), M[~gE].mean(0)
d = (mean_e - mean_w) / np.sqrt((M[gE].var(0, ddof=1) + M[~gE].var(0, ddof=1)) / 2)
bh = multipletests(p_e, method="fdr_bh")
holm = multipletests(p_e, method="holm")
tab = pd.DataFrame({"code": cols, "name": meta.loc[cols, "name"].values, "unit": meta.loc[cols, "unit"].values,
                    "east_mean": mean_e, "west_mean": mean_w, "cohen_d": d, "p": p_e,
                    "p_bh": bh[1], "p_holm": holm[1]}).sort_values("p")
tab.to_csv(RES / "east_west_tests.csv", index=False)

# 3. 偶然の分布
def rand_split(k):
    g = np.zeros(47, bool); g[rng.choice(47, k, replace=False)] = True; return g

nb = {i: set() for i in range(1, 48)}
for o, dd in adj[["o", "d"]].values:
    nb[o].add(dd); nb[dd].add(o)
def contig_split(k):
    start = int(rng.integers(1, 48)); S = {start}; front = set(nb[start])
    while len(S) < k:
        nxt = int(rng.choice(sorted(front))); S.add(nxt); front |= nb[nxt]; front -= S
    return group(sorted(S))

def null_counts(fun, k, reps, Mx):
    rows = []
    minp = []
    for _ in range(reps):
        g = fun(k)
        p, _ = welch_p(Mx, g)
        r = n_sig(p); rows.append(r); minp.append(p.min())
    return pd.DataFrame(rows), np.array(minp)

nr, minp_r = null_counts(rand_split, 17, 10000, M)
nc, minp_c = null_counts(contig_split, 17, 5000, M)
nr.to_csv(RES / "null_random_splits.csv", index=False)
nc.to_csv(RES / "null_contiguous_splits.csv", index=False)
res["null_random"] = {k: {"mean": float(nr[k].mean()), "p95": float(nr[k].quantile(.95)),
                          "share_ge1": float((nr[k] >= 1).mean())} for k in METHODS}
res["null_contig"] = {k: {"mean": float(nc[k].mean()), "p95": float(nc[k].quantile(.95)),
                          "share_ge1": float((nc[k] >= 1).mean())} for k in METHODS}
res["east_rank_in_random_raw"] = float((nr["補正なし"] >= res["east_west"]["補正なし"]).mean())
res["east_rank_in_contig_raw"] = float((nc["補正なし"] >= res["east_west"]["補正なし"]).mean())
res["east_rank_in_contig_bh"] = float((nc["BH (FDR)"] >= res["east_west"]["BH (FDR)"]).mean())
# Westfall–Young 型（でたらめな分け方の最小 p の5%点を閾値にする）
thr_r = float(np.quantile(minp_r, 0.05)); thr_c = float(np.quantile(minp_c, 0.05))
res["maxT_random"] = {"threshold": thr_r, "n_sig": int((p_e < thr_r).sum())}
res["maxT_contig"] = {"threshold": thr_c, "n_sig": int((p_e < thr_c).sum())}

# 4. 人工データでの成績
Z = (M - M.mean(0)) / M.std(0, ddof=1)
def simulate(reps, delta, n_true, corr=True):
    out = {k: {"fwer": 0, "fdp": [], "power": []} for k in METHODS}
    for _ in range(reps):
        if corr:
            Zs = Z[rng.permutation(47)]
        else:
            Zs = np.column_stack([rng.permutation(Z[:, j]) for j in range(Z.shape[1])])
        g = rand_split(17)
        Zs = Zs.copy(); Zs[np.ix_(g, np.arange(n_true))] += delta
        p, _ = welch_p(Zs, g)
        for k, m in METHODS.items():
            rej = adjust(p, m)
            fp = rej[n_true:].sum(); tp = rej[:n_true].sum()
            out[k]["fwer"] += fp > 0
            out[k]["fdp"].append(fp / max(rej.sum(), 1))
            out[k]["power"].append(tp / n_true if n_true else np.nan)
    return {k: {"FWER": v["fwer"] / reps, "FDR": float(np.mean(v["fdp"])),
                "power": float(np.nanmean(v["power"])) if n_true else None} for k, v in out.items()}

sim = {"相関あり_差1SD": simulate(2000, 1.0, 20, True),
       "相関なし_差1SD": simulate(2000, 1.0, 20, False),
       "相関あり_差0.7SD": simulate(2000, 0.7, 20, True),
       "全部ゼロ_相関あり": simulate(2000, 0.0, 0, True)}
res["simulation"] = sim

# 5. 頑健性
rob = {}
for n in [25, 50, 100, 200, X_all.shape[1]]:
    cs = list(np.random.default_rng(SEED + 1).choice(X_all.columns, n, replace=False))
    p, _ = welch_p(X_all[cs].values, gE)
    rob[f"東西_指標{n}"] = n_sig(p)
for s in [1, 2, 3]:
    cs = list(np.random.default_rng(100 + s).choice(X_all.columns, 100, replace=False))
    p, _ = welch_p(X_all[cs].values, gE)
    rob[f"東西_選び方seed{100+s}"] = n_sig(p)
gm = group(METRO)
p_m, _ = welch_p(M, gm); rob["三大都市圏8_対_ほか39"] = n_sig(p_m)
pm_mw = np.array([stats.mannwhitneyu(M[gE, j], M[~gE, j]).pvalue for j in range(M.shape[1])])
rob["東西_順位の検定"] = n_sig(pm_mw)
X15 = pd.read_csv(DATA / "indicators_2015ed.csv", index_col=0)
c15 = [c for c in cols if c in X15.columns]
p15, _ = welch_p(X15[c15].values, gE)
p26c, _ = welch_p(X[c15].values, gE)
rob[f"2015年版_同じ指標{len(c15)}"] = n_sig(p15)
rob[f"2026年版_同じ指標{len(c15)}"] = n_sig(p26c)
bh26 = multipletests(p26c, method="fdr_bh")[0]; bh15 = multipletests(p15, method="fdr_bh")[0]
rob["BH有意の一致_2015と2026"] = {"両方": int((bh26 & bh15).sum()), "2026だけ": int((bh26 & ~bh15).sum()),
                                 "2015だけ": int((~bh26 & bh15).sum())}
nm, _ = null_counts(rand_split, 8, 3000, M)
rob["三大都市圏と同じ大きさのでたらめ分割_補正なし平均"] = float(nm["補正なし"].mean())
res["robust"] = rob

# 指標どうしの相関（4,950組）
C = np.corrcoef(Z.T); iu = np.triu_indices(N_IND, 1); r = C[iu]
tt = r * np.sqrt(45 / (1 - r ** 2)); pc = 2 * stats.t.sf(np.abs(tt), 45)
res["pair_corr"] = {"pairs": int(len(r)), **n_sig(pc), "median_abs_r": float(np.median(np.abs(r)))}

(RES / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({k: res[k] for k in ["east_west", "null_random", "null_contig", "east_rank_in_random_raw",
      "east_rank_in_contig_raw", "east_rank_in_contig_bh", "maxT_random", "maxT_contig", "pair_corr"]}, ensure_ascii=False, indent=1))
print(json.dumps(sim, ensure_ascii=False, indent=1)); print(json.dumps(rob, ensure_ascii=False, indent=1))
