"""1061 同じ設定のつもりの2台で、速さはどれだけ違うのか？（架空のデータ）

架空のサーバー200台（同じ設定のつもり）。台ごとに見えない速さの違い（作成者が置いた「台の係数」）があり、
1割の台は理由の分からない遅さ（+15%）を持つ。測るたびの揺れ（回の係数）と1件ごとの揺れも置いた。
応答時間はすべて置いた分布からの乱数で、実機の計測はしていない。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1061
SRC = "架空のサーバーの応答時間（作成者が置いた分布からの乱数、seed 1061）"
BASE = {"machine_sd": 0.04, "odd_share": 0.10, "odd_slow": 0.15, "run_sd": 0.03}
N_MACHINE = 200
N_REQ = 500            # 1回の計測の件数
REQ_MED, REQ_SD = 50.0, 0.4
T_CRIT = 2.101         # t分布（自由度18）の両側5%の値：10回ずつ測って比べるとき


def machines(rng, n, machine_sd=0.04, odd_share=0.10, odd_slow=0.15, **_):
    odd = rng.random(n) < odd_share
    return np.exp(rng.normal(0, machine_sd, n)) * np.where(odd, 1 + odd_slow, 1.0), odd


def run_means(rng, factor, k, run_sd=0.03, **_):
    """台の係数 factor（形 (...)）で k 回測った、1回ごとの平均の応答時間（ms）。1回は N_REQ 件"""
    shape = np.shape(factor) + (k,)
    runf = np.exp(rng.normal(0, run_sd, shape))
    # 1回 N_REQ 件の対数正規の平均：件ごとの揺れは平均を取ると小さくなるので、平均の分布を直接引く
    m = REQ_MED * np.exp(REQ_SD ** 2 / 2)
    sd_mean = m * np.sqrt(np.exp(REQ_SD ** 2) - 1) / np.sqrt(N_REQ)
    return np.asarray(factor)[..., None] * runf * (m + sd_mean * rng.standard_normal(shape))


def welch_t(x, y):
    return (x.mean(-1) - y.mean(-1)) / np.sqrt(x.var(-1, ddof=1) / x.shape[-1] + y.var(-1, ddof=1) / y.shape[-1])


def evaluate(rng, kw, n_pair=20000):
    f, odd = machines(rng, N_MACHINE, **kw)
    i = rng.integers(0, N_MACHINE, n_pair)
    j = (i + rng.integers(1, N_MACHINE, n_pair)) % N_MACHINE       # 別の台
    true_ratio = f[j] / f[i]
    res = {"true_abs_median_pct": 100 * np.median(np.abs(true_ratio - 1)),
           "true_ge5_pct": 100 * (np.abs(true_ratio - 1) >= 0.05).mean(),
           "true_ge10_pct": 100 * (np.abs(true_ratio - 1) >= 0.10).mean(),
           "fleet_slowest_vs_fastest_pct": 100 * (f.max() / f.min() - 1)}
    # 1回ずつ・k回ずつ測ったときの見かけの差
    for k in (1, 3, 10, 30):
        a = run_means(rng, f[i], k, **kw).mean(-1)
        b = run_means(rng, f[j], k, **kw).mean(-1)
        app = b / a
        res[f"app_k{k}_abs_median_pct"] = 100 * np.median(np.abs(app - 1))
        res[f"app_k{k}_ge5_pct"] = 100 * (np.abs(app - 1) >= 0.05).mean()
        res[f"app_k{k}_err_vs_true_median_pct"] = 100 * np.median(np.abs(app / true_ratio - 1))
    # 効き目のない変更を試す（古い版と新しい版を10回ずつ）
    k = 10
    # ① 別の台で：古い版は台 i、新しい版は台 j
    x = run_means(rng, f[i], k, **kw); y = run_means(rng, f[j], k, **kw)
    t1 = welch_t(y, x)
    # ② 同じ台で交互に
    x2 = run_means(rng, f[i], k, **kw); y2 = run_means(rng, f[i], k, **kw)
    t2 = welch_t(y2, x2)
    # ③ 2台で入れかえる（どちらの版も両方の台で5回ずつ）
    x3 = np.concatenate([run_means(rng, f[i], 5, **kw), run_means(rng, f[j], 5, **kw)], -1)
    y3 = np.concatenate([run_means(rng, f[i], 5, **kw), run_means(rng, f[j], 5, **kw)], -1)
    t3 = welch_t(y3, x3)
    res.update({"null_diff_machine_sig_pct": 100 * (np.abs(t1) > T_CRIT).mean(),
                "null_diff_machine_ge5_pct": 100 * (np.abs(y.mean(-1) / x.mean(-1) - 1) >= 0.05).mean(),
                "null_same_machine_sig_pct": 100 * (np.abs(t2) > T_CRIT).mean(),
                "null_same_machine_ge5_pct": 100 * (np.abs(y2.mean(-1) / x2.mean(-1) - 1) >= 0.05).mean(),
                "null_swap_sig_pct": 100 * (np.abs(t3) > T_CRIT).mean()})
    # 本当に3%速くなる変更を、別の台で試すと「遅くなった」と見える割合
    y4 = run_means(rng, f[j] * 0.97, k, **kw)
    x4 = run_means(rng, f[i], k, **kw)
    y5 = run_means(rng, f[i] * 0.97, k, **kw)
    res.update({"true3_diff_machine_looks_slower_pct": 100 * (y4.mean(-1) > x4.mean(-1)).mean(),
                "true3_diff_machine_sig_slower_pct": 100 * (welch_t(y4, x4) > T_CRIT).mean(),
                "true3_same_machine_looks_slower_pct": 100 * (y5.mean(-1) > x.mean(-1)).mean()})
    return res, f, odd


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base, f, odd = evaluate(rng, BASE)
    base = {k: r(v, 2) for k, v in base.items()}

    # data：200台の台の係数と、1台あたり10回の計測の平均
    runs = run_means(rng, f, 10, **BASE)
    df = pd.DataFrame({"machine": [f"M{n:03d}" for n in range(1, N_MACHINE + 1)], "factor_set": f.round(4),
                       "odd": odd.astype(int)})
    for k in range(10):
        df[f"run{k + 1}_mean_ms"] = runs[:, k].round(3)
    df.to_csv(DATA / "machines_runs.csv", index=False)

    # 式どおりの確かめ：変わった台がなければ、2台の本当の差（対数）は標準偏差 √2×machine_sd の正規分布
    g = np.random.default_rng(SEED + 1)
    fz, _ = machines(g, 400000, machine_sd=0.04, odd_share=0.0)
    ratio = fz[1::2] / fz[::2]
    formula_check = {"sim_median_abs_log_pct": r(100 * np.median(np.abs(np.log(ratio))), 3),
                     "formula_median_abs_log_pct": r(100 * 0.6744898 * np.sqrt(2) * 0.04, 3)}

    # 置き方を変えた27通り
    grows = []
    n = 0
    for msd in (0.02, 0.04, 0.08):
        for rsd in (0.01, 0.03, 0.06):
            for osh in (0.0, 0.10, 0.20):
                kw = {"machine_sd": msd, "odd_share": osh, "odd_slow": 0.15, "run_sd": rsd}
                res, _, _ = evaluate(np.random.default_rng(SEED * 100 + n), kw, n_pair=5000); n += 1
                row = {"machine_sd": msd, "run_sd": rsd, "odd_share": osh}
                row.update({k: r(v, 2) for k, v in res.items()})
                grows.append(row)
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)

    ks = pd.DataFrame([{"runs_each": k, "apparent_abs_median_pct": base[f"app_k{k}_abs_median_pct"],
                        "apparent_ge5_pct": base[f"app_k{k}_ge5_pct"],
                        "error_vs_true_median_pct": base[f"app_k{k}_err_vs_true_median_pct"]} for k in (1, 3, 10, 30)])
    ks.to_csv(RES / "runs_each.csv", index=False)

    head = dict(base)
    head.update({
        "odd_machines": int(odd.sum()),
        "formula_check": formula_check,
        "grid_true_ge5_min": r(grid.true_ge5_pct.min(), 2), "grid_true_ge5_max": r(grid.true_ge5_pct.max(), 2),
        "grid_null_diff_machine_sig_min": r(grid.null_diff_machine_sig_pct.min(), 2),
        "grid_null_diff_machine_sig_max": r(grid.null_diff_machine_sig_pct.max(), 2),
        "grid_null_same_machine_sig_min": r(grid.null_same_machine_sig_pct.min(), 2),
        "grid_null_same_machine_sig_max": r(grid.null_same_machine_sig_pct.max(), 2),
        "grid_null_swap_sig_min": r(grid.null_swap_sig_pct.min(), 2),
        "grid_null_swap_sig_max": r(grid.null_swap_sig_pct.max(), 2),
        "grid_diff_gt_same_count": int((grid.null_diff_machine_sig_pct > grid.null_same_machine_sig_pct).sum()),
        "grid_true3_looks_slower_min": r(grid.true3_diff_machine_looks_slower_pct.min(), 2),
        "grid_true3_looks_slower_max": r(grid.true3_diff_machine_looks_slower_pct.max(), 2),
        "grid_k30_err_min": r(grid.app_k30_err_vs_true_median_pct.min(), 2),
        "grid_k30_err_max": r(grid.app_k30_err_vs_true_median_pct.max(), 2),
    })
    head["run_sec"] = r(time.time() - t0, 1)
    out = {"headline": {k: v for k, v in head.items() if k != "run_sec"}, "set": BASE,
           "n_machine": N_MACHINE, "n_req_per_run": N_REQ, "t_crit_df18": T_CRIT}
    json.dump(out, open(RES / "a1061_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：200台の台の係数（10回の平均で見た速さ）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    order = np.argsort(f)
    ax.bar(range(N_MACHINE), (f[order] - 1) * 100, color=np.where(odd[order], ORANGE, BLUE), width=1.0)
    ax.axhline(0, color=INK, lw=1)
    ax.set_xlabel("サーバー（置いた速さの順に200台）"); ax.set_ylabel("台の係数（ふつうより何%遅いか）")
    ax.set_xticks([])
    ax.text(5, (f.max() - 1) * 100 * 0.9, "オレンジ：理由の分からない遅さ（+15%）を置いた台", color=ORANGE, fontsize=9)
    ax.set_title("同じ設定のつもりの200台に置いた、見えない速さの違い")
    save(fig, "a1061_machines.png", SRC)

    # 図2：何回ずつ測っても、2台の差は0に近づかない
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.plot(ks.runs_each, ks.apparent_abs_median_pct, marker="o", color=BLUE, label="2台の見かけの差（中央値）")
    ax.plot(ks.runs_each, ks.error_vs_true_median_pct, marker="s", color=GRAY, label="見かけの差と、置いた台の差とのずれ（中央値）")
    ax.axhline(base["true_abs_median_pct"], color=ORANGE, ls="--", lw=1.2)
    ax.text(30, base["true_abs_median_pct"] - 0.2, f"置いた台の差（中央値） {base['true_abs_median_pct']:.2f}%",
            color=ORANGE, fontsize=9, ha="right", va="top")
    ax.set_xscale("log"); ax.set_xticks([1, 3, 10, 30]); ax.set_xticklabels(["1", "3", "10", "30"])
    ax.set_ylim(0, max(ks.apparent_abs_median_pct.max(), base["true_abs_median_pct"]) * 1.25)
    ax.set_xlabel("1台あたりの計測の回数（1回は500件）"); ax.set_ylabel("差の大きさ（%、2万組の中央値）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("何回測っても、2台の差は置いた台の差に近づくだけで0にはならない")
    save(fig, "a1061_runs.png", SRC)

    # 図3：効き目のない変更で「差がある」と出た割合（27通り）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs = np.arange(len(grid))
    ax.scatter(xs, grid.null_diff_machine_sig_pct, color=ORANGE, s=30, label="①別の台で古い版と新しい版を測る")
    ax.scatter(xs, grid.null_swap_sig_pct, color=GRAY, s=30, marker="^", label="③2台で版を入れかえる")
    ax.scatter(xs, grid.null_same_machine_sig_pct, color=BLUE, s=30, marker="s", label="②同じ台で測る")
    ax.axhline(5, color=INK, lw=1, ls="--"); ax.text(-0.5, 7.5, "本来の5%", ha="left", fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_xticks([4, 13, 22]); ax.set_xticklabels(["台の差 小(0.02)", "台の差 中(0.04)", "台の差 大(0.08)"])
    for x in (8.5, 17.5):
        ax.axvline(x, color=GRAY, lw=.6)
    ax.set_ylabel("「差がある」と出た割合（%）")
    ax.set_xlabel("区切りの中は、回の揺れ（0.01・0.03・0.06）ごとに、変わった台の割合（0・10・20%）の順", fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0.0, 1.0))
    ax.set_xlim(-1, 27)
    ax.set_title("効き目のない変更でも、別の台で比べると「差がある」と出やすい（27通り）")
    save(fig, "a1061_null.png", SRC)
    print(json.dumps(head, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
