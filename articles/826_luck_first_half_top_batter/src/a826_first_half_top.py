"""826 前半の打率トップは、後半もトップなのか？（平均への回帰）（架空のデータ）

架空のリーグの打者60人。打者ごとに「本当の打率」（打数を無限に増やしたときの打率）を置き、
前半・後半それぞれ同じ打数を打つ。1打数ごとに、本当の打率の確率でヒットになると置く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 826
SRC = "架空のリーグの打撃成績（作成者が乱数で作成、seed 826）"
rng = np.random.default_rng(SEED)
N_BAT, MU = 60, 0.265
REPS = 10000


def make_league(rng, reps, n_bat=N_BAT, sd=0.020, ab=250):
    true = rng.normal(MU, sd, (reps, n_bat))
    bad = (true < 0.18) | (true > 0.35)
    while bad.any():  # 0.18〜0.35 の外は引き直す
        true[bad] = rng.normal(MU, sd, bad.sum())
        bad = (true < 0.18) | (true > 0.35)
    h1 = rng.binomial(ab, true)
    h2 = rng.binomial(ab, true)
    return true, h1 / ab, h2 / ab


def rank_desc(x):
    """大きい順の順位（1が最上位）。同じ値はでたらめに並べる"""
    reps, n = x.shape
    jitter = np.random.default_rng(SEED + 1).random(x.shape) * 1e-9
    order = np.argsort(-(x + jitter), axis=1)
    r = np.empty_like(order)
    r[np.arange(reps)[:, None], order] = np.arange(1, n + 1)
    return r


def summarize(true, a1, a2, k=10):
    reps, n = a1.shape
    r1, r2, rt = rank_desc(a1), rank_desc(a2), rank_desc(true)
    top = r1 == 1
    top_back_rank = r2[top]
    topk = r1 <= k
    botk = r1 > n - k
    # 前半の打率から後半の打率への傾き（リーグごとの平均を引いてから）
    d1 = (a1 - a1.mean(1, keepdims=True)).ravel()
    d2 = (a2 - a2.mean(1, keepdims=True)).ravel()
    slope = float((d1 * d2).sum() / (d1 * d1).sum())
    return {
        "p_top_stays_top": round(float((top_back_rank == 1).mean()), 4),
        "p_top_in_back_top3": round(float((top_back_rank <= 3).mean()), 4),
        "p_top_in_back_top10": round(float((top_back_rank <= 10).mean()), 4),
        "top_back_rank_median": float(np.median(top_back_rank)),
        "p_top_is_true_top": round(float((rt[top] == 1).mean()), 4),
        "p_top_in_true_top10": round(float((rt[top] <= 10).mean()), 4),
        "top_front_avg": round(float(a1[top].mean()), 4),
        "top_true_avg": round(float(true[top].mean()), 4),
        "top_back_avg": round(float(a2[top].mean()), 4),
        "top10_front_avg": round(float(a1[topk].mean()), 4),
        "top10_true_avg": round(float(true[topk].mean()), 4),
        "top10_back_avg": round(float(a2[topk].mean()), 4),
        "top10_back_drop_share": round(float((a1[topk].mean() - a2[topk].mean()) / (a1[topk].mean() - a1.mean())), 3),
        "top10_stay_top10_share": round(float((r2[topk] <= k).mean()), 4),
        "bottom10_front_avg": round(float(a1[botk].mean()), 4),
        "bottom10_true_avg": round(float(true[botk].mean()), 4),
        "bottom10_back_avg": round(float(a2[botk].mean()), 4),
        "league_avg": round(float(a1.mean()), 4),
        "slope_back_on_front": round(slope, 3),
    }, top_back_rank


def main():
    t0 = time.time()
    true, a1, a2 = make_league(rng, REPS)
    base, top_back_rank = summarize(true, a1, a2)
    sd, ab = 0.020, 250
    noise_var = MU * (1 - MU) / ab
    base["reliability_theory"] = round(sd ** 2 / (sd ** 2 + noise_var), 3)
    base["noise_sd_theory"] = round(float(np.sqrt(noise_var)), 4)
    # 本当の打率に差がない（全員0.265）と置いたときの、前半トップが後半もトップの割合（でたらめと同じ）
    t0_, b1, b2 = make_league(rng, REPS, sd=1e-9)
    base["p_top_stays_top_if_no_skill_diff"] = summarize(t0_, b1, b2)[0]["p_top_stays_top"]
    # 運がない（打率＝本当の打率）なら、トップはずっとトップ
    rank_hist = pd.Series(top_back_rank).value_counts().reindex(range(1, N_BAT + 1), fill_value=0)
    rank_hist = (rank_hist / REPS).round(4)
    rank_hist.rename_axis("back_rank").rename("share").to_csv(RES / "top_back_rank_dist.csv")

    # 1回分のリーグ（data）
    i = 0
    one = pd.DataFrame({"batter_id": np.arange(1, N_BAT + 1), "true": true[i].round(4),
                        "ab1": ab, "h1": (a1[i] * ab).round().astype(int), "avg1": a1[i].round(4),
                        "ab2": ab, "h2": (a2[i] * ab).round().astype(int), "avg2": a2[i].round(4)})
    one.to_csv(DATA / "batters_one_league.csv", index=False)
    r1 = one.avg1.rank(ascending=False, method="first")
    top_row = one.loc[r1.idxmin()]
    one_info = {"top_batter_id": int(top_row.batter_id), "top_avg1": float(top_row.avg1),
                "top_avg2": float(top_row.avg2), "top_true": float(top_row.true),
                "top_back_rank": int(one.avg2.rank(ascending=False, method="min")[r1.idxmin()]),
                "top_true_rank": int(one.true.rank(ascending=False, method="min")[r1.idxmin()])}

    # 確かめ：打数と本当の打率の差を変える
    rob = []
    for sd_ in [0.010, 0.020, 0.030]:
        for ab_ in [100, 250, 500]:
            tt, x1, x2 = make_league(np.random.default_rng(SEED * 100 + int(sd_ * 1000) * 10 + ab_), REPS, sd=sd_, ab=ab_)
            s, _ = summarize(tt, x1, x2)
            nv = MU * (1 - MU) / ab_
            rob.append({"true_sd": sd_, "ab_per_half": ab_, "p_top_stays_top": s["p_top_stays_top"],
                        "top_back_rank_median": s["top_back_rank_median"],
                        "top_front_avg": s["top_front_avg"], "top_back_avg": s["top_back_avg"],
                        "top10_back_drop_share": s["top10_back_drop_share"],
                        "slope_back_on_front": s["slope_back_on_front"],
                        "reliability_theory": round(sd_ ** 2 / (sd_ ** 2 + nv), 3)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness_sd_ab.csv", index=False)
    # 確かめ：打者の人数を変える（差0.020・250打数）
    nb = []
    for n_ in [12, 30, 60, 120]:
        tt, x1, x2 = make_league(np.random.default_rng(SEED * 7 + n_), REPS, n_bat=n_)
        s, _ = summarize(tt, x1, x2)
        nb.append({"n_batters": n_, "p_top_stays_top": s["p_top_stays_top"],
                   "top_back_rank_median": s["top_back_rank_median"],
                   "top_front_avg": s["top_front_avg"], "top_back_avg": s["top_back_avg"]})
    nb = pd.DataFrame(nb)
    nb.to_csv(RES / "robustness_n_batters.csv", index=False)

    out = {"base_60batters_sd020_ab250_10000leagues": base, "one_league": one_info,
           "robustness_sd_ab": rob.to_dict("records"), "robustness_n_batters": nb.to_dict("records")}
    json.dump(out, open(RES / "a826_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分のリーグ。前半と後半の打率
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    top10 = r1 <= 10
    ax.scatter(one.avg1[~top10], one.avg2[~top10], s=22, color=LIGHT, lw=0, label="その他の打者")
    ax.scatter(one.avg1[top10], one.avg2[top10], s=30, color=ORANGE, lw=0, label="前半の上位10人")
    lo, hi = 0.17, 0.36
    ax.plot([lo, hi], [lo, hi], color=GRAY, lw=1, ls="--", label="前半と同じ打率の線")
    m = one.avg1.mean()
    xs = np.array([lo, hi])
    ax.plot(xs, one.avg2.mean() + base["slope_back_on_front"] * (xs - m), color=BLUE, lw=1.5,
            label=f"{REPS:,}リーグで求めた傾き{base['slope_back_on_front']:.2f}")
    ax.annotate(f"前半トップ {top_row.avg1:.3f}\n→ 後半 {top_row.avg2:.3f}（後半{one_info['top_back_rank']}位）",
                (top_row.avg1, top_row.avg2), xytext=(0.178, 0.357), fontsize=8.5, va="top",
                arrowprops=dict(arrowstyle="->", color=INK, lw=.8))
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.set_xlabel("前半の打率（250打数）"); ax.set_ylabel("後半の打率（250打数）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(1.02, 1))
    ax.set_title("前半の上位10人は、後半はリーグの平均の側へ戻る（1リーグ・60人）", fontsize=12)
    save(fig, "a826_scatter.png", SRC)

    # 図2：前半トップの後半の順位
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(rank_hist.index, rank_hist.values * 100, color=[ORANGE] + [BLUE] * (N_BAT - 1), width=.85)
    ax.set_xlabel("前半トップの打者の、後半の順位（60人中）"); ax.set_ylabel("割合（%）")
    ax.set_xlim(0, 61)
    ax.text(2.5, rank_hist.values[0] * 100 - .2, f"← 後半もトップ {round(base['p_top_stays_top']*1000+1e-9)/10:.1f}%", color=ORANGE, fontsize=9.5)
    ax.text(30, max(rank_hist.values) * 100 * .7,
            f"後半の順位の中央値 {base['top_back_rank_median']:.0f}位\n後半も10位以内 {base['p_top_in_back_top10']*100:.0f}%",
            fontsize=9.5)
    ax.set_title(f"前半の打率トップが後半もトップだったのは、{REPS:,}リーグの{round(base['p_top_stays_top']*1000+1e-9)/10:.1f}%")  # 0.0745 を 7.5% と表示（本文とそろえる）
    save(fig, "a826_back_rank.png", SRC)

    # 図3：確かめ。打数と本当の差ごとの、前半トップが後半もトップの割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = .26
    for j, (sd_, c) in enumerate(zip([0.010, 0.020, 0.030], [LIGHT, BLUE, INK])):
        r = rob[rob.true_sd == sd_]
        xs = np.arange(3) + (j - 1) * w
        ax.bar(xs, r.p_top_stays_top * 100, width=w, color=c, label=f"本当の打率の差（標準偏差）{sd_:.3f}")
        for xx, v in zip(xs, r.p_top_stays_top * 100):
            ax.text(xx, v + .8, f"{v:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(range(3)); ax.set_xticklabels(["前半・後半 各100打数", "各250打数（基本）", "各500打数"])
    ax.set_ylabel("前半トップが後半もトップの割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_ylim(0, max(rob.p_top_stays_top) * 100 + 10)
    ax.set_title("打数が多く、打者どうしの差が大きいほど、トップは残りやすい")
    save(fig, "a826_robust.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
