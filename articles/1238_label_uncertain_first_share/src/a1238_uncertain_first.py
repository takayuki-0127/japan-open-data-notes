"""1238 分類する仕組みが迷う件から先に付けていくと、付けたデータの中の分類の割合は実際とどれだけずれるのか？（架空のデータ）

架空の問い合わせ文20,000件。件ごとに2つの特徴（どちらも平均0・標準偏差1）を置き、
「返品の相談」である確率を 1÷(1+exp(−(b0 + k×(2×特徴1 + 1×特徴2)))) と置く（k は分かれやすさ、b0 は全体で10%になるよう決める）。
付け手は本当の分類どおりに付ける（付けまちがいなし）。最初にでたらめに100件付け、その後100件ずつ付ける。
付けるたびに、特徴の重み付きの和から確率を出す簡単な分類の仕組みを付けた件で作り直し、次の100件を選ぶ。
選び方：① 迷う件から（確率が0.5にいちばん近い件） ② でたらめ ③ 半分はでたらめ・半分は迷う件。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1238
SRC = "架空の問い合わせ文と分類する仕組み（作成者が乱数で作成、seed 1238）"
POOL, START, STEP, BUDGET = 20000, 100, 100, 2000
RATE0, K0 = 0.10, 1.0
W = np.array([2.0, 1.0])
REP = 50
STRATS = {"uncertain": "① 迷う件から", "random": "② でたらめ", "half": "③ 半分でたらめ・半分迷う件"}


def sig(v):
    return 1 / (1 + np.exp(-v))


def find_b0(rate, k):
    # 重み付きの和 k×(2x1+x2) は平均0・標準偏差 k×√5 の正規分布。格子で積分して b0 を決める
    sd = k * np.sqrt(5.0)
    t = np.linspace(-8, 8, 4001)
    dens = np.exp(-t ** 2 / 2); dens /= dens.sum()
    lo, hi = -30.0, 30.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if (sig(mid + sd * t) * dens).sum() > rate:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def fit(X, y, iters=25, ridge=1e-3):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = sig(X @ b)
        g = X.T @ (y - p) - ridge * b
        H = (X * (p * (1 - p))[:, None]).T @ X + ridge * np.eye(X.shape[1])
        step = np.linalg.solve(H, g)
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


def one_run(rng, strat, rate=RATE0, k=K0, budget=BUDGET):
    b0 = find_b0(rate, k)
    x = rng.normal(0, 1, (POOL, 2))
    ptrue = sig(b0 + k * (x @ W))
    y = (rng.random(POOL) < ptrue).astype(float)
    X = np.column_stack([np.ones(POOL), x])
    labeled = np.zeros(POOL, bool)
    is_random = np.zeros(POOL, bool)
    first = rng.choice(POOL, START, replace=False)
    labeled[first] = True; is_random[first] = True
    rec = []
    while True:
        n = labeled.sum()
        b = fit(X[labeled], y[labeled])
        pr = sig(X @ b)
        rec.append({"labeled": int(n), "share_labeled": y[labeled].mean(),
                    "share_random_part": y[is_random].mean(),
                    "pred_mean": pr.mean(), "pred_over_half": (pr >= 0.5).mean(),
                    "true_pool": y.mean(), "intercept_gap": b[0] - b0})
        if n >= budget:
            break
        cand = np.where(~labeled)[0]
        if strat == "random":
            pick = rng.choice(cand, STEP, replace=False); is_random[pick] = True
        elif strat == "uncertain":
            pick = cand[np.argsort(np.abs(pr[cand] - 0.5), kind="stable")[:STEP]]
        else:
            pr_rand = rng.choice(cand, STEP // 2, replace=False)
            is_random[pr_rand] = True
            labeled[pr_rand] = True
            cand = np.where(~labeled)[0]
            pick = cand[np.argsort(np.abs(pr[cand] - 0.5), kind="stable")[:STEP // 2]]
        labeled[pick] = True
    return pd.DataFrame(rec), x, y, labeled, ptrue


def main():
    t0 = time.time()
    # 基本：3つの選び方×50回
    curves = []
    for i, s in enumerate(STRATS):
        rng = np.random.default_rng(SEED * 10 + i)
        for r in range(REP):
            df, *_ = one_run(rng, s)
            df["strategy"] = s; df["rep"] = r
            curves.append(df)
    cv = pd.concat(curves)
    agg = cv.groupby(["strategy", "labeled"]).agg(
        share_labeled=("share_labeled", "mean"), share_random_part=("share_random_part", "mean"),
        pred_mean=("pred_mean", "mean"), pred_over_half=("pred_over_half", "mean"), true_pool=("true_pool", "mean"),
        share_labeled_p10=("share_labeled", lambda v: np.percentile(v, 10)),
        share_labeled_p90=("share_labeled", lambda v: np.percentile(v, 90))).reset_index()
    for c in ["share_labeled", "share_random_part", "pred_mean", "pred_over_half", "true_pool",
              "share_labeled_p10", "share_labeled_p90"]:
        agg[c] = (agg[c] * 100).round(2)
    agg = agg.rename(columns={c: c + "_pct" for c in agg.columns if c not in ["strategy", "labeled"]})
    agg.to_csv(RES / "by_budget.csv", index=False)

    head = {}
    for s in STRATS:
        a = agg[agg.strategy == s].set_index("labeled")
        head[s] = {"name": STRATS[s]}
        for n in [200, 500, 1000, 2000]:
            head[s][f"at{n}"] = {k: float(a.loc[n, k]) for k in ["share_labeled_pct", "share_random_part_pct", "pred_mean_pct",
                                                                   "pred_over_half_pct", "true_pool_pct",
                                                                   "share_labeled_p10_pct", "share_labeled_p90_pct"]}
            head[s][f"at{n}"]["ratio_labeled_to_pool"] = round(float(a.loc[n, "share_labeled_pct"] / a.loc[n, "true_pool_pct"]), 2)
    # 迷う件から選んだ2,000件の、本当の確率の分布（1回分）
    rng = np.random.default_rng(SEED)
    df, x, y, labeled, ptrue = one_run(rng, "uncertain")
    ex = pd.DataFrame({"id": np.arange(1, POOL + 1), "feature1": x[:, 0].round(4), "feature2": x[:, 1].round(4),
                       "true_prob": ptrue.round(4), "is_return": y.astype(int), "labeled_uncertain_first": labeled.astype(int)})
    ex.to_csv(DATA / "pool_one_run.csv", index=False)
    bins = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    lab_hist = np.histogram(ptrue[labeled], bins)[0] / labeled.sum()
    pool_hist = np.histogram(ptrue, bins)[0] / POOL
    hist = pd.DataFrame({"prob_from": bins[:-1], "prob_to": bins[1:], "labeled_pct": (lab_hist * 100).round(2),
                         "pool_pct": (pool_hist * 100).round(2)})
    hist.to_csv(RES / "true_prob_hist_one_run.csv", index=False)
    ex_sum = {"labeled_share_pct": round(float(y[labeled].mean()) * 100, 2), "pool_share_pct": round(float(y.mean()) * 100, 2),
              "labeled_true_prob_mean_pct": round(float(ptrue[labeled].mean()) * 100, 2)}

    # 確かめ：本当の割合 × 分かれやすさ k × 付ける件数（27通り、各10回）
    g = []
    j = 0
    for rate in [0.03, 0.10, 0.30]:
        for k in [0.5, 1.0, 2.0]:
            j += 1
            res = {}
            for i, s in enumerate(STRATS):
                rng = np.random.default_rng(SEED * 1000 + j * 10 + i)
                res[s] = pd.concat([one_run(rng, s, rate, k)[0] for _ in range(10)]).groupby("labeled").mean()
            for n in [500, 1000, 2000]:
                row = {"true_rate": rate, "separation": k, "labeled": n,
                       "true_pool_pct": round(float(res["random"].loc[n, "true_pool"]) * 100, 2)}
                for s in STRATS:
                    row[f"{s}_share_labeled_pct"] = round(float(res[s].loc[n, "share_labeled"]) * 100, 2)
                    row[f"{s}_pred_mean_pct"] = round(float(res[s].loc[n, "pred_mean"]) * 100, 2)
                row["half_random_part_pct"] = round(float(res["half"].loc[n, "share_random_part"]) * 100, 2)
                row["uncertain_ratio"] = round(row["uncertain_share_labeled_pct"] / row["true_pool_pct"], 3)
                g.append(row)
    grid = pd.DataFrame(g)
    grid.to_csv(RES / "grid.csv", index=False)
    robust = {
        "settings": len(grid),
        "uncertain_ratio_min": float(grid.uncertain_ratio.min()), "uncertain_ratio_max": float(grid.uncertain_ratio.max()),
        "uncertain_over_count": int((grid.uncertain_share_labeled_pct > grid.true_pool_pct).sum()),
        "uncertain_over_count_rate_le10": int(((grid.uncertain_share_labeled_pct > grid.true_pool_pct) & (grid.true_rate <= 0.1)).sum()),
        "settings_rate_le10": int((grid.true_rate <= 0.1).sum()),
        "uncertain_gap_min": round(float((grid.uncertain_share_labeled_pct - grid.true_pool_pct).min()), 2),
        "uncertain_gap_max": round(float((grid.uncertain_share_labeled_pct - grid.true_pool_pct).max()), 2),
        "random_gap_absmax": round(float((grid.random_share_labeled_pct - grid.true_pool_pct).abs().max()), 2),
        "uncertain_pred_gap_absmax": round(float((grid.uncertain_pred_mean_pct - grid.true_pool_pct).abs().max()), 2),
        "random_pred_gap_absmax": round(float((grid.random_pred_mean_pct - grid.true_pool_pct).abs().max()), 2),
        "half_random_part_gap_absmax": round(float((grid.half_random_part_pct - grid.true_pool_pct).abs().max()), 2),
    }
    json.dump({"headline": head, "example_one_run_uncertain": ex_sum, "robust": robust,
               "setup": {"pool": POOL, "start_random": START, "step": STEP, "budget": BUDGET, "true_rate": RATE0,
                         "separation": K0, "weights": W.tolist(), "reps": REP}},
              open(RES / "a1238_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：付けた件数と、付けたデータの中の返品の相談の割合
    fig, ax = plt.subplots(figsize=(7, 3.9))
    for s, c, mk in [("uncertain", ORANGE, "o"), ("half", GREEN, "^"), ("random", BLUE, "s")]:
        a = agg[agg.strategy == s]
        ax.plot(a.labeled, a.share_labeled_pct, color=c, marker=mk, ms=3, label=STRATS[s] + "（付けた件の中）")
    a = agg[agg.strategy == "half"]
    ax.plot(a.labeled, a.share_random_part_pct, color=GREEN, ls=":", label="③ のうち、でたらめに選んだ件だけ")
    ax.axhline(RATE0 * 100, color=INK, lw=1, ls="--", label="全体の本当の割合（10%）")
    ax.set_ylim(0, 55); ax.set_xlim(0, BUDGET + 50)
    ax.set_xlabel("付けた件数"); ax.set_ylabel("「返品の相談」の割合（%、50回の平均）")
    ax.set_title("迷う件から付けると、付けた件の中の割合は10%から40%台に上がった")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    save(fig, "a1238_share.png", SRC, y=-0.30)

    # 図2：付けた件と全体の、本当の確率の分布（1回分）
    fig, ax = plt.subplots(figsize=(7, 3.9))
    xs = np.arange(len(hist))
    ax.bar(xs - 0.2, hist.pool_pct, 0.4, color=GRAY, label="全体の20,000件")
    ax.bar(xs + 0.2, hist.labeled_pct, 0.4, color=ORANGE, label="① 迷う件から付けた2,000件")
    for xx, v in zip(xs - 0.2, hist.pool_pct):
        ax.text(xx, v + 1, f"{v:.2f}", ha="center", fontsize=8)
    for xx, v in zip(xs + 0.2, hist.labeled_pct):
        ax.text(xx, v + 1, f"{v:.2f}", ha="center", fontsize=8)
    ax.set_xticks(xs, [f"{a:g}〜{b:g}" for a, b in zip(hist.prob_from, hist.prob_to)])
    ax.set_ylim(0, 100); ax.set_xlabel("件の本当の「返品の相談」である確率"); ax.set_ylabel("件の割合（%）")
    ax.set_title("迷う件から付けた件は、本当の確率が0.3〜0.7の件にかたよった（1回分）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1238_hist.png", SRC)

    # 図3：27通り
    fig, axs = plt.subplots(1, 3, figsize=(11, 4), sharey=False)
    for ax, rate in zip(axs, [0.03, 0.10, 0.30]):
        gg = grid[grid.true_rate == rate]
        for k, c, mk in [(0.5, LIGHT, "o"), (1.0, BLUE, "s"), (2.0, ORANGE, "^")]:
            g2 = gg[gg.separation == k]
            ax.plot(g2.labeled, g2.uncertain_share_labeled_pct, color=c, marker=mk, label=f"① 分かれやすさ {k:g}")
        g2 = gg[gg.separation == 1.0]
        ax.plot(g2.labeled, g2.random_share_labeled_pct, color=GRAY, ls="--", marker="x", label="② でたらめ（分かれやすさ1）")
        ax.axhline(rate * 100, color=INK, lw=0.8)
        ax.set_ylim(0, 60); ax.set_xticks([500, 1000, 2000]); ax.set_xlabel("付けた件数")
        ax.set_title(f"全体の本当の割合 {rate*100:g}%", fontsize=11)
    axs[0].set_ylabel("付けた件の中の割合（%、各10回）")
    axs[0].legend(frameon=False, fontsize=8)
    save(fig, "a1238_grid.png", SRC)
    print(json.dumps(head, ensure_ascii=False)[:1500], json.dumps(robust), ex_sum, f"{time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
