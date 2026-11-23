"""1084 少ないつながりでも、たどれば何人目で全員に届くのか？（架空のデータ）

架空の会員の会（2,000人）の知り合いのつながりを作成者が置いて乱数で作る。
(1) 会員は20人ずつのサークル（100組）に入り、1人が2人ずつ知り合いを作る（1人あたり平均約4人）。
    知り合いは割合 1−p でサークルの中から、割合 p でサークルの外のでたらめな会員から選ぶ（外へのつながり＝近道）。
    p を変えて、平均で何人目に届くか、全員に届くのは何人目かを数える。
(2) つながりをでたらめに置き、1人あたりの平均の数 d を変えて、そもそも届かない会員がどれだけ出るかを数える。
(3) 会員の数を変えて、平均で何人目に届くかがどう伸びるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import networkx as nx
from scipy.sparse.csgraph import shortest_path
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1084
SRC = "架空の会員の会の知り合い（作成者が置いた作り方からの乱数、seed 1084）"
N, K = 2000, 4
CIRCLE = 20
PS = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
REPS = 5
DS = [0.8, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
RAND_REPS = 5
NS = [500, 1000, 2000, 4000, 8000, 16000]
P_SIZE = 0.1
SIZE_STARTS = 300
GRID_K = [4, 6, 10]
GRID_P = [0.01, 0.05, 0.2]
GRID_REPS = 3


def r(x, d=4):
    return round(float(x), d)


def circles_net(n, k, p, seed):
    """20人ずつのサークル。1人が k/2 人ずつ知り合いを作り、割合 p でサークルの外から選ぶ（重なりは1本に数える）"""
    rng = np.random.default_rng(seed)
    m = k // 2
    u = np.repeat(np.arange(n), m)
    circ = u // CIRCLE
    out = rng.random(len(u)) < p
    pos = u % CIRCLE
    pin = rng.integers(0, CIRCLE - 1, len(u))
    pin = pin + (pin >= pos)
    v_in = circ * CIRCLE + pin
    nc = n // CIRCLE
    oc = rng.integers(0, nc - 1, len(u))
    oc = oc + (oc >= circ)
    v_out = oc * CIRCLE + rng.integers(0, CIRCLE, len(u))
    v = np.where(out, v_out, v_in)
    g = nx.Graph()
    g.add_nodes_from(range(n))
    g.add_edges_from(zip(u.tolist(), v.tolist()))
    return g


def dist_matrix(g, starts=None):
    a = nx.to_scipy_sparse_array(g, nodelist=range(g.number_of_nodes()), format="csr")
    return shortest_path(a, method="D", unweighted=True, directed=False, indices=starts)


def summarize(dm, n):
    """dm：出発の会員ごとの、ほかの会員まで何人目か（届かなければ inf）"""
    rows = []
    for i, d in enumerate(dm):
        d = np.delete(d, np.argmin(d))  # 自分（0）を除く
        fin = np.isfinite(d)
        s = np.sort(d[fin])
        need90 = int(np.ceil(0.9 * (n - 1)))
        rows.append({"reach_share": fin.mean(),
                     "mean_steps_reachable": s.mean() if len(s) else np.nan,
                     "steps_90pct_all": s[need90 - 1] if len(s) >= need90 else np.inf,
                     "steps_all": s[-1] if fin.all() else np.inf,
                     "within6": (d <= 6).mean()})
    return pd.DataFrame(rows)


def naive_steps(n, k):
    """1人が k 人ずつ知っていて、知り合いの知り合いが重ならないと考えたときの、全員に届く人目
    （1人目で k 人、2人目からは1人あたり k−1 人ずつ増える）"""
    tot, new, s = 0, k, 0
    while tot < n - 1:
        s += 1
        tot += new
        new *= (k - 1)
    return s


def main():
    t0 = time.time()

    # (1) 近道の割合 p
    rows = []
    keep = {}
    for p in PS:
        for rep in range(REPS):
            g = circles_net(N, K, p, SEED * 100 + 10 * PS.index(p) + rep)
            dm = dist_matrix(g)
            sm = summarize(dm, N)
            if rep == 0:
                keep[p] = (g, sm, dm)
            rows.append({"p": p, "rep": rep, "mean_steps": sm.mean_steps_reachable.mean(),
                         "steps90_mean": sm.steps_90pct_all.replace(np.inf, np.nan).mean(),
                         "steps_all_mean": sm.steps_all.replace(np.inf, np.nan).mean(),
                         "steps_all_max": sm.steps_all.max(),
                         "steps_all_min": sm.steps_all.min(),
                         "mean_links": 2 * g.number_of_edges() / N,
                         "outside_links_pct": 100 * np.mean([a // CIRCLE != b // CIRCLE for a, b in g.edges()]),
                         "within6_pct": 100 * sm.within6.mean(),
                         "reach_share_pct": 100 * sm.reach_share.mean(),
                         "starts_reach_all_pct": 100 * np.isfinite(sm.steps_all).mean(),
                         "clustering": nx.average_clustering(g),
                         "connected": int(nx.is_connected(g))})
    ws = pd.DataFrame(rows)
    ws_sum = ws.groupby("p").mean(numeric_only=True).drop(columns="rep").reset_index()
    ws_sum["steps_all_max"] = ws.replace(np.inf, np.nan).groupby("p").steps_all_max.max().values
    ws_sum["steps_all_min"] = ws.replace(np.inf, np.nan).groupby("p").steps_all_min.min().values
    ws_sum = ws_sum.round(4)
    ws_sum.to_csv(RES / "shortcuts_by_p.csv", index=False)

    # データ：p＝0.1 の1回で、出発の会員ごとの届き方
    g01, sm01, _ = keep[0.1]
    sm01.to_csv(DATA / "members_p0.1_one_rep.csv", index_label="member_id", float_format="%.4f")
    pd.DataFrame(list(g01.edges()), columns=["member_a", "member_b"]).to_csv(DATA / "links_p0.1_one_rep.csv",
                                                                           index=False)
    # 何人目までに何%に届くか（p ごと、1回目）
    reach_curve = []
    for p in PS:
        _, _, dm = keep[p]
        off = dm[~np.eye(N, dtype=bool)]
        for t in range(1, 41):
            reach_curve.append({"p": p, "steps": t, "reached_pct": r(100 * (off <= t).mean(), 3)})
    reach_curve = pd.DataFrame(reach_curve)
    reach_curve.to_csv(RES / "reach_by_steps.csv", index=False)

    # (2) でたらめに置いたつながり：平均の数 d
    rows = []
    for d in DS:
        for rep in range(RAND_REPS):
            g = nx.fast_gnp_random_graph(N, d / (N - 1), seed=SEED * 200 + int(d * 10) * 10 + rep)
            dm = dist_matrix(g)
            sm = summarize(dm, N)
            comp = max(len(c) for c in nx.connected_components(g))
            off = dm[~np.eye(N, dtype=bool)]
            fin = np.isfinite(off)
            rows.append({"d": d, "rep": rep, "mean_links": 2 * g.number_of_edges() / N,
                         "largest_group_pct": 100 * comp / N,
                         "isolated_pct": 100 * np.mean([x == 0 for _, x in g.degree()]),
                         "pairs_reachable_pct": 100 * fin.mean(),
                         "mean_steps_reachable_pairs": off[fin].mean(),
                         "within6_all_pairs_pct": 100 * (off <= 6).mean(),
                         "all_connected": int(nx.is_connected(g))})
    rd = pd.DataFrame(rows)
    rd_sum = rd.groupby("d").mean(numeric_only=True).drop(columns="rep").reset_index()
    # 式：いちばん大きなかたまりの割合 S は S＝1−exp(−dS) を満たす（人数が多いときの式）
    sform = []
    for d in DS:
        s = 0.9
        for _ in range(2000):
            s = 1 - np.exp(-d * s)
        sform.append(100 * s if d > 1 else 0.0)
    rd_sum["largest_group_formula_pct"] = sform
    rd_sum["isolated_formula_pct"] = [100 * np.exp(-d) for d in DS]
    rd_sum = rd_sum.round(4)
    rd_sum.to_csv(RES / "random_links_by_d.csv", index=False)

    # (3) 会員の数
    rows = []
    for n in NS:
        g = circles_net(n, K, P_SIZE, SEED * 300 + n)
        rng = np.random.default_rng(SEED + n)
        st = np.sort(rng.choice(n, size=min(SIZE_STARTS, n), replace=False))
        dm = dist_matrix(g, st)
        sm = summarize(dm, n)
        rows.append({"n": n, "mean_steps": sm.mean_steps_reachable.mean(),
                     "steps_all_mean": sm.steps_all.replace(np.inf, np.nan).mean(),
                     "steps_all_max_of_starts": sm.steps_all.replace(np.inf, np.nan).max(),
                     "starts_reach_all_pct": 100 * np.isfinite(sm.steps_all).mean(),
                     "within6_pct": 100 * sm.within6.mean(),
                     "naive_steps_formula": naive_steps(n, K)})
    sz = pd.DataFrame(rows).round(4)
    sz.to_csv(RES / "by_members.csv", index=False)

    # 確かめ：知り合いの数 k × 近道の割合 p（9通り、各3回）
    rows = []
    for k in GRID_K:
        for p in GRID_P:
            for rep in range(GRID_REPS):
                g = circles_net(N, k, p, SEED * 400 + 100 * k + 10 * GRID_P.index(p) + rep)
                sm = summarize(dist_matrix(g), N)
                rows.append({"k": k, "p": p, "rep": rep, "mean_steps": sm.mean_steps_reachable.mean(),
                             "steps_all_mean": sm.steps_all.replace(np.inf, np.nan).mean(),
                             "steps_all_max": sm.steps_all.replace(np.inf, np.nan).max(),
                             "starts_reach_all_pct": 100 * np.isfinite(sm.steps_all).mean(),
                             "reach_share_pct": 100 * sm.reach_share.mean(),
                             "within6_pct": 100 * sm.within6.mean(), "naive_steps_formula": naive_steps(N, k)})
    grid = pd.DataFrame(rows).groupby(["k", "p"]).agg(
        mean_steps=("mean_steps", "mean"), steps_all_mean=("steps_all_mean", "mean"),
        steps_all_max=("steps_all_max", "max"), within6_pct=("within6_pct", "mean"),
        starts_reach_all_pct=("starts_reach_all_pct", "mean"), reach_share_pct=("reach_share_pct", "mean"),
        naive_steps_formula=("naive_steps_formula", "first")).reset_index().round(4)
    grid.to_csv(RES / "grid_k_p.csv", index=False)

    w = ws_sum.set_index("p")
    rs = rd_sum.set_index("d")
    zs = sz.set_index("n")
    ratio_all_mean = (grid.steps_all_mean / grid.mean_steps)
    conn = grid[grid.starts_reach_all_pct == 100]
    headline = {
        "naive_steps_formula_n2000_k4": naive_steps(N, K),
        "mean_links_p0.1": float(w.loc[0.1, "mean_links"]),
        "clustering_p0.1": float(w.loc[0.1, "clustering"]),
        "clustering_p1": float(w.loc[1.0, "clustering"]),
    }
    for p in PS:
        headline[f"p{p:g}"] = {"reach_pairs_pct": float(w.loc[p, "reach_share_pct"]),
                               "mean_steps_reachable": float(w.loc[p, "mean_steps"]),
                               "steps_all_mean": None if np.isnan(w.loc[p, "steps_all_mean"])
                               else float(w.loc[p, "steps_all_mean"]),
                               "steps_all_min_max": None if np.isnan(w.loc[p, "steps_all_max"])
                               else [float(w.loc[p, "steps_all_min"]), float(w.loc[p, "steps_all_max"])],
                               "connected_share_of_reps": float(w.loc[p, "connected"]),
                               "within6_pct": float(w.loc[p, "within6_pct"])}
    headline.update({
        "random_d1.5_largest_group_pct": float(rs.loc[1.5, "largest_group_pct"]),
        "random_d1.5_largest_group_formula_pct": r(rs.loc[1.5, "largest_group_formula_pct"], 2),
        "random_d1.5_pairs_reachable_pct": float(rs.loc[1.5, "pairs_reachable_pct"]),
        "random_d1.5_mean_steps_reachable": float(rs.loc[1.5, "mean_steps_reachable_pairs"]),
        "random_d4_pairs_reachable_pct": float(rs.loc[4.0, "pairs_reachable_pct"]),
        "random_d4_mean_steps_reachable": float(rs.loc[4.0, "mean_steps_reachable_pairs"]),
        "random_d4_isolated_pct": float(rs.loc[4.0, "isolated_pct"]),
        "random_d4_isolated_formula_pct": r(rs.loc[4.0, "isolated_formula_pct"], 2),
        "random_all_connected_any": int(rd.all_connected.max()),
        "size_mean_steps": {int(n): float(zs.loc[n, "mean_steps"]) for n in NS},
        "size_steps_all_mean": {int(n): None if np.isnan(zs.loc[n, "steps_all_mean"])
                                else float(zs.loc[n, "steps_all_mean"]) for n in NS},
        "size_starts_reach_all_pct": {int(n): float(zs.loc[n, "starts_reach_all_pct"]) for n in NS},
        "grid_connected_settings": int(len(conn)),
        "grid_connected_mean_steps_range": [float(conn.mean_steps.min()), float(conn.mean_steps.max())],
        "grid_connected_steps_all_mean_range": [float(conn.steps_all_mean.min()), float(conn.steps_all_mean.max())],
        "grid_connected_steps_all_over_mean_ratio_range": [r((conn.steps_all_mean / conn.mean_steps).min(), 3),
                                                           r((conn.steps_all_mean / conn.mean_steps).max(), 3)],
        "grid_reach_pairs_pct_range": [float(grid.reach_share_pct.min()), float(grid.reach_share_pct.max())],
        "p0_reach_formula_pct_19_over_1999": r(100 * (CIRCLE - 1) / (N - 1)),
        "steps_all_over_mean_ratio_by_p": {f"p{p:g}": r(w.loc[p, "steps_all_mean"] / w.loc[p, "mean_steps"], 3)
                                           for p in PS if not np.isnan(w.loc[p, "steps_all_mean"])},
        "random_isolated_max_abs_diff_pt_all_d": r((rd_sum.isolated_pct - rd_sum.isolated_formula_pct).abs().max(), 3),
        "random_largest_max_abs_diff_pt_d1.5to6": r((rd_sum.largest_group_pct - rd_sum.largest_group_formula_pct)
                                                     [rd_sum.d >= 1.5].abs().max(), 3),
        "size_mean_steps_added_per_doubling": r((zs.loc[NS[-1], "mean_steps"] - zs.loc[NS[0], "mean_steps"])
                                                / np.log2(NS[-1] / NS[0]), 3),
    })

    # 図1：外へのつながりの割合ごとに、届く組の割合と何人目か
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [1, 1.3]})
    x = np.arange(len(PS))
    lab = [f"{100 * p:g}%" for p in PS]
    ax[0].bar(x, ws_sum.reach_share_pct, 0.6, color=GRAY)
    for i, v in enumerate(ws_sum.reach_share_pct):
        ax[0].text(i, v + 1.5, f"{v:.1f}", ha="center", fontsize=8)
    ax[0].set_xticks(x, lab)
    ax[0].set_ylim(0, 112)
    ax[0].set_yticks(range(0, 101, 20))
    ax[0].set_xlabel("サークルの外へのつながりの割合 p")
    ax[0].set_ylabel("たどって届く組の割合（%）")
    ax[0].set_title("そもそも届く組はどれだけか")
    ax[1].bar(x - 0.2, ws_sum.mean_steps, 0.4, color=BLUE, label="平均で何人目か（届く組だけ）")
    sa = ws_sum.steps_all_mean.fillna(0)
    ax[1].bar(x + 0.2, sa, 0.4, color=ORANGE, label="全員に届くのは何人目か（届いた出発の人の平均）")
    for i in range(len(PS)):
        ax[1].text(i - 0.2, ws_sum.mean_steps[i] + 0.4, f"{ws_sum.mean_steps[i]:.1f}", ha="center", fontsize=8)
        t = "届かない" if sa[i] == 0 else f"{sa[i]:.1f}"
        ax[1].text(i + 0.2, sa[i] + 0.4, t, ha="center", fontsize=7.5 if sa[i] == 0 else 8,
                   rotation=90 if sa[i] == 0 else 0, va="bottom")
    ax[1].set_xticks(x, lab)
    ax[1].set_ylim(0, max(ws_sum.steps_all_mean.max(), ws_sum.mean_steps.max()) * 1.35)
    ax[1].set_xlabel("サークルの外へのつながりの割合 p")
    ax[1].set_ylabel("何人目")
    ax[1].set_title("何人目で届くか（5回の平均）")
    ax[1].legend(frameon=False, loc="upper right", fontsize=9)
    fig.suptitle("1人あたりの知り合いは平均3.7〜4.0人（会員2,000人、20人ずつのサークル100組）", y=1.02)
    save(fig, "a1084_shortcuts.png", SRC)

    # 図2：何人目までに何%に届くか
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for p, c, ls in [(0.02, GRAY, "-"), (0.05, GREEN, "-"), (0.1, BLUE, "-"), (1.0, ORANGE, "--")]:
        rc = reach_curve[reach_curve.p == p]
        ax.plot(rc.steps, rc.reached_pct, color=c, ls=ls, label=f"外へのつながり {100 * p:g}%")
    ax.axvline(6, color=GRAY, lw=0.8, ls=":")
    ax.text(6.3, 45, "6人目", color=GRAY, fontsize=9)
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 102)
    ax.set_xlabel("何人目まで")
    ax.set_ylabel("届いた組の割合（全部の組のうち、%）")
    ax.set_title("何人目までに何%の組に届くか（2,000人、1回分）")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "a1084_reach_curve.png", SRC)

    # 図3：でたらめのつながりで、そもそも届かない組
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(DS))
    ax.bar(x - 0.2, rd_sum.pairs_reachable_pct, 0.4, color=BLUE, label="たどって届く組の割合（%）")
    ax.bar(x + 0.2, rd_sum.within6_all_pairs_pct, 0.4, color=ORANGE, label="6人目までに届く組の割合（%）")
    for i in range(len(DS)):
        ax.text(i - 0.2, rd_sum.pairs_reachable_pct[i] + 1.5, f"{rd_sum.pairs_reachable_pct[i]:.1f}",
                ha="center", fontsize=8)
        ax.text(i + 0.2, rd_sum.within6_all_pairs_pct[i] + 1.5, f"{rd_sum.within6_all_pairs_pct[i]:.1f}",
                ha="center", fontsize=8)
    ax.set_xticks(x, [f"{d:g}" for d in DS])
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.set_xlabel("1人あたりのつながりの平均の数 d（でたらめに置いた）")
    ax.set_ylabel("全部の組のうちの割合（%）")
    ax.set_title("つながりが少ないと、そもそも届かない組が残る（2,000人、5回の平均）")
    ax.legend(frameon=False, loc="upper left", ncol=2)
    save(fig, "a1084_unreachable.png", SRC)

    out = {"seed": SEED, "settings": {"members": N, "links_per_member": K, "ps": PS, "reps": REPS, "ds": DS,
                                      "random_reps": RAND_REPS, "ns": NS, "p_for_size": P_SIZE,
                                      "size_starts": SIZE_STARTS, "grid_k": GRID_K, "grid_p": GRID_P,
                                      "grid_reps": GRID_REPS},
           "headline": headline, "shortcuts_by_p": ws_sum.to_dict("records"),
           "random_links_by_d": rd_sum.to_dict("records"), "by_members": sz.to_dict("records"),
           "grid_k_p": grid.to_dict("records")}
    with open(RES / "a1084_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(headline, ensure_ascii=False, indent=1))
    for t in [ws_sum, rd_sum, sz, grid]:
        print(t.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
