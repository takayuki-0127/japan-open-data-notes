"""1250 同じ日に2冊出すと、1冊ずつ出したときと比べて、1冊あたりの順位はどう見えるのか？（架空のデータ）

架空の電子書籍の分野（ほかの本2万冊）。ほかの本は、本ごとのふだんの1日の売れ方を置き、毎日でたらめに数を引く。
販売の順位の決まり（作成者が置いたもの）：その日までの毎日の冊数に、1日さかのぼるごとに半分の重みを付けて足した点の高い順。
作成者の架空の本 X・Y。読者（ファン）F 人が、それぞれの本を確率0.8で買う。買う日は発売の日からの日数を平均1.5日で散らす。
ファンでない人の買い方は1冊ごとに1日0.5冊。
・1冊ずつ：X を0日目、Y を14日目に出す
・同じ日：X と Y を0日目に出す。両方を買うはずのファンのうち、割合 c は片方だけ買う。両方を買う人のうち、割合 q は2冊目を平均7日おくらせて買う
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1250
SRC = "架空の電子書籍の分野と販売の順位（作成者が乱数で作成、seed 1250）"
N_POOL, DAYS = 20000, 36           # ほかの本、数える日数（0〜35日目）
GAP = 14                           # 1冊ずつのとき、2冊目は14日目
LOOK = 14                          # 発売から14日（発売の日を含む）で順位を数える
BASE = dict(F=200, p=0.8, c=0.2, q=0.3, organic=0.5, delay_mean=1.5, late_mean=7.0)
TOP = 100
BURN = 20                          # ほかの本の点がたまるまでの助走の日数
W = 0.5 ** np.arange(DAYS)        # 1日さかのぼるごとに半分


def scores(sales):
    """sales: (..., DAYS)。各日の順位の点（その日までの冊数の重み付きの和）"""
    out = np.zeros_like(sales, dtype=float)
    acc = np.zeros(sales.shape[:-1])
    for t in range(sales.shape[-1]):
        acc = acc * 0.5 + sales[..., t]
        out[..., t] = acc
    return out


def make_pool(rng):
    lam = np.exp(np.log(0.3) + 1.5 * rng.standard_normal(N_POOL))
    s = rng.poisson(lam[:, None], size=(N_POOL, DAYS + BURN))
    sc = scores(s)[:, BURN:]            # はじめの20日は、点がたまるまでの助走として捨てる
    return np.sort(sc, axis=0)          # 日ごとに並べたほかの本の点


def fan_days(rng, n, start, mean):
    return start + np.floor(rng.exponential(mean, n)).astype(int)


def author_sales(rng, p, same_day):
    F = p["F"]
    buy_x = rng.random(F) < p["p"]
    buy_y = rng.random(F) < p["p"]
    sx = np.zeros(DAYS + 60, int); sy = np.zeros(DAYS + 60, int)
    ty = 0 if same_day else GAP
    if same_day:
        both = buy_x & buy_y
        drop = both & (rng.random(F) < p["c"])
        pick_x = rng.random(F) < 0.5
        buy_x = buy_x & ~(drop & ~pick_x)
        buy_y = buy_y & ~(drop & pick_x)
        both = buy_x & buy_y
        dx = fan_days(rng, F, 0, p["delay_mean"])
        dy = fan_days(rng, F, ty, p["delay_mean"])
        late = both & (rng.random(F) < p["q"])
        # 両方を買う人のうち q は、2冊目（でたらめにどちらか）を平均7日おくらせる
        late_x = late & (rng.random(F) < 0.5)
        late_y = late & ~late_x
        extra = np.floor(rng.exponential(p["late_mean"], F)).astype(int)
        dx = dx + np.where(late_x, extra, 0)
        dy = dy + np.where(late_y, extra, 0)
    else:
        dx = fan_days(rng, F, 0, p["delay_mean"])
        dy = fan_days(rng, F, ty, p["delay_mean"])
    np.add.at(sx, dx[buy_x], 1); np.add.at(sy, dy[buy_y], 1)
    sx = sx[:DAYS]; sy = sy[:DAYS]
    org = rng.poisson(p["organic"], size=(2, DAYS))
    sx = sx + org[0]; sy = sy + org[1] * (np.arange(DAYS) >= ty)
    return sx, sy, ty


def ranks(pool_sorted, sc_self, sc_other):
    """ほかの本と、作成者のもう1冊の点より下の位置"""
    r = np.empty(DAYS, int)
    for t in range(DAYS):
        above = N_POOL - np.searchsorted(pool_sorted[:, t], sc_self[t], side="right")
        r[t] = 1 + above + int(sc_other[t] > sc_self[t])
    return r


def one_run(rng, pool, p):
    res = {}
    for mode, same in [("separate", False), ("same", True)]:
        sx, sy, ty = author_sales(rng, p, same)
        scx, scy = scores(sx), scores(sy)
        rx, ry = ranks(pool, scx, scy), ranks(pool, scy, scx)
        per = []
        for s, r, t0 in [(sx, rx, 0), (sy, ry, ty)]:
            w = slice(t0, t0 + LOOK)
            per.append({"best": int(r[w].min()), "top_days": int((r[w] <= TOP).sum()),
                        "sold14": int(s[w].sum()), "rank_day1": int(r[t0])})
        res[mode] = per
        res[mode + "_series"] = (sx, sy, rx, ry)
    return res


def run_many(p, pools, seed):
    rows = []
    for r, pool in enumerate(pools):
        g = np.random.default_rng(seed + r)
        for k in range(5):            # 1つの分野で、作成者の出し方を5回ずつ
            res = one_run(g, pool, p)
            rec = {"rep": r, "k": k}
            for mode in ["separate", "same"]:
                per = res[mode]
                rec[f"{mode}_best"] = np.mean([q["best"] for q in per])
                rec[f"{mode}_best_med"] = float(np.median([q["best"] for q in per]))
                rec[f"{mode}_top_days"] = np.mean([q["top_days"] for q in per])
                rec[f"{mode}_sold14"] = np.mean([q["sold14"] for q in per])
                rec[f"{mode}_rank_day1"] = np.mean([q["rank_day1"] for q in per])
            rows.append(rec)
    return pd.DataFrame(rows)


def summ(df):
    out = {}
    for mode in ["separate", "same"]:
        out[mode] = {"best_rank_per_book_median": round(float(np.median(df[f"{mode}_best"])), 3),
                     "best_rank_per_book_mean": round(float(df[f"{mode}_best"].mean()), 3),
                     "top100_days_per_book": round(float(df[f"{mode}_top_days"].mean()), 3),
                     "sold14_per_book": round(float(df[f"{mode}_sold14"].mean()), 3)}
    out["best_rank_ratio_same_over_sep_median"] = round(float(np.median(df.same_best / df.separate_best)), 4)
    out["sold_ratio_same_over_sep"] = round(float(df.same_sold14.mean() / df.separate_sold14.mean()), 4)
    out["top_days_ratio_same_over_sep"] = round(float(df.same_top_days.mean() / df.separate_top_days.mean()), 4)
    out["share_same_best_worse"] = round(float((df.same_best > df.separate_best).mean()), 4)
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    pools = [make_pool(np.random.default_rng(SEED * 1000 + r)) for r in range(60)]   # 同じ60の分野を使い回す
    base = run_many(BASE, pools, SEED * 2000)
    base.to_csv(RES / "base_runs.csv", index=False, float_format="%.4f")
    s_base = summ(base)
    ctrl = run_many({**BASE, "c": 0.0, "q": 0.0}, pools, SEED * 2000)   # 片方だけ買う人も、おくらせる人もいない
    s_ctrl = summ(ctrl)
    only_c = summ(run_many({**BASE, "q": 0.0}, pools, SEED * 2000))
    only_q = summ(run_many({**BASE, "c": 0.0}, pools, SEED * 2000))

    # 順位と点の関係（1つの分野の14日目）：何冊分の点で何位か
    pool = pools[0]
    curve = []
    for rk in [1, 5, 10, 20, 50, 100, 200, 500, 1000]:
        curve.append({"rank": rk, "score_needed": round(float(pool[N_POOL - rk, LOOK]), 3)})
    pd.DataFrame(curve).to_csv(RES / "rank_score_curve.csv", index=False)

    # 例の1回（基本の置き方）
    g = np.random.default_rng(SEED + 7)
    ex = one_run(g, pool, BASE)
    sxs, sys_, rxs, rys = ex["separate_series"]
    sxd, syd, rxd, ryd = ex["same_series"]
    pd.DataFrame({"day": np.arange(DAYS), "sep_X_sold": sxs, "sep_Y_sold": sys_, "sep_X_rank": rxs, "sep_Y_rank": rys,
                  "same_X_sold": sxd, "same_Y_sold": syd, "same_X_rank": rxd, "same_Y_rank": ryd}).to_csv(
        DATA / "example_run.csv", index=False)

    # 確かめ：c・q・F（27通り、各20分野×5回）
    grid = []
    for F in [100, 200, 400]:
        for c in [0.0, 0.2, 0.4]:
            for q in [0.0, 0.3, 0.6]:
                d = run_many({**BASE, "F": F, "c": c, "q": q}, pools[:20], SEED * 10 + F)
                s = summ(d)
                grid.append({"F": F, "c": c, "q": q,
                             "sep_best_med": s["separate"]["best_rank_per_book_median"],
                             "same_best_med": s["same"]["best_rank_per_book_median"],
                             "best_ratio": s["best_rank_ratio_same_over_sep_median"],
                             "sold_ratio": s["sold_ratio_same_over_sep"],
                             "top_days_sep": s["separate"]["top100_days_per_book"],
                             "top_days_same": s["same"]["top100_days_per_book"],
                             "share_same_worse": s["share_same_best_worse"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g0 = grid[(grid.c == 0) & (grid.q == 0)]
    gx = grid[~((grid.c == 0) & (grid.q == 0))]
    robust = {"best_ratio_range": [float(grid.best_ratio.min()), float(grid.best_ratio.max())],
              "best_ratio_range_c0q0": [float(g0.best_ratio.min()), float(g0.best_ratio.max())],
              "best_ratio_range_others": [float(gx.best_ratio.min()), float(gx.best_ratio.max())],
              "sold_ratio_range": [float(grid.sold_ratio.min()), float(grid.sold_ratio.max())],
              "best_ratio_q_only_range": [float(grid[(grid.c == 0) & (grid.q > 0)].best_ratio.min()),
                                          float(grid[(grid.c == 0) & (grid.q > 0)].best_ratio.max())],
              "sold_ratio_q_only_range": [float(grid[(grid.c == 0) & (grid.q > 0)].sold_ratio.min()),
                                          float(grid[(grid.c == 0) & (grid.q > 0)].sold_ratio.max())],
              "combos_best_ratio_gt_sold_inverse": int((grid.best_ratio > 1 / grid.sold_ratio + 1e-9).sum())}

    out = {"setting": {**BASE, "n_pool": N_POOL, "gap_days": GAP, "look_days": LOOK, "top": TOP},
           "base": s_base, "control_c0_q0": s_ctrl, "only_c": only_c, "only_q": only_q,
           "rank_score_curve_day14": curve,
           "example": {"separate": ex["separate"], "same": ex["same"]}, "robust": robust}
    json.dump(out, open(RES / "a1250_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の1回の順位
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 4.0), sharey=True)
    for ax, (rx, ry, ty, title) in zip(axs, [(rxs, rys, GAP, "1冊ずつ（Yは14日目に発売）"), (rxd, ryd, 0, "同じ日に2冊")]):
        dd = np.arange(DAYS)
        ax.plot(dd, rx, color=BLUE, lw=1.4, label="X")
        ax.plot(dd[ty:], ry[ty:], color=ORANGE, lw=1.4, label="Y")
        ax.set_yscale("log"); ax.invert_yaxis()
        ax.axhline(TOP, color=GRAY, lw=0.8, ls="--")
        ax.set_title(title, fontsize=11); ax.set_xlabel("Xの発売からの日")
    axs[0].set_ylabel("販売の順位（対数の目盛り、上ほど上位）")
    axs[0].text(DAYS - 1, TOP * 0.85, "100位", color=GRAY, fontsize=8.5, ha="right")
    axs[1].legend(frameon=False, fontsize=9)
    fig.suptitle("例の1回：同じ日に出すと、1冊ごとの最高順位が下がった（基本の置き方）", fontsize=12, y=1.03)
    save(fig, "a1250_example.png", SRC)

    # 図2：基本・対照・片方だけ：1冊あたりの最高順位（中央値）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    labs = ["どちらもいない\n（c=0・q=0）", "片方だけ買う人\nだけ（c=0.2）",
            "おくらせる人\nだけ（q=0.3）", "基本\n（c=0.2・q=0.3）"]
    ss = [s_ctrl, only_c, only_q, s_base]
    xs = np.arange(4)
    v1 = [s["separate"]["best_rank_per_book_median"] for s in ss]
    v2 = [s["same"]["best_rank_per_book_median"] for s in ss]
    ax.bar(xs - 0.19, v1, 0.38, color=BLUE, label="1冊ずつ")
    ax.bar(xs + 0.19, v2, 0.38, color=ORANGE, label="同じ日に2冊")
    for i in range(4):
        ax.text(xs[i] - 0.19, v1[i] + 0.5, f"{v1[i]:.1f}", ha="center", fontsize=8.5)
        ax.text(xs[i] + 0.19, v2[i] + 0.5, f"{v2[i]:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=8)
    ax.set_ylim(0, 20); ax.set_ylabel("1冊あたりの最高順位（位）\n300回の中央値、大きいほど下の順位", linespacing=1.5)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("同じ日に2冊でも、ファンの買い方が変わらなければ順位はほぼ同じ")
    save(fig, "a1250_best_rank.png", SRC)

    # 図3：27通り：売れた冊数の比と、最高順位の比
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for F, c in zip([100, 200, 400], [LIGHT, BLUE, INK]):
        d = grid[grid.F == F]
        ax.scatter(d.sold_ratio, d.best_ratio, color=c, s=28, label=f"ファン{F}人")
    xx = np.linspace(grid.sold_ratio.min() - 0.02, 1.02, 50)
    ax.plot(xx, 1 / xx, color=GRAY, lw=0.8, ls="--"); ax.text(xx[0], 1 / xx[0], " 冊数の比の逆数", color=GRAY, fontsize=8.5, va="bottom")
    ax.axhline(1, color=INK, lw=0.6); ax.axvline(1, color=INK, lw=0.6)
    ax.set_xlabel("同じ日 ÷ 1冊ずつ：1冊あたりの14日の冊数"); ax.set_ylabel("同じ日 ÷ 1冊ずつ：1冊あたりの最高順位\n（大きいほど下の順位に見える）", linespacing=1.5)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("27通りすべてで、最高順位の比は冊数の比の逆数より大きかった", fontsize=12)
    save(fig, "a1250_grid.png", SRC)
    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
