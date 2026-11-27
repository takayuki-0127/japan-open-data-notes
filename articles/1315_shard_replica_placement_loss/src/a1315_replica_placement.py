"""1315 写しを3台ずつに置いても、3台が同時に止まったときに読めなくなるデータの割合は、写しの置き方でどれだけ違うのか？（架空のデータ）

作成者が置いた架空のアプリのデータ。データ10万件を30台に置き、1件ごとに写しを3台に置く。
3台が同時に止まったとき、写しを置いた3台がすべて止まったデータは読めなくなる。
止まる3台の組み合わせ（30台なら4,060通り）をすべて数える（どの組み合わせも同じ確率と置く）。
写しの置き方は4つ：
  ①でたらめに3台：1件ごとに、30台から3台を乱数で選ぶ
  ②決まった3台の組：30台をはじめに10組（3台ずつ）に分け、1件ごとに組を乱数で選ぶ
  ③輪の上で続く3台：台を輪の上に1か所ずつ乱数で置き、データの位置から時計回りに出会う3台
  ④輪の上で続く3台（1台を16か所に分けて置く）：時計回りに出会う、違う3台
(1) 基本：30台・10万件、置き方を作り直して20回
(2) 参考：4台が同時に止まったとき（30台・10万件、27,405通り）
(3) 確かめ：台の数 15・30・60・120 × データ 1万・10万・100万件（各5回）
読めなくなるデータの割合の、止まる組み合わせについての平均は、どの置き方でも 1÷（台数から3台を選ぶ組み合わせの数）になる（式どおり）。
"""
import json
import time
from itertools import combinations
from math import comb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1315
SRC = "架空のアプリのデータの写しの置き方（作成者が乱数で置いた置き場所、seed 1315）"
N_BASE, D_BASE, REPS = 30, 100_000, 20
GRID_N, GRID_D, GRID_REPS = [15, 30, 60, 120], [10_000, 100_000, 1_000_000], 5
COLS = ["#2a78d6", "#3aa07a", "#a3a29c", "#eb6834"]
METHODS = {"random": "①でたらめに3台", "groups": "②決まった3台の組", "ring1": "③輪の上で続く3台",
           "ring16": "④輪の上で続く3台（1台16か所）"}


def r(x, d=4):
    return round(float(x), d)


