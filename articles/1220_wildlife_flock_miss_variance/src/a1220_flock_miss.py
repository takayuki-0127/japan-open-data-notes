"""1220 群れで動く生き物を数えるとき、群れを見落とすと全体の数のぶれはどれだけ大きくなるのか？（架空のデータ）

架空の湖「C湖」に、本当は1,000羽の水鳥がいる。鳥は群れに分かれていて、群れの大きさは作成者が置いた分布から引く。
数える人は群れごとに見つけるか見落とすかが決まり、見つけた群れは全部数える。
1羽ずつ同じ割合で見つかる場合と、群れごとに見落とす場合で、数の見込みのぶれを比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1220
SRC = "架空の湖と水鳥の群れ（作成者が乱数で作成、seed 1220）"
N_TRUE = 1000


def make_flocks(rng, reps, n=N_TRUE, mu=20.0, shape=1.0):
    """群れの大きさ（reps×群れ、ない所は0）。大きさ = 1 + でたらめな件数（平均 mu−1、散らばりは shape で決まる）。
    合計が n になるまで群れを並べ、最後の群れを切って合わせる。"""
    K = int(4 * n / mu) + 100
    while True:
        lam = rng.gamma(shape, (mu - 1) / shape, (reps, K))
        s = 1 + rng.poisson(lam)
        cs = s.cumsum(1)
        if (cs[:, -1] >= n).all():
            break
        K *= 2
    start = cs - s
    sizes = np.where(start < n, np.minimum(s, n - start), 0)
    return sizes


def count_flocks(rng, sizes, p_fn):
    p = p_fn(sizes)
    det = (rng.random(sizes.shape) < p) & (sizes > 0)
    return (sizes * det).sum(1), det


def within(est, n, tol):
    return float((np.abs(est / n - 1) <= tol).mean())


def surveys_needed(rng, est, n, tol=0.10, target=0.9, kmax=60):
    """k 回の見込みの平均が ±tol に入る割合が target 以上になる最小の k（独立な回を組みにして数える）"""
    for k in range(1, kmax + 1):
        m = len(est) // k
        idx = rng.permutation(len(est))[:m * k].reshape(m, k)
        if within(est[idx].mean(1), n, tol) >= target:
            return k
    return None


def r(x, k=4):
    return round(float(x), k)


def main():
    rng = np.random.default_rng(SEED)
    REPS = 20000
    P = 0.8

    # 1) 基本：群れの大きさの平均20羽、散らばり（shape=1）、群れを見つける割合0.8
    sizes = make_flocks(rng, REPS)
    cnt_f, det = count_flocks(rng, sizes, lambda s: P)
    est_f = cnt_f / P
    cnt_i = rng.binomial(N_TRUE, P, REPS)
    est_i = cnt_i / P
    sum_s2 = (sizes.astype(float) ** 2).sum(1)
    n_flocks = (sizes > 0).sum(1)
    ratio_formula = float(np.sqrt(sum_s2.mean() / N_TRUE))   # 式：群れごと÷1羽ずつ の標準偏差の比 ≈ √(Σ大きさ²÷全体)
    sd_f, sd_i = float(est_f.std()), float(est_i.std())
    base = {"n_flocks_mean": r(n_flocks.mean(), 2), "flock_size_mean": r(N_TRUE / n_flocks.mean(), 3),
            "flock_size_weighted_by_bird": r(sum_s2.mean() / N_TRUE, 3),
            "individual": {"sd": r(sd_i, 2), "p10": r(np.quantile(est_i, .1), 2), "p90": r(np.quantile(est_i, .9), 2),
                           "within10": r(within(est_i, N_TRUE, .1)), "within5": r(within(est_i, N_TRUE, .05)),
                           "mean": r(est_i.mean(), 2)},
            "flock": {"sd": r(sd_f, 2), "p10": r(np.quantile(est_f, .1), 2), "p90": r(np.quantile(est_f, .9), 2),
                      "within10": r(within(est_f, N_TRUE, .1)), "within5": r(within(est_f, N_TRUE, .05)),
                      "mean": r(est_f.mean(), 2), "min": r(est_f.min(), 2), "max": r(est_f.max(), 2)},
            "sd_ratio_sim": r(sd_f / sd_i), "sd_ratio_formula": r(ratio_formula),
            "individual_sd_formula": r(np.sqrt(N_TRUE * P * (1 - P)) / P, 2),
            "bird_weighted_over_mean_size": r((sum_s2.mean() / N_TRUE) / (N_TRUE / n_flocks.mean()), 3),
            "surveys_needed_90pct_within10": {"individual": surveys_needed(np.random.default_rng(SEED + 1), est_i, N_TRUE),
                                               "flock": surveys_needed(np.random.default_rng(SEED + 2), est_f, N_TRUE)}}

    # 2) 本当は10%減った（1,000→900）：2回の見込みの比べ
    sizes2 = make_flocks(np.random.default_rng(SEED + 3), REPS, n=900)
    cnt_f2, _ = count_flocks(np.random.default_rng(SEED + 4), sizes2, lambda s: P)
    cnt_i2 = np.random.default_rng(SEED + 5).binomial(900, P, REPS)
    decline = {"individual": {"p_down": r((cnt_i2 < cnt_i).mean()), "p_up": r((cnt_i2 > cnt_i).mean())},
               "flock": {"p_down": r((cnt_f2 < cnt_f).mean()), "p_up": r((cnt_f2 > cnt_f).mean())}}
    # 3回ずつ数えて平均したら（群れ）
    k = 3
    a = est_f[:REPS // k * k].reshape(-1, k).mean(1)
    b = (cnt_f2 / P)[:REPS // k * k].reshape(-1, k).mean(1)
    decline["flock_mean_of_3"] = {"p_down": r((b < a).mean()), "p_up": r((b > a).mean())}

    # 3) 大きい群れほど見つけやすいとき：見つけた群れの割合で割り戻すと
    def p_size(s, scale=10.0):
        return 1 - 0.5 * np.exp(-(s - 1) / scale)
    sd_rows = []
    for scale in [5.0, 10.0, 20.0]:
        for mu in [5.0, 20.0, 50.0]:
            sz = make_flocks(np.random.default_rng(SEED * 10 + int(scale) + int(mu)), 5000, mu=mu)
            c, d = count_flocks(np.random.default_rng(SEED * 20 + int(scale) + int(mu)), sz, lambda s: p_size(s, scale))
            nf = (sz > 0).sum(1)
            flock_rate = d.sum(1) / nf                         # 見つけた群れの割合
            bird_rate = c / N_TRUE                             # 見つけた鳥の割合（本当の数が分からないと出せない）
            est_by_flock_rate = c / flock_rate
            sd_rows.append({"detect_scale": scale, "flock_mean": mu, "flock_found_rate": r(flock_rate.mean()),
                            "bird_found_rate": r(bird_rate.mean()),
                            "est_by_flock_rate_mean": r(est_by_flock_rate.mean(), 2),
                            "bias_pct": r((est_by_flock_rate.mean() / N_TRUE - 1) * 100, 2),
                            "within10": r(within(est_by_flock_rate, N_TRUE, .1))})
    size_dep = pd.DataFrame(sd_rows)
    size_dep.to_csv(RES / "size_dependent_detection.csv", index=False)

    # 4) 確かめ：群れの大きさの平均×散らばり×見つける割合（27通り）
    grid = []
    gi = 0
    for mu in [5.0, 20.0, 50.0]:
        for shape in [4.0, 1.0, 0.25]:
            for p in [0.6, 0.8, 0.95]:
                gi += 1
                g_rng = np.random.default_rng(SEED * 1000 + gi)
                sz = make_flocks(g_rng, 6000, mu=mu, shape=shape)
                c, _ = count_flocks(g_rng, sz, lambda s, p=p: p)
                ef = c / p
                ei = g_rng.binomial(N_TRUE, p, 6000) / p
                ss = (sz.astype(float) ** 2).sum(1).mean()
                grid.append({"flock_mean": mu, "shape": shape, "p_found": p,
                             "size_cv": r(np.sqrt((sz[sz > 0].astype(float)).var()) / sz[sz > 0].mean(), 3),
                             "bird_weighted_flock_size": r(ss / N_TRUE, 2),
                             "sd_ratio_sim": r(ef.std() / ei.std()), "sd_ratio_formula": r(np.sqrt(ss / N_TRUE)),
                             "within10_individual": r(within(ei, N_TRUE, .1)), "within10_flock": r(within(ef, N_TRUE, .1)),
                             "surveys_needed_flock": surveys_needed(np.random.default_rng(SEED * 3000 + gi), ef, N_TRUE)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # data：例の1回の群れ
    ex_n = int((sizes[0] > 0).sum())
    pd.DataFrame({"flock": np.arange(1, ex_n + 1), "size": sizes[0, :ex_n], "found": det[0, :ex_n].astype(int)}).to_csv(
        DATA / "example_survey_flocks.csv", index=False)
    pd.DataFrame({"survey": np.arange(1, 1001), "est_individual": np.round(est_i[:1000], 2),
                  "est_flock": np.round(est_f[:1000], 2)}).to_csv(DATA / "first1000_surveys.csv", index=False)

    rel = np.abs(grid.sd_ratio_sim / grid.sd_ratio_formula - 1)
    out = {"setting": {"N_true": N_TRUE, "flock_mean": 20, "shape": 1.0, "p_found": P, "reps": REPS},
           "base": base, "decline_10pct": decline,
           "example_survey": {"n_flocks": ex_n, "largest": int(sizes[0].max()), "found_birds": int(cnt_f[0]),
                              "est": r(est_f[0], 2)},
           "size_dependent_detection": size_dep.to_dict("records"),
           "grid_summary": {"sd_ratio_sim_range": [r(grid.sd_ratio_sim.min()), r(grid.sd_ratio_sim.max())],
                            "max_rel_diff_sim_vs_formula": r(rel.max()),
                            "within10_flock_range": [r(grid.within10_flock.min()), r(grid.within10_flock.max())],
                            "within10_individual_range": [r(grid.within10_individual.min()), r(grid.within10_individual.max())],
                            "surveys_needed_flock_range": [int(grid.surveys_needed_flock.min()), int(grid.surveys_needed_flock.max())],
                            "n_flock_within10_lt_individual": int((grid.within10_flock < grid.within10_individual).sum())}}
    json.dump(out, open(RES / "a1220_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：見込みの散らばり
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.arange(600, 1420, 20)
    ax.hist(est_i, bins=bins, color=BLUE, alpha=.65, density=True, label="1羽ずつ80%で見つかる")
    ax.hist(est_f, bins=bins, color=ORANGE, alpha=.55, density=True, label="群れごとに80%で見つかる")
    ax.axvline(N_TRUE, color=INK, lw=1, ls="--"); ax.text(N_TRUE + 8, ax.get_ylim()[1] * 0.9, "本当の1,000羽", fontsize=9)
    ax.set_xlabel("数えた数を0.8で割った見込み（羽）"); ax.set_yticks([])
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"見込みの平均は同じでも、群れごとに見落とすと標準偏差は{sd_f / sd_i:.4f}倍")
    save(fig, "a1220_spread.png", SRC)

    # 図2：27通りの ±10%に入る割合（群れ）
    g8 = grid[grid.p_found == 0.8].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    SHN = {4.0: "大きさがそろう", 1.0: "ふつう", 0.25: "大きさが大きく散る"}
    labels = [f"平均{int(m)}羽・{SHN[s]}" for m, s in zip(g8.flock_mean, g8["shape"])]
    yy = np.arange(len(g8))
    ax.barh(yy, g8.within10_flock * 100, color=ORANGE)
    for i, v in enumerate(g8.within10_flock * 100):
        ax.text(v - 1, i, f"{v:.2f}%", va="center", ha="right", fontsize=8.5, color="white")
    iv = g8.within10_individual.iloc[0] * 100
    ax.axvline(iv, color=BLUE, ls="--", lw=1.2)
    ax.text(iv - 1, len(g8) - 0.4, f"1羽ずつ見つかるとき{iv:.2f}%", color=BLUE, fontsize=8.5, ha="right", va="center")
    ax.set_yticks(yy); ax.set_yticklabels(labels, fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, 110); ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel("1回の見込みが本当の±10%に入った割合（%、見つける割合0.8、各6,000回）")
    ax.set_title("群れが大きく、大きさが散るほど、1回の数は当たらない")
    save(fig, "a1220_grid.png", SRC)

    # 図3：大きい群れほど見つけやすいとき、見つけた群れの割合で割り戻すと
    s10 = size_dep[size_dep.detect_scale == 10.0].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    yy = np.arange(len(s10))
    ax.barh(yy, s10.est_by_flock_rate_mean, color=GREEN)
    for i, (v, bpct) in enumerate(zip(s10.est_by_flock_rate_mean, s10.bias_pct)):
        ax.text(v + 10, i, f"{v:.2f}羽（{bpct:+.2f}%）", va="center", fontsize=9)
    ax.axvline(N_TRUE, color=INK, ls="--", lw=1); ax.text(N_TRUE + 8, len(s10) - 0.5, "本当の1,000羽", fontsize=9, va="center")
    ax.set_yticks(yy); ax.set_yticklabels([f"群れの平均{int(m)}羽" for m in s10.flock_mean]); ax.invert_yaxis()
    ax.set_ylim(len(s10) - 0.3, -0.6)
    ax.set_xlim(0, 1600); ax.set_xlabel("見つけた群れの割合で割り戻した見込みの平均（羽、各5,000回）")
    ax.set_title("大きい群れほど見つけやすいと、群れの割合で割り戻すと多すぎる")
    save(fig, "a1220_size_detect.png", SRC)

    print(json.dumps({k: out[k] for k in ["base", "decline_10pct", "example_survey", "grid_summary"]}, ensure_ascii=False, indent=1))
    pd.set_option("display.width", 250)
    print(size_dep.to_string()); print(grid.to_string())


if __name__ == "__main__":
    main()
