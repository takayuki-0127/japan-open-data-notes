"""1110 2つの条件を別々に試した効き目を足して見込むと、組み合わせたときとどれだけずれるのか？（架空のデータ）

架空の陶芸工房が、器の釉薬（うわぐすり）のむらを減らす工夫を8つ考え、いつもの作り方と、工夫を1つずつ入れた作り方を
それぞれ n 個ずつ焼いて「むらの出た器の割合」を数える。そのあと、2つの工夫を組み合わせたときのむらの割合を
①足し算（いつもの割合＋それぞれの減った分）、②割合の掛け算（いつもの割合×それぞれの「何倍になったか」）で見込む。
本当のむらの割合は作成者が置く：むらの出やすさ（対数オッズ）＝いつも＋工夫ごとの効き目＋2つを組み合わせたときの上乗せ。
見込みと本当の値のずれ、見込みでいちばん良い組を選んだときの「見込みより悪かった分」を数える。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1110
SRC = "架空の陶芸工房の試し焼き（作成者が置いた効き目からの乱数、seed 1110）"
K = 8                                    # 工夫の数
PAIRS = list(itertools.combinations(range(K), 2))   # 28組
BASE = {"p0": 0.20, "beta_mean": -0.4, "beta_sd": 0.3, "tau": 0.3, "n": 400}
W_MAIN = 4000                            # 工房の数（基本）
W_GRID = 1000
GRID_TAU = [0.0, 0.3, 0.6]
GRID_P0 = [0.08, 0.20, 0.35]
GRID_N = [100, 400, 1600]


def r(x, d=2):
    return round(float(x), d)


def logit(p):
    return np.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-x))


def make_truth(rng, W, p0, beta_mean, beta_sd, tau):
    b0 = logit(p0)
    beta = rng.normal(beta_mean, beta_sd, (W, K))
    gam = rng.normal(0, tau, (W, len(PAIRS))) if tau > 0 else np.zeros((W, len(PAIRS)))
    I = np.array([a for a, _ in PAIRS]); J = np.array([b for _, b in PAIRS])
    p_single = expit(b0 + beta)                                  # (W,K)
    p_pair = expit(b0 + beta[:, I] + beta[:, J] + gam)           # (W,28)
    return np.full(W, p0), p_single, p_pair, I, J


def observe(rng, p, n):
    return rng.binomial(n, p) / n


def predict(p0h, psh, I, J):
    add = p0h[:, None] + (psh[:, I] - p0h[:, None]) + (psh[:, J] - p0h[:, None])
    with np.errstate(divide="ignore", invalid="ignore"):
        mult = np.where(p0h[:, None] > 0, psh[:, I] * psh[:, J] / p0h[:, None], 0.0)   # いつもが0個なら0と見込む
    return add, mult


def run(rng, W, p0, beta_mean, beta_sd, tau, n, noise=True):
    p0t, pst, ppt, I, J = make_truth(rng, W, p0, beta_mean, beta_sd, tau)
    if noise:
        p0h, psh, pph = observe(rng, p0t, n), observe(rng, pst, n), observe(rng, ppt, n)
    else:
        p0h, psh, pph = p0t.copy(), pst.copy(), ppt.copy()
    add, mult = predict(p0h, psh, I, J)
    rows = np.arange(W)
    out = {}
    for name, pred in [("add", add), ("mult", mult), ("direct", pph)]:
        err = (pred - ppt) * 100                                  # ポイント
        k = np.nanargmin(pred, axis=1)                            # 見込みでいちばん良い組
        gap = (ppt[rows, k] - pred[rows, k]) * 100                # 見込みより悪かった分（＋が悪い）
        best = np.argmin(ppt, axis=1)
        out[name] = {
            "all_pairs_mean_err_pt": r(np.nanmean(err)),
            "all_pairs_mean_abs_err_pt": r(np.nanmean(np.abs(err))),
            "all_pairs_share_abs_err_over_2pt": r(np.nanmean(np.abs(err) > 2) * 100, 2),
            "chosen_pred_pct": r(np.mean(pred[rows, k]) * 100),
            "chosen_true_pct": r(np.mean(ppt[rows, k]) * 100),
            "chosen_gap_pt": r(np.mean(gap)),
            "chosen_gap_p10_pt": r(np.percentile(gap, 10)),
            "chosen_gap_p90_pt": r(np.percentile(gap, 90)),
            "chosen_is_true_best_pct": r(np.mean(k == best) * 100, 2),
            "pred_negative_pairs_pct": r(np.nanmean(pred < 0) * 100, 2),
        }
    out["same_choice_add_mult_pct"] = r(np.mean(np.argmin(add, 1) == np.argmin(mult, 1)) * 100, 2)
    out["true_best_pct"] = r(np.mean(ppt.min(1)) * 100)
    out["true_single_mean_pct"] = r(np.mean(pst) * 100)
    out["true_pair_mean_pct"] = r(np.mean(ppt) * 100)
    return out, (p0t, pst, ppt, p0h, psh, pph, add, mult, I, J)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    b = BASE

    # 1) 1つの工房の例（data に置く）
    _, (p0t, pst, ppt, p0h, psh, pph, add, mult, I, J) = run(
        np.random.default_rng(SEED), 1, b["p0"], b["beta_mean"], b["beta_sd"], b["tau"], b["n"])
    ex = pd.DataFrame({"pair": [f"{i+1}+{j+1}" for i, j in PAIRS],
                       "kufu_a": I + 1, "kufu_b": J + 1,
                       "true_a_pct": pst[0, I] * 100, "true_b_pct": pst[0, J] * 100,
                       "true_pair_pct": ppt[0] * 100,
                       "obs_base_pct": np.full(len(PAIRS), p0h[0] * 100),
                       "obs_a_pct": psh[0, I] * 100, "obs_b_pct": psh[0, J] * 100,
                       "pred_add_pct": add[0] * 100, "pred_mult_pct": mult[0] * 100,
                       "obs_pair_direct_pct": pph[0] * 100})
    ex.round(4).to_csv(DATA / "example_workshop_pairs.csv", index=False)
    k_add = int(np.argmin(add[0])); k_true = int(np.argmin(ppt[0]))
    example = {"obs_base_pct": r(p0h[0] * 100, 2),
               "chosen_pair_add": ex.pair[k_add], "chosen_pred_add_pct": r(add[0, k_add] * 100, 2),
               "chosen_pred_mult_pct": r(mult[0, k_add] * 100, 2), "chosen_true_pct": r(ppt[0, k_add] * 100, 2),
               "true_best_pair": ex.pair[k_true], "true_best_pct": r(ppt[0, k_true] * 100, 2),
               "add_mean_abs_err_pt": r(np.mean(np.abs(add[0] - ppt[0])) * 100, 2),
               "mult_mean_abs_err_pt": r(np.mean(np.abs(mult[0] - ppt[0])) * 100, 2),
               "add_below_true_pairs": int(np.sum(add[0] < ppt[0]))}

    # 2) 基本の置き方（4,000工房）と、ずれの中身（しくみを1つずつ入れる）
    scen = [("①割合で効くだけ（上乗せなし・試しのぶれなし）", 0.0, False),
            ("②上乗せあり・試しのぶれなし", b["tau"], False),
            ("③上乗せなし・試しのぶれあり", 0.0, True),
            ("④上乗せあり・試しのぶれあり（基本）", b["tau"], True)]
    comp = []
    main_out = None
    for si, (name, tau, noise) in enumerate(scen):
        o, _ = run(np.random.default_rng(SEED * 100 + si), W_MAIN, b["p0"], b["beta_mean"], b["beta_sd"], tau, b["n"], noise)
        if si == 3:
            main_out = o
        for m in ["add", "mult", "direct"]:
            if m == "direct" and not noise:
                continue
            comp.append({"scenario": name, "method": {"add": "足し算", "mult": "割合の掛け算", "direct": "組み合わせを直接試す"}[m], **o[m]})
    comp = pd.DataFrame(comp)
    comp.to_csv(RES / "components.csv", index=False)

    # 式どおりの値：上乗せなし・ぶれなしで、足し算と割合の掛け算の差（効き目 β がみな平均のときの1組）
    p0 = b["p0"]; ps = float(expit(logit(p0) + b["beta_mean"])); pp = float(expit(logit(p0) + 2 * b["beta_mean"]))
    formula = {"single_pct": r(ps * 100), "pair_true_pct": r(pp * 100),
               "pair_add_pct": r((2 * ps - p0) * 100), "pair_mult_pct": r(ps * ps / p0 * 100),
               "add_gap_pt": r((pp - (2 * ps - p0)) * 100), "mult_gap_pt": r((pp - ps * ps / p0) * 100)}

    # 3) 確かめ：上乗せの大きさ×いつもの割合×1つあたりの個数（27通り）
    grid = []
    for gi, (tau, p0g, n) in enumerate(itertools.product(GRID_TAU, GRID_P0, GRID_N)):
        o, _ = run(np.random.default_rng(SEED * 1000 + gi), W_GRID, p0g, b["beta_mean"], b["beta_sd"], tau, n)
        grid.append({"tau": tau, "p0_pct": p0g * 100, "n": n,
                     "add_all_mean_err_pt": o["add"]["all_pairs_mean_err_pt"],
                     "mult_all_mean_err_pt": o["mult"]["all_pairs_mean_err_pt"],
                     "add_all_mean_abs_err_pt": o["add"]["all_pairs_mean_abs_err_pt"],
                     "mult_all_mean_abs_err_pt": o["mult"]["all_pairs_mean_abs_err_pt"],
                     "direct_all_mean_abs_err_pt": o["direct"]["all_pairs_mean_abs_err_pt"],
                     "add_chosen_gap_pt": o["add"]["chosen_gap_pt"],
                     "mult_chosen_gap_pt": o["mult"]["chosen_gap_pt"],
                     "add_chosen_is_best_pct": o["add"]["chosen_is_true_best_pct"],
                     "mult_chosen_is_best_pct": o["mult"]["chosen_is_true_best_pct"],
                     "add_pred_negative_pct": o["add"]["pred_negative_pairs_pct"],
                     "same_choice_pct": o["same_choice_add_mult_pct"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    gr = lambda c: [r(grid[c].min()), r(grid[c].max())]
    cg = lambda sc, m: float(comp[(comp.scenario == scen[sc][0]) & (comp.method == m)].chosen_gap_pt.iloc[0])
    decomp = {"add_from_noise_no_interaction": r(cg(2, "足し算") - cg(0, "足し算")),
              "mult_from_noise_no_interaction": r(cg(2, "割合の掛け算") - cg(0, "割合の掛け算")),
              "add_from_interaction_no_noise": r(cg(1, "足し算") - cg(0, "足し算")),
              "mult_from_interaction_no_noise": r(cg(1, "割合の掛け算") - cg(0, "割合の掛け算"))}
    out = {"base": BASE, "workshops": W_MAIN, "pairs_per_workshop": len(PAIRS), "decomposition_diffs": decomp,
           "example_workshop": example, "main": main_out, "formula_one_pair": formula,
           "grid_ranges": {c: gr(c) for c in grid.columns if c not in ("tau", "p0_pct", "n", "same_choice_pct")},
           "grid_add_gap_gt_mult_gap_count": int((grid.add_chosen_gap_pt > grid.mult_chosen_gap_pt).sum()),
           "grid_add_abs_gt_mult_abs_count": int((grid.add_all_mean_abs_err_pt > grid.mult_all_mean_abs_err_pt).sum()),
           "grid_tau0_add_gap_range": [r(grid[grid.tau == 0].add_chosen_gap_pt.min()), r(grid[grid.tau == 0].add_chosen_gap_pt.max())],
           "grid_tau0_mult_gap_range": [r(grid[grid.tau == 0].mult_chosen_gap_pt.min()), r(grid[grid.tau == 0].mult_chosen_gap_pt.max())],
           "grid_tau06_mult_gap_range": [r(grid[grid.tau == 0.6].mult_chosen_gap_pt.min()), r(grid[grid.tau == 0.6].mult_chosen_gap_pt.max())],
           "grid_mult_gap_positive_count": int((grid.mult_chosen_gap_pt > 0).sum()),
           "grid_count": len(grid), "grid_same_choice_min_pct": r(grid.same_choice_pct.min(), 2)}
    json.dump(out, open(RES / "a1110_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の工房、28組の見込みと本当
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    lim = max(ex[["true_pair_pct", "pred_add_pct", "pred_mult_pct"]].max()) * 1.08
    lo = min(0, ex.pred_add_pct.min() * 1.1)
    ax.plot([lo, lim], [lo, lim], color=GRAY, lw=1)
    ax.scatter(ex.true_pair_pct, ex.pred_add_pct, color=ORANGE, s=30, label="足し算の見込み")
    ax.scatter(ex.true_pair_pct, ex.pred_mult_pct, color=BLUE, s=30, marker="s", label="割合の掛け算の見込み")
    ax.set_xlim(lo, lim); ax.set_ylim(lo, lim)
    ax.set_xlabel("組み合わせたときの本当のむらの割合（%）"); ax.set_ylabel("1つずつの試しからの見込み（%）")
    ax.set_title(f"例の工房：足し算の見込みは28組中{example['add_below_true_pairs']}組で本当より低い", loc="left")
    ax.text(lo + (lim - lo) * 0.03, lim * 0.93, "灰色の線より下＝見込みが良すぎる", color=GRAY, fontsize=9)
    ax.legend(loc="lower right", frameon=False)
    save(fig, "a1110_example.png", SRC)

    # 図2：見込みでいちばん良い組を選んだとき、見込みより悪かった分
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    names = [s[0] for s in scen]
    short = ["①割合で効くだけ\n（上乗せなし・\n試しのぶれなし）", "②上乗せあり・\n試しのぶれなし", "③上乗せなし・\n試しのぶれあり", "④上乗せあり・\n試しのぶれあり\n（基本）"]
    x = np.arange(len(names)); wdt = 0.36
    va = [comp[(comp.scenario == s) & (comp.method == "足し算")].chosen_gap_pt.iloc[0] for s in names]
    vm = [comp[(comp.scenario == s) & (comp.method == "割合の掛け算")].chosen_gap_pt.iloc[0] for s in names]
    b1 = ax.bar(x - wdt / 2, va, wdt, color=ORANGE, label="足し算の見込み")
    b2 = ax.bar(x + wdt / 2, vm, wdt, color=BLUE, label="割合の掛け算の見込み")
    for bars in (b1, b2):
        for bb in bars:
            h = bb.get_height()
            ax.text(bb.get_x() + bb.get_width() / 2, h + (0.04 if h >= 0 else -0.04), f"{h:.2f}",
                    ha="center", va="bottom" if h >= 0 else "top", fontsize=9)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=9)
    ax.set_ylabel("本当のむらの割合−見込み（ポイント）")
    ax.set_title("見込みでいちばん良い組を選んだとき、本当−見込み（4,000工房の平均）", loc="left", fontsize=12)
    ax.legend(frameon=False, loc="upper left")
    ax.text(0.99, 0.97, f"＋は見込みより悪い。選ぶ組はどちらの見込みでも同じ（{main_out['same_choice_add_mult_pct']:g}%）", transform=ax.transAxes,
            ha="right", va="top", fontsize=9, color=GRAY)
    ymax = max(max(va), max(vm)); ymin = min(0, min(va), min(vm))
    ax.set_ylim(ymin - 0.3 if ymin < 0 else 0, ymax * 1.25)
    save(fig, "a1110_chosen_gap.png", SRC)

    # 図3：確かめの27通り
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), sharey=True)
    for ax, tau in zip(axes, GRID_TAU):
        g = grid[grid.tau == tau]
        for n, mk in zip(GRID_N, ["o", "s", "^"]):
            gg = g[g.n == n]
            ax.plot(gg.p0_pct, gg.add_chosen_gap_pt, color=ORANGE, marker=mk, lw=1.2, label=f"足し算（{n}個ずつ）")
            ax.plot(gg.p0_pct, gg.mult_chosen_gap_pt, color=BLUE, marker=mk, lw=1.2, ls="--", label=f"掛け算（{n}個ずつ）")
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_title(f"上乗せの大きさ {tau}", fontsize=11, loc="left")
        ax.set_xlabel("いつものむらの割合（%）"); ax.set_xticks([v * 100 for v in GRID_P0])
    axes[0].set_ylabel("選んだ組の本当−見込み（ポイント）")
    axes[2].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fig.suptitle("確かめの27通り：選んだ組の見込みは、27通りすべてで足し算のほうが大きく外れた", x=0.01, y=1.04, ha="left", fontsize=12)
    save(fig, "a1110_robust.png", SRC)

    print(json.dumps({k: out[k] for k in ["example_workshop", "main", "formula_one_pair"]}, ensure_ascii=False, indent=1))
    print(comp.to_string()); print(grid.to_string())
    print({k: out[k] for k in out if k.startswith("grid_")})
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
