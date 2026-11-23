"""1083 グループの分け方の細かさで、グループの数と顔ぶれはどう変わるのか？（架空のデータ）

架空の会社（240人、4本部×3部×20人）の1か月のやり取りのつながりを、作成者が置いた確率から乱数で作る。
やり取りの記録から、つながりの密な集まり（グループ）を分ける方法（ルーバン法）で、分け方の細かさ
（解像度 γ）を変えたときのグループの数、本部・部との一致、分け直したときの顔ぶれの一致を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1083
SRC = "架空の会社のやり取り（作成者が置いた確率からの乱数、seed 1083）"
N_HONBU, N_BU, BU_SIZE = 4, 3, 20
BASE = {"p_in": 0.25, "p_mid": 0.04, "p_out": 0.005}
GAMMAS = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0]
SEEDS_SAME_NET = 30
NETS = 100
GRID_P_IN = [0.15, 0.25, 0.4]
GRID_P_MID = [0.02, 0.04, 0.08]
GRID_NETS = 20
GRID_GAMMAS = [0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]
UNEVEN_SIZES = [6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 34, 36]
UNEVEN_NETS = 100


def r(x, d=4):
    return round(float(x), d)


def labels_even():
    bu = np.repeat(np.arange(N_HONBU * N_BU), BU_SIZE)
    honbu = bu // N_BU
    return honbu, bu


def make_net(rng, honbu, bu, p_in, p_mid, p_out):
    n = len(bu)
    same_bu = bu[:, None] == bu[None, :]
    same_hb = honbu[:, None] == honbu[None, :]
    p = np.where(same_bu, p_in, np.where(same_hb, p_mid, p_out))
    a = np.triu(rng.random((n, n)) < p, 1)
    g = nx.Graph()
    g.add_nodes_from(range(n))
    g.add_edges_from(zip(*np.nonzero(a)))
    return g


def split(g, gamma, seed):
    comms = nx.community.louvain_communities(g, resolution=gamma, seed=seed)
    lab = np.empty(g.number_of_nodes(), dtype=int)
    for k, c in enumerate(sorted(comms, key=lambda c: min(c))):
        lab[list(c)] = k
    return lab, comms


def pair_same(lab):
    iu = np.triu_indices(len(lab), 1)
    return (lab[:, None] == lab[None, :])[iu]


def ari(a, b):
    """調整ランド指数：2人の組ごとの同じ／違うの一致から、偶然の一致を引いた値（1で完全一致、0で偶然並み）"""
    _, ai = np.unique(a, return_inverse=True)
    _, bi = np.unique(b, return_inverse=True)
    ct = np.zeros((ai.max() + 1, bi.max() + 1))
    np.add.at(ct, (ai, bi), 1)
    c2 = lambda x: x * (x - 1) / 2
    s = c2(ct).sum()
    sa, sb = c2(ct.sum(1)).sum(), c2(ct.sum(0)).sum()
    tot = c2(len(a))
    exp = sa * sb / tot
    mx = (sa + sb) / 2
    return float((s - exp) / (mx - exp)) if mx != exp else 1.0


def pair_agree(l1, l2):
    """どちらかの分け方で同じグループだった2人の組のうち、両方で同じだった割合"""
    s1, s2 = pair_same(l1), pair_same(l2)
    return float((s1 & s2).sum() / (s1 | s2).sum())


def main():
    t0 = time.time()
    honbu, bu = labels_even()
    g0 = make_net(np.random.default_rng(SEED), honbu, bu, **BASE)
    deg = np.array([d for _, d in g0.degree()])

    # 1) 同じ1か月の記録で、細かさ γ を変える（分け直し 30回）
    rows = []
    labs_by_gamma = {}
    for gm in GAMMAS:
        labs = [split(g0, gm, s)[0] for s in range(SEEDS_SAME_NET)]
        labs_by_gamma[gm] = labs
        ng = [len(np.unique(l)) for l in labs]
        agree = [pair_agree(labs[i], labs[i + 1]) for i in range(0, SEEDS_SAME_NET - 1, 2)]
        rows.append({"gamma": gm, "groups_mean": r(np.mean(ng), 2), "groups_min": int(min(ng)),
                     "groups_max": int(max(ng)),
                     "ari_honbu": r(np.mean([ari(l, honbu) for l in labs])),
                     "ari_bu": r(np.mean([ari(l, bu) for l in labs])),
                     "modularity_gamma1": r(np.mean([nx.community.modularity(g0, split(g0, gm, s)[1])
                                                     for s in range(5)])),
                     "pair_agree_reruns_pct": r(100 * np.mean(agree), 2)})
    same_net = pd.DataFrame(rows)
    same_net.to_csv(RES / "same_month_by_gamma.csv", index=False)
    best_q_gamma = float(same_net.loc[same_net.modularity_gamma1.idxmax(), "gamma"])

    # 2) 同じ置き方で別の月の記録（ネットワークを作り直す 100回）
    rows = []
    for k in range(NETS):
        rng = np.random.default_rng(SEED * 1000 + k)
        ga = make_net(rng, honbu, bu, **BASE)
        gb = make_net(rng, honbu, bu, **BASE)
        for gm in [0.3, 1.0, 3.0]:
            la, _ = split(ga, gm, k)
            lb, _ = split(gb, gm, k)
            rows.append({"net": k, "gamma": gm, "groups": len(np.unique(la)),
                         "ari_honbu": ari(la, honbu), "ari_bu": ari(la, bu),
                         "pair_agree_two_months_pct": 100 * pair_agree(la, lb),
                         "exact_12": int(ari(la, bu) == 1.0), "exact_4": int(ari(la, honbu) == 1.0)})
    nets = pd.DataFrame(rows)
    nets_sum = nets.groupby("gamma").agg(
        groups_mean=("groups", "mean"), groups_min=("groups", "min"), groups_max=("groups", "max"),
        ari_honbu=("ari_honbu", "mean"), ari_bu=("ari_bu", "mean"),
        pair_agree_two_months_pct=("pair_agree_two_months_pct", "mean"),
        exact_bu_pct=("exact_12", "mean"), exact_honbu_pct=("exact_4", "mean")).reset_index()
    nets_sum["exact_bu_pct"] *= 100
    nets_sum["exact_honbu_pct"] *= 100
    nets_sum = nets_sum.round(4)
    nets_sum.to_csv(RES / "months_by_gamma.csv", index=False)
    gcount_dist = nets[nets.gamma == 1.0].groups.value_counts().sort_index()

    # 3) グループのない記録（つながりの数は同じまま、相手をでたらめに入れかえる）
    rows = []
    for k in range(NETS):
        rng = np.random.default_rng(SEED * 2000 + k)
        ga = make_net(rng, honbu, bu, **BASE)
        gr = ga.copy()
        nx.double_edge_swap(gr, nswap=5 * gr.number_of_edges(), max_tries=10 ** 6, seed=k)
        for kind, gg in [("部署のある記録", ga), ("相手をでたらめに入れかえた記録", gr)]:
            lab, comms = split(gg, 1.0, k)
            rows.append({"net": k, "kind": kind, "groups": len(np.unique(lab)),
                         "modularity": nx.community.modularity(gg, comms),
                         "ari_bu": ari(lab, bu)})
    null = pd.DataFrame(rows)
    null_sum = null.groupby("kind", sort=False).agg(
        groups_mean=("groups", "mean"), groups_min=("groups", "min"), groups_max=("groups", "max"),
        modularity_mean=("modularity", "mean"), modularity_min=("modularity", "min"),
        modularity_max=("modularity", "max"), ari_bu=("ari_bu", "mean")).reset_index().round(4)
    null_sum.to_csv(RES / "null_random.csv", index=False)

    # 4) 部の大きさが不ぞろいなとき（6〜36人）、小さい部はまとめられやすいか
    sizes = np.array(UNEVEN_SIZES)
    rows = []
    for k in range(UNEVEN_NETS):
        rng = np.random.default_rng(SEED * 3000 + k)
        perm = rng.permutation(len(sizes))
        bu_u = np.repeat(np.arange(len(sizes)), sizes[perm])  # 部 k の大きさは sizes[perm[k]]
        honbu_u = bu_u // N_BU
        gu = make_net(rng, honbu_u, bu_u, **BASE)
        for gm in [1.0, 2.0]:
            lab, _ = split(gu, gm, k)
            maj = {}
            for d in range(len(sizes)):
                vals, cnt = np.unique(lab[bu_u == d], return_counts=True)
                maj[d] = (vals[cnt.argmax()], cnt.max() / cnt.sum())
            for d in range(len(sizes)):
                gd = maj[d][0]
                merged = any(maj[e][0] == gd for e in range(len(sizes)) if e != d)
                rows.append({"net": k, "gamma": gm, "size": int(sizes[perm[d]]), "merged": int(merged),
                             "kept_together": int(maj[d][1] >= 0.9)})
    un = pd.DataFrame(rows)
    un_sum = un.groupby(["gamma", "size"]).agg(merged_pct=("merged", "mean"),
                                                kept_together_pct=("kept_together", "mean")).reset_index()
    un_sum[["merged_pct", "kept_together_pct"]] *= 100
    un_sum = un_sum.round(2)
    un_sum.to_csv(RES / "uneven_bu_sizes.csv", index=False)

    # 5) 確かめ：部の中・本部の中のつながりやすさ 9通り（各20回）
    rows = []
    for i, pin in enumerate(GRID_P_IN):
        for j, pmid in enumerate(GRID_P_MID):
            for k in range(GRID_NETS):
                rng = np.random.default_rng(SEED * 4000 + 100 * (3 * i + j) + k)
                gg = make_net(rng, honbu, bu, pin, pmid, BASE["p_out"])
                for gm in GRID_GAMMAS:
                    lab, _ = split(gg, gm, k)
                    rows.append({"p_in": pin, "p_mid": pmid, "net": k, "gamma": gm,
                                 "groups": len(np.unique(lab)), "ari_honbu": ari(lab, honbu),
                                 "ari_bu": ari(lab, bu)})
    grid = pd.DataFrame(rows).groupby(["p_in", "p_mid", "gamma"]).mean(numeric_only=True)\
        .drop(columns="net").reset_index().round(4)
    grid.to_csv(RES / "grid.csv", index=False)
    g1 = grid[grid.gamma == 1.0]
    best = grid.loc[grid.groupby(["p_in", "p_mid"]).ari_bu.idxmax()]
    besth = grid.loc[grid.groupby(["p_in", "p_mid"]).ari_honbu.idxmax()]

    # データ
    pd.DataFrame(list(g0.edges()), columns=["person_a", "person_b"]).to_csv(DATA / "edges_one_month.csv",
                                                                            index=False)
    people = pd.DataFrame({"person_id": np.arange(len(bu)), "honbu": honbu, "bu": bu, "links": deg,
                           "group_gamma0.3": labs_by_gamma[0.3][0], "group_gamma1": labs_by_gamma[1.0][0],
                           "group_gamma3": labs_by_gamma[3.0][0]})
    people.to_csv(DATA / "people_one_month.csv", index=False)

    s1 = same_net.set_index("gamma")
    ns = nets_sum.set_index("gamma")
    nl = null_sum.set_index("kind")
    u1 = un_sum[un_sum.gamma == 1.0].set_index("size")
    u2 = un_sum[un_sum.gamma == 2.0].set_index("size")
    small = un[(un.gamma == 1.0) & (un["size"] <= 10)].merged.mean() * 100
    large = un[(un.gamma == 1.0) & (un["size"] >= 28)].merged.mean() * 100
    small2 = un[(un.gamma == 2.0) & (un["size"] <= 10)].merged.mean() * 100
    large2 = un[(un.gamma == 2.0) & (un["size"] >= 28)].merged.mean() * 100
    exp_deg = (BU_SIZE - 1) * BASE["p_in"] + (N_BU - 1) * BU_SIZE * BASE["p_mid"] + \
        (N_HONBU - 1) * N_BU * BU_SIZE * BASE["p_out"]
    headline = {
        "one_month_edges": g0.number_of_edges(), "one_month_mean_links": r(deg.mean(), 2),
        "expected_mean_links_formula": r(exp_deg, 2),
        "gamma1_groups_mean_same_month": float(s1.loc[1.0, "groups_mean"]),
        "gamma1_ari_bu_same_month": float(s1.loc[1.0, "ari_bu"]),
        "gamma1_ari_honbu_same_month": float(s1.loc[1.0, "ari_honbu"]),
        "gamma_best_modularity_same_month": best_q_gamma,
        "groups_range_over_gammas": [float(same_net.groups_mean.min()), float(same_net.groups_mean.max())],
        "months_gamma1_groups_mean": float(ns.loc[1.0, "groups_mean"]),
        "months_gamma1_groups_min_max": [int(ns.loc[1.0, "groups_min"]), int(ns.loc[1.0, "groups_max"])],
        "months_gamma1_groups_dist": {int(k): int(v) for k, v in gcount_dist.items()},
        "months_gamma1_exact_bu_pct": float(ns.loc[1.0, "exact_bu_pct"]),
        "months_gamma03_exact_honbu_pct": float(ns.loc[0.3, "exact_honbu_pct"]),
        "months_gamma1_pair_agree_pct": float(ns.loc[1.0, "pair_agree_two_months_pct"]),
        "months_gamma03_pair_agree_pct": float(ns.loc[0.3, "pair_agree_two_months_pct"]),
        "months_gamma3_pair_agree_pct": float(ns.loc[3.0, "pair_agree_two_months_pct"]),
        "months_gamma3_groups_mean": float(ns.loc[3.0, "groups_mean"]),
        "months_gamma03_groups_mean": float(ns.loc[0.3, "groups_mean"]),
        "null_groups_mean": float(nl.loc["相手をでたらめに入れかえた記録", "groups_mean"]),
        "null_groups_min_max": [int(nl.loc["相手をでたらめに入れかえた記録", "groups_min"]),
                                int(nl.loc["相手をでたらめに入れかえた記録", "groups_max"])],
        "null_modularity_mean": float(nl.loc["相手をでたらめに入れかえた記録", "modularity_mean"]),
        "null_modularity_min_max": [float(nl.loc["相手をでたらめに入れかえた記録", "modularity_min"]),
                                    float(nl.loc["相手をでたらめに入れかえた記録", "modularity_max"])],
        "real_modularity_mean": float(nl.loc["部署のある記録", "modularity_mean"]),
        "real_groups_mean": float(nl.loc["部署のある記録", "groups_mean"]),
        "uneven_gamma1_merged_pct_size_le10": r(small, 2), "uneven_gamma1_merged_pct_size_ge28": r(large, 2),
        "uneven_gamma2_merged_pct_size_le10": r(small2, 2), "uneven_gamma2_merged_pct_size_ge28": r(large2, 2),
        "grid_gamma1_groups_range": [float(g1.groups.min()), float(g1.groups.max())],
        "grid_gamma1_ari_bu_range": [float(g1.ari_bu.min()), float(g1.ari_bu.max())],
        "grid_gamma1_ari_honbu_range": [float(g1.ari_honbu.min()), float(g1.ari_honbu.max())],
        "grid_best_gamma_for_bu": {f"p_in={a}, p_mid={b}": float(c) for a, b, c in
                                   zip(best.p_in, best.p_mid, best.gamma)},
        "grid_best_gamma_for_honbu": {f"p_in={a}, p_mid={b}": float(c) for a, b, c in
                                      zip(besth.p_in, besth.p_mid, besth.gamma)},
    }

    # 図1：細かさ γ ごとのグループの数と一致（同じ1か月の記録）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    x = np.arange(len(GAMMAS))
    ax[0].plot(x, same_net.groups_mean, "o-", color=BLUE)
    ax[0].fill_between(x, same_net.groups_min, same_net.groups_max, color=LIGHT, alpha=0.6, lw=0)
    for v, t in [(4, "本部の数 4"), (12, "部の数 12")]:
        ax[0].axhline(v, color=GRAY, ls="--", lw=1)
        ax[0].text(0, v + 0.6, t, ha="left", fontsize=9, color=GRAY)
    ax[0].set_xticks(x, [str(g) for g in GAMMAS])
    ax[0].set_ylim(0, max(same_net.groups_max) + 4)
    ax[0].set_xlabel("分け方の細かさ γ（大きいほど細かい）")
    ax[0].set_ylabel("見つかったグループの数")
    ax[0].set_title("グループの数（線は30回の平均、帯は最小〜最大）")
    ax[1].plot(x, same_net.ari_honbu, "o-", color=ORANGE, label="本部（4つ）との一致")
    ax[1].plot(x, same_net.ari_bu, "s-", color=BLUE, label="部（12）との一致")
    ax[1].set_xticks(x, [str(g) for g in GAMMAS])
    ax[1].set_ylim(0, 1.05)
    ax[1].set_xlabel("分け方の細かさ γ")
    ax[1].set_ylabel("一致の度合い（1で完全に一致、0で偶然並み）")
    ax[1].set_title("どちらの区切りに合うか")
    ax[1].legend(frameon=False, loc="lower right")
    fig.suptitle("同じ1か月のやり取りでも、細かさで別のグループになる（240人）", y=1.02)
    save(fig, "a1083_gamma.png", SRC)

    # 図2：グループのない記録でもグループは見つかる
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    kinds = list(null_sum.kind)
    cols = [BLUE, GRAY]
    ax[0].bar([0, 1], null_sum.modularity_mean, color=cols, width=0.55)
    for i, v in enumerate(null_sum.modularity_mean):
        ax[0].text(i, v + 0.01, f"{v:.3f}", ha="center")
    ax[0].set_xticks([0, 1], ["部署のある記録", "相手をでたらめに\n入れかえた記録"])
    ax[0].set_ylim(0, max(null_sum.modularity_mean) * 1.25)
    ax[0].set_ylabel("モジュラリティ（100回の平均）")
    ax[0].set_title("まとまりの強さの目安")
    ax[1].bar([0, 1], null_sum.groups_mean, color=cols, width=0.55)
    for i, v in enumerate(null_sum.groups_mean):
        ax[1].text(i, v + 0.2, f"{v:.2f}", ha="center")
    ax[1].set_xticks([0, 1], ["部署のある記録", "相手をでたらめに\n入れかえた記録"])
    ax[1].set_ylim(0, max(null_sum.groups_mean) * 1.25)
    ax[1].set_ylabel("見つかったグループの数（100回の平均）")
    ax[1].set_title("γ＝1 で見つかったグループの数")
    fig.suptitle("つながりの数を同じにして相手をでたらめにしても、グループは見つかる", y=1.02)
    save(fig, "a1083_null.png", SRC)

    # 図3：部の大きさとまとめられた割合
    fig, ax = plt.subplots(figsize=(9, 4))
    xs = np.arange(len(sizes))
    ax.bar(xs - 0.2, u1.loc[sizes, "merged_pct"], 0.4, color=BLUE, label="γ＝1")
    ax.bar(xs + 0.2, u2.loc[sizes, "merged_pct"], 0.4, color=ORANGE, label="γ＝2")
    ax.set_xticks(xs, [f"{s}人" for s in sizes])
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.set_xlabel("部の人数")
    ax.set_ylabel("ほかの部と同じグループにまとめられた割合（%）")
    ax.set_title("部の大きさが不ぞろい（6〜36人）だと、小さい部ほどまとめられる（100回）")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    save(fig, "a1083_uneven.png", SRC)

    out = {"seed": SEED, "settings": {"people": len(bu), "honbu": N_HONBU, "bu_per_honbu": N_BU, "bu_size": BU_SIZE, **BASE,
                                      "gammas": GAMMAS, "seeds_same_month": SEEDS_SAME_NET, "nets": NETS,
                                      "grid_p_in": GRID_P_IN, "grid_p_mid": GRID_P_MID, "grid_gammas": GRID_GAMMAS, "grid_nets": GRID_NETS,
                                      "uneven_sizes": UNEVEN_SIZES},
           "headline": headline,
           "same_month_by_gamma": same_net.to_dict("records"),
           "months_by_gamma": nets_sum.to_dict("records"),
           "null_random": null_sum.to_dict("records"),
           "uneven_bu_sizes": un_sum.to_dict("records")}
    with open(RES / "a1083_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(headline, ensure_ascii=False, indent=1))
    print(same_net.to_string())
    print(nets_sum.to_string())
    print(null_sum.to_string())
    print(un_sum.to_string())
    print(g1.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
