"""1256 シリーズの何冊目から読み始める人が多いかで、1冊目から順に読む割合はどう見えるのか？（架空のデータ）

架空の電子書籍のシリーズ（基本は5冊）。読者ごとに読み始める巻を作成者が置いた割合で決め、
1冊読み終えるごとに、作成者が置いた確率 p で次の巻へ進む。途中の巻から読み始めた人は、
前へ進むのをやめたあと、確率 q で1冊目に戻り、1冊目から同じ確率 p で進む（読み始めた巻の手前まで）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1256
SRC = "架空の電子書籍のシリーズの読者（作成者が乱数で作成、seed 1256）"
N = 20000
BASE = {"K": 5, "p": 0.6, "q": 0.3, "s1": 0.6, "shape": "even"}
SHAPES = {"even": "2冊目以降に均等", "newest": "いちばん新しい巻に集まる"}


def start_probs(K, s1, shape):
    pr = np.zeros(K)
    pr[0] = s1
    if K > 1:
        if shape == "even":
            pr[1:] = (1 - s1) / (K - 1)
        else:   # 残りの7割がいちばん新しい巻、3割が間の巻に均等（K=2 なら全部が2冊目）
            if K == 2:
                pr[1] = 1 - s1
            else:
                pr[-1] = (1 - s1) * 0.7
                pr[1:-1] = (1 - s1) * 0.3 / (K - 2)
    return pr


def run_streak(u, p, start, limit):
    """start の巻を読み、そのあと確率 p で次へ。limit の巻まで。読み終えた最後の巻を返す"""
    e = start.copy()
    go = np.ones(len(start), bool)
    for step in range(u.shape[1]):
        nxt = go & (e < limit) & (u[:, step] < p)
        go = nxt
        e = np.where(nxt, e + 1, e)
    return e


def simulate(rng, K, p, q, s1, shape, n=N):
    s = rng.choice(np.arange(1, K + 1), size=n, p=start_probs(K, s1, shape))
    e = run_streak(rng.random((n, K)), p, s, np.full(n, K))
    back = (s > 1) & (rng.random(n) < q)
    b = np.where(back, run_streak(rng.random((n, K)), p, np.ones(n, int), s - 1), 0)
    return s, e, back, b


def measures(s, e, back, b, K, p):
    books = np.arange(1, K + 1)
    readers = np.array([((s <= k) & (k <= e)).sum() + (back & (k <= b)).sum() for k in books])
    read1 = (s == 1) | back
    read2 = ((s <= 2) & (2 <= e)) | (back & (b >= 2))
    readall = ((s == 1) & (e == K)) | (back & (e == K) & (b == s - 1))
    first1 = s == 1
    return {
        "A_count_ratio_1to2": readers[1] / readers[0],
        "B_read1_also2": read2[read1].mean(),
        "C_started1_to2": (e[first1] >= 2).mean(),
        "A_count_ratio_1toK": readers[-1] / readers[0],
        "B_read1_readall": readall[read1].mean(),
        "C_started1_toK": (e[first1] == K).mean(),
        "formula_p": p, "formula_pK": p ** (K - 1),
        "share_book1_readers_started1": first1.sum() / read1.sum(),
        "readers": readers,
    }


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    K, p, q = BASE["K"], BASE["p"], BASE["q"]

    # 1) 基本の1回分：読者の記録
    s, e, back, b = simulate(rng, K, p, q, BASE["s1"], BASE["shape"])
    rec = pd.DataFrame({"reader_id": np.arange(1, N + 1), "start_book": s, "last_book_forward": e,
                        "went_back_to_1": back.astype(int), "last_book_after_back": b})
    rec.to_csv(DATA / "readers_base.csv", index=False)
    m = measures(s, e, back, b, K, p)
    per_book = pd.DataFrame({"book": np.arange(1, K + 1), "readers": m["readers"],
                             "ratio_to_previous": np.r_[np.nan, m["readers"][1:] / m["readers"][:-1]].round(4),
                             "started_here": np.bincount(s, minlength=K + 1)[1:]})
    per_book.to_csv(RES / "per_book_base.csv", index=False)

    # 2) 1冊目から読み始める人の割合を変える（2つの形）
    rows = []
    gi = 0
    for shape in ["even", "newest"]:
        for s1 in [1.0, 0.8, 0.6, 0.4, 0.2]:
            r2 = np.random.default_rng(SEED * 100 + gi)
            gi += 1
            mm = measures(*simulate(r2, K, p, q, s1, shape), K, p)
            rr = mm.pop("readers")
            rows.append({"shape": shape, "s1": s1, **{k: round(float(v), 4) for k, v in mm.items()},
                         "max_step_ratio": round(float((rr[1:] / rr[:-1]).max()), 4)})
    sweep = pd.DataFrame(rows)
    sweep.to_csv(RES / "start_share_sweep.csv", index=False)

    # 3) 確かめ：p・q・巻の数・途中から読み始める形の54通り（1冊目から読み始める人は6割）
    grid = []
    for shape in ["even", "newest"]:
        for KK in [3, 5, 8]:
            for pp in [0.4, 0.6, 0.8]:
                for qq in [0.0, 0.3, 0.6]:
                    r3 = np.random.default_rng(SEED * 1000 + gi)
                    gi += 1
                    mm = measures(*simulate(r3, KK, pp, qq, 0.6, shape), KK, pp)
                    rr = mm.pop("readers")
                    grid.append({"shape": shape, "K": KK, "p": pp, "q": qq,
                                 **{k: round(float(v), 4) for k, v in mm.items()},
                                 "max_step_ratio": round(float((rr[1:] / rr[:-1]).max()), 4)})
    grid = pd.DataFrame(grid)
    grid["A_over_C_1to2"] = (grid.A_count_ratio_1to2 / grid.C_started1_to2).round(4)
    grid["A_over_C_1toK"] = (grid.A_count_ratio_1toK / grid.C_started1_toK).round(4)
    grid["B_over_C_1to2"] = (grid.B_read1_also2 / grid.C_started1_to2).round(4)
    grid.to_csv(RES / "grid.csv", index=False)

    base_m = {k: (round(float(v), 4) if k != "readers" else [int(x) for x in v]) for k, v in m.items()}
    main_json = {
        "base": {**BASE, "n_readers": N, "start_probs": start_probs(K, BASE["s1"], BASE["shape"]).round(4).tolist()},
        "base_measures": base_m,
        "base_went_back_share_of_midway": round(float(back[s > 1].mean()), 4),
        "grid_range": {c: [float(grid[c].min()), float(grid[c].max())] for c in
                       ["A_count_ratio_1to2", "B_read1_also2", "C_started1_to2", "A_over_C_1to2", "A_over_C_1toK",
                        "B_over_C_1to2", "max_step_ratio", "share_book1_readers_started1"]},
        "grid_n_A_above_C_1to2": int((grid.A_count_ratio_1to2 > grid.C_started1_to2).sum()),
        "grid_n_A_above_C_1toK": int((grid.A_count_ratio_1toK > grid.C_started1_toK).sum()),
        "grid_n_step_ratio_above_1": int((grid.max_step_ratio > 1).sum()),
        "grid_n": int(len(grid)),
        "grid_A_over_C_1to2_max_by_K": {int(k): float(v) for k, v in grid.groupby("K").A_over_C_1to2.max().items()},
        "base_A_over_C_1to2": round(float(m["A_count_ratio_1to2"] / m["C_started1_to2"]), 4),
        "base_A_over_C_1toK": round(float(m["A_count_ratio_1toK"] / m["C_started1_toK"]), 4),
        "grid_max_abs_C_minus_p": round(float((grid.C_started1_to2 - grid.p).abs().max()), 4),
        "grid_q0_B_minus_C_max_abs": round(float((grid[grid.q == 0].B_read1_also2 - grid[grid.q == 0].C_started1_to2).abs().max()), 4),
    }
    with open(RES / "a1256_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：巻ごとの読者数（基本）と、読み始めた巻の内訳
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(1, K + 1)
    started = per_book.started_here.to_numpy()
    ax.bar(x, per_book.readers, color=LIGHT, label="その巻を読んだ人")
    ax.bar(x, started, color=BLUE, width=0.45, label="その巻から読み始めた人")
    for xx, v, rt in zip(x, per_book.readers, per_book.ratio_to_previous):
        ax.text(xx, v + 150, f"{v:,}人" + ("" if np.isnan(rt) else f"\n前の巻の{rt:.4f}倍"), ha="center", va="bottom", fontsize=8.5)
    ax.set_ylim(0, per_book.readers.max() * 1.25)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{k}冊目" for k in x])
    ax.set_ylabel("人数")
    ax.set_title(f"巻ごとの読者数（読者2万人、1冊目から読み始めるのは6割）")
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.92), fontsize=9)
    save(fig, "a1256_per_book.png", SRC + "。次の巻へ進む確率は0.6、途中から読んだ人の3割が1冊目に戻る")

    # 図2：1冊目から読み始める人の割合と、3つの「2冊目へ進んだ割合」
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, shape in zip(axs, ["even", "newest"]):
        sw = sweep[sweep["shape"] == shape]
        xs = sw.s1 * 100
        ax.plot(xs, sw.A_count_ratio_1to2 * 100, "o-", color=ORANGE, label="A 2冊目の人数÷1冊目の人数")
        ax.plot(xs, sw.B_read1_also2 * 100, "s-", color=GRAY, label="B 1冊目を読んだ人のうち2冊目も")
        ax.plot(xs, sw.C_started1_to2 * 100, "^-", color=BLUE, label="C 1冊目から始めて2冊目へ")
        ax.set_xlim(105, 15)
        ax.set_ylim(0, 105)
        ax.set_xlabel("1冊目から読み始める人の割合（%）")
        ax.set_title(f"途中から読み始める人：{SHAPES[shape]}", fontsize=11)
    axs[0].set_ylabel("1冊目から2冊目へ進んだ割合（%）")
    axs[0].legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.suptitle("進む確率は0.6と置いた。数え方で見える割合が変わる", y=1.02)
    save(fig, "a1256_start_share.png", SRC)

    # 図3：確かめの54通り（A÷C）
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, col, ttl, logy in [(axs[0], "A_over_C_1to2", "1冊目→2冊目", False), (axs[1], "A_over_C_1toK", "1冊目→最後の巻", True)]:
        for shape, c, mk in [("even", BLUE, "o"), ("newest", ORANGE, "s")]:
            g = grid[grid["shape"] == shape]
            kx = g.K.map({3: 0, 5: 1, 8: 2})
            off = (g.p.map({0.4: 0, 0.6: 1, 0.8: 2}) * 3 + g.q.map({0.0: 0, 0.3: 1, 0.6: 2}) - 4) * 0.035
            ax.scatter(kx + off + (0.02 if shape == "newest" else -0.02), g[col], color=c, marker=mk, s=18,
                       label=f"途中から：{SHAPES[shape]}")
        ax.axhline(1, color=INK, lw=0.8, ls="--")
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["3冊", "5冊", "8冊"])
        ax.set_xlabel("シリーズの巻の数")
        if logy:
            ax.set_yscale("log")
            ax.set_title(f"{ttl}（対数の目盛り）", fontsize=11)
        else:
            ax.set_ylim(0, grid[col].max() * 1.1)
            ax.set_title(ttl, fontsize=11)
    axs[0].set_ylabel("人数の比 ÷ 1冊目から始めた人の割合（倍）")
    axs[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle("人数の比は、1冊目から始めた人の進む割合の何倍に見えるか（54通り、破線が1倍）", y=1.02)
    save(fig, "a1256_grid.png", SRC + "。進む確率0.4・0.6・0.8、戻る割合0・0.3・0.6。1冊目から読み始めるのは6割")
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
