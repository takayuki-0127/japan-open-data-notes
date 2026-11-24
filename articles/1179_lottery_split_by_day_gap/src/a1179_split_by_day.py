"""1179 日にちごとに分けて抽選すると、混む日と空いた日の当たりやすさは何倍開くのか？（架空のデータ）

架空の体験会を5日間（A日〜E日、各日の定員100人）開く。申し込む人は5日のうち1日だけを選んで申し込み、
抽選は日ごとに行う（その日の申し込みが定員以下なら全員当たる）。
日ごとの申し込みの見込みの割合・申し込みの総数・回ごとの人気の振れを作成者が置き、乱数で申し込み数を作る。
"""
import json, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1179
SRC = "架空の体験会の日ごとの抽選（作成者が置いた申し込みの見込みからの乱数、seed 1179）"
DAYS = ["A日", "B日", "C日", "D日", "E日"]
CAP = 100
SHARES = {"flat": [0.2, 0.2, 0.2, 0.2, 0.2],
          "base": [0.32, 0.26, 0.2, 0.13, 0.09],
          "strong": [0.45, 0.25, 0.15, 0.1, 0.05]}
SHARE_JP = {"flat": "そろう（各20%）", "base": "基本（32〜9%）", "strong": "強い（45〜5%）"}
REPS = 2000


def simulate(rng, total, shares, noise, reps=REPS):
    """回ごとの日ごとの申し込み数と当たる見込み"""
    lam = total * np.array(shares)[None, :] * np.exp(rng.normal(0, noise, (reps, 5)) - noise ** 2 / 2)
    n = rng.poisson(lam)
    win = np.minimum(n, CAP)
    p = np.where(n > 0, win / np.maximum(n, 1), 1.0)  # その日に申し込んだ人の当たる見込み
    return n, win, p


def summarize(n, win, p):
    N = n.sum(1)
    pmax, pmin = p.max(1), p.min(1)  # いちばん当たりやすい日・いちばん当たりにくい日
    ratio = pmax / pmin
    overall_read = np.minimum(1, 5 * CAP / N)  # 全体の倍率から読む見込み
    actual_all = win.sum(1) / N  # 申し込んだ人全体で当たった割合
    under = (n < CAP)
    busiest = n.argmax(1)
    p_busy = p[np.arange(len(p)), busiest]
    return {
        "ratio_median": round(float(np.median(ratio)), 3),
        "ratio_p10": round(float(np.quantile(ratio, .1)), 3),
        "ratio_p90": round(float(np.quantile(ratio, .9)), 3),
        "p_hardest_mean_pct": round(float(pmin.mean() * 100), 2),
        "p_easiest_mean_pct": round(float(pmax.mean() * 100), 2),
        "overall_read_mean_pct": round(float(overall_read.mean() * 100), 2),
        "actual_all_mean_pct": round(float(actual_all.mean() * 100), 2),
        "hardest_vs_read_ratio": round(float(np.median(pmin / overall_read)), 3),
        "share_rounds_some_day_under_cap_pct": round(float(under.any(1).mean() * 100), 2),
        "empty_seats_mean": round(float((CAP - win).sum(1).mean()), 2),
        "share_rounds_busiest_is_A_pct": round(float((busiest == 0).mean() * 100), 2),
    }


