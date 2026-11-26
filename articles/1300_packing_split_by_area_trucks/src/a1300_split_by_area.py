"""1300 配送先の方面ごとに分けて詰め、方面をまぜないと、全部をまとめて詰めるより車は何台増えるのか？（架空のデータ）

作成者が置いた架空の通販の配送。1日の荷物を車に積む。車1台の荷台の容量は1,000L（大きさだけで数え、重さは数えない）。
荷物1個の大きさは、中央値20L・対数のばらつき0.8の右に長い乱数（1〜600Lに収める）。
1日の荷物の数は、大きさの合計の見込みが車 D 台分（基本10台分）になるように、平均の個数を個数の乱数で振る（平均のまわりに散らばる）。
荷物ごとに、A〜Dの4つの方面のどれに届けるかを決める（基本は同じ割合）。
積み方は、どちらも「大きい順に並べてから、入る最初の車に入れる（入らなければ新しい車）」。
  まとめて：その日の荷物を全部まとめて積む
  方面ごと：方面ごとに分けて積み、方面をまぜない（台数は方面ごとの台数の合計）
下限：まとめて＝切り上げ（大きさの合計÷1,000）、方面ごと＝方面ごとの切り上げの合計。
確かめ：方面の数（2・4・8）×1日の量（車3・10・30台分）×荷物の大きさ（中央値20L・80L）×方面の割合（同じ・偏る）の36通り。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1300
SRC = "架空の通販の配送（作成者が置いた荷物の大きさの分布・方面の割合・車の容量からの乱数、seed 1300）"
CAP = 1000.0
SIGMA = 0.8
DAYS = 200
DAYS_GRID = 100


def shares(k, kind):
    if kind == "同じ":
        return np.full(k, 1 / k)
    w = 0.6 ** np.arange(k)          # 偏る：1つ目の方面がいちばん多く、順に0.6倍ずつ
    return w / w.sum()


def pack_sorted(sizes):
    """大きい順に並べてから、入る最初の車に入れる。戻り値：車の台数、各荷物の車の番号（並べる前の順）"""
    order = np.argsort(-sizes, kind="stable")
    rem = np.zeros(len(sizes) + 1)
    used = 0
    truck = np.empty(len(sizes), int)
    for i in order:
        s = sizes[i]
        if used:
            ok = np.nonzero(rem[:used] >= s - 1e-9)[0]
        else:
            ok = []
        if len(ok):
            t = ok[0]
        else:
            t = used; rem[t] = CAP; used += 1
        rem[t] -= s
        truck[i] = t
    return used, truck


def one_day(rng, k, load, median, kind):
    mean_size = median * np.exp(SIGMA ** 2 / 2)
    n = rng.poisson(load * CAP / mean_size)
    size = np.clip(rng.lognormal(np.log(median), SIGMA, n), 1, 600)
    area = rng.choice(k, n, p=shares(k, kind))
    tot = size.sum()
    mixed, t_mixed = pack_sorted(size)
    split = 0
    t_split = np.empty(n, int)
    lb_split = 0
    per_area = []
    for a in range(k):
        m = area == a
        if m.sum() == 0:
            per_area.append((0.0, 0)); continue
        u, tt = pack_sorted(size[m])
        t_split[m] = tt + split
        split += u
        lb_split += int(np.ceil(size[m].sum() / CAP - 1e-9))
        per_area.append((float(size[m].sum()), int(u)))
    return {"n_items": int(n), "total_L": float(tot), "lb_mixed": int(np.ceil(tot / CAP - 1e-9)),
            "mixed": int(mixed), "lb_split": lb_split, "split": int(split),
            "frac_sum": float(sum((v / CAP) % 1 for v, _ in per_area))}, (size, area, t_mixed, t_split, per_area)


def run(k, load, median, kind, days, seed):
    rng = np.random.default_rng(seed)
    rows = []
    first = None
    for d in range(days):
        r, detail = one_day(rng, k, load, median, kind)
        r["day"] = d + 1
        rows.append(r)
        if first is None:
            first = detail
    df = pd.DataFrame(rows)
    df["extra"] = df.split - df.mixed
    df["fill_mixed_pct"] = 100 * df.total_L / (df.mixed * CAP)
    df["fill_split_pct"] = 100 * df.total_L / (df.split * CAP)
    return df, first


def summ(df, k):
    ex = df.extra
    return {"days": len(df), "mixed_mean": round(float(df.mixed.mean()), 3), "split_mean": round(float(df.split.mean()), 3),
            "extra_mean": round(float(ex.mean()), 3), "extra_min": int(ex.min()), "extra_max": int(ex.max()),
            "extra_pct_mean": round(float((100 * ex / df.mixed).mean()), 2),
            "fill_mixed_pct": round(float(df.fill_mixed_pct.mean()), 2),
            "fill_split_pct": round(float(df.fill_split_pct.mean()), 2),
            "fill_drop_pt": round(float((df.fill_mixed_pct - df.fill_split_pct).mean()), 2),
            "mixed_eq_lb_pct": round(float(100 * (df.mixed == df.lb_mixed).mean()), 1),
            "split_eq_lb_pct": round(float(100 * (df.split == df.lb_split).mean()), 1),
            "lb_extra_mean": round(float((df.lb_split - df.lb_mixed).mean()), 3),
            "half_rule": round((k - 1) / 2, 3),
            "extra0_pct": round(float(100 * (ex == 0).mean()), 1)}


def main():
    t0 = time.time()
    base, first = run(4, 10, 20, "同じ", DAYS, SEED)
    base.to_csv(RES / "base_days.csv", index=False, float_format="%.4f")
    sb = summ(base, 4)
    dist = base.extra.value_counts().sort_index()
    dist_pct = {int(k): round(float(100 * v / len(base)), 1) for k, v in dist.items()}

    size, area, t_mixed, t_split, per_area = first
    pd.DataFrame({"item": np.arange(1, len(size) + 1), "area": [chr(65 + a) for a in area], "size_L": size,
                  "truck_mixed": t_mixed + 1, "truck_split": t_split + 1}).to_csv(
        DATA / "day1_items.csv", index=False, float_format="%.3f")
    day1 = base.iloc[[0]].to_dict("records")[0]
    day1 = {k: (round(v, 3) if isinstance(v, float) else int(v)) for k, v in day1.items()}
    day1["per_area"] = [{"area": chr(65 + a), "size_total_L": round(v, 1), "trucks": u,
                         "fill_pct": round(100 * v / (u * CAP), 2) if u else None} for a, (v, u) in enumerate(per_area)]

    grid = []
    i = 0
    for k in [2, 4, 8]:
        for load in [3, 10, 30]:
            for med in [20, 80]:
                for kind in ["同じ", "偏る"]:
                    if (k, load, med, kind) == (4, 10, 20, "同じ"):
                        d = base.iloc[:DAYS_GRID]
                    else:
                        d, _ = run(k, load, med, kind, DAYS_GRID, SEED * 100 + i)
                    i += 1
                    grid.append({"areas": k, "load_trucks": load, "load_per_area_if_equal": round(load / k, 3), "item_median_L": med, "shares": kind, **summ(d, k)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    mm = lambda c, g=grid: [float(g[c].min()), float(g[c].max())]
    rob = {"settings": len(grid), "extra_mean": mm("extra_mean"), "extra_pct_mean": mm("extra_pct_mean"),
           "fill_drop_pt": mm("fill_drop_pt"),
           "extra_pct_by_load": {str(l): mm("extra_pct_mean", g) for l, g in grid.groupby("load_trucks")},
           "extra_mean_by_areas": {str(a): mm("extra_mean", g) for a, g in grid.groupby("areas")},
           "extra_pct_by_areas": {str(a): mm("extra_pct_mean", g) for a, g in grid.groupby("areas")},
           "extra_mean_by_shares": {s: mm("extra_mean", g) for s, g in grid.groupby("shares", sort=False)},
           "extra_mean_by_median": {str(s): mm("extra_mean", g) for s, g in grid.groupby("item_median_L")},
           "extra_zero_settings": int((grid.extra_mean == 0).sum()),
           "split_eq_lb_pct_min": float(grid.split_eq_lb_pct.min()), "mixed_eq_lb_pct_min": float(grid.mixed_eq_lb_pct.min())}
    # 同じ割合で、1つの方面の量が車2.5台分以上の置き方での、半分の目安（(方面の数−1)÷2）との差
    eq = grid[(grid.shares == "同じ") & (grid.load_trucks / grid.areas >= 2.5)]
    rob["equal_per_area_ge2_5_settings"] = int(len(eq))
    rob["equal_per_area_ge2_5_extra_minus_half"] = [round(float((eq.extra_mean - eq.half_rule).min()), 3),
                                                 round(float((eq.extra_mean - eq.half_rule).max()), 3)]

    out = {"base": {"setting": "方面4・同じ割合・1日の量は車10台分・荷物の中央値20L・車の容量1,000L", **sb,
                    "extra_dist_pct": dist_pct, "day1": day1},
           "robust": rob}
    json.dump(out, open(RES / "a1300_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1日目の車ごとの積載率（まとめて・方面ごと）
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.9), sharey=True)
    vol_m = pd.Series(size).groupby(t_mixed).sum().values / CAP * 100
    vol_s = pd.Series(size).groupby(t_split).sum().values / CAP * 100
    area_of_truck = pd.Series(area).groupby(t_split).first().values
    axes[0].bar(np.arange(1, len(vol_m) + 1), vol_m, color=BLUE)
    axes[0].set_title(f"まとめて積む：{len(vol_m)}台", fontsize=11)
    cols = [BLUE, ORANGE, GREEN, GRAY]
    axes[1].bar(np.arange(1, len(vol_s) + 1), vol_s, color=[cols[a] for a in area_of_truck])
    for a in range(4):
        axes[1].bar([0], [0], color=cols[a], label=f"{chr(65 + a)}方面")
    axes[1].legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    axes[1].set_title(f"方面ごとに分けて積む：{len(vol_s)}台", fontsize=11)
    for ax in axes:
        ax.set_xlabel("車"); ax.set_ylim(0, 110)
        ax.set_xticks(np.arange(1, max(len(vol_m), len(vol_s)) + 1))
        ax.tick_params(axis="x", labelsize=8)
    axes[0].set_ylabel("荷台の容量に対する積んだ量（%）")
    fig.suptitle("方面ごとに分けると、方面ごとの最後の1台が半端に残る（1日目）", fontsize=12, y=1.04)
    save(fig, "a1300_day1.png", SRC, y=-0.08)

    # 図2：増えた台数の分布（200日）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xs = np.arange(0, max(dist.index) + 1)
    vals = [dist_pct.get(int(v), 0.0) for v in xs]
    ax.bar(xs, vals, color=ORANGE)
    for xv, v in zip(xs, vals):
        ax.text(xv, v + 1, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels([f"+{v}台" for v in xs])
    ax.set_xlabel("方面ごとに分けて増えた車の台数（まとめて積んだときとの差）"); ax.set_ylabel("日の割合（%）")
    ax.set_ylim(0, max(vals) * 1.25)
    ax.set_title(f"方面4・1日車10台分では、平均で+{sb['extra_mean']}台（{DAYS}日）")
    save(fig, "a1300_extra_dist.png", SRC)

    # 図3：1日の量と方面の数で、増えた割合（同じ割合・中央値20L）
    g = grid[(grid.shares == "同じ") & (grid.item_median_L == 20)]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    w = 0.25
    loads = [3, 10, 30]
    for j, k in enumerate([2, 4, 8]):
        v = [float(g[(g.areas == k) & (g.load_trucks == l)].extra_pct_mean.iloc[0]) for l in loads]
        ax.bar(np.arange(3) + (j - 1) * w, v, w, color=[LIGHT, BLUE, INK][j], label=f"方面{k}")
        for xx, vv in zip(np.arange(3) + (j - 1) * w, v):
            ax.text(xx, vv + 1, f"{vv:.2f}%", ha="center", fontsize=7.5)
    ax.set_xticks(np.arange(3)); ax.set_xticklabels([f"車{l}台分" for l in loads])
    ax.set_xlabel("1日の荷物の量（大きさの合計の見込み）"); ax.set_ylabel("まとめて積むより増えた台数の割合（%）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("増える台数はほぼ方面の数で決まり、1日の量が少ないほど割合が大きい", fontsize=12)
    save(fig, "a1300_by_load.png", SRC + "。方面の割合が同じ・荷物の中央値20Lのとき")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
