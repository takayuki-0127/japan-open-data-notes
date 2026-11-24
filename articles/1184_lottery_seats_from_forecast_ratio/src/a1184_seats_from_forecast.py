"""1184 申し込む人数の見込みから枠の数を決めると、見込みの外れで倍率はどれだけ振れるのか？（架空のデータ）

作成者が置いた架空の講座（同じ講座を30回続けて開く）。主催者は、回ごとに「申し込む人数の見込み」÷目標の倍率（基本3倍）で枠の数を決める。
回ごとの本当の申し込みの平均（行きたい人の多さ）は、3,000人を中心に、対数で上下する（標準偏差20%、前の回と0.5の強さでつながる）。
申し込む人数は、その平均を中心に、1人ずつ独立に申し込む数の乱数。倍率＝申し込んだ人数÷枠。
見込み方は3通り：①前の回の申し込み人数 ②前の6回の申し込み人数の平均 ③その回の本当の平均（作成者だけが知る値。人数の偶然の上下の分だけ外れる）
枠は「見込み÷目標の倍率」を1席単位（確かめでは30席単位）に丸める。7回目〜30回目の24回を数える。
(1) 見込みの外れを決めて置いた場合（−40%〜＋40%）：倍率＝目標÷（1＋外れ）（式どおり）
(2) 基本：2,000本（各24回）
(3) 確かめ：つながりの強さ3通り×上下の大きさ3通り×平均の人数2通り×目標の倍率3通り×枠の単位2通り＝108通り（各300本）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1184
SRC = "架空の講座の枠と倍率（作成者が置いた申し込みの上下からの乱数、seed 1184）"
T_ROUNDS, WARM = 30, 6
MEAN_N, SD_LOG, RHO, TARGET, UNIT = 3000, 0.2, 0.5, 3.0, 1
R_MAIN, R_GRID = 2000, 300
METHODS = {"prev": "前の回の人数", "avg6": "前の6回の平均", "true": "本当の平均（作成者だけが知る）"}
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def simulate(rng, n, mean_n=MEAN_N, sd_log=SD_LOG, rho=RHO, target=TARGET, unit=UNIT):
    u = np.zeros((n, T_ROUNDS))
    u[:, 0] = rng.normal(0, sd_log, n)
    for t in range(1, T_ROUNDS):
        u[:, t] = rho * u[:, t - 1] + np.sqrt(1 - rho ** 2) * sd_log * rng.normal(0, 1, n)
    lam = mean_n * np.exp(u)
    apps = rng.poisson(lam).astype(float)
    out = {}
    for m in METHODS:
        if m == "prev":
            f = apps[:, WARM - 1:T_ROUNDS - 1]
        elif m == "avg6":
            f = np.stack([apps[:, t - WARM:t].mean(axis=1) for t in range(WARM, T_ROUNDS)], axis=1)
        else:
            f = lam[:, WARM:]
        seats = np.maximum(unit, np.round(f / target / unit) * unit)
        a = apps[:, WARM:]
        out[m] = {"ratio": a / seats, "fc_err": f / a - 1, "seats": seats}
    return out, apps, lam


def summarize(res, target):
    x = res["ratio"].ravel()
    e = res["fc_err"].ravel()
    lo, hi = target * 2 / 3, target * 4 / 3
    return {
        "ratio_mean": r(x.mean()), "ratio_median": r(np.median(x)),
        "ratio_p10": r(np.quantile(x, 0.1)), "ratio_p90": r(np.quantile(x, 0.9)),
        "ratio_min": r(x.min()), "ratio_max": r(x.max()),
        "outside_2_3_to_4_3_pct": r(((x < lo) | (x > hi)).mean() * 100, 2),
        "over_4_3_pct": r((x > hi).mean() * 100, 2), "under_2_3_pct": r((x < lo).mean() * 100, 2),
        "under_1_pct": r((x < 1).mean() * 100, 2),
        "fc_err_abs_median_pct": r(np.median(np.abs(e)) * 100, 2),
        "fc_err_p10_pct": r(np.quantile(e, 0.1) * 100, 2), "fc_err_p90_pct": r(np.quantile(e, 0.9) * 100, 2),
        "series_range_median": r(np.median(res["ratio"].max(axis=1) - res["ratio"].min(axis=1))),
    }


def main():
    rng = np.random.default_rng(SEED)

    # (1) 外れを決めて置いた場合
    fixed = []
    for e in [-0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4]:
        seats = round(MEAN_N * (1 + e) / TARGET)
        fixed.append({"forecast_err_pct": int(round(e * 100)), "applicants": MEAN_N, "forecast": round(MEAN_N * (1 + e)),
                      "seats": seats, "ratio": r(MEAN_N / seats), "formula_ratio": r(TARGET / (1 + e))})
    fixed = pd.DataFrame(fixed)
    fixed.to_csv(RES / "fixed_error.csv", index=False)

    # (2) 基本
    out, apps, lam = simulate(rng, R_MAIN)
    base = {m: summarize(out[m], TARGET) for m in METHODS}
    base_rows = pd.DataFrame([{"method": METHODS[m], **base[m]} for m in METHODS])
    base_rows.to_csv(RES / "base_methods.csv", index=False)

    ex_i = 0
    ex = pd.DataFrame({"round": np.arange(1, T_ROUNDS + 1), "true_mean": np.round(lam[ex_i], 1),
                       "applicants": apps[ex_i].astype(int)})
    for m in METHODS:
        s = np.full(T_ROUNDS, np.nan)
        rr = np.full(T_ROUNDS, np.nan)
        s[WARM:] = out[m]["seats"][ex_i]
        rr[WARM:] = np.round(out[m]["ratio"][ex_i], 4)
        ex[f"seats_{m}"] = s
        ex[f"ratio_{m}"] = rr
    ex.to_csv(DATA / "series_example.csv", index=False)

    # (3) 確かめ 108通り
    rows = []
    for rho in [0.0, 0.5, 0.9]:
        for sd in [0.1, 0.2, 0.4]:
            for mn in [300, 3000]:
                for tg in [1.5, 3.0, 10.0]:
                    for un in [1, 30]:
                        o, _, _ = simulate(rng, R_GRID, mn, sd, rho, tg, un)
                        for m in METHODS:
                            s = summarize(o[m], tg)
                            rows.append({"rho": rho, "sd_log": sd, "mean_applicants": mn, "target": tg, "seat_unit": un,
                                         "method": METHODS[m], "ratio_p10_over_target": r(s["ratio_p10"] / tg),
                                         "ratio_p90_over_target": r(s["ratio_p90"] / tg),
                                         "ratio_mean_over_target": r(s["ratio_mean"] / tg), **s})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid
    gp = g[g.method == METHODS["prev"]]
    ga = g[g.method == METHODS["avg6"]]
    gt = g[g.method == METHODS["true"]]
    key = ["rho", "sd_log", "mean_applicants", "target", "seat_unit"]
    mg = gp.merge(ga, on=key, suffixes=("_prev", "_avg6"))
    robust = {
        "n_settings": int(len(gp)),
        "prev_outside_min": r(gp.outside_2_3_to_4_3_pct.min(), 2), "prev_outside_max": r(gp.outside_2_3_to_4_3_pct.max(), 2),
        "avg6_outside_min": r(ga.outside_2_3_to_4_3_pct.min(), 2), "avg6_outside_max": r(ga.outside_2_3_to_4_3_pct.max(), 2),
        "true_outside_max": r(gt.outside_2_3_to_4_3_pct.max(), 2),
        "true_outside_max_setting": gt.loc[gt.outside_2_3_to_4_3_pct.idxmax(), key].to_dict(),
        "prev_p90_over_target_min": r(gp.ratio_p90_over_target.min()), "prev_p90_over_target_max": r(gp.ratio_p90_over_target.max()),
        "prev_p10_over_target_min": r(gp.ratio_p10_over_target.min()), "prev_p10_over_target_max": r(gp.ratio_p10_over_target.max()),
        "prev_mean_over_target_min": r(gp.ratio_mean_over_target.min()), "prev_mean_over_target_max": r(gp.ratio_mean_over_target.max()),
        "share_mean_over_target_gt1_pct": r((g.ratio_mean_over_target > 1).mean() * 100, 2),
        "prev_better_than_avg6_pct_by_rho": {str(k): r((v.outside_2_3_to_4_3_pct_prev < v.outside_2_3_to_4_3_pct_avg6).mean() * 100, 2)
                                             for k, v in mg.groupby("rho")},
        "by_sd_prev_outside": gp.groupby("sd_log").outside_2_3_to_4_3_pct.agg(["min", "median", "max"]).round(2).reset_index().to_dict("records"),
        "by_rho_sd_prev_avg6": mg.groupby(["rho", "sd_log"])[["outside_2_3_to_4_3_pct_prev", "outside_2_3_to_4_3_pct_avg6"]].median().round(2).reset_index().to_dict("records"),
        "unit30_small_target10": gp[(gp.mean_applicants == 300) & (gp.target == 10) & (gp.seat_unit == 30)][
            ["rho", "sd_log", "ratio_p10", "ratio_p90", "outside_2_3_to_4_3_pct"]].to_dict("records"),
    }
    fx = fixed.set_index("forecast_err_pct")
    headline = {
        "fixed_minus20_ratio": r(fx.loc[-20, "ratio"]), "fixed_plus20_ratio": r(fx.loc[20, "ratio"]),
        "fixed_minus40_ratio": r(fx.loc[-40, "ratio"]), "fixed_plus40_ratio": r(fx.loc[40, "ratio"]),
        "prev_p10": base["prev"]["ratio_p10"], "prev_p90": base["prev"]["ratio_p90"],
        "prev_outside": base["prev"]["outside_2_3_to_4_3_pct"], "prev_mean": base["prev"]["ratio_mean"],
        "avg6_p10": base["avg6"]["ratio_p10"], "avg6_p90": base["avg6"]["ratio_p90"],
        "avg6_outside": base["avg6"]["outside_2_3_to_4_3_pct"],
        "true_p10": base["true"]["ratio_p10"], "true_p90": base["true"]["ratio_p90"],
        "true_outside": base["true"]["outside_2_3_to_4_3_pct"],
        "robust_prev_outside_min": robust["prev_outside_min"], "robust_prev_outside_max": robust["prev_outside_max"],
    }
    res = {"settings": {"rounds": T_ROUNDS, "warmup": WARM, "mean_applicants": MEAN_N, "sd_log": SD_LOG, "rho": RHO,
                        "target": TARGET, "seat_unit": UNIT, "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED,
                        "outside_band": [TARGET * 2 / 3, TARGET * 4 / 3]},
           "headline": headline, "base": base, "robust": robust}
    with open(RES / "a1184_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：見込みの外れを決めて置いたときの倍率（式どおり）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    xs = np.arange(len(fixed))
    cols = [ORANGE if v < 0 else (GRAY if v == 0 else BLUE) for v in fixed.forecast_err_pct]
    ax.bar(xs, fixed.ratio, 0.6, color=cols)
    for xi, v in zip(xs, fixed.ratio):
        ax.text(xi, v + 0.06, f"{v:g}", ha="center", fontsize=8.5)
    ax.axhline(TARGET, color=INK, ls="--", lw=1, label="目標の倍率 3倍")
    ax.set_xticks(xs, [f"{v:+d}%" if v else "0%" for v in fixed.forecast_err_pct])
    ax.set_xlabel("申し込む人数の見込みの外れ（見込み÷本当の人数−1）")
    ax.set_ylabel("倍率（申し込んだ人÷枠）")
    ax.set_ylim(0, fixed.ratio.max() * 1.15)
    ax.set_title("見込みが少なめに外れた側で、倍率は大きく上に振れた（式どおり）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1184_fixed_error.png", SRC)

    # 図2：基本で、目標の4/3倍を超えた回と2/3倍を下回った回の割合（見込み方ごと）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    ms = ["prev", "avg6", "true"]
    xx = np.arange(3)
    wd = 0.36
    for i, (k, c, lab) in enumerate([("over_4_3_pct", ORANGE, "4倍を超えた回"), ("under_2_3_pct", BLUE, "2倍を下回った回")]):
        v = [base[m][k] for m in ms]
        ax.bar(xx + (i - 0.5) * wd, v, wd, color=c, label=lab)
        for xi, vi in zip(xx, v):
            ax.text(xi + (i - 0.5) * wd, vi + 0.15, f"{vi:.2f}%", ha="center", fontsize=8.5)
    ax.set_xticks(xx, ["前の回の人数", "前の6回の平均", "本当の平均\n（作成者だけが知る）"])
    ax.set_xlabel("申し込む人数の見込み方")
    ax.set_ylabel("24回×2,000本のうちの割合（%）")
    ax.set_ylim(0, max(base[m]["over_4_3_pct"] for m in ms) * 1.25)
    ax.set_title("目標3倍で枠を決めると、4倍を超えた回が2倍を下回った回より多かった")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1184_base_over_under.png", SRC, y=-0.08)

    # 図3：確かめ 108通り（2〜4倍の外に出た回の割合）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    sds = [0.1, 0.2, 0.4]
    for i, (m, c) in enumerate([("prev", ORANGE), ("avg6", BLUE), ("true", GREEN)]):
        sub = g[g.method == METHODS[m]]
        for j, sd in enumerate(sds):
            v = sub[sub.sd_log == sd].outside_2_3_to_4_3_pct.values
            xx = j + (i - 1) * 0.26 + np.linspace(-0.09, 0.09, len(v))
            ax.scatter(xx, v, s=9, color=c, alpha=0.6, label=METHODS[m] if j == 0 else None)
    ax.set_xticks(range(3), ["10%", "20%", "40%"])
    ax.set_xlabel("回ごとの申し込みの平均の上下の大きさ（対数の標準偏差）")
    ax.set_ylabel("目標の2/3〜4/3倍の外に出た回（%）")
    ax.set_ylim(0, 100)
    ax.set_title("108通りの置き方：目標の倍率から大きく外れた回の割合")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1184_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
