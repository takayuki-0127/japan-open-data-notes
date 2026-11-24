"""1191 「24時間以内に返事」の目標を置くと、返事までの時間の分布はどう形を変えるのか？（架空のデータ）

架空の会社の問い合わせ窓口（交代で24時間受ける。担当4人）。問い合わせの来る数は日ごとに波があり、
1件の対応にかかる時間はまちまち（作成者が置いた分布からの乱数）。
同じ問い合わせの列を、3つの取り方で担当が順に片付ける。
  ① 目標なし：来た順
  ② 目標あり：24時間をまだ過ぎていないものを来た順に。過ぎたものは後回し
  ③ 目標あり：②に加えて、締め切りまで余裕があるうちは軽いものから。締め切りが近い（残り B 時間）ものは先に
返事までの時間（来てから返事を送るまで）の分布を比べる。
"""
import json
import time
import heapq
from collections import deque
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1191
SRC = "架空の問い合わせ窓口（作成者が置いた来る数・対応時間からの乱数、seed 1191）"
TARGET = 24.0
AGENTS = 4
PER_DAY = 100          # 1日に来る数の中央値
DAYS = 2880            # 基本の日数（数える分）
WARM = 30              # 初めの空の状態をならす日数（数えない）
DAYS_GRID = 1440
RHO = 0.85             # 担当の手の空きに対する仕事の量（平均）
DAY_SD = 0.25          # 日ごとの来る数の波（対数の標準偏差）
DAY_AR = 0.7           # 波の続きやすさ（前の日との結びつき）
SVC_SD = 0.8           # 1件の対応時間のばらつき（対数の標準偏差）
BUFFER = 4.0           # ③で「締め切りが近い」とみなす残り時間
POL = ["①来た順", "②過ぎたものは後回し", "③余裕があれば軽いものから"]
KEYS = ["fifo", "late_last", "light_first"]


def make(rng, days, rho=RHO, day_sd=DAY_SD, svc_sd=SVC_SD):
    """来た時刻（時間）と対応時間（時間）。数える範囲は WARM 日目から"""
    total = days + WARM
    x = np.zeros(total)
    e = rng.normal(0, day_sd * np.sqrt(1 - DAY_AR ** 2), total)
    x[0] = rng.normal(0, day_sd)
    for t in range(1, total):
        x[t] = DAY_AR * x[t - 1] + e[t]
    lam = PER_DAY * np.exp(x) / np.mean(np.exp(x))      # 平均を PER_DAY にそろえる
    counts = rng.poisson(lam)
    arr = np.concatenate([d * 24 + np.sort(rng.uniform(0, 24, c)) for d, c in enumerate(counts)])
    mean_svc = rho * AGENTS * 24 / PER_DAY
    svc = mean_svc * np.exp(rng.normal(0, svc_sd, len(arr)) - svc_sd ** 2 / 2)
    return arr, svc


def simulate(arr, svc, policy, buffer=BUFFER):
    n = len(arr)
    reply = np.empty(n)
    free = [0.0] * AGENTS
    heapq.heapify(free)
    i = 0
    q = deque()           # まだ過ぎていない（来た順）
    late = deque()        # 過ぎたもの（来た順）
    light = []            # ③：対応時間の軽い順
    taken = np.zeros(n, bool)
    done = 0
    while done < n:
        f = heapq.heappop(free)
        while i < n and arr[i] <= f:
            q.append(i)
            if policy == 2:
                heapq.heappush(light, (svc[i], i))
            i += 1
        # 過ぎたものを分ける
        if policy >= 1:
            while q and (taken[q[0]] or f - arr[q[0]] >= TARGET):
                j = q.popleft()
                if not taken[j]:
                    late.append(j)
        while late and taken[late[0]]:
            late.popleft()
        if not q and not late:
            f = max(f, arr[i])
            q.append(i)
            if policy == 2:
                heapq.heappush(light, (svc[i], i))
            i += 1
        if policy == 0:
            j = q.popleft()
        elif policy == 1:
            j = q.popleft() if q else late.popleft()
        else:
            if q and f - arr[q[0]] >= TARGET - buffer:
                j = q.popleft()
            elif q:
                while True:
                    _, j = heapq.heappop(light)
                    if not taken[j] and f - arr[j] < TARGET:
                        break
            else:
                j = late.popleft()
        taken[j] = True
        end = f + svc[j]
        reply[j] = end - arr[j]
        heapq.heappush(free, end)
        done += 1
    return reply


