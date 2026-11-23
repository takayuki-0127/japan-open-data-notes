"""1030 「平均の所要時間」で計画すると、何回に1回遅れるのか？（架空のデータ）

架空の通勤（家→バス停の徒歩、バス待ち、バスに乗る時間、バス停→会社の徒歩）。
1日の所要＝4つの和。バスに乗る時間は対数正規、雨の日は1.25倍、まれに道が大きく混む日は一様分布の分だけ足す。
「平均の所要」で家を出る時刻を決めたとき、着くのが予定より遅れる日の割合を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1030
SRC = "架空の通勤の所要時間（作成者が乱数で作成、seed 1030）"
DAYS_PER_YEAR = 245
BASE = dict(walk1=(6.0, 0.5), headway=10.0, ride_med=18.0, ride_sd=0.10, rain_p=0.20, rain_f=1.25,
            jam_p=0.04, jam_lo=10.0, jam_hi=25.0, walk2=(5.0, 0.4))
N_BIG = 400_000


def make(rng, n, **kw):
    p = {**BASE, **kw}
    walk1 = rng.normal(*p["walk1"], n)
    wait = rng.uniform(0, p["headway"], n)
    rain = rng.random(n) < p["rain_p"]
    ride = p["ride_med"] * np.exp(rng.normal(0, p["ride_sd"], n)) * np.where(rain, p["rain_f"], 1.0)
    jam = rng.random(n) < p["jam_p"]
    ride = ride + np.where(jam, rng.uniform(p["jam_lo"], p["jam_hi"], n), 0.0)
    walk2 = rng.normal(*p["walk2"], n)
    total = walk1 + wait + ride + walk2
    return pd.DataFrame({"walk1": walk1, "wait": wait, "ride": ride, "walk2": walk2, "rain": rain,
                         "jam": jam, "total": total})


def late_stats(total, plan):
    late = total - plan
    return {"late_pct": round(float((late > 0).mean() * 100), 2),
            "late5_pct": round(float((late >= 5).mean() * 100), 2),
            "late10_pct": round(float((late >= 10).mean() * 100), 2)}


def main():
    rng = np.random.default_rng(SEED)

    # (1) 基本の置き方：たくさんの日で、平均どおりに出たときの遅れる割合
    big = make(rng, N_BIG)
    mean, med = float(big.total.mean()), float(big.total.median())
    base = {"mean_min": round(mean, 2), "median_min": round(med, 2),
            "p90_min": round(float(big.total.quantile(.9)), 2), "p99_min": round(float(big.total.quantile(.99)), 2),
            "plan_mean": late_stats(big.total, mean), "plan_median": late_stats(big.total, med),
            "late_pct_rain_days": round(float((big.total[big.rain] > mean).mean() * 100), 2),
            "late_pct_dry_days": round(float((big.total[~big.rain] > mean).mean() * 100), 2),
            "late_pct_jam_days": round(float((big.total[big.jam] > mean).mean() * 100), 2),
            "late_pct_normal_days": round(float((big.total[~big.jam] > mean).mean() * 100), 2),
            "share_rain_pct": round(float(big.rain.mean() * 100), 2),
            "share_jam_pct": round(float(big.jam.mean() * 100), 2),
            "mean_rain_min": round(float(big.total[big.rain].mean()), 2),
            "mean_dry_min": round(float(big.total[~big.rain].mean()), 2),
            "mean_without_jam_min": round(float(big.total[~big.jam].mean()), 2)}
    base["mean_minus_median_min"] = round(mean - med, 2)
    base["once_in_n_days"] = round(100 / base["plan_mean"]["late_pct"], 2)
    base["dry_days_share_of_all_late_pct"] = round(
        float(((big.total > mean) & ~big.rain).sum() / (big.total > mean).sum() * 100), 2)
    hist = np.histogram(big.total, bins=np.arange(10, 81, 1))

    # (2) 計画の決め方（去年1年で決めて、今年1年で確かめる、200回）
    rows = []
    for r in range(200):
        g = np.random.default_rng(SEED * 1000 + r)
        d = make(g, 2 * DAYS_PER_YEAR)
        y1, y2 = d.iloc[:DAYS_PER_YEAR], d.iloc[DAYS_PER_YEAR:].reset_index(drop=True)
        roll = d.total.rolling(20).mean().shift(1).iloc[DAYS_PER_YEAR:].reset_index(drop=True)
        plans = {"去年の平均": np.full(len(y2), y1.total.mean()),
                 "去年の中央値": np.full(len(y2), y1.total.median()),
                 "直近20日の平均": roll.values,
                 "雨かどうかで分けた去年の平均": np.where(y2.rain, y1.total[y1.rain].mean(), y1.total[~y1.rain].mean())}
        for k, pl in plans.items():
            late = y2.total.values > pl
            rows.append({"rep": r, "method": k, "late_pct": late.mean() * 100,
                         "late_rain_pct": late[y2.rain.values].mean() * 100,
                         "late_dry_pct": late[~y2.rain.values].mean() * 100,
                         "late5_pct": (y2.total.values - pl >= 5).mean() * 100,
                         "plan_mean_min": float(np.mean(pl))})
    sim = pd.DataFrame(rows)
    meth = sim.groupby("method", sort=False).agg(
        late_pct=("late_pct", "mean"), late_pct_p10=("late_pct", lambda x: x.quantile(.1)),
        late_pct_p90=("late_pct", lambda x: x.quantile(.9)), late_rain_pct=("late_rain_pct", "mean"),
        late_dry_pct=("late_dry_pct", "mean"), late5_pct=("late5_pct", "mean"),
        plan_mean_min=("plan_mean_min", "mean")).round(2).reset_index()
    meth.to_csv(RES / "plan_methods.csv", index=False)

    # (3) 確かめ：道が大きく混む日の割合 × 混んだときの増え方（平均どおりに出たとき）
    grid = []
    for jp in [0.0, 0.02, 0.04, 0.08, 0.15]:
        for lo, hi, lab in [(5, 10, "5〜10分"), (10, 25, "10〜25分"), (20, 40, "20〜40分")]:
            g = np.random.default_rng(SEED * 7 + int(jp * 100) * 10 + lo)
            d = make(g, 200_000, jam_p=jp, jam_lo=lo, jam_hi=hi)
            m = d.total.mean()
            grid.append({"jam_p_pct": jp * 100, "jam_add": lab, "mean_min": round(float(m), 2),
                         "median_min": round(float(d.total.median()), 2),
                         "late_pct": round(float((d.total > m).mean() * 100), 2),
                         "late5_pct": round(float((d.total - m >= 5).mean() * 100), 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness_jam.csv", index=False)

    # (4) 確かめ：ほかの置き方を1つずつ
    other = []
    cases = [("基本", {}),
             ("雨の日なし", {"rain_p": 0.0}),
             ("雨の日40%", {"rain_p": 0.4}),
             ("バスの待ちなし（時刻表に合わせて家を出る）", {"headway": 0.0}),
             ("バスに乗る時間の振れ大（0.25）", {"ride_sd": 0.25}),
             ("雨・混む日なし・振れ小（左右対称に近い）", {"rain_p": 0.0, "jam_p": 0.0, "ride_sd": 0.02})]
    for i, (lab, kw) in enumerate(cases):
        g = np.random.default_rng(SEED * 11 + i)
        d = make(g, 200_000, **kw)
        m = d.total.mean()
        other.append({"case": lab, "mean_min": round(float(m), 2), "median_min": round(float(d.total.median()), 2),
                      "late_pct": round(float((d.total > m).mean() * 100), 2),
                      "late5_pct": round(float((d.total - m >= 5).mean() * 100), 2)})
    other = pd.DataFrame(other)
    other.to_csv(RES / "robustness_other.csv", index=False)

    # データ：2年分の1回（490日）
    g = np.random.default_rng(SEED)
    d = make(g, 2 * DAYS_PER_YEAR)
    d.insert(0, "year", np.repeat([1, 2], DAYS_PER_YEAR))
    d.insert(1, "day", np.tile(np.arange(1, DAYS_PER_YEAR + 1), 2))
    d.round(3).to_csv(DATA / "commute_2years.csv", index=False)
    plan1 = float(d.total[d.year == 1].mean())
    one = {"year1_mean_min": round(plan1, 2),
           "year2_late_pct": round(float((d.total[d.year == 2] > plan1).mean() * 100), 2),
           "year2_late_days": int((d.total[d.year == 2] > plan1).sum())}

    all_cells = pd.concat([grid.late_pct, other.late_pct])
    out = {"base_400k_days": base, "plan_methods_200reps": meth.to_dict("records"),
           "robustness_jam": grid.to_dict("records"), "robustness_other": other.to_dict("records"),
           "robustness_late_pct_range": {"n_cases": int(len(all_cells)), "min": float(all_cells.min()),
                                         "max": float(all_cells.max())},
           "robustness_jam_late_pct_range": {"min": float(grid.late_pct.min()), "max": float(grid.late_pct.max())},
           "one_draw_2years": one}
    json.dump(out, open(RES / "a1030_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：所要の分布と平均・中央値
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = hist[1][:-1]
    late = x >= mean
    ax.bar(x[~late] + .5, hist[0][~late] / N_BIG * 100, width=1, color=LIGHT, label="平均より早く着いた日")
    ax.bar(x[late] + .5, hist[0][late] / N_BIG * 100, width=1, color=ORANGE, alpha=.8, label="平均より遅く着いた日")
    ax.axvline(mean, color=INK, lw=1.2); ax.axvline(med, color=GRAY, lw=1, ls="--")
    yt = ax.get_ylim()[1]
    ax.annotate(f"平均 {mean:.2f}分", (mean, yt * .97), xytext=(45, yt * .95), fontsize=9, va="center",
                arrowprops=dict(arrowstyle="-", color=INK, lw=.8))
    ax.annotate(f"中央値 {med:.2f}分", (med, yt * .97), xytext=(17, yt * .95), fontsize=9, va="center", color=GRAY,
                arrowprops=dict(arrowstyle="-", color=GRAY, lw=.8))
    ax.set_xlabel("1日の所要時間（分）"); ax.set_ylabel("日の割合（%）"); ax.set_xlim(15, 80)
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1, .7))
    ax.set_title(f"平均どおりに出ると、遅れる日は{base['plan_mean']['late_pct']:.2f}%（{N_BIG:,}日）")
    save(fig, "a1030_dist.png", SRC)

    # 図2：計画の決め方ごと、雨の日と雨でない日
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    yy = np.arange(len(meth))
    ax.barh(yy + .2, meth.late_dry_pct, height=.38, color=BLUE, label="雨でない日")
    ax.barh(yy - .2, meth.late_rain_pct, height=.38, color=ORANGE, label="雨の日")
    for i, (a, b) in enumerate(zip(meth.late_dry_pct, meth.late_rain_pct)):
        ax.text(a + 1, i + .2, f"{a:.2f}%", va="center", fontsize=8.5)
        ax.text(b + 1, i - .2, f"{b:.2f}%", va="center", fontsize=8.5)
    ax.set_yticks(yy); ax.set_yticklabels(meth.method); ax.invert_yaxis(); ax.set_xlim(0, 110)
    ax.set_xlabel("予定より遅く着いた日の割合（%、今年1年、200回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title(f"1つの平均で計画すると、雨の日は{meth.late_rain_pct.iloc[0]:.2f}%の日に遅れる")
    save(fig, "a1030_methods.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for lab, c in zip(["5〜10分", "10〜25分", "20〜40分"], [LIGHT, BLUE, ORANGE]):
        r = grid[grid.jam_add == lab]
        ax.plot(r.jam_p_pct, r.late_pct, marker="o", color=c, lw=2, label=f"混んだ日に {lab} 増える")
    ax.axhline(50, color=GRAY, lw=.8, ls="--"); ax.text(14.8, 50.8, "50%", color=GRAY, fontsize=9, ha="right")
    ax.set_xlabel("道が大きく混む日の割合（%）"); ax.set_ylabel("平均どおりに出て遅れる日の割合（%）")
    ax.set_ylim(0, 60); ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("まれな大きな遅れがあるほど、平均どおりで遅れる日は減る")
    save(fig, "a1030_robust.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])


if __name__ == "__main__":
    main()
