"""1272 同時に動かす数を増やすと、1つしかない置き場所の取り合いで、速さはどこから伸びなくなり、下がることもあるのか？（架空のデータ）

架空のアプリの処理。仕事は4,000個。1つの仕事は「ほかと関係なく進む計算」のあとに
「1つしかない置き場所に書きこむ」部分がある。置き場所は同時に1つの仕事しか使えず、空くのを待つ（来た順）。
置き場所を受け渡すたびに、その時に待っている仕事の数 × h ミリ秒の手間がかかる（作成者が置いた決まり）。
同時に動かす数 n を1〜64に変え、全部の仕事が終わる時間を、実機ではなくシミュレーションで数える。
"""
import json
import time
import heapq
import bisect
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1272
SRC = "架空のアプリの処理のシミュレーション（作成者が乱数で作成、seed 1272）"
N_TASK = 4000
C_MEAN, S_MEAN, SIG = 9.0, 1.0, 0.5     # 計算・置き場所の平均（ミリ秒）、対数の標準偏差
H = 0.03                                # 受け渡しの手間（待っている仕事1つあたり、ミリ秒）
NS = [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 20, 24, 32, 40, 48, 64]
REPS = 20


def lognorm(rng, mean, sig, size):
    return mean * np.exp(rng.normal(-sig ** 2 / 2, sig, size))


def simulate(C, S, n, h):
    """戻り値：全体の時間、置き場所が使われていた割合、1つの仕事が待った時間の平均、受け渡しの手間の合計"""
    m = len(C)
    nxt = 0
    heap, pend = [], []
    for w in range(min(n, m)):
        a = C[nxt]
        heapq.heappush(heap, (a, nxt)); bisect.insort(pend, a); nxt += 1
    L = 0.0
    busy = wait = over = 0.0
    end_all = 0.0
    while heap:
        a, i = heapq.heappop(heap)
        pend.pop(bisect.bisect_left(pend, a))
        start = a if a > L else L
        q = bisect.bisect_right(pend, start)      # 受け渡しの時に待っているほかの仕事
        cost = S[i] + h * q
        end = start + cost
        busy += cost; wait += start - a; over += h * q
        L = end
        end_all = end
        if nxt < m:
            na = end + C[nxt]
            heapq.heappush(heap, (na, nxt)); bisect.insort(pend, na); nxt += 1
    return end_all, busy / end_all, wait / m, over


def curve(rng, ns, h, reps, n_task=N_TASK, c_mean=C_MEAN, s_mean=S_MEAN, sig=SIG):
    rows = []
    for r in range(reps):
        C = lognorm(rng, c_mean, sig, n_task)
        S = lognorm(rng, s_mean, sig, n_task)
        T1 = C.sum() + S.sum()
        ceil = T1 / S.sum()
        for n in ns:
            T, util, w, ov = simulate(C, S, n, h)
            rows.append({"rep": r, "n": n, "time_ms": T, "speedup": T1 / T, "lock_busy": util,
                         "wait_per_task_ms": w, "handoff_ms": ov, "ceiling": ceil,
                         "lock_share_1": S.sum() / T1})
    return pd.DataFrame(rows)