def place(method, rng, n, d):
    """1件ごとに写しを置く3台（並べたもの）を返す"""
    if method == "random":
        x1 = rng.integers(0, n, d)
        x2 = rng.integers(0, n - 1, d)
        x2 += x2 >= x1
        lo, hi = np.minimum(x1, x2), np.maximum(x1, x2)
        x3 = rng.integers(0, n - 2, d)
        x3 += x3 >= lo
        x3 += x3 >= hi
        t = np.stack([x1, x2, x3], 1)
    elif method == "groups":
        perm = rng.permutation(n).reshape(-1, 3)
        t = perm[rng.integers(0, n // 3, d)]
    else:
        p = 1 if method == "ring1" else 16
        pos = rng.random(n * p)
        own = np.repeat(np.arange(n), p)
        o = np.argsort(pos)
        pos, own = pos[o], own[o]
        m = len(pos)
        trip = np.empty((m, 3), dtype=np.int64)
        for i in range(m):  # 置き場所 i から時計回りに、違う3台
            seen = []
            j = i
            while len(seen) < 3:
                if own[j % m] not in seen:
                    seen.append(own[j % m])
                j += 1
            trip[i] = seen
        pt = np.searchsorted(pos, rng.random(d)) % m
        t = trip[pt]
    return np.sort(t, axis=1)


def count_by_triple(t, n):
    a, b, c = t[:, 0].astype(np.int64), t[:, 1].astype(np.int64), t[:, 2].astype(np.int64)
    idx = (a * n + b) * n + c
    u, k = np.unique(idx, return_counts=True)
    full = np.zeros(n ** 3, dtype=np.int64)
    full[u] = k
    aa, bb, cc = np.array(list(combinations(range(n), 3))).T
    return full[(aa * n + bb) * n + cc]  # 止まる3台の組（辞書順）ごとの、読めなくなる件数


def loss_stats(cnt, d):
    lost = cnt / d * 100
    any_ = lost > 0
    return {"p_any_loss_pct": r(any_.mean() * 100, 4),
            "mean_lost_pct": r(lost.mean(), 5),
            "mean_lost_pct_if_loss": r(lost[any_].mean(), 4) if any_.any() else 0.0,
            "max_lost_pct": r(lost.max(), 4),
            "mean_lost_items_if_loss": r((cnt[any_]).mean(), 2) if any_.any() else 0.0,
            "distinct_triples_used": int((cnt > 0).sum())}


def avg_stats(lst):
    keys = lst[0].keys()
    return {k: r(np.mean([x[k] for x in lst]), 5) for k in keys}


def main():
    t0 = time.time()
    n, d = N_BASE, D_BASE
    ntri = comb(n, 3)
    formula = 100 / ntri

    # (1) 基本
    base, base_curves, ex_counts = {}, {}, {}
    for mk in METHODS:
        st, curves = [], []
        for rep in range(REPS):
            t = place(mk, np.random.default_rng([SEED, rep, list(METHODS).index(mk)]), n, d)
            cnt = count_by_triple(t, n)
            st.append(loss_stats(cnt, d))
            if rep == 0:
                ex_counts[mk] = cnt
        base[mk] = avg_stats(st)
    base_df = pd.DataFrame([{"method": METHODS[k], **v} for k, v in base.items()])
    base_df.to_csv(RES / "base_methods.csv", index=False)

    # 1回目の置き方での、止まる3台の組ごとの読めなくなる件数（data）
    combos = np.array(list(combinations(range(n), 3)))
    ex = pd.DataFrame({"down_a": combos[:, 0], "down_b": combos[:, 1], "down_c": combos[:, 2],
                       **{f"lost_{k}": ex_counts[k] for k in METHODS}})
    ex.to_csv(DATA / "lost_by_down_set_rep1.csv", index=False)

    # (2) 4台が同時に止まる（基本の1回目の置き方で）
    four = {}
    q = list(combinations(range(n), 4))
    q = np.array(q)
    lookup = {tuple(c): i for i, c in enumerate(combos)}
    sub_idx = np.array([[lookup[tuple(np.delete(row, j))] for j in range(4)] for row in q])
    for mk in METHODS:
        lost4 = ex_counts[mk][sub_idx].sum(1)
        four[METHODS[mk]] = loss_stats(lost4, d)
    four_formula = r(100 * (n - 3) / comb(n, 4), 5)  # 1件の3台を含む4台の組の数÷4台の組の数

    # (3) 確かめ
    grid = []
    for gn in GRID_N:
        for gd in GRID_D:
            for mk in METHODS:
                st = []
                for rep in range(GRID_REPS):
                    t = place(mk, np.random.default_rng([SEED, 9, gn, gd, rep, list(METHODS).index(mk)]), gn, gd)
                    st.append(loss_stats(count_by_triple(t, gn), gd))
                grid.append({"nodes": gn, "items": gd, "method": METHODS[mk], "triples_total": comb(gn, 3),
                             "formula_mean_lost_pct": r(100 / comb(gn, 3), 5), **avg_stats(st)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    def rng_of(col, m):
        s = grid[grid.method == METHODS[m]][col]
        return [r(s.min(), 5), r(s.max(), 5)]

    order_ok = 0
    for _, s_ in grid.groupby(["nodes", "items"]):
        s_ = s_.set_index("method").loc[[METHODS[m] for m in METHODS]]
        a_, b_ = s_.p_any_loss_pct.values, s_.mean_lost_pct_if_loss.values  # ①②③④
        order_ok += int(a_[0] >= a_[3] > a_[2] > a_[1] and b_[0] < b_[3] < b_[2] < b_[1])
    out = {"base": {"nodes": n, "items": d, "copies": 3, "down": 3, "down_sets": ntri,
                    "formula_mean_lost_pct": r(formula, 5), "methods": base_df.to_dict("records")},
           "four_down": {"down_sets": comb(n, 4), "formula_mean_lost_pct": four_formula, "methods": four},
           "grid_ranges": {METHODS[m]: {"p_any_loss_pct": rng_of("p_any_loss_pct", m),
                                        "mean_lost_pct_if_loss": rng_of("mean_lost_pct_if_loss", m)} for m in METHODS},
           "grid_mean_lost_minus_formula_max_abs": r((grid.mean_lost_pct - grid.formula_mean_lost_pct).abs().max(), 6),
           "n_configs": int(len(grid) // len(METHODS)),
           "configs_same_order": order_ok}
    json.dump(out, open(RES / "a1315_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    labels = [METHODS[k] for k in METHODS]
    # 図1：何かが読めなくなる割合
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    v = [base[k]["p_any_loss_pct"] for k in METHODS]
    ax.barh(labels[::-1], v[::-1], color=COLS[::-1])
    for i, x in enumerate(v[::-1]):
        ax.text(x + 1, i, f"{x}%", va="center", fontsize=9)
    ax.set_xlim(0, 115); ax.set_xlabel("3台が同時に止まったとき、何か1件でも読めなくなる割合（%）")
    ax.set_title("でたらめに置くと、どの3台が止まっても何かが読めなくなる（30台）")
    save(fig, "a1315_any_loss.png", SRC + "。データ10万件・止まる3台の組4,060通りすべて・置き方20回の平均", y=-0.05)

    # 図2：読めなくなったときの割合（対数）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    v2 = [base[k]["mean_lost_pct_if_loss"] for k in METHODS]
    yy = np.arange(len(labels))[::-1]
    ax.scatter(v2, yy, s=60, color=COLS, zorder=3)
    ax.set_yticks(yy, labels)
    ax.set_xscale("log"); ax.set_xlim(0.01, 100); ax.set_ylim(-0.6, len(labels) - 0.4)
    ax.grid(axis="x", color=GRAY, alpha=.3, lw=.6)
    ax.set_xticks([0.01, 0.1, 1, 10, 100], ["0.01", "0.1", "1", "10", "100"])
    for x, y in zip(v2, yy):
        ax.text(x * 1.25, y, f"{x}%", va="center", fontsize=9)
    ax.set_xlabel("読めなくなったとき、全体のうち読めなくなるデータの割合（%、対数の目盛り）")
    ax.set_title(f"平均はどれも{out['base']['formula_mean_lost_pct']}%（式どおり）、起き方が違う")
    save(fig, "a1315_if_loss.png", SRC + "。30台・データ10万件・置き方20回の平均", y=-0.05)

    # 図3：台の数で（データ10万件）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    sub = grid[grid["items"] == 100_000]
    for m, c, mk in zip(METHODS, COLS, ["o", "s", "^", "D"]):
        s = sub[sub.method == METHODS[m]]
        ax.plot(s.nodes, s.p_any_loss_pct, marker=mk, color=c, label=METHODS[m])
    ax.set_xscale("log"); ax.set_xticks(GRID_N, [str(x) for x in GRID_N]); ax.minorticks_off()
    ax.set_yscale("log"); ax.set_ylim(0.005, 200)
    ax.set_yticks([0.01, 0.1, 1, 10, 100], ["0.01", "0.1", "1", "10", "100"])
    ax.set_xlabel("台の数（対数の目盛り）"); ax.set_ylabel("何か読めなくなる割合（%、対数）")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    p60 = sub[(sub.method == METHODS["random"]) & (sub.nodes == 60)].p_any_loss_pct.iloc[0]
    ax.set_title(f"でたらめに置くと、60台でも{p60}%の組み合わせで何かが読めなくなる")
    save(fig, "a1315_by_nodes.png", SRC + "。データ10万件・各5回の平均", y=-0.05)
    print(round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
