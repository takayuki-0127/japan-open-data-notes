"""1105 どの条件か知っている人が仕上がりを見ると、差はどれだけ大きく出るのか？（架空のデータ）

架空の印刷工房が、いつもの乾かし方（A）と新しい乾かし方（B）で刷った紙を、採点員が見た目で1〜10点に採点する
（にじみが目立たないほど高い点）。紙ごとの本当の見た目の良さ、B の本当の良くなり方、採点員の見るぶれを作成者が置く。
どちらの乾かし方の紙か知っている採点員は、B の紙に「期待のぶん」（採点員ごとに違う）を足して採点すると置く。
知らない採点員（紙に番号だけを付けて渡す）には、期待のぶんが入らない。
B−A の平均点の差と、「差がある」と判定される割合を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.special import ndtr
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1105
SRC = "架空の印刷工房の試し刷りと採点（作成者が置いた見た目の良さと採点のぶれからの乱数、seed 1105）"
BASE = {"delta": 0.3, "sheet_sd": 1.0, "grader_noise": 0.8, "bias_mean": 0.4, "bias_sd": 0.3, "n_sheets": 30,
        "n_graders": 1, "center": 5.5}
REPS = 4000
GRID_REPS = 1500
Z = 1.959964


def r(x, d=4):
    return round(float(x), d)


def score(latent):
    return np.clip(np.round(latent), 1, 10)


def experiment(rng, reps, delta, bias_mean, bias_sd, n, graders, known, sheet_sd=1.0, noise=0.8):
    """1回の試し刷り：A・B を n 枚ずつ。graders 人が全部の紙を採点し、紙ごとに平均してから B−A の差を出す"""
    qa = sheet_sd * rng.standard_normal((reps, n))
    qb = delta + sheet_sd * rng.standard_normal((reps, n))
    b = (bias_mean + bias_sd * rng.standard_normal((reps, graders))) if known else np.zeros((reps, graders))
    sa = score(BASE["center"] + qa[:, :, None] + noise * rng.standard_normal((reps, n, graders))).mean(2)
    sb = score(BASE["center"] + qb[:, :, None] + b[:, None, :] + noise * rng.standard_normal((reps, n, graders))).mean(2)
    diff = sb.mean(1) - sa.mean(1)
    se = np.sqrt(sa.var(1, ddof=1) / n + sb.var(1, ddof=1) / n)
    return diff, se, sa, sb


def true_diff(rng, delta, sheet_sd=1.0, noise=0.8, m=400000):
    """期待のぶんが入らない採点の、点の差の期待（点に丸めて1〜10に収めたあとの物差し）"""
    qa = sheet_sd * rng.standard_normal(m); qb = delta + sheet_sd * rng.standard_normal(m)
    e1, e2 = noise * rng.standard_normal(m), noise * rng.standard_normal(m)
    return float(score(BASE["center"] + qb + e2).mean() - score(BASE["center"] + qa + e1).mean())


def summ(diff, se, td):
    sig = diff > Z * se
    return {"diff_median": r(np.median(diff), 3), "diff_p10": r(np.quantile(diff, .1), 3), "diff_p90": r(np.quantile(diff, .9), 3),
            "ratio_to_true": (None if abs(td) < 1e-9 else r(np.median(diff) / td, 3)),
            "share_B_better_judged": r(sig.mean() * 100, 2), "share_A_better_judged": r((diff < -Z * se).mean() * 100, 2),
            "se_median": r(np.median(se), 3)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    td_cache = {d: r(true_diff(np.random.default_rng(SEED + int(d * 100)), d), 4) for d in [0.0, 0.3, 0.6]}
    td_cache[0.0] = 0.0          # 0 は作りどおり（A と B が同じ）

    designs = [("知っている1人", True, 1), ("知らない1人", False, 1), ("知っている3人の平均", True, 3), ("知らない3人の平均", False, 3)]
    rows = []
    cache = {}
    for delta in [0.3, 0.0]:
        for name, known, g in designs:
            d, se, _, _ = experiment(rng, REPS, delta, BASE["bias_mean"], BASE["bias_sd"], BASE["n_sheets"], g, known)
            cache[(delta, BASE["n_sheets"], name)] = (d, se)
            rows.append({"true_effect": delta, "true_diff_points": td_cache[delta], "design": name, **summ(d, se, td_cache[delta])})
    main_tab = pd.DataFrame(rows)
    main_tab.to_csv(RES / "by_design.csv", index=False)

    # 紙の枚数を増やすと（本当の差0、知っている1人・知らない1人・知っている3人）
    nrows = []
    for n in [10, 30, 100, 300]:
        for name, known, g in [designs[0], designs[1], designs[2]]:
            if (0.0, n, name) in cache:                 # 30枚ずつは上の表と同じ4,000回を使う
                d, se = cache[(0.0, n, name)]
            else:
                d, se, _, _ = experiment(rng, REPS, 0.0, BASE["bias_mean"], BASE["bias_sd"], n, g, known)
            sem = float(np.median(se))
            bm, bv = (BASE["bias_mean"], BASE["bias_sd"] ** 2 / g) if known else (0.0, 0.0)
            formula = 1 - ndtr((Z * sem - bm) / np.sqrt(sem ** 2 + bv))      # 正規分布で近似した式
            nrows.append({"n_sheets": n, "design": name, "share_B_better_judged": r((d > Z * se).mean() * 100, 2),
                          "share_formula": r(formula * 100, 2), "diff_median": r(np.median(d), 3)})
    by_n = pd.DataFrame(nrows)
    by_n.to_csv(RES / "by_sheets_null.csv", index=False)

    # 確かめ：置き方を変える（3×4×2×3×2＝144通り）
    grid = []
    gi = 0
    for delta in [0.0, 0.3, 0.6]:
        for bm in [0.0, 0.2, 0.4, 0.8]:
            for bs in [0.0, 0.3]:
                for n in [10, 30, 100]:
                    for g in [1, 3]:
                        gr = np.random.default_rng(SEED * 1000 + gi); gi += 1
                        dk, sek, _, _ = experiment(gr, GRID_REPS, delta, bm, bs, n, g, True)
                        db, seb, _, _ = experiment(gr, GRID_REPS, delta, bm, bs, n, g, False)
                        td = td_cache[delta]
                        grid.append({"true_effect": delta, "bias_mean": bm, "bias_sd": bs, "n_sheets": n, "graders": g,
                                     "true_diff_points": td,
                                     "known_diff_median": r(np.median(dk), 3), "blind_diff_median": r(np.median(db), 3),
                                     "known_minus_blind": r(np.median(dk) - np.median(db), 3),
                                     "known_ratio": (None if td == 0 else r(np.median(dk) / td, 3)),
                                     "known_B_better": r((dk > Z * sek).mean() * 100, 2), "blind_B_better": r((db > Z * seb).mean() * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g0 = grid[grid.true_effect == 0]
    gpos = grid[(grid.true_effect > 0) & (grid.bias_mean > 0)]
    gsum = {
        "n": int(len(grid)),
        "null_known_B_better_range_biased": [r(g0[g0.bias_mean > 0].known_B_better.min(), 2), r(g0[g0.bias_mean > 0].known_B_better.max(), 2)],
        "null_blind_B_better_range": [r(g0.blind_B_better.min(), 2), r(g0.blind_B_better.max(), 2)],
        "null_known_B_better_bias0_sd0_range": [r(g0[(g0.bias_mean == 0) & (g0.bias_sd == 0)].known_B_better.min(), 2),
                                                 r(g0[(g0.bias_mean == 0) & (g0.bias_sd == 0)].known_B_better.max(), 2)],
        "null_known_B_better_bias0_sd03_1grader": g0[(g0.bias_mean == 0) & (g0.bias_sd == 0.3) & (g0.graders == 1)][["n_sheets", "known_B_better"]].to_dict("records"),
        "null_known_B_better_bias0_sd03_3graders": g0[(g0.bias_mean == 0) & (g0.bias_sd == 0.3) & (g0.graders == 3)][["n_sheets", "known_B_better"]].to_dict("records"),
        "known_ratio_range_biased": [r(gpos.known_ratio.min(), 3), r(gpos.known_ratio.max(), 3)],
        "known_minus_blind_vs_bias": {str(bm): [r(grid[grid.bias_mean == bm].known_minus_blind.min(), 3), r(grid[grid.bias_mean == bm].known_minus_blind.max(), 3)]
                                       for bm in [0.0, 0.2, 0.4, 0.8]},
        "null_biased_known_rises_with_n": int(sum(
            (g0[(g0.bias_mean == bm) & (g0.bias_sd == bs) & (g0.graders == g)].sort_values("n_sheets").known_B_better.diff().dropna() > 0).all()
            for bm in [0.2, 0.4, 0.8] for bs in [0.0, 0.3] for g in [1, 3])),
        "null_biased_cases": 12,
        "known_minus_blind_minus_bias_maxabs": r((grid.known_minus_blind - grid.bias_mean).abs().max(), 3),
        "rows_null_biased": int(len(g0[g0.bias_mean > 0])), "rows_null": int(len(g0)), "rows_pos_biased": int(len(gpos)),
    }

    # data：1回分の採点（本当の差0.3、知っている1人と知らない1人、紙30枚ずつ）
    g1 = np.random.default_rng(SEED + 1)
    qa = g1.standard_normal(30); qb = 0.3 + g1.standard_normal(30)
    bk = BASE["bias_mean"] + BASE["bias_sd"] * g1.standard_normal()
    recs = []
    for i in range(30):
        for cond, q, bb in [("A", qa[i], 0.0), ("B", qb[i], bk)]:
            recs.append({"sheet": f"{cond}{i+1:02d}", "method": cond, "true_look": round(float(q), 4),
                         "score_known": int(score(BASE["center"] + q + bb + 0.8 * g1.standard_normal())),
                         "score_blind": int(score(BASE["center"] + q + 0.8 * g1.standard_normal()))})
    one = pd.DataFrame(recs)
    one.to_csv(DATA / "scores_one_trial.csv", index=False)
    one_sum = {"known_grader_bias": r(bk, 3),
               "known_diff": r(one[one.method == "B"].score_known.mean() - one[one.method == "A"].score_known.mean(), 3),
               "blind_diff": r(one[one.method == "B"].score_blind.mean() - one[one.method == "A"].score_blind.mean(), 3),
               "true_look_diff": r(qb.mean() - qa.mean(), 3)}

    formula_known = {"known_diff_formula": r(td_cache[0.3] + BASE["bias_mean"], 4),
                     "known_ratio_formula": r((td_cache[0.3] + BASE["bias_mean"]) / td_cache[0.3], 3)}
    out = {"base": BASE, "reps": REPS, "true_diff_points": {str(k): v for k, v in td_cache.items()}, "formula": formula_known,
           "by_design": main_tab.to_dict("records"), "by_sheets_null": by_n.to_dict("records"),
           "grid_summary": gsum, "one_trial": one_sum}
    json.dump(out, open(RES / "a1105_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：本当の差0.3と0のときの、採点の差（中央値と10〜90%）
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.0), sharey=True)
    for ax, delta in zip(axs, [0.3, 0.0]):
        t = main_tab[main_tab.true_effect == delta].reset_index(drop=True)
        cols = [ORANGE, BLUE, ORANGE, BLUE]
        for i, row in t.iterrows():
            ax.plot([row.diff_p10, row.diff_p90], [i, i], color=cols[i], lw=3, alpha=.45)
            ax.plot(row.diff_median, i, "o", color=cols[i])
            ax.text(row.diff_p90 + 0.03, i, f"{row.diff_median:.3f}", va="center", fontsize=8)
        ax.axvline(td_cache[delta], color=INK, lw=1, ls="--")
        ax.axvline(0, color=GRAY, lw=0.8)
        ax.set_yticks(range(len(t))); ax.set_yticklabels(t.design, fontsize=9)
        ax.set_xlim(-0.6, 1.6)
        ax.set_title(f"本当の差 {td_cache[delta]:.4f}点（点線）", fontsize=10)
        ax.set_xlabel("B−A の平均点の差（点）")
    axs[0].invert_yaxis()
    fig.suptitle("知っている採点員の差は、期待のぶん（平均0.4点）だけ大きく出た（紙30枚ずつ、4,000回）", fontsize=11.5, y=1.03)
    save(fig, "a1105_diff.png", SRC, y=-0.03)

    # 図2：本当の差0で「B のほうが良い」と判定された割合（紙の枚数ごと）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ns = [10, 30, 100, 300]
    for name, c, mk in [("知っている1人", ORANGE, "o"), ("知っている3人の平均", "#b4441a", "s"), ("知らない1人", BLUE, "^")]:
        v = by_n[by_n.design == name].share_B_better_judged.values
        ax.plot(range(4), v, marker=mk, color=c, label=name)
        dy = {"知っている1人": -6, "知っている3人の平均": 3, "知らない1人": 2.5}[name]
        for i, y in enumerate(v):
            ax.text(i + 0.06, y + dy, f"{y:.2f}", fontsize=8, color=c)
    ax.axhline(2.5, color=GRAY, lw=1, ls="--"); ax.text(2.5, 10, "点線：偶然だけなら2.5%", fontsize=8, color=GRAY, ha="center")
    ax.set_xticks(range(4)); ax.set_xticklabels([f"{n}枚ずつ" for n in ns])
    ax.set_ylim(0, 105); ax.set_ylabel("「B のほうが良い」と判定された割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="center left")
    ax.set_title("本当の差が0でも、知っている採点員では紙を増やすほど「差あり」が増えた")
    save(fig, "a1105_null_by_sheets.png", SRC)

    # 図3：置き方を変えた144通りで、知っている−知らないの差の中央値と、置いた期待のぶん
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    jit = {0.0: -0.03, 0.3: 0.0, 0.6: 0.03}
    for delta, c in [(0.0, GRAY), (0.3, BLUE), (0.6, ORANGE)]:
        gg = grid[grid.true_effect == delta]
        ax.scatter(gg.bias_mean + jit[delta], gg.known_minus_blind, s=14, color=c, alpha=.7, label=f"本当の見た目の差 {delta}")
    ax.plot([0, 0.8], [0, 0.8], color=INK, lw=1, ls="--")
    ax.text(0.62, 0.72, "置いた期待のぶんと同じ", fontsize=8, color=INK, ha="right")
    ax.set_xlabel("置いた期待のぶん（採点員の平均、点）"); ax.set_ylabel("知っている−知らない（差の中央値、点）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_xticks([0, 0.2, 0.4, 0.8])
    ax.set_title("差の大きく出た分は、置いた期待のぶんとほぼ同じ（144通り）")
    save(fig, "a1105_robust.png", SRC, y=-0.06)

    out["run_sec"] = r(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
