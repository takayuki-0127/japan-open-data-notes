"""985 「次こそ当たる」は、どこまで正しいのか？（架空のデータ）

架空のくじの箱。1人が新しい箱から1枚ずつ、引いた札を戻さずに引いていく。
箱の中の当たりの数を作成者が置き（決まった枚数・箱ごとに違う枚数など）、最初から k 回続けて外れたあと、
次の1枚が当たる割合を、乱数で作った箱で数える。式の値（どの箱かで場合分けした重み付きの平均）とも比べる。
くじの確率の数え方だけを扱い、引くことをすすめたり止めたりはしない。
"""
import json
from math import comb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 985
SRC = "架空のくじの箱（作成者が乱数で作成、seed 985）"
N_BOX = 1_000_000
KS = [0, 5, 10, 20, 30, 40, 60]


def r4(x):
    return round(float(x), 4)


def win_dist(kind, n, p):
    """箱の中の当たりの数 W の分布（値, 確率）。replace=True は「戻す」（毎回の当たりの確率が箱ごとに W/n）"""
    m = p * n
    if kind == "fixed":
        v = np.array([round(m)]); w = np.array([1.0])
    elif kind == "binomial":
        v = np.arange(n + 1)
        w = np.array([comb(n, i) * p ** i * (1 - p) ** (n - i) for i in v])
    elif kind == "narrow":
        v = np.arange(round(0.6 * m), round(1.4 * m) + 1); w = np.ones(len(v)) / len(v)
    elif kind == "wide":
        v = np.arange(0, round(2 * m) + 1); w = np.ones(len(v)) / len(v)
    elif kind == "empty_mix":
        v = np.array([0, round(m / 0.8)]); w = np.array([0.2, 0.8])
    else:
        raise ValueError(kind)
    return v.astype(int), w / w.sum()


def p_miss_k(v, n, k, replace):
    """当たり v 枚の箱で、最初の k 回がすべて外れる確率"""
    if replace:
        return (1 - v / n) ** k
    return np.array([comb(n - x, k) / comb(n, k) if k <= n - x else 0.0 for x in v])


def next_hit_formula(v, w, n, k, replace=False):
    pm = p_miss_k(v, n, k, replace)
    nxt = v / n if replace else v / (n - k)
    return float((w * pm * nxt).sum() / (w * pm).sum())


def simulate_first_hit(rng, v, w, n, replace, n_box=N_BOX, kmax=max(KS)):
    """箱を n_box 個作り、最初に当たった回（kmax+1 回までに当たらなければ 0）を返す"""
    wins = rng.choice(v, size=n_box, p=w)
    left_w = wins.astype(float).copy()
    first = np.zeros(n_box, int)
    alive = np.ones(n_box, bool)
    for j in range(kmax + 1):
        prob = left_w / n if replace else left_w / (n - j)
        hit = alive & (rng.random(n_box) < prob)
        first[hit] = j + 1
        alive &= ~hit
        # 外れた札は戻さない（当たりの数は変わらず、残りの枚数が減る）
    return wins, first


SCEN = [("independent", "毎回5%で決まる（箱の中身と関係なし）", None, True),
        ("fixed", "当たりが5枚と決まった箱", "fixed", False),
        ("binomial", "当たりの数が二項分布の箱（平均5枚）", "binomial", False),
        ("narrow", "当たりが箱ごとに3〜7枚", "narrow", False),
        ("wide", "当たりが箱ごとに0〜10枚", "wide", False),
        ("empty_mix", "2割の箱は当たり0枚、8割は6枚", "empty_mix", False),
        ("wide_replace", "毎回の当たりの確率が台ごとに0〜10%（戻す）", "wide", True)]


