"""1275 「何倍速くなったか」は、1つで動かしたときの何と比べるかで、どれだけ違って見えるのか？（並列処理）

作成者が置いた架空のアプリの処理（仕事4,000個）をシミュレーションする。実機の計測はしていない。
3つの物差し（1つで動かしたとき）と、同時に動かす版の時間を比べる。
"""
import json
import heapq
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1275
SRC = "架空のアプリの処理（作成者が乱数で作成、seed 1275）。実機の計測ではなくシミュレーション"
N_TASK = 4000
MEAN_T = 0.002          # 1つの仕事の平均（秒）
SIGMA_T = 0.5           # 仕事の時間の散らばり（対数の標準偏差）
READ = 0.4              # どの版にもある、分けられない読み込み（秒）
H = 0.0002              # 同時に動かす版で、1つの仕事を渡す手間（秒）
U = 0.2                 # 同時に動かす版で、動かし始めと集める手間（秒、1回の処理に1度）
G = 1.5                 # 古い版の1つの仕事の時間は、今の G 倍
RUN_SD = 0.02           # 回ごとの振れ（対数の標準偏差、全体に掛ける）
N_RUN = 20
PS = [1, 2, 4, 8, 16]


def makespan(times, p):
    """終わった所が次の仕事を取りにいく形で、p 個が全部を終えるまでの時間"""
    if p == 1:
        return float(times.sum())
    free = [0.0] * p
    heapq.heapify(free)
    for t in times:
        f = heapq.heappop(free)
        heapq.heappush(free, f + t)
    return max(free)


def versions(t, h, u, g, read):
    """振れのない各版の時間（秒）"""
    out = {"old": read + g * t.sum(), "serial": read + t.sum()}
    for p in PS:
        out[f"par{p}"] = read + u + makespan(t + h, p)
    return out


def with_noise(rng, base, n):
    return {k: v * np.exp(rng.normal(0, RUN_SD, n)) for k, v in base.items()}