def summarize(df):
    g = df.groupby("n").agg(speedup=("speedup", "mean"), time_ms=("time_ms", "mean"),
                            lock_busy=("lock_busy", "mean"), wait_per_task_ms=("wait_per_task_ms", "mean"),
                            handoff_ms=("handoff_ms", "mean")).reset_index()
    return g


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base = curve(rng, NS, H, REPS)
    noh = curve(np.random.default_rng(SEED + 1), NS, 0.0, REPS)
    sb, s0 = summarize(base), summarize(noh)
    ceil = float(base["ceiling"].mean())
    share1 = float(base["lock_share_1"].mean())
    tab = pd.DataFrame({"n": sb["n"],
                        "speedup_with_handoff": sb["speedup"].round(3),
                        "speedup_no_handoff": s0["speedup"].round(3),
                        "speedup_serial_part_formula": (sb["n"] / (1 + share1 * (sb["n"] - 1))).round(3),
                        "lock_busy_share": sb["lock_busy"].round(4),
                        "wait_per_task_ms": sb["wait_per_task_ms"].round(3),
                        "handoff_share_of_lock": (sb["handoff_ms"] / (sb["lock_busy"] * sb["time_ms"])).round(4),
                        "time_s": (sb["time_ms"] / 1000).round(3)})
    tab.to_csv(RES / "speedup_by_n.csv", index=False)
    pk = int(tab.loc[tab["speedup_with_handoff"].idxmax(), "n"])
    pk_val = float(tab["speedup_with_handoff"].max())
    at64 = float(tab.loc[tab.n == 64, "speedup_with_handoff"].iloc[0])
    no64 = float(tab.loc[tab.n == 64, "speedup_no_handoff"].iloc[0])
    # 回ごとの山の位置
    per = base.loc[base.groupby("rep")["speedup"].idxmax(), ["rep", "n", "speedup"]]
    # 確かめ：置き場所の割合 × 手間 × 計算のばらつき
    grid = []
    rg = np.random.default_rng(SEED + 2)
    gns = [1, 2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64]
    for share in [0.05, 0.1, 0.2]:
        for h in [0.0, 0.01, 0.03, 0.1]:
            for sig in [0.25, 0.5, 1.0]:
                s_mean = 10.0 * share
                df = curve(rg, gns, h, 3, n_task=2000, c_mean=10.0 - s_mean, s_mean=s_mean, sig=sig)
                g = summarize(df)
                i = g["speedup"].idxmax()
                sp8 = float(g.loc[g.n == 8, "speedup"].iloc[0])
                grid.append({"lock_share": share, "handoff_ms": h, "sigma": sig,
                             "ceiling_formula": round(float(df["ceiling"].mean()), 3),
                             "peak_n": int(g.loc[i, "n"]), "peak_speedup": round(float(g.loc[i, "speedup"]), 3),
                             "knee_n_95pct": int(g.loc[g["speedup"] >= 0.95 * g["speedup"].max(), "n"].min()),
                             "speedup_8": round(sp8, 3),
                             "formula_8": round(8 / (1 + share * 7), 3),
                             "speedup_64": round(float(g.loc[g.n == 64, "speedup"].iloc[0]), 3),
                             "drop_64_vs_peak": round(1 - float(g.loc[g.n == 64, "speedup"].iloc[0]) / float(g.loc[i, "speedup"]), 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gh = grid[grid.handoff_ms > 0]
    g0 = grid[grid.handoff_ms == 0]
    # データ：1回分の仕事
    r1 = np.random.default_rng(SEED + 3)
    C = lognorm(r1, C_MEAN, SIG, N_TASK); S = lognorm(r1, S_MEAN, SIG, N_TASK)
    pd.DataFrame({"task_id": np.arange(N_TASK), "compute_ms": C.round(4), "shared_ms": S.round(4)}).to_csv(
        DATA / "tasks_example.csv", index=False)
    res = {
        "setting": {"tasks": N_TASK, "compute_mean_ms": C_MEAN, "shared_mean_ms": S_MEAN, "sigma_log": SIG,
                    "handoff_ms_per_waiting": H, "reps": REPS},
        "lock_share_at_1": round(share1, 4),
        "ceiling_formula": round(ceil, 3),
        "peak_n": pk, "peak_speedup": round(pk_val, 3),
        "peak_n_per_rep_range": [int(per.n.min()), int(per.n.max())],
        "speedup_64_with_handoff": round(at64, 3), "drop_64_vs_peak": round(1 - at64 / pk_val, 4),
        "speedup_64_no_handoff": round(no64, 3),
        "row": {int(r.n): {"with": r.speedup_with_handoff, "no": r.speedup_no_handoff,
                           "formula": r.speedup_serial_part_formula, "busy": r.lock_busy_share,
                           "wait": r.wait_per_task_ms, "handoff_share": r.handoff_share_of_lock}
                for r in tab.itertuples()},
        "grid": {"configs": len(grid), "with_handoff_configs": len(gh),
                 "peak_n_range_with_handoff": [int(gh.peak_n.min()), int(gh.peak_n.max())],
                 "drop_64_range_with_handoff": [float(gh.drop_64_vs_peak.min()), float(gh.drop_64_vs_peak.max())],
                 "peak_over_ceiling_with_handoff": [round(float((gh.peak_speedup / gh.ceiling_formula).min()), 4),
                                                    round(float((gh.peak_speedup / gh.ceiling_formula).max()), 4)],
                 "no_handoff_64_over_ceiling": [round(float((g0.speedup_64 / g0.ceiling_formula).min()), 4),
                                                round(float((g0.speedup_64 / g0.ceiling_formula).max()), 4)],
                 "no_handoff_drop_max": float(g0.drop_64_vs_peak.max()),
                 "knee_n_range_no_handoff": [int(g0.knee_n_95pct.min()), int(g0.knee_n_95pct.max())],
                 "sim8_over_formula8": [round(float((grid.speedup_8 / grid.formula_8).min()), 4),
                                        round(float((grid.speedup_8 / grid.formula_8).max()), 4)],
                 "configs_sim8_above_formula": int((grid.speedup_8 > grid.formula_8).sum())},
    }
    figs(tab, ceil, grid)
    with open(RES / "a1272_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:3000])
    print("sec", round(time.time() - t0, 1))


def figs(tab, ceil, grid):
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.plot(tab.n, tab.n, color=GRAY, lw=1, ls=":", label="数どおり（n倍）")
    ax.plot(tab.n, tab.speedup_no_handoff, color=BLUE, marker="o", ms=3.5, label="受け渡しの手間なし")
    ax.plot(tab.n, tab.speedup_with_handoff, color=ORANGE, marker="o", ms=3.5, label="受け渡しの手間あり（待つ数×0.03ミリ秒）")
    ax.plot(tab.n, tab.speedup_serial_part_formula, color=GREEN, lw=1.2, ls="--", label="分けられない部分9.97%の式で見込んだ値")
    ax.axhline(ceil, color=INK, lw=0.8, ls="--")
    ax.text(64, ceil + 0.3, f"天井 {ceil:.3f}倍（式どおり）", ha="right", fontsize=9)
    ax.set_ylim(0, 16); ax.set_xlim(0, 66)
    ax.set_xlabel("同時に動かす数"); ax.set_ylabel("1つで動かしたときの何倍速いか")
    ax.set_title("置き場所が1つだと、速さは10倍前後で止まり、手間があると下がった")
    ax.legend(fontsize=8.5, loc="upper left", frameon=False)
    save(fig, "a1272_speedup.png", SRC + "。20回の平均")

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(tab.n.astype(str), tab.lock_busy_share * 100, color=LIGHT, label="置き場所が使われていた時間の割合")
    ax.set_ylim(0, 105); ax.set_ylabel("割合（%）"); ax.set_xlabel("同時に動かす数")
    ax2 = ax.twinx()
    ax2.plot(tab.n.astype(str), tab.wait_per_task_ms, color=ORANGE, marker="o", ms=3.5, label="1つの仕事が置き場所を待った時間")
    ax2.set_ylim(0, max(tab.wait_per_task_ms) * 1.15); ax2.set_ylabel("待った時間（ミリ秒、平均）")
    ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper left", frameon=False)
    ax.set_title("置き場所が埋まりきったあとは、増やした分が待ち時間になった（手間あり）")
    save(fig, "a1272_busy_wait.png", SRC + "。20回の平均")

    fig, axs = plt.subplots(1, 3, figsize=(9.8, 3.9), sharey=True)
    for ax, share in zip(axs, [0.05, 0.1, 0.2]):
        sub = grid[(grid.lock_share == share) & (grid.sigma == 0.5)].reset_index(drop=True)
        x = np.arange(len(sub))
        ax.bar(x - 0.2, sub.peak_speedup, 0.4, color=BLUE, label="いちばん出た速さ")
        ax.bar(x + 0.2, sub.speedup_64, 0.4, color=ORANGE, label="64で動かしたとき")
        for i, r in sub.iterrows():
            ax.text(i - 0.2, r.peak_speedup + 0.3, f"{r.peak_speedup:.3f}", ha="center", va="bottom", fontsize=7.5, rotation=90)
            ax.text(i + 0.2, r.speedup_64 + 0.3, f"{r.speedup_64:.3f}", ha="center", va="bottom", fontsize=7.5, rotation=90)
        ax.set_xticks(x); ax.set_xticklabels([str(h) for h in sub.handoff_ms])
        ax.set_title(f"置き場所の割合 {int(share*100)}%（天井 約{1/share:.0f}倍）", fontsize=10)
        ax.set_xlabel("受け渡しの手間（ミリ秒）")
    axs[0].set_ylabel("1つで動かしたときの何倍速いか")
    axs[0].set_ylim(0, 26)
    axs[0].legend(fontsize=8.5, frameon=False, loc="upper right")
    fig.suptitle("受け渡しの手間があると、64で動かした速さは山より下がった（計算のばらつき0.5）", fontsize=11.5, y=1.03)
    save(fig, "a1272_peak_grid.png", SRC + "。各3回の平均。同時に動かす数は1〜64の13通りから選んだ")


if __name__ == "__main__":
    main()
