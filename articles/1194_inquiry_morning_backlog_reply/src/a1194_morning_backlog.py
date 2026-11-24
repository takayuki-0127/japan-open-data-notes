"""1194 夜と休みの日に来た分を翌朝まとめて受けると、朝の返事までの時間はどう見えるのか？（架空のデータ）

架空の会社の問い合わせ窓口。担当は平日9〜18時だけ働き、1件にかかる時間はどの時刻も同じ分布（作成者が置いた）。
夜と休みの日に来た分は、翌朝（休みの明けの朝）に積み残しとして並ぶ。
返事までの時間を「来た時刻の帯」で見るか「返した時刻の帯」で見るか、暦の時間で数えるか営業時間で数えるかで、
朝の数字がどう見えるかを数える。受け方は次の3通り。
 A 来た順に受ける
 B 営業時間中に来た分を先に受け、積み残しはあいた手で受ける
 C 来た順のまま、平日9〜11時だけ担当を1人増やす
"""
import heapq
import json
import time
from collections import deque
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1194
SRC = "架空の会社の問い合わせ窓口（作成者が置いた来る件数・担当の人数・1件の時間からの乱数、seed 1194）"
OPEN, CLOSE = 9 * 60, 18 * 60          # 平日の営業時間（分）
BUS_H_WEEK = 45                         # 1週の営業時間
OUT_H_WEEK = 168 - BUS_H_WEEK
BASE = {"staff": 4, "mean_min": 15.0, "cv": 0.8, "util": 0.8, "out_share": 0.3}
WEEKS = 27                              # はじめの1週は数えない
GRID_OUT = [0.0, 0.15, 0.3, 0.45]
GRID_UTIL = [0.6, 0.8, 0.9]
GRID_STAFF = [2, 4, 8]
GRID_WEEKS = 9
POL = {"A": "A 来た順", "B": "B 営業時間中に来た分を先に", "C": "C 9〜11時だけ1人増やす"}


def r(x, d=4):
    return round(float(x), d)


