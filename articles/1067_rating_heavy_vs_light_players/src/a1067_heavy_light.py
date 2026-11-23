"""1067 1日に何十試合もする人と、たまにしか対戦しない人の点数は、同じ物差しで比べられるのか？（架空のデータ）

架空の対戦ゲームのリーグ1,000人。1人ひとりに本当の強さと、1日に対戦する回数（よく対戦する人は
1日30試合、たまにの人は数日に1試合）を作成者が置く。対戦は、その時間に遊んでいる人どうしを
でたらめに組む。点数の付け方は、試合ごとに「勝ち負け（1か0）− 勝つ見込み」に幅 K を掛けて、
勝った人に足し、負けた人から引くもの。全員1500から始めた1シーズン（60日）の終わりに、
対戦の多さで点数の読み方がどう違うか、上位の表に誰が載るかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1067
SRC = "架空の対戦ゲームのリーグ（作成者が乱数で作成、seed 1067）"
N = 1000
MEAN, SD = 1500.0, 200.0
BASE = {"K": 32.0, "rho": 0.0, "days": 60}
ACT_MEDIAN, ACT_LOGSD, ACT_MIN, ACT_MAX = 1.5, 1.3, 0.05, 30.0
SLOTS = 30  # 1日を30の時間帯に分ける（1日30試合の人は毎回遊ぶ）
GROUPS = [(-1, 0.2, "週1回くらいまで（1日0.2試合未満）"), (0.2, 1.0, "1日0.2〜1試合"),
          (1.0, 10.0, "1日1〜10試合"), (10.0, 99, "1日10試合以上")]
GSHORT = ["週1回くらいまで", "1日0.2〜1試合", "1日1〜10試合", "1日10試合以上"]
TOP = 20
MIN_GAMES = 50


def expect(ra, rb):
    """a が b に勝つ見込み（点数の差400で10倍の比になる形）"""
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def season(rng, R, K, rho, days):
    zt = rng.standard_normal((R, N))
    true = MEAN + SD * zt
    za = rho * zt + np.sqrt(1 - rho ** 2) * rng.standard_normal((R, N))
    act = np.clip(ACT_MEDIAN * np.exp(ACT_LOGSD * za), ACT_MIN, ACT_MAX)  # 1日あたりの対戦の回数（のぞむ数）
    p = act / SLOTS
    rating = np.full((R, N), MEAN)
    mx = rating.copy()
    games = np.zeros((R, N))
    rows = np.arange(R)[:, None]
    half = np.arange(N // 2)[None, :]
    for _ in range(days * SLOTS):
        on = rng.random((R, N)) < p
        m = on.sum(1)
        key = np.where(on, rng.random((R, N)), 2.0)
        perm = np.argsort(key, axis=1)
        a, b = perm[:, 0::2], perm[:, 1::2]
        valid = (2 * half + 1) < m[:, None]
        ta, tb = true[rows, a], true[rows, b]
        win = (rng.random(a.shape) < expect(ta, tb)).astype(float)
        ra, rb = rating[rows, a], rating[rows, b]
        d = K * (win - expect(ra, rb)) * valid
        rating[rows, a] = ra + d
        rating[rows, b] = rb - d
        games[rows, a] += valid
        games[rows, b] += valid
        mx = np.maximum(mx, rating)
    return true, act, rating, mx, games


def group_of(act):
    g = np.zeros(act.shape, int)
    for i, (lo, hi, _) in enumerate(GROUPS):
        g[(act >= lo) & (act < hi)] = i
    return g


def analyze(true, act, rating, mx, games):
    R = true.shape[0]
    grp = group_of(act)
    res = {}
    # 上位の表
    true_rank = np.argsort(np.argsort(-true, 1), 1) + 1
    lists = {"end": rating, "max": mx, "end_min50": np.where(games >= MIN_GAMES, rating, -np.inf)}
    for name, val in lists.items():
        top = np.argsort(-val, 1)[:, :TOP]
        tg = np.take_along_axis(grp, top, 1)
        res[f"top_{name}_share"] = [float((tg == i).mean()) for i in range(len(GROUPS))]
        res[f"top_{name}_true_top50"] = float((np.take_along_axis(true_rank, top, 1) <= 50).mean())
        res[f"top_{name}_true_mean"] = float(np.take_along_axis(true, top, 1).mean())
    ttop = np.argsort(-true, 1)[:, :TOP]
    res["top_true_share"] = [float((np.take_along_axis(grp, ttop, 1) == i).mean()) for i in range(len(GROUPS))]
    # 本当の上位20人が、期末の点数の上位20人に入った割合（対戦の多さごと）
    end_rank = np.argsort(np.argsort(-rating, 1), 1) + 1
    tt = true_rank <= TOP
    res["true_top_found"] = [float(((end_rank <= TOP) & tt & (grp == i)).sum() / max(1, (tt & (grp == i)).sum()))
                             for i in range(len(GROUPS))]
    # 対戦の多さごと
    res["groups"] = []
    for i in range(len(GROUPS)):
        m = grp == i
        e = rating[m] - true[m]
        strong = m & (true >= MEAN + SD)  # 本当の強さが平均＋1標準偏差（1700）以上
        weak = m & (true <= MEAN - SD)
        band = m & (rating >= 1650) & (rating < 1750)
        cs = []
        for rr in range(R):
            mm = m[rr]
            if mm.sum() > 5:
                cs.append(np.corrcoef(rating[rr, mm], true[rr, mm])[0, 1])
        res["groups"].append({
            "share_players": float(m.mean()), "games_median": float(np.median(games[m])),
            "abs_err": float(np.abs(e).mean()), "corr": float(np.mean(cs)) if cs else None,
            "strong_bias": float((rating[strong] - true[strong]).mean()) if strong.any() else None,
            "weak_bias": float((rating[weak] - true[weak]).mean()) if weak.any() else None,
            "max_minus_end": float((mx[m] - rating[m]).mean()),
            "band1700_true_mean": float(true[band].mean()) if band.sum() >= 30 else None,
            "band1700_n": int(band.sum())})
    return res


def r(x, d=4):
    return None if x is None else round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    R = 20
    true, act, rating, mx, games = season(rng, R, BASE["K"], BASE["rho"], BASE["days"])
    base = analyze(true, act, rating, mx, games)

    # 1回分のデータ（data）
    pd.DataFrame({"player": np.arange(1, N + 1), "true_strength": true[0].round(1), "games_per_day_wanted": act[0].round(3),
                  "games_played": games[0].astype(int), "rating_end": rating[0].round(1), "rating_season_max": mx[0].round(1)}
                 ).to_csv(DATA / "season_one_run.csv", index=False)

    gtab = pd.DataFrame([{"group": GROUPS[i][2], "share_players_pct": r(g["share_players"] * 100, 2),
                          "games_median": r(g["games_median"], 1), "mean_abs_error": r(g["abs_err"], 2),
                          "corr_rating_true": r(g["corr"], 3), "strong_players_bias": r(g["strong_bias"], 2),
                          "weak_players_bias": r(g["weak_bias"], 2), "season_max_minus_end": r(g["max_minus_end"], 2),
                          "true_mean_of_rating_1650_1750": r(g["band1700_true_mean"], 2), "n_rating_1650_1750": g["band1700_n"],
                          "share_in_true_top20_pct": r(base["top_true_share"][i] * 100, 2),
                          "share_in_top20_end_pct": r(base["top_end_share"][i] * 100, 2),
                          "share_in_top20_max_pct": r(base["top_max_share"][i] * 100, 2),
                          "share_in_top20_end_min50_pct": r(base["top_end_min50_share"][i] * 100, 2),
                          "true_top20_found_in_end_top20_pct": r(base["true_top_found"][i] * 100, 2)}
                         for i, g in enumerate(base["groups"])])
    gtab.to_csv(RES / "by_activity.csv", index=False)
    lists = pd.DataFrame([{"list": nm, "true_top50_share_pct": r(base[f"top_{k}_true_top50"] * 100, 2),
                           "true_strength_mean": r(base[f"top_{k}_true_mean"], 1)}
                          for k, nm in [("end", "期末の点数の上位20人"), ("max", "シーズン中の最高点数の上位20人"),
                                        ("end_min50", f"{MIN_GAMES}試合以上の人だけで期末の点数の上位20人")]])
    lists.to_csv(RES / "top20_lists.csv", index=False)

    # 確かめ：幅K × 対戦の多さと強さの相関 × シーズンの日数（27通り）
    grid = []
    j = 0
    for K in [16.0, 32.0, 48.0]:
        for rho in [-0.3, 0.0, 0.3]:
            for days in [30, 60, 120]:
                o = analyze(*season(np.random.default_rng(SEED * 100 + j), 4, K, rho, days))
                j += 1
                gg = o["groups"]
                grid.append({"K": K, "rho": rho, "days": days,
                             "light_abs_err": r(gg[0]["abs_err"], 2), "heavy_abs_err": r(gg[3]["abs_err"], 2),
                             "light_strong_bias": r(gg[0]["strong_bias"], 2), "heavy_strong_bias": r(gg[3]["strong_bias"], 2),
                             "heavy_share_true_top20_pct": r(o["top_true_share"][3] * 100, 2),
                             "heavy_share_top20_end_pct": r(o["top_end_share"][3] * 100, 2),
                             "heavy_share_top20_max_pct": r(o["top_max_share"][3] * 100, 2),
                             "light_share_true_top20_pct": r(o["top_true_share"][0] * 100, 2),
                             "light_share_top20_end_pct": r(o["top_end_share"][0] * 100, 2),
                             "top20_end_true_top50_pct": r(o["top_end_true_top50"] * 100, 2),
                             "top20_max_true_top50_pct": r(o["top_max_true_top50"] * 100, 2),
                             "top20_min50_true_top50_pct": r(o["top_end_min50_true_top50"] * 100, 2),
                             "heavy_max_minus_end": r(gg[3]["max_minus_end"], 2), "light_max_minus_end": r(gg[0]["max_minus_end"], 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    g["max_minus_true"] = g.heavy_share_top20_max_pct - g.heavy_share_true_top20_pct
    g["max_minus_end_list"] = g.top20_end_true_top50_pct - g.top20_max_true_top50_pct

    gb = base["groups"]
    out = {"base_setting": dict(BASE, n_players=N, true_mean=MEAN, true_sd=SD, activity_median_per_day=ACT_MEDIAN,
                                activity_log_sd=ACT_LOGSD, activity_clip=[ACT_MIN, ACT_MAX], slots_per_day=SLOTS, reps=R,
                                top=TOP, min_games=MIN_GAMES, groups=[x[2] for x in GROUPS]),
           "headline": {
               "light_share_pct": r(gb[0]["share_players"] * 100, 2), "heavy_share_pct": r(gb[3]["share_players"] * 100, 2),
               "light_games_median": r(gb[0]["games_median"], 1), "heavy_games_median": r(gb[3]["games_median"], 1),
               "light_abs_err": r(gb[0]["abs_err"], 2), "heavy_abs_err": r(gb[3]["abs_err"], 2),
               "mid_abs_err": r(gb[2]["abs_err"], 2),
               "light_strong_bias": r(gb[0]["strong_bias"], 2), "heavy_strong_bias": r(gb[3]["strong_bias"], 2),
               "light_weak_bias": r(gb[0]["weak_bias"], 2), "heavy_weak_bias": r(gb[3]["weak_bias"], 2),
               "light_corr": r(gb[0]["corr"], 3), "heavy_corr": r(gb[3]["corr"], 3),
               "light_band1700_true": r(gb[0]["band1700_true_mean"], 2), "heavy_band1700_true": r(gb[3]["band1700_true_mean"], 2),
               "mid_band1700_true": r(gb[2]["band1700_true_mean"], 2),
               "heavy_max_minus_end": r(gb[3]["max_minus_end"], 2), "light_max_minus_end": r(gb[0]["max_minus_end"], 2),
               "heavy_true_top20_pct": r(base["top_true_share"][3] * 100, 2),
               "heavy_top20_end_pct": r(base["top_end_share"][3] * 100, 2),
               "heavy_top20_max_pct": r(base["top_max_share"][3] * 100, 2),
               "heavy_top20_max_minus_true_pt": r((base["top_max_share"][3] - base["top_true_share"][3]) * 100, 2),
               "heavy_top20_end_minus_true_pt": r((base["top_end_share"][3] - base["top_true_share"][3]) * 100, 2),
               "light_over_heavy_abs_err": r(gb[0]["abs_err"] / gb[3]["abs_err"], 3),
               "band1700_lowmid_minus_heavy": r(gb[1]["band1700_true_mean"] - gb[3]["band1700_true_mean"], 2),
               "light_true_top20_pct": r(base["top_true_share"][0] * 100, 2),
               "light_top20_end_pct": r(base["top_end_share"][0] * 100, 2),
               "top20_end_true_top50_pct": r(base["top_end_true_top50"] * 100, 2),
               "top20_max_true_top50_pct": r(base["top_max_true_top50"] * 100, 2),
               "top20_min50_true_top50_pct": r(base["top_end_min50_true_top50"] * 100, 2),
               "light_true_top_found_pct": r(base["true_top_found"][0] * 100, 2),
               "heavy_true_top_found_pct": r(base["true_top_found"][3] * 100, 2)},
           "constants": {"win_prob_scale": 400, "strong_threshold": MEAN + SD, "weak_threshold": MEAN - SD,
                         "rating_band": [1650, 1750], "slots_per_day": SLOTS},
           "by_activity": gtab.to_dict("records"),
           "top20_lists": lists.to_dict("records"),
           "grid_summary": {"n": int(len(g)),
                            "light_abs_err_min": r(g.light_abs_err.min(), 2), "light_abs_err_max": r(g.light_abs_err.max(), 2),
                            "heavy_abs_err_min": r(g.heavy_abs_err.min(), 2), "heavy_abs_err_max": r(g.heavy_abs_err.max(), 2),
                            "light_gt_heavy_err_count": int((g.light_abs_err > g.heavy_abs_err).sum()),
                            "light_strong_bias_min": r(g.light_strong_bias.min(), 2), "light_strong_bias_max": r(g.light_strong_bias.max(), 2),
                            "heavy_top20_max_minus_true_pt_min": r(g.max_minus_true.min(), 2),
                            "heavy_top20_max_minus_true_pt_max": r(g.max_minus_true.max(), 2),
                            "heavy_max_gt_true_count": int((g.max_minus_true > 0).sum()),
                            "heavy_max_gt_end_count": int((g.heavy_share_top20_max_pct > g.heavy_share_top20_end_pct).sum()),
                            "heavy_max_minus_end_rating_min": r(g.heavy_max_minus_end.min(), 2),
                            "heavy_max_minus_end_rating_max": r(g.heavy_max_minus_end.max(), 2),
                            "light_max_minus_end_rating_max": r(g.light_max_minus_end.max(), 2),
                            "max_list_worse_count": int((g.max_minus_end_list > 0).sum()), "max_list_better_count": int((g.max_minus_end_list < 0).sum()),
                            "max_list_equal_count": int((g.max_minus_end_list == 0).sum()),
                            "max_list_better_rho03_count": int(((g.max_minus_end_list < 0) & (g.rho == 0.3)).sum()),
                            "top20_end_true_top50_min": r(g.top20_end_true_top50_pct.min(), 2),
                            "top20_end_true_top50_max": r(g.top20_end_true_top50_pct.max(), 2),
                            "top20_max_true_top50_min": r(g.top20_max_true_top50_pct.min(), 2),
                            "top20_max_true_top50_max": r(g.top20_max_true_top50_pct.max(), 2),
                            "light_top20_end_max_pct": r(g.light_share_top20_end_pct.max(), 2)},
           "run_sec": None}

    # 図1：期末の点数と本当の強さ（1回分、対戦の多さで色分け）
    grp0 = group_of(act[0])
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    cols = [ORANGE, "#c9a227", LIGHT, BLUE]
    for i in range(len(GROUPS)):
        m = grp0 == i
        ax.scatter(true[0, m], rating[0, m], s=9 if i else 14, color=cols[i], alpha=0.75, label=GSHORT[i], lw=0)
    lim = [900, 2150]
    ax.plot(lim, lim, color=GRAY, lw=0.8, ls="--")
    ax.text(1960, 2110, "点数＝本当の強さ", fontsize=8, color=GRAY, ha="right")
    ax.axhline(MEAN, color=GRAY, lw=0.6, ls=":")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("本当の強さ（作成者が置いた値）")
    ax.set_ylabel("シーズンの終わりの点数")
    ax.set_title("たまにしか対戦しない人の点数は、初めの1500の近くに残る")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left", markerscale=1.8)
    save(fig, "a1067_scatter.png", SRC + "。1回分の1,000人、60日")

    # 図2：対戦の多さごとのずれ（棒、0から）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(len(GROUPS))
    v = gtab.mean_abs_error.values
    ax.bar(x, v, color=cols)
    for xi, vi, gm in zip(x, v, gtab.games_median):
        ax.text(xi, vi + 3, f"{vi:g}\n（{gm:g}試合）", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(GSHORT)
    ax.set_ylim(0, v.max() * 1.3)
    ax.set_ylabel("点数と本当の強さの差（絶対値の平均）")
    ax.set_title("点数のずれは、対戦の少ない人で大きい（括弧は試合数の中央値）")
    save(fig, "a1067_error_by_activity.png", SRC + "。20回の平均。60日")

    # 図3：上位20人の表に載る人の内訳（棒、0から）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    kinds = [("share_in_true_top20_pct", "本当の上位20人"), ("share_in_top20_end_pct", "期末の点数の上位20人"),
             ("share_in_top20_max_pct", "最高点数の上位20人"), ("share_in_top20_end_min50_pct", f"{MIN_GAMES}試合以上で\n期末の上位20人")]
    bottom = np.zeros(len(kinds))
    for i in range(len(GROUPS)):
        vals = np.array([gtab.loc[i, k] for k, _ in kinds])
        ax.bar(np.arange(len(kinds)), vals, bottom=bottom, color=cols[i], label=GSHORT[i], width=0.6)
        for xi, (vv, bb) in enumerate(zip(vals, bottom)):
            if vv >= 6:
                ax.text(xi, bb + vv / 2, f"{vv:g}%", ha="center", va="center", fontsize=8.5, color=INK)
        bottom += vals
    ax.set_xticks(np.arange(len(kinds)))
    ax.set_xticklabels([k[1] for k in kinds], fontsize=9.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("表に載った人の内訳（%）")
    ax.set_title("最高点数で並べると、1日10試合以上の人が増える")
    ax.legend(fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    save(fig, "a1067_top20.png", SRC + "。20回の平均。60日")

    with open(RES / "a1067_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=lambda v: v.item() if isinstance(v, np.generic) else v)
    pd.set_option("display.width", 250)
    print(gtab.T.to_string())
    print(lists.to_string())
    print(json.dumps(out["headline"], ensure_ascii=False))
    print(json.dumps(out["grid_summary"], ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
