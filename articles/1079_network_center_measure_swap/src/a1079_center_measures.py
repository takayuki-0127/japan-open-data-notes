"""1079 「中心の人」は、中心の測り方で入れかわるのか？（架空のデータ）

架空の会社（社員240人・8部署）の1か月のやり取り（やり取りがあった2人をつなぐ）を、作成者が置いた
「人ごとのやり取りの多さ」「部署の中と外のつながりやすさ」と、部署をまたいでつなぐ人（橋渡し役）・
部署の中でやり取りの多い人（部署の人気者）から乱数で作る。中心の測り方4つ（相手の数・間に入る度合い・
近さ・中心の人とのつながり）で上位10人を出し、測り方どうしでどれだけ入れかわるかを、同じ測り方を
翌月にもう一度数えたときの入れかわりと比べる。
"""
import json
import time
from itertools import combinations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1079
SRC = "架空の会社の社内のやり取り（作成者が置いたつながりやすさからの乱数、seed 1079）"
D, PER = 8, 30
N = D * PER
BASE = {"p_in": 0.2, "p_out": 0.003, "spread": 0.6, "n_bridge": 6, "hub_mult": 3.0, "keep_bridge": 0.8}
REPS = 100
GRID_OUT = [0.001, 0.003, 0.01]
GRID_SPREAD = [0.3, 0.6, 1.0]
GRID_BRIDGE = [0, 6, 12]
GRID_REPS = 6
MEAS = ["degree", "between", "close", "eigen"]
MJP = {"degree": "相手の数", "between": "間に入る度合い", "close": "近さ", "eigen": "中心の人とのつながり"}
TOP = 10


def r(x, d=4):
    return round(float(x), d)


def world(rng, p_in, p_out, spread, n_bridge, hub_mult, **_):
    """人ごとのやり取りの多さ・部署・人気者・橋渡し役と、その相手（月をまたいで同じ）"""
    dept = np.repeat(np.arange(D), PER)
    dens = np.linspace(0.7, 1.3, D)               # 部署ごとのやり取りの密さ（作成者が置いた）
    w = np.exp(rng.normal(-spread ** 2 / 2, spread, N))
    hubs = np.array([d * PER + rng.integers(PER) for d in range(D)])
    w[hubs] *= hub_mult
    cand = np.setdiff1d(np.arange(N), hubs)
    bridges = rng.choice(cand, n_bridge, replace=False) if n_bridge else np.array([], dtype=int)
    w[bridges] = 0.5                               # 橋渡し役は部署の中のやり取りは少ない
    partners = []
    for b in bridges:
        others = rng.choice(np.setdiff1d(np.arange(D), [dept[b]]), 3, replace=False)
        ps = [rng.choice(np.where(dept == o)[0], 2, replace=False) for o in others]
        partners.append(np.concatenate(ps))
    same = dept[:, None] == dept[None, :]
    p = np.where(same, p_in * dens[dept][:, None], p_out) * np.outer(w, w)
    return {"dept": dept, "w": w, "hubs": hubs, "bridges": bridges, "partners": partners, "p": np.minimum(p, 1.0)}


def month(rng, W, keep_bridge, **_):
    u = rng.random((N, N))
    a = np.triu(u < W["p"], 1)
    a = a | a.T
    for b, ps in zip(W["bridges"], W["partners"]):
        on = ps[rng.random(len(ps)) < keep_bridge]
        a[b, on] = True; a[on, b] = True
    np.fill_diagonal(a, False)
    return a


def distances(a):
    """全員どうしの道のり（つながりをいくつたどるか）。届かないときは -1"""
    A = a.astype(np.float64)
    dist = np.full((N, N), -1, dtype=np.int64)
    np.fill_diagonal(dist, 0)
    front = np.eye(N, dtype=bool)
    seen = front.copy()
    k = 0
    while front.any():
        k += 1
        nxt = ((front.astype(np.float64) @ A) > 0) & ~seen
        dist[nxt] = k
        seen |= nxt
        front = nxt
    return dist


