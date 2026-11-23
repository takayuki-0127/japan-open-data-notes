"""1054 温まる前の最初の数回を入れて平均すると、どれだけ遅く出るのか？（架空のデータ）

架空のアプリの処理。起動してから k 回目の処理時間（ミリ秒）＝
  温まったあとの時間（中央値 M × exp(σ×標準正規)）×（1 ＋ W × exp(−(k−1)/τ)）。
W は1回目がどれだけ遅いか（1回目は 1＋W 倍）、τ は温まりの早さ（回数）。作成者が置いた分布からの乱数で、実機では測っていない。
最初の何回かを入れて平均すると、温まったあとの平均よりどれだけ長く出るか、最初の m 回を捨てると残りはどれだけか、
温まりに時間がかかる速いやり方 A と温まりのないやり方 B を比べると、どちらが速いと出るかを数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1054
SRC = "架空のアプリの処理時間（作成者が置いた分布からの乱数、seed 1054）"
BASE = {"W": 3.0, "tau": 2.0, "sigma": 0.10}
M_B = 100.0          # B（温まりなし）の中央値
A_FASTER = 0.05      # A は温まったあと B より5%速い
NS = [5, 10, 30, 100]
DROPS = [0, 1, 3, 5]
REPS = 20000
r = lambda x, k=4: round(float(x), k)


def warm_factor(n, W, tau):
    k = np.arange(1, n + 1)
    return 1 + W * np.exp(-(k - 1) / tau)


def runs(rng, reps, n, med, W, tau, sigma):
    return med * np.exp(sigma * rng.standard_normal((reps, n))) * warm_factor(n, W, tau)[None, :]


def formula_bias(n, m, W, tau):
    """最初の m 回を捨て、残り n−m 回の平均が、温まったあとの平均より何%長いか（式）"""
    f = warm_factor(n, W, tau)[m:]
    return (f.mean() - 1) * 100


def crossover(W, tau, nmax=100000):
    """起動から N 回動かしたときの合計（期待値）で、A が B より短くなる最小の N（式）"""
    k = np.arange(1, nmax + 1)
    cum_a = np.cumsum((1 - A_FASTER) * (1 + W * np.exp(-(k - 1) / tau)))
    idx = np.where(cum_a <= k)[0]
    return int(idx[0] + 1) if len(idx) else None


def evaluate(rng, W, tau, sigma, n=10):
    a = runs(rng, REPS, n, M_B * (1 - A_FASTER), W, tau, sigma)
    b = runs(rng, REPS, n, M_B, 0.0, tau, sigma)
    steady = M_B * (1 - A_FASTER) * math.exp(sigma ** 2 / 2)
    out = {}
    for m in DROPS:
        ma, mb = a[:, m:].mean(1), b[:, m:].mean(1)
        out[f"bias_drop{m}_pct"] = (ma.mean() / steady - 1) * 100
        out[f"formula_drop{m}_pct"] = formula_bias(n, m, W, tau)
        out[f"pick_A_drop{m}_pct"] = (ma < mb).mean() * 100
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    W, tau, sg = BASE["W"], BASE["tau"], BASE["sigma"]

    # データ：A・B を20回起動し、それぞれ30回ずつ
    a20 = runs(rng, 20, 30, M_B * (1 - A_FASTER), W, tau, sg)
    b20 = runs(rng, 20, 30, M_B, 0.0, tau, sg)
    pd.DataFrame({"start": np.repeat(np.arange(1, 21), 30), "run": np.tile(np.arange(1, 31), 20),
                  "A_ms": a20.ravel().round(3), "B_ms": b20.ravel().round(3)}).to_csv(
        DATA / "runs_after_start.csv", index=False)

    # 1) A（温まりあり）だけで：何回測って最初の何回を捨てるか
    steady = M_B * (1 - A_FASTER) * math.exp(sg ** 2 / 2)
    big = runs(rng, REPS, 100, M_B * (1 - A_FASTER), W, tau, sg)
    rows = []
    for n in NS:
        for m in DROPS:
            if m >= n:
                continue
            sim = big[:, m:n].mean(1)
            rows.append({"n_runs": n, "drop_first": m, "used": n - m,
                         "bias_pct": r((sim.mean() / steady - 1) * 100, 2),
                         "formula_bias_pct": r(formula_bias(n, m, W, tau), 2),
                         "share_over_10pct_slow": r((sim / steady > 1.10).mean() * 100, 2)})
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "bias_by_n_drop.csv", index=False)

    # 2) A（温まったあと5%速い・温まりあり）と B（温まりなし）の比べ（10回測る）
    ab = evaluate(np.random.default_rng(SEED * 10), W, tau, sg)
    per_run = {"k": list(range(1, 11)),
               "A_mean_ms": [r(x, 2) for x in big[:, :10].mean(0)],
               "A_formula_ms": [r(steady * f, 2) for f in warm_factor(10, W, tau)]}

    # 3) 確かめ：W × τ × σ の27通り
    grid = []
    gi = 0
    for Wg in [1.0, 3.0, 6.0]:
        for tg in [1.0, 2.0, 5.0]:
            for sgg in [0.05, 0.10, 0.20]:
                gi += 1
                e = evaluate(np.random.default_rng(SEED * 100 + gi), Wg, tg, sgg)
                row = {"W": Wg, "tau": tg, "sigma": sgg}
                row.update({k: r(v, 2) for k, v in e.items()})
                row["crossover_runs"] = crossover(Wg, tg)
                grid.append(row)
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    gap = max(float((g[f"bias_drop{m}_pct"] - g[f"formula_drop{m}_pct"]).abs().max()) for m in DROPS)

    base_row = tab.set_index(["n_runs", "drop_first"])
    out = {
        "settings": {"median_B_ms": M_B, "A_faster_steady": A_FASTER, "W": W, "tau": tau, "sigma": sg,
                     "reps": REPS, "n_compare": 10},
        "headline": {
            "steady_mean_A_ms": r(steady, 2), "first_run_factor": r(1 + W, 2),
            "first_run_A_ms_sim": per_run["A_mean_ms"][0],
            "n10_all_bias_pct": float(base_row.loc[(10, 0), "bias_pct"]),
            "n10_all_formula_pct": float(base_row.loc[(10, 0), "formula_bias_pct"]),
            "n10_drop1_bias_pct": float(base_row.loc[(10, 1), "bias_pct"]),
            "n10_drop3_bias_pct": float(base_row.loc[(10, 3), "bias_pct"]),
            "n10_drop5_bias_pct": float(base_row.loc[(10, 5), "bias_pct"]),
            "n30_all_bias_pct": float(base_row.loc[(30, 0), "bias_pct"]),
            "n100_all_bias_pct": float(base_row.loc[(100, 0), "bias_pct"]),
            "n100_all_formula_pct": float(base_row.loc[(100, 0), "formula_bias_pct"]),
            "pick_A_n10": {f"drop{m}": r(ab[f"pick_A_drop{m}_pct"], 2) for m in DROPS},
            "crossover_runs_base": crossover(W, tau),
        },
        "base_table_max_gap_to_formula_pt": r((tab.bias_pct - tab.formula_bias_pct).abs().max(), 2),
        "per_run_A": per_run,
        "bias_by_n_drop": tab.to_dict("records"),
        "grid_summary": {
            "n": int(len(g)), "max_gap_to_formula_pt": r(gap, 2),
            "all_bias_min_pct": r(g.bias_drop0_pct.min(), 2), "all_bias_max_pct": r(g.bias_drop0_pct.max(), 2),
            "drop3_bias_min_pct": r(g.bias_drop3_pct.min(), 2), "drop3_bias_max_pct": r(g.bias_drop3_pct.max(), 2),
            "drop3_bias_over_5pct_count": int((g.bias_drop3_pct > 5).sum()),
            "drop3_bias_over_5pct_tau": sorted(set(g[g.bias_drop3_pct > 5].tau.tolist())),
            "drop5_bias_max_pct": r(g.bias_drop5_pct.max(), 2),
            "pick_A_drop0_min_pct": r(g.pick_A_drop0_pct.min(), 2), "pick_A_drop0_max_pct": r(g.pick_A_drop0_pct.max(), 2),
            "pick_A_drop3_min_pct": r(g.pick_A_drop3_pct.min(), 2), "pick_A_drop3_max_pct": r(g.pick_A_drop3_pct.max(), 2),
            "pick_A_drop0_below50_count": int((g.pick_A_drop0_pct < 50).sum()),
            "pick_A_drop3_below50_count": int((g.pick_A_drop3_pct < 50).sum()),
            "tau5_drop5_bias_by_W": {str(w): [r(g[(g.tau == 5) & (g.W == w)].bias_drop5_pct.min(), 2),
                                              r(g[(g.tau == 5) & (g.W == w)].bias_drop5_pct.max(), 2)] for w in [1.0, 6.0]},
            "tau1_drop3_bias_range": [r(g[g.tau == 1].bias_drop3_pct.min(), 2), r(g[g.tau == 1].bias_drop3_pct.max(), 2)],
            "tau1_pick_A_drop3_range": [r(g[g.tau == 1].pick_A_drop3_pct.min(), 2), r(g[g.tau == 1].pick_A_drop3_pct.max(), 2)],
            "crossover_min": int(g.crossover_runs.min()), "crossover_max": int(g.crossover_runs.max()),
        },
    }
    json.dump(out, open(RES / "a1054_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：起動から k 回目の処理時間（A・B、2万回の起動の平均）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    k = np.arange(1, 31)
    b_big = runs(np.random.default_rng(SEED * 7), REPS, 30, M_B, 0.0, tau, sg)
    ax.plot(k, big[:, :30].mean(0), "o-", color=ORANGE, ms=4, label="A（温まったあと5%速い・温まりあり）")
    ax.plot(k, b_big.mean(0), "s-", color=BLUE, ms=4, label="B（温まりなし）")
    ax.axhline(steady, color=ORANGE, lw=.8, ls="--")
    ax.set_ylim(0, 450); ax.set_xlabel("起動してから何回目の処理か"); ax.set_ylabel("処理時間の平均（ミリ秒）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"A の1回目は温まったあとの約{1+W:.0f}倍かかる（2万回の起動の平均）", fontsize=12)
    save(fig, "a1054_per_run.png", SRC)

    # 図2：10回測って最初の m 回を捨てたときの、温まったあとの平均からのずれ
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    s10 = tab[tab.n_runs == 10]
    labels = [f"最初の{m}回を捨てる" if m else "10回すべて" for m in s10.drop_first]
    ax.barh(labels[::-1], s10.bias_pct.values[::-1], color=[LIGHT, LIGHT, LIGHT, ORANGE])
    for i, v in enumerate(s10.bias_pct.values[::-1]):
        ax.text(v + 1, i, f"+{v:.1f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100); ax.set_xlabel("温まったあとの平均より何%長く出たか（A、10回測る）")
    ax.set_title("10回すべての平均は、温まったあとの平均より大きく長く出る", fontsize=12)
    save(fig, "a1054_drop.png", SRC)

    # 図3：27通りのうち σ=0.10 の9通り：最初の3回を捨てたあとのずれ と Aを選ぶ割合
    sub = g[g.sigma == 0.10]
    lab = [f"1回目{int(1+w)}倍・τ={t:g}回" for w, t in zip(sub.W, sub.tau)]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.4), sharey=True)
    y = np.arange(len(sub))
    axes[0].barh(y - .2, sub.bias_drop0_pct, .4, color=ORANGE, label="10回すべて")
    axes[0].barh(y + .2, sub.bias_drop3_pct, .4, color=BLUE, label="最初の3回を捨てる")
    axes[0].set_xlim(0, max(260, float(sub.bias_drop0_pct.max()) * 1.05)); axes[0].set_xlabel("温まったあとの平均より何%長いか（10回測る）")
    axes[0].set_yticks(y); axes[0].set_yticklabels(lab, fontsize=8.5); axes[0].invert_yaxis()
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper right")
    axes[1].barh(y - .2, sub.pick_A_drop0_pct, .4, color=ORANGE)
    axes[1].barh(y + .2, sub.pick_A_drop3_pct, .4, color=BLUE)
    axes[1].axvline(50, color=INK, lw=.8, ls="--")
    axes[1].set_xlim(0, 100); axes[1].set_xlabel("温まったあと速い A を選んだ割合（%）")
    fig.suptitle("温まりが遅い（τが大きい）と、3回捨てても長く出て A を選びにくい（ばらつき10%の9通り）", fontsize=11)
    save(fig, "a1054_grid.png", SRC)

    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, indent=1))
    print(tab.to_string())
    print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
