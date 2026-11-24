"""1183 当選した人が来なかった割合を、申し込んだ人全体が来ない割合として読めるのか？（架空のデータ）

作成者が置いた架空の催し（4日に分けて開く。1日の席は倍率から決める）。申し込む人は4,000人。
1人が申し込む日の数は1日50%・2日25%・3日15%・4日10%（日はでたらめに選ぶ）。
1人ひとりに「席を1つ持ったときに来る確率」a を置く（平均0.9、0〜1の山形の分布、標準偏差0.1。平均が1に近く作れないときは標準偏差を小さくする）。
→ 本当の「申し込んだ人全体が来ない割合」（1人に席を1つずつ渡したとき）＝1−a の平均。
抽選は日ごとに、その日の申し込みからでたらめに席の数だけ当てる（1人1日1口）。
2日以上当たった人は、当たった日のうち1日だけを選び（でたらめ）、そこへ a の確率で来る。ほかの日は来ない。
基本では、来ない日を前もって取り消す人はいない（取り消す割合 c を確かめで変える）。
当選した人が来なかった割合＝来なかった当選の席÷当選の席（取り消した席は分子・分母から除く）。
(1) 倍率（申し込みの件数÷全部の席）1.1〜20倍の7通り×各300回
(2) 確かめ：倍率4通り×申し込む日の数3通り×何日も申し込む人ほど来にくいか2通り×取り消す割合2通り×来ない割合の平均3通り＝144通り（各60回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1183
SRC = "架空の催しの抽選と当日（作成者が置いた申し込み方と来る確率からの乱数、seed 1183）"
M, D = 4000, 4
K_BASE = [0.5, 0.25, 0.15, 0.10]
K_ONE = [1.0, 0.0, 0.0, 0.0]
K_MANY = [0.25, 0.25, 0.25, 0.25]
SD_A = 0.1
RATIOS = [1.1, 1.5, 2, 3, 5, 10, 20]
R_MAIN, R_GRID = 300, 60
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def shape_ab(mean, sd):
    v = sd ** 2
    k = mean * (1 - mean) / v - 1
    return mean * k, (1 - mean) * k


def one_run(rng, ratio, kdist=K_BASE, noshow=0.1, slope=0.0, cancel=0.0, keep=False):
    k = rng.choice(np.arange(1, D + 1), size=M, p=kdist)
    # 来る確率：何日も申し込む人ほど来にくい置き方（slope：申し込む日が1日増えるごとに来ない割合の平均が増える量）
    mean_ns = noshow + slope * (k - k.mean())
    mean_ns = np.clip(mean_ns, 0.01, 0.6)
    m_a = 1 - mean_ns
    sd = np.minimum(SD_A, np.sqrt(m_a * (1 - m_a) / 2))   # 平均が1に近いときは、ばらつきを分布が作れる大きさまで小さくする
    a_par, b_par = shape_ab(m_a, sd)
    a = rng.beta(a_par, b_par)
    # 申し込み（人×日）
    days = np.argsort(rng.random((M, D)), axis=1)
    mask = np.arange(D)[None, :] < k[:, None]
    pid = np.repeat(np.arange(M), D)[mask.ravel()]
    did = days.ravel()[mask.ravel()]
    n_app = len(pid)
    seats = max(1, int(round(n_app / ratio / D)))
    key = rng.random(n_app)
    won = np.zeros(n_app, bool)
    for d in range(D):
        idx = np.flatnonzero(did == d)
        if len(idx) <= seats:
            won[idx] = True
        else:
            won[idx[np.argpartition(key[idx], seats)[:seats]]] = True
    wins_per = np.bincount(pid[won], minlength=M)
    # 当たった日のうち1日を選ぶ
    wp, wd = pid[won], did[won]
    pick_key = rng.random(len(wp))
    order = np.lexsort((pick_key, wp))
    first = np.ones(len(wp), bool)
    first[1:] = wp[order][1:] != wp[order][:-1]
    chosen = np.zeros(len(wp), bool)
    chosen[order[first]] = True
    come = chosen & (rng.random(len(wp)) < a[wp])
    cancelled = (~chosen) & (rng.random(len(wp)) < cancel)
    seats_held = (~cancelled).sum()
    no_show = ((~come) & (~cancelled)).sum()
    res = {
        "apps": n_app, "seats_per_day": seats, "ratio_real": n_app / (seats * D),
        "true_person_noshow": 1 - a.mean(),
        "true_app_noshow": 1 - (a * k).sum() / k.sum(),
        "winner_noshow": no_show / max(seats_held, 1),
        "winner_people_noshow_own": 1 - a[wins_per > 0].mean(),
        "multi_win_share": (wins_per >= 2).sum() / max((wins_per >= 1).sum(), 1),
        "extra_win_share": ((~chosen).sum()) / max(len(wp), 1),
        "cancelled": int(cancelled.sum()),
    }
    if keep:
        res["table"] = pd.DataFrame({"person_id": np.arange(1, M + 1), "days_applied": k, "come_prob": np.round(a, 4),
                                     "days_won": wins_per})
    return res


def main():
    rng = np.random.default_rng(SEED)
    ex = one_run(np.random.default_rng(SEED + 1), 2, keep=True)
    ex["table"].to_csv(DATA / "persons_example.csv", index=False)

    rows = []
    for ratio in RATIOS:
        for i in range(R_MAIN):
            x = one_run(rng, ratio)
            x["ratio_set"] = ratio
            rows.append(x)
    sim = pd.DataFrame(rows)
    main_t = sim.groupby("ratio_set").agg(
        ratio_real=("ratio_real", "mean"), seats_per_day=("seats_per_day", "mean"),
        true_person_noshow=("true_person_noshow", "mean"), true_app_noshow=("true_app_noshow", "mean"),
        winner_noshow=("winner_noshow", "mean"),
        winner_noshow_p10=("winner_noshow", lambda v: v.quantile(0.1)),
        winner_noshow_p90=("winner_noshow", lambda v: v.quantile(0.9)),
        multi_win_share=("multi_win_share", "mean"), extra_win_share=("extra_win_share", "mean"),
        winner_people_noshow_own=("winner_people_noshow_own", "mean")).reset_index()
    main_t["winner_over_true"] = main_t.winner_noshow / main_t.true_person_noshow
    # 分け方：選ばれなかった日の席（すべて来ない）＋選んだ日の席×当たった人の来ない割合
    main_t["split_extra_part"] = main_t.extra_win_share
    main_t["split_chosen_part"] = (1 - main_t.extra_win_share) * main_t.winner_people_noshow_own
    main_t["split_sum"] = main_t.split_extra_part + main_t.split_chosen_part
    main_t = main_t.round(4)
    main_t.to_csv(RES / "by_ratio.csv", index=False)

    # 確かめ 144通り
    rows = []
    kd = {"1日だけ": K_ONE, "基本": K_BASE, "何日も多め": K_MANY}
    for ratio in [1.1, 2, 5, 20]:
        for kname, kv in kd.items():
            for slope in [0.0, 0.04]:
                for cancel in [0.0, 0.5]:
                    for ns in [0.05, 0.1, 0.2]:
                        xs = [one_run(rng, ratio, kv, ns, slope, cancel) for _ in range(R_GRID)]
                        df = pd.DataFrame(xs)
                        rows.append({"ratio_set": ratio, "days_applied": kname, "slope": slope, "cancel": cancel,
                                     "noshow_set": ns,
                                     "true_person_noshow": r(df.true_person_noshow.mean()),
                                     "true_app_noshow": r(df.true_app_noshow.mean()),
                                     "winner_noshow": r(df.winner_noshow.mean()),
                                     "multi_win_share": r(df.multi_win_share.mean()),
                                     "winner_over_true": r(df.winner_noshow.mean() / df.true_person_noshow.mean())})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid
    one = g[(g.days_applied == "1日だけ")]
    multi = g[(g.days_applied != "1日だけ")]
    robust = {
        "n": int(len(g)),
        "winner_over_true_min": r(g.winner_over_true.min()), "winner_over_true_max": r(g.winner_over_true.max()),
        "one_day_slope0_min": r(one[one.slope == 0].winner_over_true.min()),
        "one_day_slope0_max": r(one[one.slope == 0].winner_over_true.max()),
        "one_day_all_min": r(one.winner_over_true.min()), "one_day_all_max": r(one.winner_over_true.max()),
        "multi_min": r(multi.winner_over_true.min()), "multi_max": r(multi.winner_over_true.max()),
        "multi_share_over_1_1": r((multi.winner_over_true > 1.1).mean() * 100, 2),
        "by_ratio_multi": multi.groupby("ratio_set").winner_over_true.agg(["min", "median", "max"]).round(4).reset_index().to_dict("records"),
        "by_ratio_multi_slope0": multi[multi.slope == 0].groupby("ratio_set").winner_over_true.agg(["min", "max"]).round(4).reset_index().to_dict("records"),
        "by_days_multi": multi.groupby("days_applied").winner_over_true.agg(["min", "median", "max"]).round(4).reset_index().to_dict("records"),
        "by_noshow_multi": multi.groupby("noshow_set").winner_over_true.agg(["min", "median", "max"]).round(4).reset_index().to_dict("records"),
        "by_cancel_multi": multi.groupby("cancel").winner_over_true.agg(["min", "median", "max"]).round(4).reset_index().to_dict("records"),
        "slope_multi_true_app_over_person_min": r((multi[multi.slope > 0].true_app_noshow / multi[multi.slope > 0].true_person_noshow).min()),
        "slope_multi_true_app_over_person_max": r((multi[multi.slope > 0].true_app_noshow / multi[multi.slope > 0].true_person_noshow).max()),
        "slope_ratio20_median_true_app_over_person": r((g[(g.slope > 0) & (g.ratio_set == 20) & (g.days_applied != "1日だけ")].true_app_noshow
                                                        / g[(g.slope > 0) & (g.ratio_set == 20) & (g.days_applied != "1日だけ")].true_person_noshow).median()),
    }
    # 1.1倍と20倍の基本の比べ（取り消し0.5）
    base_c = g[(g.days_applied == "基本") & (g.slope == 0) & (g.noshow_set == 0.1)][["ratio_set", "cancel", "winner_noshow", "winner_over_true"]]
    robust["base_cancel"] = base_c.to_dict("records")

    mt = main_t.set_index("ratio_set")
    headline = {
        "true_person_noshow": r(mt.true_person_noshow.mean()),
        "true_app_noshow": r(mt.true_app_noshow.mean()),
        "winner_noshow_1_1": r(mt.loc[1.1, "winner_noshow"]), "winner_noshow_2": r(mt.loc[2, "winner_noshow"]),
        "winner_noshow_5": r(mt.loc[5, "winner_noshow"]), "winner_noshow_20": r(mt.loc[20, "winner_noshow"]),
        "extra_1_1": r(mt.loc[1.1, "extra_win_share"]), "extra_20": r(mt.loc[20, "extra_win_share"]),
        "split_max_gap": r((main_t.split_sum - main_t.winner_noshow).abs().max()),
        "over_1_1": r(mt.loc[1.1, "winner_over_true"]), "over_20": r(mt.loc[20, "winner_over_true"]),
        "robust_multi_min": robust["multi_min"], "robust_multi_max": robust["multi_max"],
    }
    out = {"settings": {"people": M, "days": D, "days_applied_dist": K_BASE, "noshow_mean": 0.1, "noshow_sd": SD_A,
                        "ratios": RATIOS, "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
           "headline": headline,
           "example_one_run_ratio2": {k: (r(v) if isinstance(v, float) else int(v)) for k, v in ex.items() if k != "table"},
           "robust": robust}
    with open(RES / "a1183_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：倍率ごとの当選した人の来ない割合
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    x = np.arange(len(RATIOS))
    ax.bar(x, main_t.winner_noshow * 100, 0.6, color=ORANGE, label="当選した人が来なかった割合（当選の席あたり）")
    for xi, v in zip(x, main_t.winner_noshow * 100):
        ax.text(xi, v + 0.5, f"{v:.2f}%", ha="center", fontsize=8.5)
    tp = mt.true_person_noshow.mean() * 100
    ax.axhline(tp, color=INK, ls="--", lw=1, label=f"申し込んだ人全体が来ない割合（作成者が置いた値）{tp:.2f}%")
    ax.set_xticks(x, [f"{v:g}倍" for v in RATIOS])
    ax.set_xlabel("倍率（申し込みの件数÷全部の席）")
    ax.set_ylabel("来なかった割合（%）")
    ax.set_ylim(0, main_t.winner_noshow.max() * 100 * 1.25)
    ax.set_title("倍率が低いほど、当選した人の来ない割合は高く出た")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1183_by_ratio.png", SRC)

    # 図2：2日以上当たった人の割合と、来ない割合の上乗せ
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(x, main_t.multi_win_share * 100, marker="o", color=BLUE, label="当たった人のうち2日以上当たった人")
    ax.plot(x, main_t.extra_win_share * 100, marker="s", color=ORANGE, label="当選の席のうち、選ばれなかった日の席")
    for xi, v in zip(x, main_t.extra_win_share * 100):
        if xi == x[-1]:
            ax.text(xi, v + 2.5, f"{v:.2f}%", ha="center", va="bottom", fontsize=8.5, color=ORANGE)
        else:
            ax.text(xi - 0.1, v - 1.5, f"{v:.2f}%", ha="right", va="top", fontsize=8.5, color=ORANGE)
    ax.set_xlim(x[0] - 0.75, x[-1] + 0.4)
    ax.set_xticks(x, [f"{v:g}倍" for v in RATIOS])
    ax.set_xlabel("倍率（申し込みの件数÷全部の席）")
    ax.set_ylabel("割合（%）")
    ax.set_ylim(0, max(main_t.multi_win_share.max(), main_t.extra_win_share.max()) * 100 * 1.2)
    ax.set_title("倍率が低いほど、何日も当たって選ばれない日の席が増えた")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1183_multi_win.png", SRC)

    # 図3：確かめ 144通り
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    cols = {"1日だけ": GRAY, "基本": BLUE, "何日も多め": ORANGE}
    rs = [1.1, 2, 5, 20]
    for i, (kn, c) in enumerate(cols.items()):
        sub = g[g.days_applied == kn]
        for j, rr in enumerate(rs):
            v = sub[sub.ratio_set == rr].winner_over_true.values
            xx = j + (i - 1) * 0.25 + np.linspace(-0.08, 0.08, len(v))
            ax.scatter(xx, v, s=10, color=c, alpha=0.7, label=f"申し込む日：{kn}" if j == 0 else None)
    ax.axhline(1, color=INK, lw=1, ls="--")
    ax.set_xticks(range(4), [f"{v:g}倍" for v in rs])
    ax.set_xlabel("倍率（申し込みの件数÷全部の席）")
    ax.set_ylabel("当選した人の来ない割合÷全体が来ない割合")
    ax.set_ylim(0, g.winner_over_true.max() * 1.1)
    ax.set_title("144通りの置き方：当選した人の来ない割合と全体の比")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1183_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
