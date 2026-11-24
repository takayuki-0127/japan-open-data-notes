"""1277 遅れた仕事の写しを別の所でも動かすと、全体の時間はどれだけ縮み、使う手間はどれだけ増えるのか？（並列処理）

作成者が置いた架空のアプリの処理（仕事400個を20か所で動かす）をシミュレーションする。実機の計測はしていない。
写しの決まり：待っている仕事がなくなって手のあいた所は、動いている仕事のうち、
動き始めてからの時間が「終わった仕事の時間の中央値 × k」を超え、まだ写しのないものを1つ選び（いちばん長く動いているもの）、
写しを最初から動かす。先に終わった方を使い、もう一方は止める。
遅さの原因は2つの形：
  所：動かす所のせいで遅い（写しは別の所なので、写しの遅さは新しく引き直す）
  仕事：仕事そのものが大きい（写しも同じだけかかる）
"""
import json
import heapq
import itertools
import bisect
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1277
SRC = "架空のアプリの処理（作成者が乱数で作成、seed 1277）。実機の計測ではなくシミュレーション"
N_TASK = 400
P = 20
MEAN_T = 1.0
SIGMA_T = 0.3
Q = 0.05        # 1回動かすとき（形「所」）または1つの仕事（形「仕事」）が遅くなる確率
F = 5.0         # 遅くなったときの倍率
K = 1.5         # 中央値の何倍を超えたら写しの候補にするか
N_REP = 200
N_REP_GRID = 60


def make_sizes(rng, q_task, f, n=N_TASK):
    """仕事の大きさ：右に長い分布。確率 q_task で f 倍の大きな仕事"""
    base = rng.lognormal(np.log(MEAN_T) - SIGMA_T ** 2 / 2, SIGMA_T, n)
    return base * np.where(rng.random(n) < q_task, f, 1.0)


