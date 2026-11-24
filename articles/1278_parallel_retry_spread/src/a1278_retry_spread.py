"""1278 失敗した仕事をやり直す決まりがあると、同時に動かす数を増やすほど、全体の時間のばらつきはどう変わるのか？（架空のデータ）

架空のアプリの処理。決まった数の仕事（基本400個）を、同時に動かす数 W の所で処理する。
空いた所が列の先頭の仕事を取りにいく。1回の実行は確率 p で途中で失敗し（失敗する位置は仕事の中ででたらめ）、
失敗した仕事はやり直す。やり直しの決まりは2つ：
  ① その場ですぐやり直す
  ② 3秒あけてやり直す（そのあいだ所は次の仕事に移り、3秒たった仕事は列の先頭に入る）
全体の時間＝最後の仕事が終わった時刻。同じ仕事の大きさ・同じ失敗で、やり直しなし・①・②を比べる。
すべてシミュレーションで、実機では測っていない。
"""
import json
import time
import heapq
from collections import deque
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1278
SRC = "架空のアプリの処理のシミュレーション（作成者が乱数で作成、seed 1278）"
BASE = {"n": 400, "sigma": 0.5, "p": 0.02, "backoff": 3.0}
WS = [1, 2, 4, 8, 16, 32, 64]
RUNS = 1000
GRID_RUNS = 1000
GRID_WS = [1, 8, 64]
GRID2_RUNS = 300
MAXF = 12


def draw(rng, runs, n, sigma, p):
    """仕事の大きさ（平均1秒）と、仕事ごとの失敗の回数・失敗した位置（仕事の中の割合）"""
    size = rng.lognormal(-sigma ** 2 / 2, sigma, (runs, n))
    nf = rng.geometric(1 - p, (runs, n)) - 1
    nf = np.minimum(nf, MAXF)
    frac = rng.random((runs, n, MAXF))
    frac[np.arange(MAXF)[None, None, :] >= nf[..., None]] = 0.0
    return size, nf, frac


def makespan_greedy(t, w):
    """仕事の時間 t（runs×n）を、空いた所が順に取りにいく形で w か所に配ったときの全体の時間"""
    runs, n = t.shape
    free = np.zeros((runs, w))
    rows = np.arange(runs)
    for j in range(n):
        k = free.argmin(1)
        free[rows, k] += t[:, j]
    return free.max(1)


def makespan_backoff(size, nf, frac, w, b):
    """② 失敗した仕事は b 秒あけてから列の先頭に入る（そのあいだ所は次の仕事へ）"""
    n = size.size
    queue = deque(range(n))
    tried = [0] * n
    ev = []
    idle = []
    seq = 0
    end = 0.0

    def start(wk, t):
        nonlocal seq
        if queue:
            j = queue.popleft()
            a = tried[j]
            if a < nf[j]:
                heapq.heappush(ev, (t + frac[j, a] * size[j], seq, 0, wk, j))
            else:
                heapq.heappush(ev, (t + size[j], seq, 1, wk, j))
            seq += 1
        else:
            idle.append(wk)

    for wk in range(w):
        start(wk, 0.0)
    while ev:
        t, _, kind, wk, j = heapq.heappop(ev)
        if kind == 0:        # 失敗
            tried[j] += 1
            heapq.heappush(ev, (t + b, seq, 2, -1, j))
            seq += 1
            start(wk, t)
        elif kind == 1:      # 終わり
            end = t
            start(wk, t)
        else:                # やり直しの仕事が列に戻る
            queue.appendleft(j)
            if idle:
                start(idle.pop(), t)
    return end


