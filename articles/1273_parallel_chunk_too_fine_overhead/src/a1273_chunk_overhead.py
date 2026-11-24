"""1273 仕事を細かく分けすぎると、分ける手間と渡す手間で、全体はどれだけ遅くなるのか？（架空のデータ）

架空のアプリの処理。決まった量の処理（10万件、1件の時間は平均0.1ミリ秒）を k 個のかたまりに分け、
n 個を同時に動かす。かたまりは1か所（分ける係）が順に作り、1つ作るのに d ミリ秒かかる（作り終えたものから渡せる）。
動かす側は、空いたら次のかたまりを取りにいき、受け取って返すのに1つあたり h ミリ秒かかる。
実機ではなく、すべてシミュレーションで数える。
"""
import json
import time
import heapq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1273
SRC = "架空のアプリの処理のシミュレーション（作成者が乱数で作成、seed 1273）"
ITEMS = 100_000
ITEM_MEAN, SIG = 0.1, 1.0
N, D, H = 8, 0.02, 0.05
KS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 100000]
KS_GRID = [1, 4, 16, 64, 256, 1024, 4096, 16384, 50000, 100000]
REPS = 5


def items(rng):
    return ITEM_MEAN * np.exp(rng.normal(-SIG ** 2 / 2, SIG, ITEMS))


def simulate(x, k, n, d, h):
    bounds = np.linspace(0, len(x), k + 1).astype(int)
    work = np.add.reduceat(x, bounds[:-1])
    ready = d * np.arange(1, k + 1)
    if k <= n:
        fin = ready + h + work
        return float(fin.max())
    free = [0.0] * n
    heapq.heapify(free)
    w = (work + h).tolist(); r = ready.tolist()
    end = 0.0
    for j in range(k):
        f = heapq.heappop(free)
        s = f if f > r[j] else r[j]
        e = s + w[j]
        heapq.heappush(free, e)
    return float(max(free))


