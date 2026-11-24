"""1187 返事までの時間を営業時間で数えるか暦の時間で数えるかで、遅く見える曜日はどう入れかわるのか？（架空のデータ）

作成者が置いた架空の会社のメールの問い合わせ窓口。受付は24時間・毎日、返事を書くのは月〜金の9時〜18時だけ。
問い合わせは曜日・時刻ごとの来やすさ（作成者が置いた値）で、でたらめに来る。担当6人が、来た順に1通ずつ返事を書く
（1通にかかる時間は平均18分、営業時間の中だけで進む）。52週分（前後に1週ずつ余分に流し、数えない）。
(1) 来た曜日ごとに、返事までの時間を「暦の時間」（来てから返事までの実際の時間）と
    「営業時間」（そのうち月〜金9〜18時に入る時間）で数え、中央値と平均で遅い順に並べる
(2) 曜日ごとに、営業の始まり（9時）の時点で待っている問い合わせの数
(3) 確かめ：営業時間の外に来る量3通り×担当の数3通りの9通り×中央値・平均の2つ
"""
import json
import heapq
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1187
SRC = "架空の会社の問い合わせ窓口（作成者が置いた曜日・時刻ごとの来やすさと返事の時間からの乱数、seed 1187）"
DAYS = ["月", "火", "水", "木", "金", "土", "日"]
WEEKS, PAD = 52, 1
OPEN_H, CLOSE_H = 9, 18
SERVICE_MEAN = 18.0
BASE = {"off_scale": 1.0, "agents": 6}
OFF_SCALES = [0.5, 1.0, 1.5]
AGENTS = [6, 7, 8]
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def hourly_rate(off_scale):
    """曜日×時刻の1時間あたりの来る数（7×24）"""
    lam = np.zeros((7, 24))
    for d in range(7):
        for h in range(24):
            if d < 5:
                if OPEN_H <= h < CLOSE_H:
                    lam[d, h] = 10.0
                elif 7 <= h < OPEN_H or CLOSE_H <= h < 23:
                    lam[d, h] = 3.0 * off_scale
                else:
                    lam[d, h] = 0.5 * off_scale
            else:
                lam[d, h] = (4.0 if 9 <= h < 21 else 0.5) * off_scale
    return lam


def business_mask(n_weeks):
    m = np.zeros(n_weeks * 7 * 24 * 60, dtype=bool)
    for w in range(n_weeks):
        for d in range(5):
            s = ((w * 7 + d) * 24 + OPEN_H) * 60
            m[s:s + (CLOSE_H - OPEN_H) * 60] = True
    return m


