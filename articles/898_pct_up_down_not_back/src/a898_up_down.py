"""898 20%上がって20%下がると、元に戻るのか？（架空のデータ）

上がる率と下がる率は、もとにする値（分母）が違う。100が20%上がると120、120が20%下がると96。
例の計算に加え、架空の店1,000店の月の売上（前月比の平均を0%と置いたもの）を24か月作り、
「前月比の平均が0%なら横ばい」と読んだときに、実際の売上がどこに行くかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 898
SRC = "架空の店の月の売上（作成者が乱数で作成、seed 898）"
N_SHOP = 1000
START = 100.0  # 万円


def monthly_changes(rng, n, months, sigma, drift=0.0, dist="normal"):
    if dist == "normal":
        r = rng.normal(drift, sigma, (n, months))
    else:  # 毎月ちょうど +sigma か −sigma（半々）
        r = drift + sigma * rng.choice([-1.0, 1.0], (n, months))
    return np.maximum(r, -0.95)  # 1か月で95%より大きくは下がらない（売上が負にならないように）


def summarize(r):
    end = np.prod(1 + r, 1)
    mean_r = r.mean(1)
    return {"mean_of_monthly": round(float(r.mean() * 100), 3),
            "end_mean": round(float(end.mean()), 3), "end_median": round(float(np.median(end)), 3),
            "end_p10": round(float(np.quantile(end, .1)), 3), "end_p90": round(float(np.quantile(end, .9)), 3),
            "share_below_start": round(float((end < 1).mean()), 3),
            "share_meanpos_but_down": round(float(((mean_r >= 0) & (end < 1)).mean()), 3),
            "share_meanpos": round(float((mean_r >= 0).mean()), 3),
            "share_down_among_meanpos": round(float((end[mean_r >= 0] < 1).mean()), 3),
            "geo_month": round(float((np.exp(np.log1p(r).mean()) - 1) * 100), 3)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 例：上がってから下がる
    ex = []
    for x in [5, 10, 20, 30, 50]:
        f = x / 100
        ex.append({"x_pct": x, "up_then_down": round(START * (1 + f) * (1 - f), 2),
                   "down_then_up": round(START * (1 - f) * (1 + f), 2),
                   "loss_pct": round(f * f * 100, 2),
                   "needed_up_after_down_pct": round(f / (1 - f) * 100, 2)})
    pd.DataFrame(ex).to_csv(RES / "examples.csv", index=False)

    # 2) 架空の店1,000店・24か月（前月比は平均0%・標準偏差10%の正規分布）
    r = monthly_changes(rng, N_SHOP, 24, 0.10)
    sales = START * np.cumprod(1 + r, 1)
    d = pd.DataFrame(np.round(sales, 3), columns=[f"m{m:02d}" for m in range(1, 25)])
    d.insert(0, "m00", START); d.insert(0, "shop_id", np.arange(1, N_SHOP + 1))
    d.to_csv(DATA / "shops_24months.csv", index=False)
    base = summarize(r)
    # 理屈の目安：中央値 ≒ exp(24 × E[log(1+r)]) ≒ exp(−24 × σ²/2)
    base["median_rule_of_thumb"] = round(float(np.exp(-24 * 0.10 ** 2 / 2)), 3)
    path_mean = sales.mean(0); path_med = np.median(sales, 0)
    path_p10, path_p90 = np.quantile(sales, .1, 0), np.quantile(sales, .9, 0)

    # 3) 確かめ：振れ・月数・前月比の分布・平均の伸び（各2,000店）
    rob = []
    i = 0
    for dist in ["normal", "coin"]:
        for drift in [0.0, 0.01]:
            for sigma in [0.05, 0.10, 0.20, 0.30]:
                for months in [12, 24, 60]:
                    i += 1
                    rr = monthly_changes(np.random.default_rng(SEED * 100 + i), 2000, months, sigma, drift, dist)
                    s = summarize(rr)
                    rob.append({"dist": dist, "drift_pct": drift * 100, "sigma_pct": sigma * 100, "months": months, **s})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    z = rob[rob.drift_pct == 0]
    p1 = rob[rob.drift_pct == 1]
    rob_sum = {"drift0_end_median_min": float(z.end_median.min()), "drift0_end_median_max": float(z.end_median.max()),
               "drift0_below_min": float(z.share_below_start.min()), "drift0_below_max": float(z.share_below_start.max()),
               "drift0_end_mean_min": float(z.end_mean.min()), "drift0_end_mean_max": float(z.end_mean.max()),
               "drift1_end_median_min": float(p1.end_median.min()), "drift1_end_median_max": float(p1.end_median.max()),
               "drift1_below_min": float(p1.share_below_start.min()), "drift1_below_max": float(p1.share_below_start.max())}
    coin24 = {f"sigma{int(s*100)}": float(z[(z.dist == "coin") & (z.months == 24) & (z.sigma_pct == s * 100)].end_median.iloc[0])
              for s in [0.05, 0.10, 0.20, 0.30]}
    rob_sum["coin_24months_end_median"] = coin24
    q = rob[(rob.dist == "normal") & (rob.drift_pct == 1) & (rob.sigma_pct == 20) & (rob.months == 24)].iloc[0]
    rob_sum["drift1_sigma20_m24"] = {"end_mean": float(q.end_mean), "end_median": float(q.end_median),
                                     "share_below_start": float(q.share_below_start)}
    q = rob[(rob.dist == "normal") & (rob.drift_pct == 0) & (rob.sigma_pct == 10) & (rob.months == 24)].iloc[0]
    rob_sum["drift0_sigma10_m24_2000shops"] = {"end_mean": float(q.end_mean), "end_median": float(q.end_median),
                                               "share_below_start": float(q.share_below_start)}
    rob_sum["coin_24months_formula"] = {f"sigma{int(s*100)}": round(float(((1 + s) * (1 - s)) ** 12), 3)
                                         for s in [0.05, 0.10, 0.20, 0.30]}

    out = {"examples": ex, "base_1000shops_24months": base,
           "paths": {"mean_m24": round(float(path_mean[-1]), 2), "median_m24": round(float(path_med[-1]), 2),
                     "p10_m24": round(float(path_p10[-1]), 2), "p90_m24": round(float(path_p90[-1]), 2)},
           "robustness_summary": rob_sum,
           "note": "上がって下がると (1+x)(1−x)＝1−x² で、x² だけ減る（式どおり）。順番を逆にしても同じ"}
    json.dump(out, open(RES / "a898_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例
    e = pd.DataFrame(ex)
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xs = np.arange(len(e)); w = 0.38
    ax.bar(xs - w / 2, e.loss_pct, w, color=ORANGE, label="上がって下がったあとに減った分（%）")
    ax.bar(xs + w / 2, e.needed_up_after_down_pct, w, color=BLUE, label="下がったあと、元に戻るのに要る上がり（%）")
    for xx, a, b in zip(xs, e.loss_pct, e.needed_up_after_down_pct):
        ax.text(xx - w / 2, a + 2, f"{a:g}", ha="center", fontsize=9)
        ax.text(xx + w / 2, b + 2, f"{b:g}", ha="center", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels([f"±{x}%" for x in e.x_pct])
    ax.set_ylim(0, 115); ax.set_ylabel("%")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("同じ率で上がって下がると、率の2乗だけ減る（100→120→96）")
    save(fig, "a898_examples.png", SRC)

    # 図2：1,000店の24か月
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    m = np.arange(0, 25)
    ax.fill_between(m, np.r_[START, path_p10], np.r_[START, path_p90], color=LIGHT, alpha=.6, lw=0,
                    label="1,000店の10〜90%の範囲")
    ax.plot(m, np.r_[START, path_mean], color=BLUE, lw=2, label="1,000店の平均")
    ax.plot(m, np.r_[START, path_med], color=ORANGE, lw=2, label="1,000店の真ん中（中央値）")
    ax.axhline(START, color=GRAY, lw=.8, ls="--")
    ax.set_xlabel("月"); ax.set_ylabel("月の売上（万円、始めは100）"); ax.set_xticks(range(0, 25, 6))
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"前月比の平均が0%でも、24か月後の真ん中の店は{path_med[-1]:.1f}万円")
    save(fig, "a898_paths.png", SRC)

    # 図3：確かめ（前月比の平均0%・正規分布：24か月後の中央値と、始めを下回る店の割合）
    zz = z[(z.dist == "normal")]
    fig, axs = plt.subplots(1, 2, figsize=(8.0, 3.8))
    for months, c in zip([12, 24, 60], [LIGHT, BLUE, INK]):
        q = zz[zz.months == months]
        axs[0].plot(q.sigma_pct, q.end_median, "o-", color=c, label=f"{months}か月")
        axs[1].plot(q.sigma_pct, q.share_below_start * 100, "o-", color=c, label=f"{months}か月")
    axs[0].axhline(1, color=GRAY, lw=.8, ls="--")
    axs[0].set_xlabel("前月比の振れ（標準偏差、%）"); axs[0].set_ylabel("終わりの売上÷始め（中央値）")
    axs[1].axhline(50, color=GRAY, lw=.8, ls="--")
    axs[1].set_xlabel("前月比の振れ（標準偏差、%）"); axs[1].set_ylabel("始めを下回った店の割合（%）")
    axs[1].set_ylim(0, 100)
    axs[0].legend(frameon=False, fontsize=9)
    fig.suptitle("振れが大きく、月数が長いほど、真ん中の店は下がる（前月比の平均0%）", fontsize=12)
    fig.tight_layout()
    save(fig, "a898_robustness.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