def centralities(a):
    A = a.astype(np.float64)
    dist = distances(a)
    deg = A.sum(1)
    # 間に入る度合い：ほかの2人のいちばん短い道のりのうち、その人を通る割合の合計（全員から同時に数える）
    maxd = dist.max()
    sig = (dist == 0).astype(np.float64)
    for d in range(1, maxd + 1):
        sig += ((sig * (dist == d - 1)) @ A) * (dist == d)
    delta = np.zeros((N, N))
    for d in range(maxd - 1, 0, -1):
        nxt = dist == d + 1
        X = np.divide(1 + delta, sig, out=np.zeros_like(delta), where=nxt & (sig > 0))
        delta += sig * (X @ A) * (dist == d)
    btw = delta.sum(0) / 2 / ((N - 1) * (N - 2) / 2)
    # 近さ：ほかの人までの道のりの逆数の平均（届かない人は0）
    inv = np.where(dist > 0, 1.0 / np.where(dist > 0, dist, 1), 0.0)
    close = inv.sum(1) / (N - 1)
    # 中心の人とのつながり：つながりの表のいちばん大きい固有値の固有ベクトル
    vals, vecs = np.linalg.eigh(A)
    eig = np.abs(vecs[:, -1])
    return {"degree": deg, "between": btw, "close": close, "eigen": eig}, dist


def top_ids(v, k=TOP):
    return np.lexsort((np.arange(len(v)), -np.round(v, 12)))[:k]   # 同じ値は番号の若い順


