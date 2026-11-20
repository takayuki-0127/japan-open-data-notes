"""830 2年目のジンクスは、偶然だけで起きるのか？（架空のデータ）

架空の球技リーグ。毎年120人の新人が入り、1年目と2年目のシュート成功率を数える。
選手ごとに「本当の成功率」を作成者が置き、基本は1年目と2年目で変わらない（実力は落ちない）。
1年目に成功率がいちばん高かった新人（新人賞）は、2年目にどれだけ下がって見えるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 830
SRC = "架空のリーグの新人の成績（作成者が乱数で作成、seed 830）"
rng = np.random.default_rng(SEED)
N_ROOKIE = 120
MU, SD = 0.45, 0.03          # 本当の成功率の平均とばらつき（標準偏差）
SHOTS = (150, 450)           # 1年目のシュート数（一様）。2年目も同じ数
SEASONS = 5000


def seasons(rng, n_season, sd=SD, shot_mult=1.0, change=0.0):
    true1 = np.clip(rng.normal(MU, sd, (n_season, N_ROOKIE)), 0.2, 0.7)
    true2 = np.clip(true1 + change, 0.0, 1.0)
    n = np.round(rng.integers(SHOTS[0], SHOTS[1] + 1, (n_season, N_ROOKIE)) * shot_mult).astype(int)
    y1 = rng.binomial(n, true1) / n
    y2 = rng.binomial(n, true2) / n
    return true1, n, y1, y2


def summarize(true1, n, y1, y2, sd=SD):
    S, R = y1.shape
    order = np.argsort(-y1, 1)
    rows = np.arange(S)[:, None]
    top1 = order[:, :1]; top10 = order[:, :10]; bot10 = order[:, -10:]
    d = y2 - y1
    # 縮めた見込み：1年目の成績を、リーグの平均に「確かさ」の分だけ寄せる
    noise = MU * (1 - MU) / n
    r = sd ** 2 / (sd ** 2 + noise)
    pred = MU + r * (y1 - MU)
    pd_ = pred - y1
    return {
        "top1_y1": round(float(y1[rows, top1].mean()), 4), "top1_y2": round(float(y2[rows, top1].mean()), 4),
        "top1_true": round(float(true1[rows, top1].mean()), 4),
        "top1_change": round(float(d[rows, top1].mean()), 4),
        "top1_share_down": round(float((d[rows, top1] < 0).mean()), 4),
        "top1_pred_change": round(float(pd_[rows, top1].mean()), 4),
        "top1_shots_median": float(np.median(n[rows, top1])), "all_shots_median": float(np.median(n)),
        "top10_change": round(float(d[rows, top10].mean()), 4),
        "top10_share_down": round(float((d[rows, top10] < 0).mean()), 4),
        "top10_pred_change": round(float(pd_[rows, top10].mean()), 4),
        "bottom10_change": round(float(d[rows, bot10].mean()), 4),
        "bottom10_share_up": round(float((d[rows, bot10] > 0).mean()), 4),
        "all_change": round(float(d.mean()), 4),
    }


def main():
    true1, n, y1, y2 = seasons(rng, SEASONS)
    base = summarize(true1, n, y1, y2)

    # 1シーズン分（data/rookies.csv）
    o = np.argsort(-y1[0])
    df = pd.DataFrame({"player_id": np.arange(1, N_ROOKIE + 1), "true_rate": true1[0].round(4), "shots": n[0],
                       "rate_y1": y1[0].round(4), "rate_y2": y2[0].round(4),
                       "rank_y1": np.argsort(o) + 1})
    df.to_csv(DATA / "rookies.csv", index=False)
    one = df.sort_values("rank_y1").head(1).iloc[0]
    one_season = {"award_rate_y1": float(one.rate_y1), "award_rate_y2": float(one.rate_y2),
                  "award_true": float(one.true_rate), "award_shots": int(one.shots),
                  "award_true_rank": int((df.true_rate > one.true_rate).sum() + 1)}

    # 1年目の順位の帯ごとの、2年目の変化
    order = np.argsort(-y1, 1)
    rows = np.arange(SEASONS)[:, None]
    band = []
    for lo, hi in [(1, 1), (2, 5), (6, 10), (11, 30), (31, 90), (91, 110), (111, 120)]:
        idx = order[:, lo - 1:hi]
        band.append({"rank_y1": f"{lo}位" if lo == hi else f"{lo}〜{hi}位",
                     "change": round(float((y2 - y1)[rows, idx].mean()), 4),
                     "true_minus_y1": round(float((true1 - y1)[rows, idx].mean()), 4)})
    pd.DataFrame(band).to_csv(RES / "change_by_rank.csv", index=False)

    # 確かめ：本当の差の大きさ・シュート数・2年目に本当に変わる場合
    sens = []
    for sd in [0.015, 0.03, 0.045]:
        for m in [0.5, 1.0, 2.0]:
            t, nn, a, b = seasons(np.random.default_rng(SEED * 10 + int(sd * 1000) + int(m * 10)), 2000, sd, m)
            s = summarize(t, nn, a, b, sd)
            sens.append({"sd": sd, "shot_mult": m, "top1_change": s["top1_change"], "top1_pred_change": s["top1_pred_change"],
                         "top1_share_down": s["top1_share_down"], "top10_change": s["top10_change"]})
    sv = pd.DataFrame(sens)
    sv.to_csv(RES / "sensitivity.csv", index=False)
    chg = []
    for c in [-0.01, 0.0, 0.01]:
        t, nn, a, b = seasons(np.random.default_rng(SEED * 20 + int(c * 1000) + 50), 2000, SD, 1.0, c)
        s = summarize(t, nn, a, b)
        chg.append({"true_change_all": c, "top1_change": s["top1_change"], "top1_share_down": s["top1_share_down"],
                    "bottom10_change": s["bottom10_change"], "all_change": s["all_change"]})

    out = {"rookies_per_season": N_ROOKIE, "seasons": SEASONS, "true_mean": MU, "true_sd": SD, "shots_range": SHOTS,
           "base_no_true_change": base, "by_rank_y1": band, "one_season": one_season,
           "sensitivity_sd_shots": sens,
           "sensitivity_top1_change_range": {"min": float(sv.top1_change.min()), "max": float(sv.top1_change.max())},
           "sensitivity_max_abs_gap_pred": round(float((sv.top1_change - sv.top1_pred_change).abs().max()), 4),
           "sensitivity_top1_share_down_range": {"min": float(sv.top1_share_down.min()), "max": float(sv.top1_share_down.max())},
           "true_change_scenarios": chg}
    json.dump(out, open(RES / "a830_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1年目と2年目（20シーズン分）
    k = 20
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    ax.scatter(y1[:k].ravel(), y2[:k].ravel(), s=6, color=BLUE, alpha=.35, lw=0, label="新人（20シーズン分）")
    ti = order[:k, 0]
    ax.scatter(y1[np.arange(k), ti], y2[np.arange(k), ti], s=30, color=ORANGE, zorder=3, label="1年目の1位（新人賞）")
    lim = (0.30, 0.62)
    ax.plot(lim, lim, color=GRAY, lw=1, ls="--"); ax.text(0.615, 0.31, "点線：1年目＝2年目", fontsize=8.5, color=GRAY, ha="right")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("1年目のシュート成功率"); ax.set_ylabel("2年目のシュート成功率")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("実力は変えていないのに、新人賞の多くは線の下（2年目に下がる）", fontsize=12)
    save(fig, "a830_scatter.png", SRC)

    # 図2：1年目の順位の帯ごとの、2年目の変化
    b = pd.DataFrame(band)
    fig, ax = plt.subplots(figsize=(8.0, 3.9))
    v = b.change * 100
    ax.bar(b.rank_y1, v, color=[ORANGE if x < 0 else GREEN for x in v])
    for i, x in enumerate(v):
        ax.text(i, x + (0.12 if x >= 0 else -0.12), f"{x:+.1f}", ha="center", va="bottom" if x >= 0 else "top", fontsize=9)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_ylim(min(v) - 0.8, max(v) + 0.8)
    ax.tick_params(axis="x", labelsize=9.5)
    ax.set_xlabel("1年目の成功率の順位（新人120人の中で）"); ax.set_ylabel("2年目の変化（ポイント）")
    ax.set_title("1年目の上位は下がり、下位は上がる（本当の実力は同じ、5,000シーズン）")
    save(fig, "a830_by_rank.png", SRC)

    # 図3：確かめ（本当の差の大きさ・シュート数）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for sd, c in [(0.015, LIGHT), (0.03, BLUE), (0.045, GREEN)]:
        d = sv[sv.sd == sd]
        ax.plot(d.shot_mult, d.top1_change * 100, marker="o", color=c, label=f"本当の成功率のばらつき {sd:g}")
    ax.set_xscale("log", base=2); ax.set_xticks([0.5, 1, 2]); ax.set_xticklabels(["半分\n(75〜225本)", "基本\n(150〜450本)", "2倍\n(300〜900本)"])
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xlabel("1年のシュート数"); ax.set_ylabel("新人賞の2年目の変化（ポイント）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("新人賞の下がり幅は、シュート数が少なく、実力差が小さいほど大きい")
    save(fig, "a830_sensitivity.png", SRC, y=-0.08)
    print(json.dumps({k_: out[k_] for k_ in ["base_no_true_change", "by_rank_y1", "one_season",
                                            "sensitivity_top1_change_range", "true_change_scenarios"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