def curve(x, ks, n, d, h):
    W = float(x.sum())
    out = []
    for k in ks:
        T = simulate(x, k, n, d, h)
        out.append({"k": k, "time_ms": T, "work_per_worker_ms": W / n, "handoff_per_worker_ms": k * h / n,
                    "split_serial_ms": k * d, "lower_bound_ms": max(W / n + k * h / n, k * d)})
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    xs = [items(rng) for _ in range(REPS)]
    W = float(np.mean([x.sum() for x in xs]))
    # 基本：n=8
    rows = []
    for r, x in enumerate(xs):
        for c in curve(x, KS, N, D, H):
            c["rep"] = r; rows.append(c)
    df = pd.DataFrame(rows)
    tab = df.groupby("k").mean(numeric_only=True).reset_index().drop(columns="rep")
    best_i = tab.time_ms.idxmin()
    best_k, best_t = int(tab.k[best_i]), float(tab.time_ms[best_i])
    tab["vs_best"] = tab.time_ms / best_t
    tab["overhead_total_share"] = tab.k * (D + H) / W
    tab["worker_side_ms"] = tab.work_per_worker_ms + tab.handoff_per_worker_ms
    out = tab.round({"time_ms": 2, "work_per_worker_ms": 2, "handoff_per_worker_ms": 2, "split_serial_ms": 2,
                     "lower_bound_ms": 2, "worker_side_ms": 2, "vs_best": 4, "overhead_total_share": 4})
    out.to_csv(RES / "time_by_chunks_n8.csv", index=False)
    # 同時に動かす数を変える
    nrows = []
    for n in [1, 2, 4, 8, 16, 32, 64]:
        for r, x in enumerate(xs[:3]):
            for c in curve(x, KS, n, D, H):
                c["rep"] = r; c["n"] = n; nrows.append(c)
    nd = pd.DataFrame(nrows).groupby(["n", "k"]).time_ms.mean().reset_index()
    t1 = float(nd[(nd.n == 1)].time_ms.min())
    nsum = []
    for n, g in nd.groupby("n"):
        g = g.reset_index(drop=True)
        i = g.time_ms.idxmin()
        fin = float(g[g.k == 100000].time_ms.iloc[0])
        kn = float(g[g.k == min(KS, key=lambda v: abs(v - n))].time_ms.iloc[0])
        nsum.append({"n": n, "best_k": int(g.k[i]), "best_time_ms": round(float(g.time_ms[i]), 2),
                     "finest_time_ms": round(fin, 2), "finest_vs_best": round(fin / float(g.time_ms[i]), 4),
                     "speedup_best": round(t1 / float(g.time_ms[i]), 3), "speedup_finest": round(t1 / fin, 3),
                     "overhead_share_formula_finest": round(100000 * (D + H) / W, 4)})
    nsum = pd.DataFrame(nsum)
    nsum.to_csv(RES / "by_workers.csv", index=False)
    nd.round(2).to_csv(RES / "time_by_workers_chunks.csv", index=False)
    # 確かめ：27通り
    grid = []
    x0 = xs[0]; x1 = xs[1]
    for n in [4, 16, 64]:
        for d in [0.005, 0.02, 0.05]:
            for h in [0.01, 0.05, 0.2]:
                ts = np.mean([[simulate(x, k, n, d, h) for k in KS_GRID] for x in (x0, x1)], axis=0)
                i = int(np.argmin(ts))
                grid.append({"n": n, "split_ms": d, "handoff_ms": h, "best_k": KS_GRID[i],
                             "best_time_ms": round(float(ts[i]), 2),
                             "chunks_per_worker_best": round(KS_GRID[i] / n, 2),
                             "finest_vs_best": round(float(ts[-1] / ts[i]), 4),
                             "k16384_vs_best": round(float(ts[KS_GRID.index(16384)] / ts[i]), 4),
                             "split_bound_finest": bool(100000 * d > (x0.sum() + 100000 * h) / n)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    # データ：1回分の件（先頭2万件）
    pd.DataFrame({"item_id": np.arange(20000), "item_ms": xs[0][:20000].round(5)}).to_csv(DATA / "items_head.csv", index=False)
    row = lambda k: out[out.k == k].iloc[0]
    mid = out[(out.k >= 8) & (out.k <= 4096)]
    res = {
        "setting": {"items": ITEMS, "item_mean_ms": ITEM_MEAN, "sigma_log": SIG, "workers": N,
                    "split_ms_per_chunk": D, "handoff_ms_per_chunk": H, "reps": REPS},
        "total_work_ms": round(W, 2), "ideal_ms_n8": round(W / N, 2),
        "best_k": best_k, "best_time_ms": round(best_t, 2),
        "vs_best_max_k8_to_4096": float(mid.vs_best.max()),
        "k": {int(k): {"time_ms": float(row(k).time_ms), "vs_best": float(row(k).vs_best)}
              for k in [1, 4, 8, 64, 1024, 8192, 16384, 32768, 65536, 100000]},
        "finest_overhead_total_share": float(row(100000).overhead_total_share),
        "finest_split_serial_ms": float(row(100000).split_serial_ms),
        "finest_worker_side_ms": round(float(row(100000).work_per_worker_ms + row(100000).handoff_per_worker_ms), 2),
        "by_workers": nsum.to_dict(orient="records"),
        "grid": {"configs": len(grid),
                 "finest_vs_best_range": [float(grid.finest_vs_best.min()), float(grid.finest_vs_best.max())],
                 "k16384_vs_best_range": [float(grid.k16384_vs_best.min()), float(grid.k16384_vs_best.max())],
                 "best_k_values": sorted(set(int(v) for v in grid.best_k)),
                 "chunks_per_worker_best_range": [float(grid.chunks_per_worker_best.min()), float(grid.chunks_per_worker_best.max())],
                 "split_bound_finest_configs": int(grid.split_bound_finest.sum()),
                 "finest_vs_best_by_n": {int(n): [float(g.finest_vs_best.min()), float(g.finest_vs_best.max())] for n, g in grid.groupby("n")}},
    }
    with open(RES / "a1273_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    figs(out, nd, nsum, W)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    print("sec", round(time.time() - t0, 1))


def figs(out, nd, nsum, W):
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.plot(out.k, out.time_ms, color=ORANGE, marker="o", ms=3.5, label="全体の時間（シミュレーション）")
    ax.plot(out.k, out.work_per_worker_ms + out.handoff_per_worker_ms, color=BLUE, ls="--", lw=1.2,
            label="動かす側：処理÷8＋渡す手間÷8（式）")
    ax.plot(out.k, out.split_serial_ms, color=GREEN, ls="--", lw=1.2, label="分ける係：かたまりの数×0.02ミリ秒（式）")
    ax.set_xscale("log"); ax.set_ylim(0, 3000)
    ax.set_xlabel("かたまりの数（対数の目盛り）"); ax.set_ylabel("全部が終わるまでの時間（ミリ秒）")
    ax.set_title("同時に8つ：分けすぎると、渡す手間と分ける係の手間で遅くなった")
    ax.legend(fontsize=8.5, frameon=False, loc="upper center")
    save(fig, "a1273_time_by_chunks.png", SRC + "。5回の平均。かたまりが8より少ないと空いた所が出て遅い（左端は図の外）")

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    x = np.arange(len(nsum))
    ax.bar(x - 0.2, nsum.speedup_best, 0.4, color=BLUE, label="いちばん速い分け方")
    ax.bar(x + 0.2, nsum.speedup_finest, 0.4, color=ORANGE, label="1件ずつ（10万個）に分けたとき")
    for i, r in nsum.iterrows():
        ax.text(i - 0.2, r.speedup_best + 0.5, f"{r.speedup_best:.3f}", ha="center", va="bottom", fontsize=7.5, rotation=90)
        ax.text(i + 0.2, r.speedup_finest + 0.5, f"{r.speedup_finest:.3f}", ha="center", va="bottom", fontsize=7.5, rotation=90)
    ax.set_xticks(x); ax.set_xticklabels(nsum.n.astype(str))
    ax.set_xlabel("同時に動かす数"); ax.set_ylabel("1つで動かした最速の何倍速いか")
    ax.set_ylim(0, 75)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    ax.set_title("1件ずつに分けると、同時に動かす数を増やしても5倍ほどで止まった")
    save(fig, "a1273_speedup_by_workers.png", SRC + "。3回の平均")

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    cols = {1: GRAY, 8: ORANGE, 32: BLUE, 64: GREEN}
    for n, c in cols.items():
        g = nd[nd.n == n]
        ax.plot(g.k, g.time_ms / g.time_ms.min(), color=c, marker="o", ms=3, label=f"同時に{n}")
    ax.set_xscale("log"); ax.set_ylim(0, 14); ax.axhline(1, color=INK, lw=0.6)
    ax.set_xlabel("かたまりの数（対数の目盛り）"); ax.set_ylabel("いちばん速い分け方の何倍かかったか")
    ax.set_title("同時に動かす数が多いほど、分けすぎたときの遅れが大きかった")
    ax.legend(fontsize=8.5, frameon=False, loc="center", ncol=2)
    save(fig, "a1273_ratio_by_workers.png", SRC + "。3回の平均。かたまりが同時に動かす数より少ないと、空いた所が出て左側も上がる")


if __name__ == "__main__":
    main()