def formula(total, shares):
    n = total * np.array(shares)
    p = np.minimum(1, CAP / n)
    return {"p_by_day_pct": [round(float(x * 100), 2) for x in p], "ratio": round(float(p.max() / p.min()), 3),
            "overall_read_pct": round(float(min(1, 5 * CAP / total) * 100), 2),
            "all_win_pct": round(float(np.minimum(n, CAP).sum() / total * 100), 2)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 基本：申し込みの総数の見込み1,000人、基本の偏り、回ごとの人気の振れ0.15
    n, win, p = simulate(rng, 1000, SHARES["base"], 0.15)
    base = summarize(n, win, p)
    base["formula"] = formula(1000, SHARES["base"])
    by_day = pd.DataFrame({"day": DAYS, "expected_applicants": (1000 * np.array(SHARES["base"])).round(1),
                           "applicants_mean": n.mean(0).round(2), "win_prob_mean_pct": (p.mean(0) * 100).round(2),
                           "win_prob_p10_pct": (np.quantile(p, .1, axis=0) * 100).round(2),
                           "win_prob_p90_pct": (np.quantile(p, .9, axis=0) * 100).round(2),
                           "win_prob_formula_pct": base["formula"]["p_by_day_pct"],
                           "under_cap_share_pct": ((n < CAP).mean(0) * 100).round(2)})
    by_day.to_csv(RES / "by_day_base.csv", index=False)
    ex = pd.DataFrame(n[:20], columns=DAYS)
    ex.insert(0, "round", np.arange(1, 21))
    ex.to_csv(DATA / "example_rounds.csv", index=False)

    # 確かめ：総数×偏り×振れ の27通り
    rows = []
    for total in [500, 1000, 2000]:
        for sk in ["flat", "base", "strong"]:
            for noise in [0.0, 0.15, 0.3]:
                r2 = np.random.default_rng(SEED * 100 + total + int(noise * 100) + len(sk))
                s = summarize(*simulate(r2, total, SHARES[sk], noise))
                f = formula(total, SHARES[sk])
                rows.append({"total_expected": total, "shares": sk, "noise": noise, **s,
                             "ratio_formula": f["ratio"], "overall_read_formula_pct": f["overall_read_pct"]})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid
    rng_summary = {
        "ratio_median_range": [float(g.ratio_median.min()), float(g.ratio_median.max())],
        "by_shares": {sk: {"ratio_median_range": [float(d.ratio_median.min()), float(d.ratio_median.max())],
                           "hardest_vs_read_range": [float(d.hardest_vs_read_ratio.min()), float(d.hardest_vs_read_ratio.max())]}
                      for sk, d in g.groupby("shares", sort=False)},
        "noise0_formula_max_abs_diff": round(float((g[g.noise == 0].ratio_median - g[g.noise == 0].ratio_formula).abs().max()), 3),
        "flat_noise_ratio": {str(nz): [float(d.ratio_median.min()), float(d.ratio_median.max())]
                             for nz, d in g[g.shares == "flat"].groupby("noise")},
    }
    out = {"setup": {"days": 5, "cap_per_day": CAP, "shares_base": SHARES["base"], "total_expected_base": 1000,
                     "noise_base": 0.15, "reps": REPS},
           "base": base, "by_day_base": by_day.to_dict("records"), "grid_summary": rng_summary}
    # 図1：日ごとの当たる見込み（基本）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(5)
    ax.bar(x, by_day.win_prob_mean_pct, color=[ORANGE, BLUE, BLUE, BLUE, GREEN], width=.6)
    err = np.vstack([by_day.win_prob_mean_pct - by_day.win_prob_p10_pct, by_day.win_prob_p90_pct - by_day.win_prob_mean_pct])
    ax.errorbar(x, by_day.win_prob_mean_pct, yerr=err, fmt="none", ecolor=INK, capsize=4, lw=1)
    for i, v in enumerate(by_day.win_prob_mean_pct):
        ax.text(i + .18, v + 2, f"{v:.2f}%", fontsize=9)
    ax.axhline(base["overall_read_mean_pct"], color=GRAY, ls="--", lw=1)
    ax.text(-0.45, base["overall_read_mean_pct"] + 1.5, f"全体の倍率から読む見込み {base['overall_read_mean_pct']:.2f}%",
            fontsize=8.5, color=GRAY, ha="left", va="bottom")
    ax.set_xticks(x, [f"{d}\n（見込み{int(e)}人）" for d, e in zip(DAYS, by_day.expected_applicants)])
    ax.set_ylim(0, 110); ax.set_ylabel("その日に申し込んだ人の当たる見込み（%）")
    ax.set_title("日ごとに抽選すると、同じ体験会でも当たる見込みが日で違う")
    save(fig, "a1179_by_day.png", SRC + "。定員各100人、2,000回の平均、線は10〜90%の範囲")

    # 図2：回ごとの開き（いちばん当たりやすい日÷いちばん当たりにくい日）の分布
    ratio = p.max(1) / p.min(1)
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.hist(ratio, bins=np.arange(1.5, 6.01, 0.1), color=BLUE, alpha=.85)
    ax.axvline(base["formula"]["ratio"], color=ORANGE, lw=1.5)
    ax.text(4.3, ax.get_ylim()[1] * .8, f"オレンジの線：見込みの人数からの\n式の値 {base['formula']['ratio']:.2f}倍",
            color=ORANGE, fontsize=9, va="top")
    ax.set_xlabel("いちばん当たりやすい日の見込み ÷ いちばん当たりにくい日の見込み（倍）")
    ax.set_ylabel("回の数（2,000回のうち）")
    ax.set_title(f"開きは回ごとに振れる（中央値{base['ratio_median']:.2f}倍）")
    save(fig, "a1179_ratio_hist.png", SRC + "。回ごとの人気の振れ0.15")

    # 図3：27通りの開き（中央値）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    w = .26
    for j, (nz, col) in enumerate([(0.0, LIGHT), (0.15, BLUE), (0.3, INK)]):
        d = g[g.noise == nz]
        xs = np.arange(9) + (j - 1) * w
        ax.bar(xs, d.ratio_median, width=w, color=col, label=f"回ごとの人気の振れ {nz}")
    ax.set_xticks(np.arange(9), [f"{t}人\n{SHARE_JP[s].split('（')[0]}" for t in [500, 1000, 2000] for s in SHARES], fontsize=8.5)
    ax.set_ylim(0, None); ax.set_ylabel("開き（倍、2,000回の中央値）")
    ax.set_xlabel("申し込みの総数の見込み・日ごとの偏り")
    ax.legend(fontsize=8.5, frameon=False)
    ax.set_title("開きは偏りと総数で決まる（27通り）")
    save(fig, "a1179_robust.png", SRC + "。偏りは各20%・基本32〜9%・強い45〜5%")
    json.dump(out, open(RES / "a1179_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
