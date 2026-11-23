"""1059 サーバーごとの99パーセンタイルを平均すると、全体の99パーセンタイルになるのか？（架空のデータ）

架空のアプリの1時間分の応答時間（ミリ秒）。サーバー8台に処理が振り分けられ、7台はふつう、1台（H）だけ
遅い側の裾が長い。応答時間はサーバーごとに作成者が置いた対数正規分布からの乱数で、実機の計測はしていない。
サーバーごとの99パーセンタイルを平均した値と、全部の処理を合わせて数えた99パーセンタイルを比べる。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1059
SRC = "架空のアプリの応答時間（作成者が置いた分布からの乱数、seed 1059）"
Z99 = 2.3263479
N_HOUR = 100_000          # 1時間の処理の件数
N_REP = 200               # 1時間を作り直す回数
NAMES = list("ABCDEFGH")


def servers(n_srv=8, slow_sig=0.9, slow_load=1.0):
    """サーバーごとの中央値（ms）・対数の標準偏差・処理の割合。最後の1台が遅い側の裾が長いサーバー"""
    k = n_srv - 1
    med = list(np.linspace(38, 44, k)) + [55.0]
    sig = [0.45] * k + [slow_sig]
    w = np.array([1.0] * k + [slow_load])
    return np.array(med), np.array(sig), w / w.sum()


def ln_cdf(x, m, s):
    return 0.5 * (1 + math.erf((math.log(x) - math.log(m)) / (s * math.sqrt(2))))


def mix_cdf(x, med, sig, sh):
    return sum(w * ln_cdf(x, m, s) for m, s, w in zip(med, sig, sh))


def mix_q(q, med, sig, sh):
    lo, hi = 1e-3, 1e7
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if mix_cdf(mid, med, sig, sh) < q:
            lo = mid
        else:
            hi = mid
    return mid


def draw(rng, med, sig, sh, n=N_HOUR):
    srv = rng.choice(len(med), size=n, p=sh)
    ms = med[srv] * np.exp(rng.normal(0, 1, n) * sig[srv])
    return srv, ms


EDGES = 10 ** np.arange(0, 5.0001, 0.01)   # 1ms〜100,000ms を対数で 500 区切り（隣の区切りは約2.3%違い）


def hist_q(counts, q):
    c = np.cumsum(counts)
    i = int(np.searchsorted(c, q * c[-1]))
    return float(math.sqrt(EDGES[i] * EDGES[i + 1]))


def methods(srv, ms, n_srv):
    p99 = np.array([np.quantile(ms[srv == s], 0.99) for s in range(n_srv)])
    cnt = np.bincount(srv, minlength=n_srv)
    h = sum(np.histogram(ms[srv == s], EDGES)[0] for s in range(n_srv))  # サーバーごとの区切りの件数を足す
    return {"①サーバーの99%点の平均": float(p99.mean()),
            "②件数で重みを付けた平均": float((p99 * cnt).sum() / cnt.sum()),
            "③サーバーの99%点の中央値": float(np.median(p99)),
            "④サーバーの99%点の最大": float(p99.max()),
            "⑤全部の処理を合わせて数える": float(np.quantile(ms, 0.99)),
            "⑥区切りごとの件数を足し合わせる": hist_q(h, 0.99)}, p99, cnt


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    med, sig, sh = servers()
    true99 = mix_q(0.99, med, sig, sh)
    formula_p99 = med * np.exp(Z99 * sig)

    # 1) 1時間分（data に置く）
    srv, ms = draw(rng, med, sig, sh)
    pd.DataFrame({"request_id": np.arange(1, N_HOUR + 1), "server": np.array(NAMES)[srv],
                  "ms": np.round(ms, 2)}).to_csv(DATA / "requests_one_hour.csv", index=False)
    one, p99_one, cnt_one = methods(srv, ms, 8)
    per_server = pd.DataFrame({"server": NAMES, "median_ms_set": med, "log_sd_set": sig, "share_set": sh.round(4),
                               "count": cnt_one, "p99_ms": p99_one.round(2), "p99_formula_ms": formula_p99.round(2)})
    per_server.to_csv(RES / "per_server_one_hour.csv", index=False)

    # 2) 1時間を作り直して200回
    rows = []
    for rep in range(N_REP):
        g = np.random.default_rng(SEED * 1000 + rep)
        s_, m_ = draw(g, med, sig, sh)
        res, _, _ = methods(s_, m_, 8)
        for k, v in res.items():
            rows.append({"rep": rep, "method": k, "value": v, "ratio": v / true99,
                         "exceed_pct": 100 * (1 - mix_cdf(v, med, sig, sh))})
    sim = pd.DataFrame(rows)
    summ = sim.groupby("method", sort=False).agg(value_ms=("value", "mean"), ratio=("ratio", "mean"),
                                                 ratio_p5=("ratio", lambda x: x.quantile(.05)),
                                                 ratio_p95=("ratio", lambda x: x.quantile(.95)),
                                                 exceed_pct=("exceed_pct", "mean")).round(4)
    summ.to_csv(RES / "methods_200hours.csv")

    # 3) 式どおりの確かめ：8台がまったく同じ分布なら、①は全体の99%点とほぼ同じ
    same_med, same_sig, same_sh = np.full(8, 41.0), np.full(8, 0.45), np.full(8, 1 / 8)
    same_true = mix_q(0.99, same_med, same_sig, same_sh)
    same_ratio = []
    for rep in range(50):
        g = np.random.default_rng(SEED * 77 + rep)
        s_, m_ = draw(g, same_med, same_sig, same_sh)
        same_ratio.append(methods(s_, m_, 8)[0]["①サーバーの99%点の平均"] / same_true)
    same = {"true_p99_ms": r(same_true, 2), "formula_p99_ms": r(41 * math.exp(Z99 * 0.45), 2),
            "mean_of_p99_ratio_50hours": r(np.mean(same_ratio))}

    # 4) 1分ごとの99%点を60分平均する（1台、混む分ほど件数が多く遅い）
    minute = np.arange(60)
    load = 1000 + 2500 * np.exp(-0.5 * ((minute - 38) / 7) ** 2)          # 1分の件数
    med_t = 35 * (1 + 0.8 * ((load - 1000) / 2500) ** 2)                    # 混むほど中央値が上がる
    sig_t = 0.45
    true_hour = mix_q(0.99, med_t, np.full(60, sig_t), load / load.sum())
    mrows = []
    for rep in range(N_REP):
        g = np.random.default_rng(SEED * 3000 + rep)
        mp, allv, cnts = [], [], []
        for t in range(60):
            v = med_t[t] * np.exp(g.normal(0, sig_t, int(load[t])))
            mp.append(np.quantile(v, 0.99)); allv.append(v); cnts.append(len(v))
        mp, cnts = np.array(mp), np.array(cnts)
        allv = np.concatenate(allv)
        for k, v in {"1分ごとの99%点の平均": mp.mean(), "1分ごとの99%点の件数で重みを付けた平均": (mp * cnts).sum() / cnts.sum(),
                     "1分ごとの99%点の最大": mp.max(), "1時間を合わせて数える": np.quantile(allv, 0.99)}.items():
            mrows.append({"method": k, "value": v, "ratio": v / true_hour,
                          "exceed_pct": 100 * (1 - mix_cdf(v, med_t, np.full(60, sig_t), load / load.sum()))})
    msum = pd.DataFrame(mrows).groupby("method", sort=False).mean().round(4)
    msum.to_csv(RES / "minutes_200hours.csv")

    # 5) 置き方を変えた27通り：台数 × 遅いサーバーの裾の長さ × 遅いサーバーの処理の割合（ほかの1台の何倍か）
    grows = []
    for n_srv in (4, 8, 16):
        for ss in (0.6, 0.9, 1.2):
            for sl in (0.25, 1.0, 4.0):
                m2, s2, h2 = servers(n_srv, ss, sl)
                t2 = mix_q(0.99, m2, s2, h2)
                vals = []
                for rep in range(20):
                    g = np.random.default_rng(SEED * 5000 + rep + 100 * n_srv + int(ss * 10) + int(sl * 1000))
                    s_, m_ = draw(g, m2, s2, h2)
                    vals.append(methods(s_, m_, n_srv)[0])
                v = pd.DataFrame(vals).mean()
                f_mean = float(np.mean(m2 * np.exp(Z99 * s2)))
                grows.append({"n_servers": n_srv, "slow_log_sd": ss, "slow_load_x": sl, "slow_share": r(h2[-1]),
                              "true_p99": r(t2, 2), "mean_ratio": r(v.iloc[0] / t2), "weighted_ratio": r(v.iloc[1] / t2),
                              "max_ratio": r(v.iloc[3] / t2), "pooled_ratio": r(v.iloc[4] / t2),
                              "hist_ratio": r(v.iloc[5] / t2),
                              "mean_ratio_formula": r(f_mean / t2),
                              "mean_exceed_pct": r(100 * (1 - mix_cdf(v.iloc[0], m2, s2, h2))),
                              "weighted_exceed_pct": r(100 * (1 - mix_cdf(v.iloc[1], m2, s2, h2)))})
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)

    base_row = grid[(grid.n_servers == 8) & (grid.slow_log_sd == 0.9) & (grid.slow_load_x == 1.0)].iloc[0]
    S = summ["ratio"]
    head = {
        "true_p99_ms": r(true99, 2),
        "mean_p99_ms": r(summ.loc["①サーバーの99%点の平均", "value_ms"], 2),
        "mean_p99_ratio": r(S["①サーバーの99%点の平均"]),
        "mean_p99_pct_diff": r(100 * (S["①サーバーの99%点の平均"] - 1), 2),
        "mean_p99_exceed_pct": r(summ.loc["①サーバーの99%点の平均", "exceed_pct"], 2),
        "mean_p99_formula_ms": r(formula_p99.mean(), 2),
        "mean_p99_formula_exceed_pct": r(100 * (1 - mix_cdf(formula_p99.mean(), med, sig, sh)), 2),
        "weighted_ratio": r(S["②件数で重みを付けた平均"]),
        "weighted_exceed_pct": r(summ.loc["②件数で重みを付けた平均", "exceed_pct"], 2),
        "max_ratio": r(S["④サーバーの99%点の最大"]),
        "pooled_ratio": r(S["⑤全部の処理を合わせて数える"]),
        "hist_ratio": r(S["⑥区切りごとの件数を足し合わせる"]),
        "hist_exceed_pct": r(summ.loc["⑥区切りごとの件数を足し合わせる", "exceed_pct"], 2),
        "slow_server_p99_ms": r(p99_one[-1], 2),
        "share_of_over_true99_from_H_pct": r(100 * ((srv == 7) & (ms > true99)).sum() / (ms > true99).sum(), 2),
        "grid_mean_ratio_min": r(grid.mean_ratio.min()), "grid_mean_ratio_max": r(grid.mean_ratio.max()),
        "grid_mean_above_count": int((grid.mean_ratio > 1.02).sum()), "grid_mean_below_count": int((grid.mean_ratio < 0.98).sum()),
        "grid_mean_exceed_min": r(grid.mean_exceed_pct.min(), 2), "grid_mean_exceed_max": r(grid.mean_exceed_pct.max(), 2),
        "grid_weighted_ratio_min": r(grid.weighted_ratio.min()), "grid_weighted_ratio_max": r(grid.weighted_ratio.max()),
        "grid_weighted_exceed_min": r(grid.weighted_exceed_pct.min(), 2), "grid_weighted_exceed_max": r(grid.weighted_exceed_pct.max(), 2),
        "grid_hist_ratio_min": r(grid.hist_ratio.min()), "grid_hist_ratio_max": r(grid.hist_ratio.max()),
        "grid_max_formula_gap": r((grid.mean_ratio - grid.mean_ratio_formula).abs().max()),
        "base_grid_mean_ratio": r(base_row.mean_ratio),
        "minutes_true_hour_p99": r(true_hour, 2),
        "minutes_mean_ratio": r(msum.loc["1分ごとの99%点の平均", "ratio"]),
        "minutes_mean_pct_diff": r(100 * (msum.loc["1分ごとの99%点の平均", "ratio"] - 1), 2),
        "minutes_weighted_pct_diff": r(100 * (msum.loc["1分ごとの99%点の件数で重みを付けた平均", "ratio"] - 1), 2),
        "weighted_pct_diff": r(100 * (S["②件数で重みを付けた平均"] - 1), 2),
        "minutes_mean_exceed_pct": r(msum.loc["1分ごとの99%点の平均", "exceed_pct"], 2),
        "minutes_weighted_ratio": r(msum.loc["1分ごとの99%点の件数で重みを付けた平均", "ratio"]),
        "minutes_weighted_exceed_pct": r(msum.loc["1分ごとの99%点の件数で重みを付けた平均", "exceed_pct"], 2),
        "minutes_max_ratio": r(msum.loc["1分ごとの99%点の最大", "ratio"]),
        "minutes_pooled_ratio": r(msum.loc["1時間を合わせて数える", "ratio"]),
        "minutes_load_min": int(load.min()), "minutes_load_max": int(load.max()),
        "minutes_median_min": r(med_t.min(), 2), "minutes_median_max": r(med_t.max(), 2),
        "same_servers": same,
    }
    head["run_sec"] = r(time.time() - t0, 1)
    out = {"headline": {k: v for k, v in head.items() if k != "run_sec"},
           "servers_set": {"median_ms": med.round(3).tolist(), "log_sd": sig.tolist(), "share": sh.round(4).tolist()},
           "one_hour": {k: r(v, 2) for k, v in one.items()},
           "methods_200hours": summ.reset_index().to_dict("records"),
           "minutes_200hours": msum.reset_index().to_dict("records")}
    json.dump(out, open(RES / "a1059_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：サーバーごとの99%点（1時間分）と、その平均・全体の99%点
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    col = [BLUE] * 7 + [ORANGE]
    ax.bar(NAMES, p99_one, color=col)
    for i, v in enumerate(p99_one):
        ax.text(i, v + 4, f"{v:.0f}", ha="center", fontsize=9)
    ax.axhline(p99_one.mean(), color=INK, lw=1.2, ls="--")
    ax.text(-0.45, p99_one.mean() + 3, f"①8台の99%点の平均 {p99_one.mean():.0f}ms", va="bottom", fontsize=9, color=INK)
    ax.axhline(one["⑤全部の処理を合わせて数える"], color=GREEN, lw=1.5)
    ax.text(-0.45, one["⑤全部の処理を合わせて数える"] + 4, f"⑤全部を合わせた99%点 {one['⑤全部の処理を合わせて数える']:.0f}ms",
            va="bottom", fontsize=9, color=GREEN)
    ax.set_ylim(0, max(p99_one) * 1.15)
    ax.set_xlabel("サーバー（H だけ遅い側の裾が長い）"); ax.set_ylabel("99パーセンタイル（ms）")
    ax.set_title("サーバーごとの99%点を平均しても、全体の99%点にはならない（1時間分）")
    save(fig, "a1059_servers.png", SRC)

    # 図2：まとめ方ごとの「その値を超えた処理の割合」（本当は1%）
    s = summ.reset_index()
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    colors = [ORANGE, ORANGE, GRAY, GRAY, GREEN, GREEN]
    ax.barh(s.method[::-1], s.exceed_pct[::-1], color=colors[::-1])
    for i, v in enumerate(s.exceed_pct[::-1]):
        ax.text(v + 0.03, i, f"{v:.2f}%", va="center", fontsize=9)
    ax.axvline(1.0, color=INK, lw=1, ls="--")
    ax.set_xlim(0, max(s.exceed_pct) * 1.2)
    ax.set_xlabel("出した値より遅かった処理の割合（%、200時間の平均。99%点なら1%）")
    ax.set_title("サーバーごとの99%点の平均より遅い処理は、1%ではなかった")
    save(fig, "a1059_methods.png", SRC)

    # 図3：27通りの ① と ② の、本当の99%点に対する比
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.8), sharey=True)
    for ax, n_srv in zip(axes, (4, 8, 16)):
        g = grid[grid.n_servers == n_srv]
        for ss, c in zip((0.6, 0.9, 1.2), (LIGHT, BLUE, INK)):
            gg = g[g.slow_log_sd == ss]
            ax.plot(range(3), gg.mean_ratio, marker="o", color=c, label=f"①平均　裾 {ss}")
            ax.plot(range(3), gg.weighted_ratio, marker="s", ls=":", color=c, label=f"②重み付き　裾 {ss}")
        ax.axhline(1, color=GREEN, lw=1)
        ax.set_xticks(range(3)); ax.set_xticklabels(["1/4倍", "同じ", "4倍"])
        ax.set_title(f"{n_srv}台", fontsize=11)
        ax.set_ylim(0, max(grid.mean_ratio.max(), grid.weighted_ratio.max()) * 1.08)
    axes[0].set_ylabel("本当の99%点に対する比（1が正しい）")
    axes[1].set_xlabel("遅いサーバー H の処理の量（ほかの1台と比べて）")
    axes[2].legend(frameon=False, fontsize=7, loc="upper right", ncol=1)
    fig.suptitle("置き方27通り：平均は上にも下にも外れ、件数の重みを付けても直らない", fontsize=12, y=1.04)
    save(fig, "a1059_grid.png", SRC, y=-0.04)
    print(json.dumps(head, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
