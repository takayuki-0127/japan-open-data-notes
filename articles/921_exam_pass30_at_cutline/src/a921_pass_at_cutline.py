"""921 合格率30%の試験で、実力は合格ラインちょうどの人は何%受かるのか？（架空のデータ）

架空の社内資格試験（1問1点）。受験者ごとに「実力」（同じ試験を何度も受けたときの平均の正答率）を置き、
1問ずつ実力の確率で正解すると置く。合格点は毎回、得点の上から30%目の人の点（その点以上は全員合格）。
「実力が合格ラインちょうど」を2通りに決め、受かる確率を数える。
"""
import json
import time
from functools import lru_cache
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import binom
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 921
SRC = "架空の社内資格試験（作成者が乱数で作成、seed 921）"
rng = np.random.default_rng(SEED)
BASE = {"items": 100, "sd": 13.0, "n_exam": 2000, "rate": 0.30}
MEAN = 55.0          # 実力の平均（100点満点に直した点）


def ab(mean, sd):
    """平均・標準偏差（0〜1の割合）からベータ分布の a, b"""
    v = sd ** 2
    k = mean * (1 - mean) / v - 1
    return mean * k, (1 - mean) * k


def abilities(rng, size, sd):
    a, b = ab(MEAN / 100, sd / 100)
    return rng.beta(a, b, size)


def cut_of(scores, rate):
    """得点の上から rate 目の人の点（その点以上は合格）。scores は (回, 人)"""
    k = int(np.ceil(rate * scores.shape[-1])) - 1
    return -np.sort(-scores, axis=-1)[..., k]


