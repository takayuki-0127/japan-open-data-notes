"""1190 自動の受付返信を「初めの返事」に数えると、初めの返事までの時間はどれだけ縮んで見えるのか？（架空のデータ）

作成者が置いた架空の会社の窓口。問い合わせは「フォーム」（届くとすぐ自動の受付返信が出る。0.5〜3分）と
「メール」（自動の受付返信なし）の2つの入口から来る。フォームの割合 s（基本0.6）。
窓口は平日9〜18時だけ開く。担当の返事は、届いた時刻（窓口が閉まっていれば次に開く時刻）から、
窓口が開いている時間で数えて W 分あと（W の平均は基本180分、標準偏差は平均の0.82倍で右に長い）。入口で W は変えない。
届く時刻の重み：平日9〜18時 3、平日7〜9時・18〜23時 1.2、平日23〜7時 0.3、土日8〜22時 0.8、土日22〜8時 0.2
（窓口が閉まっている時間の重みに m を掛ける。基本 m=1）。
初めの返事までの時間（暦の時間）を、(a) 担当の返事だけで数える、(b) 自動の受付返信も数える（早いほう）の2通りで比べる。
(1) 基本：4週間に20,000件
(2) 6か月の動き：フォームの割合が40%から80%に増え、担当の W の平均が180分から207分（1.15倍）に延びる。各月5,000件×50回
(3) 確かめ1：s（0.2・0.4・0.5・0.6・0.8）×W の平均（60・180・480分）×m（0.5・1・2）＝45通り（各20,000件）
(4) 確かめ2：はじめのフォームの割合（0.2・0.4）×6か月での増え（0.1・0.2・0.4ポイント）×担当の遅れ（なし・1.15倍・1.3倍）
    ×W の平均（60・180・480分）＝54通り（6か月目と1か月目の差、各月5,000件×20回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1190
SRC = "架空の会社の問い合わせ窓口（作成者が置いた届く時刻・入口・担当の返事までの時間からの乱数、seed 1190）"
DAYS = 28
HORIZON = 60 * 24 * (DAYS + 21)
SHAPE = 1.5
T0 = time.time()

minute = np.arange(HORIZON)
dow = (minute // 1440) % 7          # 0=月曜
hod = (minute % 1440) / 60
weekday = dow < 5
OPEN = weekday & (hod >= 9) & (hod < 18)
CUM = np.concatenate([[0], np.cumsum(OPEN)])      # CUM[t]＝t分までに開いていた分数


def arrival_weights(m):
    w = np.where(weekday, np.where((hod >= 9) & (hod < 18), 3.0,
                                   np.where(((hod >= 7) & (hod < 9)) | ((hod >= 18) & (hod < 23)), 1.2, 0.3)),
                 np.where((hod >= 8) & (hod < 22), 0.8, 0.2))
    w = np.where(OPEN, w, w * m)[:DAYS * 1440]
    return w / w.sum()


W_CACHE = {}


def arrivals(rng, n, m):
    if m not in W_CACHE:
        W_CACHE[m] = arrival_weights(m)
    p = W_CACHE[m]
    t = rng.choice(DAYS * 1440, size=n, p=p) + rng.random(n)
    return t


def simulate(rng, n, s, w_mean, m):
    t = arrivals(rng, n, m)
    form = rng.random(n) < s
    W = rng.gamma(SHAPE, w_mean / SHAPE, size=n)
    b0 = CUM[np.floor(t).astype(int)] + OPEN[np.floor(t).astype(int)] * (t - np.floor(t))
    target = b0 + W
    idx = np.searchsorted(CUM, target, side="left")          # CUM[idx] >= target となる最初の分
    human = (idx - 1 + (target - CUM[idx - 1])) - t           # 分
    human = np.maximum(human, 0)
    auto = np.where(form, rng.uniform(0.5, 3.0, size=n), np.inf)
    first = np.minimum(human, auto)
    off = ~OPEN[np.floor(t).astype(int)]
    return t, form, human / 60, first / 60, off


def stats(h):
    return {"mean_h": h.mean(), "median_h": np.median(h), "p90_h": np.quantile(h, 0.9),
            "within_1h": (h <= 1).mean(), "within_24h": (h <= 24).mean()}


def r(x, d=4):
    return round(float(x), d)


def main():
    rng = np.random.default_rng(SEED)
    # (1) 基本
    t, form, hum, fst, off = simulate(rng, 20000, 0.6, 180, 1)
    a, b = stats(hum), stats(fst)
    base = pd.DataFrame([{"count_as": "(a)担当の返事だけ", **{k: r(v) for k, v in a.items()}},
                         {"count_as": "(b)自動の受付返信も数える", **{k: r(v) for k, v in b.items()}}])
    base.to_csv(RES / "base.csv", index=False)
    by_channel = pd.DataFrame([{"channel": "フォーム", "n": int(form.sum()), **{k: r(v) for k, v in stats(hum[form]).items()}},
                               {"channel": "メール", "n": int((~form).sum()), **{k: r(v) for k, v in stats(hum[~form]).items()}}])
    off_share = off.mean()

    # 例の1か月分（基本の置き方の最初の2,000件を時刻順に）
    ex = pd.DataFrame({"arrival_day": (t // 1440).astype(int) + 1, "arrival_weekday": np.array(list("月火水木金土日"))[((t // 1440) % 7).astype(int)],
                       "arrival_time": [f"{int(x % 1440 // 60):02d}:{int(x % 60):02d}" for x in t],
                       "channel": np.where(form, "フォーム", "メール"), "human_reply_h": np.round(hum, 3),
                       "first_reply_with_auto_h": np.round(fst, 3)})
    ex = ex.iloc[:2000].assign(_t=t[:2000]).sort_values("_t").drop(columns="_t")
    ex.insert(0, "inquiry_id", np.arange(1, len(ex) + 1))
    ex.to_csv(DATA / "inquiries_example.csv", index=False)

    # (2) 6か月の動き
    shares = np.linspace(0.4, 0.8, 6)
    slow = np.linspace(1.0, 1.15, 6)
    rows = []
    for rep in range(50):
        for i, (s, f) in enumerate(zip(shares, slow)):
            _, _, h, fs, _ = simulate(rng, 5000, s, 180 * f, 1)
            rows.append({"rep": rep, "month": i + 1, **{f"a_{k}": v for k, v in stats(h).items()}, **{f"b_{k}": v for k, v in stats(fs).items()}})
    mon = pd.DataFrame(rows)
    mt = mon.groupby("month").mean().drop(columns="rep").reset_index()
    mt.insert(1, "form_share", shares.round(2))
    mt.insert(2, "human_time_factor", slow.round(3))
    mt = mt.round(4)
    mt.to_csv(RES / "six_months.csv", index=False)
    # 1か月目→6か月目で、(b) の中央値が下がった回の割合（50回）
    piv = mon.pivot(index="rep", columns="month")
    b_med_down = (piv[("b_median_h", 6)] < piv[("b_median_h", 1)]).mean()
    a_med_up = (piv[("a_median_h", 6)] > piv[("a_median_h", 1)]).mean()
    b_mean_down = (piv[("b_mean_h", 6)] < piv[("b_mean_h", 1)]).mean()

    # (3) 確かめ1：45通り
    rows = []
    for s in [0.2, 0.4, 0.5, 0.6, 0.8]:
        for wm in [60, 180, 480]:
            for m in [0.5, 1, 2]:
                _, _, h, fs, of = simulate(rng, 20000, s, wm, m)
                sa, sb = stats(h), stats(fs)
                rows.append({"form_share": s, "w_mean_min": wm, "offhours_weight": m, "offhours_share": r(of.mean()),
                             **{f"a_{k}": r(v) for k, v in sa.items()}, **{f"b_{k}": r(v) for k, v in sb.items()},
                             "mean_ratio_b_over_a": r(sb["mean_h"] / sa["mean_h"]),
                             "median_ratio_b_over_a": r(sb["median_h"] / sa["median_h"]),
                             "p90_ratio_b_over_a": r(sb["p90_h"] / sa["p90_h"]),
                             "within24_gain_pt": r((sb["within_24h"] - sa["within_24h"]) * 100, 2),
                             "mean_formula_ratio": r(1 - s), })
    g1 = pd.DataFrame(rows)
    g1.to_csv(RES / "grid_static.csv", index=False)

    # (4) 確かめ2：54通り
    rows = []
    for s0 in [0.2, 0.4]:
        for ds in [0.1, 0.2, 0.4]:
            for sl in [1.0, 1.15, 1.3]:
                for wm in [60, 180, 480]:
                    acc = []
                    for rep in range(20):
                        _, _, h1, f1, _ = simulate(rng, 5000, s0, wm, 1)
                        _, _, h6, f6, _ = simulate(rng, 5000, s0 + ds, wm * sl, 1)
                        a1, b1, a6, b6 = stats(h1), stats(f1), stats(h6), stats(f6)
                        acc.append({f"{x}_{k}": (d6[k] - d1[k]) for x, d1, d6 in [("a", a1, a6), ("b", b1, b6)] for k in a1})
                    d = pd.DataFrame(acc).mean()
                    rows.append({"form_share_start": s0, "form_share_up": ds, "human_slowdown": sl, "w_mean_min": wm,
                                 **{f"change_{k}": r(v) for k, v in d.items()}})
    g2 = pd.DataFrame(rows)
    g2.to_csv(RES / "grid_trend.csv", index=False)

    slow2 = g2[g2.human_slowdown > 1]
    robust = {
        "static_n": int(len(g1)),
        "mean_ratio_min": r(g1.mean_ratio_b_over_a.min()), "mean_ratio_max": r(g1.mean_ratio_b_over_a.max()),
        "mean_ratio_minus_formula_maxabs": r((g1.mean_ratio_b_over_a - g1.mean_formula_ratio).abs().max()),
        "median_ratio_by_share": g1.groupby("form_share").median_ratio_b_over_a.agg(["min", "max"]).round(4).reset_index().to_dict("records"),
        "p90_ratio_by_share": g1.groupby("form_share").p90_ratio_b_over_a.agg(["min", "max"]).round(4).reset_index().to_dict("records"),
        "within24_gain_by_w": g1.groupby("w_mean_min").within24_gain_pt.agg(["min", "max"]).round(2).reset_index().to_dict("records"),
        "offhours_share_by_m": g1.groupby("offhours_weight").offhours_share.mean().round(4).to_dict(),
        "a_median_range_h": [r(g1.a_median_h.min()), r(g1.a_median_h.max())],
        "trend_n": int(len(g2)), "trend_slow_n": int(len(slow2)),
        "trend_slow_a_mean_up_b_mean_down": int(((slow2.change_a_mean_h > 0) & (slow2.change_b_mean_h < 0)).sum()),
        "trend_slow_a_median_up_b_median_down": int(((slow2.change_a_median_h > 0) & (slow2.change_b_median_h < 0)).sum()),
        "trend_slow_a_p90_up_b_p90_down": int(((slow2.change_a_p90_h > 0) & (slow2.change_b_p90_h < 0)).sum()),
        "trend_slow_a_24h_down_b_24h_up": int(((slow2.change_a_within_24h < 0) & (slow2.change_b_within_24h > 0)).sum()),
        "trend_slow_b_mean_down": int((slow2.change_b_mean_h < 0).sum()),
        "trend_noslow_a_mean_change_maxabs": r(g2[g2.human_slowdown == 1].change_a_mean_h.abs().max()),
        "trend_noslow_b_mean_change_min": r(g2[g2.human_slowdown == 1].change_b_mean_h.min()),
        "trend_noslow_b_mean_change_max": r(g2[g2.human_slowdown == 1].change_b_mean_h.max()),
    }
    robust["offhours_share_by_m"] = {str(k): v for k, v in robust["offhours_share_by_m"].items()}
    m1, m6 = mt.iloc[0], mt.iloc[-1]
    headline = {
        "offhours_share": r(off_share),
        "a_mean_h": r(a["mean_h"]), "b_mean_h": r(b["mean_h"]), "a_median_h": r(a["median_h"]), "b_median_h": r(b["median_h"]), "b_median_min": r(b["median_h"] * 60, 2),
        "a_p90_h": r(a["p90_h"]), "b_p90_h": r(b["p90_h"]),
        "a_within_1h": r(a["within_1h"]), "b_within_1h": r(b["within_1h"]),
        "a_within_24h": r(a["within_24h"]), "b_within_24h": r(b["within_24h"]),
        "mean_ratio": r(b["mean_h"] / a["mean_h"]), "median_ratio": r(b["median_h"] / a["median_h"]), "p90_ratio": r(b["p90_h"] / a["p90_h"]),
        "m1_a_median_h": m1.a_median_h, "m6_a_median_h": m6.a_median_h, "m1_b_median_h": m1.b_median_h, "m6_b_median_h": m6.b_median_h, "m6_b_median_min": r(m6.b_median_h * 60, 2),
        "m1_a_mean_h": m1.a_mean_h, "m6_a_mean_h": m6.a_mean_h, "m1_b_mean_h": m1.b_mean_h, "m6_b_mean_h": m6.b_mean_h,
        "m1_b_within_24h": m1.b_within_24h, "m6_b_within_24h": m6.b_within_24h, "m1_a_within_24h": m1.a_within_24h, "m6_a_within_24h": m6.a_within_24h,
        "six_month_b_median_down_reps": r(b_med_down), "six_month_a_median_up_reps": r(a_med_up), "six_month_b_mean_down_reps": r(b_mean_down),
    }
    out = {"settings": {"days": DAYS, "business_hours": "平日9〜18時", "form_share": 0.6, "w_mean_min": 180, "w_sd_over_mean": r(1 / np.sqrt(SHAPE)),
                        "auto_reply_min": [0.5, 3.0], "offhours_weight": 1, "base_n": 20000, "six_month_n": 5000, "six_month_reps": 50, "seed": SEED},
           "headline": headline, "base_by_channel_human": by_channel.to_dict("records"), "robust": robust}
    with open(RES / "a1190_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：基本の分布（累積）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    xs = np.sort(hum); ys = np.arange(1, len(xs) + 1) / len(xs) * 100
    ax.plot(xs, ys, color=INK, label="(a) 担当の返事だけ")
    xs2 = np.sort(fst)
    ax.plot(xs2, ys, color=ORANGE, label="(b) 自動の受付返信も数える")
    ax.axvline(24, color=GRAY, lw=0.8, ls=":")
    ax.text(24.5, 5, "24時間", fontsize=8.5, color=GRAY)
    ax.set_xlim(0, np.quantile(hum, 0.99))
    ax.set_ylim(0, 100)
    ax.set_xlabel("届いてから初めの返事までの時間（暦の時間、時間）")
    ax.set_ylabel("この時間までに返事が出た割合（%）")
    ax.set_title(f"フォーム60%の窓口：中央値は(a){r(a['median_h'])}時間、(b){r(b['median_h'])}時間")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1190_cdf.png", SRC)

    # 図2：6か月
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
    xm = mt.month
    for ax, col, ttl in [(axs[0], "median_h", "中央値"), (axs[1], "mean_h", "平均")]:
        ax.plot(xm, mt[f"a_{col}"], marker="o", color=INK, label="(a) 担当の返事だけ")
        ax.plot(xm, mt[f"b_{col}"], marker="s", color=ORANGE, label="(b) 自動の受付返信も数える")
        ax.set_ylim(0, max(mt[f"a_{col}"].max(), mt[f"b_{col}"].max()) * 1.2)
        ax.set_xticks(xm, [f"{int(mm)}か月目\n{int(round(s * 100))}%" for mm, s in zip(xm, mt.form_share)], fontsize=7.5)
        ax.set_ylabel(f"初めの返事までの時間の{ttl}（時間）")
    axs[0].legend(frameon=False, fontsize=8, loc="center left")
    fig.suptitle("フォームの割合が40→80%に増え、担当は1.15倍遅くなった6か月（50回の平均）", fontsize=11.5, y=1.02)
    fig.text(0.5, -0.04, "下の段の%はフォームの割合", ha="center", fontsize=8.5)
    save(fig, "a1190_six_months.png", SRC, y=-0.08)

    # 図3：45通りの比
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    sh = [0.2, 0.4, 0.5, 0.6, 0.8]
    for i, (col, lab, cl) in enumerate([("mean_ratio_b_over_a", "平均", BLUE), ("median_ratio_b_over_a", "中央値", ORANGE), ("p90_ratio_b_over_a", "90%点", GREEN)]):
        for j, s in enumerate(sh):
            v = g1[g1.form_share == s][col].values
            xx = j + (i - 1) * 0.25 + np.linspace(-0.07, 0.07, len(v))
            ax.scatter(xx, v, s=12, color=cl, alpha=0.85, label=lab if j == 0 else None)
    ax.plot(range(5), [1 - s for s in sh], color=INK, lw=0.8, ls="--", label="平均の式どおりの値（1−フォームの割合）")
    ax.set_xticks(range(5), [f"{int(s * 100)}%" for s in sh])
    ax.set_xlabel("フォーム（自動の受付返信あり）の割合")
    ax.set_ylabel("(b)÷(a)")
    ax.set_ylim(0, 1.05)
    ax.set_title("45通りの置き方：自動の受付返信も数えると何倍に縮むか")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1190_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), json.dumps(robust, ensure_ascii=False)[:3000], round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
