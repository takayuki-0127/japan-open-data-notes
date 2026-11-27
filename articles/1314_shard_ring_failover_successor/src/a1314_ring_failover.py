"""1314 1台が止まって、輪の上で次の台がその分をまるごと受け持つと、受け持つ台の量は平均の何倍になるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ。データ10万件と台10台を、0〜1の輪の上に乱数で置く。
データは、輪の上で時計回りに進んで最初に出会う台の置き場所の台が受け持つ（輪の上に並べる振り分け）。
1台を輪の上の何か所に分けて置くか（置き場所の数）を 1・2・4・…・256 と変える。
1台が止まると、その台の置き場所が受け持っていたデータは、それぞれ時計回りに次の（止まっていない）台へ移る。
(1) 基本：10台・置き場所1か所、輪の置き方を作り直して500回×止まる台10通り
(2) 置き場所の数ごと（各500回×10通り）
(3) 確かめ：台の数 5・10・20・50 × 置き場所 1・16・128 × データ 1万件・10万件（各100回×止まる台すべて）
(4) 参考：台を輪の上に等間隔に置いたとき（式どおり：次の台は平均の2倍、止まったあとの平均の 2×(台数−1)÷台数 倍）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT

SEED = 1314
SRC = "架空のアプリのデータの振り分け（作成者が乱数で置いた輪の上の位置、seed 1314）"
N_BASE, K_BASE = 10, 100_000
POINTS = [1, 2, 4, 8, 16, 32, 64, 128, 256]
REPS = 500
GRID_N, GRID_P, GRID_K, GRID_REPS = [5, 10, 20, 50], [1, 16, 128], [10_000, 100_000], 100


def r(x, d=4):
    return round(float(x), d)


def one_ring(rng, n, p, k):
    """輪を1つ作り、止まる台ごとの指標を返す"""
    pos = rng.random(n * p)
    own = np.repeat(np.arange(n), p)
    o = np.argsort(pos)
    pos, own = pos[o], own[o]
    keys = rng.random(k)
    pt = np.searchsorted(pos, keys) % len(pos)  # 時計回りに最初に出会う置き場所
    cnt = np.bincount(pt, minlength=len(pos))
    load = np.bincount(own, weights=cnt, minlength=n)
    m = len(pos)
    idx = np.arange(m)
    out = []
    for f in range(n):
        mask = own == f
        cand = np.where(~mask, idx, 10 * m)
        cand2 = np.concatenate([cand, cand + m])
        nxt = np.minimum.accumulate(cand2[::-1])[::-1]  # 自分以降で最初の「止まっていない」置き場所
        nxt = nxt[1:m + 1] % m  # 自分の次から探す
        recv = own[nxt[mask]]
        inc = np.bincount(recv, weights=cnt[mask], minlength=n)
        after = load + inc
        after[f] = 0
        mean_after = k / (n - 1)
        top = int(np.argmax(inc)) if inc.sum() > 0 else int(recv[0])  # 止まった台が0件なら、次の台
        out.append({"failed_share": load[f] / (k / n),
                    "top_recv_ratio_after": after[top] / mean_after,
                    "top_recv_gain_share": inc[top] / load[f] if load[f] > 0 else np.nan,
                    "max_after_ratio": after.max() / mean_after,
                    "max_before_ratio": load.max() / (k / n),
                    "n_receivers": int((inc > 0).sum()),
                    "failed_was_max": bool(load[f] == load.max())})
    return out


def summarize(rows):
    d = pd.DataFrame(rows)
    s = {"top_recv_ratio_after_mean": r(d.top_recv_ratio_after.mean()),
         "top_recv_ratio_after_p90": r(d.top_recv_ratio_after.quantile(.9)),
         "top_recv_ratio_after_max": r(d.top_recv_ratio_after.max()),
         "top_recv_gain_share_mean": r(d.top_recv_gain_share.mean()),
         "max_after_ratio_mean": r(d.max_after_ratio.mean()),
         "max_after_ratio_p90": r(d.max_after_ratio.quantile(.9)),
         "max_before_ratio_mean": r(d.max_before_ratio.mean()),
         "n_receivers_mean": r(d.n_receivers.mean(), 3),
         "share_top_recv_ge_2x": r((d.top_recv_ratio_after >= 2).mean() * 100, 2)}
    if d.failed_was_max.any():
        s["max_failed_top_recv_ratio_after_mean"] = r(d.loc[d.failed_was_max, "top_recv_ratio_after"].mean())
    return s, d


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # (1)(2) 基本：10台、置き場所の数を変える
    by_p, base_rows = [], None
    for p in POINTS:
        rows = []
        for rep in range(REPS):
            rows += one_ring(np.random.default_rng([SEED, p, rep]), N_BASE, p, K_BASE)
        s, d = summarize(rows)
        by_p.append({"points_per_node": p, **s})
        if p == 1:
            base_rows = d
    by_p = pd.DataFrame(by_p)
    by_p.to_csv(RES / "by_points.csv", index=False)

    # 1回目の輪（data）：置き場所1か所、台3が止まったとき
    rr = np.random.default_rng([SEED, 0])
    pos = np.sort(rr.random(N_BASE))
    own = np.argsort(rr.random(N_BASE))  # 台の番号は輪の順とは別
    keys = rr.random(K_BASE)
    pt = np.searchsorted(pos, keys) % N_BASE
    load = np.bincount(own[pt], minlength=N_BASE)
    nodes = pd.DataFrame({"node": np.arange(N_BASE)})
    order = np.empty(N_BASE, int); order[own] = np.arange(N_BASE)
    nodes["ring_pos"] = np.round(pos[order], 4)
    nodes["keys_before"] = load
    f = int(np.argsort(load)[N_BASE // 2])  # 真ん中くらいの量の台が止まる
    succ = own[(order[f] + 1) % N_BASE]
    after = load.copy(); after[succ] += load[f]; after[f] = 0
    nodes["keys_after_one_down"] = after
    nodes.to_csv(DATA / "ring_example.csv", index=False)
    example = {"failed_node": f, "successor": int(succ), "failed_keys": int(load[f]),
               "successor_before": int(load[succ]), "successor_after": int(after[succ]),
               "successor_after_ratio": r(after[succ] / (K_BASE / (N_BASE - 1))),
               "max_after_ratio": r(after.max() / (K_BASE / (N_BASE - 1)))}

    # 分布（基本、置き場所1か所）
    hist_edges = np.arange(0, 7.51, 0.25)
    h, _ = np.histogram(base_rows.top_recv_ratio_after, bins=hist_edges)
    dist = pd.DataFrame({"from": hist_edges[:-1], "to": hist_edges[1:], "share_pct": np.round(h / h.sum() * 100, 2)})
    dist.to_csv(RES / "base_dist.csv", index=False)

    # (4) 等間隔（式どおり）
    even = {"successor_ratio_after": r(2 * (N_BASE - 1) / N_BASE), "successor_ratio_before": 2.0}

    # (3) 確かめ
    grid = []
    for n in GRID_N:
        for p in GRID_P:
            for k in GRID_K:
                rows = []
                for rep in range(GRID_REPS):
                    rows += one_ring(np.random.default_rng([SEED, 7, n, p, k, rep]), n, p, k)
                s, _ = summarize(rows)
                grid.append({"nodes": n, "points_per_node": p, "keys": k,
                             "even_formula": r(2 * (n - 1) / n), **s})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    b = by_p.set_index("points_per_node")
    g1 = grid[grid.points_per_node == 1]
    out = {"base_points1": b.loc[1].to_dict(), "by_points": by_p.to_dict("records"), "even_spacing": even,
           "example_ring": example,
           "grid_summary": {
               "p1_top_recv_mean_range": [r(g1.top_recv_ratio_after_mean.min()), r(g1.top_recv_ratio_after_mean.max())],
               "p1_minus_even_range": [r((g1.top_recv_ratio_after_mean - g1.even_formula).min()),
                                       r((g1.top_recv_ratio_after_mean - g1.even_formula).max())],
               "p16_top_recv_mean_range": [r(grid[grid.points_per_node == 16].top_recv_ratio_after_mean.min()),
                                           r(grid[grid.points_per_node == 16].top_recv_ratio_after_mean.max())],
               "p128_top_recv_mean_range": [r(grid[grid.points_per_node == 128].top_recv_ratio_after_mean.min()),
                                            r(grid[grid.points_per_node == 128].top_recv_ratio_after_mean.max())],
               "p1_max_after_mean_range": [r(g1.max_after_ratio_mean.min()), r(g1.max_after_ratio_mean.max())],
               "p128_max_after_mean_range": [r(grid[grid.points_per_node == 128].max_after_ratio_mean.min()),
                                             r(grid[grid.points_per_node == 128].max_after_ratio_mean.max())],
               "n_configs": int(len(grid))}}
    json.dump(out, open(RES / "a1314_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回目の輪の例
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(N_BASE)
    ax.bar(x - 0.2, nodes.keys_before / 1000, 0.4, color=LIGHT, label="止まる前")
    ax.bar(x + 0.2, nodes.keys_after_one_down / 1000, 0.4, color=BLUE, label=f"台{f}が止まったあと")
    ax.bar(succ + 0.2, after[succ] / 1000, 0.4, color=ORANGE, label=f"受け持った次の台（台{succ}）")
    ax.axhline(K_BASE / (N_BASE - 1) / 1000, color=GRAY, ls="--", lw=1)
    ax.text(N_BASE - 0.5, K_BASE / (N_BASE - 1) / 1000 + 0.3, "止まったあとの平均", color=GRAY, fontsize=8, ha="right")
    ax.set_xticks(x, [f"台{i}" for i in x], fontsize=9)
    ax.set_ylabel("受け持つデータ（千件）"); ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title(f"1回目の輪：次の台は止まったあとの平均の{example['successor_after_ratio']:.4f}倍を受け持った")
    save(fig, "a1314_example.png", SRC + "。10台・置き場所1か所・データ10万件")

    # 図2：置き場所の数と、受け持つ台の量
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.plot(by_p.points_per_node, by_p.top_recv_ratio_after_mean, "o-", color=ORANGE, label="いちばん多く受け取った台（平均）")
    ax.plot(by_p.points_per_node, by_p.max_after_ratio_mean, "s-", color=BLUE, label="止まったあとのいちばん多い台（平均）")
    ax.plot(by_p.points_per_node, by_p.max_before_ratio_mean, "^--", color=GRAY, label="止まる前のいちばん多い台（平均）")
    ax.axhline(1, color=GRAY, lw=.8)
    ax.set_xscale("log", base=2); ax.set_xticks(POINTS, [str(p) for p in POINTS])
    ax.set_xlabel("1台を輪の上に置く場所の数"); ax.set_ylabel("平均の何倍か"); ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("置き場所を分けるほど、止まった台の分は多くの台に散る（10台）")
    save(fig, "a1314_by_points.png", SRC + "。各500回×止まる台10通りの平均", y=-0.05)

    # 図3：基本の分布
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar(dist["from"] + 0.125, dist.share_pct, 0.23, color=BLUE)
    ax.axvline(even["successor_ratio_after"], color=ORANGE, ls="--", lw=1)
    ax.text(even["successor_ratio_after"] + 0.05, dist.share_pct.max() * 0.95, f"平均{by_p.top_recv_ratio_after_mean.iloc[0]}倍＝等間隔のとき（式どおり）",
            color=ORANGE, fontsize=8)
    ax.set_xlabel("受け持った次の台の量（止まったあとの平均の何倍か）"); ax.set_ylabel("割合（%）"); ax.set_ylim(0, None)
    ax.set_title("置き場所1か所では、次の台の量は大きく散らばる（10台）")
    save(fig, "a1314_dist.png", SRC + "。500回×止まる台10通り＝5,000回", y=-0.05)

    sec = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3000], sec)


if __name__ == "__main__":
    main()
