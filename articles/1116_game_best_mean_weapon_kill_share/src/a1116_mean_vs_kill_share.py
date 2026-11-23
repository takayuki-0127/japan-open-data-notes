"""1116 平均のダメージがいちばん大きい武器は、決まった回数のうちに倒せる割合もいちばん高いのか？（架空のデータ）

作成者が置いた架空のゲームの武器4つ（1回の攻撃のダメージの出方を作成者が置いたもの）で、
敵の体力と攻撃できる回数を決め、その回数のうちに倒せる割合を、ダメージの分布から式どおりに数え（出方の組み合わせをすべて足し合わせる）、
乱数で戦いを作って同じになることを確かめる。平均のダメージの順と、倒せる割合の順を比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1116
SRC = "架空のゲームの武器4つ（作成者が置いたダメージの出方、seed 1116）"
MAXD = 3000


def pmf_uniform(lo, hi):
    p = np.zeros(MAXD + 1); p[lo:hi + 1] = 1.0 / (hi - lo + 1); return p


def pmf_two(v0, v1, q):
    """確率 1−q で v0、確率 q で v1"""
    p = np.zeros(MAXD + 1); p[v0] += 1 - q; p[v1] += q; return p


def weapons(c_hit=0.6, c_dmg=360):
    return {
        "A": {"name": "A 安定", "desc": "毎回190〜210（1きざみで同じ確率）", "pmf": pmf_uniform(190, 210)},
        "B": {"name": "B 会心", "desc": "170、25%で会心して2倍の340", "pmf": pmf_two(170, 340, 0.25)},
        "C": {"name": "C 大振り", "desc": f"{int(c_hit * 100)}%で当たって{c_dmg}、外れると0", "pmf": pmf_two(c_dmg, 0, 1 - c_hit)},
        "D": {"name": "D 一撃", "desc": "150、10%で会心して5倍の750", "pmf": pmf_two(150, 750, 0.10)},
    }


COLORS = {"A": GRAY, "B": BLUE, "C": ORANGE, "D": GREEN}


def r(x, d=2):
    return round(float(x), d)


def sum_pmf(p, n):
    out = np.zeros(1); out[0] = 1.0
    for _ in range(n):
        out = np.convolve(out, p)
    return out


def kill_share(p, n, hp):
    """n 回のダメージの合計が hp 以上になる確率"""
    s = sum_pmf(p[:int(np.nonzero(p)[0].max()) + 1], n)
    return float(s[int(np.ceil(hp)):].sum()) if hp < len(s) else 0.0


def kill_share_hp_spread(p, n, hp, spread):
    """敵の体力が hp×(1−spread)〜hp×(1+spread) の整数に一様に散らばるとき"""
    s = sum_pmf(p[:int(np.nonzero(p)[0].max()) + 1], n)
    tail = np.concatenate([np.cumsum(s[::-1])[::-1], [0.0]])
    hs = np.arange(int(np.ceil(hp * (1 - spread))), int(np.floor(hp * (1 + spread))) + 1)
    hs = np.clip(hs, 0, len(s))
    return float(tail[hs].mean())


def mean_of(p):
    return float((np.arange(len(p)) * p).sum())


def sd_of(p):
    m = mean_of(p); return float(np.sqrt(((np.arange(len(p)) - m) ** 2 * p).sum()))


def draw(rng, key, size, c_hit=0.6, c_dmg=360):
    if key == "A":
        return rng.integers(190, 211, size)
    u = rng.random(size)
    if key == "B":
        return np.where(u < 0.25, 340, 170)
    if key == "C":
        return np.where(u < c_hit, c_dmg, 0)
    return np.where(u < 0.10, 750, 150)


def top_keys(d, tol=1e-12):
    m = max(d.values()); return [k for k, v in d.items() if v >= m - tol]


def main():
    t0 = time.time()
    W = weapons()
    keys = list(W)
    means = {k: mean_of(W[k]["pmf"]) for k in keys}
    sds = {k: sd_of(W[k]["pmf"]) for k in keys}
    mean_rank = sorted(keys, key=lambda k: -means[k])
    HP0, N0 = 900, 5

    # 1) 基本：体力900・5回。式どおりの割合と、乱数で作った戦い（各100,000回）
    rng = np.random.default_rng(SEED)
    SIMN = 100000
    base = {}
    ex_rows = []
    for k in keys:
        hits = draw(rng, k, (SIMN, N0))
        tot = hits.sum(axis=1)
        # 倒すまでの回数（回数の決まりなし、最大40回）
        long = draw(rng, k, (SIMN, 40)).cumsum(axis=1)
        need = (long < HP0).sum(axis=1) + 1
        base[k] = {"name": W[k]["name"], "desc": W[k]["desc"], "mean": r(means[k], 2), "sd": r(sds[k], 2),
                   "mean_x5": r(means[k] * N0, 1),
                   "kill_share_exact": r(kill_share(W[k]["pmf"], N0, HP0) * 100, 2),
                   "kill_share_sim": r((tot >= HP0).mean() * 100, 2),
                   "hits_to_kill_mean": r(need.mean(), 3), "hits_to_kill_median": int(np.median(need)),
                   "hits_to_kill_le5_sim": r((need <= N0).mean() * 100, 2)}
        for b in range(1000):
            ex_rows.append({"weapon": k, "battle": b + 1, **{f"hit{i + 1}": int(hits[b, i]) for i in range(N0)},
                            "total": int(tot[b]), "killed": int(tot[b] >= HP0)})
    pd.DataFrame(ex_rows).to_csv(DATA / "example_battles.csv", index=False)
    base_share = {k: base[k]["kill_share_exact"] for k in keys}

    # 2) 体力を変えたとき（5回、500〜1500を25きざみ）
    hp_rows = []
    for hp in range(500, 1501, 25):
        rec = {"hp": hp, "need_per_hit": r(hp / N0, 1)}
        for k in keys:
            rec[k] = r(kill_share(W[k]["pmf"], N0, hp) * 100, 2)
        t = top_keys({k: rec[k] for k in keys}); rec["top"] = "・".join(t)
        hp_rows.append(rec)
    byhp = pd.DataFrame(hp_rows)
    byhp.to_csv(RES / "by_hp.csv", index=False)
    pick_hp = {str(h): {k: float(byhp.loc[byhp.hp == h, k].iloc[0]) for k in keys} | {"top": byhp.loc[byhp.hp == h, "top"].iloc[0]}
               for h in [700, 800, 900, 1000, 1100, 1200]}

    # 3) 確かめ：1回あたりに要るダメージ（体力÷回数）×回数、C の当たり方・体力の散らばりを変えて
    grid = []
    NEEDS = list(range(150, 271, 10))
    NS = [2, 3, 5, 8, 12]
    VARIANTS = [("基本（Cは60%で360）", 0.6, 360, 0.0), ("Cは50%で432", 0.5, 432, 0.0), ("Cは70%で309", 0.7, 309, 0.0),
                ("基本＋敵の体力が±10%散らばる", 0.6, 360, 0.10)]
    for vi, (vname, ch, cd, spread) in enumerate(VARIANTS):
        Wv = weapons(ch, cd)
        mv = {k: mean_of(Wv[k]["pmf"]) for k in keys}
        best_mean = max(mv, key=mv.get)
        for need in NEEDS:
            for n in NS:
                hp = need * n
                sh = {k: (kill_share_hp_spread(Wv[k]["pmf"], n, hp, spread) if spread > 0 else kill_share(Wv[k]["pmf"], n, hp)) * 100
                      for k in keys}
                t = top_keys(sh)
                rec = {"variant": vname, "need_per_hit": need, "hits": n, "hp": hp, **{k: r(sh[k], 2) for k in keys},
                       "top": "・".join(t), "best_mean": best_mean,
                       "best_mean_is_top": int(best_mean in t), "lowest_mean_A_is_top": int("A" in t),
                       "all_100_or_0": int(all(sh[k] > 99.995 for k in keys) or all(sh[k] < 0.005 for k in keys))}
                grid.append(rec)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gsum = []
    for vname, *_ in VARIANTS:
        g = grid[grid.variant == vname]
        gi = g[g.all_100_or_0 == 0]
        gsum.append({"variant": vname, "settings": len(g), "settings_not_all_same": len(gi),
                     "best_mean_top": int(gi.best_mean_is_top.sum()),
                     "A_top": int(gi.lowest_mean_A_is_top.sum()),
                     "top_counts": {kk: int(gi.top.str.contains(kk).sum()) for kk in keys},
                     "best_mean_top_need_le_mean": int(gi[gi.need_per_hit <= 210].best_mean_is_top.sum()),
                     "settings_need_le_mean": int((gi.need_per_hit <= 210).sum()),
                     "best_mean_top_need_gt_mean": int(gi[gi.need_per_hit > 210].best_mean_is_top.sum()),
                     "settings_need_gt_mean": int((gi.need_per_hit > 210).sum()),
                     "A_top_need_le_190": int(gi[gi.need_per_hit <= 190].lowest_mean_A_is_top.sum()),
                     "settings_need_le_190": int((gi.need_per_hit <= 190).sum()),
                     "C_or_D_top_need_ge_220": int(gi[gi.need_per_hit >= 220].top.str.contains("C|D").sum()),
                     "settings_need_ge_220": int((gi.need_per_hit >= 220).sum())})
    # 12回のとき、要るダメージが平均に近いところ
    g0 = grid[grid.variant == VARIANTS[0][0]]
    n12 = {str(nd): {k: float(g0[(g0.hits == 12) & (g0.need_per_hit == nd)][k].iloc[0]) for k in keys} | {"hp": nd * 12}
           for nd in [190, 200, 210, 220]}
    from math import comb
    formula = {"A_min_total_5hits": 190 * N0, "C_hits_needed_hp900": int(np.ceil(HP0 / 360)),
               "C_share_3of5_formula": r(sum(comb(5, j) * 0.6 ** j * 0.4 ** (5 - j) for j in range(3, 6)) * 100, 2),
               "D_share_formula_1_minus_0.9pow5": r((1 - 0.9 ** 5) * 100, 2),
               "B_share_formula_1_minus_0.75pow5": r((1 - 0.75 ** 5) * 100, 2)}

    out = {"hp": HP0, "hits": N0, "sim_battles": SIMN, "mean_rank": mean_rank,
           "weapons": base,
           "kill_rank": sorted(keys, key=lambda k: -base_share[k]),
           "pick_hp_5hits": pick_hp,
           "hp_range_where_C_top_5hits": [int(byhp[byhp.top.str.contains("C")].hp.min()), int(byhp[byhp.top.str.contains("C")].hp.max())],
           "hp_values_where_C_top_5hits": [int(h) for h in byhp[byhp.top.str.contains("C")].hp],
           "hp_values_5hits": len(byhp),
           "hp_values_where_C_top_count": int(byhp.top.str.contains("C").sum()),
           "hp_values_where_A_top_count": int(byhp.top.str.contains("A").sum()),
           "hp_values_where_D_top_count": int(byhp.top.str.contains("D").sum()),
           "hp_values_where_B_top_count": int(byhp.top.str.contains("B").sum()),
           "grid_summary": gsum, "hits12_by_need": n12, "formula_check": formula,
           "max_abs_exact_minus_sim": r(max(abs(base[k]["kill_share_exact"] - base[k]["kill_share_sim"]) for k in keys), 2),
           "note": "kill_share_exact は1回のダメージの出方の組み合わせをすべて足し合わせた値（式どおり）、kill_share_sim は乱数の戦い100,000回"}
    json.dump(out, open(RES / "a1116_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回のダメージの出方
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6), sharey=True)
    for ax, k in zip(axes, keys):
        p = W[k]["pmf"]; xs = np.nonzero(p)[0]
        if k == "A":
            ax.bar(xs, p[xs] * 100, width=1.0, color=INK)
        else:
            ax.bar(xs, p[xs] * 100, width=40, color=COLORS[k])
            for xx in xs:
                ax.text(xx, p[xx] * 100 + 2, f"{xx}\n{p[xx] * 100:.0f}%", ha="center", va="bottom", fontsize=8.5)
        ax.axvline(means[k], color=INK, ls="--", lw=1)
        ax.text(means[k] + 15, 92, f"平均 {means[k]:.1f}", fontsize=9, color=INK)
        ax.set_xlim(-30, 800); ax.set_ylim(0, 105)
        ax.set_title(W[k]["name"], loc="left", fontsize=11)
        ax.set_xlabel("1回のダメージ")
    axes[0].annotate("190〜210の21通りに\n1つ約4.8%ずつ", xy=(205, 4), xytext=(330, 30), fontsize=8.5,
                     arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
    axes[0].set_ylabel("確率（%）")
    fig.suptitle("作成者が置いた4つの武器：1回の平均のダメージは C（216）＞ B（212.5）＞ D（210）＞ A（200）", x=0.01, y=1.05, ha="left", fontsize=12)
    save(fig, "a1116_damage.png", SRC)

    # 図2：体力を変えたときの、5回のうちに倒せる割合
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for k in keys:
        ax.plot(byhp.hp, byhp[k], color=COLORS[k], lw=2, marker="o", ms=3, label=f"{W[k]['name']}（平均 {means[k]:.1f}）")
    ax.axvline(HP0, color=INK, ls=":", lw=1)
    ax.text(HP0 + 8, 3, "基本の体力 900", fontsize=9)
    ax.set_ylim(0, 105); ax.set_xlabel("敵の体力"); ax.set_ylabel("5回のうちに倒せる割合（%、式どおり）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.suptitle("5回のうちに倒せる割合：いちばん高い武器は、敵の体力で A・B・C・D と入れかわる", x=0.01, y=1.02, ha="left", fontsize=12)
    save(fig, "a1116_by_hp.png", SRC)

    # 図3：確かめ（基本）。1回あたりに要るダメージ×回数で、どの武器がいちばんか
    fig, ax = plt.subplots(figsize=(10, 3.9))
    for yi, n in enumerate(NS):
        for xi, need in enumerate(NEEDS):
            row = g0[(g0.hits == n) & (g0.need_per_hit == need)].iloc[0]
            if row.all_100_or_0:
                ax.add_patch(plt.Rectangle((xi - 0.5, yi - 0.5), 1, 1, color="#f0f0ee"))
                ax.text(xi, yi, "全部" + ("100%" if row.A > 50 else "0%"), ha="center", va="center", fontsize=6.5, color=GRAY)
                continue
            t = row.top.split("・")
            ax.add_patch(plt.Rectangle((xi - 0.5, yi - 0.5), 1, 1, color=COLORS[t[0]], alpha=0.75))
            ax.text(xi, yi, "・".join(t), ha="center", va="center", fontsize=8.5, color="white" if t[0] != "A" else INK)
    ax.set_xlim(-0.5, len(NEEDS) - 0.5); ax.set_ylim(-0.5, len(NS) - 0.5)
    ax.set_xticks(range(len(NEEDS))); ax.set_xticklabels([str(v) for v in NEEDS])
    ax.set_yticks(range(len(NS))); ax.set_yticklabels([f"{n}回" for n in NS])
    ax.set_xlabel("1回あたりに要るダメージ（敵の体力÷攻撃できる回数）"); ax.set_ylabel("攻撃できる回数")
    for s in ["left", "bottom"]:
        ax.spines[s].set_visible(False)
    fig.suptitle("確かめ（65通り）：倒せる割合がいちばん高い武器。平均がいちばん大きい C がいちばんになるのは一部だけ", x=0.01, y=1.03, ha="left", fontsize=12)
    save(fig, "a1116_robust.png", SRC)

    print(json.dumps(base, ensure_ascii=False, indent=0))
    print(byhp.to_string())
    print(json.dumps(gsum, ensure_ascii=False))
    print(n12)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
