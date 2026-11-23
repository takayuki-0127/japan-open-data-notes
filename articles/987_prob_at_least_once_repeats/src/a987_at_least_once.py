"""987 「少なくとも1回」の確率は、回数でどう増えるのか？（架空のデータ）

架空の工場の印刷機。1回の印刷の仕事ごとに、ある確率で「やり直し」が出ると置く。
(1) 毎回同じ確率で、前の回と関係なく起きるとき：「少なくとも1回」は 1-(1-p)^n（式どおり）で、
    確率を回数分足した n×p とどれだけずれるか。
(2) 台ごとに確率がばらつくとき（平均は同じ2%）。
(3) やり直しが続けて起きやすいとき（全体の割合は同じ2%）。
(4) 「少なくとも1回あった日の割合」から1回あたりの確率を逆算すると、どれだけずれるか。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 987
SRC = "架空の工場の印刷機の仕事（作成者が乱数で作成、seed 987）"
P0, N0 = 0.02, 30                    # 基本：1回2%、1日30回
PS = [0.005, 0.01, 0.02, 0.05, 0.1]
NS = [1, 5, 10, 20, 30, 50, 100]
SDS = [0.0, 0.01, 0.02, 0.03]        # 台ごとの確率のばらつき（標準偏差）
RS = [0.02, 0.1, 0.2, 0.4]           # やり直しの次の回もやり直しになる確率（0.02は前の回と関係なし）
N_SIM = 200_000


def beta_ab(m, sd):
    s = m * (1 - m) / sd ** 2 - 1
    return m * s, (1 - m) * s


def draw_p(rng, size, m, sd):
    if sd == 0:
        return np.full(size, m)
    a, b = beta_ab(m, sd)
    return rng.beta(a, b, size)


def formula_none_beta(n, m, sd):
    """台ごとの確率がベータ分布のとき、n回で1回も起きない確率（式）"""
    if sd == 0:
        return (1 - m) ** n
    a, b = beta_ab(m, sd)
    lb = lambda x, y: math.lgamma(x) + math.lgamma(y) - math.lgamma(x + y)
    return math.exp(lb(a, b + n) - lb(a, b))


def formula_none_markov(n, pi, r):
    """続けて起きやすいとき（全体の割合 pi、やり直しの次もやり直し r）、n回で1回も起きない確率（式）"""
    a = pi * (1 - r) / (1 - pi)       # やり直しでない回の次にやり直しになる確率
    return (1 - pi) * (1 - a) ** (n - 1)


def sim_jobs(rng, n_unit, n, p, r):
    """n_unit 台×1日 n 回。p は台ごとの全体の割合、r はやり直しの次もやり直しの確率。回数の行列を返す"""
    p = np.broadcast_to(p, (n_unit,)).astype(float)
    if r is None:
        return rng.random((n_unit, n)) < p[:, None]
    a = p * (1 - r) / (1 - p)
    x = np.empty((n_unit, n), dtype=bool)
    x[:, 0] = rng.random(n_unit) < p
    for t in range(1, n):
        u = rng.random(n_unit)
        x[:, t] = np.where(x[:, t - 1], u < r, u < a)
    return x


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 毎回同じ確率・前の回と関係なし：式・足し算・乱数
    rows = []
    for p in PS:
        for n in NS:
            k = rng.binomial(n, p, N_SIM)
            f = 1 - (1 - p) ** n
            rows.append({"p_pct": p * 100, "n": n, "formula_pct": round(f * 100, 2), "sum_pct": round(n * p * 100, 2),
                         "sim_pct": round(float((k > 0).mean()) * 100, 2),
                         "sum_minus_formula_pts": round((n * p - f) * 100, 2),
                         "mean_count": round(float(k.mean()), 3)})
    t1 = pd.DataFrame(rows)
    t1.to_csv(RES / "independent_formula_vs_sum.csv", index=False)
    base = t1[(t1.p_pct == 2) & (t1.n == 30)].iloc[0]
    # 足し算が式より5ポイント以上大きくなる最初の回数（p ごと、1〜200回で式から）
    first5 = {}
    for p in PS:
        for n in range(1, 201):
            if n * p - (1 - (1 - p) ** n) >= 0.05:
                first5[f"{p*100:g}%"] = n
                break

    # 2) 台ごとに確率がばらつく（平均2%）
    rows = []
    for sd in SDS:
        pp = draw_p(rng, N_SIM, P0, sd)
        for n in NS:
            x = rng.binomial(n, pp)
            rows.append({"sd_pct": sd * 100, "n": n, "sim_pct": round(float((x > 0).mean()) * 100, 2),
                         "formula_pct": round((1 - formula_none_beta(n, P0, sd)) * 100, 2),
                         "mean_count": round(float(x.mean()), 3)})
    t2 = pd.DataFrame(rows)
    t2.to_csv(RES / "machine_spread.csv", index=False)
    # 20日（600回）で一度もやり直しの出ない台の割合
    long_rows = []
    for sd in SDS:
        pp = draw_p(rng, N_SIM, P0, sd)
        x = rng.binomial(600, pp)
        long_rows.append({"sd_pct": sd * 100, "n": 600, "never_sim_pct": round(float((x == 0).mean()) * 100, 3),
                          "never_formula_pct": round(formula_none_beta(600, P0, sd) * 100, 3)})
    t2b = pd.DataFrame(long_rows)
    t2b.to_csv(RES / "machine_spread_600jobs_never.csv", index=False)

    # 3) 続けて起きやすい（全体の割合2%）
    rows = []
    for r in RS:
        x = sim_jobs(rng, N_SIM, max(NS), P0, None if r == P0 else r)
        cs = x.cumsum(1)
        for n in NS:
            c = cs[:, n - 1]
            rows.append({"r_pct": r * 100, "n": n, "sim_pct": round(float((c > 0).mean()) * 100, 2),
                         "formula_pct": round((1 - formula_none_markov(n, P0, r)) * 100, 2),
                         "mean_count": round(float(c.mean()), 3),
                         "three_plus_pct": round(float((c >= 3).mean()) * 100, 2)})
    t3 = pd.DataFrame(rows)
    t3.to_csv(RES / "clustered.csv", index=False)

    # 4) ばらつき × 続けて起きやすさ × 回数：少なくとも1回の割合と、そこからの逆算
    rows = []
    for n in [10, 30, 100]:
        for sd in SDS:
            for r in RS:
                pp = draw_p(rng, 100_000, P0, sd)
                x = sim_jobs(rng, 100_000, n, pp, None if r == P0 else r)
                c = x.sum(1)
                f = float((c > 0).mean())
                rows.append({"n": n, "sd_pct": sd * 100, "r_pct": r * 100,
                             "at_least_once_pct": round(f * 100, 2),
                             "formula_independent_pct": round((1 - (1 - P0) ** n) * 100, 2),
                             "back_calc_p_pct": round((1 - (1 - f) ** (1 / n)) * 100, 3),
                             "count_based_p_pct": round(float(c.sum()) / (100_000 * n) * 100, 3)})
    t4 = pd.DataFrame(rows)
    t4.to_csv(RES / "grid_spread_cluster.csv", index=False)
    g30 = t4[t4.n == 30]

    # 1回分のデータ：40台×20日×30回（ばらつき1%、続けて起きる0.2）
    r1 = np.random.default_rng(SEED + 1)
    pm = draw_p(r1, 40, P0, 0.01)
    recs = []
    for d in range(1, 21):
        x = sim_jobs(r1, 40, N0, pm, 0.2)
        c = x.sum(1)
        for i in range(40):
            recs.append({"machine": f"M{i+1:02d}", "p_machine": round(float(pm[i]), 4), "day": d, "jobs": N0,
                         "redo": int(c[i]), "any_redo": int(c[i] > 0)})
    dd = pd.DataFrame(recs)
    dd.to_csv(DATA / "machine_days.csv", index=False)
    f1 = float(dd.any_redo.mean())
    one = {"machine_days": len(dd), "any_redo_pct": round(f1 * 100, 2),
           "redo_per_job_pct": round(float(dd.redo.sum()) / (len(dd) * N0) * 100, 3),
           "back_calc_p_pct": round((1 - (1 - f1) ** (1 / N0)) * 100, 3),
           "machines_never_in_20days": int((dd.groupby("machine").redo.sum() == 0).sum()),
           "p_machine_range_pct": [round(float(pm.min()) * 100, 2), round(float(pm.max()) * 100, 2)]}

    def pick(t, **kw):
        q = t
        for k, v in kw.items():
            q = q[np.isclose(q[k], v)]
        return q.iloc[0]

    out = {"setup": {"p_base_pct": P0 * 100, "n_base": N0, "ps_pct": [p * 100 for p in PS], "ns": NS,
                     "machine_sd_pct": [s * 100 for s in SDS], "repeat_after_redo_pct": [r * 100 for r in RS],
                     "n_sim": N_SIM, "grid_n_sim": 100_000},
           "base_independent": {"formula_pct": float(base.formula_pct), "sum_pct": float(base.sum_pct),
                                "sim_pct": float(base.sim_pct), "mean_count": float(base.mean_count)},
           "first_n_sum_exceeds_formula_by_5pts": first5,
           "max_abs_sim_minus_formula_pts": {
               "independent": round(float((t1.sim_pct - t1.formula_pct).abs().max()), 2),
               "machine_spread": round(float((t2.sim_pct - t2.formula_pct).abs().max()), 2),
               "clustered": round(float((t3.sim_pct - t3.formula_pct).abs().max()), 2)},
           "n30_spread": {f"{s*100:g}": float(pick(t2, sd_pct=s * 100, n=30).sim_pct) for s in SDS},
           "n30_clustered": {f"{r*100:g}": float(pick(t3, r_pct=r * 100, n=30).sim_pct) for r in RS},
           "never_in_600": t2b.to_dict("records"),
           "grid_n30_at_least_once_range_pct": [float(g30.at_least_once_pct.min()), float(g30.at_least_once_pct.max())],
           "grid_n30_back_calc_range_pct": [float(g30.back_calc_p_pct.min()), float(g30.back_calc_p_pct.max())],
           "grid_count_based_range_pct": [float(t4.count_based_p_pct.min()), float(t4.count_based_p_pct.max())],
           "grid_max_excess_over_formula_pts": round(float((t4.at_least_once_pct - t4.formula_independent_pct).max()), 2),
           "grid_all_range_by_n": {str(n): [float(t4[t4.n == n].at_least_once_pct.min()), float(t4[t4.n == n].at_least_once_pct.max())]
                                   for n in [10, 30, 100]},
           "one_draw": one}

    # 図1：式と足し算
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    n = np.arange(1, 101)
    for p, c in [(0.01, LIGHT), (0.02, BLUE), (0.05, ORANGE)]:
        ax.plot(n, (1 - (1 - p) ** n) * 100, color=c, lw=2, label=f"1回{p*100:g}%：少なくとも1回（式）")
        ax.plot(n, n * p * 100, color=c, lw=1.2, ls="--", label=f"1回{p*100:g}%：回数分を足した値")
        s = t1[np.isclose(t1.p_pct, p * 100)]
        ax.scatter(s.n, s.sim_pct, color=c, s=18, zorder=3)
    ax.axhline(100, color=GRAY, lw=0.8)
    ax.annotate(f"30回：式 {base.formula_pct:.2f}%／足し算 {base.sum_pct:.0f}%", (30, base.formula_pct), (38, 25),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", color=INK, lw=0.6))
    ax.set_xlabel("くり返す回数"); ax.set_ylabel("%（点は乱数20万回）"); ax.set_ylim(0, 160)
    ax.legend(frameon=False, fontsize=7.8, loc="upper left", ncol=1)
    ax.set_title("足し算は100%を超えるが、「少なくとも1回」は100%に近づくだけ")
    save(fig, "a987_formula_vs_sum.png", SRC)

    # 図2：ばらつき・続けて起きやすいと
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.9), sharey=True)
    for s, c in zip(SDS, [INK, LIGHT, BLUE, ORANGE]):
        x = t2[np.isclose(t2.sd_pct, s * 100)]
        axs[0].plot(x.n, x.sim_pct, marker="o", ms=3.5, color=c, label=f"台ごとのばらつき {s*100:g}%")
    for r, c in zip(RS, [INK, LIGHT, BLUE, ORANGE]):
        x = t3[np.isclose(t3.r_pct, r * 100)]
        lab = "前の回と関係なし" if r == P0 else f"やり直しの次もやり直し {r*100:g}%"
        axs[1].plot(x.n, x.sim_pct, marker="o", ms=3.5, color=c, label=lab)
    axs[0].set_title("台ごとに確率がばらつく（平均2%）", fontsize=11)
    axs[1].set_title("続けて起きやすい（全体の割合2%）", fontsize=11)
    for a in axs:
        a.set_xlabel("1台がくり返す回数"); a.legend(frameon=False, fontsize=8, loc="lower right"); a.set_ylim(0, 100)
    axs[0].set_ylabel("少なくとも1回やり直しが出る割合（%）")
    fig.suptitle("平均は同じ2%でも、「少なくとも1回」は式より低くなる", y=1.02)
    save(fig, "a987_spread_cluster.png", SRC)

    # 図3：30回での少なくとも1回と逆算した確率（16通り）
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.8))
    for a, col, ttl, fmt in [(axs[0], "at_least_once_pct", "少なくとも1回の割合（%、式では45.45%）", "{:.2f}"),
                             (axs[1], "back_calc_p_pct", "その割合から逆算した1回の確率（%、本当は2%）", "{:.3f}")]:
        m = g30.pivot(index="sd_pct", columns="r_pct", values=col).values
        im = a.imshow(m, cmap="Blues_r" if col == "at_least_once_pct" else "Oranges_r", aspect="auto")
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                a.text(j, i, fmt.format(m[i, j]), ha="center", va="center", fontsize=9,
                       color="white" if (m[i, j] < np.median(m)) else INK)
        a.set_xticks(range(len(RS))); a.set_xticklabels(["関係なし"] + [f"{r*100:g}%" for r in RS[1:]])
        a.set_yticks(range(len(SDS))); a.set_yticklabels([f"{s*100:g}%" for s in SDS])
        a.set_xlabel("やり直しの次もやり直しになる確率"); a.set_ylabel("台ごとのばらつき（標準偏差）")
        a.set_title(ttl, fontsize=10)
    fig.suptitle("1日30回・平均2%の16通り（各10万台）", y=1.03)
    save(fig, "a987_grid.png", SRC)

    json.dump(out, open(RES / "a987_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(t1.to_string()); print(t2.to_string()); print(t3.to_string()); print(t4.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
