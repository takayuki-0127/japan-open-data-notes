"""827 連勝の長さは、偶然でどこまで伸びるのか？（架空のデータ）

架空のチーム。1シーズン140試合。1試合ごとに本当の勝率で勝ち（引き分けなし）、
基本は試合どうしが互いに影響しない（勢いなし）と置く。シーズンの最長連勝を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 827
SRC = "架空のチームの試合結果（作成者が乱数で作成、seed 827）"
rng = np.random.default_rng(SEED)
G = 140
REPS = 100_000


def games(rng, p, shape, d=0.0):
    """試合の勝ち負け（shape=(..., G)）。d>0 なら勝った次は p+d、負けた次は全体の勝率が p になる値"""
    p = np.broadcast_to(np.asarray(p, float), shape[:-1])
    if d == 0:
        return rng.random(shape) < p[..., None]
    p_ww = np.minimum(p + d, 0.99)
    p_lw = p * (1 - p_ww) / (1 - p)
    w = np.zeros(shape, bool)
    w[..., 0] = rng.random(shape[:-1]) < p
    for j in range(1, shape[-1]):
        w[..., j] = rng.random(shape[:-1]) < np.where(w[..., j - 1], p_ww, p_lw)
    return w


def longest_run(w):
    cur = np.zeros(w.shape[:-1], int)
    mx = np.zeros(w.shape[:-1], int)
    for j in range(w.shape[-1]):
        cur = (cur + 1) * w[..., j]
        mx = np.maximum(mx, cur)
    return mx


def dist_summary(x):
    return {"mean": round(float(x.mean()), 2), "median": float(np.median(x)),
            "p10": float(np.quantile(x, .1)), "p90": float(np.quantile(x, .9)),
            "share_ge_5": round(float((x >= 5).mean()), 4), "share_ge_7": round(float((x >= 7).mean()), 4),
            "share_ge_10": round(float((x >= 10).mean()), 4), "share_ge_12": round(float((x >= 12).mean()), 4)}


def main():
    t0 = time.time()

    # 1) 1チーム・140試合の最長連勝（勝率0.4・0.5・0.6）
    single, hist = {}, {}
    for p in [0.4, 0.5, 0.6]:
        x = longest_run(games(rng, p, (REPS, G)))
        single[str(p)] = dist_summary(x)
        hist[p] = np.bincount(x, minlength=31)[:31] / REPS
    hdf = pd.DataFrame({"longest": np.arange(31), **{f"p{int(p*100)}": np.round(h, 5) for p, h in hist.items()}})
    hdf.to_csv(RES / "longest_streak_dist_140games.csv", index=False)

    # 2) 実力が同じ12チーム（全員勝率0.5）のリーグで、いちばん長い連勝
    L = 20000
    xl = longest_run(games(rng, 0.5, (L, 12, G)))
    league_max = xl.max(1)
    league_eq = dist_summary(league_max)

    # 3) 実力に差のある12チーム（本当の勝率 平均0.5・標準偏差0.05）。最長連勝のチームは本当にいちばん強いか
    def league_check(sd, d=0.0, seed_add=0):
        r = np.random.default_rng(SEED * 10 + seed_add)
        tp = np.clip(r.normal(0.5, sd, (L, 12)), 0.3, 0.7)
        xx = longest_run(games(r, tp, (L, 12, G), d))
        # 最長連勝のチーム（同じ長さは乱数で1つ選ぶ）
        key = xx + r.random(xx.shape) * 0.5
        lead = key.argmax(1)
        rank_true = (-tp).argsort(1).argsort(1) + 1  # 本当の勝率の順位
        lt = rank_true[np.arange(L), lead]
        corr = float(np.corrcoef(xx.ravel(), tp.ravel())[0, 1])
        return {"true_sd": sd, "p_streak_leader_is_true_best": round(float((lt == 1).mean()), 4),
                "p_streak_leader_in_true_top3": round(float((lt <= 3).mean()), 4),
                "streak_leader_true_rank_median": float(np.median(lt)),
                "streak_leader_true_p_mean": round(float(tp[np.arange(L), lead].mean()), 4),
                "league_max_streak_median": float(np.median(xx.max(1))),
                "corr_longest_vs_true_p": round(corr, 3)}, tp, xx
    lv = []
    for k, sd in enumerate([0.03, 0.05, 0.08]):
        res, tp, xx = league_check(sd, seed_add=k)
        lv.append(res)
        if sd == 0.05:
            tp05, xx05 = tp, xx
    lv = pd.DataFrame(lv)
    lv.to_csv(RES / "streak_leader_vs_true.csv", index=False)
    # 本当の勝率の帯ごとの最長連勝（差0.05）
    bands = pd.cut(tp05.ravel(), [0.3, 0.45, 0.48, 0.52, 0.55, 0.7])
    bt = pd.DataFrame({"band": bands, "longest": xx05.ravel()}).groupby("band", observed=True)["longest"]
    band_tab = pd.DataFrame({"teams": bt.size(), "median": bt.median(), "p10": bt.quantile(.1), "p90": bt.quantile(.9)})
    band_tab.index = band_tab.index.astype(str)
    band_tab.to_csv(RES / "longest_by_true_band.csv")

    # 4) 勢い：勝った次は勝ちやすいと置くと、最長連勝は伸びるか。1シーズンの最長連勝で見分けられるか
    mom = []
    xs_mom = {}
    for d in [0.0, 0.05, 0.10, 0.20]:
        x = longest_run(games(rng, 0.5, (REPS, G), d))
        xs_mom[d] = x
        s = dist_summary(x); s["d"] = d
        s["p_after_win"] = round(0.5 + d, 2); s["p_after_loss"] = round(0.5 * (1 - (0.5 + d)) / 0.5, 2)
        mom.append(s)
    x0 = xs_mom[0.0]
    for row in mom:
        x = xs_mom[row["d"]]
        i, j = rng.integers(0, REPS, 200000), rng.integers(0, REPS, 200000)
        row["p_longer_than_no_momentum"] = round(float((x[i] > x0[j]).mean()), 4)
        row["p_tie_with_no_momentum"] = round(float((x[i] == x0[j]).mean()), 4)
        # 勢いなしの90%点を超える割合（「偶然では長すぎる」とする線を超える割合）
        row["share_above_no_momentum_p95"] = round(float((x > np.quantile(x0, .95)).mean()), 4)
    mom = pd.DataFrame(mom)[["d", "p_after_win", "p_after_loss", "mean", "median", "p10", "p90", "share_ge_7",
                             "share_ge_10", "p_longer_than_no_momentum", "p_tie_with_no_momentum",
                             "share_above_no_momentum_p95"]]
    mom.to_csv(RES / "momentum_check.csv", index=False)
    no_mom_p95 = float(np.quantile(x0, .95))

    # 確かめ：試合数を変える（勝率0.5、1チーム）
    by_g = []
    for g in [40, 70, 140, 280]:
        x = longest_run(games(rng, 0.5, (REPS, g)))
        s = dist_summary(x); s["games"] = g
        by_g.append(s)
    by_g = pd.DataFrame(by_g)[["games", "mean", "median", "p10", "p90", "share_ge_7", "share_ge_10"]]
    by_g.to_csv(RES / "longest_by_games.csv", index=False)

    # 1回分のリーグ（実力が同じ12チーム、data）
    one = games(np.random.default_rng(SEED + 1), 0.5, (12, G))
    long = pd.DataFrame({"team_id": np.repeat(np.arange(1, 13), G), "game": np.tile(np.arange(1, G + 1), 12),
                         "win": one.ravel().astype(int)})
    long.to_csv(DATA / "league_equal_one_season.csv", index=False)
    lr = longest_run(one)
    one_info = {"longest_by_team": lr.tolist(), "wins_by_team": one.sum(1).tolist(),
                "league_longest": int(lr.max())}

    out = {"random_pick_is_true_best_12teams": round(1 / 12, 4), "single_team_140games": single, "equal_league_12teams_max": league_eq,
           "streak_leader_vs_true": lv.to_dict("records"), "longest_by_true_band_sd05": band_tab.reset_index().to_dict("records"),
           "momentum_p50": mom.to_dict("records"), "no_momentum_p95_line": no_mom_p95,
           "longest_by_games_p50": by_g.to_dict("records"), "one_equal_league": one_info}
    json.dump(out, open(RES / "a827_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1チームの最長連勝の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for p, c in zip([0.4, 0.5, 0.6], [LIGHT, BLUE, INK]):
        ax.plot(hdf.longest, hdf[f"p{int(p*100)}"] * 100, "-o", ms=3.5, color=c, lw=1.6,
                label=f"本当の勝率{p}（中央値{single[str(p)]['median']:.0f}連勝）")
    ax.set_xlim(0, 22); ax.set_xticks(range(0, 23, 2))
    ax.set_xlabel("1シーズン（140試合）の最長連勝"); ax.set_ylabel("割合（%）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"勝率5割のチームでも、140試合の最長連勝は{single['0.5']['p10']:.0f}〜{single['0.5']['p90']:.0f}連勝がふつう（10〜90%の範囲）")
    save(fig, "a827_single.png", SRC + "。乱数10万シーズン")

    # 図2：実力差のあるリーグ。本当の勝率と最長連勝
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    k = 3000
    jit = np.random.default_rng(SEED + 2).uniform(-.3, .3, k)
    ax.scatter(tp05.ravel()[:k], xx05.ravel()[:k] + jit, s=5, color=BLUE, alpha=.35, lw=0)
    ax.set_xlabel("本当の勝率"); ax.set_ylabel("1シーズンの最長連勝")
    r05 = lv[lv.true_sd == 0.05].iloc[0]
    ax.set_title(f"最長連勝のチームが本当にいちばん強かったのは{r05.p_streak_leader_is_true_best*100:.0f}%（12チーム・差0.05）",
                 fontsize=12)
    ax.text(0.02, 0.95, f"本当の勝率と最長連勝の相関 {r05.corr_longest_vs_true_p:.2f}", fontsize=9.5, color=INK, transform=ax.transAxes)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    save(fig, "a827_true_vs_streak.png", SRC + f"。{k:,}チーム分を表示（点は上下に少しずらした）")

    # 図3：勢いの有無で、最長連勝の分布はどれだけ重なるか
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for d, c in zip([0.0, 0.10, 0.20], [BLUE, ORANGE, INK]):
        h = np.bincount(xs_mom[d], minlength=31)[:31] / REPS
        lab = "勢いなし" if d == 0 else f"勢いあり（勝った次は{0.5+d:.1f}、負けた次は{0.5-d:.1f}）"
        ax.plot(np.arange(31), h * 100, "-o", ms=3.5, color=c, lw=1.6, label=lab)
    ax.axvline(no_mom_p95 + .5, color=GRAY, lw=1, ls="--")
    sh0 = float(mom.loc[mom.d == 0, "share_above_no_momentum_p95"].iloc[0])
    ax.text(no_mom_p95 + .7, ax.get_ylim()[1] * .9, f"{no_mom_p95 + 1:.0f}連勝以上\n（勢いなしでは{sh0*100:.1f}%）",
            fontsize=8.5, color=GRAY)
    ax.set_xlim(0, 26); ax.set_xticks(range(0, 27, 2))
    ax.set_xlabel("1シーズン（140試合）の最長連勝（勝率0.5）"); ax.set_ylabel("割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", bbox_to_anchor=(1, .78))
    ax.set_title("勢いを入れると連勝は伸びるが、勢いなしとの分布は大きく重なる")
    save(fig, "a827_momentum.png", SRC + "。乱数10万シーズン")

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