def main():
    rng = np.random.default_rng(SEED)
    mu = np.log(MEAN_T) - SIGMA_T ** 2 / 2
    t = rng.lognormal(mu, SIGMA_T, N_TASK)
    pd.DataFrame({"task_id": np.arange(1, N_TASK + 1), "time_ms": np.round(t * 1000, 4)}).to_csv(
        DATA / "tasks.csv", index=False)

    base = versions(t, H, U, G, READ)
    runs = with_noise(rng, base, N_RUN)
    med = {k: float(np.median(v)) for k, v in runs.items()}
    pd.DataFrame({k: np.round(v, 4) for k, v in runs.items()}).assign(run=np.arange(1, N_RUN + 1)).to_csv(
        DATA / "runs_base.csv", index=False)

    rows = []
    for p in PS:
        tp = med[f"par{p}"]
        rows.append({"p": p, "time_sec": round(tp, 4),
                     "vs_par1": round(med["par1"] / tp, 4),
                     "vs_serial": round(med["serial"] / tp, 4),
                     "vs_old": round(med["old"] / tp, 4)})
    speed = pd.DataFrame(rows)
    speed.to_csv(RES / "speedup_base.csv", index=False)

    # 1回ずつの組で比べたときの幅（8つ、20回×20回の組）
    single = {}
    for key in ["par1", "serial", "old"]:
        r = (runs[key][:, None] / runs["par8"][None, :]).ravel()
        single[key] = [round(float(np.quantile(r, 0.1)), 4), round(float(np.quantile(r, 0.9)), 4)]

    # 確かめ（振れなし）：渡す手間 × 始めの手間 × 古い版の倍率 × 読み込み
    grid = []
    for h, u, g, rd in itertools.product([0.0, 0.0001, 0.0002, 0.0004], [0.0, 0.2, 0.6], [1.0, 1.5, 2.0], [0.0, 0.4]):
        b = versions(t, h, u, g, rd)
        m = b  # 確かめは回ごとの振れを入れない値で比べる
        t8 = m["par8"]
        grid.append({"hand_ms": h * 1000, "start_sec": u, "old_factor": g, "read_sec": rd,
                     "vs_par1_p8": round(m["par1"] / t8, 4), "vs_serial_p8": round(m["serial"] / t8, 4),
                     "vs_old_p8": round(m["old"] / t8, 4),
                     "old_over_serial_view": round(m["old"] / m["serial"], 4),
                     "par1_over_serial_view": round(m["par1"] / m["serial"], 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    s8 = speed[speed.p == 8].iloc[0]
    g_no_over = grid[(grid.hand_ms == 0) & (grid.start_sec == 0)]
    main_json = {
        "settings": {"n_task": N_TASK, "mean_task_ms": MEAN_T * 1000, "sigma_log": SIGMA_T, "read_sec": READ,
                     "hand_ms": H * 1000, "start_sec": U, "old_factor": G, "run_sd_log": RUN_SD, "n_run": N_RUN},
        "task_total_sec": round(float(t.sum()), 4),
        "median_time_sec": {k: round(v, 4) for k, v in med.items()},
        "p8": {"vs_par1": s8.vs_par1, "vs_serial": s8.vs_serial, "vs_old": s8.vs_old,
               "old_over_serial": round(s8.vs_old / s8.vs_serial, 4),
               "par1_over_serial": round(s8.vs_par1 / s8.vs_serial, 4)},
        "p8_single_run_pairs_10_90": single,
        "p16": speed[speed.p == 16].iloc[0][["vs_par1", "vs_serial", "vs_old"]].to_dict(),
        "grid": {"n": len(grid),
                 "vs_par1_range": [grid.vs_par1_p8.min(), grid.vs_par1_p8.max()],
                 "vs_serial_range": [grid.vs_serial_p8.min(), grid.vs_serial_p8.max()],
                 "vs_old_range": [grid.vs_old_p8.min(), grid.vs_old_p8.max()],
                 "max_over_min_per_setting": [round(float((grid[["vs_par1_p8", "vs_serial_p8", "vs_old_p8"]].max(axis=1) /
                                                           grid[["vs_par1_p8", "vs_serial_p8", "vs_old_p8"]].min(axis=1)).min()), 4),
                                              round(float((grid[["vs_par1_p8", "vs_serial_p8", "vs_old_p8"]].max(axis=1) /
                                                           grid[["vs_par1_p8", "vs_serial_p8", "vs_old_p8"]].min(axis=1)).max()), 4)],
                 "n_vs_old_over_8": int((grid.vs_old_p8 > 8).sum()),
                 "n_vs_serial_over_8": int((grid.vs_serial_p8 > 8).sum()),
                 "n_vs_par1_over_8": int((grid.vs_par1_p8 > 8).sum()),
                 "no_overhead_vs_serial_range": [g_no_over.vs_serial_p8.min(), g_no_over.vs_serial_p8.max()],
                 "no_overhead_par1_eq_serial_max_gap": round(float((g_no_over.vs_par1_p8 - g_no_over.vs_serial_p8).abs().max()), 4)},
    }
    main_json = json.loads(json.dumps(main_json, default=float))
    with open(RES / "a1275_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：8つで動かしたときの「何倍」
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = ["同時に動かす版を\n1つで動かした時間", "同時に動かさない\n今の版の時間", "手直し前の\n古い版の時間"]
    vals = [s8.vs_par1, s8.vs_serial, s8.vs_old]
    bars = ax.bar(labels, vals, color=[BLUE, GREEN, ORANGE], width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v:.4f}倍", ha="center", fontsize=10)
    ax.axhline(8, color=GRAY, ls="--", lw=1)
    ax.text(2.33, 8.1, "数どおりの8倍", color=GRAY, fontsize=9, ha="right", va="bottom")
    ax.set_ylim(0, 10)
    ax.set_ylabel("8つで動かした時間の何倍か（中央値どうし）")
    ax.set_title("同じ8つで動かした結果を、3つの物差しで割ると")
    save(fig, "a1275_p8_three.png", SRC + "。仕事4,000個、各20回の中央値")

    # 図2：数を変えたときの「何倍」
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for col, c, lab in [("vs_old", ORANGE, "古い版と比べる"), ("vs_par1", BLUE, "同時に動かす版を1つで"),
                        ("vs_serial", GREEN, "同時に動かさない今の版と比べる")]:
        ax.plot(speed.p, speed[col], "o-", color=c, label=lab)
    ax.plot(PS, PS, ls=":", color=GRAY, label="数どおり")
    ax.set_xscale("log", base=2)
    ax.set_xticks(PS)
    ax.set_xticklabels([str(p) for p in PS])
    ax.set_ylim(0, 17)
    ax.set_xlabel("同時に動かす数")
    ax.set_ylabel("何倍速くなったか")
    ax.set_title("同時に動かす数と「何倍」（物差しごと）")
    ax.legend(fontsize=9, frameon=False)
    save(fig, "a1275_by_p.png", SRC)

    # 図3：72通りの幅
    fig, ax = plt.subplots(figsize=(7, 4))
    cols = [("vs_par1_p8", BLUE, "同時に動かす版を\n1つで"), ("vs_serial_p8", GREEN, "同時に動かさない\n今の版"),
            ("vs_old_p8", ORANGE, "手直し前の\n古い版")]
    for i, (col, c, lab) in enumerate(cols):
        y = grid[col].values
        x = i + (np.random.default_rng(SEED + 9).random(len(y)) - 0.5) * 0.3
        ax.scatter(x, y, s=12, color=c, alpha=0.7)
    ax.set_xticks(range(3))
    ax.set_xticklabels([c[2] for c in cols])
    ax.axhline(8, color=GRAY, ls="--", lw=1)
    ax.set_ylim(0, max(17, grid.vs_old_p8.max() * 1.05))
    ax.set_ylabel("8つで動かしたときの何倍")
    ax.set_title(f"置き方を変えた{len(grid)}通り（点1つが1通り、回ごとの振れなし）")
    save(fig, "a1275_grid.png", SRC + "。渡す手間・始めの手間・古い版の倍率・読み込みを変えた")


if __name__ == "__main__":
    main()
