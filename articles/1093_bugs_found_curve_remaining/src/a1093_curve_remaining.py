"""1093 バグの見つかり方の曲線から、残りのバグの数はどこまで読めるのか？（架空のデータ）

架空のアプリに作りこまれたバグ300件を作成者が置き、1件ずつ「見つかりやすさ」をガンマ分布で置く。
週ごとのテストで、バグ i がその週に見つかる確率は 1−exp(−0.1×その週のテストの量×見つかりやすさ_i)。
T週までの見つかった件数の累計に頭打ちの曲線 a×(1−exp(−b×t)) を当てはめ、a−（見つかった件数）を残りの見込みとする。
もう1つの読み方として、2つのグループが別々に探し、両方が見つけたバグの重なりから全体の件数を見込む（n1×n2÷重なり）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1093
SRC = "架空のアプリのバグと週ごとのテスト（作成者が置いたバグの数・見つかりやすさからの乱数、seed 1093）"
N_BUG = 300
RATE = 0.1          # 見つかりやすさ1・テストの量1の週に見つかる強さ
BASE = {"cv": 1.0, "weeks": 10, "effort": "一定"}
REPS = 300
B_GRID = np.exp(np.linspace(np.log(0.002), np.log(2.0), 500))
EFFORTS = ["一定", "後半3割の週は半分"]


def r(x, d=4):
    return round(float(x), d)


def effort_vec(kind, weeks):
    e = np.ones(weeks)
    if kind != "一定":
        e[int(round(weeks * 0.7)):] = 0.5
    return e


def detect(rng, reps, cv):
    if cv == 0:
        return np.ones((reps, N_BUG))
    k = 1 / cv ** 2
    return rng.gamma(k, 1 / k, (reps, N_BUG))


def simulate(rng, reps, cv, weeks, effort):
    """2グループがそれぞれ半分の量で探す。週ごとに（どちらかが）初めて見つけた件数と、各グループが見つけたか"""
    d = detect(rng, reps, cv)
    e = effort_vec(effort, weeks)
    h = RATE * d  # 1週・量1あたりの強さ
    found_week = np.full((reps, N_BUG), -1)
    g1 = np.zeros((reps, N_BUG), bool)
    g2 = np.zeros((reps, N_BUG), bool)
    for w in range(weeks):
        p_half = 1 - np.exp(-h * e[w] / 2)
        a = rng.random((reps, N_BUG)) < p_half
        b = rng.random((reps, N_BUG)) < p_half
        new = (a | b) & (found_week < 0)
        found_week[new] = w
        g1 |= a
        g2 |= b
    weekly = np.stack([(found_week == w).sum(1) for w in range(weeks)], 1)
    return d, found_week, weekly, g1, g2


def fit_curve(cum, x):
    """累計 cum（reps×T）に a×(1−exp(−b×x)) を最小二乗で当てはめる（b は格子で探し、a はそのときの最良値）"""
    g = 1 - np.exp(-B_GRID[:, None] * x[None, :])          # (B, T)
    gg = (g ** 2).sum(1)                                     # (B,)
    yg = cum @ g.T                                           # (reps, B)
    a = yg / gg
    sse = (cum ** 2).sum(1)[:, None] - yg ** 2 / gg
    j = sse.argmin(1)
    return a[np.arange(len(cum)), j], B_GRID[j]


def estimate(rng, reps, cv, weeks, effort):
    d, fw, weekly, g1, g2 = simulate(rng, reps, cv, weeks, effort)
    cum = weekly.cumsum(1).astype(float)
    found = cum[:, -1]
    remain_true = N_BUG - found
    t = np.arange(1, weeks + 1, dtype=float)
    a_cal, _ = fit_curve(cum, t)                               # 週を横軸に
    a_eff, _ = fit_curve(cum, effort_vec(effort, weeks).cumsum())  # テストの量の累計を横軸に
    n1, n2, m = g1.sum(1), g2.sum(1), (g1 & g2).sum(1)
    n_cap = n1 * n2 / np.maximum(m, 1)
    out = {}
    for key, est_total in [("curve_weeks", a_cal), ("curve_effort", a_eff), ("two_groups", n_cap)]:
        rem_est = np.maximum(est_total - found, 0)
        ratio = rem_est / remain_true
        out[key] = ratio
    return out, remain_true, found, d, fw


def summ(ratio):
    return {"median": r(np.median(ratio), 2), "p10": r(np.quantile(ratio, .1), 2), "p90": r(np.quantile(ratio, .9), 2),
            "share_within_25pct": r(np.mean(np.abs(ratio - 1) <= 0.25)), "share_below_half": r(np.mean(ratio < 0.5))}


def main():
    rng = np.random.default_rng(SEED)
    # 1) 1回分（基本の置き方）を20週まで流し、10週目までで当てはめる
    d, fw, weekly, g1, g2 = simulate(rng, 1, BASE["cv"], 20, "一定")
    cum = weekly.cumsum(1)[0]
    a10, b10 = fit_curve(cum[None, :10].astype(float), np.arange(1, 11, dtype=float))
    one = pd.DataFrame({"week": np.arange(1, 21), "found_in_week": weekly[0], "found_cum": cum,
                        "curve_fit_on_10_weeks": np.round(a10[0] * (1 - np.exp(-b10[0] * np.arange(1, 21))), 3)})
    one.to_csv(DATA / "weekly_one_draw.csv", index=False)
    pd.DataFrame({"bug_id": np.arange(1, N_BUG + 1), "findability": d[0].round(4),
                  "found_week": np.where(fw[0] >= 0, fw[0] + 1, 0)}).to_csv(DATA / "bugs_one_draw.csv", index=False)
    found10 = int(cum[9])
    left = d[0][(fw[0] < 0) | (fw[0] >= 10)]
    got = d[0][(fw[0] >= 0) & (fw[0] < 10)]
    one_res = {"found_by_week10": found10, "true_remaining_week10": N_BUG - found10,
               "curve_total": r(a10[0], 2), "curve_remaining": r(a10[0] - found10, 2),
               "found_by_week20": int(cum[19]), "curve_says_by_week20": r(one.curve_fit_on_10_weeks.iloc[19], 2),
               "findability_mean_found": r(got.mean()), "findability_mean_left": r(left.mean())}

    # 2) 基本の置き方（300回）
    est, rem, found, _, _ = estimate(np.random.default_rng(SEED * 10), REPS, **BASE)
    base = {k: summ(v) for k, v in est.items()}
    base["true_remaining_mean"] = r(rem.mean(), 2)
    base["found_mean"] = r(found.mean(), 2)

    # 3) 置き方を変えた確かめ：見つかりやすさの散らばり × 見た週 × テストの量
    rows = []
    gi = 0
    for cv in [0.0, 1.0, 2.0]:
        for weeks in [6, 10, 14]:
            for eff in EFFORTS:
                gi += 1
                e2, rem2, f2, _, _ = estimate(np.random.default_rng(SEED * 100 + gi), REPS, cv, weeks, eff)
                row = {"cv": cv, "weeks": weeks, "effort": eff, "found_mean": r(f2.mean(), 2),
                       "true_remaining_mean": r(rem2.mean(), 2)}
                for k, v in e2.items():
                    s = summ(v)
                    row.update({f"{k}_median": s["median"], f"{k}_p10": s["p10"], f"{k}_p90": s["p90"],
                                f"{k}_within_25pct": s["share_within_25pct"]})
                rows.append(row)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    het = grid[grid.cv > 0]
    out = {"n_bug": N_BUG, "rate": RATE, "base_setting": BASE, "reps": REPS, "one_draw": one_res, "base_300reps": base,
           "grid_n": int(len(grid)),
           "cv0_const_curve_weeks_median_range": [r(grid[(grid.cv == 0) & (grid.effort == "一定")].curve_weeks_median.min(), 2),
                                                  r(grid[(grid.cv == 0) & (grid.effort == "一定")].curve_weeks_median.max(), 2)],
           "cv0_two_groups_median_range": [r(grid[grid.cv == 0].two_groups_median.min(), 2), r(grid[grid.cv == 0].two_groups_median.max(), 2)],
           "het_curve_weeks_median_range": [r(het.curve_weeks_median.min(), 2), r(het.curve_weeks_median.max(), 2)],
           "het_curve_effort_median_range": [r(het.curve_effort_median.min(), 2), r(het.curve_effort_median.max(), 2)],
           "het_two_groups_median_range": [r(het.two_groups_median.min(), 2), r(het.two_groups_median.max(), 2)],
           "het_n": int(len(het)),
           "het_curve_weeks_median_below_1": int((het.curve_weeks_median < 1).sum()),
           "het_two_groups_median_below_1": int((het.two_groups_median < 1).sum()),
           "drop_effort_curve_weeks_lower_than_const": int(sum(
               grid[(grid.effort != "一定") & (grid.cv == c) & (grid.weeks == w)].curve_weeks_median.iloc[0] <
               grid[(grid.effort == "一定") & (grid.cv == c) & (grid.weeks == w)].curve_weeks_median.iloc[0]
               for c in [0.0, 1.0, 2.0] for w in [6, 10, 14])),
           "drop_effort_pairs_n": 9}
    json.dump(out, open(RES / "a1093_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pd.DataFrame([{"method": k, **v} for k, v in base.items() if isinstance(v, dict)]).to_csv(RES / "methods_base.csv", index=False)

    # 図1：1回分の累計と、10週目までで当てはめた曲線
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(one.week, one.found_cum, "o-", color=BLUE, ms=4, label="見つかったバグの累計")
    ax.plot(one.week, one.curve_fit_on_10_weeks, "--", color=ORANGE, label="10週目までで当てはめた頭打ちの曲線")
    ax.axhline(N_BUG, color=INK, lw=1); ax.text(1, N_BUG + 5, f"作りこまれたバグ {N_BUG}件（置いた値）", fontsize=9)
    ax.axvline(10.5, color=GRAY, lw=0.8, ls=":")
    ax.text(10.7, 255, "ここから先は\n当てはめに使っていない", fontsize=8, color=GRAY)
    ax.set_ylim(0, N_BUG * 1.12); ax.set_xticks(range(1, 21, 2))
    ax.set_xlabel("週"); ax.set_ylabel("件数")
    ax.legend(frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1.0, 0.08))
    ax.set_title(f"1回分：10週目で残り{one_res['true_remaining_week10']}件のところ、曲線は残り{one_res["curve_remaining"]:.2f}件と読んだ")
    save(fig, "a1093_one_draw.png", SRC)

    # 図2：読み方ごとの「見込んだ残り÷本当の残り」（10週目・テストの量一定、300回）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    g0 = grid[(grid.cv == 0) & (grid.weeks == 10) & (grid.effort == "一定")].iloc[0]
    items = [("2グループの重なり（散らばり1）", base["two_groups"]),
             ("頭打ちの曲線（散らばり1）", base["curve_weeks"]),
             ("2グループの重なり（散らばり0）", {"median": g0.two_groups_median, "p10": g0.two_groups_p10, "p90": g0.two_groups_p90}),
             ("頭打ちの曲線（散らばり0）", {"median": g0.curve_weeks_median, "p10": g0.curve_weeks_p10, "p90": g0.curve_weeks_p90})]
    for i, (lab, s_) in enumerate(items):
        col = BLUE if "散らばり1" in lab else GRAY
        ax.plot([s_["p10"], s_["p90"]], [i, i], color=LIGHT if col == BLUE else "#d9d8d3", lw=6, solid_capstyle="butt")
        ax.plot(s_["median"], i, "o", color=col, ms=8)
        ax.text(s_["p90"] + 0.03, i + 0.22, f"中央値{s_['median']:.2f}倍（10〜90%：{s_['p10']:.2f}〜{s_['p90']:.2f}倍）",
                va="center", fontsize=8)
    ax.axvline(1, color=ORANGE, lw=1.2); ax.text(1.01, 3.55, "ぴったり（1倍）", color=ORANGE, fontsize=8)
    ax.set_yticks(range(4)); ax.set_yticklabels([lab for lab, _ in items])
    ax.set_ylim(-0.6, 3.8); ax.set_xlim(0, 3.2)
    ax.set_xlabel("見込んだ残り÷本当の残り（10週目・テストの量一定、各300回）")
    ax.set_title("見つかりやすさの散らばりを置くと、2つの読み方とも残りを少なく見込む")
    save(fig, "a1093_methods.png", SRC)

    # 図3：置き方を変えた確かめ（左：散らばり、右：テストの量が後半に減るとき）
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 4.0), sharey=True)
    ax = axes[0]
    for cv, col, mk in [(0.0, GRAY, "o"), (1.0, BLUE, "s"), (2.0, ORANGE, "^")]:
        g = grid[(grid.cv == cv) & (grid.effort == "一定")]
        ax.plot(g.weeks, g.curve_weeks_median, mk + "-", color=col, label=f"散らばり{cv:.0f}・曲線")
        ax.plot(g.weeks, g.two_groups_median, mk + ":", color=col, mfc="white", label=f"散らばり{cv:.0f}・重なり")
    ax.set_title("テストの量が一定のとき", fontsize=10)
    ax.legend(frameon=False, fontsize=7, loc="center right")
    ax = axes[1]
    g = grid[(grid.cv == 0) & (grid.effort != "一定")]
    ax.plot(g.weeks, g.curve_weeks_median, "o-", color=ORANGE, label="曲線（週を横軸）")
    ax.plot(g.weeks, g.curve_effort_median, "s-", color=BLUE, label="曲線（テストの量の累計を横軸）")
    ax.plot(g.weeks, g.two_groups_median, "^:", color=GREEN, mfc="white", label="重なり")
    ax.set_title("後半3割の週のテストの量が半分\n（散らばり0）", fontsize=10)
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    for ax in axes:
        ax.axhline(1, color=INK, lw=0.8); ax.set_xticks([6, 10, 14]); ax.set_xlabel("見た週"); ax.set_ylim(0, 1.3)
    axes[0].set_ylabel("見込んだ残り÷本当の残り（中央値、300回）")
    fig.suptitle("散らばりを置くと1倍を下回り、テストの量が減ると週を横軸の曲線も下回る", fontsize=11.5, y=1.07)
    save(fig, "a1093_robust.png", SRC)


if __name__ == "__main__":
    main()
