"""855 「9割終わった」から残りが長いのはなぜか？（架空のデータ）

架空のプロジェクト。作業100件を担当者 W 人で並行して進める。作業の長さは対数正規分布（平均3日、ばらつき sigma）。
作業は決まった順（乱数で並べた順）に、手の空いた人が次の1件を取る。
「9割終わった」＝作業の件数で90件が終わった時点。その時点から最後の作業が終わるまでの日数が、全体の日数の何%かを数える。
最後の点検で、終わった作業の一部に手直しが見つかる場合（手直しは元の作業の半分の長さ、計画の100件には入っていない）も数える。
"""
import json, heapq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 855
SRC = "架空のプロジェクトの作業（作成者が乱数で作成、seed 855）"
N_TASK, MEAN_DAYS = 100, 3.0
REPS = 2000


def durations(rng, n, sigma):
    if sigma == 0:
        return np.full(n, MEAN_DAYS)
    mu = np.log(MEAN_DAYS) - sigma ** 2 / 2  # 平均が3日になるように
    return rng.lognormal(mu, sigma, n)


def schedule(d, workers):
    """決まった順に、手の空いた人が次の作業を取る。各作業の (担当, 開始, 終了) を返す"""
    free = [(0.0, w) for w in range(workers)]
    heapq.heapify(free)
    who, st, en = np.zeros(len(d), int), np.zeros(len(d)), np.zeros(len(d))
    for i, x in enumerate(d):
        t, w = heapq.heappop(free)
        who[i], st[i], en[i] = w, t, t + x
        heapq.heappush(free, (t + x, w))
    return who, st, en


def run_once(rng, sigma, workers, rework=0.0):
    d = durations(rng, N_TASK, sigma)
    who, st, en = schedule(d, workers)
    t90 = np.sort(en)[int(N_TASK * 0.9) - 1]  # 90件目が終わった時点
    end_main = en.max()
    end = end_main
    if rework > 0:  # 最後の点検（全部終わった時点）で手直しが見つかる
        bad = rng.random(N_TASK) < rework
        if bad.any():
            _, _, e2 = schedule(d[bad] * 0.5, workers)
            end = end_main + e2.max()
    left = d[en > t90]  # 90件目の時点でまだ終わっていなかった作業の長さ
    return {"t90": t90, "end": end, "tail_share": (end - t90) / end, "naive_ratio": (end - t90) / (t90 / 9),
            "left_mean_len": float(left.mean()) if len(left) else np.nan, "all_mean_len": float(d.mean()),
            "busy_after90": float(((np.minimum(en, end_main) - np.maximum(st, t90)).clip(0).sum()) / max(end_main - t90, 1e-9))}


def summarize(rows):
    df = pd.DataFrame(rows)
    return {"tail_share_mean": round(float(df.tail_share.mean()), 3),
            "tail_share_p10": round(float(df.tail_share.quantile(.1)), 3),
            "tail_share_p90": round(float(df.tail_share.quantile(.9)), 3),
            "naive_ratio_median": round(float(df.naive_ratio.median()), 2),
            "left_len_ratio": round(float((df.left_mean_len / df.all_mean_len).mean()), 2),
            "busy_workers_after90": round(float(df.busy_after90.mean()), 2),
            "total_days_mean": round(float(df.end.mean()), 1)}


