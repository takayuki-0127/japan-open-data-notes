"""1253 試し読みから買った割合は、試し読みの数で割るか、本の紹介ページを見た数で割るかで、本の順がどう変わるのか？（架空のデータ）

作成者が置いた架空の電子書籍の2つのシリーズ（A・B、各6巻、計12冊）。
紹介ページを見た人を2種類に分ける。
  続きを待っていた人：前の巻を読んだ人。2巻目以降の紹介ページだけに来る。試し読みはせず、そのまま買う人がいる。
  はじめての人：本ごとの割合で試し読みをし、試し読みした人のうち本ごとの割合で買う（これが本当の「試し読みから買った割合」）。
                試し読みをしない人も、少しだけそのまま買う。
記録から分かるのは、紹介ページを見た数・試し読みの数・買った数（全部）だけで、買った人が試し読みをしたかは分からないと置く。
比べ方：①買った数÷試し読みの数　②買った数÷紹介ページを見た数　本当：試し読みした人のうち買った割合（作成者だけが知っている）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1253
SRC = "架空の電子書籍2シリーズ12冊（作成者が置いた閲覧・試し読み・購入の割合からの乱数、seed 1253）"
VOLS = 6
NAMES = [f"{s}{v}" for s in "AB" for v in range(1, VOLS + 1)]
VOL = np.array([v for s in "AB" for v in range(1, VOLS + 1)])
BASE = dict(f=0.3, d=0.4, t_lo=0.10, t_hi=0.30, c_lo=0.05, c_hi=0.30, a=0.01, keep=0.7)


def one_set(rng, f=0.3, d=0.4, t_lo=0.10, t_hi=0.30, c_lo=0.05, c_hi=0.30, a=0.01, keep=0.7):
    v1 = rng.uniform(3000, 9000, 2)                              # 1巻の紹介ページを見た数（シリーズごと）
    views = rng.poisson(np.repeat(v1, VOLS) * keep ** (VOL - 1))  # 巻が進むと見る人は減る
    wait_share = np.where(VOL == 1, 0.0, f)                      # 2巻目以降は、見た人のうち f が続きを待っていた人
    wait = rng.binomial(views, wait_share)
    new = views - wait
    t = rng.uniform(t_lo, t_hi, len(NAMES))                      # はじめての人が試し読みする割合
    c = rng.uniform(c_lo, c_hi, len(NAMES))                      # 試し読みした人のうち買う割合（本当）
    trials = rng.binomial(new, t)
    buy_after = rng.binomial(trials, c)
    buy_direct_new = rng.binomial(new - trials, a)
    buy_wait = rng.binomial(wait, d)
    buys = buy_after + buy_direct_new + buy_wait
    m1 = buys / np.maximum(trials, 1)
    m2 = buys / views
    return dict(views=views, wait=wait, trials=trials, buys=buys, buy_after=buy_after, buy_wait=buy_wait,
                buy_direct_new=buy_direct_new, t=t, c=c, m1=m1, m2=m2, true=buy_after / np.maximum(trials, 1))


def agree(a, b):
    i, j = np.triu_indices(len(a), 1)
    return int(np.sum(np.sign(a[i] - a[j]) == np.sign(b[i] - b[j])))


def top(a, k=3):
    return set(np.argsort(-a)[:k])


def ranks(a):
    return (-a).argsort().argsort() + 1


def main():
    t0 = time.time()
    n_pairs = len(NAMES) * (len(NAMES) - 1) // 2

    # 1回分（data に置く）
    o = one_set(np.random.default_rng([SEED, 0]), **BASE)
    df = pd.DataFrame({"book": NAMES, "volume": VOL, "views": o["views"], "trials": o["trials"], "buys": o["buys"],
                       "buys_after_trial": o["buy_after"], "buys_waiting_readers": o["buy_wait"], "buys_direct_new": o["buy_direct_new"],
                       "true_trial_to_buy": o["c"].round(4), "m1_buys_per_trial": o["m1"].round(4), "m2_buys_per_view": o["m2"].round(4)})
    df.to_csv(DATA / "books_one_set.csv", index=False)

    # 2) 基本の置き方で500回
    rows, rk = [], []
    for r in range(500):
        o = one_set(np.random.default_rng([SEED, 1, r]), **BASE)
        c = o["c"]
        rows.append({"rep": r,
                     "agree_m1_m2": agree(o["m1"], o["m2"]),
                     "agree_m1_true": agree(o["m1"], c), "agree_m2_true": agree(o["m2"], c),
                     "agree_true_obs_true": agree(o["true"], c),
                     "agree_m1_true_later": agree(o["m1"][VOL > 1], c[VOL > 1]),
                     "agree_m2_true_later": agree(o["m2"][VOL > 1], c[VOL > 1]),
                     "m1_over_100_later_share": float(np.mean(o["m1"][VOL > 1] > 1)),
                     "top3_m1_m2_overlap": len(top(o["m1"]) & top(o["m2"])),
                     "top3_m1_true": len(top(o["m1"]) & top(c)), "top3_m2_true": len(top(o["m2"]) & top(c)),
                     "m1_over_100_books": int(np.sum(o["m1"] > 1)),
                     "m1_over_100_vol1": int(np.sum((o["m1"] > 1) & (VOL == 1))),
                     "top3_m1_later_vol": int(np.sum(VOL[list(top(o["m1"]))] > 1)),
                     "top3_m2_later_vol": int(np.sum(VOL[list(top(o["m2"]))] > 1)),
                     "top3_true_later_vol": int(np.sum(VOL[list(top(c))] > 1))})
        for i, n in enumerate(NAMES):
            rk.append({"rep": r, "book": n, "volume": VOL[i], "m1": o["m1"][i], "m2": o["m2"][i], "true": c[i],
                       "rank_m1": ranks(o["m1"])[i], "rank_m2": ranks(o["m2"])[i], "rank_true": ranks(c)[i],
                       "after_share_of_buys": o["buy_after"][i] / max(o["buys"][i], 1)})
    reps = pd.DataFrame(rows)
    reps.to_csv(RES / "reps_base.csv", index=False)
    rk = pd.DataFrame(rk)
    byvol = rk.groupby("volume").agg(m1=("m1", "median"), m2=("m2", "median"), true=("true", "median"),
                                     rank_m1=("rank_m1", "mean"), rank_m2=("rank_m2", "mean"), rank_true=("rank_true", "mean"),
                                     after_share=("after_share_of_buys", "mean")).round(4).reset_index()
    byvol.to_csv(RES / "by_volume.csv", index=False)
    head = {"pairs": n_pairs, "random_order_disagree_expected": n_pairs / 2, "later_random_order_disagree_expected": 22.5,
            "disagree_m1_m2_mean": round(float(n_pairs - reps.agree_m1_m2.mean()), 2),
            "disagree_m1_m2_p10_p90": [float(n_pairs - reps.agree_m1_m2.quantile(0.9)), float(n_pairs - reps.agree_m1_m2.quantile(0.1))],
            "disagree_m1_true_mean": round(float(n_pairs - reps.agree_m1_true.mean()), 2),
            "disagree_m2_true_mean": round(float(n_pairs - reps.agree_m2_true.mean()), 2),
            "disagree_observed_true_mean": round(float(n_pairs - reps.agree_true_obs_true.mean()), 2),
            "later_pairs": 45,
            "disagree_m1_true_later_mean": round(float(45 - reps.agree_m1_true_later.mean()), 2),
            "disagree_m2_true_later_mean": round(float(45 - reps.agree_m2_true_later.mean()), 2),
            "m1_over_100_later_share": round(float(reps.m1_over_100_later_share.mean()), 4),
            "top3_m1_m2_overlap_mean": round(float(reps.top3_m1_m2_overlap.mean()), 3),
            "top3_m1_true_mean": round(float(reps.top3_m1_true.mean()), 3),
            "top3_m2_true_mean": round(float(reps.top3_m2_true.mean()), 3),
            "m1_over_100_books_mean": round(float(reps.m1_over_100_books.mean()), 2),
            "m1_over_100_vol1_total": int(reps.m1_over_100_vol1.sum()),
            "share_reps_m1_over_100": round(float((reps.m1_over_100_books > 0).mean()), 4),
            "top3_later_vol_mean": {"m1": round(float(reps.top3_m1_later_vol.mean()), 3), "m2": round(float(reps.top3_m2_later_vol.mean()), 3),
                                    "true": round(float(reps.top3_true_later_vol.mean()), 3)},
            "vol1_vs_vol2plus_median": {k: [float(rk[rk.volume == 1][k].median().round(4)), float(rk[rk.volume > 1][k].median().round(4))]
                                        for k in ["m1", "m2", "true"]},
            "vol1_after_share_of_buys": float(byvol.after_share[0]),
            "vol2plus_after_share_of_buys": round(float(rk[rk.volume > 1].after_share_of_buys.mean()), 4)}

    # 3) 確かめ：続きを待っていた人の割合×その人がそのまま買う割合×試し読みする割合の本ごとの差（27通り、各40回）
    grid = []
    for f in [0.1, 0.3, 0.6]:
        for d in [0.2, 0.4, 0.8]:
            for (tl, th) in [(0.15, 0.25), (0.10, 0.30), (0.05, 0.40)]:
                acc = []
                for r in range(40):
                    o = one_set(np.random.default_rng([SEED, 2, int(f * 10), int(d * 10), int(tl * 100), r]), **{**BASE, "f": f, "d": d, "t_lo": tl, "t_hi": th})
                    acc.append([n_pairs - agree(o["m1"], o["m2"]), n_pairs - agree(o["m1"], o["c"]), n_pairs - agree(o["m2"], o["c"]),
                                np.sum(o["m1"] > 1), np.sum(VOL[list(top(o["m1"]))] > 1)])
                acc = np.array(acc, float).mean(0)
                grid.append({"f": f, "d": d, "t_lo": tl, "t_hi": th, "disagree_m1_m2": round(acc[0], 2), "disagree_m1_true": round(acc[1], 2),
                             "disagree_m2_true": round(acc[2], 2), "m1_over_100_books": round(acc[3], 2), "top3_m1_later_vol": round(acc[4], 3)})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    robust = {"settings": int(len(gr)),
              "disagree_m1_m2_range": [float(gr.disagree_m1_m2.min()), float(gr.disagree_m1_m2.max())],
              "disagree_m1_true_range": [float(gr.disagree_m1_true.min()), float(gr.disagree_m1_true.max())],
              "disagree_m2_true_range": [float(gr.disagree_m2_true.min()), float(gr.disagree_m2_true.max())],
              "m1_over_100_books_range": [float(gr.m1_over_100_books.min()), float(gr.m1_over_100_books.max())],
              "top3_m1_later_vol_range": [float(gr.top3_m1_later_vol.min()), float(gr.top3_m1_later_vol.max())],
              "disagree_m1_m2_by_f": {str(f): [float(gr[gr.f == f].disagree_m1_m2.min()), float(gr[gr.f == f].disagree_m1_m2.max())] for f in [0.1, 0.3, 0.6]},
              "disagree_m1_m2_by_t": {f"{tl}-{th}": [float(gr[gr.t_lo == tl].disagree_m1_m2.min()), float(gr[gr.t_lo == tl].disagree_m1_m2.max())]
                                      for tl, th in [(0.15, 0.25), (0.10, 0.30), (0.05, 0.40)]},
              "disagree_m1_true_by_f": {str(f): [float(gr[gr.f == f].disagree_m1_true.min()), float(gr[gr.f == f].disagree_m1_true.max())] for f in [0.1, 0.3, 0.6]}}

    out = {"headline": head, "robust": robust,
           "setup": {"books": NAMES, **BASE, "vol1_views": [3000, 9000], "reps": 500, "grid_reps": 40}}
    json.dump(out, open(RES / "a1253_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の12冊。①と②と本当
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    x = np.arange(len(NAMES))
    ax.bar(x - 0.27, df.m1_buys_per_trial * 100, 0.27, color=INK, label="①買った数÷試し読みの数")
    ax.bar(x, df.m2_buys_per_view * 100, 0.27, color=ORANGE, label="②買った数÷紹介ページを見た数")
    ax.bar(x + 0.27, df.true_trial_to_buy * 100, 0.27, color=LIGHT, label="本当：試し読みした人のうち買った割合")
    ax.axhline(100, color=GRAY, lw=0.8, ls="--")
    ax.set_xticks(x); ax.set_xticklabels(NAMES)
    ax.set_xlabel("本（A・Bはシリーズ、数字は何巻目か）")
    ax.set_ylim(0, max(200, df.m1_buys_per_trial.max() * 100 + 20)); ax.set_ylabel("%")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("2巻目以降は、試し読みの数で割ると100%を超えることがある（1回分）", fontsize=12)
    save(fig, "a1253_one_set.png", SRC)

    # 図2：巻ごとの平均の順位（500回）
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    xv = np.arange(1, VOLS + 1)
    ax.plot(xv, byvol.rank_m1, color=INK, marker="o", label="①買った数÷試し読みの数")
    ax.plot(xv, byvol.rank_m2, color=ORANGE, marker="o", label="②買った数÷紹介ページを見た数")
    ax.plot(xv, byvol.rank_true, color=LIGHT, marker="o", label="本当：試し読みした人のうち買った割合")
    ax.set_ylim(12.5, 0.5); ax.set_yticks([1, 3, 6, 9, 12])
    ax.set_xlabel("何巻目か"); ax.set_ylabel("12冊の中の順位（平均、上ほど上位）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("①でも②でも1巻が下に来るが、本当の順位は巻によらない（500回の平均）", fontsize=11.5)
    save(fig, "a1253_rank_by_volume.png", SRC)

    # 図3：確かめ。27通りの、①と②で順が逆になった組
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    gs = gr.reset_index(drop=True)
    gx = np.arange(len(gs))
    ax.bar(gx, gs.disagree_m1_m2, color=BLUE, label="①と②で順が逆の組")
    ax.plot(gx, gs.disagree_m1_true, color=INK, marker="o", ms=4, lw=0, label="①と本当で順が逆の組")
    ax.plot(gx, gs.disagree_m2_true, color=ORANGE, marker="o", ms=4, lw=0, label="②と本当で順が逆の組")
    for kk in [9, 18]:
        ax.axvline(kk - 0.5, color=GRAY, lw=0.8, ls=":")
    for kk, f in enumerate([10, 30, 60]):
        ax.text(kk * 9 + 4, 41, f"続きを待っていた人{f}%", ha="center", fontsize=8)
    ax.set_xticks(gx); ax.set_xticklabels([f"{int(d*100)}" for d in gs.d], fontsize=6.5)
    ax.set_xlabel("27通り（下の数字は、待っていた人がそのまま買う割合%。同じ数字の中は試し読みする割合の本ごとの差が小・中・大の順）", fontsize=7.5)
    ax.set_ylim(0, 44); ax.set_ylabel("順が逆になった組（66組中、各40回の平均）", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    ax.set_title("①と②の逆は試し読みする割合の差で、①と本当の逆は待っていた人の多さで増える", fontsize=11)
    save(fig, "a1253_grid.png", SRC, y=-0.2)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(byvol)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
