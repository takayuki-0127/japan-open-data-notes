"""914 全数検査なら、不良はゼロになるのか？（架空のデータ）

架空の工場で、月に100,000個の部品（樹脂のカバー）を作り、全部を目で見る外観検査にかける。
不良の入る割合（基本 0.5%）と、不良1個ごとの「見つけやすさ」（1回の検査で見つかる確率）を作成者が置く。
見つけやすさは平均 s（基本 90%）のベータ分布で、ばらつきの大きさを集まり具合 κ で変える（κ＝∞ は全部同じ 90%）。
検査を1〜3回くり返したとき、見逃されて出ていく不良の数と、その読み方を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 914
SRC = "架空の工場の外観検査（作成者が乱数で作成、seed 914）"
N_MONTH = 100_000
KAPPAS = [None, 20, 4, 1]          # None は全部同じ見つけやすさ
KLAB = {None: "全部同じ（κ＝∞）", 20: "少し違う（κ＝20）", 4: "違う（κ＝4）", 1: "大きく違う（κ＝1）"}


def visibility(rng, k, s, kappa):
    if kappa is None:
        return np.full(k, s)
    return rng.beta(s * kappa, (1 - s) * kappa, k)


def run_months(rng, months, p, s, kappa, passes=3):
    """months か月分。月ごとの不良の数・各回の検査のあとに残った数・2回目で見つかった数"""
    rows = []
    for _ in range(months):
        k = rng.binomial(N_MONTH, p)
        v = visibility(rng, k, s, kappa)
        alive = np.ones(k, dtype=bool)
        rec = {"defects": k}
        for j in range(1, passes + 1):
            found = alive & (rng.random(k) < v)
            rec[f"found_{j}"] = int(found.sum())
            alive &= ~found
            rec[f"left_{j}"] = int(alive.sum())
        rows.append(rec)
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    out = {"setting": {"made_per_month": N_MONTH}}
    P0, S0 = 0.005, 0.90

    # 1) 検査の回数ごとに、出ていく不良（月、1,000か月の平均）。見つけやすさのばらつき4通り
    rows = []
    keep = {}
    for i, kappa in enumerate(KAPPAS):
        df = run_months(np.random.default_rng(SEED + i), 1000, P0, S0, kappa)
        keep[kappa] = df
        for j in [1, 2, 3]:
            left = df[f"left_{j}"]
            rows.append({"kappa": "inf" if kappa is None else kappa, "label": KLAB[kappa], "passes": j,
                         "defects_mean": round(float(df.defects.mean()), 1),
                         "escape_mean": round(float(left.mean()), 2),
                         "escape_ppm": round(float(left.mean() / N_MONTH * 1e6), 1),
                         "escape_formula_indep": round(float(df.defects.mean() * (1 - S0) ** j), 2),
                         "ratio_to_indep": round(float(left.mean() / (df.defects.mean() * (1 - S0) ** j)), 2),
                         "found_rate_of_left_before": round(float(df[f"found_{j}"].sum() / (df.defects.sum() if j == 1 else df[f"left_{j-1}"].sum())), 3),
                         "share_month_zero_escape": round(float((left == 0).mean()), 3)})
    esc = pd.DataFrame(rows)
    esc.to_csv(RES / "escape_by_passes.csv", index=False)
    out["escape_by_passes"] = rows

    # 2) 2回目の検査で見つかった数から、1回目のあとに残っていた数と2回目のあとに残る数を読む
    #    素直な読み方：2回目も「見本で測った90%」で見つかるとして、残り＝見つかった数÷0.9、2回目のあと＝その10%
    rows = []
    for kappa in KAPPAS:
        df = keep[kappa]
        est_left1 = df.found_2 / S0
        est_left2 = est_left1 * (1 - S0)
        rows.append({"kappa": "inf" if kappa is None else kappa, "label": KLAB[kappa],
                     "true_left_after_1": round(float(df.left_1.mean()), 1),
                     "found_in_2nd": round(float(df.found_2.mean()), 1),
                     "naive_left_after_1": round(float(est_left1.mean()), 1),
                     "true_left_after_2": round(float(df.left_2.mean()), 2),
                     "naive_left_after_2": round(float(est_left2.mean()), 2),
                     "true_over_naive_after_2": round(float(df.left_2.mean() / est_left2.mean()), 2)})
    naive = pd.DataFrame(rows)
    naive.to_csv(RES / "naive_estimate.csv", index=False)
    out["naive_estimate"] = rows

    # 3) 「ゼロの月」がどれだけあるか：不良の入る割合×見つけやすさの平均（κ＝4、1回・2回）
    rows = []
    case = 0
    for p in [0.0005, 0.001, 0.005, 0.02]:
        for s in [0.9, 0.99]:
            for kappa in [None, 4]:
                case += 1
                df = run_months(np.random.default_rng(SEED * 10 + case),
                                1000, p, s, kappa, passes=2)
                rows.append({"p_pct": p * 100, "s": s, "kappa": "inf" if kappa is None else kappa,
                             "defects_mean": round(float(df.defects.mean()), 1),
                             "escape1_mean": round(float(df.left_1.mean()), 2),
                             "zero_month_1pass": round(float((df.left_1 == 0).mean()), 3),
                             "escape2_mean": round(float(df.left_2.mean()), 3),
                             "zero_month_2pass": round(float((df.left_2 == 0).mean()), 3)})
    zero = pd.DataFrame(rows)
    zero.to_csv(RES / "zero_escape_months.csv", index=False)
    out["zero_escape_months"] = rows

    # 4) 確かめ：見つけやすさの平均 s（80・90・95・99%）× ばらつき κ（∞・20・4・1）の16通り
    rows = []
    for s in [0.8, 0.9, 0.95, 0.99]:
        for kappa in KAPPAS:
            g = np.random.default_rng(SEED * 100 + int(s * 100) + (0 if kappa is None else kappa))
            v = visibility(g, 400_000, s, kappa)        # 不良40万個ぶんの見つけやすさ
            e = {j: float(np.mean((1 - v) ** j)) for j in [1, 2, 3]}
            naive2 = float(np.mean(v * (1 - v))) / s * (1 - s)  # 2回目で見つかる割合÷s×(1−s)
            rows.append({"s": s, "kappa": "inf" if kappa is None else kappa,
                         "escape_rate_1": round(e[1], 5), "escape_rate_2": round(e[2], 5), "escape_rate_3": round(e[3], 6),
                         "ratio2_to_indep": round(e[2] / (1 - s) ** 2, 2), "ratio3_to_indep": round(e[3] / (1 - s) ** 3, 2),
                         "true_over_naive_2": round(e[2] / naive2, 2),
                         "second_pass_found_rate": round(1 - e[2] / e[1], 3)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "robust_s_kappa.csv", index=False)
    out["robust_s_kappa"] = rows
    g2 = grid[grid.kappa != "inf"]
    out["robust_range"] = {"ratio2_min": float(g2.ratio2_to_indep.min()), "ratio2_max": float(g2.ratio2_to_indep.max()),
                           "ratio3_min": float(g2.ratio3_to_indep.min()), "ratio3_max": float(g2.ratio3_to_indep.max()),
                           "true_over_naive_2_min": float(g2.true_over_naive_2.min()),
                           "true_over_naive_2_max": float(g2.true_over_naive_2.max()),
                           "second_pass_found_min": float(g2.second_pass_found_rate.min()),
                           "second_pass_found_max": float(g2.second_pass_found_rate.max()),
                           "inf_ratio2": sorted(set(grid[grid.kappa == "inf"].ratio2_to_indep.tolist()))}

    # data：基本（κ＝4）の1か月分の不良1個ずつ
    g = np.random.default_rng(SEED * 1000)
    k = g.binomial(N_MONTH, P0)
    v = visibility(g, k, S0, 4)
    alive = np.ones(k, dtype=bool)
    rec = {"defect_id": np.arange(1, k + 1), "visibility": np.round(v, 4)}
    for j in [1, 2, 3]:
        f = alive & (g.random(k) < v)
        rec[f"found_in_pass{j}"] = f.astype(int)
        alive &= ~f
    rec["escaped_after_3"] = alive.astype(int)
    one = pd.DataFrame(rec)
    one.to_csv(DATA / "one_month_defects_kappa4.csv", index=False)
    out["data_one_month"] = {"defects": int(k), "found_1": int(one.found_in_pass1.sum()), "found_2": int(one.found_in_pass2.sum()),
                             "found_3": int(one.found_in_pass3.sum()), "escaped_after_3": int(one.escaped_after_3.sum()),
                             "share_visibility_below_50": round(float((v < .5).mean()), 3)}

    # 見つけやすさの分布：全部の不良と、1回目・2回目のあとに残った不良（κ＝4、大きく作る）
    g = np.random.default_rng(SEED * 2000)
    v = visibility(g, 400_000, S0, 4)
    a1 = g.random(v.size) >= v
    a2 = a1 & (g.random(v.size) >= v)
    out["visibility_mean"] = {"all": round(float(v.mean()), 3), "left_after_1": round(float(v[a1].mean()), 3),
                              "left_after_2": round(float(v[a2].mean()), 3)}
    json.dump(out, open(RES / "a914_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：検査の回数と出ていく不良（ppm、対数の目盛り）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for kappa, c in zip(KAPPAS, [GRAY, LIGHT, BLUE, ORANGE]):
        s = esc[esc.label == KLAB[kappa]]
        ax.plot(s.passes, s.escape_ppm, marker="o", color=c, lw=1.8, label=KLAB[kappa])
        ax.text(3.08, s.escape_ppm.iloc[-1], f"{s.escape_ppm.iloc[-1]:.1f}", va="center", fontsize=8.5, color=c)
    ax.set_yscale("log"); ax.set_yticks([5, 10, 20, 50, 100, 200, 500]); ax.set_yticklabels(["5", "10", "20", "50", "100", "200", "500"])
    ax.minorticks_off(); ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["1回", "2回", "3回"]); ax.set_xlim(.8, 3.35)
    ax.set_xlabel("全数検査をくり返した回数"); ax.set_ylabel("出ていく不良（100万個あたり、対数の目盛り）")
    ax.legend(frameon=False, fontsize=8.5, title="不良ごとの見つけやすさ", title_fontsize=8.5)
    ax.set_title("見つけやすさが不良ごとに違うと、くり返しても出ていく不良が減りにくい")
    save(fig, "a914_escape_passes.png", SRC)

    # 図2：見つけやすさの分布（全部・1回目のあとに残った・2回目のあとに残った）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    bins = np.linspace(0, 1, 41)
    for arr, c, lab in [(v, GRAY, f"全部の不良（平均{v.mean()*100:.0f}%）"),
                        (v[a1], BLUE, f"1回目で見逃された不良（平均{v[a1].mean()*100:.0f}%）"),
                        (v[a2], ORANGE, f"2回目でも見逃された不良（平均{v[a2].mean()*100:.0f}%）")]:
        ax.hist(arr, bins=bins, density=True, histtype="step", lw=1.8, color=c, label=lab)
    ax.set_xlabel("1回の検査で見つかる確率（不良ごと）"); ax.set_yticks([]); ax.set_ylabel("不良の多さ（形を比べる）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("見逃されて残るのは、もともと見つけにくい不良（κ＝4・平均90%）")
    save(fig, "a914_visibility.png", SRC)

    # 図3：素直な読み方に対して、本当に2回目のあとに残る不良は何倍か（16通り）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ss = [0.8, 0.9, 0.95, 0.99]
    w = .2
    for i, (kappa, c) in enumerate(zip(KAPPAS, [GRAY, LIGHT, BLUE, ORANGE])):
        kk = "inf" if kappa is None else kappa
        vals = [float(grid[(grid.s == s) & (grid.kappa == kk)].true_over_naive_2.iloc[0]) for s in ss]
        ax.bar(np.arange(4) + (i - 1.5) * w, vals, w, color=c, label=KLAB[kappa])
        for x, val in zip(np.arange(4) + (i - 1.5) * w, vals):
            ax.text(x, val * 1.08, f"{val:g}", ha="center", fontsize=7.5)
    ax.axhline(1, color=INK, lw=.7)
    ax.set_yscale("log"); ax.set_ylim(.8, 250)
    ax.set_yticks([1, 2, 5, 10, 20, 50, 100]); ax.set_yticklabels(["1", "2", "5", "10", "20", "50", "100"])
    ax.minorticks_off()
    ax.set_xticks(range(4)); ax.set_xticklabels([f"平均{int(s*100)}%" for s in ss])
    ax.set_xlabel("見本で測った見つけやすさの平均"); ax.set_ylabel("本当の残り÷素直に読んだ残り（倍、対数）")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
    ax.set_title("2回目の見つかった数から残りを読むと、見つけにくさが違うほど少なく読む")
    save(fig, "a914_naive.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:7000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