def main():
    rng = np.random.default_rng(SEED)

    # 1) 理由を1つずつ足していく
    steps = [("長さ同じ・1人", 0.0, 1, 0.0), ("長さ同じ・5人", 0.0, 5, 0.0), ("長さばらつく・1人", 0.8, 1, 0.0),
             ("長さばらつく・5人", 0.8, 5, 0.0), ("長さばらつく・5人＋最後に手直し15%", 0.8, 5, 0.15)]
    step_res = []
    for name, sg, w, rw in steps:
        s = summarize([run_once(rng, sg, w, rw) for _ in range(REPS)])
        step_res.append({"case": name, "sigma": sg, "workers": w, "rework": rw, **s})
    pd.DataFrame(step_res).to_csv(RES / "steps.csv", index=False)

    # 2) 確かめ：長さのばらつき × 人数（手直しなし、各1000回）
    grid = []
    for sg in [0.2, 0.5, 0.8, 1.2]:
        for w in [1, 3, 5, 10, 20]:
            s = summarize([run_once(rng, sg, w) for _ in range(1000)])
            grid.append({"sigma": sg, "workers": w, **s})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness_sigma_workers.csv", index=False)

    # 3) 確かめ：最後の手直しの割合（長さばらつく0.8・5人、各1000回）
    rwk = []
    for rw in [0.0, 0.1, 0.15, 0.2, 0.3]:
        s = summarize([run_once(rng, 0.8, 5, rw) for _ in range(1000)])
        rwk.append({"rework": rw, **s})
    rwk = pd.DataFrame(rwk)
    rwk.to_csv(RES / "robustness_rework.csv", index=False)

    # 1回分の作業の記録（長さばらつく0.8・5人）
    # 候補200回（seed 8550〜8749）のうち、残りの割合が候補の中央値にいちばん近い1回を使う
    cand = []
    for k in range(200):
        dd = durations(np.random.default_rng(SEED * 10 + k), N_TASK, 0.8)
        _, _, ee = schedule(dd, 5)
        t9 = np.sort(ee)[89]
        cand.append((ee.max() - t9) / ee.max())
    cand = np.array(cand)
    pick = int(np.argmin(np.abs(cand - np.median(cand))))
    d = durations(np.random.default_rng(SEED * 10 + pick), N_TASK, 0.8)
    who, st, en = schedule(d, 5)
    tasks = pd.DataFrame({"task_id": np.arange(1, N_TASK + 1), "days": d, "worker": who + 1, "start": st, "end": en})
    tasks.to_csv(DATA / "tasks.csv", index=False, float_format="%.3f")
    t90 = np.sort(en)[89]
    one = {"t90": round(float(t90), 1), "end": round(float(en.max()), 1),
           "tail_share": round(float((en.max() - t90) / en.max()), 3),
           "left_tasks": int((en > t90).sum()), "left_mean_len": round(float(d[en > t90].mean()), 2),
           "all_mean_len": round(float(d.mean()), 2), "longest_task": round(float(d.max()), 1),
           "picked_seed": SEED * 10 + pick, "candidates_median_tail_share": round(float(np.median(cand)), 3)}

    out = {"steps_2000reps": step_res, "robustness_sigma_workers": grid.to_dict("records"),
           "robustness_rework": rwk.to_dict("records"), "one_run": one}
    json.dump(out, open(RES / "a855_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の進み具合（件数の%）と、手の動いている人数
    ts = np.linspace(0, en.max(), 600)
    done = np.array([(en <= t).mean() * 100 for t in ts])
    busy = np.array([((st <= t) & (en > t)).sum() for t in ts])
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(ts, done, color=BLUE, lw=2, label="終わった作業の件数（%）")
    ax.axhline(90, color=GRAY, lw=.8, ls=":")
    ax.axvline(t90, color=ORANGE, lw=1, ls="--")
    ax.text(t90 - 0.8, 15, f"9割の時点\n{t90:.0f}日目", color=ORANGE, fontsize=9, ha="right")
    ax.set_xlabel("日数"); ax.set_ylabel("終わった作業の件数（%）"); ax.set_ylim(0, 105)
    ax2 = ax.twinx(); ax2.step(ts, busy, color=GREEN, lw=1, where="post", label="作業中の人数")
    ax2.set_ylim(0, 10); ax2.set_ylabel("作業中の人数（人）", color=GREEN); ax2.spines["right"].set_visible(True)
    ax.set_title(f"9割の時点から終わりまで{en.max()-t90:.0f}日（全体の{one['tail_share']*100:.0f}%）。終わり近くは人が余る")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="center right")
    save(fig, "a855_progress.png", SRC + "。作業100件・5人・長さのばらつき0.8。候補200回のうち残りの割合が中央値に近い1回")

    # 図2：理由を1つずつ足したときの残りの割合
    s = pd.DataFrame(step_res)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.barh(s.case[::-1], s.tail_share_mean[::-1] * 100, color=[ORANGE, BLUE, LIGHT, LIGHT, GRAY])
    for i, (v, a, b) in enumerate(zip(s.tail_share_mean[::-1] * 100, s.tail_share_p10[::-1] * 100, s.tail_share_p90[::-1] * 100)):
        ax.text(v + 0.8, i, f"{v:.0f}%（{a:.0f}〜{b:.0f}%）", va="center", fontsize=9)
    ax.axvline(10, color=GRAY, lw=.8, ls=":")
    ax.set_xlim(0, 40); ax.set_xlabel("9割の時点から後の日数が全体に占める割合（%、2,000回の平均。括弧は10〜90%）")
    ax.set_title("件数の残り1割に、日数は1割で済まない（並行と長さのばらつき）")
    save(fig, "a855_steps.png", SRC)

    # 図3：ばらつき×人数
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for sg, c in zip([0.2, 0.5, 0.8, 1.2], [GRAY, LIGHT, BLUE, INK]):
        g = grid[grid.sigma == sg]
        ax.plot(g.workers, g.tail_share_mean * 100, "o-", color=c, label=f"長さのばらつき {sg}")
    ax.axhline(10, color=GRAY, lw=.8, ls=":")
    ax.set_xscale("log"); ax.set_xticks([1, 3, 5, 10, 20]); ax.set_xticklabels(["1", "3", "5", "10", "20"])
    ax.set_xlabel("並行して進める人数（作業は100件）"); ax.set_ylabel("9割の時点から後の割合（%）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("人数が多く、作業の長さがばらつくほど、最後の1割が長い")
    save(fig, "a855_grid.png", SRC + "。各1,000回の平均、手直しなし")
    print("done")


if __name__ == "__main__":
    main()
