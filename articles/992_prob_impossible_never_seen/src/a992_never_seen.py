"""992 「ありえない」と感じる確率は、何%くらいなのか？（架空のデータ）

架空の店で起きうる「めったにないこと」500種類。種類ごとに1日に起きる本当の確率を作成者が置く
（0.01%〜10%の間で、対数で一様）。店を開いてからの30日で一度も起きていない種類を「ありえない」と呼ぶ
（作成者が置いた定義）。「ありえない」とした種類の本当の確率は何%くらいか、次の1年でどれだけ起きるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 992
SRC = "架空の店の「めったにないこと」（作成者が乱数で作成、seed 992）"
K = 500
P_LO, P_HI = 1e-4, 0.1
N_SEEN = 30
NEXT = 365
REPS = 200


def draw_p(rng, k=K, lo=P_LO, hi=P_HI):
    return np.exp(rng.uniform(np.log(lo), np.log(hi), k))


def one_rep(rng, n_seen=N_SEEN, lo=P_LO, hi=P_HI):
    p = draw_p(rng, K, lo, hi)
    c0 = rng.binomial(n_seen, p)
    c1 = rng.binomial(NEXT, p)
    c30 = rng.binomial(30, p)          # 次の30日
    return p, c0, c1, c30


def summarize(p, c0, c1, c30):
    z = c0 == 0
    pz = p[z]
    return {"n_impossible": int(z.sum()), "share_impossible_pct": z.mean() * 100,
            "mean_p_pct": pz.mean() * 100, "median_p_pct": np.median(pz) * 100, "p90_p_pct": np.quantile(pz, 0.9) * 100,
            "share_p_ge1pct": (pz >= 0.01).mean() * 100,
            "share_happen_next365_pct": (c1[z] >= 1).mean() * 100,
            "kinds_happen_next30": float((c30[z] >= 1).sum()), "any_happen_next30": float((c30[z] >= 1).any()),
            "times_next365": float(c1[z].sum())}


def expected_share_impossible(n, lo=P_LO, hi=P_HI, m=200001):
    """式：対数で一様な p について (1−p)^n の平均（数値積分）"""
    u = np.linspace(np.log(lo), np.log(hi), m)
    return float(np.trapezoid((1 - np.exp(u)) ** n, u) / (u[-1] - u[0]))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 基本：500種類×200回
    rows = []
    first = None
    for r in range(REPS):
        p, c0, c1, c30 = one_rep(rng)
        if r == 0:
            first = (p, c0, c1, c30)
        rows.append(summarize(p, c0, c1, c30))
    sim = pd.DataFrame(rows)
    base = {k: round(float(v), 3) for k, v in sim.mean().items()}
    base["any_happen_next30_pct"] = round(float(sim.any_happen_next30.mean()) * 100, 2)
    base.pop("any_happen_next30")
    base["share_impossible_formula_pct"] = round(expected_share_impossible(N_SEEN) * 100, 3)

    # 2) 1つの種類について：本当の確率 p と見た日数 n で、一度も起きない確率（式）と、次の1年に起きる確率（式）
    single = []
    for p in [0.001, 0.0027, 0.005, 0.01, 0.03, 0.05, 0.1]:
        row = {"p_pct": p * 100}
        for n in [30, 90, 365]:
            row[f"never_in_{n}d_pct"] = round((1 - p) ** n * 100, 2)
        row["happen_next365_pct"] = round((1 - (1 - p) ** 365) * 100, 2)
        single.append(row)
    single = pd.DataFrame(single)
    single.to_csv(RES / "single_event.csv", index=False)
    upper = {n: {"p95_upper_pct": round((1 - 0.05 ** (1 / n)) * 100, 3), "three_over_n_pct": round(3 / n * 100, 3)}
             for n in [30, 90, 365]}
    # 乱数での確かめ：p=1%、30日を20万回
    chk = rng.binomial(30, 0.01, 200000)
    single_check = {"p1pct_never_in_30d_sim_pct": round(float((chk == 0).mean()) * 100, 2),
                    "p1pct_never_in_30d_formula_pct": round(0.99 ** 30 * 100, 2)}

    # 3) 確かめ：見た日数と、確率の上の端を変える（各100回）
    grid = []
    for n in [30, 90, 365]:
        for lo in [1e-5, 1e-4, 1e-3]:
            for hi in [0.03, 0.1, 0.3]:
                g = np.random.default_rng(SEED * 100 + n + int(hi * 1000) + int(-np.log10(lo)) * 7)
                rr = pd.DataFrame([summarize(*one_rep(g, n, lo, hi)) for _ in range(100)])
                grid.append({"days_seen": n, "p_min_pct": lo * 100, "p_max_pct": hi * 100,
                             "share_impossible_pct": round(float(rr.share_impossible_pct.mean()), 2),
                             "median_p_pct": round(float(rr.median_p_pct.mean()), 4),
                             "p90_p_pct": round(float(rr.p90_p_pct.mean()), 3),
                             "share_p_ge1pct": round(float(rr.share_p_ge1pct.mean()), 2),
                             "share_happen_next365_pct": round(float(rr.share_happen_next365_pct.mean()), 2),
                             "kinds_happen_next30": round(float(rr.kinds_happen_next30.mean()), 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_days_pmax.csv", index=False)

    # データ：1回分
    p, c0, c1, c30 = first
    ev = pd.DataFrame({"kind": np.arange(1, K + 1), "p_true": p, "count_first30": c0, "count_next365": c1,
                       "impossible": (c0 == 0).astype(int)})
    ev.to_csv(DATA / "events.csv", index=False, float_format="%.6f")
    one = summarize(p, c0, c1, c30)
    one = {k: (round(float(v), 3)) for k, v in one.items()}

    out = {"setting": {"kinds": K, "p_min_pct": P_LO * 100, "p_max_pct": P_HI * 100, "days_seen": N_SEEN,
                       "next_days": NEXT, "reps": REPS},
           "base_200reps": base, "first_rep": one, "upper_95": upper, "single_check": single_check,
           "single_event": single.to_dict("records"), "grid": grid.to_dict("records"),
           "grid_info": {"cases": int(len(grid)), "reps_each": 100, "cases_365d": int((grid.days_seen == 365).sum())},
           "grid_range": {c: [float(grid[c].min()), float(grid[c].max())]
                          for c in ["share_p_ge1pct", "share_happen_next365_pct", "median_p_pct", "p90_p_pct", "kinds_happen_next30"]},
           "grid_range_30d": {c: [float(grid[grid.days_seen == 30][c].min()), float(grid[grid.days_seen == 30][c].max())]
                              for c in ["share_p_ge1pct", "share_happen_next365_pct", "median_p_pct", "p90_p_pct"]}}
    json.dump(out, open(RES / "a992_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：本当の確率の分布（30日で起きた種類と、一度も起きていない種類）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.logspace(np.log10(P_LO), np.log10(P_HI), 31)
    z = c0 == 0
    ax.hist([p[z] * 100, p[~z] * 100], bins=bins * 100, stacked=True, color=[ORANGE, LIGHT],
            label=[f"30日で一度も起きていない（「ありえない」{z.sum()}種類）", f"30日で起きた（{(~z).sum()}種類）"])
    ax.set_xscale("log")
    ax.set_xticks([0.01, 0.1, 1, 10]); ax.set_xticklabels(["0.01%", "0.1%", "1%", "10%"])
    ax.set_xlabel("1日に起きる本当の確率（対数の目盛り）"); ax.set_ylabel("種類の数")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    ax.set_title("「ありえない」とした種類にも、1日に1%を超えるものが混ざる（1回分）", fontsize=12)
    save(fig, "a992_hist.png", SRC)

    # 図2：一度も起きない確率と、本当の確率（式）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    pp = np.logspace(-4, np.log10(0.3), 400)
    for n, c in [(30, ORANGE), (90, BLUE), (365, GREEN)]:
        ax.plot(pp * 100, (1 - pp) ** n * 100, color=c, lw=2, label=f"{n}日見て一度も起きない確率")
        u = upper[n]["p95_upper_pct"]
        ax.plot([u], [5], "o", color=c, ms=5)
        ax.text(u * 1.08, 8, f"{u:.2f}%", color=c, fontsize=9)
    ax.axhline(5, color=GRAY, lw=1, ls="--")
    ax.set_xscale("log"); ax.set_xticks([0.01, 0.1, 1, 10]); ax.set_xticklabels(["0.01%", "0.1%", "1%", "10%"])
    ax.set_xlabel("1日に起きる本当の確率（対数の目盛り）"); ax.set_ylabel("一度も起きない確率（%）")
    ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, 0.1))
    ax.set_title("一度も起きない確率が5%になる本当の確率（点）は、見た日数で決まる", fontsize=12)
    save(fig, "a992_never_curve.png", SRC)

    # 図3：確かめ。「ありえない」とした種類のうち、次の1年で起きた割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(3); bw = 0.26
    for j, (lo, c) in enumerate([(1e-5, LIGHT), (1e-4, BLUE), (1e-3, ORANGE)]):
        g = grid[(grid.p_min_pct == lo * 100) & (grid.p_max_pct == P_HI * 100)]
        ax.bar(x + (j - 1) * bw, g.share_happen_next365_pct, bw, color=c, label=f"確率の下の端 {lo * 100:g}%")
        for i, v in enumerate(g.share_happen_next365_pct):
            ax.text(i + (j - 1) * bw, v + 1, f"{v:.1f}%", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"{n}日見て一度もない" for n in [30, 90, 365]])
    ax.set_ylabel("次の1年で起きた割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("「ありえない」とした種類のうち、次の1年で一度は起きた割合\n（確率の上の端10%、各100回）", fontsize=12)
    save(fig, "a992_next_year.png", SRC)

    print(json.dumps({k: out[k] for k in out if k not in ("grid", "single_event")}, ensure_ascii=False, indent=1))
    print(single.to_string()); print(grid.to_string()); print(round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
