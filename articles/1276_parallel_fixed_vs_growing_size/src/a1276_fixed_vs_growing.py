"""1276 量を変えずに数を増やす試し方と、数に合わせて量も増やす試し方では、速さの伸び方はどう違って見えるのか？（並列処理）

作成者が置いた架空のアプリの処理をシミュレーションする。実機の計測はしていない。
試し方①：仕事の量（4,096個）を変えずに、同時に動かす数を1〜64に増やす。
試し方②：1つあたり64個になるよう、数に合わせて量も増やす（同時に64で4,096個）。
"""
import json
import heapq
import itertools
from functools import lru_cache
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1276
SRC = "架空のアプリの処理（作成者が乱数で作成、seed 1276）。実機の計測ではなくシミュレーション"
PS = [1, 2, 4, 8, 16, 32, 64]
PMAX = 64
W = 64                 # 試し方②の1つあたりの仕事の数
MEAN_T = 0.010         # 1つの仕事の平均（秒）
SIGMA_T = 0.5
S0 = 0.5               # 量によらない分けられない部分（動かし始め、秒）
M = 0.002              # 同時に動かした1つごとの結果を、最後に1つずつまとめる手間（秒）
D_GROW = 0.0005        # 量に比例する分けられない部分（仕事1個あたり、秒）。置き方Bだけ
RUN_SD = 0.02
N_RUN = 10

rng = np.random.default_rng(SEED)
POOL = rng.lognormal(np.log(MEAN_T) - SIGMA_T ** 2 / 2, SIGMA_T, 256 * PMAX)


@lru_cache(maxsize=None)
def makespan(n, p):
    t = POOL[:n]
    if p == 1:
        return float(t.sum())
    free = [0.0] * p
    for x in t:
        f = heapq.heappop(free)
        heapq.heappush(free, f + x)
    return max(free)


def time_of(n, p, s0, d, m):
    """振れのない時間：量によらない部分＋量に比例する部分＋まとめる手間＋分けた仕事"""
    return s0 + d * n + m * p + makespan(n, p)


def table(s0, d, m, w, noise_rng=None):
    n_fixed = w * PMAX
    rows = []
    for p in PS:
        ts = time_of(n_fixed, p, s0, d, m)
        tw = time_of(w * p, p, s0, d, m)
        if noise_rng is not None:
            ts = float(np.median(ts * np.exp(noise_rng.normal(0, RUN_SD, N_RUN))))
            tw = float(np.median(tw * np.exp(noise_rng.normal(0, RUN_SD, N_RUN))))
        rows.append({"p": p, "fixed_time": ts, "grow_time": tw})
    df = pd.DataFrame(rows)
    t1s, t1w = df.fixed_time.iloc[0], df.grow_time.iloc[0]
    df["fixed_speedup"] = t1s / df.fixed_time
    df["grow_scaled_speedup"] = df.p * t1w / df.grow_time   # 1つのときの何倍の速さで仕事を片づけたか
    df["grow_time_ratio"] = df.grow_time / t1w               # 1つのときの何倍の時間がかかったか
    return df


