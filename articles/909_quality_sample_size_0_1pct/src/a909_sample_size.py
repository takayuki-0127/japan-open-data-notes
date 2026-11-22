"""909 不良率0.1%を確かめるには、何個検査すればよいのか？（架空のデータ）

架空の工場の部品。本当の不良率 p を作成者が置き、n 個を検査して見つかった不良の数から
「不良率は0.1%以下」と言える（95%の片側の上限が0.1%以下になる）確率を数える。
上限はクロッパー・ピアソンの方法（二項分布の式）。日ごとに不良率が上下する場合は乱数で数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import binom, beta
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 909
SRC = "架空の工場の部品の検査（作成者が乱数で作成、seed 909）"
P0 = 0.001          # 確かめたい不良率
ALPHA = 0.05        # 片側95%
rng = np.random.default_rng(SEED)


def c_max(n):
    """n 個の検査で「0.1%以下」と言える不良の数の上限（言えないときは -1）。
    上限 ≤ P0 は、P0 のときに不良が c 個以下になる確率 ≤ 5% と同じ"""
    n = np.asarray(n)
    c = binom.ppf(ALPHA, n, P0).astype(int)          # cdf ≥ 5% になる最小の c
    c = np.where(binom.cdf(c, n, P0) <= ALPHA, c, c - 1)
    return c


def upper(x, n):
    """不良 x 個・n 個検査のときの95%の片側の上限（クロッパー・ピアソン）"""
    return float(beta.ppf(1 - ALPHA, x + 1, n - x))


def p_confirm(n, p):
    c = c_max(n)
    return np.where(c >= 0, binom.cdf(c, n, p), 0.0)


def needed_n(p, target, grid):
    """「0.1%以下」と言える確率が target 以上になり、それより多いどの件数でも下回らない最小の件数"""
    pr = p_confirm(grid, p)
    bad = np.where(pr < target)[0]
    if len(bad) == len(grid):
        return None
    if len(bad) == 0:
        return int(grid[0])
    if bad[-1] == len(grid) - 1:
        return None
    return int(grid[bad[-1] + 1])


def day_rates(rng, p, cv, size):
    """日ごとの不良率。平均 p、ばらつき（変動係数）cv のガンマ分布。cv=0 は毎日 p"""
    if cv == 0:
        return np.full(size, p)
    k = 1 / cv ** 2
    return rng.gamma(k, p / k, size)


def sim_cluster(rng, p, cv, n, mode, reps=200000, days=20):
    """日ごとに不良率が上下するとき、「0.1%以下」と言える確率。
    mode='one'：n 個をすべて1日の製品から取る、'spread'：20日から同じ数ずつ取る"""
    c = int(c_max(n))
    if mode == "one":
        r = day_rates(rng, p, cv, reps)
        x = rng.binomial(n, np.minimum(r, 1))
    else:
        r = day_rates(rng, p, cv, (reps, days))
        x = rng.binomial(n // days, np.minimum(r, 1)).sum(1)
    return float((x <= c).mean())


def main():
    t0 = time.time()
    out = {"settings": {"target_rate": P0, "one_sided_conf": 1 - ALPHA, "method": "Clopper-Pearson"}}

    # 1) 不良0個なら何個で言えるか（式）
    n0 = int(np.ceil(np.log(ALPHA) / np.log(1 - P0)))
    out["zero_defect_n"] = n0
    out["rule_of_three_n"] = int(round(3 / P0))
    out["upper_if_zero"] = {str(n): round(upper(0, n), 5) for n in [1000, 2000, 3000, 5000]}
    out["p_zero_at_1000"] = {str(p): round(float((1 - p) ** 1000), 4) for p in [0.001, 0.003]}

    # 2) 件数ごとの「言える不良の数」と、本当の不良率ごとに言える確率
    ns = [1000, 2000, 3000, 5000, 10000, 20000, 50000, 100000]
    ps = [0.0002, 0.0005, 0.0008, 0.001, 0.0015, 0.002]
    rows = []
    for n in ns:
        row = {"n": n, "c_max": int(c_max(n))}
        for p in ps:
            row[f"p={p*100:.2f}%"] = round(float(p_confirm(n, p)), 4)
        rows.append(row)
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "confirm_prob_by_n.csv", index=False)
    out["confirm_prob_by_n"] = rows

    # 3) 9割・5割の確率で言える件数
    grid = np.arange(100, 2_000_001, 100)
    need = []
    for p in [0.0001, 0.0002, 0.0003, 0.0005, 0.0007, 0.0008, 0.0009]:
        need.append({"true_rate_pct": round(p * 100, 3),
                     "n_for_50pct": needed_n(p, 0.5, grid), "n_for_90pct": needed_n(p, 0.9, grid)})
    pd.DataFrame(need).to_csv(RES / "needed_n.csv", index=False)
    out["needed_n"] = need
    # 0.1%ちょうど・それより悪いとき、言えてしまう確率の上限（件数を問わず）
    big = np.array([1000, 3000, 10000, 100000, 1000000])
    out["false_confirm_at_0_1"] = {str(int(n)): round(float(p_confirm(n, 0.001)), 4) for n in big}
    out["false_confirm_max_at_0_1_grid"] = round(float(p_confirm(grid, 0.001).max()), 4)

    # 4) 日ごとに不良率が上下するとき（3,000個・10,000個）
    clus = []
    k = 0
    for n in [3000, 10000]:
        for p in [0.0005, 0.0015]:
            for cv in [0, 0.5, 1, 2]:
                r = {"n": n, "true_rate_pct": p * 100, "cv": cv}
                for mode in ["one", "spread"]:
                    k += 1
                    r[mode] = round(sim_cluster(np.random.default_rng(SEED * 100 + k), p, cv, n, mode), 4)
                r["formula_independent"] = round(float(p_confirm(n, p)), 4)
                clus.append(r)
    cl = pd.DataFrame(clus)
    cl.to_csv(RES / "day_variation.csv", index=False)
    out["day_variation"] = clus

    # 例：20日分の記録（不良率の平均0.15%、日ごとのばらつき cv=1、1日150個を検査）
    r = day_rates(rng, 0.0015, 1.0, 20)
    made = np.full(20, 5000)
    insp = np.full(20, 150)
    dfx = rng.binomial(insp, r)
    ex = pd.DataFrame({"day": np.arange(1, 21), "made": made, "true_day_rate": np.round(r, 6),
                       "inspected": insp, "defects": dfx})
    ex.to_csv(DATA / "inspection_days_example.csv", index=False)
    tot_x, tot_n = int(dfx.sum()), int(insp.sum())
    out["example_20days"] = {"inspected": tot_n, "defects": tot_x, "upper": round(upper(tot_x, tot_n), 5),
                             "c_max": int(c_max(tot_n)), "true_mean_rate": round(float(r.mean()), 6),
                             "days_with_zero": int((dfx == 0).sum())}
    out["run_note"] = "式（scipy の二項分布・ベータ分布）と乱数（日ごとの上下）"
    json.dump(out, open(RES / "a909_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：件数と「0.1%以下と言える確率」
    gn = np.unique(np.round(np.logspace(3, 6, 400) / 100) * 100).astype(int)
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    cols = {0.0002: GREEN, 0.0005: BLUE, 0.0008: LIGHT, 0.001: ORANGE, 0.0015: GRAY}
    for p, c in cols.items():
        ax.plot(gn, p_confirm(gn, p) * 100, color=c, lw=1.8, label=f"本当の不良率 {p*100:.2f}%")
    ax.set_xscale("log"); ax.set_ylim(-2, 102)
    ax.set_xlabel("検査した個数（対数の目盛り）"); ax.set_ylabel("「0.1%以下」と言える確率（%）")
    ax.axhline(90, color=GRAY, lw=.8, ls=":"); ax.text(1050, 92, "90%", color=GRAY, fontsize=8)
    ax.legend(frameon=False, fontsize=8.5, loc="center left", bbox_to_anchor=(1.0, 0.5))
    ax.set_title("本当の不良率が0.1%に近いほど、言えるまでの個数は急に増える")
    save(fig, "a909_confirm_curve.png", SRC)

    # 図2：9割の確率で言える件数
    nd = pd.DataFrame(need)
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    lab = [f"{v:.2f}%" for v in nd.true_rate_pct]
    ax.bar(lab, nd.n_for_90pct, color=BLUE)
    for i, v in enumerate(nd.n_for_90pct):
        ax.text(i, v * 1.15, f"{v:,}個", ha="center", fontsize=8.5)
    ax.set_yscale("log"); ax.set_ylim(1000, nd.n_for_90pct.max() * 4)
    ax.set_xlabel("本当の不良率"); ax.set_ylabel("9割の確率で言える個数（対数の目盛り）")
    ax.set_title("「0.1%以下」を9割の確率で言うのに要る検査の個数")
    save(fig, "a909_needed_n.png", SRC)

    # 図3：日ごとの上下と取り方（3,000個、本当0.15%）
    sub = cl[(cl.n == 3000) & (cl.true_rate_pct == 0.15)]
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    x = np.arange(len(sub)); w = .38
    ax.bar(x - w / 2, sub["one"] * 100, w, color=ORANGE, label="3,000個を1日の製品から")
    ax.bar(x + w / 2, sub["spread"] * 100, w, color=BLUE, label="20日から150個ずつ")
    for i, (a, b) in enumerate(zip(sub["one"], sub["spread"])):
        ax.text(i - w / 2, a * 100 + .6, f"{a*100:.1f}%", ha="center", fontsize=8)
        ax.text(i + w / 2, b * 100 + .6, f"{b*100:.1f}%", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"日ごとのばらつき\n（変動係数{v}）" if v else "毎日同じ\n不良率" for v in sub.cv])
    ax.set_ylabel("「0.1%以下」と言えてしまう確率（%）")
    ax.set_ylim(0, max(sub["one"].max(), sub["spread"].max()) * 100 * 1.25)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("本当は0.15%でも、1日の製品だけを調べると「0.1%以下」と出やすくなる")
    save(fig, "a909_day_variation.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
