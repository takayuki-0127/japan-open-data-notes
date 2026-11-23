"""1003 数取りの人による数え間違いは、どれだけ出るのか？（架空のデータ）

架空の展示施設（入口2つ：東口・西口、9:00〜17:00）。入口を通る本当の人数を1分ごとに作成者が乱数で置き、
数取りの係（8人、1時間ずつ交代）が手で数えたときの数え漏れ・二度押しで、
1日の合計・15分ごとの数・ピーク・入口どうしの比べがどれだけずれるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1003
SRC = "架空の展示施設の入口の人数と数取り（作成者が乱数で作成、seed 1003）"
T = 480                      # 9:00〜17:00 を分で
SLOT = 15
NS = T // SLOT
N_STAFF = 8
MG = 0.8                     # 組の人数 = 1 + ポアソン(0.8)（平均1.8人）
BASE = dict(b=0.02, slope=1.0, dbl=0.005, spread=0.5, group=0.15)
LAM = 3 + 22 * np.exp(-((np.arange(T) - 210) / 70.0) ** 2)   # 1分あたりの平均人数（12:30 ごろがピーク）


def staff_pool(rng, b, spread):
    return b * np.exp(rng.normal(0, spread, N_STAFF) - spread ** 2 / 2)


def count_entrance(rng, staff_b_by_min, p, checker_b_by_min=None):
    """1つの入口の1日。戻り値：本当・数えた・数えた数の期待値（1分ごと）と、検算の人の数"""
    G = rng.poisson(LAM / (1 + MG))
    minute = np.repeat(np.arange(T), G)
    g = 1 + rng.poisson(MG, minute.size)
    true = np.bincount(minute, weights=g, minlength=T)
    flow = true[minute]

    def click(bm):
        pm = np.minimum(bm[minute] * (1 + p["slope"] * flow / 10) * (1 + p["group"] * (g - 1)), 0.9)
        c = rng.binomial(g, 1 - pm)
        c = c + rng.binomial(c, p["dbl"])
        ex = g * (1 - pm) * (1 + p["dbl"])
        return np.bincount(minute, weights=c, minlength=T), np.bincount(minute, weights=ex, minlength=T)

    cnt, ex = click(staff_b_by_min)
    chk = click(checker_b_by_min)[0] if checker_b_by_min is not None else None
    return true, cnt, ex, chk


def sim_day(rng, pool, p):
    perm = rng.permutation(N_STAFF)
    hour = np.arange(T) // 60
    east_staff = perm[hour % 8]
    west_staff = perm[(hour + 4) % 8]
    chk_staff = perm[(hour + 2) % 8]
    tE, cE, xE, kE = count_entrance(rng, pool[east_staff], p, pool[chk_staff])
    tW, cW, xW, _ = count_entrance(rng, pool[west_staff], p)
    return dict(tE=tE, cE=cE, xE=xE, kE=kE, tW=tW, cW=cW, xW=xW, sE=east_staff, sW=west_staff)


def slots(x):
    return x.reshape(NS, SLOT).sum(1)


def calib(rng, t, c, kind):
    """15分の区切り4つを録画で数え直し、本当÷数えた の比で1日の合計を直す"""
    ts, cs = slots(t), slots(c)
    if kind == "random":
        idx = rng.choice(NS, 4, replace=False)
    else:                        # 開館直後の1時間（空いている時間）
        idx = np.arange(4)
    f = ts[idx].sum() / cs[idx].sum()
    return c.sum() * f / t.sum() - 1


def run(rng, pool, p, n_days, keep_slots=False):
    rows, slot_rows = [], []
    for dday in range(n_days):
        d = sim_day(rng, pool, p)
        tot_t, tot_c = d["tE"].sum() + d["tW"].sum(), d["cE"].sum() + d["cW"].sum()
        tot_x = d["xE"].sum() + d["xW"].sum()
        sE_t, sE_c = slots(d["tE"]), slots(d["cE"])
        pk_t, pk_c = sE_t.argmax(), sE_c.argmax()
        rows.append({"day": dday,
                     "err_total": tot_c / tot_t - 1, "err_expected": tot_x / tot_t - 1,
                     "err_east": d["cE"].sum() / d["tE"].sum() - 1, "err_west": d["cW"].sum() / d["tW"].sum() - 1,
                     "ew_true": d["tE"].sum() / d["tW"].sum() - 1, "ew_count": d["cE"].sum() / d["cW"].sum() - 1,
                     "peak_ratio": sE_c.max() / sE_t.max(), "peak_slot_moved": int(pk_t != pk_c),
                     "peak_err_at_true_peak": sE_c[pk_t] / sE_t[pk_t] - 1,
                     "peak_to_mean_true": sE_t.max() / sE_t.mean(), "peak_to_mean_count": sE_c.max() / sE_c.mean(),
                     "chk_diff": abs(d["cE"].sum() - d["kE"].sum()) / d["tE"].sum(),
                     "chk_avg_err": abs((d["cE"].sum() + d["kE"].sum()) / 2 / d["tE"].sum() - 1),
                     "chk_avg_signed": (d["cE"].sum() + d["kE"].sum()) / 2 / d["tE"].sum() - 1,
                     "cal_random": calib(rng, d["tE"], d["cE"], "random"),
                     "cal_offpeak": calib(rng, d["tE"], d["cE"], "offpeak")})
        if keep_slots:
            for s in range(NS):
                slot_rows.append({"day": dday, "slot": s, "true": sE_t[s], "count": sE_c[s]})
        if dday == 0:
            first = d
    return pd.DataFrame(rows), (pd.DataFrame(slot_rows) if keep_slots else None), first


def q(x, a):
    return round(float(np.quantile(x, a)) * 100, 3)


def main():
    rng = np.random.default_rng(SEED)
    pool = staff_pool(rng, BASE["b"], BASE["spread"])
    df, sl, first = run(rng, pool, BASE, 500, keep_slots=True)
    df.round(6).to_csv(RES / "days_base_500.csv", index=False)

    # 1日目の1分ごと（data）
    m = pd.DataFrame({"minute": np.tile(np.arange(T), 2), "entrance": ["東口"] * T + ["西口"] * T,
                      "true": np.r_[first["tE"], first["tW"]].astype(int), "count": np.r_[first["cE"], first["cW"]].astype(int),
                      "staff": np.r_[first["sE"], first["sW"]] + 1})
    m.to_csv(DATA / "day1_minutes.csv", index=False)
    pd.DataFrame({"staff": np.arange(1, N_STAFF + 1), "base_miss": pool.round(5)}).to_csv(DATA / "staff.csv", index=False)

    # 15分ごとの誤差を、流れの多さで分ける
    sl["flow_per_min"] = sl["true"] / SLOT
    sl["err"] = sl["count"] / sl["true"] - 1
    bins = [0, 5, 10, 15, 20, 100]
    labels = ["5人未満", "5〜10人", "10〜15人", "15〜20人", "20人以上"]
    sl["flow_bin"] = pd.cut(sl.flow_per_min, bins, right=False, labels=labels)
    st = sl.groupby("flow_bin", observed=True).err.agg(n="size", mean="mean", p5=lambda x: x.quantile(.05),
                                                     p95=lambda x: x.quantile(.95))
    st[["mean", "p5", "p95"]] = (st[["mean", "p5", "p95"]] * 100).round(3)
    st.to_csv(RES / "slot_error_by_flow.csv")

    rand_part = df.err_total - df.err_expected
    base = {"staff_base_miss": [round(float(v), 5) for v in pool], "staff_base_miss_mean": round(float(pool.mean()), 5),
            "staff_base_miss_min_pct": round(float(pool.min()) * 100, 3), "staff_base_miss_max_pct": round(float(pool.max()) * 100, 3),
            "true_day1_both": None,
            "err_total_mean_pct": round(float(df.err_total.mean()) * 100, 3),
            "err_total_p5_pct": q(df.err_total, .05), "err_total_p95_pct": q(df.err_total, .95),
            "err_expected_mean_pct": round(float(df.err_expected.mean()) * 100, 3),
            "sim_minus_expected_mean_pct": round(float(rand_part.mean()) * 100, 4),
            "sd_random_part_pct": round(float(rand_part.std()) * 100, 3),
            "sd_expected_part_pct": round(float(df.err_expected.std()) * 100, 3),
            "err_east_mean_pct": round(float(df.err_east.mean()) * 100, 3),
            "err_east_p5_pct": q(df.err_east, .05), "err_east_p95_pct": q(df.err_east, .95),
            "peak_ratio_mean_pct": round((float(df.peak_ratio.mean()) - 1) * 100, 3),
            "peak_err_at_true_peak_mean_pct": round(float(df.peak_err_at_true_peak.mean()) * 100, 3),
            "peak_slot_moved_share_pct": round(float(df.peak_slot_moved.mean()) * 100, 1),
            "peak_to_mean_true": round(float(df.peak_to_mean_true.mean()), 3),
            "peak_to_mean_count": round(float(df.peak_to_mean_count.mean()), 3),
            "ew_true_absmean_pct": round(float(df.ew_true.abs().mean()) * 100, 3),
            "ew_count_absmean_pct": round(float(df.ew_count.abs().mean()) * 100, 3),
            "ew_error_abs_gt2_share_pct": round(float(((df.ew_count - df.ew_true).abs() > 0.02).mean()) * 100, 1),
            "ew_error_p5_pct": q(df.ew_count - df.ew_true, .05), "ew_error_p95_pct": q(df.ew_count - df.ew_true, .95),
            "chk_diff_mean_pct": round(float(df.chk_diff.mean()) * 100, 3),
            "chk_avg_abs_err_mean_pct": round(float(df.chk_avg_err.mean()) * 100, 3),
            "chk_avg_signed_mean_pct": round(float(df.chk_avg_signed.mean()) * 100, 3),
            "chk_diff_lt_avgerr_share_pct": round(float((df.chk_diff < df.chk_avg_err).mean()) * 100, 1),
            "cal_random_mean_pct": round(float(df.cal_random.mean()) * 100, 3),
            "cal_random_p5_pct": q(df.cal_random, .05), "cal_random_p95_pct": q(df.cal_random, .95),
            "cal_offpeak_mean_pct": round(float(df.cal_offpeak.mean()) * 100, 3),
            "cal_offpeak_p5_pct": q(df.cal_offpeak, .05), "cal_offpeak_p95_pct": q(df.cal_offpeak, .95)}
    tm = pd.read_csv(DATA / "day1_minutes.csv")
    base["true_day1_both"] = int(tm["true"].sum())   # 1日目の2入口の本当の合計（参考）

    # 確かめ：数え漏れの基本の割合 × 流れによる増え方 × 二度押し（27通り、各100日、係の8人の比は基本と同じ）
    grid = []
    gi = 0
    for b in [0.01, 0.02, 0.04]:
        for s in [0.0, 1.0, 2.0]:
            for dbl in [0.0, 0.005, 0.02]:
                p = dict(BASE, b=b, slope=s, dbl=dbl)
                r2 = np.random.default_rng(SEED * 10 + gi); gi += 1
                pl = pool * (b / BASE["b"])          # 係どうしの比は基本と同じにして、水準だけ変える
                g, _, _ = run(r2, pl, p, 100)
                grid.append({"base_miss": b, "slope": s, "double": dbl,
                             "err_total_mean_pct": round(float(g.err_total.mean()) * 100, 3),
                             "err_total_p5_pct": q(g.err_total, .05), "err_total_p95_pct": q(g.err_total, .95),
                             "peak_ratio_mean_pct": round((float(g.peak_ratio.mean()) - 1) * 100, 3),
                             "cal_random_p5_pct": q(g.cal_random, .05), "cal_random_p95_pct": q(g.cal_random, .95),
                             "cal_offpeak_mean_pct": round(float(g.cal_offpeak.mean()) * 100, 3)})
    gd = pd.DataFrame(grid)
    gd.to_csv(RES / "grid_miss_slope_double.csv", index=False)

    # 確かめ：係どうしの差（ばらつき 0・0.5・1.0）、各200日、係は5回作り直す
    spr = []
    for sp in [0.0, 0.5, 1.0]:
        parts = []
        for k in range(5):
            r3 = np.random.default_rng(SEED * 100 + int(sp * 10) * 10 + k)
            pl = staff_pool(r3, BASE["b"], sp)
            g, _, _ = run(r3, pl, dict(BASE, spread=sp), 40)
            parts.append(g)
        g = pd.concat(parts)
        spr.append({"spread": sp, "err_total_p5_pct": q(g.err_total, .05), "err_total_p95_pct": q(g.err_total, .95),
                    "ew_error_abs_gt2_share_pct": round(float(((g.ew_count - g.ew_true).abs() > 0.02).mean()) * 100, 1),
                    "chk_diff_mean_pct": round(float(g.chk_diff.mean()) * 100, 3),
                    "chk_avg_abs_err_mean_pct": round(float(g.chk_avg_err.mean()) * 100, 3)})
    sp_df = pd.DataFrame(spr)
    sp_df.to_csv(RES / "by_staff_spread.csv", index=False)

    out = {"base_500days": base, "slot_error_by_flow": st.reset_index().to_dict("records"),
           "grid_summary": {"err_total_mean_min": float(gd.err_total_mean_pct.min()), "err_total_mean_max": float(gd.err_total_mean_pct.max()),
                            "peak_ratio_min": float(gd.peak_ratio_mean_pct.min()), "peak_ratio_max": float(gd.peak_ratio_mean_pct.max()),
                            "peak_ratio_slope0_min": float(gd[gd.slope == 0].peak_ratio_mean_pct.min()),
                            "peak_ratio_slope0_max": float(gd[gd.slope == 0].peak_ratio_mean_pct.max()),
                            "cal_random_p5_min": float(gd.cal_random_p5_pct.min()), "cal_random_p95_max": float(gd.cal_random_p95_pct.max()),
                            "cal_offpeak_mean_min": float(gd.cal_offpeak_mean_pct.min()), "cal_offpeak_mean_max": float(gd.cal_offpeak_mean_pct.max()),
                            "cal_offpeak_mean_slope0_min": float(gd[gd.slope == 0].cal_offpeak_mean_pct.min()),
                            "cal_offpeak_mean_slope0_max": float(gd[gd.slope == 0].cal_offpeak_mean_pct.max()),
                            "cal_offpeak_mean_slope_pos_min": float(gd[gd.slope > 0].cal_offpeak_mean_pct.min()),
                            "cal_offpeak_mean_slope_pos_max": float(gd[gd.slope > 0].cal_offpeak_mean_pct.max()),
                            "n": int(len(gd))},
           "grid": gd.to_dict("records"), "by_staff_spread": sp_df.to_dict("records")}
    json.dump(out, open(RES / "a1003_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1日目の東口、15分ごと
    ts, cs = slots(first["tE"]), slots(first["cE"])
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(7.6, 5.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    x = np.arange(NS)
    ax.bar(x, ts, color=LIGHT, label="本当に通った人数")
    ax.plot(x, cs, "o-", color=ORANGE, ms=3.5, lw=1.2, label="係が数えた人数")
    ax.set_ylabel("15分ごとの人数")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("流れの多い昼ほど、数えた人数は本当より少ない（1日目の東口）")
    e = (cs / ts - 1) * 100
    ax2.bar(x, e, color=[ORANGE if v < 0 else BLUE for v in e])
    ax2.axhline(0, color=GRAY, lw=1)
    ax2.set_ylabel("ずれ（%）")
    ax2.set_xticks(np.arange(0, NS, 4)); ax2.set_xticklabels([f"{9 + h}時" for h in range(8)])
    save(fig, "a1003_day1.png", SRC)

    # 図2：流れの多さとずれ
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xx = np.arange(len(st))
    ax.bar(xx, st["mean"], color=BLUE)
    ax.errorbar(xx, st["mean"], yerr=[st["mean"] - st.p5, st.p95 - st["mean"]], fmt="none", ecolor=INK, capsize=3, lw=1)
    for i, v in enumerate(st["mean"]):
        ax.text(i + 0.12, v - 0.6, f"{v:.1f}%", fontsize=9, va="top")
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xticks(xx); ax.set_xticklabels(st.index)
    ax.set_xlabel("その15分に1分あたり何人通ったか（本当の人数）")
    ax.set_ylabel("数えた人数のずれ（%、線は5〜95%）")
    ax.set_title("流れが多いほど数え漏れが増える（東口、500日×15分の区切り32個）", fontsize=12)
    save(fig, "a1003_by_flow.png", SRC)

    # 図3：1日の合計のずれと、録画で直したあと
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    data = [df.err_east * 100, df.cal_random * 100, df.cal_offpeak * 100]
    names = ["そのまま", "録画で直す：\nでたらめな15分×4", "録画で直す：\n開館直後の15分×4"]
    bp = ax.boxplot(data, vert=False, whis=(5, 95), showfliers=False, patch_artist=True, widths=0.5)
    for patch, c in zip(bp["boxes"], [GRAY, BLUE, ORANGE]):
        patch.set_facecolor(c); patch.set_alpha(.6)
    for med in bp["medians"]:
        med.set_color(INK)
    ax.set_yticks([1, 2, 3]); ax.set_yticklabels(names, fontsize=9)
    ax.axvline(0, color=INK, lw=1)
    ax.set_xlabel("東口の1日の合計のずれ（%、箱は25〜75%、ひげは5〜95%、500日）")
    ax.set_title("空いている時間で直しても、混む時間の数え漏れは戻らない")
    save(fig, "a1003_calibration.png", SRC)
    print(json.dumps(base, ensure_ascii=False, indent=1))
    print(st.to_string()); print(gd.to_string()); print(sp_df.to_string())


if __name__ == "__main__":
    main()
