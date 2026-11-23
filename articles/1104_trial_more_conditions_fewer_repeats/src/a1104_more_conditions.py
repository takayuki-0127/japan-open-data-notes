"""1104 条件の数を増やして繰り返しを減らすと、何を見落とすのか？（架空のデータ）

架空の塗装工房が、試し塗りの板24枚で、塗り方の条件（薄め方・吹き付けの距離・乾かす時間の組み合わせ）を選ぶ。
候補の条件は24通り。条件ごとに「本当の平均のむらの点」と「板ごとのばらつき（安定さ）」を作成者が置く。
むらの点が55を超えた板は手直し（作成者が置いた線）。条件の本当の手直しの割合は、平均とばらつきで決まる。
24枚を「k通りの条件×1条件あたり r 枚（k×r＝24）」に分けて塗り、見かけの平均のむらがいちばん小さい条件を選ぶ。
選んだ条件の本当の手直しの割合、見かけと本当の差、ばらつきの大きい条件を選んだ割合を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.special import ndtr
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1104
SRC = "架空の塗装工房の試し塗り（作成者が置いた平均とばらつきからの乱数、seed 1104）"
POOL = 24          # 候補の条件の数
LIMIT = 55.0       # むらの点がこれを超えた板は手直し
BASE = {"mean_center": 50.0, "mean_spread": 5.0, "sd_typical": 4.0, "sd_hetero": 0.5, "budget": 24}
ALLOC = [(2, 12), (3, 8), (4, 6), (6, 4), (8, 3), (12, 2), (24, 1)]
REPS = 4000
GRID_REPS = 1000


def r(x, d=4):
    return round(float(x), d)


def make_pool(rng, reps, mean_spread, sd_typical, sd_hetero):
    m = BASE["mean_center"] + mean_spread * rng.standard_normal((reps, POOL))
    s = sd_typical * np.exp(sd_hetero * rng.standard_normal((reps, POOL)) - sd_hetero ** 2 / 2)
    fail = 1 - ndtr((LIMIT - m) / s)                     # 本当の手直しの割合
    return m, s, fail


def run(rng, m, s, fail, k, rr):
    """候補のうち k 通り（候補はでたらめに並んでいるので先頭の k 通り）を rr 枚ずつ塗り、見かけの平均で選ぶ"""
    reps = m.shape[0]
    y = m[:, :k, None] + s[:, :k, None] * rng.standard_normal((reps, k, rr))
    obs = y.mean(2)
    pick = obs.argmin(1)
    idx = np.arange(reps)
    hi_sd = s >= np.sort(s, 1)[:, [POOL * 3 // 4]]      # 候補24通りのうちばらつきの大きい4分の1
    if np.allclose(s, s[:, :1]):
        hi_sd = np.full(s.shape, np.nan)                 # ばらつきが条件で同じなら数えない
    out = {
        "pick_fail": fail[idx, pick],
        "pick_mean_gap": obs[idx, pick] - m[idx, pick],   # 見かけ−本当（負なら良く見えた）
        "pick_obs_fail": (y[idx, pick] > LIMIT).mean(1),  # 選んだ条件の板のうち手直しの割合（見かけ）
        "pick_hi_sd": hi_sd[idx, pick],
        "pick_is_best": pick == fail[:, :k].argmin(1),    # 試した中で本当にいちばん手直しの少ない条件か
        "pick_is_pool_best": (fail[idx, pick] == fail.min(1)),
        "best_tested_fail": fail[:, :k].min(1),
        "pick_sd_ratio": (y[idx, pick].std(1, ddof=1) / s[idx, pick]) if rr >= 2 else np.full(reps, np.nan),
        "pick_true_mean": m[idx, pick],
    }
    return out


def two_stage(rng, m, s, fail, k1=12, r1=1, top=3, r2=4):
    """12通りを1枚ずつ→見かけの良い3通りを4枚ずつ（合わせて24枚）。2段目の4枚の平均で選ぶ"""
    reps = m.shape[0]
    idx = np.arange(reps)
    y1 = m[:, :k1] + s[:, :k1] * rng.standard_normal((reps, k1))
    keep = np.argsort(y1, 1)[:, :top]
    mk, sk = np.take_along_axis(m, keep, 1), np.take_along_axis(s, keep, 1)
    y2 = mk[:, :, None] + sk[:, :, None] * rng.standard_normal((reps, top, r2))
    p = y2.mean(2).argmin(1)
    pick = keep[idx, p]
    hi_sd = s >= np.sort(s, 1)[:, [POOL * 3 // 4]]
    return {"pick_fail": fail[idx, pick], "pick_mean_gap": y2.mean(2)[idx, p] - m[idx, pick],
            "pick_obs_fail": (y2[idx, p] > LIMIT).mean(1), "pick_hi_sd": hi_sd[idx, pick],
            "pick_is_best": pick == fail[:, :k1].argmin(1), "pick_is_pool_best": fail[idx, pick] == fail.min(1),
            "best_tested_fail": fail[:, :k1].min(1),
            "pick_sd_ratio": y2[idx, p].std(1, ddof=1) / s[idx, pick], "pick_true_mean": m[idx, pick]}


def summarize(o):
    sdr = o["pick_sd_ratio"]
    return {"pick_fail_mean": r(o["pick_fail"].mean() * 100, 2), "pick_fail_median": r(np.median(o["pick_fail"]) * 100, 2),
            "pick_obs_fail_mean": r(o["pick_obs_fail"].mean() * 100, 2),
            "pick_mean_gap_mean": r(o["pick_mean_gap"].mean(), 3),
            "pick_looks_better_by": r(-o["pick_mean_gap"].mean(), 3),
            "pick_hi_sd_share": (None if np.isnan(o["pick_hi_sd"].astype(float)).all() else r(np.mean(o["pick_hi_sd"]) * 100, 2)),
            "pick_is_best_tested": r(o["pick_is_best"].mean() * 100, 2),
            "pick_is_pool_best": r(o["pick_is_pool_best"].mean() * 100, 2),
            "best_tested_fail_mean": r(o["best_tested_fail"].mean() * 100, 2),
            "pick_sd_ratio_median": (None if np.isnan(sdr).all() else r(np.nanmedian(sdr), 3)),
            "pick_sd_under_half": (None if np.isnan(sdr).all() else r((sdr < 0.5).mean() * 100, 2)),
            "pick_true_mean_mean": r(o["pick_true_mean"].mean(), 3)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    m, s, fail = make_pool(rng, REPS, BASE["mean_spread"], BASE["sd_typical"], BASE["sd_hetero"])
    pool_info = {"pool_fail_mean": r(fail.mean() * 100, 2), "pool_best_fail_mean": r(fail.min(1).mean() * 100, 3),
                 "pool_lowest_mean_fail_mean": r(fail[np.arange(REPS), m.argmin(1)].mean() * 100, 2),
                 "pool_lowest_mean_is_best": r((m.argmin(1) == fail.argmin(1)).mean() * 100, 2),
                 "hi_sd_share_baseline": 25.0}

    rows = []
    for k, rr in ALLOC:
        o = run(rng, m, s, fail, k, rr)
        rows.append({"design": f"{k}通り×{rr}枚", "k": k, "r": rr, **summarize(o)})
    o2 = two_stage(rng, m, s, fail)
    rows.append({"design": "12通り×1枚→良い3通り×4枚", "k": 12, "r": 0, **summarize(o2)})
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "by_design.csv", index=False)

    # 対照：ばらつきが条件で同じ（sd_hetero=0）とき
    m0, s0, f0 = make_pool(rng, REPS, BASE["mean_spread"], BASE["sd_typical"], 0.0)
    ctrl = []
    for k, rr in ALLOC:
        o = run(rng, m0, s0, f0, k, rr)
        ctrl.append({"design": f"{k}通り×{rr}枚", **{x: summarize(o)[x] for x in
                     ["pick_fail_mean", "pick_obs_fail_mean", "pick_mean_gap_mean", "pick_looks_better_by", "pick_is_pool_best"]}})
    ctrl = pd.DataFrame(ctrl)
    ctrl.to_csv(RES / "control_same_sd.csv", index=False)

    # 確かめ：置き方を変える（54通り）
    grid = []
    gi = 0
    for sd_typ in [2.0, 4.0, 8.0]:
        for het in [0.0, 0.5, 1.0]:
            for spread in [2.5, 5.0, 10.0]:
                for budget in [24, 48]:
                    g = np.random.default_rng(SEED * 100 + gi); gi += 1
                    gm, gs, gf = make_pool(g, GRID_REPS, spread, sd_typ, het)
                    res = {}
                    for k, rr0 in ALLOC:
                        rr = rr0 * budget // 24
                        o = run(g, gm, gs, gf, k, rr)
                        res[k] = o
                    pf = {k: res[k]["pick_fail"].mean() * 100 for k in res}
                    best_k = min(pf, key=pf.get)
                    grid.append({"sd_typical": sd_typ, "sd_hetero": het, "mean_spread": spread, "budget": budget,
                                 "best_k": best_k, "fail_k2": r(pf[2], 2), "fail_k6": r(pf[6], 2),
                                 "fail_k24": r(pf[24], 2), "fail_best_k": r(pf[best_k], 2),
                                 "pool_best_fail": r(gf.min(1).mean() * 100, 2),
                                 "obs_fail_k24": r(res[24]["pick_obs_fail"].mean() * 100, 2),
                                 "gap_k24": r(res[24]["pick_mean_gap"].mean(), 3),
                                 "gap_k2": r(res[2]["pick_mean_gap"].mean(), 3),
                                 "hi_sd_k24": (np.nan if het == 0 else r(res[24]["pick_hi_sd"].mean() * 100, 2)),
                                 "hi_sd_k2": (np.nan if het == 0 else r(res[2]["pick_hi_sd"].mean() * 100, 2))})
    grid = pd.DataFrame(grid)
    gh = grid[grid.sd_hetero > 0]
    grid.to_csv(RES / "grid.csv", index=False)
    gh = grid[grid.sd_hetero > 0]
    grid_sum = {
        "n": int(len(grid)),
        "best_k_counts": {str(k): int(v) for k, v in grid.best_k.value_counts().sort_index().items()},
        "best_k_counts_same_sd": {str(k): int(v) for k, v in grid[grid.sd_hetero == 0].best_k.value_counts().sort_index().items()},
        "best_k_counts_hetero": {str(k): int(v) for k, v in gh.best_k.value_counts().sort_index().items()},
        "k24_over_best_ratio_hetero": [r((gh.fail_k24 / gh.fail_best_k).min(), 3), r((gh.fail_k24 / gh.fail_best_k).max(), 3)],
        "k24_worse_than_k6_hetero": int((gh.fail_k24 > gh.fail_k6).sum()),
        "k24_worse_than_k6_same_sd": int((grid[grid.sd_hetero == 0].fail_k24 > grid[grid.sd_hetero == 0].fail_k6).sum()),
        "best_k_is_middle": int(grid.best_k.isin([3, 4, 6, 8, 12]).sum()),
        "gap_k24_range": [r(grid.gap_k24.min(), 3), r(grid.gap_k24.max(), 3)],
        "looks_better_k24_range": [r(-grid.gap_k24.max(), 3), r(-grid.gap_k24.min(), 3)],
        "best_k_12_or_24_same_sd": int(grid[grid.sd_hetero == 0].best_k.isin([12, 24]).sum()),
        "best_k_3_to_8_hetero": int(gh.best_k.isin([3, 4, 6, 8]).sum()),
        "obs_fail_k24_max": r(grid.obs_fail_k24.max(), 2),
        "hi_sd_k24_range_hetero": [r(gh.hi_sd_k24.min(), 2), r(gh.hi_sd_k24.max(), 2)],
        "hi_sd_k2_range_hetero": [r(gh.hi_sd_k2.min(), 2), r(gh.hi_sd_k2.max(), 2)],
        "hi_sd_k24_gt_k2_hetero": int((gh.hi_sd_k24 > gh.hi_sd_k2).sum()), "n_hetero": int(len(gh)),
        "k24_worse_than_k6": int((grid.fail_k24 > grid.fail_k6).sum()),
        "k2_worse_than_k6": int((grid.fail_k2 > grid.fail_k6).sum()),
    }

    # data：1回分の候補24通りと 24通り×1枚・6通り×4枚 の板
    g1 = np.random.default_rng(SEED + 1)
    m1, s1, f1 = make_pool(g1, 1, BASE["mean_spread"], BASE["sd_typical"], BASE["sd_hetero"])
    pd.DataFrame({"condition": [f"C{i+1:02d}" for i in range(POOL)], "true_mean": m1[0].round(4),
                  "true_sd": s1[0].round(4), "true_fail_share": f1[0].round(4)}).to_csv(DATA / "conditions_one_draw.csv", index=False)
    pieces = []
    for k, rr in [(24, 1), (6, 4)]:
        y = m1[0, :k, None] + s1[0, :k, None] * g1.standard_normal((k, rr))
        for i in range(k):
            for j in range(rr):
                pieces.append({"design": f"{k}x{rr}", "condition": f"C{i+1:02d}", "piece": j + 1, "unevenness": round(float(y[i, j]), 4)})
    pd.DataFrame(pieces).to_csv(DATA / "pieces_one_draw.csv", index=False)

    k24 = tab.set_index("design").loc["24通り×1枚", "pick_fail_mean"]; k6 = tab.set_index("design").loc["6通り×4枚", "pick_fail_mean"]
    out = {"base": BASE, "limit": LIMIT, "ratio_fail_k24_over_k6": r(k24 / k6, 3), "reps": REPS, "pool": pool_info, "by_design": tab.to_dict("records"),
           "control_same_sd": ctrl.to_dict("records"), "grid_summary": grid_sum}
    json.dump(out, open(RES / "a1104_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：割り方ごとの、選んだ条件の本当の手直しの割合と見かけの手直しの割合
    t = tab
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    x = np.arange(len(t))
    ax.bar(x - 0.2, t.pick_fail_mean, 0.4, color=BLUE, label="選んだ条件の本当の手直しの割合")
    ax.bar(x + 0.2, t.pick_obs_fail_mean, 0.4, color=LIGHT, label="試し塗りの板で見えた手直しの割合")
    for i, (a, b) in enumerate(zip(t.pick_fail_mean, t.pick_obs_fail_mean)):
        ax.text(i - 0.2, a + 0.15, f"{a:.2f}", ha="center", fontsize=7.5)
        ax.text(i + 0.2, b + 0.15, f"{b:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{k}通り\n×{rr}枚" for k, rr in ALLOC] + ["12通り×1枚\n→良い3通り\n×4枚"], fontsize=8)
    ax.set_ylim(0, max(t.pick_fail_mean.max(), t.pick_obs_fail_mean.max()) * 1.25)
    ax.set_ylabel("手直しの割合（%、4,000回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("24枚の割り方と、選んだ条件の手直しの割合（基本の置き方）")
    save(fig, "a1104_designs.png", SRC)

    # 図2：ばらつきの大きい条件を選んだ割合と、見かけの良く見えた分
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.2))
    lab = [f"{k}×{rr}" for k, rr in ALLOC] + ["2段"]
    axs[0].bar(np.arange(len(t)), t.pick_hi_sd_share, color=ORANGE)
    axs[0].axhline(25, color=GRAY, lw=1, ls="--"); axs[0].text(-0.4, 55, "点線：でたらめに選ぶと25%", fontsize=8, color=GRAY)
    for i, v in enumerate(t.pick_hi_sd_share):
        axs[0].text(i, v + 0.8, f"{v:.1f}", ha="center", fontsize=7)
    axs[0].set_ylim(0, 60); axs[0].set_xticks(np.arange(len(t))); axs[0].set_xticklabels(lab, fontsize=8, rotation=45)
    axs[0].set_title("ばらつきの大きい条件を選んだ割合（%）", fontsize=10)
    axs[1].bar(np.arange(len(t)), -t.pick_mean_gap_mean, color=BLUE)
    for i, v in enumerate(-t.pick_mean_gap_mean):
        axs[1].text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=7)
    axs[1].set_ylim(0, (-t.pick_mean_gap_mean).max() * 1.2)
    axs[1].set_xticks(np.arange(len(t))); axs[1].set_xticklabels(lab, fontsize=8, rotation=45)
    axs[1].set_title("見かけが本当より良く見えた分（むらの点）", fontsize=10)
    fig.text(0.5, -0.06, "条件の数×1条件あたりの枚数（2段は12通り×1枚→良い3通り×4枚）", ha="center", fontsize=9)
    fig.suptitle("1条件あたり3枚以下では、ばらつきの大きい条件を選ぶ割合が31.3〜47.2%に上がった（基本の置き方）", fontsize=12, y=1.04)
    save(fig, "a1104_variance_pick.png", SRC, y=-0.1)

    # 図3：置き方54通りで、いちばん手直しの少なかった割り方
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ks = [k for k, _ in ALLOC]
    c_h = gh.best_k.value_counts().reindex(ks, fill_value=0)
    c_s = grid[grid.sd_hetero == 0].best_k.value_counts().reindex(ks, fill_value=0)
    xl = [f"{k}通り" for k in ks]
    ax.bar(xl, c_s.values, color=GRAY, label="ばらつきが条件で同じ（18通り）")
    ax.bar(xl, c_h.values, bottom=c_s.values, color=BLUE, label="ばらつきが条件で違う（36通り）")
    for i, (a, b) in enumerate(zip(c_s.values, c_h.values)):
        ax.text(i, a + b + 0.3, str(a + b), ha="center", fontsize=9)
    ax.set_ylim(0, (c_s + c_h).max() * 1.3)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_ylabel("置き方の数（54通りのうち）")
    ax.set_xlabel("試した条件の数（残りの枚数は繰り返しに回す）")
    ax.set_title("選んだ条件の手直しがいちばん少なかった条件の数は、置き方で変わる")
    save(fig, "a1104_robust.png", SRC, y=-0.08)

    out["run_sec"] = r(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
