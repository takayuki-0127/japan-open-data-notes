"""1123 失敗するたびに成功率が上がる強化の決まりでは、成功までの回数の平均とばらつきはどれだけ縮むのか？（架空のデータ）

架空のゲームで、ゲームの中の素材を1個使って装備の強化を試す。
  決まった率：毎回 p0 で成功
  上がる率　：はじめ p0、失敗するたびに k ポイント上がる（100%で止まる）。成功したら p0 に戻る
成功までの回数の分布は式で決まる（P(N=n)＝(1−p1)…(1−p_{n−1})×p_n）。式の値と、架空のプレイヤーの乱数で数えた値を並べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1123
SRC = "架空のゲームの強化（作成者が置いた成功率の決まりと乱数、seed 1123）"
P0, K = 0.10, 0.02
N_PLAYERS = 20000
GRID_P0 = [0.05, 0.10, 0.20]
GRID_K = [0.01, 0.02, 0.05]
NMAX = 2000


def r(x, d=3):
    return round(float(x), d)


def probs(p0, k):
    n = np.arange(1, NMAX + 1)
    return np.minimum(p0 + k * (n - 1), 1.0)


def dist(p0, k):
    p = probs(p0, k)
    surv = np.concatenate([[1.0], np.cumprod(1 - p)[:-1]])
    return surv * p          # P(N=n), n=1..NMAX


def stats_from_dist(pm):
    n = np.arange(1, len(pm) + 1)
    mean = float((n * pm).sum()); sd = float(np.sqrt(((n - mean) ** 2 * pm).sum()))
    cdf = np.cumsum(pm)
    q = lambda a: int(np.searchsorted(cdf, a - 1e-12) + 1)
    return {"mean": r(mean, 3), "sd": r(sd, 3), "p50": q(0.5), "p90": q(0.9), "p99": q(0.99),
            "max_possible": int(n[pm > 0].max()) if pm[-1] == 0 else None,
            "over_30": r(100 * (1 - cdf[29]), 2), "rate_per_try_pct": r(100 / mean, 2)}


def simulate(rng, p0, k, n):
    tries = np.zeros(n, dtype=int); done = np.zeros(n, dtype=bool); t = 0
    while not done.all():
        t += 1
        p = min(p0 + k * (t - 1), 1.0)
        succ = (~done) & (rng.random(n) < p)
        tries[succ] = t; done |= succ
    return tries


def stats_from_sample(x):
    return {"mean": r(x.mean(), 3), "sd": r(x.std(), 3), "p50": int(np.percentile(x, 50, method="inverted_cdf")),
            "p90": int(np.percentile(x, 90, method="inverted_cdf")), "p99": int(np.percentile(x, 99, method="inverted_cdf")),
            "max": int(x.max()), "over_30": r(100 * (x > 30).mean(), 2), "rate_per_try_pct": r(100 * len(x) / x.sum(), 2)}


def match_scale(p0, k, target_mean):
    """はじめの率と上がり幅を同じ倍率 c で下げて、平均を target_mean にそろえる c を求める"""
    lo, hi = 1e-6, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        mm = float((np.arange(1, NMAX + 1) * dist(mid * p0, mid * k)).sum())
        if mm > target_mean:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res = {"setup": {"p0": P0, "k": K, "players": N_PLAYERS, "grid_p0": GRID_P0, "grid_k": GRID_K}}

    # 基本：決まった10%・上がる率（10%＋失敗ごとに2ポイント）・平均をそろえた上がる率
    c = match_scale(P0, K, 1 / P0)
    p0m, km = c * P0, c * K
    rules = [("fixed", "決まった率10%", P0, 0.0), ("rise", "上がる率（10%から+2ポイント）", P0, K),
             ("rise_matched", "上がる率（平均10回にそろえた）", p0m, km)]
    res["matched"] = {"scale": r(c, 4), "p0_pct": r(100 * p0m, 2), "k_pt": r(100 * km, 2)}
    base = {}; samples = {}; dists = {}
    for key, name, p0, k in rules:
        pm = dist(p0, k); dists[key] = pm
        x = simulate(rng, p0, k, N_PLAYERS); samples[key] = x
        base[key] = {"name": name, "p0_pct": r(100 * p0, 2), "k_pt": r(100 * k, 2),
                     "formula": stats_from_dist(pm), "sim": stats_from_sample(x)}
        if k > 0:
            base[key]["guaranteed_by"] = int(np.ceil((1 - p0) / k) + 1)
    res["base"] = base
    f, ri, rm = base["fixed"]["formula"], base["rise"]["formula"], base["rise_matched"]["formula"]
    res["base_ratio"] = {"mean_rise_over_fixed": r(ri["mean"] / f["mean"], 3), "sd_rise_over_fixed": r(ri["sd"] / f["sd"], 3),
                         "sd_matched_over_fixed": r(rm["sd"] / f["sd"], 3), "p99_fixed": f["p99"], "p99_rise": ri["p99"],
                         "p99_matched": rm["p99"]}

    # 失敗が続いた人の、次の1回の成功率（記録から数えた値）
    rows = []
    for key in ("fixed", "rise"):
        x = samples[key]
        for j in range(0, 31, 5):
            at_risk = (x > j).sum(); succ = (x == j + 1).sum()
            rows.append({"rule": key, "fails_before": j, "players": int(at_risk),
                         "next_success_pct": r(100 * succ / at_risk, 2) if at_risk else None,
                         "set_rate_pct": r(100 * min(P0 + (K if key == "rise" else 0) * j, 1), 2)})
    cond = pd.DataFrame(rows); cond.to_csv(RES / "after_fails.csv", index=False)
    res["after_fails"] = rows

    # 分布の表（式の値と数えた値）
    tab = pd.DataFrame({"tries": np.arange(1, 61)})
    for key, _, _, _ in rules:
        tab[f"{key}_formula_pct"] = np.round(100 * dists[key][:60], 4)
        tab[f"{key}_sim_pct"] = np.round(100 * np.bincount(samples[key], minlength=61)[1:61] / N_PLAYERS, 4)
    tab.to_csv(RES / "tries_dist.csv", index=False)

    # データ：プレイヤーごとの回数
    pd.DataFrame({"player_id": np.arange(1, N_PLAYERS + 1), **{f"tries_{k}": samples[k] for k, _, _, _ in rules}}
                 ).to_csv(DATA / "players_tries.csv", index=False)

    # 置き方を変えた9通り（式の値）
    g = []
    for p0 in GRID_P0:
        for k in GRID_K:
            fx = stats_from_dist(dist(p0, 0.0)); rs = stats_from_dist(dist(p0, k))
            cc = match_scale(p0, k, 1 / p0); rmm = stats_from_dist(dist(cc * p0, cc * k))
            g.append({"p0_pct": r(100 * p0, 1), "k_pt": r(100 * k, 1),
                      "fixed_mean": fx["mean"], "fixed_sd": fx["sd"], "fixed_p99": fx["p99"],
                      "rise_mean": rs["mean"], "rise_sd": rs["sd"], "rise_p99": rs["p99"], "rise_rate_per_try_pct": rs["rate_per_try_pct"],
                      "mean_ratio": r(rs["mean"] / fx["mean"], 3), "sd_ratio": r(rs["sd"] / fx["sd"], 3),
                      "matched_p0_pct": r(100 * cc * p0, 2), "matched_k_pt": r(100 * cc * k, 2), "matched_sd": rmm["sd"], "matched_sd_ratio": r(rmm["sd"] / fx["sd"], 3),
                      "matched_p99": rmm["p99"]})
    grid = pd.DataFrame(g); grid.to_csv(RES / "grid.csv", index=False)
    res["grid_range"] = {c: [r(grid[c].min(), 3), r(grid[c].max(), 3)] for c in
                         ["mean_ratio", "sd_ratio", "matched_sd_ratio", "rise_rate_per_try_pct", "matched_p0_pct", "matched_k_pt", "rise_p99", "matched_p99", "fixed_p99"]}
    res["grid_shown_over_rate_ratio"] = [r((grid["rise_rate_per_try_pct"] / grid["p0_pct"]).min(), 2),
                                         r((grid["rise_rate_per_try_pct"] / grid["p0_pct"]).max(), 2)]

    # 図1：成功までの回数の分布
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    n = np.arange(1, 41); w = 0.4
    ax.bar(n - w / 2, 100 * dists["fixed"][:40], width=w, color=GRAY, label="決まった率10%")
    ax.bar(n + w / 2, 100 * dists["rise"][:40], width=w, color=BLUE, label="10%から失敗ごとに+2ポイント")
    ax.set_xlabel("成功までに使った素材の数（回）"); ax.set_ylabel("割合（%）"); ax.set_ylim(0, None)
    ax.set_title("成功までの回数（式の値）")
    ax.legend(frameon=False)
    save(fig, "a1123_dist.png", SRC)

    # 図2：何個用意すれば何%の人が成功するか
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    n = np.arange(1, 61)
    for key, name, col in [("fixed", "決まった率10%", GRAY), ("rise", "10%から+2ポイント", BLUE),
                           ("rise_matched", f"{base['rise_matched']['p0_pct']}%から+{base['rise_matched']['k_pt']}ポイント（平均10回にそろえた）", ORANGE)]:
        ax.plot(n, 100 * np.cumsum(dists[key])[:60], color=col, lw=2.2, label=name)
    ax.axhline(90, color=GRAY, lw=0.8, ls="--"); ax.axhline(99, color=GRAY, lw=0.8, ls=":")
    ax.set_xlim(0, 60); ax.set_ylim(0, 101)
    ax.set_xlabel("用意した素材の数（個）"); ax.set_ylabel("その数までに成功した人の割合（%）")
    ax.set_title("平均を10回にそろえても、遅い人の回数は縮む（式の値）")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "a1123_cumulative.png", SRC)

    # 図3：9通りのばらつきの比
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    labels = [f"{a:g}%\n+{b:g}" for a, b in zip(grid["p0_pct"], grid["k_pt"])]
    x = np.arange(len(grid)); w = 0.38
    ax.bar(x - w / 2, grid["sd_ratio"], width=w, color=BLUE, label="同じはじめの率（平均も縮む）")
    ax.bar(x + w / 2, grid["matched_sd_ratio"], width=w, color=ORANGE, label="平均をそろえた")
    ax.axhline(1, color=GRAY, lw=0.8, ls="--")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9); ax.set_ylim(0, 1.2)
    ax.set_xlabel("はじめの率と、失敗ごとに上がるポイント"); ax.set_ylabel("標準偏差の比（決まった率＝1）")
    ax.set_title("9通りの置き方での、ばらつきの縮み（式の値）")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    save(fig, "a1123_grid.png", SRC, y=-0.05)

    (RES / "a1123_main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