def stats(x):
    return {"mean": float(np.mean(x)), "sd": float(np.std(x)), "cv": float(np.std(x) / np.mean(x)),
            "p50": float(np.quantile(x, 0.5)), "p95": float(np.quantile(x, 0.95))}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    n, sigma, p, b = BASE["n"], BASE["sigma"], BASE["p"], BASE["backoff"]
    size, nf, frac = draw(rng, RUNS, n, sigma, p)
    t_retry = size * (1 + frac.sum(2))
    rows = []
    store = {}
    for w in WS:
        ms_none = makespan_greedy(size, w)
        ms_a = makespan_greedy(t_retry, w)
        ms_b = np.array([makespan_backoff(size[r], nf[r], frac[r], w, b) for r in range(RUNS)])
        store[w] = (ms_none, ms_a, ms_b)
        for rule, ms in [("none", ms_none), ("retry_now", ms_a), ("retry_after_3s", ms_b)]:
            s = stats(ms)
            s.update({"w": w, "rule": rule,
                      "p95_over_p50": s["p95"] / s["p50"],
                      "mean_over_none": float(ms.mean() / ms_none.mean()),
                      "extra_sec_mean": float((ms - ms_none).mean()),
                      "extra_sec_sd": float((ms - ms_none).std()),
                      "extra_sec_p95": float(np.quantile(ms - ms_none, 0.95)),
                      "share_extra_over_1s": float(((ms - ms_none) >= 1.0).mean())})
            rows.append(s)
    base = pd.DataFrame(rows)[["rule", "w", "mean", "sd", "cv", "p50", "p95", "p95_over_p50",
                               "mean_over_none", "extra_sec_mean", "extra_sec_sd", "extra_sec_p95", "share_extra_over_1s"]]
    base = base.round(4)
    base.to_csv(RES / "base_by_w.csv", index=False)

    # 式との照らし合わせ：所が1つなら、①の全体の時間の平均は 仕事の数×(1＋失敗の回数の平均×0.5)
    ef = float(np.mean(nf))
    check = {"failures_per_job_mean": round(ef, 5), "failures_per_job_formula": round(p / (1 - p), 5),
             "w1_retry_now_mean": round(float(store[1][1].mean()), 3),
             "w1_retry_now_formula": round(n * (1 + p / (1 - p) * 0.5), 3),
             "total_work_extra_pct": round(float((t_retry.sum(1) / size.sum(1)).mean() - 1) * 100, 3),
             "runs_with_any_failure_pct": round(float((nf.sum(1) > 0).mean()) * 100, 2),
             "runs_with_any_failure_formula_pct": round((1 - (1 - p) ** n) * 100, 2)}

    # 1回分の例（W=64）
    r0 = 0
    pd.DataFrame({"job_id": np.arange(n), "size_sec": size[r0].round(4), "failures": nf[r0],
                  "wasted_sec": (size[r0] * frac[r0].sum(1)).round(4)}).to_csv(DATA / "example_run.csv", index=False)

    # 確かめ：27通り（①、所 1・8・64）
    grng = np.random.default_rng(SEED + 1)
    grows = []
    for gp in [0.005, 0.02, 0.05]:
        for gs in [0.25, 0.5, 1.0]:
            for gn in [100, 400, 1600]:
                sz, f, fr = draw(grng, GRID_RUNS, gn, gs, gp)
                tr = sz * (1 + fr.sum(2))
                row = {"p": gp, "sigma": gs, "n": gn}
                for w in GRID_WS:
                    a = makespan_greedy(sz, w)
                    c = makespan_greedy(tr, w)
                    row[f"cv_none_w{w}"] = float(np.std(a) / np.mean(a))
                    row[f"cv_retry_w{w}"] = float(np.std(c) / np.mean(c))
                    row[f"mean_over_none_w{w}"] = float(c.mean() / a.mean())
                    row[f"p95_over_p50_retry_w{w}"] = float(np.quantile(c, .95) / np.quantile(c, .5))
                row["cv_retry_ratio_w64_vs_w1"] = row["cv_retry_w64"] / row["cv_retry_w1"]
                row["cv_retry_over_none_w64"] = row["cv_retry_w64"] / row["cv_none_w64"]
                row["cv_retry_over_none_w1"] = row["cv_retry_w1"] / row["cv_none_w1"]
                grows.append(row)
    grid = pd.DataFrame(grows).round(4)
    grid.to_csv(RES / "grid.csv", index=False)

    # 確かめ2：② のあける秒数×失敗の確率×大きさの散らばり（仕事400個、所 1・64、各300回）
    brng = np.random.default_rng(SEED + 2)
    brows = []
    for gb in [1.0, 3.0, 10.0]:
        for gp in [0.005, 0.02, 0.05]:
            for gs in [0.25, 0.5, 1.0]:
                sz, f, fr = draw(brng, GRID2_RUNS, n, gs, gp)
                tr = sz * (1 + fr.sum(2))
                row = {"backoff": gb, "p": gp, "sigma": gs}
                for w in [1, 64]:
                    a = makespan_greedy(sz, w)
                    c = makespan_greedy(tr, w)
                    d = np.array([makespan_backoff(sz[r], f[r], fr[r], w, gb) for r in range(GRID2_RUNS)])
                    row[f"cv_none_w{w}"] = float(np.std(a) / np.mean(a))
                    row[f"cv_now_w{w}"] = float(np.std(c) / np.mean(c))
                    row[f"cv_after_w{w}"] = float(np.std(d) / np.mean(d))
                    row[f"mean_over_none_now_w{w}"] = float(c.mean() / a.mean())
                    row[f"mean_over_none_after_w{w}"] = float(d.mean() / a.mean())
                brows.append(row)
    grid2 = pd.DataFrame(brows).round(4)
    grid2.to_csv(RES / "grid_backoff.csv", index=False)

    def g(rule, w, col):
        return float(base[(base.rule == rule) & (base.w == w)][col].iloc[0])

    main_json = {
        "setting": {**BASE, "ws": WS, "runs": RUNS, "job_mean_sec": 1.0},
        "check": check,
        "headline": {
            "cv_none_w1": g("none", 1, "cv"), "cv_none_w64": g("none", 64, "cv"),
            "cv_now_w1": g("retry_now", 1, "cv"), "cv_now_w64": g("retry_now", 64, "cv"),
            "cv_after_w1": g("retry_after_3s", 1, "cv"), "cv_after_w64": g("retry_after_3s", 64, "cv"),
            "mean_over_none_now_w1": g("retry_now", 1, "mean_over_none"),
            "mean_over_none_now_w64": g("retry_now", 64, "mean_over_none"),
            "mean_over_none_after_w1": g("retry_after_3s", 1, "mean_over_none"),
            "mean_over_none_after_w64": g("retry_after_3s", 64, "mean_over_none"),
        },
        "grid_range": {
            "cv_retry_ratio_w64_vs_w1": [float(grid.cv_retry_ratio_w64_vs_w1.min()), float(grid.cv_retry_ratio_w64_vs_w1.max())],
            "cv_retry_over_none_w64": [float(grid.cv_retry_over_none_w64.min()), float(grid.cv_retry_over_none_w64.max())],
            "cv_retry_over_none_w1": [float(grid.cv_retry_over_none_w1.min()), float(grid.cv_retry_over_none_w1.max())],
            "mean_over_none_w64": [float(grid.mean_over_none_w64.min()), float(grid.mean_over_none_w64.max())],
            "mean_over_none_w1": [float(grid.mean_over_none_w1.min()), float(grid.mean_over_none_w1.max())],
            "n_cv_w64_gt_w1": int((grid.cv_retry_w64 > grid.cv_retry_w1).sum()),
            "n_retry_cv_gt_none_w64": int((grid.cv_retry_w64 > grid.cv_none_w64).sum()),
        },
        "grid_backoff_range": {
            "mean_over_none_after_w64": [float(grid2.mean_over_none_after_w64.min()), float(grid2.mean_over_none_after_w64.max())],
            "mean_over_none_after_w1": [float(grid2.mean_over_none_after_w1.min()), float(grid2.mean_over_none_after_w1.max())],
            "cv_after_w64": [float(grid2.cv_after_w64.min()), float(grid2.cv_after_w64.max())],
            "cv_now_w64": [float(grid2.cv_now_w64.min()), float(grid2.cv_now_w64.max())],
            "n_after_cv_gt_now_w64": int((grid2.cv_after_w64 > grid2.cv_now_w64).sum()),
            "n_after_cv_gt_now_w1": int((grid2.cv_after_w1 > grid2.cv_now_w1).sum()),
            "after_minus_now_pt_w1": [round(float((grid2.mean_over_none_after_w1 - grid2.mean_over_none_now_w1).min() * 100), 2),
                                      round(float((grid2.mean_over_none_after_w1 - grid2.mean_over_none_now_w1).max() * 100), 2)],
            "after_minus_now_pt_w64": [round(float((grid2.mean_over_none_after_w64 - grid2.mean_over_none_now_w64).min() * 100), 2),
                                       round(float((grid2.mean_over_none_after_w64 - grid2.mean_over_none_now_w64).max() * 100), 2)],
        },
    }

    # 図1：ばらつき（変動係数）と W
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for rule, lab, c, m in [("none", "やり直しなし", GRAY, "o"), ("retry_now", "① すぐやり直す", BLUE, "s"),
                            ("retry_after_3s", "② 3秒あけてやり直す", ORANGE, "^")]:
        d = base[base.rule == rule]
        ax.plot(d.w, d.cv * 100, marker=m, color=c, label=lab)
    ax.set_xscale("log", base=2)
    ax.set_xticks(WS); ax.set_xticklabels([str(w) for w in WS])
    ax.set_ylim(0, None)
    ax.set_xlabel("同時に動かす数")
    ax.set_ylabel("全体の時間のばらつき（標準偏差÷平均、%）")
    ax.set_title("仕事400個・失敗2%：同時に動かす数と全体の時間のばらつき（1,000回）")
    ax.legend(frameon=False)
    save(fig, "a1278_cv_by_w.png", SRC)

    # 図2：W=64 と W=1 の全体の時間の分布（やり直しなしとの比）
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    for ax, w in zip(axes, [1, 64]):
        none, a, bb = store[w]
        bins = np.linspace(min(none.min(), a.min()) * 0.99, np.quantile(bb, 0.995), 40)
        ax.hist(none, bins=bins, color=GRAY, alpha=0.6, label="やり直しなし")
        ax.hist(a, bins=bins, histtype="step", color=BLUE, lw=1.6, label="① すぐ")
        ax.hist(bb, bins=bins, histtype="step", color=ORANGE, lw=1.6, label="② 3秒あけて")
        ax.set_title(f"同時に動かす数 {w}")
        ax.set_xlabel("全体の時間（秒）")
        ax.set_ylabel("回数（1,000回のうち）")
    axes[1].legend(frameon=False, fontsize=9)
    fig.suptitle("全体の時間の分布（仕事400個・失敗2%）", y=1.02)
    save(fig, "a1278_hist_w1_w64.png", SRC, y=-0.04)

    # 図3：② の確かめ27通り：やり直しなしより平均で延びた割合（所 1 と 64）
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    x = np.arange(len(grid2))
    ax.bar(x - 0.2, (grid2.mean_over_none_after_w1 - 1) * 100, 0.4, color=LIGHT, label="同時に動かす数 1")
    ax.bar(x + 0.2, (grid2.mean_over_none_after_w64 - 1) * 100, 0.4, color=ORANGE, label="同時に動かす数 64")
    ax.set_ylim(0, None)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r.backoff:g}秒/{r.p*100:g}%/{r.sigma:g}" for r in grid2.itertuples()], rotation=90, fontsize=7)
    ax.set_xlabel("あける秒数／失敗の確率／仕事の大きさの散らばり（仕事400個、各300回）")
    ax.set_ylabel("やり直しなしより延びた割合（平均、%）")
    ax.set_title("② あけてやり直す：27通りで全体の時間が延びた割合")
    ax.legend(frameon=False)
    save(fig, "a1278_grid_backoff.png", SRC, y=-0.2)

    main_json["run_sec_note"] = "所要は環境で変わる"
    with open(RES / "a1278_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)
    print(base.to_string())
    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
