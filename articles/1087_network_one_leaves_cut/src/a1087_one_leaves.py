"""1087 1人が抜けると、全体のつながりはどれだけ切れるのか？（架空のデータ）

架空の会社（社員300人、10部署×30人）の仕事のやり取りのつながりを、作成者が置いた確率から乱数で作る。
部署の中は互いにやり取りしやすく、部署をまたぐやり取りは少なく、一部の人に集まる（窓口になる人）。
1人ずつ抜いて（異動などで抜けたとして）、①切れたつながりの数、②行き来できなくなった2人の組、
③遠回りになった分（全体の近さ＝距離の逆数の平均の下がり方）の3つの物差しで「どれだけ切れたか」を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, shortest_path
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1087
SRC = "架空の会社の社員どうしのやり取り（作成者が置いた確率からの乱数、seed 1087）"
N_DEPT, DEPT_SIZE = 10, 30
N = N_DEPT * DEPT_SIZE
BASE = {"p_in": 0.15, "cross": 30, "cv_cross": 2.0}
REPS = 60
GRID_CROSS = [15, 30, 60]
GRID_CV = [0.5, 2.0]
GRID_REPS = 30


def r(x, d=4):
    return round(float(x), d)


def company(rng, p_in=BASE["p_in"], cross=BASE["cross"], cv_cross=BASE["cv_cross"]):
    dept = np.arange(N) // DEPT_SIZE
    same = dept[:, None] == dept[None, :]
    u = rng.random((N, N))
    a = np.triu((u < p_in) & same, 1)
    # 部署をまたぐやり取り：外とのやり取りの多さ（ガンマ分布、変動係数 cv_cross）に比例して両端を選ぶ
    k = 1 / cv_cross ** 2
    w = rng.gamma(k, 1 / k, N)
    p = w / w.sum()
    made = 0
    while made < cross:
        i, j = rng.choice(N, 2, p=p)
        if dept[i] == dept[j]:
            continue
        lo, hi = min(i, j), max(i, j)
        if a[lo, hi]:
            continue
        a[lo, hi] = True
        made += 1
    a = a | a.T
    return a, dept


def reach_pairs(a, keep):
    sub = a[np.ix_(keep, keep)]
    _, lab = connected_components(csr_matrix(sub), directed=False)
    cnt = np.bincount(lab)
    return float((cnt * (cnt - 1) // 2).sum())


def efficiency(a, keep):
    sub = a[np.ix_(keep, keep)]
    d = shortest_path(csr_matrix(sub), directed=False, unweighted=True)
    n = len(keep)
    with np.errstate(divide="ignore"):
        inv = np.where(np.isfinite(d) & (d > 0), 1.0 / d, 0.0)
    return float(inv.sum() / (n * (n - 1)))


def removal_table(a, with_eff=False, with_btw=True):
    deg = a.sum(1)
    allk = np.arange(N)
    base_reach = reach_pairs(a, allk)
    base_eff = efficiency(a, allk) if with_eff else None
    tot_pairs_others = (N - 1) * (N - 2) / 2
    _, lab = connected_components(csr_matrix(a), directed=False)
    rows = []
    for i in range(N):
        keep = np.delete(allk, i)
        # i を含む組を除いた、もとの行き来できる組の数
        before = base_reach - (np.sum(lab == lab[i]) - 1)
        after = reach_pairs(a, keep)
        row = {"person": i, "deg": int(deg[i]), "cut_pairs_share": (before - after) / tot_pairs_others}
        if with_eff:
            # i を除いた人どうしの近さ（もとの値も i を除いた人どうしで数える）
            sub_before = efficiency_without(a, i)
            row["eff_drop_rel"] = (sub_before - efficiency(a, keep)) / sub_before
        rows.append(row)
    df = pd.DataFrame(rows)
    df["lost_ties_share"] = df.deg / deg.sum() * 2
    if with_btw:
        g = nx.from_numpy_array(a.astype(np.int8))
        b = nx.betweenness_centrality(g)
        df["betweenness"] = [b[i] for i in range(N)]
    return df


_EFF_CACHE = {}


def efficiency_without(a, i):
    """i を抜く前の、i 以外の人どうしの近さ（i を通る道は使える）"""
    key = id(a)
    if key not in _EFF_CACHE:
        _EFF_CACHE.clear()
        _EFF_CACHE[key] = shortest_path(csr_matrix(a), directed=False, unweighted=True)
    d = _EFF_CACHE[key]
    keep = np.delete(np.arange(N), i)
    dd = d[np.ix_(keep, keep)]
    n = len(keep)
    inv = np.where(np.isfinite(dd) & (dd > 0), 1.0 / np.where(dd > 0, dd, 1), 0.0)
    return float(inv.sum() / (n * (n - 1)))


def summarize(df):
    top_cut = df.cut_pairs_share.max()
    who = df.cut_pairs_share.idxmax()
    o = {"mean_cut": df.cut_pairs_share.mean(), "max_cut": top_cut,
         "share_zero_cut": (df.cut_pairs_share <= 0).mean(),
         "max_cut_person_deg": int(df.deg[who]),
         "max_cut_person_deg_rank": int((df.deg > df.deg[who]).sum() + 1),
         "top_deg_cut": df.cut_pairs_share[df.deg.idxmax()],
         "top_deg_is_top_cut": bool(df.cut_pairs_share[df.deg.idxmax()] >= top_cut - 1e-12) if top_cut > 0 else None,
         "mean_deg": df.deg.mean(), "max_deg": int(df.deg.max())}
    if "betweenness" in df:
        tb = df.betweenness.idxmax()
        o["top_btw_cut"] = df.cut_pairs_share[tb]
        o["top_btw_is_top_cut"] = bool(df.cut_pairs_share[tb] >= top_cut - 1e-12) if top_cut > 0 else None
    return o


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 1社（data）：全員を1人ずつ抜き、3つの物差しで数える
    a, dept = company(rng)
    one = removal_table(a, with_eff=True)
    one.insert(1, "dept", [f"D{d + 1:02d}" for d in dept])
    one["person"] = [f"P{i:03d}" for i in one.person]
    one.round(6).to_csv(DATA / "removal_one_company.csv", index=False)
    ii, jj = np.where(np.triu(a, 1))
    pd.DataFrame({"person_a": [f"P{i:03d}" for i in ii], "person_b": [f"P{j:03d}" for j in jj]}).to_csv(
        DATA / "ties_one_company.csv", index=False)
    o1 = summarize(one)
    o1.update({"n_ties": int(a.sum() // 2), "n_cross": int((dept[ii] != dept[jj]).sum()),
               "mean_lost_ties_share": one.lost_ties_share.mean(), "formula_2_over_n": 2 / N,
               "max_lost_ties_share": one.lost_ties_share.max(),
               "mean_eff_drop": one.eff_drop_rel.mean(), "max_eff_drop": one.eff_drop_rel.max(),
               "share_eff_drop_lt_0_5pct": (one.eff_drop_rel < 0.005).mean(),
               "top_deg_eff_drop": one.eff_drop_rel[one.deg.idxmax()],
               "top_btw_eff_drop": one.eff_drop_rel[one.betweenness.idxmax()],
               "rank_top_eff_by_deg": int((one.deg > one.deg[one.eff_drop_rel.idxmax()]).sum() + 1),
               "rho_deg_eff": float(one.deg.rank().corr(one.eff_drop_rel.rank())),
               "rho_btw_eff": float(one.betweenness.rank().corr(one.eff_drop_rel.rank())),
               "rho_deg_cut": float(one.deg.rank().corr(one.cut_pairs_share.rank())),
               "n_cut_positive": int((one.cut_pairs_share > 0).sum())})
    w = int(one.cut_pairs_share.idxmax())
    cross_deg = ((a[w]) & (dept != dept[w])).sum()
    keep = np.delete(np.arange(N), w)
    _, lab2 = connected_components(csr_matrix(a[np.ix_(keep, keep)]), directed=False)
    cnt2 = np.bincount(lab2)
    o1.update({"max_cut_person_cross_ties": int(cross_deg), "max_cut_person_dept_cross_ties_total": int(
        sum(((a[i]) & (dept != dept[w])).sum() for i in np.where(dept == dept[w])[0])),
        "after_max_cut_component_sizes_top3": sorted(cnt2.tolist(), reverse=True)[:3]})
    top5 = one.sort_values("cut_pairs_share", ascending=False).head(8)[["person", "dept", "deg", "cut_pairs_share", "eff_drop_rel", "betweenness"]]
    top5.round(5).to_csv(RES / "one_company_top8.csv", index=False)

    # 2) 60社：いちばん切る人は、つながりの多い人か
    rows = []
    for rep in range(REPS):
        aa, _ = company(np.random.default_rng(SEED * 100 + rep))
        df = removal_table(aa)
        rows.append({"rep": rep, **summarize(df)})
    reps = pd.DataFrame(rows)
    reps.round(6).to_csv(RES / "companies_60.csv", index=False)
    rs = {"mean_cut": reps.mean_cut.mean(), "mean_max_cut": reps.max_cut.mean(),
          "max_cut_p10": reps.max_cut.quantile(.1), "max_cut_p90": reps.max_cut.quantile(.9),
          "share_zero_cut": reps.share_zero_cut.mean(),
          "share_companies_max_cut_gt_5pct": (reps.max_cut > 0.05).mean(),
          "top_deg_is_top_cut": reps.top_deg_is_top_cut.dropna().astype(float).mean(),
          "top_btw_is_top_cut": reps.top_btw_is_top_cut.dropna().astype(float).mean(),
          "mean_top_deg_cut": reps.top_deg_cut.mean(), "mean_top_btw_cut": reps.top_btw_cut.mean(),
          "median_max_cut_person_deg_rank": reps.max_cut_person_deg_rank.median(),
          "mean_max_cut_person_deg": reps.max_cut_person_deg.mean(), "mean_max_deg": reps.max_deg.mean(),
          "mean_deg": reps.mean_deg.mean()}

    # 3) 確かめ：部署をまたぐつながりの数 × 集まり方（6通り、各30社）
    grid = []
    for cr in GRID_CROSS:
        for cv in GRID_CV:
            g = []
            for rep in range(GRID_REPS):
                aa, _ = company(np.random.default_rng(SEED * 1000 + cr * 10 + int(cv * 10) * 1000 + rep), cross=cr, cv_cross=cv)
                g.append(summarize(removal_table(aa, with_btw=False)))
            g = pd.DataFrame(g)
            grid.append({"cross": cr, "cv_cross": cv, "mean_cut": r(g.mean_cut.mean(), 6), "mean_max_cut": r(g.max_cut.mean()),
                         "share_zero_cut": r(g.share_zero_cut.mean()),
                         "share_companies_max_cut_gt_5pct": r((g.max_cut > 0.05).mean()),
                         "top_deg_is_top_cut": r(g.top_deg_is_top_cut.dropna().astype(float).mean()),
                         "median_max_cut_person_deg_rank": float(g.max_cut_person_deg_rank.median())})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    out = {"settings": {"n": N, "departments": N_DEPT, "dept_size": DEPT_SIZE, **BASE, "reps": REPS,
                        "grid_cross": GRID_CROSS, "grid_cv": GRID_CV, "grid_reps": GRID_REPS, "seed": SEED},
           "one_company": {k: (r(v, 6) if isinstance(v, float) else v) for k, v in o1.items()},
           "companies_60": {k: r(v, 6) for k, v in rs.items()},
           "grid_6": grid.to_dict("records"),
           "grid_ranges": {k: [r(grid[k].min(), 6), r(grid[k].max(), 6)] for k in
                           ["mean_max_cut", "share_zero_cut", "share_companies_max_cut_gt_5pct", "top_deg_is_top_cut"]}}
    json.dump(out, open(RES / "a1087_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1社の300人、つながりの数と行き来できなくなった組
    fig, axs = plt.subplots(1, 2, figsize=(10.4, 4.2))
    jit = np.random.default_rng(1).uniform(-0.2, 0.2, N)
    axs[0].scatter(one.deg + jit, one.cut_pairs_share * 100, s=12, color=BLUE, alpha=.6, lw=0)
    axs[0].set_xlabel("その人のつながりの数（人）"); axs[0].set_ylabel("行き来できなくなった2人の組（全体の%）")
    axs[0].set_ylim(bottom=0); axs[0].set_xlim(left=0)
    axs[0].set_title("② 行き来できなくなった組", fontsize=11.5)
    axs[1].scatter(one.deg + jit, one.eff_drop_rel * 100, s=12, color=ORANGE, alpha=.6, lw=0)
    axs[1].set_xlabel("その人のつながりの数（人）"); axs[1].set_ylabel("全体の近さの下がり方（%）")
    axs[1].set_ylim(bottom=0); axs[1].set_xlim(left=0)
    axs[1].set_title("③ 遠回りになった分", fontsize=11.5)
    fig.suptitle(f"社員300人の1社：{o1['n_cut_positive']}人だけが組を切り、いちばん切ったのはつながり{o1['max_cut_person_deg']}人の人", fontsize=12.5, y=1.02)
    save(fig, "a1087_one_company.png", SRC)

    # 図2：3つの物差しの平均と最大（1社）
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    labs = ["① 切れたつながりの数", "② 行き来できなくなった組", "③ 全体の近さの下がり方"]
    mean_v = [one.lost_ties_share.mean() * 100, one.cut_pairs_share.mean() * 100, one.eff_drop_rel.mean() * 100]
    max_v = [one.lost_ties_share.max() * 100, one.cut_pairs_share.max() * 100, one.eff_drop_rel.max() * 100]
    y = np.arange(3)[::-1]
    ax.barh(y + 0.18, mean_v, 0.36, color=LIGHT, label="300人の平均")
    ax.barh(y - 0.18, max_v, 0.36, color=BLUE, label="いちばん大きい人")
    for yy, v in zip(y + 0.18, mean_v):
        ax.text(v + 0.05, yy, f"{v:.2f}%", va="center", fontsize=8.5)
    for yy, v in zip(y - 0.18, max_v):
        ax.text(v + 0.05, yy, f"{v:.2f}%", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(labs); ax.set_xlim(0, max(max_v) * 1.2)
    ax.set_xlabel("1人が抜けたときに切れた分（全体に対する%）"); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("同じ1人の抜け方でも、物差しで「切れた大きさ」が違う（1社）")
    save(fig, "a1087_measures.png", SRC, y=-0.05)

    # 図3：確かめ（6通り）：いちばん切る人が、つながりのいちばん多い人だった割合
    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    xl = [f"またぐ{row.cross}本\n集まり方{'強' if row.cv_cross > 1 else '弱'}" for row in grid.itertuples()]
    x = np.arange(len(grid))
    ax.bar(x - 0.2, grid.top_deg_is_top_cut * 100, 0.4, color=ORANGE, label="いちばん切る人＝つながりのいちばん多い人の割合")
    ax.bar(x + 0.2, grid.share_companies_max_cut_gt_5pct * 100, 0.4, color=BLUE, label="1人で全体の組の5%超を切る人がいる会社の割合")
    for xx, v in zip(x - 0.2, grid.top_deg_is_top_cut * 100):
        ax.text(xx, v + 1.5, f"{v:.1f}", ha="center", fontsize=7.5, color=ORANGE)
    for xx, v in zip(x + 0.2, grid.share_companies_max_cut_gt_5pct * 100):
        ax.text(xx, v + 1.5, f"{v:.1f}", ha="center", fontsize=7.5, color=BLUE)
    ax.set_xticks(x); ax.set_xticklabels(xl, fontsize=8.5); ax.set_ylim(0, 115); ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("%（各30社）"); ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("6通りのどれでも、いちばん切る人はほぼ「つながりのいちばん多い人」ではない", fontsize=12)
    save(fig, "a1087_robust.png", SRC, y=-0.06)

    print(json.dumps({k: out[k] for k in ["one_company", "companies_60", "grid_ranges"]}, ensure_ascii=False, indent=1))
    print(top5.to_string()); print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
