"""1306 データの件数を変えずに、振り分ける台数を10台から100台に増やすと、いちばん多い1台と平均の比はどう広がるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ。1件ずつ、番号をでたらめな数に変えて k 台のどれに置くかを決める
（どの台も同じ確率 1/k、1件ごとに独立）。いちばん多い1台の件数 ÷ 平均（件数÷台数）を数える。
基本：1万件、台数 10・20・50・100・200・500・1,000台、各2,000回。
分けて見る：1台あたりの件数を1,000件・100件にそろえたまま台数を増やす（件数を台数に合わせて増やす）。
確かめ：件数 1万・10万・100万件 × 台数7通り＝21通り（各2,000回）。
目安の式：平均 + （k 個の正規の乱数のいちばん大きい値の平均）×√(件数×1/k×(1−1/k))。
実機では測らず、すべてシミュレーション。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1306
SRC = "架空のアプリのデータの振り分け（作成者が置いた件数・台数からの乱数、seed 1306）"
REPS = 2000
K_LIST = [10, 20, 50, 100, 200, 500, 1000]
N_LIST = [10_000, 100_000, 1_000_000]
_X = np.linspace(-10, 10, 40001)
_PHI = np.exp(-_X * _X / 2) / math.sqrt(2 * math.pi)
_CDF = 0.5 * (1 + np.array([math.erf(v / math.sqrt(2)) for v in _X]))


def emax_normal(k):
    return float(np.sum(_X * k * _PHI * _CDF ** (k - 1)) * (_X[1] - _X[0]))


def run(n, k, tag):
    g = np.random.default_rng([SEED, n, k, tag])
    c = g.multinomial(n, np.full(k, 1 / k), size=REPS)
    mean = n / k
    r = c.max(1) / mean
    lo = c.min(1) / mean
    return {"n": n, "k": k, "per_server": mean,
            "max_ratio_mean": round(float(r.mean()), 4),
            "max_ratio_p10": round(float(np.quantile(r, .1)), 4),
            "max_ratio_p90": round(float(np.quantile(r, .9)), 4),
            "min_ratio_mean": round(float(lo.mean()), 4),
            "sd_ratio_one_server": round(math.sqrt(mean * (1 - 1 / k)) / mean, 4),
            "emax_normal_k": round(emax_normal(k), 4),
            "formula_ratio": round(1 + emax_normal(k) * math.sqrt(mean * (1 - 1 / k)) / mean, 4)}, c


def main():
    t0 = time.time()
    grid, keep = [], {}
    for n in N_LIST:
        for k in K_LIST:
            s, c = run(n, k, 0)
            grid.append(s)
            if n == 10_000 and k in (10, 100):
                keep[k] = c
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    base = grid[grid.n == 10_000].reset_index(drop=True)
    base.to_csv(RES / "base_10000.csv", index=False)

    # 1台あたりの件数をそろえたまま台数を増やす
    fixed = []
    for per in (1000, 100):
        for k in K_LIST:
            s, _ = run(per * k, k, 1)
            s["fixed_per_server"] = per
            fixed.append(s)
    fixed = pd.DataFrame(fixed)
    fixed.to_csv(RES / "fixed_per_server.csv", index=False)

    # 1回目の100台の件数（data）
    one = pd.DataFrame({"server": np.arange(1, 101), "records": keep[100][0]})
    one.to_csv(DATA / "trial1_100servers.csv", index=False)
    pd.DataFrame({"server": np.arange(1, 11), "records": keep[10][0]}).to_csv(DATA / "trial1_10servers.csv", index=False)

    b10 = base[base.k == 10].iloc[0]; b100 = base[base.k == 100].iloc[0]
    f = fixed.set_index(["fixed_per_server", "k"])
    out = {"base_10000": base.to_dict("records"), "fixed_per_server": fixed.to_dict("records"),
           "grid": grid.to_dict("records"),
           "summary": {
               "k10_ratio": b10.max_ratio_mean, "k100_ratio": b100.max_ratio_mean,
               "excess_k10_pct": round((b10.max_ratio_mean - 1) * 100, 2),
               "excess_k100_pct": round((b100.max_ratio_mean - 1) * 100, 2),
               "excess_mult_10_to_100": round((b100.max_ratio_mean - 1) / (b10.max_ratio_mean - 1), 3),
               "sd_mult_10_to_100": round(b100.sd_ratio_one_server / b10.sd_ratio_one_server, 3),
               "emax_mult_10_to_100": round(b100.emax_normal_k / b10.emax_normal_k, 3),
               "fixed1000_k10": f.loc[(1000, 10), "max_ratio_mean"], "fixed1000_k100": f.loc[(1000, 100), "max_ratio_mean"],
               "fixed1000_k1000": f.loc[(1000, 1000), "max_ratio_mean"],
               "k10_one_trial_max": int(keep[10][0].max()), "k10_one_trial_min": int(keep[10][0].min()),
               "k100_one_trial_max": int(keep[100][0].max()), "k100_one_trial_min": int(keep[100][0].min()),
               "grid_k10_range": [float(grid[grid.k == 10].max_ratio_mean.min()), float(grid[grid.k == 10].max_ratio_mean.max())],
               "grid_k100_range": [float(grid[grid.k == 100].max_ratio_mean.min()), float(grid[grid.k == 100].max_ratio_mean.max())],
               "grid_excess_mult_10_to_100": {str(n): round((grid[(grid.n == n) & (grid.k == 100)].max_ratio_mean.iloc[0] - 1)
                                                            / (grid[(grid.n == n) & (grid.k == 10)].max_ratio_mean.iloc[0] - 1), 3)
                                              for n in N_LIST},
               "all_sim_ge_formula": bool((grid.max_ratio_mean >= grid.formula_ratio).all()),
               "max_gap_at": {"n": int(grid.loc[(grid.max_ratio_mean - grid.formula_ratio).abs().idxmax(), "n"]),
                              "k": int(grid.loc[(grid.max_ratio_mean - grid.formula_ratio).abs().idxmax(), "k"])},
               "max_abs_gap_formula": round(float((grid.max_ratio_mean - grid.formula_ratio).abs().max()), 4)}}
    json.dump(out, open(RES / "a1306_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)

    # 図1：10台と100台の1回目
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), gridspec_kw={"width_ratios": [1, 2.2]})
    for ax, k in zip(axes, (10, 100)):
        c = keep[k][0]; mean = 10_000 / k
        r = c / mean
        ax.bar(np.arange(1, k + 1), r, color=[ORANGE if v == c.max() else BLUE for v in c], width=0.8)
        ax.axhline(1, color=INK, lw=1, ls="--")
        ax.set_ylim(0, 1.45); ax.set_xlabel("台の番号")
        ax.set_title(f"{k}台：いちばん多い台は{c.max():,}件（平均{mean:,.0f}件）", fontsize=11)
    axes[0].set_ylabel("件数 ÷ 平均（破線＝1）")
    fig.suptitle("同じ1万件でも、100台に分けると台ごとの件数の差が広がる（1回目）", fontsize=13, y=1.02)
    save(fig, "a1306_one_trial.png", SRC)

    # 図2：台数といちばん多い1台÷平均（1万件）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.fill_between(base.k, base.max_ratio_p10, base.max_ratio_p90, color=LIGHT, alpha=.7, label="10〜90%")
    ax.plot(base.k, base.max_ratio_mean, "o-", color=BLUE, label="数えた平均")
    ax.plot(base.k, base.formula_ratio, "s--", color=ORANGE, ms=4, lw=1, label="目安の式")
    for k, v in zip(base.k, base.max_ratio_mean):
        ax.text(k, v + 0.04, f"{v:.4f}", ha="center", fontsize=8.5)
    ax.set_xscale("log"); ax.set_xticks(K_LIST); ax.set_xticklabels([f"{k:,}" for k in K_LIST])
    ax.set_ylim(0.9, 2.6); ax.set_xlabel("台数（1万件のまま、対数の目盛り）"); ax.set_ylabel("いちばん多い1台 ÷ 平均")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("件数を変えずに台数を増やすと、いちばん多い1台は平均から離れる")
    save(fig, "a1306_by_servers.png", SRC)

    # 図3：1台あたりの件数をそろえたとき
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for per, col in ((100, ORANGE), (1000, GREEN)):
        d = fixed[fixed.fixed_per_server == per]
        ax.plot(d.k, d.max_ratio_mean, "o-", color=col, label=f"1台あたり{per:,}件にそろえる（件数を台数に合わせて増やす）")
    ax.plot(base.k, base.max_ratio_mean, "o--", color=BLUE, label="1万件のまま（1台あたりの件数が減る）")
    ax.set_xscale("log"); ax.set_xticks(K_LIST); ax.set_xticklabels([f"{k:,}" for k in K_LIST])
    ax.set_ylim(0.9, 2.6); ax.set_xlabel("台数（対数の目盛り）"); ax.set_ylabel("いちばん多い1台 ÷ 平均")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("広がりの多くは、1台あたりの件数が減る分から来る")
    save(fig, "a1306_fixed_per_server.png", SRC)
    print(json.dumps(out["summary"], ensure_ascii=False, indent=1, default=float))
    print(base.to_string()); print(fixed[["fixed_per_server", "k", "max_ratio_mean"]].to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
