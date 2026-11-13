"""526 1事故ごとの免責と1年の合計の免責では、同じ見込みの支払いでも、支払いの振れはどれだけ違うのか（保険数理・リスク）

架空の1つの契約（または契約のまとまり）の1年分の損害。
- 事故件数 N：平均10件。ポアソン（散らばりなし）と負の二項（分散＝平均の3倍）
- 1件の損害額 X：対数正規（平均10万円、裾の軽い σ=0.8 と重い σ=1.6）
- 1事故ごとの免責 d：支払い = Σ max(X − d, 0)。d = 5万・10万・20万円
- 1年の合計の免責 D：支払い = max(Σ X − D, 0)。D は、見込みの支払い（平均）が 1事故ごとの免責と同じになるように決める
支払いの標準偏差・99.5%点・支払いが0の年の割合・件数の多い年の支払いを比べる。乱数の種 526、各場面 40万年。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の事故件数と損害額（作成者が乱数で作成、seed 526）"
YEARS = 400_000
MEAN_N = 10
MEAN_X = 100_000
DS = [50_000, 100_000, 200_000]


def simulate(rng, disp, sigma):
    if disp == 1:
        n = rng.poisson(MEAN_N, YEARS)
    else:
        k = MEAN_N / (disp - 1)                       # 分散 = 平均 × disp になる負の二項
        n = rng.negative_binomial(k, k / (k + MEAN_N), YEARS)
    mu = np.log(MEAN_X) - sigma ** 2 / 2
    x = rng.lognormal(mu, sigma, n.sum())
    yr = np.repeat(np.arange(YEARS), n)
    return n, x, yr


def agg_ded_for_mean(S, target):
    # max(S − D, 0) の平均が target になる D を二分法で探す
    lo, hi = 0.0, float(S.max())
    for _ in range(80):
        mid = (lo + hi) / 2
        if np.maximum(S - mid, 0).mean() > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def stats(pay):
    return dict(mean=float(pay.mean()), sd=float(pay.std()), q995=float(np.quantile(pay, 0.995)),
                q99=float(np.quantile(pay, 0.99)), zero_share=float((pay == 0).mean()))


def main():
    rng = np.random.default_rng(526)
    rows = []
    keep = {}
    for disp in [1, 3]:
        for sigma in [0.8, 1.6]:
            n, x, yr = simulate(rng, disp, sigma)
            S = np.bincount(yr, weights=x, minlength=YEARS)
            for d in DS:
                per = np.bincount(yr, weights=np.maximum(x - d, 0), minlength=YEARS)
                D = agg_ded_for_mean(S, per.mean())
                agg = np.maximum(S - D, 0)
                a, b = stats(per), stats(agg)
                hi = n >= np.quantile(n, 0.9)            # 件数の多い年（上位1割）
                lo = n <= np.quantile(n, 0.1)
                rows.append(dict(count=("ポアソン" if disp == 1 else "負の二項（分散3倍）"), disp=disp, sigma=sigma, d=d,
                                 agg_D=round(D), mean_per=round(a["mean"]), mean_agg=round(b["mean"]),
                                 sd_per=round(a["sd"]), sd_agg=round(b["sd"]), sd_ratio=round(b["sd"] / a["sd"], 3),
                                 q995_per=round(a["q995"]), q995_agg=round(b["q995"]), q995_ratio=round(b["q995"] / a["q995"], 3),
                                 zero_per=round(a["zero_share"], 4), zero_agg=round(b["zero_share"], 4),
                                 hiN_per=round(per[hi].mean()), hiN_agg=round(agg[hi].mean()),
                                 loN_per=round(per[lo].mean()), loN_agg=round(agg[lo].mean()),
                                 kept_per=round(1 - a["mean"] / S.mean(), 4)))
                if d == 100_000:
                    keep[(disp, sigma)] = (per, agg, n)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "summary.csv", index=False)

    base = df[(df.d == 100_000)]
    main_ = {r["count"] + "・σ" + str(r["sigma"]): {k: r[k] for k in ["agg_D", "mean_per", "sd_per", "sd_agg", "sd_ratio", "q995_per", "q995_agg", "q995_ratio", "zero_per", "zero_agg", "hiN_per", "hiN_agg", "loN_per", "loN_agg", "kept_per"]} for r in base.to_dict("records")}
    json.dump({"years": YEARS, "mean_n": MEAN_N, "mean_x": MEAN_X, "d=10万円": main_,
               "sd_ratio_range": [float(df.sd_ratio.min()), float(df.sd_ratio.max())],
               "q995_ratio_range": [float(df.q995_ratio.min()), float(df.q995_ratio.max())]},
              open(RES / "a526_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：d=10万円での標準偏差と99.5%点
    lab = [f"{'ポアソン' if r['disp'] == 1 else '負の二項'}\n額σ{r['sigma']}" for r in base.to_dict("records")]
    xx = np.arange(len(base))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for j, (c1, c2, t) in enumerate([("sd_per", "sd_agg", "支払いの標準偏差（万円）"), ("q995_per", "q995_agg", "支払いの99.5%点（万円）")]):
        ax[j].bar(xx - 0.2, base[c1] / 1e4, 0.4, color=BLUE, label="1事故ごとの免責（10万円）")
        ax[j].bar(xx + 0.2, base[c2] / 1e4, 0.4, color=ORANGE, label="1年の合計の免責（平均を合わせた額）")
        for i, (u, v) in enumerate(zip(base[c1], base[c2])):
            ax[j].text(i + 0.2, v / 1e4, f"{v / u:.2f}倍", ha="center", va="bottom", fontsize=8.5)
        ax[j].set_xticks(xx); ax[j].set_xticklabels(lab, fontsize=9); ax[j].set_title(t, fontsize=11)
        ax[j].set_ylim(0, max(base[c2].max(), base[c1].max()) / 1e4 * 1.12)
    h, l = ax[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=9, frameon=False, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("見込みの支払いは同じでも、合計の免責のほうが支払いは大きく振れる", fontsize=12, y=1.03)
    save(fig, "a526_sd_q995.png", SRC, y=-0.1)

    # 図2：件数の多い年・少ない年の支払い（ポアソン・σ0.8 と 負の二項・σ1.6）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for j, key in enumerate([(1, 0.8), (3, 1.6)]):
        per, agg, n = keep[key]
        ns = np.arange(0, 31)
        mp = [per[n == k].mean() / 1e4 if (n == k).sum() > 200 else np.nan for k in ns]
        ma = [agg[n == k].mean() / 1e4 if (n == k).sum() > 200 else np.nan for k in ns]
        ax[j].plot(ns, mp, color=BLUE, marker="o", ms=3, label="1事故ごとの免責")
        ax[j].plot(ns, ma, color=ORANGE, marker="o", ms=3, label="1年の合計の免責")
        ax[j].set_xlabel("その年の事故件数"); ax[j].set_ylabel("支払いの平均（万円）")
        ax[j].set_title(("ポアソン・額σ0.8" if key[0] == 1 else "負の二項・額σ1.6"), fontsize=11)
    ax[0].legend(fontsize=9, frameon=False)
    fig.suptitle("件数の多い年ほど、合計の免責の支払いは急に増える（件数が少ない年は0に近い）", fontsize=12, y=1.03)
    save(fig, "a526_by_count.png", SRC)

    # 図3：免責の額ごとの標準偏差の比
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for (disp, sigma), c, ls in [((1, 0.8), BLUE, "-"), ((1, 1.6), BLUE, "--"), ((3, 0.8), ORANGE, "-"), ((3, 1.6), ORANGE, "--")]:
        s = df[(df.disp == disp) & (df.sigma == sigma)]
        ax.plot(s.d / 1e4, s.sd_ratio, color=c, ls=ls, marker="o", label=f"{'ポアソン' if disp == 1 else '負の二項'}・額σ{sigma}")
    ax.axhline(1, color=GRAY, lw=1)
    ax.set_xlabel("1事故ごとの免責（万円）"); ax.set_ylabel("標準偏差の比（合計の免責 ÷ 1事故ごと）")
    ax.legend(fontsize=9, frameon=False)
    ax.set_title("件数がばらつき、額の裾が軽いほど、2つの形の振れの差は大きい", fontsize=12)
    save(fig, "a526_ratio_by_d.png", SRC)
    print(df[["count", "sigma", "d", "agg_D", "mean_per", "sd_per", "sd_agg", "sd_ratio", "q995_ratio", "zero_per", "zero_agg", "kept_per"]].to_string())


if __name__ == "__main__":
    main()
