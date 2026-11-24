"""1252 本ごとの売れ方を出した月で比べると、月の途中で出した本はどう見えるのか？（架空のデータ）

作成者が置いた架空の電子書籍48冊。本ごとに「ふだんの1日の冊数」（本当の売れる力）を置き、
発売の日から数日は山が立って売れ、その後ふだんの売れ方に落ち着く形を式で置いて、1日の冊数を乱数で作る。
1日の見込み＝ふだんの1日の冊数 ×（1＋山の高さ × exp(−発売からの日数÷τ)）。τ は山の上乗せが約37%に減るまでの日数。
発売の日は、架空の1年（365日、月の日数はふつうの暦どおり）の1月1日〜10月31日から一様に選ぶ。
比べ方：①発売した月の冊数　②発売した月の1日あたり（売っていた日数で割る）　③発売から30日の冊数　④発売の翌月の冊数
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1252
SRC = "架空の電子書籍48冊（作成者が置いた売れる力と発売の山の形からの乱数、seed 1252）"
MDAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
MSTART = np.concatenate([[0], np.cumsum(MDAYS)[:-1]])
NB, HORIZON, TOP = 48, 100, 10
BASE = dict(peak=4.0, tau=7.0, sigma=0.5)
MEAS = ["m1_month", "m2_month_per_day", "m3_first30", "m4_next_month"]
MEAS_JA = {"m1_month": "①発売した月の冊数", "m2_month_per_day": "②発売した月の1日あたり",
           "m3_first30": "③発売から30日の冊数", "m4_next_month": "④発売の翌月の冊数"}


def curve(t, peak, tau):
    return 1 + peak * np.exp(-t / tau)


def measures_from_daily(rel, daily):
    """rel: 発売の日（0始まりの通し日）、daily: 発売の日からの1日の冊数（本×日）"""
    mon = np.searchsorted(MSTART, rel, side="right") - 1
    days_in_month = MSTART[mon] + MDAYS[mon] - rel          # 発売した月に売っていた日数
    nxt_start = MSTART[mon] + MDAYS[mon] - rel               # 翌月の初日は発売から何日目か
    nxt_len = MDAYS[mon + 1]
    t = np.arange(daily.shape[1])[None, :]
    m1 = np.sum(daily * (t < days_in_month[:, None]), 1)
    m2 = m1 / days_in_month
    m3 = np.sum(daily[:, :30], 1)
    m4 = np.sum(daily * ((t >= nxt_start[:, None]) & (t < (nxt_start + nxt_len)[:, None])), 1)
    return {"m1_month": m1, "m2_month_per_day": m2, "m3_first30": m3, "m4_next_month": m4}, mon, days_in_month


def one_set(rng, peak=4.0, tau=7.0, sigma=0.5):
    s = np.exp(np.log(2.0) + sigma * rng.standard_normal(NB))   # ふだんの1日の冊数（本当の売れる力）
    rel = rng.integers(0, MSTART[10] + MDAYS[10], NB)            # 1月1日〜10月31日
    t = np.arange(HORIZON)[None, :]
    daily = rng.poisson(s[:, None] * curve(t, peak, tau))
    m, mon, dim = measures_from_daily(rel, daily)
    return s, rel, m, mon, dim, daily


def concord(a, b):
    i, j = np.triu_indices(len(a), 1)
    return float(np.mean(np.sign(a[i] - a[j]) == np.sign(b[i] - b[j])))


def tophit(a, b, k=TOP):
    return len(set(np.argsort(-a)[:k]) & set(np.argsort(-b)[:k])) / k


def main():
    t0 = time.time()

    # 1) 式どおり：ふだんの1日の冊数が1冊の本を、30日の月の d 日に出したときの見込み
    rows = []
    for d in range(1, 31):
        sold = 31 - d                                     # 30日の月で、d 日に出すと売っていた日数
        tt = np.arange(200)
        lam = curve(tt, **{k: BASE[k] for k in ["peak", "tau"]})
        m1 = lam[:sold].sum()
        rows.append({"release_day": d, "days_on_sale": sold, "m1_month": round(m1, 3), "m2_month_per_day": round(m1 / sold, 3),
                     "m3_first30": round(lam[:30].sum(), 3), "m4_next_month_30": round(lam[sold:sold + 30].sum(), 3)})
    ex = pd.DataFrame(rows)
    ex.to_csv(RES / "expected_by_release_day.csv", index=False)
    e1, e25 = ex.iloc[0], ex.iloc[24]
    expected = {k: [float(e1[k]), float(e25[k]), round(float(e25[k] / e1[k]), 4)]
                for k in ["m1_month", "m2_month_per_day", "m3_first30", "m4_next_month_30"]}

    # 1回分（data に置く）
    s, rel, m, mon, dim, daily = one_set(np.random.default_rng([SEED, 0]), **BASE)
    d = pd.DataFrame({"book_id": np.arange(1, NB + 1), "true_daily": s.round(4), "release_dayofyear": rel + 1,
                      "release_month": mon + 1, "release_day": rel - MSTART[mon] + 1, "days_on_sale_in_month": dim})
    for k in MEAS:
        d[k] = np.round(m[k], 4)
    d.to_csv(DATA / "books_one_set.csv", index=False)

    # 2) 基本の置き方で300回
    reps, binrows = [], []
    for r in range(300):
        s, rel, m, mon, dim, _ = one_set(np.random.default_rng([SEED, 1, r]), **BASE)
        day = rel - MSTART[mon] + 1
        row = {"rep": r}
        for k in MEAS:
            row[f"concord_{k}"] = concord(m[k], s)
            row[f"top10_{k}"] = tophit(m[k], s)
        reps.append(row)
        for k in MEAS:
            for lo, hi, lab in [(1, 10, "1〜10日"), (11, 20, "11〜20日"), (21, 31, "21日〜末日")]:
                sel = (day >= lo) & (day <= hi)
                binrows.append({"rep": r, "measure": k, "bin": lab, "ratio_sum": float(np.sum(m[k][sel] / s[sel])), "n": int(sel.sum())})
    reps = pd.DataFrame(reps)
    reps.to_csv(RES / "reps_base.csv", index=False, float_format="%.6f")
    bd = pd.DataFrame(binrows).groupby(["measure", "bin"], sort=False)[["ratio_sum", "n"]].sum()
    bd["per_true_daily"] = (bd.ratio_sum / bd.n).round(3)
    bd = bd.reset_index()[["measure", "bin", "per_true_daily", "n"]]
    # 1〜10日を1とした比
    for k in MEAS:
        b0 = bd[(bd.measure == k) & (bd.bin == "1〜10日")].per_true_daily.values[0]
        bd.loc[bd.measure == k, "vs_1to10"] = (bd[bd.measure == k].per_true_daily / b0).round(4)
    bd.to_csv(RES / "by_release_day_bin.csv", index=False)
    head = {"concord_mean": {k: round(float(reps[f"concord_{k}"].mean()), 4) for k in MEAS},
            "top10_mean": {k: round(float(reps[f"top10_{k}"].mean()), 4) for k in MEAS},
            "pairs": int(NB * (NB - 1) / 2),
            "by_bin_vs_1to10": {k: {b: float(bd[(bd.measure == k) & (bd.bin == b)].vs_1to10.values[0])
                                    for b in ["1〜10日", "11〜20日", "21日〜末日"]} for k in MEAS}}

    # 3) 確かめ：山の高さ×山の減る速さ×本どうしの差（36通り、各40回）
    grid = []
    for peak in [0.0, 2.0, 4.0, 8.0]:
        for tau in [3.0, 7.0, 14.0]:
            for sigma in [0.3, 0.5, 0.8]:
                c = {k: [] for k in MEAS}; h = {k: [] for k in MEAS}
                for r in range(40):
                    s, rel, m, _, _, _ = one_set(np.random.default_rng([SEED, 2, int(peak), int(tau), int(sigma * 10), r]),
                                                 peak=peak, tau=tau, sigma=sigma)
                    for k in MEAS:
                        c[k].append(concord(m[k], s)); h[k].append(tophit(m[k], s))
                grid.append({"peak": peak, "tau": tau, "sigma": sigma,
                             **{f"concord_{k}": round(float(np.mean(c[k])), 4) for k in MEAS},
                             **{f"top10_{k}": round(float(np.mean(h[k])), 4) for k in MEAS}})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    best = gr[[f"concord_{k}" for k in MEAS]].idxmax(axis=1).str.replace("concord_", "")
    robust = {"settings": int(len(gr)),
              "concord_range": {k: [float(gr[f"concord_{k}"].min()), float(gr[f"concord_{k}"].max())] for k in MEAS},
              "top10_range": {k: [float(gr[f"top10_{k}"].min()), float(gr[f"top10_{k}"].max())] for k in MEAS},
              "m3_best_settings": int((best == "m3_first30").sum()),
              "m1_lowest_settings": int((gr[[f"concord_{k}" for k in MEAS]].idxmin(axis=1) == "concord_m1_month").sum()),
              "m3_not_best": gr[best != "m3_first30"][["peak", "tau", "sigma"]].to_dict("records"),
              "m3_not_best_winner": sorted(set(best[best != "m3_first30"])),
              "m3_not_best_gap_max": round(float((gr[[f"concord_{k}" for k in MEAS]].max(axis=1) - gr.concord_m3_first30)[best != "m3_first30"].max()), 4),
              "m1_not_lowest": gr[gr[[f"concord_{k}" for k in MEAS]].idxmin(axis=1) != "concord_m1_month"][["peak", "tau", "sigma"]].to_dict("records"),
              "m1_not_lowest_lowest_is": sorted(set(gr[[f"concord_{k}" for k in MEAS]].idxmin(axis=1)) - {"concord_m1_month"}),
              "mean_concord_when_no_peak": {k: float(gr[gr.peak == 0][f"concord_{k}"].mean().round(4)) for k in MEAS},
              "mean_top10_when_no_peak": {k: float(gr[gr.peak == 0][f"top10_{k}"].mean().round(4)) for k in MEAS},
              "m1_concord_by_sigma": {str(sg): [float(gr[gr.sigma == sg].concord_m1_month.min()), float(gr[gr.sigma == sg].concord_m1_month.max())]
                                      for sg in [0.3, 0.5, 0.8]},
              "m3_concord_by_sigma": {str(sg): [float(gr[gr.sigma == sg].concord_m3_first30.min()), float(gr[gr.sigma == sg].concord_m3_first30.max())]
                                      for sg in [0.3, 0.5, 0.8]}}

    out = {"headline": head, "expected_30day_month_day1_vs_day25": expected, "robust": robust,
           "setup": {"books": NB, "release_range": "1月1日〜10月31日", "base_daily_median": 2.0, **BASE, "reps": 300, "grid_reps": 40}}
    json.dump(out, open(RES / "a1252_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：式どおり。出した日ごとの見込み（ふだんの1日の冊数が1冊の本、30日の月）
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 3.8))
    ax = axs[0]
    ax.plot(ex.release_day, ex.m1_month, color=INK, marker="o", ms=3, label=MEAS_JA["m1_month"])
    ax.plot(ex.release_day, ex.m3_first30, color=BLUE, ls="--", label=MEAS_JA["m3_first30"])
    ax.plot(ex.release_day, ex.m4_next_month_30, color=ORANGE, marker="o", ms=3, label="④発売の翌月の冊数（翌月30日）")
    ax.set_ylim(0, 90); ax.set_xlabel("月の何日に出したか"); ax.set_ylabel("冊数の見込み")
    ax.legend(frameon=False, fontsize=7.5, loc="upper center")
    ax.set_title("冊数", fontsize=11)
    ax = axs[1]
    ax.plot(ex.release_day, ex.m2_month_per_day, color=GREEN, marker="o", ms=3, label=MEAS_JA["m2_month_per_day"])
    ax.axhline(ex.m3_first30[0] / 30, color=BLUE, ls="--", lw=1, label="③÷30")
    ax.set_ylim(0, 5.5); ax.set_xlabel("月の何日に出したか"); ax.set_ylabel("1日あたりの冊数の見込み")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    ax.set_title("1日あたり", fontsize=11)
    fig.suptitle("同じ力の本でも、出した日で見え方が変わる（式どおり、ふだん1日1冊・30日の月）", fontsize=12)
    fig.tight_layout()
    save(fig, "a1252_expected_by_day.png", SRC)

    # 図2：出した日の区切りごとの、本当の力1あたりの値（1〜10日を1とした比、300回）
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    x = np.arange(4); bins = ["1〜10日", "11〜20日", "21日〜末日"]; cols = [LIGHT, BLUE, INK]
    for i, b in enumerate(bins):
        v = [float(bd[(bd.measure == k) & (bd.bin == b)].vs_1to10.values[0]) for k in MEAS]
        ax.bar(x + (i - 1) * 0.26, v, 0.26, color=cols[i], label=f"{b}に出した本")
        for xi, vv in zip(x, v):
            ax.text(xi + (i - 1) * 0.26, vv + 0.04, f"{vv:g}", ha="center", fontsize=7)
    ax.axhline(1, color=GRAY, lw=0.8, ls="--")
    ax.set_xticks(x); ax.set_xticklabels([MEAS_JA[k] for k in MEAS], fontsize=8.5)
    ax.set_ylim(0, 2.6); ax.set_ylabel("本当の力1あたりの値（1〜10日に出した本＝1）", fontsize=9.5)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("月の後半に出した本は、①で低く、②と④で高く見える（300回）", fontsize=12)
    save(fig, "a1252_by_release_bin.png", SRC)

    # 図3：確かめ。36通りの、上位10冊の当たり
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    gs = gr.sort_values(["peak", "tau", "sigma"]).reset_index(drop=True)
    gx = np.arange(len(gs)); colm = {"m1_month": INK, "m2_month_per_day": GREEN, "m3_first30": BLUE, "m4_next_month": ORANGE}
    for k in MEAS:
        ax.plot(gx, gs[f"top10_{k}"] * 100, marker="o", ms=4, lw=0, color=colm[k], label=MEAS_JA[k])
    for kk in [9, 18, 27]:
        ax.axvline(kk - 0.5, color=GRAY, lw=0.8, ls=":")
    for kk, p in enumerate([0, 2, 4, 8]):
        ax.text(kk * 9 + 4, 102, f"山の高さ{p}", ha="center", fontsize=8)
    ax.set_xticks(gx); ax.set_xticklabels([f"{int(t)}" for t in gs.tau], fontsize=6.5)
    ax.set_xlabel("36通り（下の数字は、山の上乗せが約37%に減るまでの日数。同じ数字の中は本どうしの差が小・中・大の順）", fontsize=8.5)
    ax.set_ylim(0, 108); ax.set_ylabel("本当の上位10冊の当たり（%、各40回）", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    ax.set_title("③の当たりは置き方によらず高く、①②④は山の形で動く", fontsize=12)
    save(fig, "a1252_grid.png", SRC, y=-0.2)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
