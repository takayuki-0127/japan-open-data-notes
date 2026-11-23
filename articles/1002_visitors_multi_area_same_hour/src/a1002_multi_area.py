"""1002 同じ時間に複数の場所にいる人を、どう数えるのか？（架空のデータ）

架空の展示イベント（1日、10:00〜18:00）。会場はエリア4つ（A：ステージ、B〜D：展示・物販・飲食）。
来場者1人ずつの動き（どのエリアに何時から何時までいたか）を作成者が乱数で置き、
「1時間ごとに、エリアごとの人数を足した数」が、その1時間に会場にいた本当の人数とどれだけずれるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1002
SRC = "架空の展示イベントの来場者の動き（作成者が乱数で作成、seed 1002）"
OPEN = 480                       # 10:00〜18:00 を分で
N_PEOPLE = 6000
SHOW_FROM, SHOW_TO, SHOW_END = 225, 240, 270   # 13:45〜14:00 に A へ移り、14:30 まで
HOURS = [f"{10 + h}時台" for h in range(8)]


def make_day(rng, n=N_PEOPLE, dwell=25.0, n_areas=4, show=0.4):
    """1日分の来場者の動き。戻り値は 1行＝1人が1つのエリアにいた区間（person, area, start, end）"""
    w = np.array([0.3] + [0.7 / (n_areas - 1)] * (n_areas - 1))
    cw = np.cumsum(w)
    mix = rng.random(n) < 0.7
    arr = np.where(mix, rng.normal(120, 70, n), rng.uniform(0, 400, n))
    arr = np.clip(arr, 0, 420)
    stay = np.maximum(rng.gamma(3, 50, n), 20)
    leave = np.minimum(arr + stay, OPEN)
    sw = rng.uniform(SHOW_FROM, SHOW_TO, n)
    s_end = SHOW_END + rng.uniform(0, 10, n)
    joins = (rng.random(n) < show) & (arr <= sw) & (sw < leave)
    leave = np.where(joins, np.minimum(np.maximum(leave, s_end), OPEN), leave)
    # 乱数はまとめて引いておく（エリアの選び方と、1回の滞在の長さ）
    m = int(4 * (OPEN / dwell) + 40)
    u = rng.random((n, m))
    d = np.maximum(rng.gamma(2, dwell / 2, (n, m)), 3)
    P, A, S, E = [], [], [], []

    def pick(x, cur):
        k = int(np.searchsorted(cw, x * cw[-1]))
        return k

    for i in range(n):
        t, j, done = arr[i], 0, False
        cur = pick(u[i, j], -1); j += 1
        while t < leave[i] - 1e-9:
            e = min(t + d[i, j], leave[i])
            if joins[i] and not done and sw[i] < e:
                if cur == 0:
                    P.append(i); A.append(0); S.append(t); E.append(s_end[i])
                else:
                    if sw[i] > t:
                        P.append(i); A.append(cur); S.append(t); E.append(sw[i])
                    P.append(i); A.append(0); S.append(sw[i]); E.append(s_end[i])
                t, done = s_end[i], True
                cur = 0
            else:
                P.append(i); A.append(cur); S.append(t); E.append(e)
                t = e
            # 次のエリア（いまと違うところ）
            nxt = cur
            while nxt == cur:
                nxt = pick(u[i, j % m], cur); j += 1
                if n_areas == 1:
                    break
            cur = nxt
    return pd.DataFrame({"person": P, "area": A, "start": S, "end": E})


def slot_counts(v, t0, t1):
    msk = (v.start.values < t1) & (v.end.values > t0)
    p, a = v.person.values[msk], v.area.values[msk]
    U = len(np.unique(p))
    S = len(np.unique(p * 16 + a))
    Ent = int(((v.start.values >= t0) & (v.start.values < t1)).sum())
    return U, S, Ent


def occ(v, t, area=None):
    msk = (v.start.values <= t) & (v.end.values > t)
    if area is not None:
        msk &= v.area.values == area
    return int(msk.sum())


def per_area_in_slot(v, t0, t1):
    """その区切りにいた人ごとの、いたエリアの数"""
    msk = (v.start.values < t1) & (v.end.values > t0)
    g = pd.DataFrame({"p": v.person.values[msk], "a": v.area.values[msk]}).drop_duplicates()
    return g.groupby("p").size()


def hourly(v, n_areas=4):
    rows = []
    for h in range(8):
        t0, t1 = 60 * h, 60 * (h + 1)
        U, S, Ent = slot_counts(v, t0, t1)
        tk = [t0 + 60 * k / n_areas for k in range(n_areas)]
        stag = sum(occ(v, t, k) for k, t in enumerate(tk))
        true_mean = np.mean([occ(v, t) for t in tk])
        snap = sum(occ(v, t0 + 30, k) for k in range(n_areas))
        rows.append({"hour": HOURS[h], "U": U, "S": S, "Ent": Ent, "snap_sum": snap, "snap_true": occ(v, t0 + 30),
                     "stag_sum": stag, "stag_true": true_mean})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)

    # 1) 基本の置き方で20日分
    days = []
    worlds = [make_day(np.random.default_rng(SEED * 100 + r)) for r in range(20)]
    one = worlds[0]
    for r, v in enumerate(worlds):
        h = hourly(v)
        h["day"] = r
        U_day = v.person.nunique()
        S_day = len(v[["person", "area"]].drop_duplicates())
        h["U_day"], h["S_day"] = U_day, S_day
        days.append(h)
    hd = pd.concat(days, ignore_index=True)
    one.assign(area=one.area.map(dict(enumerate("ABCD")))).to_csv(DATA / "visits_day1.csv", index=False,
                                                                     float_format="%.2f")

    hd["ratio_S"] = hd.S / hd.U
    hd["ratio_E"] = hd.Ent / hd.U
    hd["stag_err_pct"] = (hd.stag_sum / hd.stag_true - 1) * 100
    hd["snap_diff"] = hd.snap_sum - hd.snap_true
    hd["f_day"] = hd.S_day / hd.U_day
    hd["dayfactor_err_pct"] = (hd.S / hd.f_day / hd.U - 1) * 100
    f13 = hd[hd.hour == "13時台"].set_index("day").ratio_S
    hd["f13"] = hd.day.map(f13)
    hd["f13_err_pct"] = (hd.S / hd.f13 / hd.U - 1) * 100
    tab = hd.groupby("hour", sort=False).agg(U=("U", "mean"), S=("S", "mean"), Ent=("Ent", "mean"),
                                              ratio_S=("ratio_S", "mean"), ratio_S_min=("ratio_S", "min"),
                                              ratio_S_max=("ratio_S", "max"), ratio_E=("ratio_E", "mean"),
                                              stag_err_pct=("stag_err_pct", "mean"),
                                              stag_err_min=("stag_err_pct", "min"), stag_err_max=("stag_err_pct", "max"),
                                              snap_absdiff_max=("snap_diff", lambda x: int(np.abs(x).max())),
                                              dayfactor_err_pct=("dayfactor_err_pct", "mean"),
                                              dayfactor_err_min=("dayfactor_err_pct", "min"),
                                              dayfactor_err_max=("dayfactor_err_pct", "max"),
                                              f13_err_pct=("f13_err_pct", "mean"), f13_err_min=("f13_err_pct", "min"),
                                              f13_err_max=("f13_err_pct", "max")).round(3)
    tab.to_csv(RES / "hourly_base_20days.csv")
    dd = hd.drop_duplicates("day")
    # 1日の合計：エリアごとの「その日に来た人」を足した数 ÷ 実人数 ＝ 1人が訪れたエリアの数の平均（式どおり）
    mean_areas = []
    for v in worlds:
        mean_areas.append(v[["person", "area"]].drop_duplicates().groupby("person").size().mean())
    daily = {"U_day_mean": round(float(dd.U_day.mean()), 1), "S_day_mean": round(float(dd.S_day.mean()), 1),
             "ratio_day_mean": round(float((dd.S_day / dd.U_day).mean()), 3),
             "ratio_day_min": round(float((dd.S_day / dd.U_day).min()), 3),
             "ratio_day_max": round(float((dd.S_day / dd.U_day).max()), 3),
             "mean_areas_per_person": round(float(np.mean(mean_areas)), 3),
             "identity_maxdiff": float(np.max(np.abs(dd.S_day.values / dd.U_day.values - np.array(mean_areas)))),
             "sum_hourly_U_over_U_day": round(float(hd.groupby("day").U.sum().mean() / dd.U_day.mean()), 3),
             "sum_hourly_S_over_U_day": round(float(hd.groupby("day").S.sum().mean() / dd.U_day.mean()), 3),
             "snap_absdiff_max_all": int(np.abs(hd.snap_diff).max())}

    # 2) 1日目で、1時間ごとの「いたエリアの数」を、その時間にいた人300人から見積もって割る
    corr = []
    for h in range(8):
        t0, t1 = 60 * h, 60 * (h + 1)
        k = per_area_in_slot(one, t0, t1)
        U, S, _ = slot_counts(one, t0, t1)
        kv = k.values.astype(float)
        formula_b = (kv.mean() ** 2 / (kv ** 2).mean() - 1) * 100   # エリアの数に比例して選ぶときの式の値
        for rep in range(500):
            idx = rng.choice(len(kv), 300, replace=False)
            f = kv[idx].mean()
            # 偏った300人：いたエリアの多い人ほど選ばれやすい（エリアの数に比例）
            idx2 = rng.choice(len(kv), 300, replace=False, p=kv / kv.sum())
            f2 = kv[idx2].mean()
            corr.append({"hour": HOURS[h], "rep": rep, "err_random_pct": (S / f / U - 1) * 100,
                         "err_biased_pct": (S / f2 / U - 1) * 100, "formula_biased_pct": formula_b,
                         "share_k1": float((kv == 1).mean())})
    cd = pd.DataFrame(corr)
    ctab = cd.groupby("hour", sort=False).agg(rand_p5=("err_random_pct", lambda x: x.quantile(.05)),
                                               rand_p95=("err_random_pct", lambda x: x.quantile(.95)),
                                               rand_mean=("err_random_pct", "mean"),
                                               biased_mean=("err_biased_pct", "mean"),
                                               formula_biased=("formula_biased_pct", "first"),
                                               share_one_area=("share_k1", "first")).round(3)
    ctab["biased_minus_formula"] = (ctab.biased_mean - ctab.formula_biased).round(2)
    ctab.to_csv(RES / "correction_sample300_day1.csv")

    # 3) 区切りの長さ（基本の20日分）
    slots = []
    for L in [15, 30, 60, 120, 240, 480]:
        su, ss = 0, 0
        for v in worlds:
            for t0 in range(0, OPEN, L):
                U, S, _ = slot_counts(v, t0, t0 + L)
                su += U; ss += S
        slots.append({"slot_min": L, "ratio_sumS_over_sumU": round(ss / su, 3)})
    sl = pd.DataFrame(slots)
    sl.to_csv(RES / "by_slot_length.csv", index=False)

    # 4) 確かめ：1回の滞在の長さ × エリアの数 × ステージへ移る人の割合（各1日）
    grid = []
    gi = 0
    for dwell in [10, 25, 50]:
        for na in [2, 4, 8]:
            for sh in [0.0, 0.4, 0.7]:
                v = make_day(np.random.default_rng(SEED * 7 + gi), dwell=dwell, n_areas=na, show=sh); gi += 1
                h = hourly(v, na)
                r_h = h.S / h.U
                f_day = len(v[["person", "area"]].drop_duplicates()) / v.person.nunique()
                err = (h.S / f_day / h.U - 1) * 100
                e13 = (h.S / r_h.iloc[3] / h.U - 1) * 100
                st = (h.stag_sum / h.stag_true - 1) * 100
                grid.append({"dwell_min": dwell, "n_areas": na, "show_share": sh, "ratio_day": round(f_day, 3),
                             "ratio_hour_min": round(float(r_h.min()), 3), "ratio_hour_max": round(float(r_h.max()), 3),
                             "dayfactor_abs_err_max_pct": round(float(np.abs(err).max()), 2),
                             "f13_abs_err_max_pct": round(float(np.abs(e13).max()), 2),
                             "stag_err_14h_pct": round(float(st.iloc[4]), 2),
                             "stag_abs_err_max_other_pct": round(float(np.abs(st.drop(index=4)).max()), 2),
                             "ratio_13h": round(float(r_h.iloc[3]), 3), "ratio_14h": round(float(r_h.iloc[4]), 3)})
    gd = pd.DataFrame(grid)
    gd.to_csv(RES / "grid_dwell_areas_show.csv", index=False)

    out = {"daily_base_20days": daily,
           "hourly_base_20days": tab.reset_index().to_dict("records"),
           "correction_sample300_day1": ctab.reset_index().to_dict("records"),
           "by_slot_length": sl.to_dict("records"),
           "grid_summary": {"ratio_day_min": float(gd.ratio_day.min()), "ratio_day_max": float(gd.ratio_day.max()),
                            "ratio_hour_min": float(gd.ratio_hour_min.min()), "ratio_hour_max": float(gd.ratio_hour_max.max()),
                            "dayfactor_abs_err_max_min": float(gd.dayfactor_abs_err_max_pct.min()),
                            "dayfactor_abs_err_max_max": float(gd.dayfactor_abs_err_max_pct.max()),
                            "dayfactor_abs_err_max_show0_max": float(gd[gd.show_share == 0].dayfactor_abs_err_max_pct.max()),
                            "dayfactor_abs_err_max_show0_min": float(gd[gd.show_share == 0].dayfactor_abs_err_max_pct.min()),
                            "f13_abs_err_max_min": float(gd.f13_abs_err_max_pct.min()),
                            "f13_abs_err_max_max": float(gd.f13_abs_err_max_pct.max()),
                            "stag_err_14h_min": float(gd.stag_err_14h_pct.min()), "stag_err_14h_max": float(gd.stag_err_14h_pct.max()),
                            "stag_err_14h_show0_min": float(gd[gd.show_share == 0].stag_err_14h_pct.min()),
                            "stag_err_14h_show0_max": float(gd[gd.show_share == 0].stag_err_14h_pct.max()),
                            "stag_err_14h_show07_min": float(gd[gd.show_share == 0.7].stag_err_14h_pct.min()),
                            "stag_err_14h_show07_max": float(gd[gd.show_share == 0.7].stag_err_14h_pct.max()),
                            "stag_err_14h_show_ge04_areas_ge4_min": float(gd[(gd.show_share >= 0.4) & (gd.n_areas >= 4)].stag_err_14h_pct.min()),
                            "stag_err_14h_show_ge04_areas_ge4_max": float(gd[(gd.show_share >= 0.4) & (gd.n_areas >= 4)].stag_err_14h_pct.max()),
                            "stag_err_14h_areas2_min": float(gd[gd.n_areas == 2].stag_err_14h_pct.min()),
                            "stag_err_14h_areas2_max": float(gd[gd.n_areas == 2].stag_err_14h_pct.max()),
                            "stag_abs_err_other_max_areas4": float(gd[gd.n_areas == 4].stag_abs_err_max_other_pct.max()),
                            "stag_abs_err_other_max_areas8": float(gd[gd.n_areas == 8].stag_abs_err_max_other_pct.max()),
                            "n": int(len(gd))},
           "grid": gd.to_dict("records")}
    json.dump(out, open(RES / "a1002_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1時間ごとの3つの数（20日の平均）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(8)
    ax.bar(x - 0.27, tab.U, 0.27, color=INK, label="その1時間に会場にいた本当の人数")
    ax.bar(x, tab.S, 0.27, color=ORANGE, label="エリアごとの「いた人」を足した数")
    ax.bar(x + 0.27, tab.Ent, 0.27, color=LIGHT, label="エリアの入口で数えた入場を足した数")
    for i in range(8):
        ax.text(i, tab.S.iloc[i] + 60, f"{tab.ratio_S.iloc[i]:.2f}倍", ha="center", fontsize=8, color=ORANGE)
    ax.set_xticks(x); ax.set_xticklabels(tab.index, fontsize=9)
    ax.set_ylabel("人（20日の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_ylim(0, tab.S.max() * 1.25)
    ax.set_title("エリアの人数を足すと、1時間に何か所も回った人を何度も数える")
    save(fig, "a1002_hourly.png", SRC)

    # 図2：区切りの長さと、足した数÷本当の人数
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(sl.slot_min, sl.ratio_sumS_over_sumU, marker="o", color=BLUE)
    for a_, b_ in zip(sl.slot_min, sl.ratio_sumS_over_sumU):
        ax.text(a_, b_ + 0.06, f"{b_:.2f}倍", ha="center", fontsize=9)
    ax.set_xscale("log"); ax.set_xticks(sl.slot_min); ax.set_xticklabels([f"{m}分" for m in sl.slot_min])
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.axhline(1, color=GRAY, lw=1, ls="--"); ax.text(15, 1.04, "本当の人数（1倍）", color=GRAY, fontsize=9)
    ax.set_ylim(0.8, sl.ratio_sumS_over_sumU.max() + 0.4)
    ax.set_xlabel("数える区切りの長さ（対数の目盛り。480分＝1日）")
    ax.set_ylabel("エリアの合計 ÷ 本当の人数")
    ax.set_title("区切りが長いほど、足した数は本当の人数より大きくなる（基本の置き方、20日）")
    save(fig, "a1002_slot_length.png", SRC)

    # 図3：割り戻しの誤差（1日の倍率で割る、その時間の300人で割る）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(x, tab.f13_err_pct.values, marker="o", color=ORANGE, label="13時台に調べた倍率で、どの時間も割る（20日の平均）")
    ax.fill_between(x, ctab.rand_p5, ctab.rand_p95, color=LIGHT, alpha=.7, label="その時間にいた300人の倍率で割る（1日目、500回の5〜95%）")
    ax.plot(x, ctab.rand_mean, color=BLUE, lw=1)
    ax.plot(x, ctab.biased_mean, marker="s", color=GREEN, ls="--", label="300人がよく回る人に偏ったとき（1日目、500回の平均）")
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xticks(x); ax.set_xticklabels(HOURS, fontsize=9)
    ax.set_ylabel("割り戻した人数の誤差（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("ほかの時間の倍率で割るとずれ、その時間の人から見積もると近づく")
    save(fig, "a1002_correction.png", SRC)
    # 図4：エリアを15分ずつずらして数えた合計の誤差
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    ax.bar(x, tab.stag_err_pct, color=[ORANGE if i == 4 else BLUE for i in range(8)])
    ax.errorbar(x, tab.stag_err_pct, yerr=[tab.stag_err_pct - tab.stag_err_min, tab.stag_err_max - tab.stag_err_pct],
                fmt="none", ecolor=INK, lw=1, capsize=3)
    for i in range(8):
        v_ = tab.stag_err_pct.iloc[i]
        ax.text(i, tab.stag_err_max.iloc[i] + 0.8, f"{v_:+.1f}%", ha="center", fontsize=8.5)
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xticks(x); ax.set_xticklabels(HOURS, fontsize=9)
    ax.set_ylim(tab.stag_err_min.min() - 2, tab.stag_err_max.max() + 4)
    ax.set_ylabel("本当の同時の人数との差（%）")
    ax.set_title("A→B→C→Dと15分ずつずらして数えると、ステージの終わる回で二重に数える（20日、線は最小〜最大）", fontsize=11)
    save(fig, "a1002_staggered.png", SRC)
    print(json.dumps(out["daily_base_20days"], ensure_ascii=False, indent=1))
    print(tab.to_string())
    print(ctab.to_string())
    print(sl.to_string())
    print(gd.to_string())


if __name__ == "__main__":
    main()