def evaluate(rng, kw):
    W = world(rng, **kw)
    a1 = month(rng, W, **kw)
    a2 = month(rng, W, **kw)
    c1, dist = centralities(a1)
    c2, _ = centralities(a2)
    t1 = {m: set(top_ids(c1[m])) for m in MEAS}
    t2 = {m: set(top_ids(c2[m])) for m in MEAS}
    res = {}
    for x, y in combinations(MEAS, 2):
        res[f"ov_{x}_{y}"] = len(t1[x] & t1[y])
        res[f"rc_{x}_{y}"] = pd.Series(c1[x]).rank().corr(pd.Series(c1[y]).rank())
    res["ov_between_measures_mean"] = np.mean([res[f"ov_{x}_{y}"] for x, y in combinations(MEAS, 2)])
    res["in_all4_top"] = len(set.intersection(*t1.values()))
    res["in_any_top"] = len(set.union(*t1.values()))
    tops1 = [int(top_ids(c1[m], 1)[0]) for m in MEAS]
    res["top1_distinct"] = len(set(tops1))
    res["top1_all_same"] = float(len(set(tops1)) == 1)
    for m in MEAS:
        res[f"same_next_{m}"] = len(t1[m] & t2[m])
        res[f"bridges_in_top_{m}"] = len(t1[m] & set(W["bridges"].tolist()))
        res[f"hubs_in_top_{m}"] = len(t1[m] & set(W["hubs"].tolist()))
        res[f"depts_in_top_{m}"] = len(set(W["dept"][list(t1[m])]))
        res[f"top1_same_next_{m}"] = float(top_ids(c1[m], 1)[0] == top_ids(c2[m], 1)[0])
    res["eigen_top_in_densest"] = int((W["dept"][list(t1["eigen"])] == D - 1).sum())
    res["degree_top_in_densest"] = int((W["dept"][list(t1["degree"])] == D - 1).sum())
    res["same_next_mean"] = np.mean([res[f"same_next_{m}"] for m in MEAS])
    res["mean_degree"] = c1["degree"].mean()
    res["reach_all"] = float((dist >= 0).all())
    return res, W, a1, c1


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    first = None
    for i in range(REPS):
        res, W, a1, c1 = evaluate(rng, BASE)
        rows.append({"rep": i, **{k: r(v, 4) for k, v in res.items()}})
        if first is None:
            first = (W, a1, c1)
    br = pd.DataFrame(rows)
    br.to_csv(RES / "base_reps.csv", index=False)
    M = br.mean(numeric_only=True)

    pairs = pd.DataFrame([{"pair": f"{MJP[x]} と {MJP[y]}", "top10_overlap_mean": r(M[f"ov_{x}_{y}"], 2),
                           "rank_corr_mean": r(M[f"rc_{x}_{y}"], 3)} for x, y in combinations(MEAS, 2)])
    pairs.to_csv(RES / "pairs.csv", index=False)
    per = pd.DataFrame([{"measure": MJP[m], "same_next_month_top10_overlap": r(M[f"same_next_{m}"], 2),
                         "top1_same_next_month_pct": r(M[f"top1_same_next_{m}"] * 100, 2),
                         "bridges_in_top10": r(M[f"bridges_in_top_{m}"], 2), "hubs_in_top10": r(M[f"hubs_in_top_{m}"], 2),
                         "depts_in_top10": r(M[f"depts_in_top_{m}"], 2)} for m in MEAS])
    per.to_csv(RES / "by_measure.csv", index=False)

    grid = []
    j = 0
    for po in GRID_OUT:
        for sp in GRID_SPREAD:
            for nb in GRID_BRIDGE:
                g_rng = np.random.default_rng(SEED * 100 + j); j += 1
                kw = dict(BASE, p_out=po, spread=sp, n_bridge=nb)
                rs = pd.DataFrame([evaluate(g_rng, kw)[0] for _ in range(GRID_REPS)]).mean()
                grid.append({"p_out": po, "spread": sp, "n_bridge": nb, "mean_degree": r(rs.mean_degree, 2),
                             "ov_between_measures_mean": r(rs.ov_between_measures_mean, 2),
                             "same_next_mean": r(rs.same_next_mean, 2),
                             "ov_degree_between": r(rs.ov_degree_between, 2), "ov_degree_eigen": r(rs.ov_degree_eigen, 2),
                             "ov_between_eigen": r(rs.ov_between_eigen, 2),
                             "top1_all_same_pct": r(rs.top1_all_same * 100, 1), "in_all4_top": r(rs.in_all4_top, 2),
                             "depts_in_top_eigen": r(rs.depts_in_top_eigen, 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    # data：1回分（1か月目）のやり取りと社員ごとの4つの値
    W, a1, c1 = first
    sid = np.array([f"S{i:03d}" for i in range(N)])
    role = np.full(N, "その他", dtype=object)
    role[W["hubs"]] = "部署の人気者（置いた）"
    role[W["bridges"]] = "橋渡し役（置いた）"
    dn = np.array([chr(65 + k) + "部" for k in range(D)])
    pd.DataFrame({"staff_id": sid, "dept": dn[W["dept"]], "role_set": role,
                  **{m: np.round(c1[m], 6) for m in MEAS}}).to_csv(DATA / "staff_one_run.csv", index=False)
    ii, jj = np.nonzero(np.triu(a1, 1))
    pd.DataFrame({"staff_a": sid[ii], "staff_b": sid[jj]}).to_csv(DATA / "ties_one_run.csv", index=False)

    hl = {"mean_degree": r(M.mean_degree, 2), "reach_all_pct": r(M.reach_all * 100, 2),
          "ov_between_measures_mean": r(M.ov_between_measures_mean, 2), "same_next_mean": r(M.same_next_mean, 2),
          "in_all4_top": r(M.in_all4_top, 2), "in_any_top": r(M.in_any_top, 2),
          "top1_all_same_pct": r(M.top1_all_same * 100, 2), "top1_distinct_mean": r(M.top1_distinct, 2),
          **{f"ov_{x}_{y}": r(M[f"ov_{x}_{y}"], 2) for x, y in combinations(MEAS, 2)},
          **{f"rc_{x}_{y}": r(M[f"rc_{x}_{y}"], 3) for x, y in combinations(MEAS, 2)},
          **{f"same_next_{m}": r(M[f"same_next_{m}"], 2) for m in MEAS},
          **{f"bridges_in_top_{m}": r(M[f"bridges_in_top_{m}"], 2) for m in MEAS},
          **{f"hubs_in_top_{m}": r(M[f"hubs_in_top_{m}"], 2) for m in MEAS},
          **{f"depts_in_top_{m}": r(M[f"depts_in_top_{m}"], 2) for m in MEAS},
          "eigen_top_in_densest": r(M.eigen_top_in_densest, 2), "degree_top_in_densest": r(M.degree_top_in_densest, 2),
          "grid_depts_in_top_eigen_min": r(g.depts_in_top_eigen.min(), 2), "grid_depts_in_top_eigen_max": r(g.depts_in_top_eigen.max(), 2),
          "grid_ov_between_min": r(g.ov_between_measures_mean.min(), 2), "grid_ov_between_max": r(g.ov_between_measures_mean.max(), 2),
          "grid_same_next_min": r(g.same_next_mean.min(), 2), "grid_same_next_max": r(g.same_next_mean.max(), 2),
          "grid_between_lt_next_count": int((g.ov_between_measures_mean < g.same_next_mean).sum()),
          "grid_between_ge_next_count": int((g.ov_between_measures_mean >= g.same_next_mean).sum()),
          "grid_top1_all_same_min_pct": r(g.top1_all_same_pct.min(), 1), "grid_top1_all_same_max_pct": r(g.top1_all_same_pct.max(), 1),
          "grid_ov_degree_between_min": r(g.ov_degree_between.min(), 2), "grid_ov_degree_between_max": r(g.ov_degree_between.max(), 2),
          "grid_ov_degree_eigen_min": r(g.ov_degree_eigen.min(), 2), "grid_ov_degree_eigen_max": r(g.ov_degree_eigen.max(), 2)}
    for nb in GRID_BRIDGE:
        sub = g[g.n_bridge == nb]
        hl[f"grid_bridge{nb}_ov_degree_between_min"] = r(sub.ov_degree_between.min(), 2)
        hl[f"grid_bridge{nb}_ov_degree_between_max"] = r(sub.ov_degree_between.max(), 2)
    out = {"base_setting": dict(BASE, n_staff=N, n_dept=D, dept_density=np.linspace(0.7, 1.3, D).round(3).tolist()),
           "reps": REPS, "grid_reps": GRID_REPS, "headline": hl,
           "pairs": pairs.to_dict("records"), "by_measure": per.to_dict("records"), "grid": g.to_dict("records")}
    json.dump(out, open(RES / "a1079_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：測り方どうしの上位10人の重なりと、同じ測り方の翌月との重なり（棒、0始まり）
    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    SH = {"degree": "相手の数", "between": "間に入る", "close": "近さ", "eigen": "中心との\nつながり"}
    lab = [f"{SH[x]}\n×\n{SH[y]}" for x, y in combinations(MEAS, 2)] + ["同じ測り方を\n翌月に\n（4つの平均）"]
    vals = list(pairs.top10_overlap_mean) + [hl["same_next_mean"]]
    cols = [BLUE] * len(pairs) + [GRAY]
    xx = np.arange(len(vals))
    ax.bar(xx, vals, .62, color=cols)
    for x_, v in zip(xx, vals):
        ax.text(x_, v + .15, f"{v:.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(xx); ax.set_xticklabels(lab, fontsize=8)
    ax.set_ylim(0, 10.5); ax.set_ylabel("上位10人のうち重なった人数（100回の平均）")
    ax.set_title("測り方の組で、上位10人の重なりは大きく違う（灰色は翌月に測り直したとき）")
    save(fig, "a1079_overlap.png", SRC, y=-0.1)

    # 図2：上位10人に入った、置いた橋渡し役・部署の人気者の人数と、上位10人の部署の数（棒、0始まり）
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    xx = np.arange(len(MEAS)); wd = .27
    b1 = [hl[f"bridges_in_top_{m}"] for m in MEAS]
    b2 = [hl[f"hubs_in_top_{m}"] for m in MEAS]
    b3 = [hl[f"depts_in_top_{m}"] for m in MEAS]
    for k_, (vs, c, nm) in enumerate([(b1, ORANGE, f"橋渡し役（置いた{BASE['n_bridge']}人）"),
                                      (b2, BLUE, f"部署の人気者（置いた{D}人）"), (b3, GRAY, "上位10人の部署の数（8部署）")]):
        ax.bar(xx + (k_ - 1) * wd, vs, wd, color=c, label=nm)
        for x_, v in zip(xx + (k_ - 1) * wd, vs):
            ax.text(x_, v + .12, f"{v:.2f}", ha="center", fontsize=7.6)
    ax.set_xticks(xx); ax.set_xticklabels([MJP[m] for m in MEAS])
    ax.set_ylim(0, 10); ax.set_ylabel("人数・部署の数（100回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("上位10人に入る人の種類が、測り方で違う")
    save(fig, "a1079_roles.png", SRC)

    # 図3：27通りの、測り方どうしの重なりと翌月との重なり
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    cl = {0: GRAY, 6: BLUE, 12: ORANGE}
    mk = {0.001: "o", 0.003: "s", 0.01: "^"}
    for (nb, po), gg in g.groupby(["n_bridge", "p_out"]):
        ax.scatter(gg.same_next_mean, gg.ov_between_measures_mean, color=cl[nb], marker=mk[po], s=36, zorder=3)
    ax.plot([0, 10], [0, 10], color=INK, lw=.7, ls="--")
    for nb, c in cl.items():
        ax.scatter([], [], color=c, marker="o", label=f"橋渡し役 {nb}人")
    for po, m_ in mk.items():
        ax.scatter([], [], color=INK, marker=m_, label=f"部署の外とのつながりやすさ {po}")
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.text(9.6, 9.0, "同じ", fontsize=8.5, ha="right")
    ax.set_xlabel("同じ測り方で翌月に測り直したときの、上位10人の重なり（人）")
    ax.set_ylabel("測り方どうしの上位10人の重なり（人、6組の平均）")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("27通り（各6回）：点線より下なら、測り方の違いのほうが大きい")
    save(fig, "a1079_grid.png", SRC)

    print(json.dumps(hl, ensure_ascii=False, indent=1)); print(pairs.to_string()); print(per.to_string()); print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
