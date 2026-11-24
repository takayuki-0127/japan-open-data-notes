"""1216 足あとやふんの数から生き物の数を見込むと、跡が残る日数の違いで何がずれるのか？（架空のデータ）

架空のC草地の種B（けもの）。本当の数を作成者が置き、1頭が1日に落とすふんの数と、
ふんが消えるまでの日数（残る日数）を置く。調べる帯（草地の5%）に残っているふんを数え、
「数えたふん÷（帯の割合×1頭1日のふん×残る日数）」で頭数を見込む。
ふんは毎日、その日の残る日数の逆数の見込みで消える（消える見込みは古さによらない）。
足あとは、雨の日に消え、雨のあとの夜の数だけたまると置く。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1216
SRC = "架空のC草地の種B（作成者が置いた頭数・ふんの数・残る日数からの乱数、seed 1216）"
rng = np.random.default_rng(SEED)

N = 40            # 本当の頭数
R = 20.0          # 1頭1日のふん
F = 0.05          # 調べる帯の割合
D_FIXED = 30.0    # 一度測って使い続ける残る日数


def season_D(t):
    """残る日数：0日目60日（乾いた時期）〜182日目15日（雨の多い時期）"""
    return 37.5 + 22.5 * np.cos(2 * np.pi * np.asarray(t, float) / 365)


def simulate_stock(rng, n_days, n_of_day, D_of_day, reps, s0=None):
    """毎日：残っていたふんのうち 1/D が消え、新しいふんが加わる。reps 回ぶん"""
    S = np.zeros(reps, int) if s0 is None else s0.copy()
    E = np.zeros(1) if s0 is None else np.array([float(s0.mean())])
    hist, ehist = [], []
    e = float(E[0])
    for t in range(n_days):
        h = 1.0 / D_of_day(t)
        S = S - rng.binomial(S, h) + rng.poisson(F * n_of_day(t) * R, reps)
        e = e * (1 - h) + F * n_of_day(t) * R
        hist.append(S.copy()); ehist.append(e)
    return np.array(hist), np.array(ehist)


def main():
    out = {}
    # ① 季節で残る日数が変わる1年（頭数は40頭のまま）。2年流して2年目を見る
    reps = 200
    H, EH = simulate_stock(rng, 730, lambda t: N, lambda t: season_D(t), reps)
    days = np.arange(365, 730, 30)
    rows = []
    for d in days:
        c = H[d]
        dd = d - 365
        est_fixed = c / (F * R * D_FIXED)
        est_now = c / (F * R * season_D(d))
        rows.append({"day_of_year": int(dd), "persist_days_now": round(float(season_D(d)), 2),
                     "count_mean": round(float(c.mean()), 1),
                     "est_fixed30_mean": round(float(est_fixed.mean()), 2),
                     "est_fixed30_ratio_pct": round(float(est_fixed.mean() / N * 100), 2),
                     "est_now_mean": round(float(est_now.mean()), 2),
                     "est_now_ratio_pct": round(float(est_now.mean() / N * 100), 2),
                     "formula_now_ratio_pct": round(float(EH[d] / (F * R * season_D(d)) / N * 100), 2),
                     "steady_fixed30_ratio_pct": round(float(season_D(d) / D_FIXED * 100), 2)})
    sea = pd.DataFrame(rows)
    sea.to_csv(RES / "season_year.csv", index=False)
    out["season"] = {"fixed30_ratio_range_pct": [float(sea.est_fixed30_ratio_pct.min()), float(sea.est_fixed30_ratio_pct.max())],
                     "now_ratio_range_pct": [float(sea.est_now_ratio_pct.min()), float(sea.est_now_ratio_pct.max())],
                     "max_abs_diff_formula_pt": round(float((sea.est_now_ratio_pct - sea.formula_now_ratio_pct).abs().max()), 2)}
    # 1回分のふんの数（毎日）
    pd.DataFrame({"day_of_year": np.arange(365), "persist_days": np.round(season_D(np.arange(365, 730)), 2),
                  "dung_count_in_strips": H[365:730, 0]}).to_csv(DATA / "dung_count_one_year.csv", index=False)

    # ② 頭数が同じ2つの草地（残る日数20日と50日）。印を付けた新しいふんで残る日数を測って直す
    plots = {"A草地（残る日数20日）": 20.0, "B草地（残る日数50日）": 50.0}
    two = []
    counts = {}
    for name, D in plots.items():
        c = rng.poisson(F * N * R * D, 2000)
        counts[name] = c
        for m in [10, 20, 50]:
            life = rng.exponential(D, size=(2000, m))
            dhat = np.minimum(life, 90).mean(1)        # 90日で見回りを終える
            est = c / (F * R * dhat)
            two.append({"plot": name, "persist_days": D, "marked": m, "count_mean": round(float(c.mean()), 1),
                        "est_fixed30_mean": round(float((c / (F * R * D_FIXED)).mean()), 2),
                        "est_measured_median": round(float(np.median(est)), 2),
                        "est_measured_p10": round(float(np.quantile(est, .1)), 2),
                        "est_measured_p90": round(float(np.quantile(est, .9)), 2),
                        "measured_days_mean": round(float(dhat.mean()), 2)})
    tw = pd.DataFrame(two)
    tw.to_csv(RES / "two_plots.csv", index=False)
    ca, cb = counts["A草地（残る日数20日）"], counts["B草地（残る日数50日）"]
    out["two_plots"] = {"count_ratio_A_over_B": round(float(ca.mean() / cb.mean()), 4), "rows": tw.to_dict("records")}

    # ③ 頭数が40頭から28頭（−30%）に減ったあと、ふんの数はいつ追いつくか
    lag = []
    for D in [15.0, 50.0]:
        s0 = rng.poisson(F * N * R * D, 500)
        Hc, _ = simulate_stock(rng, 120, lambda t: 28, lambda t: D, 500, s0)
        for k in [7, 14, 30, 60, 90, 120]:
            a = Hc[k - 1] / s0 - 1
            lag.append({"persist_days": D, "days_after": k, "apparent_change_pct": round(float(a.mean() * 100), 2),
                        "p10_pct": round(float(np.quantile(a, .1) * 100), 2), "p90_pct": round(float(np.quantile(a, .9) * 100), 2),
                        "formula_pct": round(float(-30 * (1 - (1 - 1 / D) ** k)), 2)})
    lg = pd.DataFrame(lag)
    lg.to_csv(RES / "after_decrease.csv", index=False)
    out["after_decrease"] = lg.to_dict("records")

    # ④ 足あと：雨の日（見込み0.25）に消える。1頭1晩に3つ。決まった曜日に数える
    q, tr = 0.25, 3.0
    g = rng.geometric(q, 20000) - 1                         # 雨のあとの晩の数（0なら前の晩が雨）
    c = rng.poisson(F * N * tr * g)
    ok = g > 0
    ft = []
    for meth, est in [("雨のあとの晩の数で割る", np.where(ok, c / (F * tr * np.maximum(g, 1)), np.nan)),
                      ("1晩分とみなす", c / (F * tr)),
                      ("晩の数の平均（3晩）で割る", c / (F * tr * (1 - q) / q))]:
        e = est[~np.isnan(est)] / N
        ft.append({"method": meth, "ratio_mean_pct": round(float(e.mean() * 100), 2),
                   "p10_pct": round(float(np.quantile(e, .1) * 100), 2), "p90_pct": round(float(np.quantile(e, .9) * 100), 2)})
    fp = pd.DataFrame(ft)
    fp.to_csv(RES / "footprints.csv", index=False)
    out["footprints"] = {"rain_chance": q, "share_rained_last_night_pct": round(float((~ok).mean() * 100), 2),
                         "mean_nights": round(float(g.mean()), 3), "rows": fp.to_dict("records")}

    # ⑤ 確かめ：本当の残る日数×見回りを終える日×印の数×消え方の散らばり＝48通り（各2,000回）
    grid = []
    gr = np.random.default_rng(SEED * 7)
    for D in [15.0, 30.0, 60.0, 90.0]:
        for cut in [30, 60, 120]:
            for m in [10, 30]:
                for shape in [1.0, 4.0]:
                    c = gr.poisson(F * N * R * D, 2000)       # 落ち着いた時期の数は残る日数の平均だけで決まる
                    life = gr.gamma(shape, D / shape, size=(2000, m))
                    dhat = np.minimum(life, cut).mean(1)
                    est = c / (F * R * dhat) / N
                    grid.append({"persist_days": D, "stop_check_day": cut, "marked": m, "spread": "大" if shape == 1 else "小",
                                 "ratio_mean_pct": round(float(est.mean() * 100), 2),
                                 "ratio_median_pct": round(float(np.median(est) * 100), 2),
                                 "p10_pct": round(float(np.quantile(est, .1) * 100), 2),
                                 "p90_pct": round(float(np.quantile(est, .9) * 100), 2),
                                 "fixed30_ratio_pct": round(float((c / (F * R * D_FIXED)).mean() / N * 100), 2)})
    gd = pd.DataFrame(grid)
    gd.to_csv(RES / "grid.csv", index=False)
    long_cut = gd[gd.stop_check_day >= 4 * gd.persist_days]
    out["robust"] = {"n_settings": int(len(gd)),
                     "median_range_pct": [float(gd.ratio_median_pct.min()), float(gd.ratio_median_pct.max())],
                     "median_range_cut_ge_4x_pct": [float(long_cut.ratio_median_pct.min()), float(long_cut.ratio_median_pct.max())],
                     "n_cut_ge_4x": int(len(long_cut)),
                     "median_range_cut_le_D_pct": [float(gd[gd.stop_check_day <= gd.persist_days].ratio_median_pct.min()), float(gd[gd.stop_check_day <= gd.persist_days].ratio_median_pct.max())],
                     "n_cut_le_D": int((gd.stop_check_day <= gd.persist_days).sum()),
                     "median_by_D_cut60_m30": {str(int(D)): float(gd[(gd.persist_days == D) & (gd.stop_check_day == 60) & (gd.marked == 30) & (gd.spread == "大")].ratio_median_pct.iloc[0]) for D in [15, 30, 60, 90]},
                     "p10_p90_width_m10_mean_pt": round(float((gd[gd.marked == 10].p90_pct - gd[gd.marked == 10].p10_pct).mean()), 2),
                     "p10_p90_width_m30_mean_pt": round(float((gd[gd.marked == 30].p90_pct - gd[gd.marked == 30].p10_pct).mean()), 2),
                     "fixed30_range_pct": [float(gd.fixed30_ratio_pct.min()), float(gd.fixed30_ratio_pct.max())]}
    out["headline"] = {"fixed30_season_range_pct": out["season"]["fixed30_ratio_range_pct"],
                       "now_season_range_pct": out["season"]["now_ratio_range_pct"]}
    json.dump(out, open(RES / "a1216_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：季節の1年
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(sea.day_of_year, sea.est_fixed30_mean, color=ORANGE, marker="o", ms=4, label="残る日数を30日と決めて割る")
    ax.plot(sea.day_of_year, sea.est_now_mean, color=BLUE, marker="o", ms=4, label="その日の残る日数で割る")
    ax.axhline(N, color=INK, ls="--", lw=1, label="本当の頭数（40頭のまま）")
    ax.set_ylim(0, max(sea.est_fixed30_mean.max(), sea.est_now_mean.max()) * 1.15)
    ax.set_xlabel("年のはじめからの日数（0日目は残る日数60日、182日目は15日）"); ax.set_ylabel("見込んだ頭数（200回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("頭数は同じでも、残る日数を決めて割ると季節で上下した")
    save(fig, "a1216_season.png", SRC)

    # 図2：減ったあとの追いつき
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for D, col in [(15.0, BLUE), (50.0, ORANGE)]:
        s = lg[lg.persist_days == D]
        ax.plot(s.days_after, s.apparent_change_pct, color=col, marker="o", ms=4, label=f"残る日数{int(D)}日")
    ax.axhline(-30, color=INK, ls="--", lw=1); ax.text(120, -28.8, "本当 −30%", fontsize=9, ha="right")
    ax.axhline(0, color=GRAY, lw=.8)
    ax.set_ylim(-35, 2); ax.set_xlabel("頭数が減ってからの日数"); ax.set_ylabel("ふんの数の増減（%、500回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("ふんの数は、残る日数が長いほど遅れて減った")
    save(fig, "a1216_after_decrease.png", SRC)

    # 図3：確かめ（見回りを終える日と残る日数、印30個・散らばり大）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    sub = gd[(gd.marked == 30) & (gd.spread == "大")]
    cuts = [30, 60, 120]; cols = [ORANGE, BLUE, LIGHT]
    for i, cut in enumerate(cuts):
        v = sub[sub.stop_check_day == cut].ratio_median_pct.values
        ax.bar(np.arange(4) + (i - 1) * 0.27, v, width=0.27, color=cols[i], label=f"{cut}日で見回りを終える")
    ax.axhline(100, color=INK, ls="--", lw=1)
    ax.set_xticks(range(4)); ax.set_xticklabels(["15日", "30日", "60日", "90日"])
    ax.set_xlabel("本当の残る日数（印を付けたふん30個で測る。消える日の散らばり大）"); ax.set_ylabel("見込んだ頭数÷本当の頭数（%、中央値）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("見回りを早く終えるほど、残る日数を短く測り、頭数を多く見込んだ")
    save(fig, "a1216_grid.png", SRC)
    print(json.dumps(out["season"], ensure_ascii=False), json.dumps(out["robust"], ensure_ascii=False))


if __name__ == "__main__":
    main()
