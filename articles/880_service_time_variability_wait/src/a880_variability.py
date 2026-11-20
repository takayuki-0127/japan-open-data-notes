"""880 平均の処理時間が同じでも、ばらつきが大きいと待ちは？（架空のデータ）

架空の店の受付窓口（窓口は1つ）。1人の用件の時間は、どの置き方でも平均4分にそろえ、
ばらつきだけを変える（全員4分・小さい・中くらい・1割が長い用件・20人に1人がとても長い用件）。
来る人の数も同じにして、待ち時間（来てから自分の番が始まるまで）がどれだけ変わるかを数える。
基本は「1日8時間受け付け、朝は誰も並んでいない」を2,000日。
確かめとして、混み具合（利用率）0.6・0.75・0.9、来方（でたらめ・予約に近い・まとまって来る）を変え、
ずっと開け続けたときの平均を、待ち行列の式（ポラチェック・ヒンチンの式）の値と比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 880
SRC = "架空の店の受付窓口（作成者が乱数で作成、seed 880）"
MEAN = 4.0
OPEN_MIN = 480
PURPLE = "#7b5ea7"

# 用件の時間の置き方（どれも平均4分）。混合は、短い用件と長い用件それぞれの中でも少し散らばる（変動係数0.2）
DISTS = [
    {"key": "const", "name": "全員4分", "kind": "const"},
    {"key": "g05", "name": "ばらつき小", "kind": "gamma", "cv": 0.5},
    {"key": "exp", "name": "ばらつき中", "kind": "gamma", "cv": 1.0},
    {"key": "mix10", "name": "1割が17.5分", "kind": "mix", "p_long": 0.10, "short": 2.5, "long": 17.5},
    {"key": "mix5", "name": "20人に1人が42分", "kind": "mix", "p_long": 0.05, "short": 2.0, "long": 42.0},
]
COLORS = [GRAY, LIGHT, BLUE, ORANGE, PURPLE]
INNER_CV = 0.2


def gamma(rng, size, mean, cv):
    k = 1 / cv ** 2
    return rng.gamma(k, mean / k, size)


def draw_service(rng, d, size):
    if d["kind"] == "const":
        return np.full(size, MEAN), np.zeros(size, bool)
    if d["kind"] == "gamma":
        return gamma(rng, size, MEAN, d["cv"]), np.zeros(size, bool)
    is_long = rng.random(size) < d["p_long"]
    s = np.where(is_long, gamma(rng, size, d["long"], INNER_CV), gamma(rng, size, d["short"], INNER_CV))
    return s, is_long


def theory_cv(d):
    if d["kind"] == "const":
        return 0.0
    if d["kind"] == "gamma":
        return d["cv"]
    m2 = (d["p_long"] * d["long"] ** 2 + (1 - d["p_long"]) * d["short"] ** 2) * (1 + INNER_CV ** 2)
    return float(np.sqrt(m2 - MEAN ** 2) / MEAN)


ARRIVALS = [("でたらめに来る", 1.0), ("予約に近い（間隔のばらつき小）", 0.5), ("まとまって来る（間隔のばらつき大）", 1.5)]


def gaps(rng, size, mean_gap, cv_a):
    if cv_a == 1.0:
        return rng.exponential(mean_gap, size)
    return gamma(rng, size, mean_gap, cv_a)


def sim_days(rng, d, rho, cv_a, days=2000, nmax=None):
    """1日8時間の受付。朝は空。来た順に1つの窓口。返す：待ち・用件・長い用件か・その日の何人目か（1日ごとの行）"""
    mean_gap = MEAN / rho
    nmax = nmax or int(OPEN_MIN / mean_gap * 2.2) + 20
    arr = np.cumsum(gaps(rng, (days, nmax), mean_gap, cv_a), axis=1)
    svc, is_long = draw_service(rng, d, (days, nmax))
    valid = arr < OPEN_MIN
    w = np.zeros((days, nmax))
    for i in range(1, nmax):
        w[:, i] = np.maximum(0.0, w[:, i - 1] + svc[:, i - 1] - (arr[:, i] - arr[:, i - 1]))
    return w[valid], svc[valid], is_long[valid], arr, svc, w, valid


def sim_steady(rng, d, rho, cv_a, reps=400, n=12000, warm=2000):
    """ずっと開け続けたとき（最初の2,000人を捨てる）"""
    mean_gap = MEAN / rho
    w = np.zeros(reps)
    out = np.empty((reps, n - warm))
    s_prev, _ = draw_service(rng, d, reps)
    for i in range(1, n):
        g = gaps(rng, reps, mean_gap, cv_a)
        w = np.maximum(0.0, w + s_prev - g)
        s_prev, _ = draw_service(rng, d, reps)
        if i >= warm:
            out[:, i - warm] = w
    return out.ravel()


def summarize(w, svc, is_long):
    r = {"customers": int(len(w)), "mean_wait": round(float(w.mean()), 2),
         "median_wait": round(float(np.median(w)), 2), "p90_wait": round(float(np.quantile(w, .9)), 2),
         "share_wait_ge_15": round(float((w >= 15).mean()), 4), "share_no_wait": round(float((w <= 1e-9).mean()), 4),
         "mean_service": round(float(svc.mean()), 3)}
    if is_long.any():
        r["mean_wait_short_errand"] = round(float(w[~is_long].mean()), 2)
        r["mean_wait_long_errand"] = round(float(w[is_long].mean()), 2)
        r["short_errand_service"] = round(float(svc[~is_long].mean()), 2)
    return r


def pk_wait(rho, cv_s, cv_a=1.0):
    """ポラチェック・ヒンチンの式（でたらめに来るとき）。来方が違うときはキングマンの近い値"""
    return rho / (1 - rho) * (cv_a ** 2 + cv_s ** 2) / 2 * MEAN


def main():
    rng = np.random.default_rng(SEED)
    # 1) 基本：利用率0.75・でたらめに来る・1日8時間×2,000日
    base_rows, base_w = [], {}
    for j, d in enumerate(DISTS):
        w, s, lg, *_ = sim_days(np.random.default_rng(SEED * 10 + j), d, 0.75, 1.0)
        r = {"dist": d["name"], "service_cv": round(theory_cv(d), 3), **summarize(w, s, lg)}
        base_rows.append(r)
        base_w[d["key"]] = w
    base = pd.DataFrame(base_rows)
    base.to_csv(RES / "base_rho075_days.csv", index=False)

    # 2) 確かめ：利用率×来方×ばらつき（1日8時間×1,000日）
    grid = []
    for rho in [0.6, 0.75, 0.9]:
        for ai, (aname, cv_a) in enumerate(ARRIVALS):
            for j, d in enumerate(DISTS):
                sd = SEED * 1000 + int(rho * 100) * 37 + ai * 7 + j
                w, s, lg, *_ = sim_days(np.random.default_rng(sd), d, rho, cv_a, days=1000)
                grid.append({"rho": rho, "arrival": aname, "arrival_cv": cv_a, "dist": d["name"],
                             "service_cv": round(theory_cv(d), 3), "mean_wait": round(float(w.mean()), 2),
                             "p90_wait": round(float(np.quantile(w, .9)), 2),
                             "share_wait_ge_15": round(float((w >= 15).mean()), 4)})
    grid = pd.DataFrame(grid)
    grid["ratio_to_const"] = grid.mean_wait / grid.groupby(["rho", "arrival"]).mean_wait.transform("first")
    grid["ratio_to_const"] = grid.ratio_to_const.round(2)
    grid.to_csv(RES / "sensitivity_days.csv", index=False)
    order_same = []
    for (rho, a), g in grid.groupby(["rho", "arrival"], sort=False):
        order_same.append(bool(np.all(np.diff(g.mean_wait.values) > 0)))

    # 3) ずっと開け続けたとき（でたらめに来る）を式と比べる
    steady = []
    for rho in [0.6, 0.75, 0.9]:
        for j, d in enumerate(DISTS):
            w = sim_steady(np.random.default_rng(SEED * 3 + int(rho * 100) * 11 + j), d, rho, 1.0)
            cv = theory_cv(d)
            steady.append({"rho": rho, "dist": d["name"], "service_cv": round(cv, 3),
                           "sim_mean_wait": round(float(w.mean()), 2), "formula_mean_wait": round(pk_wait(rho, cv), 2)})
    steady = pd.DataFrame(steady)
    steady["sim_over_formula"] = (steady.sim_mean_wait / steady.formula_mean_wait).round(3)
    steady.to_csv(RES / "steady_vs_formula.csv", index=False)

    # data：同じ来方の10日分で、5つの置き方の用件の時間と待ち
    drng = np.random.default_rng(SEED + 1)
    mean_gap = MEAN / 0.75
    rows = []
    arr = np.cumsum(drng.exponential(mean_gap, (10, 300)), axis=1)
    cols = {}
    for d in DISTS:
        s, lg = draw_service(drng, d, (10, 300))
        w = np.zeros((10, 300))
        for i in range(1, 300):
            w[:, i] = np.maximum(0.0, w[:, i - 1] + s[:, i - 1] - (arr[:, i] - arr[:, i - 1]))
        cols[d["key"]] = (s, w)
    for day in range(10):
        for i in range(300):
            if arr[day, i] >= OPEN_MIN:
                break
            row = {"day": day + 1, "customer": i + 1, "arrive_min": round(float(arr[day, i]), 3)}
            for d in DISTS:
                row[f"service_{d['key']}"] = round(float(cols[d["key"]][0][day, i]), 3)
                row[f"wait_{d['key']}"] = round(float(cols[d["key"]][1][day, i]), 3)
            rows.append(row)
    pd.DataFrame(rows).to_csv(DATA / "ten_days_same_arrivals.csv", index=False)

    b = base.set_index("dist")
    recs = [{k: v for k, v in r.items() if v == v} for r in base.to_dict("records")]  # NaN（短い／長い用件の区別なし）を落とす
    out = {"base_rho075_poisson_2000days": recs,
           "base_ratio_mix5_to_const": round(float(b.loc["20人に1人が42分", "mean_wait"] / b.loc["全員4分", "mean_wait"]), 2),
           "base_ratio_exp_to_const": round(float(b.loc["ばらつき中", "mean_wait"] / b.loc["全員4分", "mean_wait"]), 2),
           "base_median_min": float(base.median_wait.min()), "base_median_max": float(base.median_wait.max()),
           "sensitivity": {"settings": int(len(grid) // len(DISTS)), "order_same_in_all": bool(all(order_same)),
                           "order_same_count": int(sum(order_same)),
                           "mix5_ratio_to_const_min": float(grid[grid.dist == "20人に1人が42分"].ratio_to_const.min()),
                           "mix5_ratio_to_const_max": float(grid[grid.dist == "20人に1人が42分"].ratio_to_const.max()),
                           "exp_ratio_to_const_min": float(grid[grid.dist == "ばらつき中"].ratio_to_const.min()),
                           "exp_ratio_to_const_max": float(grid[grid.dist == "ばらつき中"].ratio_to_const.max())},
           "steady_vs_formula": steady.to_dict("records"),
           "steady_sim_over_formula_min": float(steady.sim_over_formula.min()),
           "steady_sim_over_formula_max": float(steady.sim_over_formula.max())}
    json.dump(out, open(RES / "a880_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：平均の待ち（基本）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    names = base.dist.tolist()[::-1]
    vals = base.mean_wait.tolist()[::-1]
    ax.barh(names, vals, color=COLORS[::-1])
    for i, (v, cv) in enumerate(zip(vals, base.service_cv.tolist()[::-1])):
        ax.text(v + 0.3, i, f"{v:.1f}分（用件の時間の変動係数 {cv:.2f}）", va="center", fontsize=9)
    ax.set_xlim(0, max(vals) * 1.55)
    ax.set_xlabel("待ち時間の平均（分）。用件の時間の平均はどれも4分、利用率0.75")
    ax.set_title(f"用件の時間の平均は同じでも、待ちの平均は{vals[-1]:.1f}分から{vals[0]:.1f}分まで変わる", fontsize=12)
    save(fig, "a880_mean_wait.png", SRC)

    # 図2：x分以上待った人の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xs = np.arange(0, 61, 1)
    for d, c in zip(DISTS, COLORS):
        w = np.sort(base_w[d["key"]])
        share = 1 - np.searchsorted(w, xs, side="left") / len(w)
        ax.plot(xs, share * 100, color=c, lw=2, label=d["name"])
    ax.set_xlabel("待ち時間（分）"); ax.set_ylabel("これ以上待った人の割合（%）")
    ax.set_ylim(0, 80); ax.set_xlim(0, 60)
    ax.legend(frameon=False, fontsize=9)
    sh = b.loc["20人に1人が42分", "share_wait_ge_15"] * 100
    sc = b.loc["全員4分", "share_wait_ge_15"] * 100
    ax.set_title(f"15分以上待った人：全員4分なら{sc:.1f}%、20人に1人が42分なら{sh:.1f}%", fontsize=12)
    save(fig, "a880_tail.png", SRC)

    # 図3：利用率ごと（でたらめに来る、1日8時間）
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.9), sharey=True)
    for ax, (aname, cv_a) in zip(axes, ARRIVALS):
        g = grid[grid.arrival == aname]
        for d, c in zip(DISTS, COLORS):
            gg = g[g.dist == d["name"]]
            ax.plot(gg.rho, gg.mean_wait, marker="o", color=c, lw=2, label=d["name"])
        ax.set_yscale("log"); ax.set_xticks([0.6, 0.75, 0.9])
        ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50]); ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20", "50"])
        ax.minorticks_off()
        ax.set_title(aname, fontsize=10.5); ax.set_xlabel("利用率（窓口が使われている時間の割合）")
    axes[0].set_ylabel("待ち時間の平均（分、対数の目盛り）")
    axes[0].legend(frameon=False, fontsize=8.5)
    fig.suptitle("来方や混み具合を変えても、ばらつきの大きい順に待ちは長い（1日8時間×1,000日）", fontsize=12.5, y=1.02)
    save(fig, "a880_by_rho.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
