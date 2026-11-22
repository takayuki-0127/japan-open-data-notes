"""930 合格点ぎりぎりで落ちた人と受かった人は、どれだけ違うのか？（架空のデータ）

架空の社内資格試験（1問1点、合格点は固定）。受験者ごとに「実力」（同じ試験を何度も受けたときの平均の正答率）を置き、
当日の調子で実力が少し上下したうえで、1問ずつその確率で正解すると置く。
合格点の1問下で落ちた人と、合格点ちょうどで受かった人の、本当の実力の差と、もう一度受けたときの合否を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import beta as beta_dist, binom
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 930
SRC = "架空の社内資格試験（作成者が乱数で作成、seed 930）"
BASE = {"items": 100, "sd": 13.0, "day": 3.0, "cut_rate": 0.60}
MEAN = 55.0            # 実力の平均（100点満点に直した点）
N_BASE = 2_000_000


def ab(mean, sd):
    """平均・標準偏差（0〜1の割合）からベータ分布の a, b"""
    k = mean * (1 - mean) / sd ** 2 - 1
    return mean * k, (1 - mean) * k


def sit(rng, p, items, day):
    """実力 p（0〜1）の人が1回受けたときの得点（問題数）"""
    q = np.clip(p + rng.normal(0, day / 100, p.shape), 0, 1)
    return rng.binomial(items, q)


def p_greater(a, b):
    """a から1人・b から1人を選んだとき、a の実力が b より高い確率（同じ値は半分）"""
    b = np.sort(b)
    lo = np.searchsorted(b, a, "left")
    hi = np.searchsorted(b, a, "right")
    return float(((lo + hi) / 2).mean() / len(b))


def run(rng, n, items, sd, day, cut_rate):
    a, b = ab(MEAN / 100, sd / 100)
    p = rng.beta(a, b, n)
    x = sit(rng, p, items, day)
    x2 = sit(rng, p, items, day)            # もう一度受けたとき（実力は同じ）
    cut = int(round(cut_rate * items))
    t = p * 100
    below, just = x == cut - 1, x == cut
    obs = x / items * 100
    rel = float(np.var(t) / np.var(obs))   # 信頼性（本当の実力のばらつき÷得点のばらつき）
    out = {"items": items, "sd": sd, "day": day, "cut_rate": cut_rate, "cut": cut,
           "one_item_pts": 100 / items, "pass_rate": float((x >= cut).mean()), "reliability": rel,
           "n_below": int(below.sum()), "n_just": int(just.sum()),
           "true_below": float(t[below].mean()), "true_just": float(t[just].mean()),
           "gap_true_pts": float(t[just].mean() - t[below].mean()),
           "gap_ratio_to_one_item": float((t[just].mean() - t[below].mean()) / (100 / items)),
           "P_below_higher": p_greater(t[below], t[just]),
           "retest_pass_below": float((x2[below] >= cut).mean()), "retest_pass_just": float((x2[just] >= cut).mean()),
           "true_fail_all": float(t[x < cut].mean()), "true_pass_all": float(t[x >= cut].mean())}
    out["gap_all_pts"] = out["true_pass_all"] - out["true_fail_all"]
    return out, p, x, x2


GH_Z, GH_W = np.polynomial.hermite_e.hermegauss(31)
GH_W = GH_W / GH_W.sum()


def exact(items, sd, day, cut_rate, n_grid=4000):
    """乱数を使わない計算：実力を細かい目盛りに分け、当日の調子はガウス・エルミートの点で平均する"""
    a, b = ab(MEAN / 100, sd / 100)
    p = (np.arange(n_grid) + 0.5) / n_grid
    w = beta_dist.pdf(p, a, b); w /= w.sum()
    cut = int(round(cut_rate * items))
    zs = GH_Z if day > 0 else np.array([0.0])
    hs = GH_W if day > 0 else np.array([1.0])
    q = np.clip(p[:, None] + day / 100 * zs[None, :], 0, 1)
    pmf = lambda s: (binom.pmf(s, items, q) * hs).sum(1)
    sf = (binom.sf(cut - 1, items, q) * hs).sum(1)          # 合格点以上になる確率
    t = p * 100
    fb, fj = w * pmf(cut - 1), w * pmf(cut)
    fb, fj = fb / fb.sum(), fj / fj.sum()
    Fj = np.cumsum(fj) - fj
    ex = items * (q * hs).sum(1)
    vx = (items * q * (1 - q) * hs).sum(1) + items ** 2 * ((q ** 2 * hs).sum(1) - (q * hs).sum(1) ** 2)
    var_obs = ((w * (vx + ex ** 2)).sum() - (w * ex).sum() ** 2) * (100 / items) ** 2
    var_t = (w * t ** 2).sum() - (w * t).sum() ** 2
    wp, wf = w * sf, w * (1 - sf)
    o = {"items": items, "sd": sd, "day": day, "cut_rate": cut_rate, "cut": cut, "one_item_pts": 100 / items,
         "pass_rate": float(wp.sum()), "reliability": float(var_t / var_obs),
         "share_below": float((w * pmf(cut - 1)).sum()), "share_just": float((w * pmf(cut)).sum()),
         "true_below": float((fb * t).sum()), "true_just": float((fj * t).sum()),
         "P_below_higher": float((fb * (Fj + fj / 2)).sum()),
         "retest_pass_below": float((fb * sf).sum()), "retest_pass_just": float((fj * sf).sum()),
         "true_fail_all": float((wf * t).sum() / wf.sum()), "true_pass_all": float((wp * t).sum() / wp.sum())}
    o["gap_true_pts"] = o["true_just"] - o["true_below"]
    o["gap_ratio_to_one_item"] = o["gap_true_pts"] / (100 / items)
    o["gap_all_pts"] = o["true_pass_all"] - o["true_fail_all"]
    o["reliability_x_one_item"] = o["reliability"] * 100 / items
    return o


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base, p, x, x2 = run(rng, N_BASE, **{k: BASE[k] for k in ["items", "sd", "day", "cut_rate"]})
    cut = base["cut"]
    t = p * 100

    # 得点ごとの本当の実力
    rows = []
    for s in range(45, 76):
        m = x == s
        rows.append({"score": s, "n": int(m.sum()), "true_mean": t[m].mean(), "true_p10": np.percentile(t[m], 10),
                     "true_p90": np.percentile(t[m], 90), "share_true_ge_cut": (t[m] >= cut).mean(),
                     "retest_pass": (x2[m] >= cut).mean(), "retest_mean": x2[m].mean()})
    by_score = pd.DataFrame(rows).round(4)
    by_score.to_csv(RES / "by_score.csv", index=False)

    # 帯で比べる：合格点の k 問下〜1問下 と 合格点〜k−1問上
    bands = []
    for k in [1, 3, 5]:
        lo = (x >= cut - k) & (x < cut)
        hi = (x >= cut) & (x < cut + k)
        bands.append({"band_items": k, "fail_range": f"{cut-k}-{cut-1}", "pass_range": f"{cut}-{cut+k-1}",
                      "true_fail_band": t[lo].mean(), "true_pass_band": t[hi].mean(),
                      "gap_true_pts": t[hi].mean() - t[lo].mean(), "P_fail_band_higher": p_greater(t[lo], t[hi]),
                      "retest_pass_fail_band": (x2[lo] >= cut).mean(), "retest_pass_pass_band": (x2[hi] >= cut).mean()})
    bands = pd.DataFrame(bands).round(4)
    bands.to_csv(RES / "bands.csv", index=False)

    below, just = x == cut - 1, x == cut
    extra = {"share_below_true_ge_cut": float((t[below] >= cut).mean()),
             "share_just_true_lt_cut": float((t[just] < cut).mean()),
             "below_true_p10": float(np.percentile(t[below], 10)), "below_true_p90": float(np.percentile(t[below], 90)),
             "just_true_p10": float(np.percentile(t[just], 10)), "just_true_p90": float(np.percentile(t[just], 90)),
             "kelley_gap_pts": base["reliability"] * 1.0,
             "retest_just_minus_below_pt": (base["retest_pass_just"] - base["retest_pass_below"]) * 100,
             "max_abs_retest_mean_minus_true_mean_45_75": float((by_score.retest_mean - by_score.true_mean).abs().max()),
             "share_below_of_all": float(below.mean()), "share_just_of_all": float(just.mean())}

    # 確かめ：問題数 × 人どうしの差 × 当日の調子（36通り）と、合格点の位置（3通り）
    grid = []
    for i, items in enumerate([25, 50, 100, 200]):
        for j, sd in enumerate([8.0, 13.0, 18.0]):
            for k, day in enumerate([0.0, 3.0, 6.0]):
                grid.append(exact(items, sd, day, 0.60))
    for i, cr in enumerate([0.50, 0.60, 0.70]):
        grid.append(exact(100, 13.0, 3.0, cr))
    grid = pd.DataFrame(grid).round(4)
    ex_base = exact(**{k: BASE[k] for k in ["items", "sd", "day", "cut_rate"]})
    grid.to_csv(RES / "robustness.csv", index=False)
    g36 = grid.iloc[:36]
    g100 = g36[g36["items"] == 100]

    # data：最初の5,000人
    pd.DataFrame({"person": np.arange(1, 5001), "true_pts": np.round(t[:5000], 2), "score": x[:5000],
                  "retest_score": x2[:5000]}).to_csv(DATA / "exam_sample_5000.csv", index=False)

    rnd = lambda d: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}
    out = {"settings": {**BASE, "mean_pts": MEAN, "n_people": N_BASE, "seed": SEED},
           "base": rnd(base), "base_exact": rnd(ex_base),
           "max_abs_sim_minus_exact": round(max(abs(base[k] - ex_base[k]) for k in
                                                ["pass_rate", "true_below", "true_just", "P_below_higher",
                                                 "retest_pass_below", "retest_pass_just", "reliability"]), 4),
           "max_abs_sim_minus_exact_key": max(["pass_rate", "true_below", "true_just", "P_below_higher",
                                               "retest_pass_below", "retest_pass_just", "reliability"],
                                              key=lambda k: abs(base[k] - ex_base[k])),
           "base_extra": rnd(extra), "bands": bands.to_dict("records"),
           "grid36_ranges": {"gap_true_pts": [float(g36.gap_true_pts.min()), float(g36.gap_true_pts.max())],
                             "gap_ratio_to_one_item": [float(g36.gap_ratio_to_one_item.min()), float(g36.gap_ratio_to_one_item.max())],
                             "P_below_higher": [float(g36.P_below_higher.min()), float(g36.P_below_higher.max())],
                             "retest_pass_below": [float(g36.retest_pass_below.min()), float(g36.retest_pass_below.max())],
                             "retest_pass_just": [float(g36.retest_pass_just.min()), float(g36.retest_pass_just.max())],
                             "retest_just_minus_below_pt": [float(((g36.retest_pass_just - g36.retest_pass_below) * 100).min().round(2)),
                                                            float(((g36.retest_pass_just - g36.retest_pass_below) * 100).max().round(2))],
                             "gap_all_pts": [float(g36.gap_all_pts.min()), float(g36.gap_all_pts.max())],
                             "reliability": [float(g36.reliability.min()), float(g36.reliability.max())],
                             "abs_gap_minus_reliability_x_one_item_max": float(
                                 (g36.gap_true_pts - g36.reliability_x_one_item).abs().max())},
           "grid_items100_ranges": {"gap_true_pts": [float(g100.gap_true_pts.min()), float(g100.gap_true_pts.max())],
                                    "P_below_higher": [float(g100.P_below_higher.min()), float(g100.P_below_higher.max())]},
           "cut_position": grid.iloc[36:][["cut_rate", "cut", "pass_rate", "gap_true_pts", "P_below_higher",
                                           "retest_pass_below", "retest_pass_just"]].to_dict("records")}
    json.dump(out, open(RES / "a930_main.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

    # 図1：得点ごとの本当の実力
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    b = by_score
    ax.fill_between(b.score, b.true_p10, b.true_p90, color=LIGHT, alpha=.6, label="本当の実力の10〜90%の範囲")
    ax.plot(b.score, b.true_mean, "o-", color=BLUE, ms=3.5, label="本当の実力の平均")
    ax.plot(b.score, b.score, ":", color=GRAY, label="得点そのまま")
    ax.axvline(cut - 0.5, color=ORANGE, lw=1)
    ax.text(cut - 0.7, 76.5, "合格点60点", color=ORANGE, ha="right", fontsize=9)
    for s, col in [(cut - 1, ORANGE), (cut, BLUE)]:
        r = b[b.score == s].iloc[0]
        ax.plot(s, r.true_mean, "o", color=col, ms=7)
    r59, r60 = b[b.score == cut - 1].iloc[0], b[b.score == cut].iloc[0]
    ax.annotate(f"59点の人 {r59.true_mean:.1f}点\n60点の人 {r60.true_mean:.1f}点", (cut, r60.true_mean), (cut + 3.5, 51),
                fontsize=9, arrowprops={"arrowstyle": "-", "color": GRAY})
    ax.set_xlabel("その回の得点（100問・1問1点）"); ax.set_ylabel("本当の実力（何度も受けたときの平均の点）")
    ax.set_ylim(40, 80); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("1点の差は、本当の実力ではもっと小さい（200万人）", fontsize=11.5)
    save(fig, "a930_true_by_score.png", SRC)

    # 図2：59点の人と60点の人の本当の実力の分布
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    bins = np.arange(40, 80.5, 1)
    ax.hist(t[below], bins=bins, density=True, histtype="step", lw=2, color=ORANGE,
            label=f"59点で落ちた人（{base['n_below']:,}人）")
    ax.hist(t[just], bins=bins, density=True, histtype="step", lw=2, color=BLUE,
            label=f"60点で受かった人（{base['n_just']:,}人）")
    ax.axvline(cut, color=GRAY, lw=.8, ls=":")
    ax.set_xlabel("本当の実力（点）"); ax.set_ylabel("人の割合（1点ごと）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"2つの山はほぼ重なる：59点の人のほうが実力が上の組は{base['P_below_higher']*100:.1f}%", fontsize=11.5)
    save(fig, "a930_two_groups.png", SRC)

    # 図3：置き方を変えると（1問の差が本当の実力で何問分か／59点側が上の確率）
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 3.9))
    for sd, col in [(8.0, ORANGE), (13.0, BLUE), (18.0, GREEN)]:
        s = g36[(g36.sd == sd) & (g36.day == 3.0)].sort_values("items")
        axs[0].plot(s["items"], s.gap_ratio_to_one_item, "o-", color=col, label=f"実力の標準偏差 {sd:.0f}点")
        axs[1].plot(s["items"], s.P_below_higher * 100, "o-", color=col, label=f"実力の標準偏差 {sd:.0f}点")
    axs[0].set_ylabel("本当の実力の差（1問分を1とする）"); axs[0].set_ylim(0, 1)
    axs[0].set_title("1問差が、本当の実力で何問分の差か", fontsize=10.5)
    axs[1].set_ylabel("落ちた人のほうが実力が上の組（%）"); axs[1].set_ylim(38, 50.5)
    axs[1].axhline(50, color=GRAY, lw=.8, ls=":")
    axs[1].set_title("合格点の1問下の人が、ちょうどの人より上の確率", fontsize=10.5)
    for ax in axs:
        ax.set_xscale("log"); ax.minorticks_off(); ax.set_xticks([25, 50, 100, 200]); ax.set_xticklabels(["25", "50", "100", "200"])
        ax.set_xlabel("問題数")
    axs[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle("合格点は6割・当日の調子の振れ3点と置いた場合（乱数を使わない計算）", fontsize=11)
    fig.tight_layout()
    save(fig, "a930_by_items.png", SRC)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