def simulate(att_seed, size, q_place, f, copy, k=K, p=P):
    """1回ごとに確率 q_place で、動かす所のせいで f 倍かかる"""
    n = len(size)
    att_rng = np.random.default_rng(att_seed)

    def duration(i):
        return size[i] * (f if att_rng.random() < q_place else 1.0)

    queue = list(range(n))
    qi = 0
    events = []                      # (時刻, 種類, 番号)
    attempts = []                    # [task, worker, start, end, alive, is_copy]
    by_task = {}                     # task -> 動いている attempt の番号
    has_copy = np.zeros(n, bool)
    done = np.zeros(n, bool)
    finished = []                    # 終わった仕事にかかった時間（並べたまま）
    idle = []
    work = 0.0
    copy_work = 0.0
    n_copy = n_copy_won = 0

    def start(task, w, now, is_copy):
        d = duration(task)
        a = len(attempts)
        attempts.append([task, w, now, now + d, True, is_copy])
        by_task.setdefault(task, []).append(a)
        heapq.heappush(events, (now + d, 0, a))

    def try_assign(now):
        nonlocal qi, n_copy
        still = []
        wake = np.inf
        for w in idle:
            if qi < n:
                start(queue[qi], w, now, False)
                qi += 1
                continue
            if not copy or not finished:
                still.append(w)
                continue
            th = k * finished[len(finished) // 2]
            best, best_el = None, -1.0
            for t_id, alist in by_task.items():
                if done[t_id] or has_copy[t_id]:
                    continue
                a0 = attempts[alist[0]]
                el = now - a0[2]
                if el > th + 1e-12:
                    if el > best_el:
                        best, best_el = t_id, el
                else:
                    wake = min(wake, a0[2] + th)
            if best is None:
                still.append(w)
            else:
                has_copy[best] = True
                n_copy += 1
                start(best, w, now, True)
        idle[:] = still
        if idle and wake < np.inf:
            heapq.heappush(events, (wake + 1e-9, 1, -1))

    for w in range(p):
        idle.append(w)
    try_assign(0.0)
    end_time = 0.0
    while events:
        now, kind, a = heapq.heappop(events)
        if kind == 1:
            try_assign(now)
            continue
        at = attempts[a]
        if not at[4]:
            continue
        task = at[0]
        done[task] = True
        bisect.insort(finished, now - attempts[by_task[task][0]][2])
        if at[5]:
            n_copy_won += 1
        for b in by_task.pop(task):
            ab = attempts[b]
            ab[4] = False
            work += now - ab[2]
            if ab[5]:
                copy_work += now - ab[2]
            idle.append(ab[1])
        end_time = now
        if done.all():
            break
        try_assign(now)
    return {"makespan": end_time, "work": work, "copy_work": copy_work, "n_copy": n_copy, "n_copy_won": n_copy_won,
            "ideal_work": float(size.sum())}


def run_pair(seed, cause, q=Q, f=F, k=K):
    """同じ仕事・同じ乱数で、写しなし・写しありの2つを動かす。
    cause：place（所）・task（仕事）・mixed（半分ずつ：仕事が大きい確率 q/2、所で遅い確率 q/2）"""
    q_task = {"place": 0.0, "task": q, "mixed": q / 2}[cause]
    q_place = q - q_task
    rng = np.random.default_rng(seed)
    size = make_sizes(rng, q_task, f)
    att = int(rng.integers(1 << 62))
    return simulate(att, size, q_place, f, False, k), simulate(att, size, q_place, f, True, k)


def main():
    causes = {"place": "所のせいで遅い", "task": "仕事そのものが大きい"}
    rows = []
    for cause in causes:
        for rep in range(N_REP):
            r0, r1 = run_pair(SEED * 1000 + rep, cause)
            rows.append({"cause": cause, "rep": rep + 1,
                         "makespan_no_copy": round(r0["makespan"], 4), "makespan_copy": round(r1["makespan"], 4),
                         "work_no_copy": round(r0["work"], 4), "work_copy": round(r1["work"], 4),
                         "copy_work": round(r1["copy_work"], 4),
                         "n_copy": r1["n_copy"], "n_copy_won": r1["n_copy_won"]})
    reps = pd.DataFrame(rows)
    reps.to_csv(DATA / "reps_base.csv", index=False)

    summ = []
    for cause in causes:
        d = reps[reps.cause == cause]
        ratio = d.makespan_copy / d.makespan_no_copy
        summ.append({"cause": cause,
                     "makespan_no_copy_median": round(d.makespan_no_copy.median(), 4),
                     "makespan_copy_median": round(d.makespan_copy.median(), 4),
                     "makespan_ratio_median": round(ratio.median(), 4),
                     "makespan_ratio_p10": round(ratio.quantile(0.1), 4),
                     "makespan_ratio_p90": round(ratio.quantile(0.9), 4),
                     "share_reps_shorter": round(float((ratio < 1 - 1e-9).mean()), 4),
                     "share_reps_longer": round(float((ratio > 1 + 1e-9).mean()), 4),
                     "work_increase_pct_median": round(float(((d.work_copy / d.work_no_copy - 1) * 100).median()), 4),
                     "work_increase_pct_max": round(float(((d.work_copy / d.work_no_copy - 1) * 100).max()), 4),
                     "copy_work_pct_median": round(float((d.copy_work / d.work_no_copy * 100).median()), 4),
                     "copy_work_pct_max": round(float((d.copy_work / d.work_no_copy * 100).max()), 4),
                     "n_copy_mean": round(d.n_copy.mean(), 4),
                     "copy_won_share": round(float(d.n_copy_won.sum() / max(d.n_copy.sum(), 1)), 4)})
    summ = pd.DataFrame(summ)
    summ.to_csv(RES / "base_summary.csv", index=False)

    # k を変える（形ごと）
    krows = []
    for cause, k in itertools.product(causes, [1.0, 1.5, 2.0, 3.0, 5.0]):
        res = [run_pair(SEED * 1000 + 50000 + rep, cause, k=k) for rep in range(N_REP_GRID)]
        m0 = np.array([a["makespan"] for a, b in res]); m1 = np.array([b["makespan"] for a, b in res])
        w0 = np.array([a["work"] for a, b in res]); w1 = np.array([b["work"] for a, b in res])
        krows.append({"cause": cause, "k": k, "makespan_ratio_median": round(float(np.median(m1 / m0)), 4),
                      "work_increase_pct_median": round(float(np.median((w1 / w0 - 1) * 100)), 4),
                      "n_copy_mean": round(float(np.mean([b["n_copy"] for a, b in res])), 4)})
    ksweep = pd.DataFrame(krows)
    ksweep.to_csv(RES / "k_sweep.csv", index=False)

    # 確かめ：遅くなる確率 × 倍率 × 形（k は1.5）
    grid = []
    for (q, f, cause) in itertools.product([0.02, 0.05, 0.1], [3.0, 5.0, 10.0], list(causes) + ["mixed"]):
        res = []
        for rep in range(N_REP_GRID):
            res.append(run_pair(SEED * 1000 + 90000 + rep, cause, q, f))
        m0 = np.array([a["makespan"] for a, b in res]); m1 = np.array([b["makespan"] for a, b in res])
        w0 = np.array([a["work"] for a, b in res]); w1 = np.array([b["work"] for a, b in res])
        grid.append({"q": q, "factor": f, "cause": cause,
                     "makespan_no_copy_median": round(float(np.median(m0)), 4),
                     "makespan_copy_median": round(float(np.median(m1)), 4),
                     "makespan_ratio_median": round(float(np.median(m1 / m0)), 4),
                     "work_increase_pct_median": round(float(np.median((w1 / w0 - 1) * 100)), 4),
                     "n_copy_mean": round(float(np.mean([b["n_copy"] for a, b in res])), 4),
                     "copy_won_share": round(float(sum(b["n_copy_won"] for a, b in res) / max(sum(b["n_copy"] for a, b in res), 1)), 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    def rng_of(g):
        return [g.min(), g.max()]
    gp, gt, gm = grid[grid.cause == "place"], grid[grid.cause == "task"], grid[grid.cause == "mixed"]
    sp = summ.set_index("cause")
    main_json = {
        "settings": {"n_task": N_TASK, "workers": P, "mean_task_sec": MEAN_T, "sigma_log": SIGMA_T, "q": Q, "factor": F,
                     "k": K, "n_rep": N_REP, "n_rep_grid": N_REP_GRID},
        "base": {c: sp.loc[c].to_dict() for c in causes},
        "k_sweep": ksweep.to_dict(orient="records"),
        "grid": {"n": len(grid),
                 "place_ratio_range": rng_of(gp.makespan_ratio_median), "place_work_pct_range": rng_of(gp.work_increase_pct_median),
                 "task_ratio_range": rng_of(gt.makespan_ratio_median), "task_work_pct_range": rng_of(gt.work_increase_pct_median),
                 "mixed_ratio_range": rng_of(gm.makespan_ratio_median), "mixed_work_pct_range": rng_of(gm.work_increase_pct_median),
                 "place_copy_won_range": rng_of(gp.copy_won_share), "task_copy_won_range": rng_of(gt.copy_won_share)},
    }
    main_json = json.loads(json.dumps(main_json, default=float))
    with open(RES / "a1277_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：基本の置き方、全体の時間の分布
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, cause in zip(axs, causes):
        d = reps[reps.cause == cause]
        bins = np.linspace(15, max(reps.makespan_no_copy.max(), reps.makespan_copy.max()) * 1.02, 40)
        ax.hist(d.makespan_no_copy, bins=bins, color=GRAY, alpha=0.7, label="写しなし")
        ax.hist(d.makespan_copy, bins=bins, color=BLUE, alpha=0.7, label="写しあり")
        s = sp.loc[cause]
        ax.axvline(s.makespan_no_copy_median, color=INK, ls=":", lw=1)
        ax.axvline(s.makespan_copy_median, color=BLUE, ls="--", lw=1)
        extra = "（写しなしと写しありが重なる）" if cause == "task" else ""
        ax.set_title(f"遅さの原因：{causes[cause]}{extra}\n中央値 {s.makespan_no_copy_median}秒 → {s.makespan_copy_median}秒", fontsize=11)
        ax.set_xlabel("全体が終わるまでの時間（秒）")
    axs[0].set_ylabel("回数（200回のうち）")
    axs[0].legend(frameon=False, fontsize=9)
    save(fig, "a1277_makespan.png", SRC + "。仕事400個・20か所。5%が5倍遅い。写しは中央値の1.5倍を超えた仕事")

    # 図2：k を変えたときの、縮み方と手間
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    for cause, c in [("place", BLUE), ("task", ORANGE)]:
        d = ksweep[ksweep.cause == cause]
        axs[0].plot(d.k, d.makespan_ratio_median, "o-", color=c, label=causes[cause])
        axs[1].plot(d.k, d.work_increase_pct_median, "o-", color=c, label=causes[cause])
    axs[0].axhline(1, color=GRAY, lw=1, ls="--")
    axs[0].set_ylim(0, 1.2)
    axs[0].set_ylabel("写しありの時間 ÷ 写しなしの時間")
    axs[0].set_title("全体の時間（中央値）", fontsize=11)
    axs[1].axhline(0, color=GRAY, lw=1, ls="--")
    axs[1].set_ylim(min(-1, ksweep.work_increase_pct_median.min() * 1.3), ksweep.work_increase_pct_median.max() * 1.15)
    axs[1].set_ylabel("使う手間の増え方（%）")
    axs[1].set_title("使った時間の合計の増え方（中央値）", fontsize=11)
    for ax in axs:
        ax.set_xlabel("写しを作る目安（終わった仕事の中央値の何倍か）")
    axs[0].legend(frameon=False, fontsize=9)
    save(fig, "a1277_k.png", SRC + "。各60回")

    # 図3：確かめの27通り
    fig, ax = plt.subplots(figsize=(7, 4.6))
    lab = {"place": "所のせいで遅い", "task": "仕事そのものが大きい", "mixed": "半分ずつ"}
    for cause, c in [("place", BLUE), ("task", ORANGE), ("mixed", GREEN)]:
        g = grid[grid.cause == cause]
        ax.scatter(g.work_increase_pct_median, g.makespan_ratio_median, color=c, s=28, label=lab[cause])
    ax.axhline(1, color=GRAY, lw=1, ls="--")
    ax.set_ylim(0, 1.2)
    ax.axvline(0, color=GRAY, lw=1, ls="--")
    ax.set_xlim(grid.work_increase_pct_median.min() - 0.5, grid.work_increase_pct_median.max() + 0.5)
    ax.set_xlabel("使う手間の増え方（%、中央値）")
    ax.set_ylabel("写しありの時間 ÷ 写しなしの時間")
    ax.set_title(f"遅くなる確率・倍率・原因を変えた{len(grid)}通り")
    ax.legend(frameon=False, fontsize=9, title="遅さの原因", title_fontsize=9, loc="lower right")
    save(fig, "a1277_grid.png", SRC + "。遅くなる確率2・5・10%、倍率3・5・10倍、各60回")


if __name__ == "__main__":
    main()