def main():
    pd.DataFrame({"task_id": np.arange(1, W * PMAX + 1), "time_ms": np.round(POOL[:W * PMAX] * 1000, 4)}).to_csv(
        DATA / "tasks_4096.csv", index=False)
    nr = np.random.default_rng(SEED + 1)
    cases = {"A": (S0, 0.0, M), "B": (S0, D_GROW, M)}
    out = []
    for key, (s0, d, m) in cases.items():
        df = table(s0, d, m, W, nr)
        df.insert(0, "case", key)
        out.append(df)
    base = pd.concat(out).round(4)
    base.to_csv(RES / "base_two_cases.csv", index=False)

    grid = []
    for s0, d, m, w in itertools.product([0.1, 0.5, 2.0], [0.0, 0.00025, 0.001], [0.0, 0.002, 0.01], [16, 64, 256]):
        df = table(s0, d, m, w)
        last = df.iloc[-1]
        k = df.fixed_speedup.idxmax()
        grid.append({"start_sec": s0, "grow_part_ms_per_task": d * 1000, "merge_ms_per_worker": m * 1000,
                     "tasks_per_worker": w,
                     "fixed_speedup_p64": round(last.fixed_speedup, 4),
                     "grow_scaled_speedup_p64": round(last.grow_scaled_speedup, 4),
                     "grow_over_fixed_p64": round(last.grow_scaled_speedup / last.fixed_speedup, 4),
                     "grow_time_ratio_p64": round(last.grow_time_ratio, 4),
                     "formula_64xT1grow_over_T1fixed": round(PMAX * df.grow_time.iloc[0] / df.fixed_time.iloc[0], 4),
                     "fixed_best_p": int(df.p[k]), "fixed_best_speedup": round(df.fixed_speedup[k], 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    by = grid.groupby(["start_sec", "tasks_per_worker"]).grow_over_fixed_p64.agg(["min", "max"]).reset_index()
    by.columns = ["start_sec", "tasks_per_worker", "grow_over_fixed_min", "grow_over_fixed_max"]
    by.round(4).to_csv(RES / "grid_ratio_by_start_size.csv", index=False)

    def pick(case, p):
        r = base[(base.case == case) & (base.p == p)].iloc[0]
        return {c: float(r[c]) for c in ["fixed_time", "grow_time", "fixed_speedup", "grow_scaled_speedup", "grow_time_ratio"]}

    g0 = grid[grid.grow_part_ms_per_task == 0]
    gd = grid[grid.grow_part_ms_per_task > 0]
    main_json = {
        "settings": {"p_list": PS, "tasks_fixed": W * PMAX, "tasks_per_worker_grow": W, "mean_task_ms": MEAN_T * 1000,
                     "sigma_log": SIGMA_T, "start_sec": S0, "merge_ms_per_worker": M * 1000,
                     "grow_part_ms_per_task_caseB": D_GROW * 1000, "run_sd_log": RUN_SD, "n_run": N_RUN},
        "task_total_4096_sec": round(float(POOL[:W * PMAX].sum()), 4),
        "A_p64": pick("A", 64), "B_p64": pick("B", 64), "A_p8": pick("A", 8), "B_p8": pick("B", 8),
        "A_p1": pick("A", 1), "B_p1": pick("B", 1),
        "A_implied_one_worker_4096_sec": round(PMAX * pick("A", 1)["grow_time"], 4),
        "B_implied_one_worker_4096_sec": round(PMAX * pick("B", 1)["grow_time"], 4),
        "grid": {"n": len(grid),
                 "n_grow_over_fixed": int((grid.grow_over_fixed_p64 > 1).sum()),
                 "grow_over_fixed_range": [grid.grow_over_fixed_p64.min(), grid.grow_over_fixed_p64.max()],
                 "fixed_speedup_range": [grid.fixed_speedup_p64.min(), grid.fixed_speedup_p64.max()],
                 "grow_scaled_range": [grid.grow_scaled_speedup_p64.min(), grid.grow_scaled_speedup_p64.max()],
                 "no_grow_part_n": len(g0),
                 "no_grow_part_grow_scaled_range": [g0.grow_scaled_speedup_p64.min(), g0.grow_scaled_speedup_p64.max()],
                 "no_grow_part_fixed_range": [g0.fixed_speedup_p64.min(), g0.fixed_speedup_p64.max()],
                 "with_grow_part_grow_scaled_range": [gd.grow_scaled_speedup_p64.min(), gd.grow_scaled_speedup_p64.max()],
                 "with_grow_part_fixed_range": [gd.fixed_speedup_p64.min(), gd.fixed_speedup_p64.max()],
                 "max_gap_ratio_vs_formula": round(float((grid.grow_over_fixed_p64 - grid.formula_64xT1grow_over_T1fixed).abs().max()), 4),
                 "n_fixed_peak_before_64": int((grid.fixed_best_p < 64).sum()),
                 "fixed_peak_p_values": sorted(grid.fixed_best_p.unique().tolist())},
    }
    main_json = json.loads(json.dumps(main_json, default=float))
    with open(RES / "a1276_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：2つの置き方 × 2つの試し方
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
    ttl = {"A": "A：分けられない部分が量によらない", "B": "B：分けられない部分が量に比例して増える"}
    for ax, case in zip(axs, ["A", "B"]):
        d = base[base.case == case]
        ax.plot(d.p, d.grow_scaled_speedup, "o-", color=ORANGE, label="② 数に合わせて量も増やす")
        ax.plot(d.p, d.fixed_speedup, "o-", color=BLUE, label="① 量を変えずに数を増やす")
        ax.plot(PS, PS, ":", color=GRAY, label="数どおり")
        for col, c in [("grow_scaled_speedup", ORANGE), ("fixed_speedup", BLUE)]:
            v = d[col].iloc[-1]
            ax.text(64 * 1.08, v, f"{round(v, 4)}倍", color=c, fontsize=9, va="center")
        ax.set_xscale("log", base=2)
        ax.set_xticks(PS)
        ax.set_xticklabels([str(p) for p in PS])
        ax.set_xlim(0.8, 130)
        ax.set_ylim(0, 66)
        ax.set_title(ttl[case], fontsize=11)
        ax.set_xlabel("同時に動かす数")
    axs[0].set_ylabel("1つのときの何倍の速さか")
    axs[0].legend(fontsize=9, frameon=False, loc="upper left")
    save(fig, "a1276_two_ways.png", SRC + "。①は仕事4,096個、②は1つあたり64個。B は仕事1個あたり0.5ms が分けられない")

    # 図2：時間そのもの
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, case in zip(axs, ["A", "B"]):
        d = base[base.case == case]
        ax.plot(d.p, d.fixed_time, "o-", color=BLUE, label="① 量を変えない（4,096個）")
        ax.plot(d.p, d.grow_time, "o-", color=ORANGE, label="② 量も増やす（64個×数）")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_yticks([1, 2, 5, 10, 20, 50])
        ax.set_yticklabels(["1", "2", "5", "10", "20", "50"])
        ax.minorticks_off()
        ax.set_xticks(PS)
        ax.set_xticklabels([str(p) for p in PS])
        ax.set_title(ttl[case] + "（縦は対数の目盛り）", fontsize=10)
        ax.set_xlabel("同時に動かす数")
    axs[0].set_ylabel("全体が終わるまでの時間（秒）")
    axs[0].legend(fontsize=9, frameon=False)
    save(fig, "a1276_time.png", SRC)

    # 図3：81通り、同時に64での2つの試し方
    fig, ax = plt.subplots(figsize=(6.4, 5))
    for dv, c, lab in [(0.0, GREEN, "量に比例する部分なし"), (0.25, BLUE, "仕事1個あたり0.25ms"), (1.0, ORANGE, "仕事1個あたり1ms")]:
        g = grid[grid.grow_part_ms_per_task == dv]
        ax.scatter(g.fixed_speedup_p64, g.grow_scaled_speedup_p64, s=18, color=c, alpha=0.8, label=lab)
    ax.plot([0, 64], [0, 64], color=GRAY, lw=1, ls="--")
    ax.text(40, 36, "2つが同じ線", color=GRAY, fontsize=9, rotation=38)
    ax.set_xlim(0, 66)
    ax.set_ylim(0, 66)
    ax.set_xlabel("① 量を変えない試し方の「何倍」（同時に64）")
    ax.set_ylabel("② 量も増やす試し方の「何倍」（同時に64）")
    ax.set_title(f"置き方を変えた{len(grid)}通り（回ごとの振れなし）", fontsize=12)
    ax.legend(fontsize=9, frameon=False, title="分けられない部分のうち量に比例する分", title_fontsize=9)
    save(fig, "a1276_grid.png", SRC + "。始めの手間・量に比例する部分・まとめる手間・1つあたりの量を変えた")


if __name__ == "__main__":
    main()