def summarize(r):
    return {"band_0_20_pct": round(float(np.mean(r <= 20)) * 100, 2),
            "within24_pct": round(float(np.mean(r <= TARGET)) * 100, 2),
            "mean_h": round(float(np.mean(r)), 2),
            "median_h": round(float(np.median(r)), 2),
            "p90_h": round(float(np.quantile(r, 0.9)), 2),
            "p99_h": round(float(np.quantile(r, 0.99)), 2),
            "max_h": round(float(np.max(r)), 1),
            "band_20_24_pct": round(float(np.mean((r > 20) & (r <= 24))) * 100, 2),
            "band_24_28_pct": round(float(np.mean((r > 24) & (r <= 28))) * 100, 2),
            "band_24_48_pct": round(float(np.mean((r > 24) & (r <= 48))) * 100, 2),
            "over48_pct": round(float(np.mean(r > 48)) * 100, 2),
            "over24_mean_h": round(float(np.mean(r[r > TARGET])), 2) if np.any(r > TARGET) else None}


def run_all(rng, days, **kw):
    buffer = kw.pop("buffer", BUFFER)
    arr, svc = make(rng, days, **kw)
    keep = arr >= WARM * 24
    out = {}
    for p, k in enumerate(KEYS):
        r = simulate(arr, svc, p, buffer)
        out[k] = r[keep]
    return out, arr[keep], svc[keep]


