"""1305 1万件のデータを乱数で10台に振り分けると、いちばん多い1台の件数は平均の何倍になるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ。1件ずつ、番号をでたらめな数に変えて10台のどれに置くかを決める
（どの台も同じ確率 1/10、1件ごとに独立）。いちばん多い1台の件数 ÷ 平均（件数÷台数）を数える。
基本：1万件・10台・2,000回。確かめ：件数（1,000・1万・10万・100万件）×台数（10台）を各2,000回。
目安の式：平均 + （10個の正規の乱数のいちばん大きい値の平均）×√(件数×1/10×9/10)。
実機では測らず、すべてシミュレーション。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1305
SRC = "架空のアプリのデータの振り分け（作成者が置いた件数・台数からの乱数、seed 1305）"
N, K, REPS = 10_000, 10, 2000
N_LIST = [1_000, 10_000, 100_000, 1_000_000]


def emax_normal(k):
    """k 個の標準の正規の乱数のいちばん大きい値の平均（数値積分）"""
    x = np.linspace(-10, 10, 40001)
    phi = np.exp(-x * x / 2) / math.sqrt(2 * math.pi)
    Phi = 0.5 * (1 + np.array([math.erf(v / math.sqrt(2)) for v in x]))
    f = x * k * phi * Phi ** (k - 1)
    return float(np.sum(f) * (x[1] - x[0]))


def summarize(counts, n, k):
    mean = n / k
    r = counts.max(1) / mean
    lo = counts.min(1) / mean
    return {"n": n, "k": k, "mean_per_server": mean,
            "max_ratio_mean": round(float(r.mean()), 4),
            "max_ratio_p10": round(float(np.quantile(r, .1)), 4),
            "max_ratio_p90": round(float(np.quantile(r, .9)), 4),
            "max_ratio_p99": round(float(np.quantile(r, .99)), 4),
            "min_ratio_mean": round(float(lo.mean()), 4),
            "share_max_over_1_05": round(float((r > 1.05).mean() * 100), 2),
            "share_max_over_1_10": round(float((r > 1.10).mean() * 100), 2),
            "formula_ratio": round(1 + emax_normal(k) * math.sqrt(n / k * (1 - 1 / k)) / mean, 4)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 基本：1件ずつ置き場所を決める（2,000回）
    place = rng.integers(0, K, size=(REPS, N), dtype=np.int8)
    counts = np.stack([np.bincount(p, minlength=K) for p in place])
    base = summarize(counts, N, K)
    base["emax_normal_10"] = round(emax_normal(K), 4)
    base["second_ratio_mean"] = round(float(np.sort(counts, 1)[:, -2].mean() / (N / K)), 4)
    one = pd.DataFrame({"server": np.arange(1, K + 1), "records": counts[0]})
    one.to_csv(RES / "one_trial_counts.csv", index=False)
    pd.DataFrame({"record_id": np.arange(1, N + 1), "server": place[0].astype(int) + 1}).to_csv(
        DATA / "trial1_records.csv", index=False)
    base["one_trial_max"] = int(counts[0].max()); base["one_trial_min"] = int(counts[0].min())
    ratios = counts.max(1) / (N / K)
    pd.DataFrame({"trial": np.arange(1, REPS + 1), "max_records": counts.max(1), "min_records": counts.min(1),
                  "max_ratio": ratios.round(4)}).to_csv(RES / "base_trials.csv", index=False)

    # 確かめ：件数を変える（10台、各2,000回）
    rows = []
    for i, n in enumerate(N_LIST):
        if n == N:
            s = summarize(counts, n, K)
        else:
            g = np.random.default_rng(SEED * 100 + i)
            c = g.multinomial(n, np.full(K, 1 / K), size=REPS)
            s = summarize(c, n, K)
        rows.append(s)
    grid = pd.DataFrame(rows)
    grid["excess_pct"] = ((grid.max_ratio_mean - 1) * 100).round(2)
    grid["gap_to_formula"] = (grid.max_ratio_mean - grid.formula_ratio).round(4)
    grid.to_csv(RES / "by_records.csv", index=False)

    out = {"base": base, "by_records": grid.to_dict("records")}
    json.dump(out, open(RES / "a1305_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回目の10台の件数
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    col = [ORANGE if v == counts[0].max() else BLUE for v in counts[0]]
    ax.bar(one.server.astype(str), one.records, color=col)
    for i, v in enumerate(one.records):
        ax.text(i, max(v, 1000) + 15, f"{v:,}", ha="center", fontsize=8.5)
    ax.axhline(N / K, color=INK, lw=1, ls="--"); ax.text(-0.4, 1130, "破線：平均1,000件", fontsize=9)
    ax.set_ylim(0, 1200); ax.set_xlabel("台の番号"); ax.set_ylabel("置かれた件数")
    ax.set_title(f"1回目：いちばん多い台は{counts[0].max():,}件、少ない台は{counts[0].min():,}件（1万件・10台）")
    save(fig, "a1305_one_trial.png", SRC)

    # 図2：2,000回のいちばん多い1台÷平均
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.hist(ratios, bins=np.arange(0.9995, 1.13, 0.003), color=BLUE, alpha=.8)
    ax.axvline(base["max_ratio_mean"], color=ORANGE, lw=1.5)
    ax.text(base["max_ratio_mean"] + 0.002, ax.get_ylim()[1] * 0.9, f"平均 {base['max_ratio_mean']:.4f}倍",
            color=ORANGE, fontsize=9)
    ax.set_xlabel("いちばん多い1台の件数 ÷ 平均（1,000件）"); ax.set_ylabel("回数")
    ax.set_title("1万件・10台を2,000回振り分けたときの、いちばん多い1台の倍率")
    save(fig, "a1305_max_ratio_hist.png", SRC)

    # 図3：件数を変えると
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = grid.n.values
    ax.fill_between(x, grid.max_ratio_p10, grid.max_ratio_p90, color=LIGHT, alpha=.7, label="10〜90%")
    ax.plot(x, grid.max_ratio_mean, "o-", color=BLUE, label="数えた平均")
    ax.plot(x, grid.formula_ratio, "s--", color=ORANGE, ms=4, lw=1, label="目安の式")
    for xi, v in zip(x, grid.max_ratio_mean):
        ax.text(xi, v + 0.012, f"{v:.4f}", ha="center", fontsize=8.5)
    ax.set_xscale("log"); ax.set_xticks(x); ax.set_xticklabels(["1,000件", "1万件", "10万件", "100万件"])
    ax.set_ylim(0.98, 1.25); ax.set_ylabel("いちばん多い1台 ÷ 平均"); ax.set_xlabel("データの件数（10台、対数の目盛り）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("件数が多いほど、いちばん多い1台は平均に近づく（10台）")
    save(fig, "a1305_by_records.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