def simulate(rng, off_scale, agents):
    n_weeks = WEEKS + 2 * PAD
    lam = hourly_rate(off_scale)
    # 来る時刻（分、連続）
    counts = rng.poisson(np.tile(lam.ravel(), n_weeks))
    hour_idx = np.repeat(np.arange(len(counts)), counts)
    arr = np.sort(hour_idx * 60 + rng.random(len(hour_idx)) * 60)
    mask = business_mask(n_weeks)
    cum = np.concatenate([[0], np.cumsum(mask)])          # cum[t]：t 分までの営業分
    open_idx = np.flatnonzero(mask)                         # 営業分 k が始まる暦の分
    fl = np.floor(arr).astype(int)
    frac = arr - fl
    b_arr = cum[fl] + np.where(mask[fl], frac, 0.0)          # 営業の時計での到着
    service = rng.exponential(SERVICE_MEAN, len(arr))
    free = [0.0] * agents
    heapq.heapify(free)
    b_end = np.empty(len(arr))
    for i in range(len(arr)):
        f = heapq.heappop(free)
        st = max(f, b_arr[i])
        b_end[i] = st + service[i]
        heapq.heappush(free, b_end[i])
    k = np.floor(b_end).astype(int)
    cal_end = open_idx[np.minimum(k, len(open_idx) - 1)] + (b_end - k)
    cal_h = (cal_end - arr) / 60
    bus_h = (b_end - b_arr) / 60
    week = (arr // (7 * 24 * 60)).astype(int)
    dow = ((arr // (24 * 60)) % 7).astype(int)
    hour = ((arr // 60) % 24).astype(int)
    keep = (week >= PAD) & (week < PAD + WEEKS)
    df = pd.DataFrame({"arrive_min": arr, "week": week, "dow": dow, "hour": hour, "calendar_h": cal_h,
                       "business_h": bus_h})[keep].reset_index(drop=True)
    # 営業の始まりの時点で待っている数（まだ返事を書き始めていない数＝来たが、書き始めが9時より後）
    starts = b_end - service
    backlog = []
    for w in range(PAD, PAD + WEEKS):
        for d in range(5):
            t_open = ((w * 7 + d) * 24 + OPEN_H) * 60
            b_open = cum[t_open]
            backlog.append({"week": w, "dow": d,
                            "waiting": int(((arr <= t_open) & (starts >= b_open)).sum())})
    return df, pd.DataFrame(backlog), lam


def by_day(df):
    g = df.groupby("dow")
    t = pd.DataFrame({"day": DAYS, "count": g.size().values,
                      "calendar_median_h": g.calendar_h.median().values, "calendar_mean_h": g.calendar_h.mean().values,
                      "business_median_h": g.business_h.median().values, "business_mean_h": g.business_h.mean().values})
    for c in ["calendar_median_h", "calendar_mean_h", "business_median_h", "business_mean_h"]:
        t[c.replace("_h", "_rank")] = t[c].rank(ascending=False, method="min").astype(int)  # 1＝いちばん遅い
        t[c] = t[c].round(2)
    return t


def rank_corr(a, b):
    return float(np.corrcoef(pd.Series(a).rank(), pd.Series(b).rank())[0, 1])


def main():
    rng = np.random.default_rng(SEED)
    df, bl, lam = simulate(rng, BASE["off_scale"], BASE["agents"])
    wk = lam.sum()
    bus_share = sum(lam[d, h] for d in range(5) for h in range(OPEN_H, CLOSE_H)) / wk
    out = {"setting": {"weeks": WEEKS, "open": f"月〜金 {OPEN_H}:00〜{CLOSE_H}:00", "service_mean_min": SERVICE_MEAN,
                       **BASE, "per_week_expected": r(wk, 1), "business_hours_arrival_share_pct": r(bus_share * 100, 2),
                       "load_pct": r(wk * SERVICE_MEAN / (BASE["agents"] * 45 * 60) * 100, 1)},
           "base": {"inquiries": len(df), "calendar_median_h": r(df.calendar_h.median(), 2),
                    "business_median_h": r(df.business_h.median(), 2),
                    "calendar_mean_h": r(df.calendar_h.mean(), 2), "business_mean_h": r(df.business_h.mean(), 2),
                    "calendar_minus_business_min_h": r((df.calendar_h - df.business_h).min(), 4) + 0.0}}
    t = by_day(df)
    t.to_csv(RES / "by_weekday.csv", index=False)
    out["by_weekday"] = t.to_dict(orient="records")
    bl_day = bl.groupby("dow").waiting.mean()
    out["backlog_at_open_mean"] = {DAYS[d]: r(v, 1) for d, v in bl_day.items()}
    out["base"]["rankcorr_median_calendar_vs_business"] = r(rank_corr(t.calendar_median_h, t.business_median_h), 3)
    out["base"]["rankcorr_mean_calendar_vs_business"] = r(rank_corr(t.calendar_mean_h, t.business_mean_h), 3)
    # 月曜の内訳：来た時刻で（週末・金曜の夜の分を含めた待ち）
    mon = df[df.dow == 0]
    out["monday"] = {"arrive_before_open_business_median_h": r(mon[mon.hour < OPEN_H].business_h.median(), 2),
                     "arrive_in_hours_business_median_h": r(mon[(mon.hour >= OPEN_H) & (mon.hour < CLOSE_H)].business_h.median(), 2)}
    wed = df[df.dow == 2]
    out["wednesday"] = {"arrive_in_hours_business_median_h": r(wed[(wed.hour >= OPEN_H) & (wed.hour < CLOSE_H)].business_h.median(), 2)}
    pd.DataFrame({"arrive_min": df.arrive_min.round(3), "day": [DAYS[d] for d in df.dow], "hour": df.hour,
                  "calendar_h": df.calendar_h.round(4), "business_h": df.business_h.round(4)})[df.week == PAD].to_csv(
        DATA / "inquiries_first_week.csv", index=False)
    print("base", round(time.time() - T0, 1), flush=True)

    rows = []
    for sc in OFF_SCALES:
        for a in AGENTS:
            d, b, lm = simulate(rng, sc, a)
            tt = by_day(d)
            bs = sum(lm[x, h] for x in range(5) for h in range(OPEN_H, CLOSE_H)) / lm.sum()
            for stat in ["median", "mean"]:
                c, bu = tt[f"calendar_{stat}_h"], tt[f"business_{stat}_h"]
                rows.append({"off_scale": sc, "agents": a, "stat": stat,
                             "business_hours_arrival_share_pct": r(bs * 100, 2),
                             "load_pct": r(lm.sum() * SERVICE_MEAN / (a * 45 * 60) * 100, 1),
                             "slowest_calendar": DAYS[int(np.argmax(c))], "slowest_business": DAYS[int(np.argmax(bu))],
                             "fastest_calendar": DAYS[int(np.argmin(c))], "fastest_business": DAYS[int(np.argmin(bu))],
                             "calendar_max_h": r(c.max(), 2), "business_max_h": r(bu.max(), 2),
                             "monday_rank_calendar": int(tt[f"calendar_{stat}_rank"].iloc[0]),
                             "monday_rank_business": int(tt[f"business_{stat}_rank"].iloc[0]),
                             "rankcorr": r(rank_corr(c, bu), 3),
                             "backlog_monday_open": r(b[b.dow == 0].waiting.mean(), 1),
                             **{f"rank_cal_{DAYS[i]}": int(tt[f"calendar_{stat}_rank"].iloc[i]) for i in range(7)},
                             **{f"rank_bus_{DAYS[i]}": int(tt[f"business_{stat}_rank"].iloc[i]) for i in range(7)}})
        print("grid", sc, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"settings": len(grid),
                   "slowest_differs": int((grid.slowest_calendar != grid.slowest_business).sum()),
                   "slowest_calendar_counts": grid.slowest_calendar.value_counts().to_dict(),
                   "slowest_business_counts": grid.slowest_business.value_counts().to_dict(),
                   "rankcorr_min": grid.rankcorr.min(), "rankcorr_max": grid.rankcorr.max(),
                   "monday_rank_calendar_min": int(grid.monday_rank_calendar.min()),
                   "monday_rank_calendar_max": int(grid.monday_rank_calendar.max()),
                   "monday_rank_business_counts": grid.monday_rank_business.value_counts().sort_index().to_dict(),
                   "slowest_differs_median": int(((grid.stat == "median") & (grid.slowest_calendar != grid.slowest_business)).sum()),
                   "sat_rank_business_median_values": sorted(set(int(v) for v in grid[grid.stat == "median"].rank_bus_土)),
                   "sun_rank_calendar_median_values": sorted(set(int(v) for v in grid[grid.stat == "median"].rank_cal_日)),
                   "mon_rank_calendar_median_values": sorted(set(int(v) for v in grid[grid.stat == "median"].rank_cal_月)),
                   "load_pct_values": sorted(set(grid.load_pct)),
                   "bus_share_values": sorted(set(grid.business_hours_arrival_share_pct))}
    ti = t.set_index("day")
    out["headline"] = {"slowest_calendar_median": t.day[t.calendar_median_rank == 1].iloc[0],
                       "slowest_business_median": t.day[t.business_median_rank == 1].iloc[0],
                       "sat_calendar_median_h": ti.loc["土", "calendar_median_h"],
                       "sat_business_median_h": ti.loc["土", "business_median_h"],
                       "mon_calendar_median_h": ti.loc["月", "calendar_median_h"],
                       "mon_business_median_h": ti.loc["月", "business_median_h"],
                       "mon_calendar_rank": int(ti.loc["月", "calendar_median_rank"]),
                       "sat_business_rank": int(ti.loc["土", "business_median_rank"])}

    # 図1：曜日ごとの中央値（暦・営業）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))
    for ax, col, rk, title, colr in [(axes[0], "calendar_median_h", "calendar_median_rank", "暦の時間で数える", GRAY),
                                     (axes[1], "business_median_h", "business_median_rank", "営業時間で数える", BLUE)]:
        cs = [ORANGE if v == 1 else colr for v in t[rk]]
        ax.bar(range(7), t[col], color=cs)
        for i, v in enumerate(t[col]):
            ax.text(i, v + t[col].max() * 0.02, f"{v:g}", ha="center", fontsize=8)
        ax.set_xticks(range(7))
        ax.set_xticklabels([f"{d}曜" for d in DAYS])
        ax.set_ylim(0, t[col].max() * 1.15)
        ax.set_ylabel("返事までの時間の中央値（時間）")
        ax.set_xlabel("問い合わせが来た曜日")
        ax.set_title(f"{title}（いちばん遅い：{t.day[t[rk] == 1].iloc[0]}曜）", fontsize=11)
    save(fig, "a1187_weekday.png", SRC)

    # 図2：営業の始まりに待っている数
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    v = [bl_day[d] for d in range(5)]
    ax.bar(range(5), v, color=[ORANGE] + [BLUE] * 4)
    for i, x in enumerate(v):
        ax.text(i, x + max(v) * 0.02, f"{x:.1f}", ha="center", fontsize=9)
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"{d}曜 9時" for d in DAYS[:5]])
    ax.set_ylim(0, max(v) * 1.15)
    ax.set_ylabel("返事を書き始めていない問い合わせ（件、52週の平均）")
    ax.set_title("月曜の朝は、週末と金曜の夜の分が待っている")
    save(fig, "a1187_backlog.png", SRC)

    # 図3：9通り（中央値）で、遅い順の順位
    med = grid[grid.stat == "median"].reset_index(drop=True)
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.6), sharey=True)
    labels = [f"外の量×{sc:g}・担当{a}人" for sc, a in zip(med.off_scale, med.agents)]
    for ax, key, title in [(axes[0], "cal", "暦の時間で数える"), (axes[1], "bus", "営業時間で数える")]:
        m = np.array([[med.loc[i, f"rank_{key}_{d}"] for d in DAYS] for i in range(len(med))])
        ax.imshow(m, cmap="Blues_r", vmin=1, vmax=10, aspect="auto")
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                ax.text(j, i, str(m[i, j]), ha="center", va="center", fontsize=9,
                        color=ORANGE if m[i, j] == 1 else ("white" if m[i, j] <= 3 else INK),
                        fontweight="bold" if m[i, j] == 1 else "normal")
        ax.set_xticks(range(7))
        ax.set_xticklabels([f"{d}曜" for d in DAYS])
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("問い合わせが来た曜日")
    axes[0].set_yticks(range(len(labels)))
    axes[0].set_yticklabels(labels, fontsize=8.5)
    fig.suptitle("中央値の遅い順（1＝いちばん遅い）。9通りとも、いちばん遅い曜日は2つの数え方で違う", fontsize=11.5)
    save(fig, "a1187_grid.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1187_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
