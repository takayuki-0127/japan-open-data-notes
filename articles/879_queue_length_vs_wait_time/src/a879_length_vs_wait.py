"""879 行列の長さと、待ち時間の長さは同じなのか？（架空のデータ）

A：性格の違う3つの列（レジ3台・手続きの窓口1つ・30人ずつ乗る乗り物）を、同じ混み具合で長く動かし、
   「来たときに前に何人いたか」と「実際に待った時間」を比べる。
B：架空の店のレジの1日（10〜20時、時間帯ごとに来る人数と開けるレジの台数が変わる）を作り、
   時間帯ごとの「並んでいる人数の平均」と「待ち時間の平均」の順位がどれだけ合うかを数える。
待ち時間＝来てから自分の番（レジ・窓口・乗り物）が始まるまで。並んでいる人数は、会計中・手続き中の人を含まない。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 879
SRC = "架空の店・窓口・乗り物の列（作成者が乱数で作成、seed 879）"
T0 = time.time()

# ---- B の1日の置き方 ----
HOURS = list(range(10, 20))
LAM_H = np.array([40, 80, 220, 180, 48, 48, 50, 90, 160, 40])  # 1時間に来る人数（平均）
REGS = np.array([1, 2, 4, 4, 1, 1, 1, 2, 3, 1])                  # 開けているレジの台数
SVC_MEAN, SVC_CV = 1.0, 0.7                                      # 1人の会計の時間（分）


def gamma_svc(rng, n, mean, cv):
    if cv == 0:
        return np.full(n, mean)
    k = 1 / cv ** 2
    return rng.gamma(k, mean / k, n)


def poisson_arrivals(rng, lam_per_min_by_hour):
    """時間帯ごとに一定の割合で来る（ポアソン到着）。分単位の時刻を返す"""
    out = []
    for h, lam in enumerate(lam_per_min_by_hour):
        n = rng.poisson(lam * 60)
        out.append(np.sort(rng.uniform(h * 60, (h + 1) * 60, n)))
    return np.concatenate(out)


def fifo_schedule(arr, svc, regs_by_hour):
    """来た順に、空いて開いているレジへ。レジの台数は時間帯ごとに変わる（閉めるレジは会計中の人を終えてから閉める）"""
    cmax = int(max(regs_by_hour))
    free = np.zeros(cmax)
    last = len(regs_by_hour) - 1
    start = np.empty(len(arr))
    for i, (a, s) in enumerate(zip(arr, svc)):
        best, bk = np.inf, -1
        for k in range(cmax):
            t = max(a, free[k])
            h = min(int(t // 60), last)
            if regs_by_hour[h] <= k:
                nxt = [h2 for h2 in range(h + 1, last + 1) if regs_by_hour[h2] > k]
                if not nxt:
                    continue
                t = nxt[0] * 60.0
            if t < best:
                best, bk = t, k
        start[i] = best
        free[bk] = best + s
    return start


def n_ahead(arr, start):
    """来たときに前で並んでいた人数（会計中の人は含まない）。来た順＝始まる順なので数えで出せる"""
    a_before = np.arange(len(arr))  # 自分より前に来た人数
    started = np.searchsorted(start, arr, side="right")  # 自分が来た時点までに始まった人数
    return a_before - np.minimum(started, a_before)


def waiting_count_grid(arr, start, grid):
    return np.searchsorted(arr, grid, side="right") - np.searchsorted(start, grid, side="right")


def one_day(rng, lam_h=LAM_H, regs=REGS, mean=SVC_MEAN, cv=SVC_CV):
    arr = poisson_arrivals(rng, lam_h / 60)
    svc = gamma_svc(rng, len(arr), mean, cv)
    start = fifo_schedule(arr, svc, regs)
    wait = start - arr
    grid = np.arange(0, 600, 0.25) + 0.125
    q = waiting_count_grid(arr, start, grid)
    hour = (arr // 60).astype(int)
    L = q.reshape(10, -1).mean(1)
    W = np.array([wait[hour == h].mean() if (hour == h).any() else np.nan for h in range(10)])
    lam_obs = np.bincount(hour, minlength=10) / 60
    return dict(arr=arr, svc=svc, start=start, wait=wait, hour=hour, L=L, W=W, lam=lam_obs)


def spearman(x, y):
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    return float(np.corrcoef(rx, ry)[0, 1])


def day_stats(d):
    return {"rank_corr": round(spearman(d["L"], d["W"]), 3),
            "longest_line_hour": HOURS[int(np.argmax(d["L"]))],
            "longest_wait_hour": HOURS[int(np.argmax(d["W"]))]}


# ---- A：3つの列 ----
def line_register(rng, minutes=600):
    lam = 2.5  # 毎分
    n = rng.poisson(lam * minutes)
    arr = np.sort(rng.uniform(0, minutes, n))
    svc = gamma_svc(rng, n, 1.0, 0.7)
    start = fifo_schedule(arr, svc, [3] * 10)
    return arr, start, lam


def line_window(rng, minutes=600):
    lam = 0.17  # 毎分（1時間に約10人）
    n = rng.poisson(lam * minutes)
    arr = np.sort(rng.uniform(0, minutes, n))
    svc = gamma_svc(rng, n, 5.0, 0.7)
    start = fifo_schedule(arr, svc, [1] * 10)
    return arr, start, lam


def line_ride(rng, minutes=600, every=3.0, cap=30):
    lam = 9.0  # 毎分
    n = rng.poisson(lam * minutes)
    arr = np.sort(rng.uniform(0, minutes, n))
    start = np.empty(n)
    i, t = 0, every
    while i < n:
        j = min(np.searchsorted(arr, t, side="right"), i + cap)
        start[i:j] = t
        i = j
        t += every
    return arr, start, lam


LINES = [("レジ（3台・1人平均1分）", line_register, 1.0 / 3),
         ("手続きの窓口（1つ・1人平均5分）", line_window, 5.0),
         ("乗り物（3分ごとに30人）", line_ride, 0.1)]


def run_lines(reps=120):
    rows, pts = [], {}
    for li, (name, fn, per) in enumerate(LINES):
        W, N, Ls, lam_list = [], [], [], []
        for r in range(reps):
            rng = np.random.default_rng(SEED * 100 + li * 1000 + r)
            arr, start, lam = fn(rng)
            keep = (arr >= 60) & (arr < 540)  # 始めと終わりの1時間を除く
            w = (start - arr)[keep]
            n = n_ahead(arr, start)[keep]
            grid = np.arange(60, 540, 0.25) + 0.125
            Ls.append(waiting_count_grid(arr, start, grid).mean())
            lam_list.append(keep.sum() / 480)
            W.append(w); N.append(n)
        W, N = np.concatenate(W), np.concatenate(N)
        slope = float(np.polyfit(N, W, 1)[0]) if li < 2 else None  # 乗り物は30人までが同じ便なので直線で測らない
        at10 = W[N == 10]
        rows.append({"line": name, "mean_people_waiting": round(float(np.mean(Ls)), 2),
                     "mean_wait_min": round(float(W.mean()), 2),
                     "arrivals_per_min": round(float(np.mean(lam_list)), 3),
                     "little_L_over_lambda": round(float(np.mean(Ls) / np.mean(lam_list)), 2),
                     "slope_min_per_person": round(slope, 3) if slope is not None else None, "theory_min_per_person": round(per, 3),
                     "n_cases_10_ahead": int(len(at10)),
                     "wait_10_ahead_median": round(float(np.median(at10)), 2),
                     "wait_10_ahead_p10": round(float(np.quantile(at10, .1)), 2),
                     "wait_10_ahead_p90": round(float(np.quantile(at10, .9)), 2)})
        # 図用に間引く
        idx = np.random.default_rng(SEED + li).choice(len(W), min(3000, len(W)), replace=False)
        pts[name] = (N[idx], W[idx])
    return pd.DataFrame(rows), pts


def main():
    # ---- A ----
    lines, pts = run_lines()
    lines.to_csv(RES / "three_lines.csv", index=False)

    # ---- B：基本の置き方で300日 ----
    days, Ls, Ws = [], [], []
    for r in range(300):
        d = one_day(np.random.default_rng(SEED * 10 + r))
        days.append(day_stats(d)); Ls.append(d["L"]); Ws.append(d["W"])
    days = pd.DataFrame(days)
    Ls, Ws = np.array(Ls), np.array(Ws)
    by_hour = pd.DataFrame({"hour": [f"{h}時台" for h in HOURS], "arrivals_per_hour": LAM_H, "registers": REGS,
                            "utilization": np.round(LAM_H * SVC_MEAN / 60 / REGS, 3),
                            "mean_people_waiting": Ls.mean(0).round(2), "mean_wait_min": Ws.mean(0).round(2),
                            "L_over_lambda_min": (Ls.mean(0) / (LAM_H / 60)).round(2)})
    by_hour["rank_by_line"] = by_hour.mean_people_waiting.rank(ascending=False).astype(int)
    by_hour["rank_by_wait"] = by_hour.mean_wait_min.rank(ascending=False).astype(int)
    by_hour.to_csv(RES / "by_hour_300days.csv", index=False)
    rank_corr_avg = spearman(by_hour.mean_people_waiting, by_hour.mean_wait_min)
    days.to_csv(RES / "days_base.csv", index=False)
    base = {"days": 300, "rank_corr_of_300day_average": round(rank_corr_avg, 3), "rank_corr_mean": round(float(days.rank_corr.mean()), 3),
            "rank_corr_p5": round(float(days.rank_corr.quantile(.05)), 3),
            "rank_corr_p95": round(float(days.rank_corr.quantile(.95)), 3),
            "share_days_longest_line_ne_longest_wait": round(float((days.longest_line_hour != days.longest_wait_hour).mean()), 3),
            "longest_line_hour_mode": int(days.longest_line_hour.mode()[0]),
            "longest_wait_hour_mode": int(days.longest_wait_hour.mode()[0]),
            "share_longest_line_is_12": round(float((days.longest_line_hour == 12).mean()), 3),
            "share_longest_wait_is_16": round(float((days.longest_wait_hour == 16).mean()), 3),
            "share_longest_line_in_12_13": round(float(days.longest_line_hour.isin([12, 13]).mean()), 3),
            "share_longest_wait_in_14_16": round(float(days.longest_wait_hour.isin([14, 15, 16]).mean()), 3)}

    # 1日分（data）
    d0 = one_day(np.random.default_rng(SEED))
    nah = n_ahead(d0["arr"], d0["start"])
    pd.DataFrame({"customer_id": np.arange(1, len(d0["arr"]) + 1), "arrive_min": d0["arr"].round(3),
                  "hour": [HOURS[h] for h in d0["hour"]], "people_ahead": nah, "service_min": d0["svc"].round(3),
                  "start_min": d0["start"].round(3), "wait_min": d0["wait"].round(3)}).to_csv(
        DATA / "day_customers.csv", index=False)
    one = {"customers": int(len(d0["arr"])), **day_stats(d0),
           "L_by_hour": [round(float(x), 2) for x in d0["L"]], "W_by_hour": [round(float(x), 2) for x in d0["W"]]}

    # ---- B の確かめ：会計の時間の平均×ばらつき、午後のレジの台数 ----
    sens = []
    for scale in [0.9, 1.0, 1.05]:
        for cv in [0.3, 0.7, 1.0]:
            for pm in [1, 2]:
                regs = REGS.copy()
                if pm == 2:
                    regs[[4, 5, 6]] = 2
                lam = LAM_H * scale
                mean = SVC_MEAN
                st, LL, WW = [], [], []
                for r in range(100):
                    d = one_day(np.random.default_rng(SEED * 7 + int(scale * 100) * 31 + int(cv * 10) * 7 + pm * 3 + r * 1000),
                                lam, regs, mean, cv)
                    st.append(day_stats(d)); LL.append(d["L"]); WW.append(d["W"])
                st = pd.DataFrame(st)
                LL, WW = np.array(LL).mean(0), np.array(WW).mean(0)
                sens.append({"arrival_scale": scale, "svc_cv": cv, "afternoon_regs": pm,
                             "rank_corr_mean": round(float(st.rank_corr.mean()), 3),
                             "share_days_longest_line_ne_longest_wait": round(
                                 float((st.longest_line_hour != st.longest_wait_hour).mean()), 3),
                             "avg_longest_line_hour": HOURS[int(np.argmax(LL))],
                             "avg_longest_wait_hour": HOURS[int(np.argmax(WW))],
                             "lunch12_people": round(float(LL[2]), 2), "lunch12_wait": round(float(WW[2]), 2),
                             "pm16_people": round(float(LL[6]), 2), "pm16_wait": round(float(WW[6]), 2),
                             "lunch_longer_line_than_pm16": bool(LL[2] > LL[6]),
                             "lunch_shorter_wait_than_pm16": bool(WW[2] < WW[6])})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_day.csv", index=False)

    out = {"three_lines": lines.to_dict("records"),
           "little_max_gap_min": round(float((lines.mean_wait_min - lines.little_L_over_lambda).abs().max()), 2), "day_base_300": base,
           "by_hour_300days": by_hour.to_dict("records"), "one_day": one,
           "sensitivity_day": {"settings": int(len(sens)),
                               "rank_corr_min": float(sens.rank_corr_mean.min()),
                               "rank_corr_max": float(sens.rank_corr_mean.max()),
                               "flip_share_min": float(sens.share_days_longest_line_ne_longest_wait.min()),
                               "flip_share_max": float(sens.share_days_longest_line_ne_longest_wait.max()),
                               "pm1_flip_min": float(sens[sens.afternoon_regs == 1].share_days_longest_line_ne_longest_wait.min()),
                               "pm1_flip_max": float(sens[sens.afternoon_regs == 1].share_days_longest_line_ne_longest_wait.max()),
                               "pm2_flip_min": float(sens[sens.afternoon_regs == 2].share_days_longest_line_ne_longest_wait.min()),
                               "pm2_flip_max": float(sens[sens.afternoon_regs == 2].share_days_longest_line_ne_longest_wait.max()),
                               "pm1_settings_lunch_longer_line_and_shorter_wait": int(
                                   (sens[sens.afternoon_regs == 1].lunch_longer_line_than_pm16
                                    & sens[sens.afternoon_regs == 1].lunch_shorter_wait_than_pm16).sum()),
                               "pm2_settings_lunch_longer_line_and_shorter_wait": int(
                                   (sens[sens.afternoon_regs == 2].lunch_longer_line_than_pm16
                                    & sens[sens.afternoon_regs == 2].lunch_shorter_wait_than_pm16).sum())}}
    json.dump(out, open(RES / "a879_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：前に並んでいた人数と待ち時間（3つの列）
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), sharey=False)
    for ax, (name, _, _), col in zip(axes, LINES, [BLUE, ORANGE, GREEN]):
        n, w = pts[name]
        ax.scatter(n, w, s=5, color=col, alpha=.3, lw=0)
        row = lines[lines.line == name].iloc[0]
        ax.axvline(10, color=GRAY, lw=.8, ls="--")
        ax.set_title(name, fontsize=10.5)
        ax.set_xlabel("来たとき前に並んでいた人数")
        per = (f"1人あたり約{row.slope_min_per_person:.2f}分" if row.slope_min_per_person == row.slope_min_per_person
               and row.slope_min_per_person is not None else "30人までは次の便（3分以内）")
        ax.text(0.03, 0.95, f"前に10人：待ち{row.wait_10_ahead_median:.1f}分（中央値）\n{per}",
                transform=ax.transAxes, va="top", fontsize=8.5, color=INK)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("実際に待った時間（分）")
    w10 = lines.wait_10_ahead_median
    fig.suptitle(f"同じ「前に10人」でも、待ち時間（中央値）は{w10.min():.1f}分から{w10.max():.0f}分まで列の性格で変わる",
                 fontsize=13, y=1.02)
    save(fig, "a879_three_lines.png", SRC)

    # 図2：時間帯ごとの並んでいる人数と待ち時間
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
    x = np.arange(10)
    lab = [f"{h}\n{rg}台" for h, rg in zip(HOURS, REGS)]
    c1 = [ORANGE if h == 12 else LIGHT for h in HOURS]
    c2 = [ORANGE if h == 12 else BLUE for h in HOURS]
    axes[0].bar(x, by_hour.mean_people_waiting, color=c1)
    axes[0].set_title("並んでいる人数の平均（人）", fontsize=11)
    axes[1].bar(x, by_hour.mean_wait_min, color=c2)
    axes[1].set_title("待ち時間の平均（分）", fontsize=11)
    for ax in axes:
        ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=9); ax.set_xlabel("時台（下の段は開けているレジの台数）")
    r12 = by_hour.iloc[2]
    fig.suptitle(f"12時台（橙）は並ぶ人数が{'いちばん' if r12.rank_by_line == 1 else str(r12.rank_by_line) + '番目に'}多いのに、待ち時間は10の時間帯で{r12.rank_by_wait}番目"
                 "（架空の店のレジ、300日の平均）", fontsize=12, y=1.02)
    save(fig, "a879_by_hour.png", SRC, y=-0.07)

    # 図3：リトルの法則（並んでいる人数÷1分に来る人数＝待ち時間）
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    one_reg = by_hour.registers == 1
    ax.scatter(by_hour.mean_people_waiting[one_reg], by_hour.mean_wait_min[one_reg], s=40, color=ORANGE, label="レジ1台の時間帯")
    ax.scatter(by_hour.mean_people_waiting[~one_reg], by_hour.mean_wait_min[~one_reg], s=40, color=BLUE, label="レジ2〜4台の時間帯")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    for _, r in by_hour.iterrows():
        ax.annotate(f"{r.hour}（{r.registers}台）", (r.mean_people_waiting, r.mean_wait_min), fontsize=8,
                    xytext=(4, 3), textcoords="offset points", color=INK)
    ax.set_xlabel("並んでいる人数の平均（人）"); ax.set_ylabel("待ち時間の平均（分）")
    ax.set_xlim(left=0); ax.set_ylim(bottom=0)
    ax.set_title("レジ1台の時間帯は、並ぶ人数が少なくても待ちが長い（300日の平均）", fontsize=12)
    save(fig, "a879_scatter_hours.png", SRC)

    out["run_sec"] = round(time.time() - T0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