def in_window(t, lo, hi):
    day = int(t // 1440)
    m = t - day * 1440
    return day % 7 < 5 and lo <= m < hi


def next_open(t, lo=OPEN, hi=CLOSE):
    """t 以後で、その担当が働ける最初の時刻"""
    if in_window(t, lo, hi):
        return t
    day = int(t // 1440)
    m = t - day * 1440
    if day % 7 < 5 and m < lo:
        return day * 1440 + lo
    day += 1
    while day % 7 >= 5:
        day += 1
    return day * 1440 + lo


def is_business(t):
    t = np.asarray(t)
    day = (t // 1440).astype(int)
    m = t - day * 1440
    return (day % 7 < 5) & (m >= OPEN) & (m < CLOSE)


def bus_cum(t):
    """0 から t までの営業時間（分）"""
    t = np.asarray(t, dtype=float)
    day = np.floor(t / 1440)
    m = t - day * 1440
    week = np.floor(day / 7)
    dow = day - week * 7
    full = week * 5 * (CLOSE - OPEN) + np.minimum(dow, 5) * (CLOSE - OPEN)
    part = np.where(dow < 5, np.clip(m - OPEN, 0, CLOSE - OPEN), 0)
    return full + part


def arrivals(rng, weeks, util, out_share, staff, mean_min):
    cap_h = staff * 60 / mean_min
    total = util * cap_h * BUS_H_WEEK
    lam_in = total * (1 - out_share) / BUS_H_WEEK
    lam_out = total * out_share / OUT_H_WEEK
    ts = []
    for h in range(weeks * 168):
        lam = lam_in if is_business(h * 60 + 1) else lam_out
        k = rng.poisson(lam)
        if k:
            ts.append(h * 60 + rng.uniform(0, 60, k))
    t = np.sort(np.concatenate(ts))
    return t


def simulate(rng, policy="A", weeks=WEEKS, util=BASE["util"], out_share=BASE["out_share"],
             staff=BASE["staff"], mean_min=BASE["mean_min"], cv=BASE["cv"]):
    arr = arrivals(rng, weeks, util, out_share, staff, mean_min)
    n = len(arr)
    k = 1 / cv ** 2
    svc = rng.gamma(k, mean_min / k, n)
    outh = ~is_business(arr)
    windows = [(OPEN, CLOSE)] * staff
    if policy == "C":
        windows = windows + [(OPEN, 11 * 60)]
    heap = [(next_open(0.0, *w), i) for i, w in enumerate(windows)]
    heapq.heapify(heap)
    q_in, q_out = deque(), deque()
    fin = np.full(n, np.nan)
    p = 0
    done = 0
    while done < n:
        t, i = heapq.heappop(heap)
        while p < n and arr[p] <= t:
            (q_out if (policy == "B" and outh[p]) else q_in).append(p)
            p += 1
        if not q_in and not q_out:
            heapq.heappush(heap, (next_open(arr[p], *windows[i]), i))
            continue
        j = q_in.popleft() if q_in else q_out.popleft()
        fin[j] = t + svc[j]
        done += 1
        heapq.heappush(heap, (next_open(fin[j], *windows[i]), i))
    df = pd.DataFrame({"arrive_min": arr, "reply_min": fin, "out_of_hours": outh})
    df["cal_h"] = (df.reply_min - df.arrive_min) / 60
    df["bus_min"] = bus_cum(df.reply_min.values) - bus_cum(df.arrive_min.values)
    day = (df.arrive_min // 1440).astype(int)
    df["arrive_band"] = np.where(df.out_of_hours, "時間外", ((df.arrive_min - day * 1440) // 60).astype(int).astype(str) + "時台")
    rday = (df.reply_min // 1440).astype(int)
    rh = ((df.reply_min - rday * 1440) // 60).astype(int)
    df["reply_band"] = np.where(rh >= 18, "18時以降", rh.astype(str) + "時台")
    df["monday"] = (rday % 7 == 0)
    return df[df.arrive_min >= 7 * 1440].reset_index(drop=True)


BANDS = ["時間外"] + [f"{h}時台" for h in range(9, 18)]
RBANDS = [f"{h}時台" for h in range(9, 18)] + ["18時以降"]


def by_arrival(df):
    g = df.groupby("arrive_band")
    out = []
    for b in BANDS:
        d = df[df.arrive_band == b]
        out.append({"arrive_band": b, "n": len(d), "mean_cal_h": r(d.cal_h.mean(), 3), "median_cal_h": r(d.cal_h.median(), 3),
                    "mean_bus_min": r(d.bus_min.mean(), 2), "median_bus_min": r(d.bus_min.median(), 2)})
    return out


def by_reply(df):
    out = []
    for b in RBANDS:
        d = df[df.reply_band == b]
        out.append({"reply_band": b, "n": len(d), "mean_cal_h": r(d.cal_h.mean(), 3), "mean_bus_min": r(d.bus_min.mean(), 2),
                    "share_out_of_hours_pct": r(100 * d.out_of_hours.mean(), 2)})
    return out


def morning_ratio(df):
    m = df[df.arrive_band == "9時台"].bus_min.mean()
    a = df[df.arrive_band.isin(["15時台", "16時台", "17時台"])].bus_min.mean()
    return m, a


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    seeds = rng.integers(0, 2**31, 1 + len(GRID_OUT) * len(GRID_UTIL) * len(GRID_STAFF))
    res = {"seed": SEED, "base": BASE, "weeks_counted": WEEKS - 1,
           "weekly_arrivals_set": r(BASE["util"] * BASE["staff"] * 60 / BASE["mean_min"] * BUS_H_WEEK, 1)}
    dfs = {}
    for pol in ["A", "B", "C"]:      # 3通りとも同じ来る時刻・同じ1件の時間（同じ乱数）で比べる
        dfs[pol] = simulate(np.random.default_rng(seeds[0]), pol)
    # 1 来た時刻の帯ごと
    rows = []
    for pol in ["A", "B", "C"]:
        for x in by_arrival(dfs[pol]):
            rows.append({"policy": pol, **x})
    arr_df = pd.DataFrame(rows)
    arr_df.to_csv(RES / "by_arrival_band.csv", index=False)
    # 2 返した時刻の帯ごと（A）
    rep_df = pd.DataFrame(by_reply(dfs["A"]))
    rep_df.to_csv(RES / "by_reply_band_A.csv", index=False)
    # 月曜とそれ以外の朝（A、9時台に返した分）
    dA = dfs["A"]
    nine = dA[dA.reply_band == "9時台"]
    res["reply_9_monday_mean_cal_h"] = r(nine[nine.monday].cal_h.mean(), 3)
    res["reply_9_other_mean_cal_h"] = r(nine[~nine.monday].cal_h.mean(), 3)
    # 3 受け方ごとのまとめ
    prow = []
    for pol in ["A", "B", "C"]:
        d = dfs[pol]
        m, a = morning_ratio(d)
        prow.append({"policy": pol, "label": POL[pol], "n": len(d),
                     "all_mean_cal_h": r(d.cal_h.mean(), 3), "all_mean_bus_min": r(d.bus_min.mean(), 2),
                     "out_mean_bus_min": r(d[d.out_of_hours].bus_min.mean(), 2),
                     "in_mean_bus_min": r(d[~d.out_of_hours].bus_min.mean(), 2),
                     "arrive9_mean_bus_min": r(m, 2), "arrive15_17_mean_bus_min": r(a, 2), "ratio_9_vs_15_17": r(m / a, 3),
                     "reply9_mean_cal_h": r(d[d.reply_band == "9時台"].cal_h.mean(), 3),
                     "reply15_17_mean_cal_h": r(d[d.reply_band.isin(["15時台", "16時台", "17時台"])].cal_h.mean(), 3),
                     "in_within_60bus_pct": r(100 * (d[~d.out_of_hours].bus_min <= 60).mean(), 2),
                     "out_within_60bus_pct": r(100 * (d[d.out_of_hours].bus_min <= 60).mean(), 2)})
    pol_df = pd.DataFrame(prow)
    pol_df.to_csv(RES / "policies.csv", index=False)
    # 4 確かめ：時間外の割合 × 込み具合 × 担当の人数（A と B）
    grow = []
    k = 1
    for s in GRID_OUT:
        for u in GRID_UTIL:
            for c in GRID_STAFF:
                row = {"out_share": s, "util": u, "staff": c}
                for pol in ["A", "B"]:
                    d = simulate(np.random.default_rng(seeds[k]), pol, weeks=GRID_WEEKS, util=u, out_share=s, staff=c)
                    m, a = morning_ratio(d)
                    row[f"{pol}_arrive9_bus_min"] = r(m, 2)
                    row[f"{pol}_arrive15_17_bus_min"] = r(a, 2)
                    row[f"{pol}_ratio_9_vs_15_17"] = r(m / a, 3)
                    row[f"{pol}_reply9_cal_h"] = r(d[d.reply_band == "9時台"].cal_h.mean(), 3)
                    row[f"{pol}_reply9_out_share_pct"] = r(100 * d[d.reply_band == "9時台"].out_of_hours.mean(), 2)
                    row[f"{pol}_all_bus_min"] = r(d.bus_min.mean(), 2)
                k += 1
                grow.append(row)
    grid = pd.DataFrame(grow)
    grid.to_csv(RES / "grid.csv", index=False)

    # まとめ
    A = pol_df.set_index("policy")
    res["policies"] = prow
    res["weekly_arrivals_counted_mean"] = r(len(dA) / (WEEKS - 1), 1)
    res["by_arrival_A"] = arr_df[arr_df.policy == "A"].drop(columns="policy").to_dict("records")
    res["by_reply_A"] = rep_df.to_dict("records")
    g0 = grid[grid.out_share == 0]
    gp = grid[grid.out_share > 0]
    res["grid_summary"] = {
        "A_ratio_out0_range": [r(g0.A_ratio_9_vs_15_17.min(), 3), r(g0.A_ratio_9_vs_15_17.max(), 3)],
        "A_ratio_outpos_range": [r(gp.A_ratio_9_vs_15_17.min(), 3), r(gp.A_ratio_9_vs_15_17.max(), 3)],
        "A_ratio_outpos_gt1_count": int((gp.A_ratio_9_vs_15_17 > 1).sum()), "outpos_count": int(len(gp)),
        "B_ratio_outpos_range": [r(gp.B_ratio_9_vs_15_17.min(), 3), r(gp.B_ratio_9_vs_15_17.max(), 3)],
        "A_reply9_cal_h_outpos_range": [r(gp.A_reply9_cal_h.min(), 3), r(gp.A_reply9_cal_h.max(), 3)],
        "A_reply9_cal_h_out0_range": [r(g0.A_reply9_cal_h.min(), 3), r(g0.A_reply9_cal_h.max(), 3)],
        "A_reply9_out_share_outpos_range": [r(gp.A_reply9_out_share_pct.min(), 2), r(gp.A_reply9_out_share_pct.max(), 2)],
        "all_bus_B_over_A_range": [r((gp.B_all_bus_min / gp.A_all_bus_min).min(), 3), r((gp.B_all_bus_min / gp.A_all_bus_min).max(), 3)],
    }
    res["grid_by_out_share_A_ratio"] = {str(s): [r(grid[grid.out_share == s].A_ratio_9_vs_15_17.min(), 3),
                                                 r(grid[grid.out_share == s].A_ratio_9_vs_15_17.max(), 3)] for s in GRID_OUT}
    res["grid_base_rows"] = grid[(grid.staff == 4) & (grid.util == 0.8)].to_dict("records")
    # データ（A の1回分の一部：数えた最初の4週）
    dd = dA[dA.arrive_min < 7 * 1440 * 5].copy()
    out = dd[["arrive_min", "reply_min", "out_of_hours", "arrive_band", "reply_band", "cal_h", "bus_min"]].copy()
    out["arrive_min"] = out.arrive_min.round(2)
    out["reply_min"] = out.reply_min.round(2)
    out["cal_h"] = out.cal_h.round(3)
    out["bus_min"] = out.bus_min.round(2)
    out.to_csv(DATA / "inquiries_A_weeks1_4.csv", index=False)

    # 図1 来た時刻の帯ごとの返事までの時間（営業時間の分）
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(len(BANDS))
    w = 0.27
    for i, (pol, col) in enumerate([("A", BLUE), ("B", ORANGE), ("C", GREEN)]):
        v = arr_df[arr_df.policy == pol].set_index("arrive_band").loc[BANDS, "mean_bus_min"].values
        ax.bar(x + (i - 1) * w, v, w, color=col, label=POL[pol])
    ax.set_xticks(x)
    ax.set_xticklabels(BANDS, fontsize=9)
    ax.set_ylim(0, None)
    ax.set_ylabel("返事までの時間の平均（営業時間の分）")
    ax.set_xlabel("問い合わせが来た時刻の帯（時間外＝平日の夜と土日）")
    ax.set_title("来た時刻で分けると、朝に来た分が長く待つ（担当の速さはどの時刻も同じと置いた）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1194_by_arrival.png", "出典：" + SRC)

    # 図2 返した時刻の帯ごとの返事までの時間（暦の時間）と時間外の割合
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(len(RBANDS))
    v = rep_df.set_index("reply_band").loc[RBANDS, "mean_cal_h"].values
    sh = rep_df.set_index("reply_band").loc[RBANDS, "share_out_of_hours_pct"].values
    ax.bar(x, v, 0.6, color=BLUE)
    for xi, vi, si in zip(x, v, sh):
        ax.text(xi, vi + 0.2, f"{vi:g}時間\n時間外{si:g}%", ha="center", va="bottom", fontsize=7.5, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(RBANDS, fontsize=9)
    ax.set_ylim(0, max(v) * 1.25)
    ax.set_ylabel("返事までの時間の平均（暦の時間）")
    ax.set_xlabel("返事を返した時刻の帯（A 来た順）")
    ax.set_title("返した時刻で分けると、9時台の返事は前の晩からの待ちを含む")
    save(fig, "a1194_by_reply.png", "出典：" + SRC)

    # 図3 確かめ：9時台に来た分÷15〜17時台に来た分（A）
    fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharey=True)
    ymax = grid[["A_ratio_9_vs_15_17", "B_ratio_9_vs_15_17"]].values.max() * 1.1
    for ax, c in zip(axes, GRID_STAFF):
        for u, col in zip(GRID_UTIL, [LIGHT, BLUE, INK]):
            d = grid[(grid.staff == c) & (grid.util == u)].sort_values("out_share")
            ax.plot(d.out_share * 100, d.A_ratio_9_vs_15_17, "o-", color=col, label=f"A 込み具合{u:.0%}")
            ax.plot(d.out_share * 100, d.B_ratio_9_vs_15_17, "s--", color=col, alpha=0.8, label=f"B 込み具合{u:.0%}")
        ax.axhline(1, color=GRAY, lw=0.8)
        ax.set_title(f"担当{c}人")
        ax.set_xlabel("時間外に来る割合（%）")
        ax.set_ylim(0, ymax)
        ax.set_xticks([s * 100 for s in GRID_OUT])
    axes[0].set_ylabel("9時台÷15〜17時台に来た分\n（営業時間の待ちの平均の比）")
    axes[2].legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.suptitle("時間外の分があると、来た順（A、実線）では9時台に来た分が長く待つ。B（破線）では差が小さい（36通り）", y=1.02)
    save(fig, "a1194_grid.png", "出典：" + SRC + "。込み具合＝1週に来る件数÷営業時間に受けられる件数")

    res["run_sec"] = r(time.time() - t0, 1)
    with open(RES / "a1194_main.json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in res.items() if k != "run_sec"}, f, ensure_ascii=False, indent=1)
    print(json.dumps(res["policies"], ensure_ascii=False, indent=1))
    print(json.dumps(res["grid_summary"], ensure_ascii=False))
    print(res["reply_9_monday_mean_cal_h"], res["reply_9_other_mean_cal_h"], res["run_sec"])


if __name__ == "__main__":
    main()
