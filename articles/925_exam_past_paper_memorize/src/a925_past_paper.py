"""925 過去問の点が上がったのは、実力か問題を覚えたからか？（架空のデータ）

架空の大人向けの資格試験の勉強。過去問の集まり（300問）から、週に1回40問を選んで解き、
答え合わせをする。これを12週続ける。点が上がる理由は2つ置く。
 ①実力が週ごとに伸びる（初めて見る問題でも解ける力）
 ②一度見た問題の答えを覚える（答え合わせのたびに、ある確率で覚える。忘れない）
本当の実力は「初めて見る問題を解いたときの正答率」として、作成者が分かる形で数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 925
SRC = "架空の資格試験の過去問と学ぶ人（作成者が乱数で作成、seed 925）"
N_LEARN, N_WEEK, N_ITEM = 200, 12, 40
POOL, MEM, GROW = 300, 0.3, 0.05


def prob(theta, b):
    return 1.0 / (1.0 + np.exp(-1.7 * (theta - b)))


def run(rng, pool=POOL, mem_mean=MEM, grow_mean=GROW, n_learn=N_LEARN, n_week=N_WEEK, n_item=N_ITEM,
        new_b=None):
    """学ぶ人 n_learn 人 × n_week 週。週ごとの点を返す"""
    b = rng.normal(0.0, 1.0, pool)
    if new_b is None:
        new_b = rng.normal(0.0, 1.0, 2000)          # 初めて見る問題（本当の実力を測る物差し）
    th0 = rng.normal(-0.5, 0.7, n_learn)
    g = rng.uniform(0, 2 * grow_mean, n_learn)       # 1週あたりの実力の伸び
    m = np.clip(rng.uniform(mem_mean - 0.2, mem_mean + 0.2, n_learn), 0, 1) if mem_mean > 0 else np.zeros(n_learn)
    seen = np.zeros((n_learn, pool), dtype=np.int16)
    known = np.zeros((n_learn, pool), dtype=bool)
    cols = {k: [] for k in ["past_score", "true_new_score", "n_first_seen", "first_seen_score", "n_known_before"]}
    r = np.arange(n_learn)[:, None]
    for w in range(n_week):
        th = th0 + g * w
        idx = np.argpartition(rng.random((n_learn, pool)), n_item, axis=1)[:, :n_item]
        kn = known[r, idx]
        first = seen[r, idx] == 0
        p = prob(th[:, None], b[idx])
        correct = kn | (rng.random(p.shape) < p)
        n_first = first.sum(1)
        cols["past_score"].append(100 * correct.mean(1))
        cols["true_new_score"].append(100 * prob(th[:, None], new_b[None, :]).mean(1))
        cols["n_first_seen"].append(n_first)
        cols["first_seen_score"].append(np.where(n_first > 0, 100 * (correct & first).sum(1) / np.maximum(n_first, 1), np.nan))
        cols["n_known_before"].append(kn.sum(1))
        # 答え合わせ：見た問題を数え、ある確率で答えを覚える
        seen[r, idx] += 1
        learn = rng.random(idx.shape) < m[:, None]
        known[r, idx] |= learn
    rows = {"learner_id": np.tile(np.arange(1, n_learn + 1), n_week), "week": np.repeat(np.arange(1, n_week + 1), n_learn)}
    rows.update({k: np.concatenate(v) for k, v in cols.items()})
    df = pd.DataFrame(rows)
    # 本番：初めて見る40問
    th_end = th0 + g * (n_week - 1)
    eb = rng.choice(new_b, n_item, replace=False)
    exam = 100 * (rng.random((n_learn, n_item)) < prob(th_end[:, None], eb[None, :])).mean(1)
    learners = pd.DataFrame({"learner_id": np.arange(1, n_learn + 1), "theta_start": th0, "growth_per_week": g,
                             "memory_rate": m, "exam_score": exam})
    return df, learners


def summarize(df, learners):
    w1, wl = df[df.week == 1].set_index("learner_id"), df[df.week == df.week.max()].set_index("learner_id")
    past_gain = wl.past_score - w1.past_score
    true_gain = wl.true_new_score - w1.true_new_score
    fs_gain = wl.first_seen_score - w1.first_seen_score
    mem_part = past_gain.mean() - true_gain.mean()
    top = past_gain.rank(ascending=False, method="first") <= len(past_gain) * 0.2
    top_t = true_gain.rank(ascending=False, method="first") <= len(true_gain) * 0.2
    return {"past_w1": w1.past_score.mean(), "past_last": wl.past_score.mean(),
            "true_w1": w1.true_new_score.mean(), "true_last": wl.true_new_score.mean(),
            "past_gain": past_gain.mean(), "true_gain": true_gain.mean(),
            "memory_part": mem_part, "memory_share_of_gain": mem_part / past_gain.mean() if past_gain.mean() > 0 else np.nan,
            "first_seen_gain": fs_gain.mean(),
            "share_known_last": wl.n_known_before.mean() / N_ITEM,
            "n_first_seen_last_mean": wl.n_first_seen.mean(),
            "exam_mean": learners.exam_score.mean(),
            "past_last_minus_exam": wl.past_score.mean() - learners.exam_score.mean(),
            "past_last_minus_true_last": wl.past_score.mean() - wl.true_new_score.mean(),
            "first_seen_last_minus_true_last": (wl.first_seen_score - wl.true_new_score).mean(),
            "share_learners_no_first_seen_last": (wl.n_first_seen == 0).mean(),
            "corr_pastgain_truegain": np.corrcoef(past_gain, true_gain)[0, 1],
            "corr_firstseen_gain_truegain": np.corrcoef(fs_gain.fillna(fs_gain.mean()), true_gain)[0, 1],
            "corr_pastgain_memory_rate": np.corrcoef(past_gain, learners.set_index("learner_id").memory_rate)[0, 1],
            "top20_pastgain_in_top20_truegain": (top & top_t).sum() / top.sum()}


def r3(d):
    return {k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in d.items()}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    df, learners = run(rng)
    df.round(3).to_csv(DATA / "weekly_scores.csv", index=False)
    learners.round(4).to_csv(DATA / "learners.csv", index=False)
    base = summarize(df, learners)
    base["true_w1_minus_past_w1"] = base["true_w1"] - base["past_w1"]
    base = r3(base)
    weekly = df.groupby("week").agg(past_score=("past_score", "mean"), true_new_score=("true_new_score", "mean"),
                                    first_seen_score=("first_seen_score", "mean"),
                                    n_first_seen=("n_first_seen", "mean"),
                                    n_known_before=("n_known_before", "mean")).round(3)
    weekly.to_csv(RES / "weekly_mean.csv")

    # 例の200人を作り直して100回：基本の値の幅
    reps = pd.DataFrame([summarize(*run(np.random.default_rng(SEED * 100 + k))) for k in range(100)])
    rep_sum = {c: {"mean": round(float(reps[c].mean()), 3), "p10": round(float(reps[c].quantile(.1)), 3),
                   "p90": round(float(reps[c].quantile(.9)), 3)}
               for c in ["past_gain", "true_gain", "memory_part", "memory_share_of_gain", "first_seen_gain",
                         "past_last_minus_exam", "past_last_minus_true_last", "first_seen_last_minus_true_last", "corr_pastgain_truegain", "top20_pastgain_in_top20_truegain"]}

    # 確かめ：過去問の数・覚える確率・実力の伸びを変えると（各200人×10回の平均）
    grid = []
    k = 0
    for pool in [100, 300, 1000, 3000]:
        for mem in [0.0, 0.15, 0.3, 0.5]:
            for grow in [0.0, 0.05, 0.1]:
                ss = [summarize(*run(np.random.default_rng(SEED * 7 + k * 31 + j), pool=pool, mem_mean=mem,
                                     grow_mean=grow)) for j in range(10)]
                k += 1
                s = pd.DataFrame(ss).mean()
                grid.append({"pool": pool, "memory_rate_mean": mem, "growth_per_week_mean": grow,
                             **{c: round(float(s[c]), 3) for c in
                                ["past_gain", "true_gain", "memory_part", "memory_share_of_gain", "first_seen_gain",
                                 "past_last_minus_true_last", "share_known_last", "n_first_seen_last_mean",
                                 "corr_pastgain_truegain"]}})
    grid = pd.DataFrame(grid)
    # 伸びがない置き方では「伸びのうち覚えた分の割合」は意味がないので空にする
    grid.loc[grid.growth_per_week_mean == 0, "memory_share_of_gain"] = np.nan
    grid.to_csv(RES / "robustness.csv", index=False)
    g_pos = grid[(grid.memory_rate_mean > 0) & (grid.growth_per_week_mean > 0)]
    g_zero_mem = grid[grid.memory_rate_mean == 0]
    g_zero_grow = grid[(grid.growth_per_week_mean == 0) & (grid.memory_rate_mean > 0)]
    rob = {"memory_share_range_mem_and_grow_pos": [round(float(g_pos.memory_share_of_gain.min()), 3),
                                                   round(float(g_pos.memory_share_of_gain.max()), 3)],
           "memory_part_range_mem_and_grow_pos": [round(float(g_pos.memory_part.min()), 3),
                                                  round(float(g_pos.memory_part.max()), 3)],
           "past_minus_true_last_range_mem_and_grow_pos": [round(float(g_pos.past_last_minus_true_last.min()), 3),
                                                           round(float(g_pos.past_last_minus_true_last.max()), 3)],
           "memory0_abs_memory_part_max": round(float(g_zero_mem.memory_part.abs().max()), 3),
           "memory0_abs_first_seen_minus_true_gain_max": round(float((g_zero_mem.first_seen_gain - g_zero_mem.true_gain).abs().max()), 3),
           "all_abs_first_seen_minus_true_gain_max": round(float((grid.first_seen_gain - grid.true_gain).abs().max()), 3),
           "pool300plus_abs_first_seen_minus_true_gain_max": round(float((grid[grid.pool >= 300].first_seen_gain - grid[grid.pool >= 300].true_gain).abs().max()), 3),
           "pool100_n_first_seen_last_mean_range": [round(float(grid[grid.pool == 100].n_first_seen_last_mean.min()), 3),
                                                    round(float(grid[grid.pool == 100].n_first_seen_last_mean.max()), 3)],
           "grow0_past_gain_range": [round(float(g_zero_grow.past_gain.min()), 3), round(float(g_zero_grow.past_gain.max()), 3)],
           "corr_pastgain_truegain_range_mem_pos_grow_pos": [round(float(g_pos.corr_pastgain_truegain.min()), 3),
                                                             round(float(g_pos.corr_pastgain_truegain.max()), 3)]}

    out = {"setting": {"learners": N_LEARN, "weeks": N_WEEK, "items_per_week": N_ITEM, "pool": POOL,
                       "memory_rate_mean": MEM, "memory_rate_range": [MEM - 0.2, MEM + 0.2],
                       "growth_per_week_mean": GROW},
           "example_200": base, "weekly_mean": weekly.reset_index().to_dict("records"),
           "reps100": rep_sum, "robustness_summary": rob}
    json.dump(out, open(RES / "a925_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：週ごとの平均
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    wk = weekly.index.values
    ax.plot(wk, weekly.past_score, color=ORANGE, marker="o", ms=4, label="過去問の点（40問）")
    ax.plot(wk, weekly.first_seen_score, color=GREEN, marker="s", ms=4, ls="--", label="そのうち初めて見た問題だけの点")
    ax.plot(wk, weekly.true_new_score, color=BLUE, lw=2.2, label="本当の実力（初めて見る問題の正答率）")
    ax.set_xlabel("週"); ax.set_ylabel("点（100点満点、200人の平均）"); ax.set_xticks(wk)
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"過去問の点は{base['past_gain']:.1f}点上がり、本当の実力は{base['true_gain']:.1f}点上がった（200人）", fontsize=12)
    save(fig, "a925_weekly.png", SRC)

    # 図2：1人ずつの伸び
    w1, wl = df[df.week == 1].set_index("learner_id"), df[df.week == N_WEEK].set_index("learner_id")
    pg, tg = wl.past_score - w1.past_score, wl.true_new_score - w1.true_new_score
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    sc = ax.scatter(tg, pg, c=learners.set_index("learner_id").memory_rate, cmap="Oranges", s=16, vmin=0, vmax=0.6,
                    edgecolor=GRAY, lw=.3)
    lim = [min(tg.min(), pg.min()) - 3, max(tg.max(), pg.max()) + 3]
    ax.plot(lim, lim, color=GRAY, lw=.8); ax.text(lim[1] - 1, lim[1] - 4, "同じ伸び", color=GRAY, fontsize=8.5, ha="right")
    ax.set_xlabel("本当の実力の伸び（点）"); ax.set_ylabel("過去問の点の伸び（1週目→12週目、点）")
    cb = fig.colorbar(sc, ax=ax, shrink=.8); cb.set_label("答えを覚える確率（1回見るごと）")
    ax.set_title(f"過去問の伸びと本当の伸びの相関は{base['corr_pastgain_truegain']:.2f}（200人）", fontsize=12)
    save(fig, "a925_learners.png", SRC)

    # 図3：過去問の数と覚える確率で、伸びのうち覚えた分の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    sub = grid[grid.growth_per_week_mean == GROW]
    for mem, col in [(0.0, GRAY), (0.15, LIGHT), (0.3, BLUE), (0.5, ORANGE)]:
        s = sub[sub.memory_rate_mean == mem].sort_values("pool")
        ax.plot(s.pool, s.memory_share_of_gain * 100, marker="o", color=col, label=f"覚える確率 平均{mem}")
    ax.set_xscale("log"); ax.minorticks_off(); ax.set_xticks([100, 300, 1000, 3000]); ax.set_xticklabels(["100問", "300問（基本）", "1,000問", "3,000問"])
    ax.set_xlabel("過去問の集まりの問題数（対数の目盛り）"); ax.set_ylabel("過去問の点の伸びのうち、覚えた分（%）")
    ax.set_ylim(-5, 100); ax.legend(frameon=False, fontsize=9)
    ax.set_title("過去問が少なく、よく覚えるほど、伸びの多くは覚えた分になる（実力の伸び 週0.05）", fontsize=12)
    save(fig, "a925_settings.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