GRID_RHO = [0.8, 0.85, 0.9]
GRID_DAY = [0.15, 0.25, 0.35]
GRID_SVC = [0.5, 0.8, 1.1]
GRID_BUF = [2.0, 4.0, 8.0]
BANDS = [("20時間以内", 0, 20), ("20〜24時間", 20, 24), ("24〜48時間", 24, 48), ("48時間超", 48, 1e9)]


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res, arr, svc = run_all(rng, DAYS)
    base = {k: summarize(res[k]) for k in KEYS}
    base["mean_svc_h"] = round(float(np.mean(svc)), 3)
    base["n_tickets"] = int(len(arr))
    # 24時間を過ぎた件の中身（①で過ぎた件が②でどうなるか）
    late1 = res["fifo"] > TARGET
    base["fifo_late_share_within24_in_late_last_pct"] = round(float(np.mean(res["late_last"][late1] <= TARGET)) * 100, 2)
    # ③で軽いもの・重いもの
    heavy = svc > np.quantile(svc, 0.75)
    base["light_first_heavy_within24_pct"] = round(float(np.mean(res["light_first"][heavy] <= TARGET)) * 100, 2)
    base["light_first_light_within24_pct"] = round(float(np.mean(res["light_first"][~heavy] <= TARGET)) * 100, 2)
    base["fifo_heavy_within24_pct"] = round(float(np.mean(res["fifo"][heavy] <= TARGET)) * 100, 2)
    base["light_first_heavy_band_20_24_pct"] = round(float(np.mean((res["light_first"][heavy] > 20) & (res["light_first"][heavy] <= 24))) * 100, 2)

    # data：初めの90日分
    keep = arr < (WARM + 90) * 24
    pd.DataFrame({"arrive_h": np.round(arr[keep] - WARM * 24, 3), "handle_h": np.round(svc[keep], 3),
                  "reply_fifo_h": np.round(res["fifo"][keep], 3), "reply_late_last_h": np.round(res["late_last"][keep], 3),
                  "reply_light_first_h": np.round(res["light_first"][keep], 3)}).to_csv(DATA / "first_90days.csv", index=False)

    # 締め切りが近いとみなす残り時間（③）
    buf_rows = []
    for b in GRID_BUF:
        r, _, _ = run_all(np.random.default_rng(SEED + 2), DAYS_GRID, buffer=b)
        sm = summarize(r["light_first"])
        buf_rows.append({"buffer_h": b, **{f"light_first_{k}": v for k, v in sm.items()}})
    pd.DataFrame(buf_rows).to_csv(RES / "buffer.csv", index=False)

    # 27通り
    rows = []
    g = 0
    for rho in GRID_RHO:
        for dsd in GRID_DAY:
            for ssd in GRID_SVC:
                g += 1
                r, _, _ = run_all(np.random.default_rng(SEED + 100 + g), DAYS_GRID, rho=rho, day_sd=dsd, svc_sd=ssd)
                row = {"rho": rho, "day_sd": dsd, "svc_sd": ssd}
                for k in KEYS:
                    sm = summarize(r[k])
                    for kk in ["within24_pct", "mean_h", "median_h", "p90_h", "p99_h", "band_20_24_pct", "band_24_28_pct", "over24_mean_h"]:
                        row[f"{k}_{kk}"] = sm[kk]
                rows.append(row)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    act = grid[grid["fifo_within24_pct"] < 99.5]   # ①で24時間を過ぎる件がある程度ある通り

    def rng_(col, df=grid):
        return [float(df[col].min()), float(df[col].max())]

    gsum = {"n_settings": int(len(grid)),
            "n_settings_fifo_late_over_0_5pct": int(len(act)),
            "fifo_within24_range": rng_("fifo_within24_pct"),
            "late_last_within24_range": rng_("late_last_within24_pct"),
            "light_first_within24_range": rng_("light_first_within24_pct"),
            "n_late_last_within24_ge_fifo": int((grid["late_last_within24_pct"] >= grid["fifo_within24_pct"]).sum()),
            "n_light_first_band2024_gt_fifo": int((grid["light_first_band_20_24_pct"] > grid["fifo_band_20_24_pct"]).sum()),
            "n_act_late_last_p99_gt_fifo": int((act["late_last_p99_h"] > act["fifo_p99_h"]).sum()),
            "n_act_late_last_over24mean_gt_fifo": int((act["late_last_over24_mean_h"] > act["fifo_over24_mean_h"]).sum()),
            "act_p99_ratio_late_last_range": [round(float((act["late_last_p99_h"] / act["fifo_p99_h"]).min()), 3),
                                              round(float((act["late_last_p99_h"] / act["fifo_p99_h"]).max()), 3)],
            "act_over24mean_ratio_late_last_range": [round(float((act["late_last_over24_mean_h"] / act["fifo_over24_mean_h"]).min()), 3),
                                                     round(float((act["late_last_over24_mean_h"] / act["fifo_over24_mean_h"]).max()), 3)],
            "mean_diff_late_last_minus_fifo_range": [round(float((grid["late_last_mean_h"] - grid["fifo_mean_h"]).min()), 2),
                                                     round(float((grid["late_last_mean_h"] - grid["fifo_mean_h"]).max()), 2)],
            "mean_rel_diff_late_last_vs_fifo_pct_range": [round(float(((grid["late_last_mean_h"] / grid["fifo_mean_h"] - 1) * 100).min()), 2),
                                                          round(float(((grid["late_last_mean_h"] / grid["fifo_mean_h"] - 1) * 100).max()), 2)],
            "n_light_first_within24_ge_fifo": int((grid["light_first_within24_pct"] >= grid["fifo_within24_pct"]).sum()),
            "n_act_light_first_over24mean_gt_fifo": int((act["light_first_over24_mean_h"] > act["fifo_over24_mean_h"]).sum()),
            "mean_rel_diff_light_first_vs_fifo_pct_range": [round(float(((grid["light_first_mean_h"] / grid["fifo_mean_h"] - 1) * 100).min()), 2),
                                                            round(float(((grid["light_first_mean_h"] / grid["fifo_mean_h"] - 1) * 100).max()), 2)],
            "within24_gain_late_last_pt_range": [round(float((grid["late_last_within24_pct"] - grid["fifo_within24_pct"]).min()), 2),
                                                 round(float((grid["late_last_within24_pct"] - grid["fifo_within24_pct"]).max()), 2)],
            "light_first_band2024_range": rng_("light_first_band_20_24_pct"),
            "fifo_band2024_range": rng_("fifo_band_20_24_pct"),
            "act_ids": act.index.tolist()}
    out = {"settings": {"agents": AGENTS, "per_day_median": PER_DAY, "days": DAYS, "warm_days": WARM, "days_grid": DAYS_GRID,
                        "rho": RHO, "day_sd": DAY_SD, "day_ar": DAY_AR, "svc_sd": SVC_SD, "target_h": TARGET, "buffer_h": BUFFER,
                        "grid_rho": GRID_RHO, "grid_day_sd": GRID_DAY, "grid_svc_sd": GRID_SVC, "grid_buffer": GRID_BUF, "seed": SEED},
           "base": base, "buffer": buf_rows, "grid_summary": gsum, "run_sec_note": "所要は確かめたことに書く"}
    with open(RES / "a1191_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：分布の形
    bins = np.arange(0, 98, 2)
    hist = {"from_h": bins[:-1]}
    for k in KEYS:
        h, _ = np.histogram(np.minimum(res[k], 95.999), bins=bins)
        hist[k + "_pct"] = np.round(h / len(res[k]) * 100, 2)
    hist = pd.DataFrame(hist)
    hist.to_csv(RES / "hist.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    cols = [GRAY, BLUE, ORANGE]
    YMAX = 16
    for k, lab, c, ls in zip(KEYS, POL, cols, ["-", "--", "-"]):
        v = hist[k + "_pct"].values
        ax.step(bins, np.append(v, v[-1]), where="post", color=c, lw=2 if k != "late_last" else 1.6, ls=ls,
                label=f"{lab}（0〜2時間は{v[0]:.2f}%）")
    ax.axvline(TARGET, color=INK, lw=0.8, ls=":")
    ax.text(TARGET + 0.8, YMAX * 0.93, "24時間", fontsize=9, color=INK)
    ax.set_xlabel("返事までの時間（時間、2時間ごと。94時間を超えた分は右端の区分にまとめた）")
    ax.set_ylabel("全体に占める割合（%）")
    ax.set_xlim(0, 96); ax.set_ylim(0, YMAX)
    ax.set_title("目標を置くと、24時間の前後に山ができる（0〜2時間の区分は図の上にはみ出す）", fontsize=11.5)
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1191_hist.png", SRC)

    # 図2：区分ごとの割合
    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.26
    xs = np.arange(len(BANDS))
    for p, (k, lab, c) in enumerate(zip(KEYS, POL, cols)):
        v = [float(np.mean((res[k] > lo) & (res[k] <= hi))) * 100 for _, lo, hi in BANDS]
        b = ax.bar(xs + (p - 1) * w, v, w, color=c, label=lab)
        for xx, vv in zip(xs + (p - 1) * w, v):
            ax.text(xx, vv + 1, f"{vv:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(xs); ax.set_xticklabels([b[0] for b in BANDS])
    ax.set_ylim(0, 100); ax.set_ylabel("全体に占める割合（%）")
    ax.set_title("返事までの時間の区分（基本の置き方、2,880日分）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1191_bands.png", SRC)

    # 図3：27通り
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.3))
    ax = axs[0]
    ax.scatter(grid["fifo_within24_pct"], grid["late_last_within24_pct"], color=BLUE, s=22, label="②過ぎたものは後回し")
    ax.scatter(grid["fifo_within24_pct"], grid["light_first_within24_pct"], color=ORANGE, s=14, marker="x", label="③余裕があれば軽いものから")
    lo = min(grid["fifo_within24_pct"].min(), 40)
    ax.plot([lo, 100], [lo, 100], color=GRAY, lw=0.8)
    ax.set_xlabel("①来た順の24時間以内（%）"); ax.set_ylabel("目標ありの24時間以内（%）")
    ax.set_title("24時間以内の割合", fontsize=11)
    ax.legend(frameon=False, fontsize=8)
    ax = axs[1]
    a = grid.loc[act.index]
    ax.scatter(a["fifo_over24_mean_h"], a["late_last_over24_mean_h"], color=BLUE, s=22, label="②過ぎたものは後回し")
    ax.scatter(a["fifo_over24_mean_h"], a["light_first_over24_mean_h"], color=ORANGE, s=14, marker="x", label="③余裕があれば軽いものから")
    mx = max(a[["fifo_over24_mean_h", "late_last_over24_mean_h", "light_first_over24_mean_h"]].max())
    ax.plot([24, mx], [24, mx], color=GRAY, lw=0.8)
    ax.set_xscale("log"); ax.set_yscale("log")
    tk = [25, 50, 100, 200, 400, 800]
    from matplotlib.ticker import FixedLocator, NullLocator, FixedFormatter
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(FixedLocator(tk)); axis.set_major_formatter(FixedFormatter([str(t) for t in tk]))
        axis.set_minor_locator(NullLocator())
    ax.set_xlabel("①来た順で24時間を過ぎた件の平均（時間）"); ax.set_ylabel("目標ありで過ぎた件の平均（時間）")
    ax.set_title(f"24時間を過ぎた件の平均（{len(act)}通り、目盛りは対数）", fontsize=11)
    fig.suptitle("置き方27通り：灰色の線より上なら、目標ありのほうが大きい", fontsize=12)
    fig.tight_layout()
    save(fig, "a1191_robust.png", SRC)
    print(json.dumps(base, ensure_ascii=False))
    print(json.dumps(gsum, ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
