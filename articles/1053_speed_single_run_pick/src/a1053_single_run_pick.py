"""1053 1回ずつ測った処理時間で速い方を選ぶと、何回に1回まちがえるのか？（架空のデータ）

架空のアプリの処理 A と B。処理時間（ミリ秒）は作成者が置いた分布からの乱数で、実機では測っていない。
1回の処理時間 ＝ ふだんの時間（中央値 × exp(σ×標準正規)）＋ まれに入る大きな遅れ（確率 p で平均60ミリ秒の指数分布）。
B のふだんの時間は A より d（基本5%）短く、まれな遅れは A と B で同じ。なので B は平均でも中央値でも本当に速い。
1回ずつ（または n 回ずつの平均）で比べて「A のほうが速い」と出る割合を、まちがえる割合として数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1053
SRC = "架空のアプリの処理時間（作成者が置いた分布からの乱数、seed 1053）"
BASE = {"d": 0.05, "sigma": 0.10, "p": 0.05}
MED_A = 120.0      # A のふだんの時間の中央値（ミリ秒）
SPIKE_MEAN = 60.0  # まれな遅れの平均（ミリ秒）
NS = [1, 2, 3, 5, 10, 20, 30, 50, 100]
r = lambda x, k=4: round(float(x), k)


def runs(rng, shape, med, sigma, p):
    base = med * np.exp(sigma * rng.standard_normal(shape))
    spike = np.where(rng.random(shape) < p, rng.exponential(SPIKE_MEAN, shape), 0.0)
    return base + spike


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def error_curve(rng, d, sigma, p, reps, nmax):
    """n=1..nmax 回ずつの平均で比べたとき、A のほうが速いと出る割合"""
    a = runs(rng, (reps, nmax), MED_A, sigma, p)
    b = runs(rng, (reps, nmax), MED_A * (1 - d), sigma, p)
    k = np.arange(1, nmax + 1)
    ma, mb = a.cumsum(1) / k, b.cumsum(1) / k
    return (ma < mb).mean(0)


def first_n_below(curve, thr=0.05):
    idx = np.where(curve <= thr)[0]
    return int(idx[0] + 1) if len(idx) else None


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # データ：基本の置き方で A・B を500回ずつ
    a500 = runs(rng, 500, MED_A, BASE["sigma"], BASE["p"])
    b500 = runs(rng, 500, MED_A * (1 - BASE["d"]), BASE["sigma"], BASE["p"])
    pd.DataFrame({"run": np.arange(1, 501), "A_ms": a500.round(3), "B_ms": b500.round(3)}).to_csv(
        DATA / "runs_a_b_500.csv", index=False)

    # 本当の値（基本）
    true_mean_a = MED_A * math.exp(BASE["sigma"] ** 2 / 2) + BASE["p"] * SPIKE_MEAN
    true_mean_b = MED_A * (1 - BASE["d"]) * math.exp(BASE["sigma"] ** 2 / 2) + BASE["p"] * SPIKE_MEAN
    big_a = runs(rng, 2_000_000, MED_A, BASE["sigma"], BASE["p"])
    big_b = runs(rng, 2_000_000, MED_A * (1 - BASE["d"]), BASE["sigma"], BASE["p"])

    # 1) 基本：1回ずつの比べ（200万組）と、まれな遅れの確率ごとの n 回ずつの平均
    one_shot = float((big_a < big_b).mean())
    formula_no_spike = phi(math.log(1 - BASE["d"]) / (BASE["sigma"] * math.sqrt(2)))
    a0 = runs(rng, 2_000_000, MED_A, BASE["sigma"], 0.0)
    b0 = runs(rng, 2_000_000, MED_A * (1 - BASE["d"]), BASE["sigma"], 0.0)
    one_shot_no_spike = float((a0 < b0).mean())

    rows = []
    curves = {}
    for p in [0.0, 0.05, 0.20]:
        c = error_curve(np.random.default_rng(SEED * 10 + int(p * 100)), BASE["d"], BASE["sigma"], p, 10000, 400)
        curves[p] = c
        for n in NS:
            rows.append({"p_spike": p, "n_each": n, "wrong_pct": r(c[n - 1] * 100, 2)})
        rows.append({"p_spike": p, "n_each": "n_for_wrong_le_5pct", "wrong_pct": first_n_below(c)})
    by_n = pd.DataFrame(rows)
    by_n.to_csv(RES / "wrong_by_n.csv", index=False)
    n_need = {str(p): first_n_below(curves[p]) for p in curves}

    # 2) 同じ速さ（d=0）なのに、1回ずつで「5%以上違う」と出る割合
    s0a = runs(rng, 2_000_000, MED_A, BASE["sigma"], BASE["p"])
    s0b = runs(rng, 2_000_000, MED_A, BASE["sigma"], BASE["p"])
    ratio = s0b / s0a
    same_diff_ge5 = float(((ratio <= 0.95) | (ratio >= 1 / 0.95)).mean())
    c10a = runs(rng, (200000, 10), MED_A, BASE["sigma"], BASE["p"]).mean(1)
    c10b = runs(rng, (200000, 10), MED_A, BASE["sigma"], BASE["p"]).mean(1)
    ratio10 = c10b / c10a
    same_diff_ge5_n10 = float(((ratio10 <= 0.95) | (ratio10 >= 1 / 0.95)).mean())

    # 3) 確かめ：差 d × ふだんのばらつき σ × まれな遅れの確率 p の36通り
    grid = []
    gi = 0
    for d in [0.02, 0.05, 0.10, 0.20]:
        for sg in [0.05, 0.10, 0.20]:
            for p in [0.0, 0.05, 0.20]:
                gi += 1
                c = error_curve(np.random.default_rng(SEED * 100 + gi), d, sg, p, 4000, 1000)
                f = phi(math.log(1 - d) / (sg * math.sqrt(2)))
                grid.append({"d": d, "sigma": sg, "p_spike": p, "wrong_n1_pct": r(c[0] * 100, 2),
                             "formula_n1_no_spike_pct": r(f * 100, 2) if p == 0 else None,
                             "wrong_n10_pct": r(c[9] * 100, 2), "n_for_wrong_le_5pct": first_n_below(c)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    g0 = g[g.p_spike == 0]
    max_formula_gap = float((g0.wrong_n1_pct - g0.formula_n1_no_spike_pct).abs().max())
    gn = g.n_for_wrong_le_5pct.dropna()

    out = {
        "settings": {"median_A_ms": MED_A, "d_base": BASE["d"], "sigma_base": BASE["sigma"], "p_spike_base": BASE["p"],
                     "spike_mean_ms": SPIKE_MEAN, "pairs_one_shot": 2_000_000, "reps_by_n": 10000, "by_n_max": 400, "reps_grid": 4000,
                     "grid_n_max": 1000},
        "headline": {
            "true_mean_A_ms": r(true_mean_a, 2), "true_mean_B_ms": r(true_mean_b, 2),
            "true_mean_diff_pct": r((1 - true_mean_b / true_mean_a) * 100, 2),
            "sim_mean_A_ms": r(big_a.mean(), 2), "sim_mean_B_ms": r(big_b.mean(), 2),
            "true_median_A_ms": r(np.median(big_a), 2), "true_median_B_ms": r(np.median(big_b), 2),
            "one_shot_wrong_pct": r(one_shot * 100, 2),
            "one_shot_wrong_no_spike_pct": r(one_shot_no_spike * 100, 2),
            "formula_no_spike_pct": r(formula_no_spike * 100, 2),
            "n10_wrong_pct": r(curves[0.05][9] * 100, 2),
            "by_n_n1_wrong_pct": r(curves[0.05][0] * 100, 2),
            "one_shot_minus_by_n_n1_pt": r(one_shot * 100 - round(curves[0.05][0] * 100, 2), 2),
            "n_for_wrong_le_5pct": n_need,
            "same_speed_one_shot_diff_ge5_pct": r(same_diff_ge5 * 100, 2),
            "same_speed_n10_diff_ge5_pct": r(same_diff_ge5_n10 * 100, 2),
        },
        "grid_summary": {
            "n": int(len(g)),
            "wrong_n1_min_pct": r(g.wrong_n1_pct.min(), 2), "wrong_n1_max_pct": r(g.wrong_n1_pct.max(), 2),
            "wrong_n10_min_pct": r(g.wrong_n10_pct.min(), 2), "wrong_n10_max_pct": r(g.wrong_n10_pct.max(), 2),
            "no_spike_max_gap_to_formula_pt": r(max_formula_gap, 2),
            "n_need_min": int(gn.min()), "n_need_max_found": int(gn.max()),
            "n_need_over_1000_count": int(g.n_for_wrong_le_5pct.isna().sum()),
            "n_need_1_count": int((g.n_for_wrong_le_5pct == 1).sum()),
            "n10_not_better_than_n1_count": int((g.wrong_n10_pct >= g.wrong_n1_pct).sum()),
            "n10_not_better_than_n1_cases": g[g.wrong_n10_pct >= g.wrong_n1_pct][["d", "sigma", "p_spike", "wrong_n1_pct", "wrong_n10_pct"]].to_dict("records"),
            "d5_s10_by_p": {str(p): {"wrong_n1_pct": float(g[(g.d == .05) & (g.sigma == .1) & (g.p_spike == p)].wrong_n1_pct.iloc[0]),
                                     "n_need": g[(g.d == .05) & (g.sigma == .1) & (g.p_spike == p)].n_for_wrong_le_5pct.iloc[0]}
                            for p in [0.0, 0.05, 0.2]},
        },
        "wrong_by_n": by_n.to_dict("records"),
    }
    out["grid_summary"]["d5_s10_by_p"] = {k: {"wrong_n1_pct": v["wrong_n1_pct"],
                                              "n_need": None if pd.isna(v["n_need"]) else int(v["n_need"])}
                                          for k, v in out["grid_summary"]["d5_s10_by_p"].items()}
    json.dump(out, open(RES / "a1053_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回ずつの処理時間の分布（データの500回ずつ）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.linspace(60, 300, 61)
    ax.hist(a500, bins=bins, color=ORANGE, alpha=.55, label="A（ふだんの時間の中央値120ミリ秒）")
    ax.hist(b500, bins=bins, color=BLUE, alpha=.55, label="B（Aより5%短い）")
    ax.set_xlabel("1回の処理時間（ミリ秒）"); ax.set_ylabel("回数（500回ずつ）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"本当はBが速いのに、1回ずつ比べるとAが速いと出るのは{one_shot*100:.1f}%", fontsize=12)
    save(fig, "a1053_one_shot.png", SRC)

    # 図2：n 回ずつの平均で比べたときのまちがい
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    k = np.arange(1, 401)
    for p, col, lab in [(0.0, GRAY, "まれな遅れなし"), (0.05, BLUE, "まれな遅れ5%（基本）"), (0.20, ORANGE, "まれな遅れ20%")]:
        ax.plot(k, curves[p] * 100, color=col, lw=2, label=lab)
    ax.axhline(5, color=INK, lw=.8, ls="--"); ax.text(250, 6, "5%", fontsize=9)
    ax.set_xscale("log"); ax.set_ylim(0, 50)
    ax.set_xticks([1, 2, 5, 10, 20, 50, 100, 200, 400]); ax.set_xticklabels(["1", "2", "5", "10", "20", "50", "100", "200", "400"])
    ax.set_xlabel("A・B を何回ずつ測って平均したか（対数の目盛り）"); ax.set_ylabel("Aが速いと出る割合（%）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("まれな遅れが多いほど、まちがいを5%まで減らすのに回数が要る（本当の差5%・ばらつき10%）", fontsize=11)
    save(fig, "a1053_wrong_by_n.png", SRC)

    # 図3：36通りの1回ずつのまちがい（まれな遅れ5%の12通りを棒、ほかの p を点）
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    lab, y = [], 0
    for d in [0.02, 0.05, 0.10, 0.20]:
        for sg in [0.05, 0.10, 0.20]:
            sub = g[(g.d == d) & (g.sigma == sg)].set_index("p_spike")
            ax.barh(y, sub.loc[0.05, "wrong_n1_pct"], color=LIGHT)
            ax.plot(sub.loc[0.0, "wrong_n1_pct"], y, "o", color=GRAY, ms=5)
            ax.plot(sub.loc[0.20, "wrong_n1_pct"], y, "D", color=ORANGE, ms=5)
            lab.append(f"差{int(d*100)}%・ばらつき{int(sg*100)}%"); y += 1
    ax.set_yticks(range(len(lab))); ax.set_yticklabels(lab, fontsize=8.5); ax.invert_yaxis()
    ax.set_xlim(0, 55); ax.set_xlabel("1回ずつの比べでAが速いと出る割合（%）")
    ax.plot([], [], "s", color=LIGHT, label="棒：まれな遅れ5%"); ax.plot([], [], "o", color=GRAY, label="まれな遅れなし")
    ax.plot([], [], "D", color=ORANGE, label="まれな遅れ20%")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("まちがいの割合は、本当の差・ばらつき・まれな遅れで大きく変わる（36通り）", fontsize=12)
    save(fig, "a1053_grid.png", SRC)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, indent=1))
    print("sec", out["run_sec"])


if __name__ == "__main__":
    main()
