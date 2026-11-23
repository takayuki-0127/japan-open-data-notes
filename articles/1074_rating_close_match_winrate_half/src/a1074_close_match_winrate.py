"""1074 力の近い人どうしを当てると、勝率はなぜ皆5割に近づくのか？（架空のデータ）

架空の対戦ゲームのリーグ。作成者が1人ひとりの「本当の強さ」を置き、点数の付け方（勝つと上がり負けると下がる点数）で
点数を付けながら対戦させる。相手の決め方を ①でたらめ ②点数の近い人どうし ③本当の強さの近い人どうし（参考）
の3つで比べ、勝率と点数がどれだけ本当の強さを表すかを数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1074
SRC = "架空の対戦ゲームのリーグ（作成者が乱数で作成、seed 1074）"
BASE = {"n": 2000, "sd": 200.0, "k": 32.0, "w": 50.0, "rounds": 400, "count_from": 200}


def pwin(d):
    """点の差 d（自分−相手）のときに勝つ確率。差400点で10対1"""
    return 1.0 / (1.0 + 10.0 ** (-d / 400.0))


def run(rng, mode, n=2000, sd=200.0, k=32.0, w=50.0, rounds=400, count_from=200, track=False):
    true = rng.normal(1500, sd, n)
    rating = np.full(n, 1500.0)
    wins = np.zeros(n); games = np.zeros(n); pexp = np.zeros(n); opp_true = np.zeros(n)
    rating_at_start = None
    blocks = []  # 20回ごとの勝率（強さの上位10%・中位・下位10%）
    q = np.quantile(true, [0.1, 0.45, 0.55, 0.9])
    grp = {"top": true >= q[3], "mid": (true >= q[1]) & (true <= q[2]), "bottom": true <= q[0]}
    bw = np.zeros(n); bg = 0
    for t in range(rounds):
        if t == count_from:
            rating_at_start = rating.copy()
        if mode == "random":
            order = rng.permutation(n)
        elif mode == "rating":
            order = np.argsort(rating + rng.normal(0, w, n) if w > 0 else rating + rng.random(n) * 1e-6)
        else:  # true
            order = np.argsort(true + rng.normal(0, w, n) if w > 0 else true + rng.random(n) * 1e-6)
        a, b = order[0::2], order[1::2]
        p = pwin(true[a] - true[b])
        win_a = (rng.random(len(a)) < p).astype(float)
        e = pwin(rating[a] - rating[b])
        rating[a] += k * (win_a - e); rating[b] -= k * (win_a - e)
        res = np.empty(n); res[a] = win_a; res[b] = 1 - win_a
        pe = np.empty(n); pe[a] = p; pe[b] = 1 - p
        ot = np.empty(n); ot[a] = true[b]; ot[b] = true[a]
        bw += res; bg += 1
        if (t + 1) % 20 == 0:
            blocks.append({"round_end": t + 1, **{g: float(bw[m].mean() / bg) for g, m in grp.items()}})
            bw[:] = 0; bg = 0
        if t >= count_from:
            wins += res; games += 1; pexp += pe; opp_true += ot
    wr = wins / games
    return {"true": true, "rating": rating, "rating_at_start": rating_at_start, "wr": wr,
            "pexp": pexp / games, "opp_true": opp_true / games, "blocks": blocks, "games": int(games[0])}


def spearman(x, y):
    rx = pd.Series(x).rank().to_numpy(); ry = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def summarize(o):
    t, wr, rt = o["true"], o["wr"], o["rating"]
    g = o["games"]
    top = t >= np.quantile(t, 0.9); bot = t <= np.quantile(t, 0.1)
    top10_true = np.argsort(-t)[: len(t) // 10]
    top10_wr = np.argsort(-wr)[: len(t) // 10]
    top10_rt = np.argsort(-rt)[: len(t) // 10]
    noise_sd = math.sqrt(float(np.mean(o["pexp"] * (1 - o["pexp"]))) / g)
    return {"wr_sd": float(wr.std()), "binom_noise_sd": noise_sd,
            "share_45_55": float(((wr >= 0.45) & (wr <= 0.55)).mean()),
            "mean_abs_p_minus_half": float(np.abs(o["pexp"] - 0.5).mean()),
            "spearman_wr_true": spearman(wr, t), "spearman_rating_true": spearman(rt, t),
            "corr_wr_gap": float(np.corrcoef(wr, t - o["rating_at_start"])[0, 1]),
            "top10_wr_mean": float(wr[top].mean()), "bottom10_wr_mean": float(wr[bot].mean()),
            "top10_hit_by_wr": float(len(set(top10_true) & set(top10_wr)) / len(top10_true)),
            "top10_hit_by_rating": float(len(set(top10_true) & set(top10_rt)) / len(top10_true)),
            "corr_opp_true": float(np.corrcoef(t, o["opp_true"])[0, 1]),
            "rating_err_sd": float((rt - t).std()),
            "rating_slope": float(np.polyfit(t, rt, 1)[0])}


def r(x, d=4):
    return round(float(x), d)


def binom_share(g, lo=0.45, hi=0.55, p=0.5):
    return sum(math.comb(g, i) * p ** i * (1 - p) ** (g - i) for i in range(g + 1) if lo - 1e-12 <= i / g <= hi + 1e-12)


def main():
    t0 = time.time()
    modes = [("random", "でたらめ"), ("rating", "点数の近い人どうし"), ("true", "本当の強さの近い人どうし（参考）")]
    outs, summ = {}, {}
    for i, (m, _) in enumerate(modes):
        outs[m] = run(np.random.default_rng([SEED, i]), m, **BASE)
        summ[m] = summarize(outs[m])
    tab = pd.DataFrame([{"mode": m, "label": lab, **{k: r(v) for k, v in summ[m].items()}} for m, lab in modes])
    tab.to_csv(RES / "by_mode.csv", index=False)
    blocks = pd.DataFrame(outs["rating"]["blocks"]); blocks.to_csv(RES / "blocks_rating_mode.csv", index=False)
    blocks_r = pd.DataFrame(outs["random"]["blocks"])

    o = outs["rating"]
    pd.DataFrame({"player_id": np.arange(1, BASE["n"] + 1), "true": o["true"].round(1),
                  "rating_end_close": o["rating"].round(1), "winrate_close": o["wr"].round(4),
                  "winrate_random": outs["random"]["wr"].round(4),
                  "rating_end_random": outs["random"]["rating"].round(1)}).to_csv(DATA / "players.csv", index=False)

    # 確かめ：強さの散らばり × 相手を決めるときの点数のゆらぎ × 1試合で動かす点の幅（27通り）
    grid = []
    j = 0
    for sd in [100.0, 200.0, 300.0]:
        for w in [0.0, 50.0, 200.0]:
            for k in [16.0, 32.0, 64.0]:
                kw = dict(BASE, sd=sd, w=w, k=k)
                s = summarize(run(np.random.default_rng([SEED, 100 + j]), "rating", **kw)); j += 1
                grid.append({"sd": sd, "w": w, "k": k, **{kk: r(s[kk]) for kk in
                             ["wr_sd", "binom_noise_sd", "share_45_55", "spearman_wr_true", "spearman_rating_true",
                              "top10_wr_mean", "top10_hit_by_wr", "top10_hit_by_rating", "rating_slope"]}})
    g = pd.DataFrame(grid); g.to_csv(RES / "grid.csv", index=False)
    # でたらめな相手の場合も同じ3通りの散らばりで
    rnd = []
    for i, sd in enumerate([100.0, 200.0, 300.0]):
        s = summarize(run(np.random.default_rng([SEED, 200 + i]), "random", **dict(BASE, sd=sd)))
        rnd.append({"sd": sd, **{kk: r(s[kk]) for kk in ["wr_sd", "share_45_55", "spearman_wr_true", "spearman_rating_true"]}})

    G = BASE["rounds"] - BASE["count_from"]
    sr, sc, st = summ["random"], summ["rating"], summ["true"]
    out = {"base_setting": BASE,
           "by_mode": tab.to_dict("records"),
           "formula": {"games_counted": G, "binom_sd_at_half": r(math.sqrt(0.25 / G)),
                       "binom_share_45_55_at_half": r(binom_share(G)),
                       "win_prob_diff_100": r(pwin(100)), "win_prob_diff_200": r(pwin(200)), "win_prob_diff_400": r(pwin(400))},
           "headline": {"random_wr_sd_pt": r(sr["wr_sd"] * 100, 2), "close_wr_sd_pt": r(sc["wr_sd"] * 100, 2),
                        "close_binom_noise_sd_pt": r(sc["binom_noise_sd"] * 100, 2),
                        "random_share_45_55_pct": r(sr["share_45_55"] * 100, 2),
                        "close_share_45_55_pct": r(sc["share_45_55"] * 100, 2),
                        "true_share_45_55_pct": r(st["share_45_55"] * 100, 2),
                        "random_spearman_wr": r(sr["spearman_wr_true"], 3), "close_spearman_wr": r(sc["spearman_wr_true"], 3),
                        "close_spearman_rating": r(sc["spearman_rating_true"], 3),
                        "random_spearman_rating": r(sr["spearman_rating_true"], 3),
                        "random_top10_wr_pct": r(sr["top10_wr_mean"] * 100, 2), "close_top10_wr_pct": r(sc["top10_wr_mean"] * 100, 2),
                        "close_bottom10_wr_pct": r(sc["bottom10_wr_mean"] * 100, 2),
                        "random_top10_hit_wr_pct": r(sr["top10_hit_by_wr"] * 100, 2),
                        "close_top10_hit_wr_pct": r(sc["top10_hit_by_wr"] * 100, 2),
                        "close_top10_hit_rating_pct": r(sc["top10_hit_by_rating"] * 100, 2),
                        "close_corr_wr_gap": r(sc["corr_wr_gap"], 3), "close_corr_opp_true": r(sc["corr_opp_true"], 3),
                        "close_mean_abs_p_half_pt": r(sc["mean_abs_p_minus_half"] * 100, 2),
                        "random_mean_abs_p_half_pt": r(sr["mean_abs_p_minus_half"] * 100, 2),
                        "close_rating_err_sd": r(sc["rating_err_sd"], 1),
                        "close_rating_slope": r(sc["rating_slope"], 2), "random_rating_slope": r(sr["rating_slope"], 2),
                        "true_spearman_wr": r(st["spearman_wr_true"], 3),
                        "close_wr_sd_over_noise": r(sc["wr_sd"] / sc["binom_noise_sd"], 3),
                        "top_first20_wr_pct": r(blocks.top.iloc[0] * 100, 2), "top_last20_wr_pct": r(blocks.top.iloc[-1] * 100, 2),
                        "bottom_first20_wr_pct": r(blocks.bottom.iloc[0] * 100, 2),
                        "bottom_last20_wr_pct": r(blocks.bottom.iloc[-1] * 100, 2)},
           "grid_summary": {"n": int(len(g)),
                            "share_45_55_min": r(g.share_45_55.min()), "share_45_55_max": r(g.share_45_55.max()),
                            "spearman_wr_min": r(g.spearman_wr_true.min(), 3), "spearman_wr_max": r(g.spearman_wr_true.max(), 3),
                            "spearman_rating_min": r(g.spearman_rating_true.min(), 3),
                            "spearman_rating_max": r(g.spearman_rating_true.max(), 3),
                            "rating_beats_wr_count": int((g.spearman_rating_true > g.spearman_wr_true).sum()),
                            "top10_wr_min": r(g.top10_wr_mean.min()), "top10_wr_max": r(g.top10_wr_mean.max()),
                            "w200_spearman_wr_min": r(g[g.w == 200].spearman_wr_true.min(), 3),
                            "w200_spearman_wr_max": r(g[g.w == 200].spearman_wr_true.max(), 3),
                            "w0_spearman_wr_min": r(g[g.w == 0].spearman_wr_true.min(), 3),
                            "w0_spearman_wr_max": r(g[g.w == 0].spearman_wr_true.max(), 3),
                            "wr_sd_below_noise_count": int((g.wr_sd < g.binom_noise_sd).sum()),
                            "slope_min": r(g.rating_slope.min(), 2), "slope_max": r(g.rating_slope.max(), 2),
                            "w200_slope_min": r(g[g.w == 200].rating_slope.min(), 2),
                            "w200_slope_max": r(g[g.w == 200].rating_slope.max(), 2)},
           "random_by_sd": rnd}
    json.dump(out, open(RES / "a1074_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：勝率の分布（でたらめ と 点数の近い人どうし）
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8), sharey=True)
    bins = np.arange(0.0, 1.0001, 0.02)
    for ax, m, c in [(axes[0], "random", GRAY), (axes[1], "rating", BLUE)]:
        ax.hist(outs[m]["wr"], bins=bins, color=c)
        ax.axvspan(0.45, 0.55, color=ORANGE, alpha=0.12)
        ax.set_xlim(0, 1); ax.set_xlabel(f"後半{G}試合の勝率")
        lab = dict(modes)[m]
        ax.set_title(f"相手の決め方：{lab}\n45〜55%に入る人 {summ[m]['share_45_55']*100:.2f}%", fontsize=11)
    axes[0].set_ylabel("人数（2,000人中）")
    fig.suptitle("力の近い相手と当てると、ほとんどの人の勝率が5割前後に集まる", fontsize=13, y=1.03)
    save(fig, "a1074_hist.png", SRC)

    # 図2：本当の強さと勝率・点数（点数の近い人どうし）
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.9))
    ax = axes[0]
    ax.scatter(o["true"], o["wr"] * 100, s=4, color=BLUE, alpha=.35)
    ax.scatter(outs["random"]["true"], outs["random"]["wr"] * 100, s=4, color=GRAY, alpha=.25)
    ax.set_xlabel("本当の強さ"); ax.set_ylabel(f"後半{G}試合の勝率（%）"); ax.set_ylim(0, 100)
    ax.text(0.02, 0.97, f"灰：でたらめ（順位相関 {sr['spearman_wr_true']:.3f}）\n青：点数の近い人どうし（{sc['spearman_wr_true']:.3f}）",
            transform=ax.transAxes, fontsize=8.5, va="top")
    ax.set_title("勝率", fontsize=11)
    ax = axes[1]
    ax.scatter(o["true"], o["rating"], s=4, color=BLUE, alpha=.35)
    lo, hi = o["true"].min(), o["true"].max()
    ax.plot([lo, hi], [lo, hi], color=INK, lw=.8, ls="--")
    ax.set_xlabel("本当の強さ"); ax.set_ylabel("最後の点数")
    ax.text(0.02, 0.97, f"点数の近い人どうし（順位相関 {sc['spearman_rating_true']:.3f}）", transform=ax.transAxes, fontsize=8.5, va="top")
    ax.set_title("点数", fontsize=11)
    fig.suptitle("力の近い相手と当てると、強さは勝率ではなく点数に出る", fontsize=13, y=1.03)
    save(fig, "a1074_scatter.png", SRC)

    # 図3：20試合ごとの勝率の動き（強さの上位10%・中位・下位10%）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for col, lab, c in [("top", "強さの上位10%", ORANGE), ("mid", "強さが真ん中の10%", GRAY), ("bottom", "強さの下位10%", BLUE)]:
        ax.plot(blocks.round_end, blocks[col] * 100, color=c, marker="o", ms=3, label=f"点数の近い人どうし：{lab}")
        ax.plot(blocks_r.round_end, blocks_r[col] * 100, color=c, lw=.9, ls=":", label=f"でたらめ：{lab}")
    ax.axhline(50, color=INK, lw=.7, ls="--")
    ax.axvline(BASE["count_from"], color=GRAY, lw=.7)
    ax.text(BASE["count_from"] + 4, 3, "ここから後半", fontsize=8, color=GRAY)
    ax.set_ylim(0, 100); ax.set_xlabel("何試合目まで（20試合ごとの勝率）"); ax.set_ylabel("勝率（%）")
    ax.legend(frameon=False, fontsize=7.5, loc="center", bbox_to_anchor=(0.58, 0.67), ncol=2)
    ax.set_title("強い人の勝率は、点数が上がるにつれて5割に下りてくる")
    save(fig, "a1074_blocks.png", SRC)

    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, indent=1))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
