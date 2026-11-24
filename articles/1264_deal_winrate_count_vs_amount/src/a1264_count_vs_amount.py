"""1264 件数で数えた受注率と金額で数えた受注率では、良かった月はどう入れかわるのか？（架空のデータ）

作成者が置いた架空の会社の法人向けの商談。24か月、毎月決まる商談の数は平均40件（数え上げの乱数）。
商談の金額は中央値300万円で、対数の散らばり（基本1.0）を置く。
商談ごとの本当の受注の確率は、ロジットの尺度で 基準（30%）＋月の良さ＋金額の効き（大きい商談ほど取りにくい）。
  月の良さ：月ごとに平均0・標準偏差0.3（作成者だけが知っている「本当に良かった月」の順）
  金額の効き：金額が e 倍になるごとに −0.5
取れる・取れないは、この確率で乱数で決める。
  件数の受注率：受注した件数 ÷ 決まった件数
  金額の受注率：受注した金額の合計 ÷ 決まった商談の金額の合計
24か月の276組のうち、大小が逆になる組の数と、上位3か月の重なりを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1264
SRC = "架空の法人向けの商談24か月（作成者が置いた月の良さ・金額・受注の確率からの乱数、seed 1264）"
M = 24
BASE = dict(sigma=1.0, beta=-0.5, n=40, month_sd=0.3)
LOGIT0 = np.log(0.3 / 0.7)


def one_set(rng, sigma=1.0, beta=-0.5, n=40, month_sd=0.3):
    eff = rng.normal(0, month_sd, M)
    cnt = rng.poisson(n, M)
    cnt = np.maximum(cnt, 1)
    month = np.repeat(np.arange(M), cnt)
    z = rng.normal(0, 1, len(month))
    amt = np.round(300 * np.exp(sigma * z), 1)               # 万円
    p = 1 / (1 + np.exp(-(LOGIT0 + eff[month] + beta * sigma * z)))
    won = rng.random(len(month)) < p
    c = np.bincount(month, won, M) / cnt
    v = np.bincount(month, amt * won, M) / np.bincount(month, amt, M)
    big_share = np.zeros(M); big_won = np.zeros(M, bool)
    for t in range(M):
        idx = np.where(month == t)[0]
        j = idx[np.argmax(amt[idx])]
        big_share[t] = amt[j] / amt[idx].sum()
        big_won[t] = won[j]
    return dict(eff=eff, cnt=cnt, month=month, amt=amt, p=p, won=won, c=c, v=v, big_share=big_share, big_won=big_won)


def disagree(a, b):
    i, j = np.triu_indices(len(a), 1)
    return int(np.sum(np.sign(a[i] - a[j]) != np.sign(b[i] - b[j])))


def top(a, k=3):
    return set(np.argsort(-a, kind="stable")[:k])


def main():
    t0 = time.time()
    n_pairs = M * (M - 1) // 2

    o = one_set(np.random.default_rng([SEED, 0]), **BASE)
    pd.DataFrame({"month": o["month"] + 1, "amount_man_yen": o["amt"], "true_p": o["p"].round(4),
                  "won": o["won"].astype(int)}).to_csv(DATA / "deals_one_set.csv", index=False)
    mdf = pd.DataFrame({"month": np.arange(1, M + 1), "decided": o["cnt"], "won": np.bincount(o["month"], o["won"], M).astype(int),
                        "rate_count": o["c"].round(4), "rate_amount": o["v"].round(4), "true_month_effect": o["eff"].round(4),
                        "largest_deal_share": o["big_share"].round(4), "largest_deal_won": o["big_won"].astype(int)})
    mdf.to_csv(DATA / "months_one_set.csv", index=False)
    one = {"top3_count": sorted(int(x) + 1 for x in top(o["c"])), "top3_amount": sorted(int(x) + 1 for x in top(o["v"])),
           "top3_true": sorted(int(x) + 1 for x in top(o["eff"])),
           "best_count": int(np.argmax(o["c"])) + 1, "best_amount": int(np.argmax(o["v"])) + 1,
           "rank_in_count_of_best_amount": int((-o["c"]).argsort().argsort()[np.argmax(o["v"])]) + 1,
           "disagree_count_amount": disagree(o["c"], o["v"])}

    rows = []
    for r in range(500):
        o = one_set(np.random.default_rng([SEED, 1, r]), **BASE)
        rows.append({"rep": r, "disagree_c_v": disagree(o["c"], o["v"]),
                     "disagree_c_true": disagree(o["c"], o["eff"]), "disagree_v_true": disagree(o["v"], o["eff"]),
                     "top3_c_v": len(top(o["c"]) & top(o["v"])),
                     "top3_c_true": len(top(o["c"]) & top(o["eff"])), "top3_v_true": len(top(o["v"]) & top(o["eff"])),
                     "best_same": int(np.argmax(o["c"]) == np.argmax(o["v"])),
                     "mean_c": o["c"].mean(), "mean_v": o["v"].mean(),
                     "sd_c": o["c"].std(), "sd_v": o["v"].std(),
                     "big_share_median": float(np.median(o["big_share"])),
                     "v_minus_c_big_won": float(np.mean((o["v"] - o["c"])[o["big_won"]])) if o["big_won"].any() else np.nan,
                     "v_minus_c_big_lost": float(np.mean((o["v"] - o["c"])[~o["big_won"]])) if (~o["big_won"]).any() else np.nan,
                     "top3_v_with_big_won": float(np.mean(o["big_won"][list(top(o["v"]))]))})
    reps = pd.DataFrame(rows)
    reps.round(5).to_csv(RES / "reps_base.csv", index=False)

    # 対照：金額がすべて同じ（散らばり0）
    ctrl = []
    for r in range(200):
        o = one_set(np.random.default_rng([SEED, 2, r]), sigma=0.0, beta=-0.5, n=40, month_sd=0.3)
        ctrl.append(disagree(o["c"], o["v"]))

    grid = []
    for sg in [0.5, 1.0, 1.5]:
        for bt in [0.0, -0.5, -1.0]:
            for n in [20, 40, 80]:
                rr = []
                for r in range(40):
                    o = one_set(np.random.default_rng([SEED, 3, int(sg * 10), int(-bt * 10), n, r]), sigma=sg, beta=bt, n=n, month_sd=0.3)
                    rr.append([disagree(o["c"], o["v"]), disagree(o["c"], o["eff"]), disagree(o["v"], o["eff"]),
                               len(top(o["c"]) & top(o["v"]))])
                rr = np.array(rr, float)
                grid.append({"sigma": sg, "beta": bt, "n": n, "disagree_c_v": rr[:, 0].mean(), "disagree_c_true": rr[:, 1].mean(),
                             "disagree_v_true": rr[:, 2].mean(), "top3_c_v": rr[:, 3].mean()})
    gr = pd.DataFrame(grid)
    gr.round(4).to_csv(RES / "grid.csv", index=False)

    # 確かめ2：月の良さの差を変える（基本の金額で、各100回）
    msd = []
    for sd in [0.1, 0.3, 0.6]:
        rr = []
        for r in range(100):
            o = one_set(np.random.default_rng([SEED, 4, int(sd * 10), r]), sigma=1.0, beta=-0.5, n=40, month_sd=sd)
            rr.append([disagree(o["c"], o["v"]), disagree(o["c"], o["eff"]), disagree(o["v"], o["eff"])])
        rr = np.array(rr, float)
        msd.append({"month_sd": sd, "disagree_c_v": rr[:, 0].mean(), "disagree_c_true": rr[:, 1].mean(), "disagree_v_true": rr[:, 2].mean()})
    msd = pd.DataFrame(msd)
    msd.round(4).to_csv(RES / "month_sd.csv", index=False)

    q = lambda x, p: round(float(np.quantile(x, p)), 4)
    m = lambda x: round(float(np.nanmean(x)), 4)
    m2 = lambda x: round(float(np.nanmean(x)), 2)
    head = {"pairs": n_pairs, "disagree_c_v_mean": m2(reps.disagree_c_v), "disagree_c_v_p10_p90": [q(reps.disagree_c_v, .1), q(reps.disagree_c_v, .9)],
            "disagree_c_true_mean": m2(reps.disagree_c_true), "disagree_v_true_mean": m2(reps.disagree_v_true),
            "top3_c_v_mean": m(reps.top3_c_v), "top3_c_true_mean": m(reps.top3_c_true), "top3_v_true_mean": m(reps.top3_v_true),
            "best_month_same_share": m(reps.best_same),
            "mean_rate_count": m(reps.mean_c), "mean_rate_amount": m(reps.mean_v),
            "sd_rate_count": m(reps.sd_c), "sd_rate_amount": m(reps.sd_v),
            "largest_deal_share_median": m(reps.big_share_median),
            "v_minus_c_when_largest_won": m(reps.v_minus_c_big_won), "v_minus_c_when_largest_lost": m(reps.v_minus_c_big_lost),
            "top3_amount_months_largest_won_share": m(reps.top3_v_with_big_won),
            "control_sigma0_disagree_mean": round(float(np.mean(ctrl)), 4), "control_sigma0_disagree_max": int(np.max(ctrl))}
    robust = {"settings": int(len(gr)),
              "disagree_c_v_range": [round(gr.disagree_c_v.min(), 4), round(gr.disagree_c_v.max(), 4)],
              "disagree_c_v_range_by_sigma": {str(s): [round(gr[gr.sigma == s].disagree_c_v.min(), 4), round(gr[gr.sigma == s].disagree_c_v.max(), 4)] for s in [0.5, 1.0, 1.5]},
              "disagree_c_true_range": [round(gr.disagree_c_true.min(), 4), round(gr.disagree_c_true.max(), 4)],
              "disagree_v_true_range": [round(gr.disagree_v_true.min(), 4), round(gr.disagree_v_true.max(), 4)],
              "settings_amount_closer_to_true": int(np.sum(gr.disagree_v_true < gr.disagree_c_true)),
              "settings_count_closer_to_true": int(np.sum(gr.disagree_c_true < gr.disagree_v_true)),
              "top3_c_v_range": [round(gr.top3_c_v.min(), 4), round(gr.top3_c_v.max(), 4)],
              "month_sd": msd.round(4).to_dict(orient="records")}
    out = {"headline": head, "one_set": one, "robust": robust,
           "settings": {"months": M, "base": BASE, "base_rate": 0.3, "amount_median_man_yen": 300, "reps_base": 500, "reps_control": 200,
                        "reps_grid": 40, "reps_month_sd": 100}}
    json.dump(out, open(RES / "a1264_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1 1回分の24か月
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    x = mdf.month.values
    ax.plot(x, mdf.rate_count * 100, color=BLUE, marker="o", ms=4, label="件数の受注率")
    ax.plot(x, mdf.rate_amount * 100, color=ORANGE, marker="s", ms=4, label="金額の受注率")
    for t in one["top3_count"]:
        ax.annotate("件", (t, mdf.rate_count[t - 1] * 100), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8, color=BLUE)
    for t in one["top3_amount"]:
        ax.annotate("金", (t, mdf.rate_amount[t - 1] * 100), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8, color=ORANGE)
    ax.set_ylim(0, max(mdf.rate_count.max(), mdf.rate_amount.max()) * 100 + 18)
    ax.set_xticks(x)
    ax.set_xlabel("何か月目か")
    ax.set_ylabel("受注率（%）")
    ax.set_title("1回分の24か月（「件」「金」はそれぞれの上位3か月）")
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=2)
    save(fig, "a1264_one_set.png", SRC)

    # 図2 大小が逆の組
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    labs = ["件数 と 金額", "件数 と 本当の月の良さ", "金額 と 本当の月の良さ"]
    v = [head["disagree_c_v_mean"], head["disagree_c_true_mean"], head["disagree_v_true_mean"]]
    ax.bar(labs, v, color=[GRAY, BLUE, ORANGE], width=0.55)
    for i, vv in enumerate(v):
        ax.text(i, vv + 2, f"{vv:.2f}組", ha="center", fontsize=10)
    ax.axhline(n_pairs / 2, color=INK, lw=0.8, ls="--")
    ax.text(2.3, n_pairs / 2 + 2, "でたらめなら138組", ha="right", fontsize=8.5)
    ax.set_ylim(0, 160)
    ax.set_ylabel("大小が逆の組（276組中、平均）")
    ax.set_title("24か月の並びの食い違い（基本の置き方、500回の平均）")
    save(fig, "a1264_disagree.png", SRC)

    # 図3 27通り
    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.8), sharey=True)
    for ax, sg in zip(axes, [0.5, 1.0, 1.5]):
        for bt, c in zip([0.0, -0.5, -1.0], [LIGHT, BLUE, INK]):
            d = gr[(gr.sigma == sg) & (gr.beta == bt)]
            ax.plot(d.n, d.disagree_c_v, color=c, marker="o", ms=4, label=f"金額の効き {bt:+.1f}")
        ax.set_title(f"金額の散らばり {sg}", fontsize=11)
        ax.set_xticks([20, 40, 80])
        ax.set_xlabel("月に決まる商談（平均件数）")
    axes[0].set_ylabel("件数と金額で逆の組（276組中）")
    axes[0].set_ylim(0, max(140, gr.disagree_c_v.max() + 10))
    axes[0].legend(frameon=False, fontsize=8.5)
    fig.suptitle("27通りの置き方（各40回の平均）", fontsize=12, y=1.04)
    save(fig, "a1264_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