def main():
    n, p = 100, 0.05
    rows, curves = [], {}
    sample = None
    for i, (key, label, kind, replace) in enumerate(SCEN):
        if key == "independent":
            v, w = np.array([5]), np.array([1.0])
        else:
            v, w = win_dist(kind, n, p)
        rng = np.random.default_rng(SEED * 10 + i)
        wins, first = simulate_first_hit(rng, v, w, n, replace)
        if key == "wide":
            sample = pd.DataFrame({"box_id": np.arange(1, 2001), "wins": wins[:2000],
                                   "first_hit_draw_upto61": first[:2000]})
        var_w = float((w * (v - (w * v).sum()) ** 2).sum())
        for k in KS:
            surv = (first == 0) | (first > k)
            sim = float((first[surv] == k + 1).mean())
            frm = next_hit_formula(v, w, n, k, replace)
            # k 回外れた箱のうち、当たり0枚の箱の割合
            pm = p_miss_k(v, n, k, replace)
            post0 = float((w * pm)[v == 0].sum() / (w * pm).sum()) if (v == 0).any() else 0.0
            rows.append({"scenario": key, "label": label, "replace": replace, "misses_k": k,
                         "boxes_with_k_misses": int(surv.sum()), "next_hit_sim": r4(sim), "next_hit_formula": r4(frm),
                         "share_zero_win_boxes": r4(post0), "var_wins": round(var_w, 3)})
    base = pd.DataFrame(rows)
    base.to_csv(RES / "next_hit_base.csv", index=False)
    sample.to_csv(DATA / "boxes_wide_sample.csv", index=False)

    # 当たり0〜10枚の箱：20回外れる前と後の、当たりの数の分布（式）
    v, w = win_dist("wide", n, p)
    post = w * p_miss_k(v, n, 20, False); post /= post.sum()
    post_df = pd.DataFrame({"wins": v, "share_before": np.round(w, 4), "share_after_20_misses": np.round(post, 4)})
    post_df.to_csv(RES / "wins_after_20_misses.csv", index=False)

    # 確かめ：箱の大きさ × 当たりの割合 × 当たりの数の分布（式）。外れは箱の2割（n/5 回）
    grid = []
    for n2 in [50, 100, 200, 1000]:
        for p2 in [0.02, 0.05, 0.10]:
            for kind in ["fixed", "binomial", "narrow", "wide", "empty_mix"]:
                v, w = win_dist(kind, n2, p2)
                mean_p = float((w * v).sum() / n2)
                var_w = float((w * (v - (w * v).sum()) ** 2).sum())
                var_bin = n2 * mean_p * (1 - mean_p)
                k = n2 // 5
                nx = next_hit_formula(v, w, n2, k)
                grid.append({"box_size": n2, "p_set": p2, "kind": kind, "mean_p": r4(mean_p),
                             "var_wins": round(var_w, 3), "var_binomial": round(var_bin, 3),
                             "var_ratio": round(var_w / var_bin, 3), "misses_k": k,
                             "next_hit": round(nx, 5), "next_over_p": round(nx / mean_p, 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_formula.csv", index=False)
    g2 = grid[(grid.var_ratio - 1).abs() > 1e-6]
    agree = int((np.sign(g2.next_over_p - 1) == np.sign(1 - g2.var_ratio)).sum())

    sim_err = r4((base.next_hit_sim - base.next_hit_formula).abs().max())
    b = base.set_index(["scenario", "misses_k"])
    out = {"box_size": n, "p": p, "n_boxes_per_scenario": N_BOX,
           "next_hit_after_20": {s: {"sim": float(b.loc[(s, 20), "next_hit_sim"]),
                                     "formula": float(b.loc[(s, 20), "next_hit_formula"])} for s, *_ in SCEN},
           "next_hit_after_60": {s: {"sim": float(b.loc[(s, 60), "next_hit_sim"]),
                                     "formula": float(b.loc[(s, 60), "next_hit_formula"])} for s, *_ in SCEN},
           "max_abs_diff_sim_formula": sim_err,
           "wide_zero_box_share": {"before": float(b.loc[("wide", 0), "share_zero_win_boxes"]),
                                   "after_20": float(b.loc[("wide", 20), "share_zero_win_boxes"]),
                                   "after_60": float(b.loc[("wide", 60), "share_zero_win_boxes"])},
           "grid": {"n_cases": int(len(grid)), "n_cases_var_not_binomial": int(len(g2)),
                    "direction_matches_var_rule": agree,
                    "next_over_p_min": float(grid.next_over_p.min()), "next_over_p_max": float(grid.next_over_p.max()),
                    "binomial_next_over_p_minmax": [float(grid[grid.kind == "binomial"].next_over_p.min()),
                                                    float(grid[grid.kind == "binomial"].next_over_p.max())]}}
    json.dump(out, open(RES / "a985_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：外れた回数と、次の1枚の当たり
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    sty = {"independent": (GRAY, "o", "-"), "fixed": (ORANGE, "o", "-"), "binomial": (INK, "s", ":"),
           "narrow": (LIGHT, "o", "-"), "wide": (BLUE, "o", "-"), "empty_mix": (GREEN, "^", "-"),
           "wide_replace": (BLUE, "x", "--")}
    for s, lab, *_ in SCEN:
        d = base[base.scenario == s]
        c, mk, ls = sty[s]
        ax.plot(d.misses_k, d.next_hit_sim * 100, ls=ls, marker=mk, color=c, label=lab, ms=5)
    ax.axhline(5, color=GRAY, lw=.6)
    ax.set_xlabel("最初から続けて外れた回数（100枚の箱）")
    ax.set_ylabel("次の1枚が当たった割合（%）")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("同じ「平均5%」でも、外れのあとに上がるか下がるかは箱の中身しだい", fontsize=12)
    save(fig, "a985_next_hit.png", SRC)

    # 図2：0〜10枚の箱、20回外れる前と後の当たりの数
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = post_df.wins
    ax.bar(x - 0.2, post_df.share_before * 100, width=.4, color=GRAY, label="引く前")
    ax.bar(x + 0.2, post_df.share_after_20_misses * 100, width=.4, color=BLUE, label="20回続けて外れたあと")
    ax.set_xticks(x); ax.set_xlabel("箱の中の当たりの数（枚）"); ax.set_ylabel("箱の割合（%）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("20回外れた箱は、当たりの少ない箱である見込みが高くなる（0〜10枚の箱）", fontsize=12)
    save(fig, "a985_wins_after_misses.png", SRC)

    # 図3：散らばりの比と、次の当たり÷平均の当たり
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cm = {"fixed": ORANGE, "binomial": INK, "narrow": LIGHT, "wide": BLUE, "empty_mix": GREEN}
    jp = {"fixed": "決まった枚数", "binomial": "二項分布", "narrow": "平均の6〜14割で一様", "wide": "0〜平均の2倍で一様",
          "empty_mix": "2割の箱が0枚"}
    for kind, d in grid.groupby("kind", sort=False):
        xv = np.maximum(d.var_ratio, 0.01)
        big = kind == "fixed"
        ax.scatter(xv, d.next_over_p, color=cm[kind], label=jp[kind], s=70 if big else 28, marker="D" if big else "o",
                   edgecolor="white", lw=.5, zorder=3 if big else 2, alpha=.85 if big else 1)
    ax.set_xscale("log"); ax.axhline(1, color=GRAY, lw=.8); ax.axvline(1, color=GRAY, lw=.8, ls="--")
    ax.set_xlabel("当たりの数の散らばり ÷ 二項分布の散らばり（対数の目盛り、0は0.01に置いた）")
    ax.set_ylabel("外れたあとの当たり ÷ 平均の当たり")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title(f"散らばりが二項分布より小さいと上がり、大きいと下がる\n（{len(grid)}通り、箱の2割を続けて外したあと）", fontsize=12)
    save(fig, "a985_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
