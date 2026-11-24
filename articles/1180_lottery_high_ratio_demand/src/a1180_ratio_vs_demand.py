"""1180 倍率の高い回は、申し込みたい人の多い回だと読んでよいのか？（架空のデータ）

架空の文化教室の特別講座を1年に200回開く。回ごとに「本当に行きたい人の数」を作成者が置き、
枠（会場の席の数）は、主催者が人気の見込みに合わせて決める（合わせる強さ c を置く）。
申し込む人は、行きたい人のうち告知が届いて申し込んだ人（申し込む割合を回ごとに置く）。
倍率＝申し込んだ人数÷枠。倍率の高い順・申し込みの多い順が、本当に行きたい人の多い順をどれだけ当てるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1180
SRC = "架空の講座200回の抽選（作成者が置いた行きたい人の数・枠・申し込む割合からの乱数、seed 1180）"
N_ROUND = 200
TOP = 20
SD_DEMAND = 0.6   # 行きたい人の数（対数）のばらつき
MED_DEMAND = 300
MED_SEAT = 100
REPS = 1000
REPS_GRID = 300


def make(rng, c=0.7, sd_seat=0.4, sd_q=0.5, n=N_ROUND):
    """1年分200回。c：枠を人気の見込みに合わせる強さ、sd_seat：枠の決め方のぶれ（対数）、sd_q：申し込む割合のぶれ（オッズの対数での標準偏差）"""
    z = rng.normal(0, 1, n)
    demand = np.round(MED_DEMAND * np.exp(SD_DEMAND * z)).astype(int)
    seat = np.clip(np.round(MED_SEAT * np.exp(c * SD_DEMAND * z + rng.normal(0, sd_seat, n))), 10, None).astype(int)
    q = 1 / (1 + np.exp(-(np.log(0.6 / 0.4) + rng.normal(0, sd_q, n))))
    apply_ = rng.binomial(demand, q)
    return demand, seat, apply_


def top_overlap(score, truth, k=TOP):
    a = set(np.argsort(-score, kind="stable")[:k]); b = set(np.argsort(-truth, kind="stable")[:k])
    return len(a & b) / k


def corr_log(x, y):
    return float(np.corrcoef(np.log(np.maximum(x, 0.5)), np.log(np.maximum(y, 0.5)))[0, 1])


def evaluate(rng, reps, **kw):
    r = {"ov_ratio": [], "ov_apply": [], "ov_seat_small": [], "corr_ratio": [], "corr_apply": [],
         "top_ratio_demand_med_rel": [], "top_ratio_small_seat_share": []}
    for _ in range(reps):
        d, s, a = make(rng, **kw)
        ratio = a / s
        r["ov_ratio"].append(top_overlap(ratio, d))
        r["ov_apply"].append(top_overlap(a.astype(float), d))
        r["ov_seat_small"].append(top_overlap(-s.astype(float), d))
        r["corr_ratio"].append(corr_log(ratio, d))
        r["corr_apply"].append(corr_log(a, d))
        top = np.argsort(-ratio, kind="stable")[:TOP]
        r["top_ratio_demand_med_rel"].append(np.median(d[top]) / np.median(d))
        r["top_ratio_small_seat_share"].append(np.mean(s[top] <= np.quantile(s, 1 / 3)))
    return {k: float(np.mean(v)) for k, v in r.items()}


def corr_formula(c, sd_seat, sd_q):
    """対数の倍率と対数の行きたい人の相関の近似（申し込む割合のぶれは、割合0.6の近くで対数に直して0.4倍）"""
    sd_lq = sd_q * 0.4
    return (1 - c) * SD_DEMAND / np.sqrt(((1 - c) * SD_DEMAND) ** 2 + sd_seat ** 2 + sd_lq ** 2)


def main():
    rng = np.random.default_rng(SEED)
    d, s, a = make(rng)
    ex = pd.DataFrame({"round": np.arange(1, N_ROUND + 1), "demand_true": d, "seats": s, "applicants": a,
                       "ratio": np.round(a / s, 3)})
    ex.to_csv(DATA / "one_year.csv", index=False)
    one = {"ratio_median": round(float(np.median(a / s)), 3), "ratio_max": round(float((a / s).max()), 3),
           "rounds_ratio_below1": int((a / s < 1).sum()),
           "top20_ratio_overlap_pct": round(top_overlap(a / s, d) * 100, 1),
           "top20_apply_overlap_pct": round(top_overlap(a.astype(float), d) * 100, 1)}

    base = evaluate(np.random.default_rng(SEED + 1), REPS)
    base_r = {"top20_overlap_ratio_pct": round(base["ov_ratio"] * 100, 2),
              "top20_overlap_applicants_pct": round(base["ov_apply"] * 100, 2),
              "top20_overlap_small_seats_pct": round(base["ov_seat_small"] * 100, 2),
              "top20_overlap_random_pct": round(TOP / N_ROUND * 100, 2),
              "corr_log_ratio_demand": round(base["corr_ratio"], 3),
              "corr_log_ratio_demand_formula": round(float(corr_formula(0.7, 0.4, 0.5)), 3),
              "corr_log_applicants_demand": round(base["corr_apply"], 3),
              "top20_ratio_demand_median_rel": round(base["top_ratio_demand_med_rel"], 3),
              "top20_ratio_small_seat_share_pct": round(base["top_ratio_small_seat_share"] * 100, 2)}

    rows = []
    for c in [0.0, 0.5, 0.9]:
        for ss in [0.2, 0.4, 0.8]:
            for sq in [0.25, 0.5, 1.0]:
                e = evaluate(np.random.default_rng(SEED * 10 + int(c * 10) * 100 + int(ss * 10) * 10 + int(sq * 4)), REPS_GRID,
                             c=c, sd_seat=ss, sd_q=sq)
                rows.append({"match_c": c, "seat_sd": ss, "apply_sd": sq,
                             "top20_overlap_ratio_pct": round(e["ov_ratio"] * 100, 2),
                             "top20_overlap_applicants_pct": round(e["ov_apply"] * 100, 2),
                             "corr_log_ratio_demand": round(e["corr_ratio"], 3),
                             "corr_formula": round(float(corr_formula(c, ss, sq)), 3),
                             "corr_log_applicants_demand": round(e["corr_apply"], 3),
                             "top20_ratio_small_seat_share_pct": round(e["top_ratio_small_seat_share"] * 100, 2)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    gs = {"ratio_overlap_range": [float(grid.top20_overlap_ratio_pct.min()), float(grid.top20_overlap_ratio_pct.max())],
          "applicants_overlap_range": [float(grid.top20_overlap_applicants_pct.min()), float(grid.top20_overlap_applicants_pct.max())],
          "applicants_beats_ratio_count": int((grid.top20_overlap_applicants_pct > grid.top20_overlap_ratio_pct).sum()),
          "corr_vs_formula_max_abs_diff": round(float((grid.corr_log_ratio_demand - grid.corr_formula).abs().max()), 3),
          "by_c": {str(c): {"ratio_overlap_range": [float(g.top20_overlap_ratio_pct.min()), float(g.top20_overlap_ratio_pct.max())],
                            "applicants_overlap_range": [float(g.top20_overlap_applicants_pct.min()), float(g.top20_overlap_applicants_pct.max())],
                            "corr_ratio_range": [float(g.corr_log_ratio_demand.min()), float(g.corr_log_ratio_demand.max())]}
                   for c, g in grid.groupby("match_c")}}
    out = {"setup": {"rounds": N_ROUND, "top": TOP, "demand_median": MED_DEMAND, "demand_log_sd": SD_DEMAND,
                     "seat_median": MED_SEAT, "match_c_base": 0.7, "seat_sd_base": 0.4, "apply_rate_center": 0.6,
                     "apply_sd_base": 0.5, "reps": REPS, "reps_grid": REPS_GRID},
           "one_year": one, "base": base_r, "grid_summary": gs}
    json.dump(out, open(RES / "a1180_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1年分の散布（倍率と本当に行きたい人の数）
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    sc = ax.scatter(d, a / s, c=np.log(s), cmap="Blues", s=22, edgecolor=GRAY, lw=.3)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("本当に行きたい人の数（人、対数の目盛り）"); ax.set_ylabel("倍率（申し込み÷枠、対数の目盛り）")
    from matplotlib.ticker import ScalarFormatter, NullFormatter
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(ScalarFormatter()); axis.set_minor_formatter(NullFormatter())
    ax.set_yticks([0.5, 1, 2, 4], ["0.5", "1", "2", "4"]); ax.set_xticks([100, 300, 1000], ["100", "300", "1,000"])
    cb = fig.colorbar(sc, ax=ax); cb.set_label("枠の大きさ（濃いほど大きい、対数）"); cb.set_ticks([])
    ax.set_title(f"1年分200回：倍率と行きたい人の数（上位{TOP}回の重なり{one['top20_ratio_overlap_pct']:.0f}%）")
    save(fig, "a1180_scatter.png", SRC + "。基本の置き方（枠を人気に合わせる強さ0.7）の1年分")

    # 図2：上位20回の重なり（基本、1,000年の平均）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    labels = ["倍率の高い順", "申し込みの多い順", "枠の小さい順", "でたらめに選ぶ"]
    vals = [base_r["top20_overlap_ratio_pct"], base_r["top20_overlap_applicants_pct"],
            base_r["top20_overlap_small_seats_pct"], base_r["top20_overlap_random_pct"]]
    ax.barh(labels[::-1], vals[::-1], color=[GRAY, LIGHT, BLUE, ORANGE])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 1, i, f"{v:.2f}%", va="center", fontsize=9.5)
    ax.set_xlim(0, 100); ax.set_xlabel(f"本当に行きたい人の上位{TOP}回に入っていた割合（%）")
    ax.set_title(f"上位{TOP}回を何で選ぶか（基本の置き方、1,000年の平均）")
    save(fig, "a1180_overlap.png", SRC)

    # 図3：枠を合わせる強さ別（27通り）の重なり
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for c, col, mk in [(0.0, LIGHT, "o"), (0.5, BLUE, "s"), (0.9, INK, "^")]:
        g = grid[grid.match_c == c]
        ax.scatter(g.top20_overlap_applicants_pct, g.top20_overlap_ratio_pct, color=col, marker=mk, s=40,
                   edgecolor=INK, lw=.4, label=f"枠を人気に合わせる強さ {c}")
    ax.plot([0, 100], [0, 100], color=GRAY, lw=1, ls="--")
    ax.text(25, 4, "点線より下：倍率の高い順のほうが当たらない", color=GRAY, fontsize=8.5)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xlabel(f"申し込みの多い順の上位{TOP}回の当たり（%）"); ax.set_ylabel(f"倍率の高い順の上位{TOP}回の当たり（%）")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    ax.set_title("27通りの置き方：倍率の順は申し込みの順より当たらない")
    save(fig, "a1180_robust.png", SRC + "。各300年の平均")


if __name__ == "__main__":
    main()
