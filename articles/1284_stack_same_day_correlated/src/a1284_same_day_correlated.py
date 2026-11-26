"""1284 同じ日に作った部品どうしで寸法のずれがそろうとき、関係なしと見て二乗で足した幅は、実際の幅よりどれだけ狭く出るのか？（架空のデータ）

架空の棚。5種類の部品（板・枠など）を重ねて高さが決まる。部品ごとの寸法のずれは平均0、標準偏差0.10mm。
そのうち割合 rho の分は「作った日」で決まり、同じ日に作った部品は種類が違ってもそろって同じ向きにずれる
（湿り気・機械の設定などを想定した作成者の置き方）。残りは1個ずつでたらめ。
1つの工場の記録：60日、1日に棚20台、記録として種類ごとに1日10個を測る。
見込み：記録の標準偏差を部品ごとに出し、二乗で足して平方根をとる（関係なしと見た見込み）。
  ① 60日分の記録（600個）から  ② 最初の1日分の記録（10個）から
実際：組んだ1,200台の棚の高さの標準偏差と、見込みの±3倍の外に出た台数の割合。
棚の部品は、同じ日に作ったものを使う（k=1）か、直近 k 日のどれかの日のものをまぜて使う。
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1284
SRC = "架空の棚の部品の寸法のシミュレーション（作成者が乱数で作成、seed 1284）"
SIG = 0.10
BASE = {"n": 5, "rho": 0.3, "k": 1, "shared": 5}
DAYS, PER_DAY, REC = 60, 20, 10
R_BASE, R_GRID, R_SWEEP = 500, 200, 200


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def two_side(z):
    return 2 * (1 - ncdf(z))


def factory(rng, n, rho, k, shared):
    """1工場分。shared 種類の部品だけが日のずれを分け合う（残りは日のずれなし・同じ標準偏差）"""
    sd_day = SIG * math.sqrt(rho)
    sd_in = SIG * math.sqrt(1 - rho)
    day = rng.normal(0, sd_day, DAYS)
    has = np.zeros(n, bool)
    has[:shared] = True
    sd_in_i = np.where(has, sd_in, SIG)
    # 記録（種類ごとに1日 REC 個）
    rec = rng.normal(0, 1, (DAYS, REC, n)) * sd_in_i + np.where(has, day[:, None, None], 0.0)
    # 棚
    t = np.repeat(np.arange(DAYS), PER_DAY)
    u = rng.integers(0, k, (t.size, n))
    dd = (t[:, None] - u) % DAYS
    parts = rng.normal(0, 1, (t.size, n)) * sd_in_i + np.where(has, day[dd], 0.0)
    h = parts.sum(1)
    s_all = rec.reshape(-1, n).std(0, ddof=1)
    s_day1 = rec[0].std(0, ddof=1)
    rss_all = math.sqrt((s_all ** 2).sum())
    rss_day1 = math.sqrt((s_day1 ** 2).sum())
    worst = 3 * s_all.sum()
    sd_h = h.std(ddof=1)
    return {"sd_actual": sd_h, "rss_all": rss_all, "rss_day1": rss_day1, "worst_all": worst,
            "out_rss_all": float((np.abs(h) > 3 * rss_all).mean()),
            "out_rss_day1": float((np.abs(h) > 3 * rss_day1).mean()),
            "out_worst": float((np.abs(h) > worst).mean()),
            "corr_rec": float(np.corrcoef(rec.reshape(-1, n)[:, 0], rec.reshape(-1, n)[:, 1])[0, 1])}, h, rec


def run(rng, R, n, rho, k, shared):
    rows = [factory(rng, n, rho, k, shared)[0] for _ in range(R)]
    df = pd.DataFrame(rows)
    df["ratio_all"] = df.sd_actual / df.rss_all
    df["ratio_day1"] = df.sd_actual / df.rss_day1
    return df


def formula_ratio(n, rho, k, shared):
    # 共有する種類どうしの組の数 × 同じ日の確率（k 日まぜると 1/k）
    pairs = shared * (shared - 1)
    p_same = 1.0 / k
    return math.sqrt((n + pairs * rho * p_same) / n)


def summ(df):
    q = lambda c, p: round(float(df[c].quantile(p)), 4)
    return {"ratio_all_median": q("ratio_all", 0.5), "ratio_all_p05": q("ratio_all", 0.05), "ratio_all_p95": q("ratio_all", 0.95),
            "ratio_day1_median": q("ratio_day1", 0.5), "ratio_day1_p05": q("ratio_day1", 0.05), "ratio_day1_p95": q("ratio_day1", 0.95),
            "out_rss_all_mean_pct": round(100 * df.out_rss_all.mean(), 3), "out_rss_all_p05_pct": round(100 * df.out_rss_all.quantile(0.05), 3),
            "out_rss_all_p95_pct": round(100 * df.out_rss_all.quantile(0.95), 3),
            "out_rss_day1_mean_pct": round(100 * df.out_rss_day1.mean(), 3),
            "out_worst_mean_pct": round(100 * df.out_worst.mean(), 3),
            "share_ratio_all_over_1_1": round(100 * (df.ratio_all > 1.1).mean(), 1)}


def main():
    rng = np.random.default_rng(SEED)
    n, rho, k, sh = BASE["n"], BASE["rho"], BASE["k"], BASE["shared"]

    # 例の1工場
    ex, h_ex, rec_ex = factory(rng, n, rho, k, sh)
    pd.DataFrame({"day": np.repeat(np.arange(1, DAYS + 1), PER_DAY), "height_dev_mm": h_ex.round(4)}).to_csv(DATA / "example_shelves.csv", index=False)
    recdf = pd.DataFrame(rec_ex.reshape(-1, n).round(4), columns=[f"part{i + 1}_dev_mm" for i in range(n)])
    recdf.insert(0, "day", np.repeat(np.arange(1, DAYS + 1), REC))
    recdf.to_csv(DATA / "example_records.csv", index=False)

    base = run(rng, R_BASE, n, rho, k, sh)
    fr = formula_ratio(n, rho, k, sh)
    base_s = summ(base)

    # 関係の強さを0〜1で動かす（n=5、k=1）
    sweep = []
    for r in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        df = run(rng, R_SWEEP, n, r, 1, n)
        s = summ(df)
        sweep.append({"rho": r, "formula_ratio": round(formula_ratio(n, r, 1, n), 4),
                      "formula_out_pct": round(100 * two_side(3 / formula_ratio(n, r, 1, n)), 3), **s})
    sweep = pd.DataFrame(sweep)
    sweep.to_csv(RES / "sweep_rho.csv", index=False)

    # 一部の種類だけがそろう（n=5、rho=0.3）
    sub = []
    for s_ in [5, 4, 3, 2, 1]:
        df = run(rng, R_GRID, n, rho, 1, s_)
        sub.append({"shared_parts": s_, "formula_ratio": round(formula_ratio(n, rho, 1, s_), 4), **summ(df)})
    sub = pd.DataFrame(sub)
    sub.to_csv(RES / "shared_parts.csv", index=False)

    # 27通り
    grid = []
    for r in [0.1, 0.3, 0.6]:
        for nn in [3, 5, 8]:
            for kk in [1, 2, 5]:
                df = run(rng, R_GRID, nn, r, kk, nn)
                f = formula_ratio(nn, r, kk, nn)
                grid.append({"rho": r, "n_parts": nn, "mix_days": kk, "formula_ratio": round(f, 4),
                             "formula_out_pct": round(100 * two_side(3 / f), 3), **summ(df)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    main_json = {
        "setting": {"n_parts": n, "sd_each_mm": SIG, "rho_day_share": rho, "days": DAYS, "shelves_per_day": PER_DAY,
                    "records_per_part_per_day": REC, "factories": R_BASE, "seed": SEED},
        "example_factory": {**{k_: round(v, 4) for k_, v in ex.items()},
                            "out_rss_all_pct": round(100 * ex["out_rss_all"], 3)},
        "base": {**base_s, "formula_ratio": round(fr, 4), "formula_out_pct": round(100 * two_side(3 / fr), 3),
                 "independent_out_pct": round(100 * two_side(3), 3),
                 "worst_over_rss": round(math.sqrt(n), 4),
                 "sd_actual_median_mm": round(float(base.sd_actual.median()), 4),
                 "rss_all_median_mm": round(float(base.rss_all.median()), 4),
                 "rss_day1_median_mm": round(float(base.rss_day1.median()), 4),
                 "corr_rec_median": round(float(base.corr_rec.median()), 4),
                 "rss_over_actual_median": round(float((base.rss_all / base.sd_actual).median()), 4),
                 "rss_day1_over_actual_median": round(float((base.rss_day1 / base.sd_actual).median()), 4)},
        "grid_range": {"ratio_all_median_min": float(grid.ratio_all_median.min()), "ratio_all_median_max": float(grid.ratio_all_median.max()),
                       "out_rss_all_mean_min_pct": float(grid.out_rss_all_mean_pct.min()), "out_rss_all_mean_max_pct": float(grid.out_rss_all_mean_pct.max()),
                       "ratio_day1_median_min": float(grid.ratio_day1_median.min()), "ratio_day1_median_max": float(grid.ratio_day1_median.max()),
                       "max_abs_diff_median_vs_formula": round(float((grid.ratio_all_median - grid.formula_ratio).abs().max()), 4)},
    }
    with open(RES / "a1284_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：関係の強さと、実際÷見込み
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(sweep.rho, sweep.formula_ratio, color=GRAY, lw=1.5, label="式の値")
    ax.errorbar(sweep.rho, sweep.ratio_all_median, yerr=[sweep.ratio_all_median - sweep.ratio_all_p05, sweep.ratio_all_p95 - sweep.ratio_all_median],
                fmt="o", color=BLUE, ms=5, capsize=3, label="60日分の記録から見込んだとき（200工場の中央値、5〜95%）")
    sw7 = sweep[sweep.rho <= 0.7]
    ax.plot(sw7.rho, sw7.ratio_day1_median, "s", color=ORANGE, ms=5, label="1日分の記録から見込んだとき（中央値、0.7まで）")
    ax.axhline(math.sqrt(n), color=INK, ls="--", lw=1)
    ax.text(0.02, math.sqrt(n) - 0.15, f"実際の±3倍が、許容差をそのまま足した幅に届く線（{round(math.sqrt(n), 4):g}倍）", fontsize=9)
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_xlabel("寸法のずれのうち、作った日で決まる割合")
    ax.set_ylabel("実際の棚の標準偏差 ÷ 二乗で足した見込み")
    ax.set_ylim(0, 4.0)
    ax.set_title("同じ日の部品のずれがそろうほど、見込みより広くなる（部品5つ）")
    ax.legend(fontsize=8.5, loc="upper left", bbox_to_anchor=(0, 0.9), frameon=False)
    save(fig, "a1284_ratio_by_rho.png", SRC)
    # 図2：例の1工場の棚の高さ
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.hist(h_ex, bins=50, color=LIGHT, edgecolor="white")
    for v in [-3 * ex["rss_all"], 3 * ex["rss_all"]]:
        ax.axvline(v, color=ORANGE, lw=1.5)
    for v in [-ex["worst_all"], ex["worst_all"]]:
        ax.axvline(v, color=INK, ls="--", lw=1)
    ax.text(3 * ex["rss_all"], ax.get_ylim()[1] * 0.92, " 二乗の足し算の±3倍", color=ORANGE, fontsize=9)
    ax.text(ex["worst_all"], ax.get_ylim()[1] * 0.8, "そのまま足した幅 ", color=INK, fontsize=9, ha="right")
    ax.set_xlabel("棚の高さの、決めた寸法からのずれ（mm）")
    ax.set_ylabel("台数")
    ax.set_title(f"例の1工場（1,200台）：二乗の足し算の幅の外に{round(100 * ex['out_rss_all'], 3):g}%")
    save(fig, "a1284_example_hist.png", SRC)
    # 図3：27通りのうち部品5つ、外れの割合
    g5 = grid[grid.n_parts == 5]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    xs = np.arange(3)
    for j, kk in enumerate([1, 2, 5]):
        gg = g5[g5.mix_days == kk]
        ax.bar(xs + (j - 1) * 0.26, gg.out_rss_all_mean_pct, 0.26, color=[BLUE, GREEN, GRAY][j],
               label=["同じ日の部品で組む", "2日分をまぜて組む", "5日分をまぜて組む"][j])
        for x, v in zip(xs + (j - 1) * 0.26, gg.out_rss_all_mean_pct):
            ax.text(x, v + 0.1, f"{v:g}", ha="center", fontsize=8)
    ax.axhline(100 * two_side(3), color=ORANGE, ls="--", lw=1, label="関係なしと見た見込み（0.27%）")
    ax.set_xticks(xs, ["0.1", "0.3", "0.6"])
    ax.set_xlabel("寸法のずれのうち、作った日で決まる割合")
    ax.set_ylabel("見込みの±3倍の外に出た棚（%）")
    ax.set_ylim(0, None)
    ax.set_title("部品5つ：二乗の足し算の幅の外に出た棚の割合（200工場の平均）")
    ax.legend(fontsize=9, frameon=False, loc="upper left", bbox_to_anchor=(0, 0.95))
    save(fig, "a1284_grid_out.png", SRC)
    print(json.dumps(main_json, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
