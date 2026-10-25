"""中心性とコミュニティ検出（Leiden）。"""
import json
import numpy as np
import pandas as pd
import igraph as ig
import leidenalg as la
import networkx as nx
from collections import Counter
from sklearn.metrics import adjusted_rand_score as ARI, normalized_mutual_info_score as NMI
from common import DATA, RES, SEED

RES.mkdir(exist_ok=True)
YEARS = ["1990", "2000", "2010", "2025"]
mig = {y: pd.read_csv(DATA / f"migration_{y}.csv", index_col=0) for y in YEARS + ["2025all"]}
PREF = list(mig["2025"].index)
pop = pd.read_csv(DATA / "pref_pop.csv", index_col=0)
N_SEEDS = 100

def sym(M):
    A = M + M.T
    np.fill_diagonal(A, 0)
    return A.astype(float)

def normalize(A, how, popv=None):
    if how == "count":
        return A
    if how == "lift":  # 出し入れの大きさで期待される量との比
        s = A.sum(1); S = s.sum()
        E = np.outer(s, s) / S
        return np.where(E > 0, A / E, 0)
    if how == "pop":  # 人口の積で割る（人口あたりの結びつき）
        P = np.outer(popv, popv)
        B = A / P
        return B / B.sum() * A.sum()
    raise ValueError(how)

def graph(W, names):
    iu = np.triu_indices_from(W, 1)
    edges = [(i, j) for i, j in zip(*iu) if W[i, j] > 0]
    g = ig.Graph(n=len(names), edges=edges)
    g.vs["name"] = names
    g.es["weight"] = [W[i, j] for i, j in edges]
    return g

def leiden(g, res, seed):
    p = la.find_partition(g, la.RBConfigurationVertexPartition, weights="weight",
                          resolution_parameter=res, seed=seed, n_iterations=-1)
    return np.array(p.membership), g.modularity(p.membership, weights="weight")

def canon(m):
    # 番号の付け方をそろえる（最初に出てきた順）
    mp = {}; out = []
    for x in m:
        mp.setdefault(x, len(mp)); out.append(mp[x])
    return tuple(out)

def stable(g, res, n=N_SEEDS):
    parts = [canon(leiden(g, res, SEED + s)[0]) for s in range(n)]
    cnt = Counter(parts)
    best, freq = cnt.most_common(1)[0]
    # 同じ組になった割合（共起行列）
    P = np.array(parts); k = P.shape[1]
    co = np.zeros((k, k))
    for p in P:
        co += (p[:, None] == p[None, :])
    co /= len(P)
    q = g.modularity(list(best), weights="weight")
    return np.array(best), freq / n, co, q

out = {}
# 1) 中心性（向きつき・重みつき）
cen = []
for y in YEARS:
    M = mig[y].values.astype(float)
    G = nx.DiGraph()
    for i, a in enumerate(PREF):
        for j, b in enumerate(PREF):
            if i != j and M[i, j] > 0:
                G.add_edge(a, b, weight=M[i, j])
    pr = nx.pagerank(G, weight="weight")
    for i, a in enumerate(PREF):
        cen.append({"year": y, "pref": a, "in": M[:, i].sum(), "out": M[i, :].sum(), "net": M[:, i].sum() - M[i, :].sum(), "pagerank": pr[a]})
cen = pd.DataFrame(cen)
cen["pr_rank"] = cen.groupby("year")["pagerank"].rank(ascending=False).astype(int)
cen.to_csv(RES / "centrality.csv", index=False)

# 東京圏（埼玉・千葉・東京・神奈川）への流れの割合（他の道府県からの移動のうち）
TK = [PREF.index(p) for p in ["埼玉県", "千葉県", "東京都", "神奈川県"]]
share = {}
for y in YEARS:
    M = mig[y].values
    others = [i for i in range(47) if i not in TK]
    share[y] = {"to_tokyo_area_share": float(M[np.ix_(others, TK)].sum() / M[others, :].sum()),
                "total": int(M.sum())}
out["tokyo_share"] = share

# 2) コミュニティ：解像度 × 正規化 × 年
rows = []; parts = {}
RESOS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
for y in YEARS:
    A = sym(mig[y].values)
    popv = pop["jp2012"].values if y in ("1990", "2000", "2010") else pop["jp2023"].values
    for how in ["count", "lift", "pop"]:
        if how == "pop" and y in ("1990", "2000"):
            continue  # 人口の表がないので 2010・2025 だけ
        W = normalize(A, how, popv)
        g = graph(W, PREF)
        for r in RESOS:
            m, freq, co, q = stable(g, r)
            parts[(y, how, r)] = m
            iu = np.triu_indices_from(co, 1)
            rows.append({"year": y, "norm": how, "resolution": r, "n_comm": len(set(m)), "modularity": q,
                         "share_pairs_always_same_or_apart": float(np.mean((co[iu] > 0.95) | (co[iu] < 0.05))),
                         "top_partition_share": freq,
                         "mean_coassign_uncertainty": float(np.mean(np.minimum(co, 1 - co)))})
grid = pd.DataFrame(rows)
grid.to_csv(RES / "community_grid.csv", index=False)

memb = pd.DataFrame({f"{y}_{h}_{r}": m for (y, h, r), m in parts.items()}, index=PREF)
memb.to_csv(RES / "membership_pref.csv")