def cut_dist(rng, items, sd, n_exam, rate, reps):
    """合格点の分布：回ごとに受験者を作り直す"""
    cuts = np.empty(reps, int)
    pass_rate = np.empty(reps)
    step = max(1, 2_000_000 // n_exam)
    for s in range(0, reps, step):
        m = min(step, reps - s)
        p = abilities(rng, (m, n_exam), sd)
        x = rng.binomial(items, p)
        c = cut_of(x, rate)
        cuts[s:s + m] = c
        pass_rate[s:s + m] = (x >= c[:, None]).mean(1)
    vals, cnt = np.unique(cuts, return_counts=True)
    return vals, cnt / reps, float(pass_rate.mean())


def p_pass(true_score, items, vals, w):
    """実力（100点満点の点）の人が受かる確率：合格点の分布で平均"""
    p = np.clip(np.asarray(true_score, float) / 100, 0, 1)
    out = (binom.sf(vals[None, :] - 1, items, np.atleast_1d(p)[:, None]) * w[None, :]).sum(-1)
    return out if p.ndim else float(out[0])


@lru_cache(None)
def ability_quantile(q, sd):
    """実力の分布の q 分位（100点満点）。乱数で求める"""
    g = np.random.default_rng(SEED + 7)
    return float(np.quantile(abilities(g, 2_000_000, sd), q) * 100)


def summarize(items, sd, n_exam, rate, reps, rng):
    vals, w, pr = cut_dist(rng, items, sd, n_exam, rate, reps)
    cut_pts = vals / items * 100                       # 合格点を100点満点に直す
    med_cut = float(cut_pts[np.argmax(np.cumsum(w) >= 0.5)])
    line_rank = ability_quantile(1 - rate, sd)         # 実力の順で上から rate ちょうど
    grid = np.arange(0, 100.01, 0.05)
    pp = p_pass(grid, items, vals, w)
    need90 = float(grid[np.argmax(pp >= 0.9)])
    need10 = float(grid[np.argmax(pp >= 0.1)])
    need50 = float(grid[np.argmax(pp >= 0.5)])
    # 受かる確率が1〜9割の人の割合（実力の分布で数える）
    g = np.random.default_rng(SEED + 11)
    t = abilities(g, 200_000, sd) * 100
    pt = np.interp(t, grid, pp)
    return {"items": items, "sd": sd, "n_exam": n_exam, "rate": rate,
            "actual_pass_rate": round(pr, 4),
            "cut_median_pts": round(med_cut, 2),
            "cut_p10_pts": round(float(cut_pts[np.argmax(np.cumsum(w) >= 0.1)]), 2),
            "cut_p90_pts": round(float(cut_pts[np.argmax(np.cumsum(w) >= 0.9)]), 2),
            "line_rank_pts": round(line_rank, 2),
            "cut_minus_rankline": round(med_cut - line_rank, 2),
            "P_at_cut": round(float(p_pass(med_cut, items, vals, w)), 4),
            "P_at_rankline": round(float(p_pass(line_rank, items, vals, w)), 4),
            "need50_minus_cut": round(need50 - med_cut, 2),
            "need90_minus_cut": round(need90 - med_cut, 2),
            "need10_minus_cut": round(need10 - med_cut, 2),
            "share_uncertain_10_90": round(float(((pt > 0.1) & (pt < 0.9)).mean()), 4),
            "_vals": vals, "_w": w, "_grid": grid, "_pp": pp}


def public(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def main():
    t0 = time.time()
    # 基本の置き方
    base = summarize(BASE["items"], BASE["sd"], BASE["n_exam"], BASE["rate"], 4000, rng)
    vals, w = base["_vals"], base["_w"]

    # 合格点を固定したとき（基本の置き方で合格率が30%前後になる点＝合格点の中央値）
    fixed_cut = int(round(base["cut_median_pts"] / 100 * BASE["items"]))
    fv, fw = np.array([fixed_cut]), np.array([1.0])
    fixed = {"fixed_cut": fixed_cut,
             "P_at_cut": round(float(p_pass(fixed_cut, BASE["items"], fv, fw)), 4),
             "P_at_rankline": round(float(p_pass(base["line_rank_pts"], BASE["items"], fv, fw)), 4),
             "P_at_cut_minus_half_point": round(float(p_pass(fixed_cut - 0.5, BASE["items"], fv, fw)), 4),
             "P_score_exactly_cut": round(float(binom.pmf(fixed_cut, BASE["items"], fixed_cut / BASE["items"])), 4)}

    # 合格点の分布（基本・受験者50人）
    small = summarize(BASE["items"], BASE["sd"], 50, BASE["rate"], 40000, rng)

    # 実力ごとの受かる確率（表）
    rows = []
    for d in [-10, -5, -3, -1, 0, 1, 3, 5, 10]:
        t = base["cut_median_pts"] + d
        rows.append({"true_minus_cut": d, "true_score": round(t, 2),
                     "P_pass_2000": round(float(p_pass(t, BASE["items"], vals, w)), 4),
                     "P_pass_50": round(float(p_pass(t, BASE["items"], small["_vals"], small["_w"])), 4)})
    curve = pd.DataFrame(rows)
    curve.to_csv(RES / "pass_prob_by_ability.csv", index=False)

    # 頑健性：問題数×実力の散らばり×合格率×受験者数
    rob = []
    for items in [20, 50, 100, 200]:
        for sd in [8.0, 13.0, 18.0]:
            for rate in [0.10, 0.30, 0.50]:
                for n_exam in [50, 2000]:
                    reps = 3000 if n_exam == 50 else 400
                    rob.append(public(summarize(items, sd, n_exam, rate, reps, rng)))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    r30 = rob[rob.rate == 0.30]

    # 1回分の受験者（data）
    p = abilities(rng, BASE["n_exam"], BASE["sd"])
    x = rng.binomial(BASE["items"], p)
    c1 = int(cut_of(x[None, :], BASE["rate"])[0])
    one = pd.DataFrame({"id": np.arange(1, BASE["n_exam"] + 1), "true_score": np.round(p * 100, 2), "score": x,
                        "passed": (x >= c1).astype(int)})
    one["p_pass"] = np.round(p_pass(one.true_score.values, BASE["items"], vals, w), 4)
    one.to_csv(DATA / "exam_one_session.csv", index=False)
    top_true = one.true_score >= one.true_score.quantile(0.7)
    one_res = {"cut": c1, "pass_rate": round(float(one.passed.mean()), 4),
               "near_cut_people_within_2pts": int((one.true_score - c1).abs().le(2).sum()),
               "near_cut_pass_rate": round(float(one.passed[(one.true_score - c1).abs() <= 2].mean()), 4),
               "passers_not_top30_by_ability": round(float((~top_true[one.passed == 1]).mean()), 4)}

    out = {"base": public(base), "fixed_cut": fixed, "small_50": public(small),
           "cut_dist_2000": {str(int(v)): round(float(q), 4) for v, q in zip(vals, w)},
           "cut_dist_50_p10_p90": [small["cut_p10_pts"], small["cut_p90_pts"]],
           "curve": curve.to_dict("records"),
           "robust_rate30": {"P_at_cut_min": float(r30.P_at_cut.min()), "P_at_cut_max": float(r30.P_at_cut.max()),
                             "P_at_rankline_min": float(r30.P_at_rankline.min()),
                             "P_at_rankline_max": float(r30.P_at_rankline.max()),
                             "need90_min": float(r30.need90_minus_cut.min()),
                             "need90_max": float(r30.need90_minus_cut.max()),
                             "uncertain_min": float(r30.share_uncertain_10_90.min()),
                             "uncertain_max": float(r30.share_uncertain_10_90.max())},
           "robust_all": {"P_at_cut_min": float(rob.P_at_cut.min()), "P_at_cut_max": float(rob.P_at_cut.max()),
                          "P_at_rankline_min": float(rob.P_at_rankline.min()),
                          "P_at_rankline_max": float(rob.P_at_rankline.max())},
           "robust_by_rate": {str(r): {"P_at_cut_min": float(q.P_at_cut.min()), "P_at_cut_max": float(q.P_at_cut.max()),
                                       "P_at_rankline_min": float(q.P_at_rankline.min()),
                                       "P_at_rankline_max": float(q.P_at_rankline.max()),
                                       "need90_min": float(q.need90_minus_cut.min()),
                                       "need90_max": float(q.need90_minus_cut.max())}
                              for r, q in rob.groupby("rate")},
           "one_session": one_res}
    json.dump(out, open(RES / "a921_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：実力と受かる確率
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    g = base["_grid"]
    ax.plot(g, base["_pp"] * 100, color=BLUE, lw=2, label="受験者2,000人の回")
    ax.plot(small["_grid"], small["_pp"] * 100, color=ORANGE, lw=1.6, ls="--", label="受験者50人の回")
    ax.axvline(base["cut_median_pts"], color=GRAY, lw=1, ls=":")
    ax.text(base["cut_median_pts"] + 0.6, 8, f"合格点 {base['cut_median_pts']:.0f}点", color=INK, fontsize=9)
    ax.axhline(50, color=GRAY, lw=0.8)
    ax.set_xlim(base["cut_median_pts"] - 25, base["cut_median_pts"] + 25); ax.set_ylim(0, 100)
    ax.set_xlabel("実力（何度も受けたときの平均点、100問）"); ax.set_ylabel("受かる確率（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"実力が合格点ちょうどの人が受かる確率は{base['P_at_cut']*100:.0f}%"
                 f"（9割受かるには合格点より{base['need90_minus_cut']:.1f}点上）")
    save(fig, "a921_pass_curve.png", SRC)

    # 図2：合格点の振れ（2,000人と50人）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(vals - 0.2, w * 100, width=0.4, color=BLUE, label="受験者2,000人の回")
    ax.bar(small["_vals"] + 0.2, small["_w"] * 100, width=0.4, color=ORANGE, label="受験者50人の回")
    ax.set_xlabel("その回の合格点（上から30%目の人の点、100問）"); ax.set_ylabel("回の割合（%）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_xlim(small["cut_p10_pts"] - 6, small["cut_p90_pts"] + 6)
    ax.set_xticks(np.arange(int(small["cut_p10_pts"]) - 5, int(small["cut_p90_pts"]) + 6, 2))
    ax.set_title("受験者が少ない回ほど、合格点そのものが回ごとに動く")
    save(fig, "a921_cut_by_session.png", SRC)

    # 図3：頑健性（合格率30%、受験者2,000人）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    sub = rob[(rob.rate == 0.30) & (rob.n_exam == 2000)]
    cols = {8.0: LIGHT, 13.0: BLUE, 18.0: INK}
    for sd, gq in sub.groupby("sd"):
        ax.plot(gq["items"], gq.need90_minus_cut, marker="o", color=cols[sd], label=f"実力の散らばり {sd:.0f}点")
    ax.set_xscale("log"); ax.set_xticks([20, 50, 100, 200]); ax.set_xticklabels(["20問", "50問", "100問", "200問"])
    ax.minorticks_off()
    ax.set_ylabel("9割受かるのに要る実力（合格点より何点上か）")
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("問題数が少ないほど、合格点より大きく上の実力が要る（合格率30%）")
    save(fig, "a921_need90_by_items.png", SRC)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps({k: out[k] for k in ["base", "fixed_cut", "small_50", "robust_rate30", "robust_by_rate",
                                          "one_session", "run_sec"]}, ensure_ascii=False, indent=1))
    print(curve)


if __name__ == "__main__":
    main()
