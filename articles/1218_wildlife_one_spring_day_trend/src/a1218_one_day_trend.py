"""1218 春の1日だけ数えた数で、年ごとの数の増減を読めるのか？（架空のデータ）

架空の草地「A草地」に、渡りの途中で春に立ち寄る鳥の種A。
年ごとの本当の数（立ち寄る鳥の総数）を作成者が置き、立ち寄る数は日ごとに山の形（山の日は年ごとにずれる）、
天気で日ごとに見つかる数が上下する（続く日どうしは似る）。決めた日に数えた数で、年ごとの増減が読めるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1218
SRC = "架空の草地と鳥の数（作成者が乱数で作成、seed 1218）"
N0 = 400          # 1年目の本当の数（その春に立ち寄る総数）
Q = 0.5           # 山の日に、本当の数のうち数えられる割合
WIDTH = 10        # 立ち寄る数の山の幅（日、標準偏差）
DAYS = np.arange(-20, 21)   # 予定日を0とした日
DESIGNS = {"予定日の1日": [0],
           "3日続けて（予定日と前後1日）": [-1, 0, 1],
           "3日を2週おき（−14・0・+14日）": [-14, 0, 14],
           "5日を1週おき（−14〜+14日）": [-14, -7, 0, 7, 14]}


def simulate(rng, reps, n_years=10, trend=-0.03, sd_peak=7.0, sd_w=0.35, rho=0.6, drift=0.0):
    """数えた数（reps×年×日）と本当の数（年）を返す"""
    yrs = np.arange(n_years)
    N = N0 * (1 + trend) ** yrs
    peak = drift * yrs[None, :] + rng.normal(0, sd_peak, (reps, n_years))
    # 天気：日ごとの上下（続く日どうしは相関 rho、ばらつき sd_w の対数）
    e = np.empty((reps, n_years, len(DAYS)))
    e[..., 0] = rng.normal(0, sd_w, (reps, n_years))
    s = sd_w * np.sqrt(1 - rho ** 2)
    for k in range(1, len(DAYS)):
        e[..., k] = rho * e[..., k - 1] + rng.normal(0, s, (reps, n_years))
    g = np.exp(-(DAYS[None, None, :] - peak[..., None]) ** 2 / (2 * WIDTH ** 2))
    lam = N[None, :, None] * Q * g * np.exp(e - sd_w ** 2 / 2)
    return rng.poisson(lam), N


def design_counts(counts, days):
    idx = [int(np.where(DAYS == d)[0][0]) for d in days]
    return counts[..., idx].mean(-1)


def slope_change(c):
    """各回の log(数+0.5) を年に直線で当てはめ、9年（=年数−1）での変化の割合を返す"""
    n = c.shape[1]
    x = np.arange(n) - (n - 1) / 2
    y = np.log(c + 0.5)
    b = (y * x).sum(1) / (x ** 2).sum()
    return np.exp(b * (n - 1)) - 1


def summarize(c, true_dir=-1):
    ch = slope_change(c)
    d = np.diff(c, axis=1)
    pair = (d < 0).mean() if true_dir < 0 else (d > 0).mean()
    return {"pair_correct": float(pair), "pair_wrong": float((d > 0).mean() if true_dir < 0 else (d < 0).mean()),
            "p_slope_neg": float((ch < 0).mean()), "p_slope_pos": float((ch > 0).mean()),
            "change_median": float(np.median(ch)), "change_p10": float(np.quantile(ch, .1)),
            "change_p90": float(np.quantile(ch, .9)), "p_change_lt_m10": float((ch < -0.10).mean()),
            "p_change_gt_p10": float((ch > 0.10).mean())}


def r(x, k=4):
    return round(float(x), k)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    REPS = 4000
    counts, N = simulate(rng, REPS)
    true_change = float(N[-1] / N[0] - 1)

    # 1) 基本：4つの数え方
    rows, sd_log = [], {}
    for name, days in DESIGNS.items():
        c = design_counts(counts, days)
        s = summarize(c)
        # 同じ年の中のぶれ：1年目の数の log の標準偏差（回をまたいで）
        sdl = float(np.log(c[:, 0] + 0.5).std())
        q10, q50, q90 = np.quantile(c[:, 0], [.1, .5, .9])
        rows.append({"design": name, "n_days": len(days), "sd_log_count_year1": r(sdl),
                     "year1_p10_over_median": r(q10 / q50), "year1_p90_over_median": r(q90 / q50),
                     **{k: r(v) for k, v in s.items()}})
        sd_log[name] = sdl
    base = pd.DataFrame(rows)
    base.to_csv(RES / "designs_base.csv", index=False)

    # 近似の式：前の年より減ったと出る割合 ≈ Φ(−ln(1+trend) / (√2・σ))（σ は1日の数の log のぶれ）
    from math import erf, sqrt, log
    phi = lambda z: 0.5 * (1 + erf(z / sqrt(2)))
    approx = {k: r(phi(-log(0.97) / (sqrt(2) * v))) for k, v in sd_log.items()}

    # 2) 何年続ければ：5・10・20年（1日・5日）
    years_rows = []
    for ny in [5, 10, 20]:
        cc, NN = simulate(np.random.default_rng(SEED * 10 + ny), 3000, n_years=ny)
        for name in ["予定日の1日", "5日を1週おき（−14〜+14日）"]:
            ch = slope_change(design_counts(cc, DESIGNS[name]))
            years_rows.append({"n_years": ny, "design": name, "true_change": r(NN[-1] / NN[0] - 1),
                               "p_slope_neg": r((ch < 0).mean()), "change_p10": r(np.quantile(ch, .1)),
                               "change_median": r(np.median(ch)), "change_p90": r(np.quantile(ch, .9))})
    by_years = pd.DataFrame(years_rows)
    by_years.to_csv(RES / "by_years.csv", index=False)

    # 3) 山の日が年ごとに早まる（本当の数は横ばい）
    drift_rows = []
    for dr in [0.0, -0.5, -1.0, 1.0]:
        cc, _ = simulate(np.random.default_rng(SEED * 100 + int(dr * 10) + 50), 3000, trend=0.0, drift=dr)
        for name, days in DESIGNS.items():
            ch = slope_change(design_counts(cc, days))
            drift_rows.append({"drift_days_per_year": dr, "design": name, "true_change": 0.0,
                               "change_median": r(np.median(ch)), "change_p10": r(np.quantile(ch, .1)),
                               "change_p90": r(np.quantile(ch, .9)), "p_change_lt_m10": r((ch < -0.10).mean())})
    drift = pd.DataFrame(drift_rows)
    drift.to_csv(RES / "drift.csv", index=False)
    # 式：山が9日早まったとき、予定日の数の期待値は exp(−81/(2·10²)) 倍（年ごとのずれ sd_peak を除いたとき）
    drift_formula_1day = r(np.exp(-(9.0 ** 2) / (2 * WIDTH ** 2)) - 1)

    # 4) 確かめ：山の日のずれ×天気のぶれ×本当の増減（27通り）
    grid_rows = []
    gi = 0
    for sp in [0.0, 7.0, 14.0]:
        for sw in [0.2, 0.35, 0.6]:
            for tr in [-0.01, -0.03, -0.05]:
                gi += 1
                cc, NN = simulate(np.random.default_rng(SEED * 1000 + gi), 1500, trend=tr, sd_peak=sp, sd_w=sw)
                row = {"sd_peak_days": sp, "sd_weather_log": sw, "trend_per_year": tr,
                       "true_change": r(NN[-1] / NN[0] - 1)}
                for key, name in [("d1", "予定日の1日"), ("d5", "5日を1週おき（−14〜+14日）")]:
                    s = summarize(design_counts(cc, DESIGNS[name]))
                    row[f"{key}_pair_correct"] = r(s["pair_correct"])
                    row[f"{key}_p_slope_neg"] = r(s["p_slope_neg"])
                    row[f"{key}_change_median"] = r(s["change_median"])
                grid_rows.append(row)
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False)

    # data：1回分の例（年ごとの本当の数と4つの数え方の数）
    ex = pd.DataFrame({"year": np.arange(1, 11), "true_number": np.round(N, 2)})
    for i, (name, days) in enumerate(DESIGNS.items()):
        ex[f"design{i+1}_mean_count"] = np.round(design_counts(counts[:1], days)[0], 2)
    ex.to_csv(DATA / "example_10years.csv", index=False)
    pd.DataFrame({"design": [f"design{i+1}" for i in range(4)], "name": list(DESIGNS.keys()),
                  "days": [" ".join(map(str, d)) for d in DESIGNS.values()]}).to_csv(DATA / "designs.csv", index=False)

    g = grid
    out = {"setting": {"N0": N0, "Q": Q, "width_days": WIDTH, "trend_per_year": -0.03, "sd_peak_days": 7,
                       "sd_weather_log": 0.35, "weather_rho": 0.6, "reps": REPS, "years": 10},
           "true_change_9y": r(true_change),
           "designs_base": base.to_dict("records"),
           "pair_correct_approx_formula": approx,
           "by_years": by_years.to_dict("records"),
           "drift": drift.to_dict("records"), "drift_formula_1day_9days_earlier": drift_formula_1day,
           "grid_range": {"d1_pair_correct": [r(g.d1_pair_correct.min()), r(g.d1_pair_correct.max())],
                          "d5_pair_correct": [r(g.d5_pair_correct.min()), r(g.d5_pair_correct.max())],
                          "d1_p_slope_neg": [r(g.d1_p_slope_neg.min()), r(g.d1_p_slope_neg.max())],
                          "d5_p_slope_neg": [r(g.d5_p_slope_neg.min()), r(g.d5_p_slope_neg.max())],
                          "n_d5_ge_d1_slope": int((g.d5_p_slope_neg >= g.d1_p_slope_neg).sum()),
                          "n_d1_slope_ge_0_9": int((g.d1_p_slope_neg >= 0.9).sum()),
                          "n_d5_slope_ge_0_9": int((g.d5_p_slope_neg >= 0.9).sum())},
           "grid_range_trend_m3": {k: [r(g[g.trend_per_year == -0.03][k].min()), r(g[g.trend_per_year == -0.03][k].max())]
                                   for k in ["d1_pair_correct", "d5_pair_correct", "d1_p_slope_neg", "d5_p_slope_neg"]}}

    # 図1：例の10年
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    yrs = ex.year
    ax.plot(yrs, ex.true_number / ex.true_number.mean(), color=INK, lw=2, label="本当の数")
    ax.plot(yrs, ex.design1_mean_count / ex.design1_mean_count.mean(), color=ORANGE, marker="o", lw=1.2,
            label="予定日の1日に数えた数")
    ax.plot(yrs, ex.design4_mean_count / ex.design4_mean_count.mean(), color=BLUE, marker="s", lw=1.2,
            label="5日を1週おきに数えた数の平均")
    ax.set_xticks(yrs); ax.set_xlabel("年"); ax.set_ylabel("10年の平均を1とした値")
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("例の1回：本当は毎年3%ずつ減るが、1日の数は年ごとに上下する")
    save(fig, "a1218_example.png", SRC)

    # 図2：4つの数え方で、減る向きが読めた割合
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    yy = np.arange(len(base))
    ax.barh(yy + 0.2, base.pair_correct * 100, height=0.38, color=LIGHT, label="前の年より減ったと出た年の割合")
    ax.barh(yy - 0.2, base.p_slope_neg * 100, height=0.38, color=BLUE, label="10年の当てはめが減る向きだった回の割合")
    for i, (a, b) in enumerate(zip(base.pair_correct, base.p_slope_neg)):
        ax.text(a * 100 + 1, i + 0.2, f"{a*100:.2f}%", va="center", fontsize=8.5)
        ax.text(b * 100 + 1, i - 0.2, f"{b*100:.2f}%", va="center", fontsize=8.5)
    ax.set_yticks(yy); ax.set_yticklabels(base.design); ax.invert_yaxis()
    ax.set_xlim(0, 110); ax.set_xticks(range(0, 101, 20)); ax.set_xlabel("%（4,000回）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.4, -0.16), ncol=2)
    ax.set_title("本当は毎年3%減：1日だけでは、前の年との比べはほぼ半々")
    save(fig, "a1218_designs.png", SRC, y=-0.1)

    # 図3：山の日が年1日早まる（本当は横ばい）
    d1 = drift[drift.drift_days_per_year == -1.0].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    yy = np.arange(len(d1))
    ax.barh(yy, d1.change_median * 100, color=[ORANGE, LIGHT, BLUE, BLUE])
    for i, v in enumerate(d1.change_median * 100):
        ax.text(v - 1, i, f"{v:.2f}%", va="center", ha="right", fontsize=9)
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(yy); ax.set_yticklabels(d1.design); ax.invert_yaxis()
    ax.set_xlim(-60, 5); ax.set_xlabel("10年の当てはめから読んだ9年の変化（%、3,000回の中央値。本当は0%）")
    ax.set_title("本当は横ばいで、山の日が毎年1日早まると、1日の数は減って見える")
    save(fig, "a1218_drift.png", SRC)

    json.dump(out, open(RES / "a1218_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ["true_change_9y", "designs_base", "pair_correct_approx_formula", "grid_range"]},
                     ensure_ascii=False, indent=1))
    print(by_years.to_string()); print(drift.to_string()); print("formula", drift_formula_1day)
    print(f"{time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