# 年どうし・正規化どうしの一致（ARI）
cmp = []
for r in [1.0]:
    for a in YEARS:
        for b in YEARS:
            cmp.append({"what": "year", "a": a, "b": b, "res": r, "ARI": ARI(parts[(a, "count", r)], parts[(b, "count", r)]),
                        "NMI": NMI(parts[(a, "count", r)], parts[(b, "count", r)])})
    for y in ["2010", "2025"]:
        for h in ["lift", "pop"]:
            cmp.append({"what": "norm", "a": f"{y}_count", "b": f"{y}_{h}", "res": r,
                        "ARI": ARI(parts[(y, "count", r)], parts[(y, h, r)]), "NMI": NMI(parts[(y, "count", r)], parts[(y, h, r)])})
    # 外国人を含めた 2025
    A = sym(mig["2025all"].values); g = graph(A, PREF); m, *_ = stable(g, r)
    parts[("2025all", "count", r)] = m
    cmp.append({"what": "foreign", "a": "2025_count", "b": "2025all_count", "res": r,
                "ARI": ARI(parts[("2025", "count", r)], m), "NMI": NMI(parts[("2025", "count", r)], m)})
pd.DataFrame(cmp).to_csv(RES / "partition_agreement.csv", index=False)

# 地方ブロック（8地方）との一致
BLOCK = [0]*1 + [1]*6 + [2]*7 + [3]*9 + [4]*7 + [5]*5 + [6]*4 + [7]*8
blk = []
for y in YEARS:
    for r in RESOS:
        blk.append({"year": y, "res": r, "NMI_vs_8blocks": NMI(BLOCK, parts[(y, "count", r)]), "ARI_vs_8blocks": ARI(BLOCK, parts[(y, "count", r)])})
pd.DataFrame(blk).to_csv(RES / "vs_regional_blocks.csv", index=False)

# 3) 通勤：1都3県の市区町村
od = pd.read_csv(DATA / "commute_od.csv", dtype={"res": str, "work": str})
mun = pd.read_csv(DATA / "commute_municipalities.csv", dtype={"code": str})
codes = sorted(set(mun["code"]))
ix = {c: i for i, c in enumerate(codes)}
C = np.zeros((len(codes), len(codes)))
for r_, w_, n in od.itertuples(index=False):
    if r_ in ix and w_ in ix:
        C[ix[r_], ix[w_]] += n
Gd = nx.DiGraph()
for i in range(len(codes)):
    for j in range(len(codes)):
        if C[i, j] > 0:
            Gd.add_edge(codes[i], codes[j], weight=C[i, j])
prc = nx.pagerank(Gd, weight="weight")
mun = mun.set_index("code").reindex(codes)
mun["in_commuters"] = C.sum(0); mun["out_commuters"] = C.sum(1); mun["pagerank"] = [prc.get(c, 0) for c in codes]
A = C + C.T
gC = graph(A, codes)
crow = []; cparts = {}
for r in [0.5, 1.0, 1.5, 2.0, 3.0]:
    m, freq, co, q = stable(gC, r, n=50)
    cparts[r] = m
    pref_lab = [c[:2] for c in codes]
    iu = np.triu_indices_from(co, 1)
    crow.append({"resolution": r, "n_comm": len(set(m)), "modularity": q, "top_partition_share": freq,
                 "share_pairs_always_same_or_apart": float(np.mean((co[iu] > 0.95) | (co[iu] < 0.05))),
                 "NMI_vs_pref": NMI(pref_lab, m)})
# 10%ルールの通勤圏（その市区町村の就業者の10%以上が通う先のうち最大のところにつなぐ。たどった先を中心とする）
wk = mun["workers15_all"].values
best = C.argmax(1); bshare = C.max(1) / np.where(wk > 0, wk, 1)
parent = np.where(bshare >= 0.10, best, np.arange(len(codes)))
def root(i, seen=None):
    seen = seen or set()
    while parent[i] != i and i not in seen:
        seen.add(i); i = parent[i]
    return i
rule = np.array([root(i) for i in range(len(codes))])
for r, m in cparts.items():
    for d in crow:
        if d["resolution"] == r:
            d["NMI_vs_10pct_rule"] = NMI(rule, m); d["ARI_vs_10pct_rule"] = ARI(rule, m)
pd.DataFrame(crow).to_csv(RES / "commute_grid.csv", index=False)
for r, m in cparts.items():
    mun[f"comm_{r}"] = m
mun["rule10_core"] = [codes[i] for i in rule]
mun.reset_index().to_csv(RES / "commute_nodes.csv", index=False)

# 通勤のまとまりの中身（解像度1）
m1 = cparts[1.0]
summ = []
for c in sorted(set(m1)):
    idx = np.where(m1 == c)[0]
    inside = C[np.ix_(idx, idx)].sum(); outall = C[idx, :].sum()
    top = mun.iloc[idx].sort_values("in_commuters", ascending=False)
    summ.append({"comm": int(c), "n_mun": len(idx), "workers": int(mun.iloc[idx]["workers15_all"].sum()),
                 "inside_share_of_outcommute": float(inside / outall) if outall else np.nan,
                 "top_in": "・".join(top["name"].head(3)), "prefs": "・".join(sorted(set(c_[:2] for c_ in np.array(codes)[idx])))})
pd.DataFrame(summ).to_csv(RES / "commute_communities_r1.csv", index=False)
out["commute_total_flow"] = float(C.sum()); out["n_municipalities"] = len(codes)
out["rule10_n_cores"] = int(len(set(rule)))
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(grid[grid.norm == "count"].pivot(index="resolution", columns="year", values="n_comm"))
print(pd.DataFrame(crow))
print(json.dumps(out, ensure_ascii=False))
