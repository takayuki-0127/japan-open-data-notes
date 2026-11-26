"""1292 部品ごとに20個だけ測った標準偏差から組み立て品の幅を見込むと、本当の幅より狭く見込む回はどれだけあるのか？（架空のデータ）

架空の棚：5枚の部品（天板・仕切り・棚板など）を重ねた高さ。部品ごとの本当の標準偏差は作成者が置く。
部品ごとに n 個を測って標準偏差 s を出し、組み立て品の幅を「±3×√(s の2乗の和)」（二乗で足す）で見込む。
本当の幅は「±3×√(本当の標準偏差の2乗の和)」。真ん中は分かっている（ずれていない）と置き、ばらつきの見込みだけを比べる。
見込んだ幅の外に出る組み立て品の割合は、本当の組み立て品100万個（部品の形どおりに作る）で数える。
確かめ：測る個数 n、部品の形（山が1つ・平ら・まれに大きくずれる）、部品の数（2・5・10）、標準偏差の置き方（そろう・1つが大きい）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1292
SRC = "架空の棚の部品の寸法（作成者が乱数で作成、seed 1292）"
MAIN_SDS = [0.10, 0.08, 0.12, 0.06, 0.09]
NS = [5, 10, 20, 50, 100]
SHAPES = ["normal", "flat", "rare_wide"]
SHAPE_JA = {"normal": "山が1つ", "flat": "平ら", "rare_wide": "まれに大きくずれる"}
KS = [2, 5, 10]
PATTERNS = ["equal", "one_big"]
PATTERN_JA = {"equal": "そろう（どれも0.1mm）", "one_big": "1つが大きい（0.3mm、ほかは0.1mm）"}
REPS_MAIN, REPS_GRID = 20000, 4000
N_TRUE = 1_000_000
RARE_P, RARE_K = 0.05, 3.0


def draw(rng, shape, sd, size):
    """平均0・標準偏差 sd の形ごとの乱数。sd は最後の次元に合わせて並べた配列"""
    if shape == "normal":
        return rng.normal(0, 1, size) * sd
    if shape == "flat":
        return rng.uniform(-np.sqrt(3), np.sqrt(3), size) * sd
    a = 1 / np.sqrt(1 - RARE_P + RARE_P * RARE_K ** 2)
    z = rng.normal(0, 1, size)
    big = rng.random(size) < RARE_P
    return np.where(big, z * RARE_K * a, z * a) * sd


def true_abs_sorted(rng, shape, sds):
    tot = np.zeros(N_TRUE)
    for s in sds:
        tot += draw(rng, shape, s, N_TRUE)
    return np.sort(np.abs(tot))


def out_rate(sorted_abs, h):
    return 1 - np.searchsorted(sorted_abs, h, side="right") / len(sorted_abs)


def run(rng, shape, sds, n, reps, true_sorted):
    sds = np.asarray(sds)
    x = draw(rng, shape, sds[None, None, :], (reps, n, len(sds)))
    s = x.std(axis=1, ddof=1)                        # reps × 部品
    est = 3 * np.sqrt((s ** 2).sum(axis=1))
    true_h = 3 * np.sqrt((sds ** 2).sum())
    ratio = est / true_h
    outs = out_rate(true_sorted, est) * 100
    return dict(narrower_pct=float(np.mean(ratio < 1) * 100), narrower10_pct=float(np.mean(ratio < 0.9) * 100),
                narrower20_pct=float(np.mean(ratio < 0.8) * 100),
                ratio_p10=float(np.quantile(ratio, 0.1)), ratio_p50=float(np.median(ratio)), ratio_p90=float(np.quantile(ratio, 0.9)),
                out_pct_true_width=float(out_rate(true_sorted, np.array([true_h]))[0] * 100),
                out_pct_median=float(np.median(outs)), out_pct_p90=float(np.quantile(outs, 0.9)),
                out_over1_pct=float(np.mean(outs > 1) * 100)), ratio, outs


def rnd(d):
    return {kk: (round(v, 2 if kk.endswith("_pct") else 4) if isinstance(v, float) else v) for kk, v in d.items()}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # ① 基本：5枚・山が1つ・本当の標準偏差 MAIN_SDS、n を変える
    ts = true_abs_sorted(rng, "normal", MAIN_SDS)
    main_rows, keep = [], {}
    for n in NS:
        res, ratio, outs = run(rng, "normal", MAIN_SDS, n, REPS_MAIN, ts)
        main_rows.append(rnd(dict(n=n, **res)))
        keep[n] = (ratio, outs)
    main_tab = pd.DataFrame(main_rows)
    main_tab.to_csv(RES / "main_by_n.csv", index=False)

    # ② 確かめ：形×部品の数×標準偏差の置き方×n（各4,000回）
    grid = []
    for shape in SHAPES:
        for k in KS:
            for pat in PATTERNS:
                sds = [0.1] * k if pat == "equal" else [0.3] + [0.1] * (k - 1)
                tsg = true_abs_sorted(rng, shape, sds)
                for n in NS:
                    res, _, _ = run(rng, shape, sds, n, REPS_GRID, tsg)
                    grid.append(rnd(dict(part_shape=SHAPE_JA[shape], k_parts=k, sd_pattern=PATTERN_JA[pat], n=n, **res)))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g20 = grid[grid.n == 20]
    g20sum = g20.groupby("part_shape").agg(narrower_min=("narrower_pct", "min"), narrower_max=("narrower_pct", "max"),
                                      narrower10_min=("narrower10_pct", "min"), narrower10_max=("narrower10_pct", "max"),
                                      out_p90_min=("out_pct_p90", "min"), out_p90_max=("out_pct_p90", "max")).reset_index()
    g20sum.to_csv(RES / "grid_n20_summary.csv", index=False)

    # data：基本の1回分の測った値（5枚×20個）
    rng_d = np.random.default_rng(SEED + 1)
    x = draw(rng_d, "normal", np.array(MAIN_SDS)[None, :], (20, 5))
    pd.DataFrame([dict(part=f"部品{j+1}", sample=i + 1, true_sd_mm=MAIN_SDS[j], deviation_mm=round(float(x[i, j]), 4))
                  for j in range(5) for i in range(20)]).to_csv(DATA / "measure_one_round.csv", index=False)

    m20 = main_tab[main_tab.n == 20].iloc[0].to_dict()
    main_json = dict(
        setting=dict(main_true_sds_mm=MAIN_SDS, true_halfwidth_mm=round(3 * float(np.sqrt(np.sum(np.square(MAIN_SDS)))), 4),
                     reps_main=REPS_MAIN, reps_grid=REPS_GRID, n_true_assemblies=N_TRUE, rare_share=RARE_P, rare_sd_times=RARE_K),
        main_n20=m20, main_by_n=main_tab.to_dict(orient="records"),
        grid_n20_summary=g20sum.to_dict(orient="records"),
        grid_n20_all_range=dict(n_cases=int(len(g20)), narrower_min=float(g20.narrower_pct.min()), narrower_max=float(g20.narrower_pct.max()),
                                narrower10_min=float(g20.narrower10_pct.min()), narrower10_max=float(g20.narrower10_pct.max())),
        grid_n20_normal_5parts={PATTERN_JA[p]: grid[(grid.n == 20) & (grid.part_shape == "山が1つ") & (grid.k_parts == 5) &
                                                   (grid.sd_pattern == PATTERN_JA[p])].iloc[0].to_dict() for p in PATTERNS},
    )
    with open(RES / "a1292_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1, default=float)

    # 図1：n=20 の見込みの幅÷本当の幅
    ratio, outs = keep[20]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.hist(ratio, bins=np.linspace(0.6, 1.4, 81), color=BLUE, alpha=0.8)
    ax.axvline(1.0, color=INK, lw=1.2)
    ax.axvline(0.9, color=ORANGE, lw=1.2, ls="--")
    ax.text(1.12, ax.get_ylim()[1] * 0.92, "← 本当の幅（1.0）", fontsize=9)
    ax.text(0.89, ax.get_ylim()[1] * 0.92, f"1割以上狭い：{m20['narrower10_pct']:.2f}%", fontsize=9, ha="right", color=ORANGE)
    ax.set_xlabel("見込んだ幅÷本当の幅"); ax.set_ylabel("回数（20,000回のうち）")
    ax.set_title(f"部品ごとに20個測って見込んだ幅：本当より狭いのは{m20['narrower_pct']:.2f}%の回")
    save(fig, "a1292_ratio_hist.png", SRC)

    # 図2：n ごとの狭く見込む回の割合
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    w = 0.38
    xs = np.arange(len(NS))
    ax.bar(xs - w / 2, main_tab.narrower_pct, width=w, color=LIGHT, label="本当の幅より狭い")
    ax.bar(xs + w / 2, main_tab.narrower10_pct, width=w, color=ORANGE, label="1割以上狭い")
    for xx, a_, b_ in zip(xs, main_tab.narrower_pct, main_tab.narrower10_pct):
        ax.text(xx - w / 2, a_ + 1, f"{a_:.2f}", ha="center", fontsize=8.5)
        ax.text(xx + w / 2, b_ + 1, f"{b_:.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"{n}個" for n in NS])
    ax.set_xlabel("部品ごとに測る個数"); ax.set_ylabel("回の割合（%）"); ax.set_ylim(0, 75)
    ax.set_title("測る個数ごとの、幅を狭く見込む回（5枚・山が1つ）")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "a1292_by_n.png", SRC)

    # 図3：確かめ。n=20・5枚で、形と標準偏差の置き方ごとの「1割以上狭い」回
    fig, ax = plt.subplots(figsize=(8.0, 4.3))
    sub = grid[(grid.n == 20) & (grid.k_parts == 5)]
    for j, pat in enumerate(PATTERNS):
        vals = [sub[(sub.part_shape == SHAPE_JA[s]) & (sub.sd_pattern == PATTERN_JA[pat])].narrower10_pct.iloc[0] for s in SHAPES]
        xx = np.arange(len(SHAPES)) + (j - 0.5) * w
        ax.bar(xx, vals, width=w, color=[BLUE, ORANGE][j], label=f"標準偏差：{PATTERN_JA[pat]}")
        for a_, v in zip(xx, vals):
            ax.text(a_, v + 0.8, f"{v:.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(np.arange(len(SHAPES))); ax.set_xticklabels([SHAPE_JA[s] for s in SHAPES])
    ax.set_xlabel("部品の寸法の形"); ax.set_ylabel("1割以上狭く見込む回（%）")
    ax.set_ylim(0, max(sub.narrower10_pct) * 1.35)
    ax.set_title("20個ずつ・5枚：形と標準偏差の置き方で変わる（各4,000回）")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    save(fig, "a1292_robust.png", SRC)

    print(main_tab.to_string()); print(g20.to_string()); print(g20sum.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
