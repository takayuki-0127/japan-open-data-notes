"""1037 待ち合わせに余裕を何分みれば、9割の確率で間に合うのか？（架空のデータ）

架空の移動：家から駅まで歩く → 電車を待つ（決まった間隔で来る） → 乗る → 駅から待ち合わせの場所まで歩く。
ときどき遅れが出て、遅れやすい日（2人に共通）もある。作成者が置いたこの決まりで、
「平均の所要時間＋何分」で9割間に合うか、過去の記録から余裕を決めると本当に9割になるか、
2人とも間に合う確率はどうなるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1037
SRC = "架空の移動の記録（作成者が乱数で作成、seed 1037）"
BASE = {"headway": 10.0, "p_delay": 0.05, "bad_share": 0.15, "p_delay_bad": 0.30, "delay_mean": 8.0, "shared": True}
N_BIG = 400_000
Z90 = 1.2815516


def trip(rng, n, bad, headway=10.0, p_delay=0.05, p_delay_bad=0.30, delay_mean=8.0, **_):
    """1回の移動の時間（分）。bad：遅れやすい日なら True"""
    walk1 = rng.normal(8, 1.0, n)
    wait = rng.uniform(0, headway, n)
    ride = 20 * np.exp(rng.normal(0, 0.08, n)) * np.where(bad, 1.1, 1.0)
    p = np.where(bad, p_delay_bad, p_delay)
    delay = np.where(rng.random(n) < p, rng.exponential(delay_mean, n), 0.0)
    walk2 = rng.normal(5, 0.7, n)
    return walk1 + wait + ride + delay + walk2


def days(rng, n, kw):
    """n日分の2人（A・B）の移動の時間。遅れやすい日は shared なら2人に共通"""
    bad_a = rng.random(n) < kw["bad_share"]
    bad_b = bad_a if kw["shared"] else rng.random(n) < kw["bad_share"]
    return trip(rng, n, bad_a, **kw), trip(rng, n, bad_b, **kw)


def coverage(sorted_big, thr):
    return np.searchsorted(sorted_big, thr, side="right") / len(sorted_big)


def evaluate(rng, kw, n_person=20000, ns=(10, 20, 50)):
    a, b = days(rng, N_BIG, kw)
    sa = np.sort(a)
    mean, sd = a.mean(), a.std()
    q50, q90, q95 = np.quantile(a, [.5, .9, .95])
    res = {"mean": mean, "sd": sd, "median": q50, "q90": q90, "q95": q95,
           "buffer90_over_mean": q90 - mean, "ontime_at_mean": coverage(sa, mean),
           "ontime_at_median": coverage(sa, q50),
           "normal_rule_true_params": coverage(sa, mean + Z90 * sd)}
    # 2人とも間に合う
    both_q90 = float(((a <= q90) & (b <= q90)).mean())
    mx = np.sort(np.maximum(a, b))
    t_joint = mx[int(np.ceil(0.9 * len(mx))) - 1]
    res.update({"both_at_own_q90": both_q90, "joint90_threshold": t_joint,
                "joint90_buffer_over_mean": t_joint - mean, "joint90_single_cov": coverage(sa, t_joint),
                "extra_for_two": t_joint - q90})
    # 過去の記録から余裕を決める（1人あたり n 回の記録、人を変えて n_person 人）
    for n in ns:
        bad = rng.random((n_person, n)) < kw["bad_share"]
        rec = trip(rng, n_person * n, bad.ravel(), **kw).reshape(n_person, n)
        rules = {"q90": np.quantile(rec, 0.9, axis=1),
                 "normal": rec.mean(1) + Z90 * rec.std(1, ddof=1),
                 "max": rec.max(1)}
        for k, thr in rules.items():
            cov = coverage(sa, thr)
            res[f"n{n}_{k}_cov"] = float(cov.mean())
            res[f"n{n}_{k}_lt80"] = float((cov < 0.8).mean())
            res[f"n{n}_{k}_buffer"] = float((thr - mean).mean())
    return res, a, b


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base, a, b = evaluate(rng, BASE)
    # 1回分の記録（data）：2人の365日
    rd = np.random.default_rng(SEED + 1)
    bad = rd.random(365) < BASE["bad_share"]
    ta, tb = trip(rd, 365, bad, **BASE), trip(rd, 365, bad, **BASE)
    pd.DataFrame({"day": np.arange(1, 366), "bad_day": bad.astype(int), "A_min": ta.round(2), "B_min": tb.round(2)}).to_csv(
        DATA / "trips_365days.csv", index=False)

    # 記録の回数ごとの決め方（基本）
    rows = []
    for n in (10, 20, 50):
        for k, nm in [("q90", "過去の90%点"), ("normal", "平均＋1.28×標準偏差"), ("max", "過去の最長")]:
            rows.append({"records": n, "rule": nm, "mean_ontime": r(base[f"n{n}_{k}_cov"]),
                         "share_persons_below_80pct": r(base[f"n{n}_{k}_lt80"]),
                         "mean_buffer_over_true_mean_min": r(base[f"n{n}_{k}_buffer"], 2)})
    rules = pd.DataFrame(rows)
    rules.to_csv(RES / "rules_by_records.csv", index=False)

    # 確かめ：2人の遅れやすい日が別々（独立）
    ind, ai, bi = evaluate(np.random.default_rng(SEED * 3), dict(BASE, shared=False), n_person=2000, ns=(10,))
    # 確かめ：電車の間隔 × ふだんの遅れの確率 × 遅れやすい日の割合（27通り）
    grid = []
    j = 0
    for h in [5.0, 10.0, 20.0]:
        for pdl in [0.02, 0.05, 0.10]:
            for bs in [0.0, 0.15, 0.30]:
                kw = dict(BASE, headway=h, p_delay=pdl, bad_share=bs)
                res, _, _ = evaluate(np.random.default_rng(SEED * 100 + j), kw, n_person=5000, ns=(10,))
                j += 1
                grid.append({"headway": h, "p_delay": pdl, "bad_share": bs, "mean": r(res["mean"], 2),
                             "buffer90_over_mean": r(res["buffer90_over_mean"], 2),
                             "ontime_at_mean": r(res["ontime_at_mean"]),
                             "normal_rule_true_params": r(res["normal_rule_true_params"]),
                             "n10_q90_cov": r(res["n10_q90_cov"]), "n10_max_cov": r(res["n10_max_cov"]),
                             "both_at_own_q90": r(res["both_at_own_q90"]),
                             "joint90_buffer_over_mean": r(res["joint90_buffer_over_mean"], 2),
                             "extra_for_two": r(res["extra_for_two"], 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    out = {"base_setting": BASE, "n_big": N_BIG,
           "base": {k: r(v, 4) for k, v in base.items()},
           "headline": {"mean_min": r(base["mean"], 2), "q90_min": r(base["q90"], 2),
                        "buffer90_over_mean_min": r(base["buffer90_over_mean"], 2),
                        "ontime_at_mean_pct": r(base["ontime_at_mean"] * 100, 2),
                        "normal_rule_true_params_pct": r(base["normal_rule_true_params"] * 100, 2),
                        "n10_q90_ontime_pct": r(base["n10_q90_cov"] * 100, 2),
                        "n10_q90_persons_below80_pct": r(base["n10_q90_lt80"] * 100, 2),
                        "n10_max_ontime_pct": r(base["n10_max_cov"] * 100, 2),
                        "both_at_own_q90_pct": r(base["both_at_own_q90"] * 100, 2),
                        "joint90_buffer_over_mean_min": r(base["joint90_buffer_over_mean"], 2),
                        "joint90_single_cov_pct": r(base["joint90_single_cov"] * 100, 2),
                        "extra_for_two_min": r(base["extra_for_two"], 2)},
           "independent_bad_days": {k: r(ind[k], 4) for k in ["mean", "q90", "both_at_own_q90", "joint90_buffer_over_mean",
                                                                "joint90_single_cov", "extra_for_two"]},
           "shared_minus_independent_both_pt": r((base["both_at_own_q90"] - ind["both_at_own_q90"]) * 100, 2),
           "constants": {"walk1_mean_sd": [8, 1.0], "ride_min": 20, "ride_log_sd": 0.08, "bad_day_ride_factor": 1.1,
                         "walk2_mean_sd": [5, 0.7], "n_person_base": 20000, "z90": Z90},
           "formula": {"order_stat_max_n10": r(10 / 11), "order_stat_max_n20": r(20 / 21), "order_stat_max_n50": r(50 / 51),
                       "independent_both": 0.81, "independent_each_for_joint90": r(np.sqrt(0.9))},
           "rules_by_records": rules.to_dict("records"),
           "grid_summary": {"n": int(len(g)),
                            "buffer90_min": r(g.buffer90_over_mean.min(), 2), "buffer90_max": r(g.buffer90_over_mean.max(), 2),
                            "ontime_at_mean_min": r(g.ontime_at_mean.min()), "ontime_at_mean_max": r(g.ontime_at_mean.max()),
                            "normal_min": r(g.normal_rule_true_params.min()), "normal_max": r(g.normal_rule_true_params.max()),
                            "n10_q90_min": r(g.n10_q90_cov.min()), "n10_q90_max": r(g.n10_q90_cov.max()),
                            "n10_max_min": r(g.n10_max_cov.min()), "n10_max_max": r(g.n10_max_cov.max()),
                            "both_min": r(g.both_at_own_q90.min()), "both_max": r(g.both_at_own_q90.max()),
                            "extra_two_min": r(g.extra_for_two.min(), 2), "extra_two_max": r(g.extra_for_two.max(), 2),
                            "joint_buffer_min": r(g.joint90_buffer_over_mean.min(), 2),
                            "joint_buffer_max": r(g.joint90_buffer_over_mean.max(), 2)}}
    json.dump(out, open(RES / "a1037_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1人の所要時間の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.hist(a, bins=np.arange(25, 85, 1), color=LIGHT, density=True)
    for v, lab, c, dy in [(base["mean"], f"平均 {base['mean']:.2f}分", INK, .95),
                          (base["q90"], f"90%点 {base['q90']:.2f}分", ORANGE, .82),
                          (base["joint90_threshold"], f"2人とも9割 {base['joint90_threshold']:.2f}分", BLUE, .69)]:
        ax.axvline(v, color=c, lw=1.4, ls="--")
    ymax = ax.get_ylim()[1]
    for v, lab, c, dy in [(base["mean"], f"平均 {base['mean']:.2f}分", INK, .95),
                          (base["q90"], f"90%点 {base['q90']:.2f}分", ORANGE, .82),
                          (base["joint90_threshold"], f"2人とも9割 {base['joint90_threshold']:.2f}分", BLUE, .69)]:
        ax.text(base["joint90_threshold"] + 1.0, ymax * dy, lab, color=c, fontsize=9,
                bbox=dict(facecolor="white", edgecolor="none", pad=1))
    ax.set_xlabel("家から待ち合わせの場所までの時間（分）"); ax.set_yticks([])
    ax.set_title(f"平均の時間で出ると間に合うのは{base['ontime_at_mean']*100:.2f}%、9割には平均＋{base['buffer90_over_mean']:.2f}分")
    save(fig, "a1037_distribution.png", SRC)

    # 図2：過去の記録から決めたときの、本当に間に合う割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cl = {"過去の90%点": ORANGE, "平均＋1.28×標準偏差": GRAY, "過去の最長": BLUE}
    for nm, gg in rules.groupby("rule", sort=False):
        ax.plot(gg.records, gg.mean_ontime * 100, marker="o", color=cl[nm], label=nm)
        for x_, y_ in zip(gg.records, gg.mean_ontime * 100):
            ax.text(x_ + 1.0, y_ - 0.55, f"{y_:.2f}%", fontsize=8, color=cl[nm],
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
    ax.axhline(90, color=INK, lw=.8, ls="--")
    ax.set_xticks([10, 20, 50]); ax.set_xlabel("決めるのに使った過去の記録（回）")
    ax.set_ylabel("本当に間に合う割合（%、2万人の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("過去10回の90%点で決めると、9割に届かない")
    save(fig, "a1037_records.png", SRC)

    # 図3：27通りの、1人の余裕と2人の余裕
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cl2 = {5.0: GRAY, 10.0: BLUE, 20.0: ORANGE}
    for h, gg in g.groupby("headway"):
        ax.scatter(gg.buffer90_over_mean, gg.joint90_buffer_over_mean, color=cl2[h], s=30, label=f"電車の間隔 {h:.0f}分")
    m = g.joint90_buffer_over_mean.max() * 1.08
    ax.plot([0, m], [0, m], color=INK, lw=.8, ls="--"); ax.text(m * .7, m * .63, "1人と同じ", fontsize=8)
    ax.set_xlabel("1人が9割間に合う余裕（平均＋何分）"); ax.set_ylabel("2人とも9割間に合う余裕（平均＋何分）")
    ax.set_xlim(0, m); ax.set_ylim(0, m)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("置き方27通り：2人とも間に合うには、1人分より長い余裕が要る")
    save(fig, "a1037_grid.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
