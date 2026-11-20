"""881 「最後尾の人の待ち時間」と「平均の待ち時間」の違いは？（架空のデータ）

架空のテーマパークの乗り物1つ。3分ごとに30人ずつ乗る（1時間に600人）。
9時から21時まで、時間帯ごとに決めた割合で客がでたらめに来て、列の最後尾に並ぶ（21時を過ぎても列が空になるまで動かす）。
客ごとの待ち時間（並んでから乗るまで）を出し、次の3つを比べる。
  ・1日の平均の待ち（来た客全員の平均）
  ・最後尾の人の待ち（その時刻に並んだ客が、実際に待った時間）
  ・掲示の出し方2つ：A 直近30分に乗った客の待ちの平均、B 並んでいる人数÷1分に乗れる人数＋1.5分
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 881
SRC = "架空のテーマパークの乗り物（作成者が乱数で作成、seed 881）"
OPEN = 720  # 9時から21時（分）
EVERY = 3.0
RATE_H = np.array([300, 550, 750, 850, 850, 800, 700, 600, 500, 400, 300, 200])  # 1時間に来る人数（9時台〜20時台）
GRID = np.arange(0, OPEN, 1.0)


def clock(m):
    return f"{9 + int(m // 60)}:{int(m % 60):02d}"


def one_day(rng, rate=RATE_H, cap=30, seat_low=None):
    """seat_low を与えると、1便に乗る人数が seat_low〜cap 人で揺れる（掲示Bは cap 人で計算したまま）"""
    arr = np.concatenate([np.sort(rng.uniform(h * 60, (h + 1) * 60, rng.poisson(r))) for h, r in enumerate(rate)])
    n = len(arr)
    board = np.empty(n)
    i, t = 0, EVERY
    while i < n:
        c = cap if seat_low is None else int(rng.integers(seat_low, cap + 1))
        j = min(np.searchsorted(arr, t, side="right"), i + c)
        board[i:j] = t
        i = j
        t += EVERY
    wait = board - arr
    # 最後尾の人の待ち：その時刻以降に最初に並んだ客の待ち
    idx = np.minimum(np.searchsorted(arr, GRID, side="left"), n - 1)
    last = wait[idx]
    # 掲示A：直近30分に乗った客の平均
    cs = np.concatenate([[0], np.cumsum(wait)])
    lo = np.searchsorted(board, GRID - 30, side="right")
    hi = np.searchsorted(board, GRID, side="right")
    cnt = hi - lo
    sign_a = np.where(cnt > 0, (cs[hi] - cs[lo]) / np.maximum(cnt, 1), 0.0)
    # 掲示B：並んでいる人数÷1分に乗れる人数＋1.5分
    in_line = np.searchsorted(arr, GRID, side="right") - hi
    sign_b = in_line / (cap / EVERY) + EVERY / 2
    return dict(arr=arr, board=board, wait=wait, last=last, sign_a=sign_a, sign_b=sign_b, in_line=in_line)


def day_stats(d):
    w, last = d["wait"], d["last"]
    peak_i = int(np.argmax(last))
    grow = np.arange(len(GRID)) < peak_i
    shrink = ~grow
    busy = last >= 10  # 最後尾の待ちが10分以上の時間帯だけで誤差を見る
    ea, eb = d["sign_a"] - last, d["sign_b"] - last
    return {"guests": int(len(w)), "person_mean": float(w.mean()), "person_median": float(np.median(w)),
            "person_p90": float(np.quantile(w, .9)), "time_mean_last": float(last.mean()),
            "peak_last": float(last.max()), "peak_time_min": float(GRID[peak_i]),
            "share_wait_gt_mean": float((w > w.mean()).mean()), "share_wait_gt_2mean": float((w > 2 * w.mean()).mean()),
            "a_err_grow": float(ea[grow & busy].mean()) if (grow & busy).any() else np.nan,
            "a_err_shrink": float(ea[shrink & busy].mean()) if (shrink & busy).any() else np.nan,
            "b_err_grow": float(eb[grow & busy].mean()) if (grow & busy).any() else np.nan,
            "b_err_shrink": float(eb[shrink & busy].mean()) if (shrink & busy).any() else np.nan,
            "a_abs_err": float(np.abs(ea[busy]).mean()) if busy.any() else np.nan,
            "b_abs_err": float(np.abs(eb[busy]).mean()) if busy.any() else np.nan,
            "a_peak": float(d["sign_a"].max()), "a_at_true_peak": float(d["sign_a"][peak_i])}


def main():
    days = []
    store = None
    for r in range(500):
        d = one_day(np.random.default_rng(SEED * 10 + r))
        days.append(day_stats(d))
        if r == 0:
            store = d
    days = pd.DataFrame(days)
    days.to_csv(RES / "days_base.csv", index=False, float_format="%.3f")
    m = days.mean()
    base = {k: round(float(v), 2) for k, v in m.items()}
    base.update({"days": 500, "peak_over_person_mean": round(float((days.peak_last / days.person_mean).mean()), 2),
                 "peak_last_p5": round(float(days.peak_last.quantile(.05)), 1),
                 "peak_last_p95": round(float(days.peak_last.quantile(.95)), 1),
                 "peak_time_median": clock(float(days.peak_time_min.median())),
                 "a_lag_at_peak": round(float((days.peak_last - days.a_at_true_peak).mean()), 2)})

    # 時刻ごとの平均（500日）は重いので、図用に50日分だけ
    lasts, sa, sb = [], [], []
    for r in range(50):
        d = one_day(np.random.default_rng(SEED * 10 + r))
        lasts.append(d["last"]); sa.append(d["sign_a"]); sb.append(d["sign_b"])
    prof = pd.DataFrame({"minute_from_9": GRID.astype(int), "clock": [clock(t) for t in GRID],
                         "last_in_line_wait": np.mean(lasts, 0).round(2), "sign_a_recent30": np.mean(sa, 0).round(2),
                         "sign_b_people": np.mean(sb, 0).round(2)})
    prof.to_csv(RES / "profile_50days.csv", index=False)

    # 1日分のデータ
    d0 = store
    pd.DataFrame({"guest_id": np.arange(1, len(d0["arr"]) + 1), "arrive_min_from_9": d0["arr"].round(3),
                  "arrive_clock": [clock(t) for t in d0["arr"]], "board_min_from_9": d0["board"].round(1),
                  "wait_min": d0["wait"].round(3)}).to_csv(DATA / "day_guests.csv", index=False)
    s0 = day_stats(d0)
    one = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in s0.items()}
    one["peak_time"] = clock(s0["peak_time_min"])

    # 確かめ：来る人数×乗れる人数（各200日）
    sens = []
    for scale in [0.9, 1.0, 1.1]:
        for cap in [27, 30, 33]:
            st = pd.DataFrame([day_stats(one_day(np.random.default_rng(SEED * 1000 + int(scale * 100) * 53 + cap * 7 + r),
                                                 RATE_H * scale, cap)) for r in range(200)])
            sens.append({"arrival_scale": scale, "seats_per_3min": cap, "per_hour": int(cap * 20),
                         "person_mean": round(float(st.person_mean.mean()), 1),
                         "time_mean_last": round(float(st.time_mean_last.mean()), 1),
                         "peak_last": round(float(st.peak_last.mean()), 1),
                         "peak_over_person_mean": round(float((st.peak_last / st.person_mean).mean()), 2),
                         "share_wait_gt_mean": round(float(st.share_wait_gt_mean.mean()), 3),
                         "a_err_grow": round(float(st.a_err_grow.mean()), 1),
                         "a_err_shrink": round(float(st.a_err_shrink.mean()), 1),
                         "b_err_grow": round(float(st.b_err_grow.mean()), 1),
                         "b_err_shrink": round(float(st.b_err_shrink.mean()), 1)})
    # 確かめ：1便に乗る人数が24〜30人で揺れる（平均27人）のに、掲示Bは30人で計算する
    st = pd.DataFrame([day_stats(one_day(np.random.default_rng(SEED * 2000 + r), RATE_H, 30, 24)) for r in range(200)])
    sens.append({"arrival_scale": 1.0, "seats_per_3min": "24〜30（掲示Bは30で計算）", "per_hour": 540,
                 "person_mean": round(float(st.person_mean.mean()), 1),
                 "time_mean_last": round(float(st.time_mean_last.mean()), 1),
                 "peak_last": round(float(st.peak_last.mean()), 1),
                 "peak_over_person_mean": round(float((st.peak_last / st.person_mean).mean()), 2),
                 "share_wait_gt_mean": round(float(st.share_wait_gt_mean.mean()), 3),
                 "a_err_grow": round(float(st.a_err_grow.mean()), 1), "a_err_shrink": round(float(st.a_err_shrink.mean()), 1),
                 "b_err_grow": round(float(st.b_err_grow.mean()), 1), "b_err_shrink": round(float(st.b_err_shrink.mean()), 1)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"base_500days": base, "one_day": one, "rate_per_hour_9_to_20": RATE_H.tolist(),
           "sensitivity": sens.to_dict("records"),
           "sens_range": {"peak_over_person_mean_min": float(sens.peak_over_person_mean.min()),
                          "peak_over_person_mean_max": float(sens.peak_over_person_mean.max()),
                          "a_err_grow_min": float(sens.a_err_grow.min()), "a_err_grow_max": float(sens.a_err_grow.max()),
                          "a_err_shrink_min": float(sens.a_err_shrink.min()), "a_err_shrink_max": float(sens.a_err_shrink.max()),
                          "b_abs_err_grow_max_fixed_seats": float(sens.b_err_grow[:9].abs().max()),
                          "b_abs_err_shrink_max_fixed_seats": float(sens.b_err_shrink[:9].abs().max())}}
    json.dump(out, open(RES / "a881_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1日の動き（50日の平均）
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    ax.plot(GRID, prof.last_in_line_wait, color=INK, lw=2.4, label="最後尾の人の待ち（その時刻に並んだ客が実際に待った時間）")
    ax.plot(GRID, prof.sign_a_recent30, color=ORANGE, lw=1.8, label="掲示A：直近30分に乗った客の待ちの平均")
    ax.plot(GRID, prof.sign_b_people, color=BLUE, lw=1.4, ls="--", label="掲示B：並んでいる人数÷1分に乗れる人数＋1.5分")
    ax.axhline(base["person_mean"], color=GREEN, lw=1.4, ls=":")
    ax.text(5, base["person_mean"] + 2, f"1日の平均 {base['person_mean']:.0f}分（来た客全員）", color=GREEN, fontsize=9)
    ax.set_xticks(np.arange(0, OPEN + 1, 120)); ax.set_xticklabels([clock(t) for t in np.arange(0, OPEN + 1, 120)])
    ax.set_xlabel("並んだ時刻"); ax.set_ylabel("待ち時間（分）"); ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_ylim(0, max(prof.last_in_line_wait.max(), prof.sign_a_recent30.max()) * 1.35)
    ax.set_title("掲示Aは最後尾の待ちより遅れて動く（50日の平均）", fontsize=12.5)
    save(fig, "a881_day_profile.png", SRC)

    # 図2：客の待ちの分布（500日）と、1日の平均・最後尾のいちばん長い待ち
    allw = []
    for r in range(0, 500, 10):
        allw.append(one_day(np.random.default_rng(SEED * 10 + r))["wait"])
    allw = np.concatenate(allw)
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.hist(allw, bins=np.arange(0, allw.max() + 5, 5), weights=np.full(len(allw), 100.0 / len(allw)), color=LIGHT, edgecolor="white")
    ax.axvline(base["person_mean"], color=GREEN, lw=2)
    ax.axvline(base["peak_last"], color=ORANGE, lw=2)
    yl = ax.get_ylim()[1]
    ax.text(base["person_mean"] + 1.5, yl * 0.92, f"1日の平均\n{base['person_mean']:.0f}分", color=GREEN, fontsize=9, va="top")
    ax.text(base["peak_last"] + 1.5, yl * 0.92, f"最後尾のいちばん\n長い待ち {base['peak_last']:.0f}分", color=ORANGE, fontsize=9, va="top")
    ax.set_xlabel("客1人の待ち時間（分、5分ごと）"); ax.set_ylabel("客の割合（%）")
    ax.set_title(f"いちばん混む時刻に並んだ人は、1日の平均の約{base['peak_over_person_mean']:.1f}倍待つ", fontsize=12.5)
    save(fig, "a881_wait_hist.png", SRC)

    # 図3：掲示の誤差（列が伸びる時間と縮む時間、最後尾の待ちが10分以上の時刻）
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    x = np.arange(2)
    ax.bar(x - 0.18, [base["a_err_grow"], base["a_err_shrink"]], 0.36, color=ORANGE, label="掲示A：直近30分の平均")
    ax.bar(x + 0.18, [base["b_err_grow"], base["b_err_shrink"]], 0.36, color=BLUE, label="掲示B：人数から見積もる")
    for i, (va, vb) in enumerate([(base["a_err_grow"], base["b_err_grow"]), (base["a_err_shrink"], base["b_err_shrink"])]):
        ax.text(i - 0.18, va + (1 if va >= 0 else -1), f"{va:+.1f}分".replace("-", "−"), ha="center", va="bottom" if va >= 0 else "top", fontsize=9)
        ax.text(i + 0.18, vb + (1 if vb >= 0 else -1), f"{vb:+.1f}分".replace("-", "−"), ha="center", va="bottom" if vb >= 0 else "top", fontsize=9)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(x); ax.set_xticklabels(["列が伸びている時間\n（最後尾の待ちがいちばん長くなる前）", "列が縮んでいる時間\n（その後）"])
    ax.set_ylabel("掲示−最後尾の人の実際の待ち（分）")
    lo_, hi_ = min(base["a_err_grow"], base["b_err_grow"]), max(base["a_err_shrink"], base["b_err_shrink"])
    ax.set_ylim(min(lo_ * 1.4, -3), max(hi_ * 1.4, 3))
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("直近の平均は、伸びるときは短く、縮むときは長く出る（500日の平均）", fontsize=12)
    save(fig, "a881_sign_error.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
