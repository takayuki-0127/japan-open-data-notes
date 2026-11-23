"""1021 前日のキャンセルと当日の無断の不来店は、分けて数えるべきか？（架空のデータ）

架空の体験教室3つ（A・B・C）。1回の定員10人で、予約はいつも定員まで埋まると置く。
予約した人は、前日までに確率 c で取り消し、取り消さなかった人は当日、確率 n で連絡なく来ない（無断）。
前日までの取り消しで空いた枠は、確率 r で別の人が埋め直す（埋め直した人も確率 n で無断）。
当日の無断で空いた枠は埋め直せない。
「合わせたキャンセル率」（取り消し＋無断）÷予約 と、当日の空き席を比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1021
SRC = "架空の体験教室の予約（作成者が乱数で作成、seed 1021）"
CAP = 10
R_BASE = 0.6
CLASSES = {"A": (0.12, 0.02), "B": (0.04, 0.10), "C": (0.08, 0.06)}      # （前日までの取り消し、当日の無断）
SETS = {"差が小さい": {"A": (0.10, 0.04), "B": (0.06, 0.08)},
        "基本": {"A": CLASSES["A"], "B": CLASSES["B"]},
        "差が大きい": {"A": (0.14, 0.005), "B": (0.01, 0.13)}}


def exact(c, n, r):
    """1人分（1席分）の式の値"""
    lumped = c + (1 - c) * n
    empty = c * (1 - r) + c * r * n + (1 - c) * n
    return lumped, empty


def simulate(rng, c, n, r, sessions, cap=CAP):
    canc = rng.binomial(cap, c, sessions)
    noshow_orig = rng.binomial(cap - canc, n)
    refill = rng.binomial(canc, r)
    noshow_refill = rng.binomial(refill, n)
    attend = cap - canc - noshow_orig + refill - noshow_refill
    return pd.DataFrame({"booked": cap, "cancel_before": canc, "noshow": noshow_orig, "refilled": refill,
                         "refill_noshow": noshow_refill, "attended": attend, "empty": cap - attend})


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {}

    # 1) 3つの教室（2,000回ずつ）
    rows, sims = [], {}
    for k, (c, n) in CLASSES.items():
        s = simulate(rng, c, n, R_BASE, 2000)
        sims[k] = s
        lum, emp = exact(c, n, R_BASE)
        rows.append({"class": k, "cancel_before_pct": c * 100, "noshow_pct": n * 100, "noshow_of_booked_exact_pct": round((1 - c) * n * 100, 2),
                     "lumped_exact_pct": round(lum * 100, 2), "empty_per_session_exact": round(emp * CAP, 3),
                     "lumped_sim_pct": round((s.cancel_before + s.noshow).sum() / s.booked.sum() * 100, 2),
                     "cancel_before_sim_pct": round(s.cancel_before.sum() / s.booked.sum() * 100, 2),
                     "noshow_sim_pct_of_booked": round(s.noshow.sum() / s.booked.sum() * 100, 2),
                     "empty_per_session_sim": round(s["empty"].mean(), 3),
                     "share_sessions_2plus_empty_pct": round((s["empty"] >= 2).mean() * 100, 2)})
    cls = pd.DataFrame(rows)
    cls.to_csv(RES / "classes.csv", index=False)
    pd.concat([d.head(200).assign(**{"class": k, "session": np.arange(1, 201)}) for k, d in sims.items()])[
        ["class", "session", "booked", "cancel_before", "noshow", "refilled", "refill_noshow", "attended", "empty"]
    ].to_csv(DATA / "sessions_first200.csv", index=False)
    e = cls.set_index("class")
    out["classes"] = cls.to_dict("records")
    la0, ea0 = exact(*CLASSES["A"], R_BASE); lb0, eb0 = exact(*CLASSES["B"], R_BASE)
    out["B_over_A_empty_exact"] = round(eb0 / ea0, 3)
    out["B_over_A_lumped_exact"] = round(lb0 / la0, 3)
    out["max_abs_diff_sim_vs_exact"] = {
        "lumped_pt": round(float((cls.lumped_sim_pct - cls.lumped_exact_pct).abs().max()), 2),
        "empty_seats": round(float((cls.empty_per_session_sim - cls.empty_per_session_exact).abs().max()), 3)}

    # 1b) 1か月（8回）ごとに比べると：合わせた率で A のほうが高いのに、空き席は B のほうが多い月
    m = 8
    months = 2000 // m
    def mon(s):
        g = s.groupby(np.arange(len(s)) // m).sum()
        return (g.cancel_before + g.noshow) / g.booked * 100, g["empty"] / m
    la, ea = mon(sims["A"]); lb, eb = mon(sims["B"])
    out["monthly_8_sessions"] = {
        "months": int(months),
        "lumped_A_higher_pct": round(float((la > lb).mean() * 100), 1),
        "empty_B_higher_pct": round(float((eb > ea).mean() * 100), 1),
        "lumped_A_higher_and_empty_B_higher_pct": round(float(((la > lb) & (eb > ea)).mean() * 100), 1)}

    # 2) 教室Cで、7か月目から「無断になるはずだった人の半分が前日までに連絡する」ようになった年
    c, n = CLASSES["C"]
    c2 = c + (1 - c) * n * 0.5
    n2 = n * 0.5 * (1 - c) / (1 - c2)
    lum1, emp1 = exact(c, n, R_BASE); lum2, emp2 = exact(c2, n2, R_BASE)
    out["shift_C"] = {"before": {"cancel_before_pct": round(c * 100, 2), "noshow_of_booked_pct": round((1 - c) * n * 100, 2),
                                 "lumped_pct": round(lum1 * 100, 2), "empty_per_session": round(emp1 * CAP, 3)},
                      "after": {"cancel_before_pct": round(c2 * 100, 2), "noshow_of_booked_pct": round((1 - c2) * n2 * 100, 2),
                                "lumped_pct": round(lum2 * 100, 2), "empty_per_session": round(emp2 * CAP, 3)},
                      "empty_drop_pct": round((1 - emp2 / emp1) * 100, 1)}
    # 1年（月8回×12か月）を1,000年
    yrs = []
    for y in range(1000):
        r_ = np.random.default_rng(SEED * 1000 + y)
        s1 = simulate(r_, c, n, R_BASE, 48); s2 = simulate(r_, c2, n2, R_BASE, 48)
        l1 = (s1.cancel_before + s1.noshow).sum() / s1.booked.sum() * 100
        l2 = (s2.cancel_before + s2.noshow).sum() / s2.booked.sum() * 100
        yrs.append({"lumped_change_pt": l2 - l1, "empty_change": s2["empty"].mean() - s1["empty"].mean(),
                    "noshow_change_pt": (s2.noshow.sum() / s2.booked.sum() - s1.noshow.sum() / s1.booked.sum()) * 100})
    yrs = pd.DataFrame(yrs)
    out["shift_C_1000_years"] = {
        "lumped_change_pt_p10_p90": [round(float(yrs.lumped_change_pt.quantile(.1)), 2), round(float(yrs.lumped_change_pt.quantile(.9)), 2)],
        "lumped_up_or_same_pct": round(float((yrs.lumped_change_pt >= 0).mean() * 100), 1),
        "empty_down_pct": round(float((yrs.empty_change < 0).mean() * 100), 1),
        "noshow_down_pct": round(float((yrs.noshow_change_pt < 0).mean() * 100), 1),
        "empty_change_mean": round(float(yrs.empty_change.mean()), 3)}
    # 1年分の例（月ごと）
    ry = np.random.default_rng(SEED + 7)
    ex = pd.concat([simulate(ry, c, n, R_BASE, 48), simulate(ry, c2, n2, R_BASE, 48)], ignore_index=True)
    ex["month"] = np.arange(96) // 8 + 1
    ex_m = ex.groupby("month").sum()
    ex_m = pd.DataFrame({"lumped_pct": ((ex_m.cancel_before + ex_m.noshow) / ex_m.booked * 100).round(2),
                         "cancel_before_pct": (ex_m.cancel_before / ex_m.booked * 100).round(2),
                         "noshow_pct": (ex_m.noshow / ex_m.booked * 100).round(2),
                         "empty_per_session": (ex_m["empty"] / 8).round(3)})
    ex_m.to_csv(RES / "shift_C_example_year.csv")

    # 3) 確かめ：埋め直す割合×教室の差の置き方（式）、乱数でも確かめる
    grid = []
    for sn, st in SETS.items():
        for r in [0.0, 0.3, 0.6, 0.9]:
            (ca, na), (cb, nb) = st["A"], st["B"]
            la_, ea_ = exact(ca, na, r); lb_, eb_ = exact(cb, nb, r)
            sa = simulate(np.random.default_rng(SEED * 10 + len(grid)), ca, na, r, 20000)
            sb = simulate(np.random.default_rng(SEED * 20 + len(grid)), cb, nb, r, 20000)
            grid.append({"set": sn, "refill": r, "A_lumped_pct": round(la_ * 100, 2), "B_lumped_pct": round(lb_ * 100, 2),
                         "A_empty": round(ea_ * CAP, 3), "B_empty": round(eb_ * CAP, 3),
                         "B_over_A_empty": round(eb_ / ea_, 3),
                         "sim_B_over_A_empty": round(sb["empty"].mean() / sa["empty"].mean(), 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    g0 = grid[grid.refill > 0]
    out["grid"] = {"n_cases": int(len(grid)),
                   "B_over_A_empty_range_refill_gt0": [float(g0.B_over_A_empty.min()), float(g0.B_over_A_empty.max())],
                   "B_over_A_empty_refill0": grid[grid.refill == 0].set_index("set").B_over_A_empty.to_dict(),
                   "lumped_pairs": grid.drop_duplicates("set").set_index("set")[["A_lumped_pct", "B_lumped_pct"]].to_dict("index"),
                   "max_rel_diff_sim_vs_exact_ratio_pct": round(float(((grid.sim_B_over_A_empty / grid.B_over_A_empty) - 1).abs().max() * 100), 1)}
    run_sec = round(time.time() - t0, 1)
    json.dump(out, open(RES / "a1021_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：3つの教室の合わせた率と空き席
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8))
    x = np.arange(3); ks = list(CLASSES)
    ax = axes[0]
    cb_ = [CLASSES[k][0] * 100 for k in ks]; ns_ = [(1 - CLASSES[k][0]) * CLASSES[k][1] * 100 for k in ks]
    ax.bar(x, cb_, 0.55, color=LIGHT, label="前日までの取り消し")
    ax.bar(x, ns_, 0.55, bottom=cb_, color=ORANGE, label="当日の無断")
    for xi, k in zip(x, ks):
        ax.text(xi, e.loc[k, "lumped_exact_pct"] + 0.3, f"{e.loc[k, 'lumped_exact_pct']:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(x, [f"教室{k}" for k in ks]); ax.set_ylabel("予約に対する割合（%）"); ax.set_ylim(0, 18)
    ax.set_title("合わせたキャンセル率はほぼ同じ", fontsize=11); ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax = axes[1]
    ax.bar(x, [e.loc[k, "empty_per_session_exact"] for k in ks], 0.55, color=[GRAY, BLUE, GRAY])
    for xi, k in zip(x, ks):
        v = e.loc[k, "empty_per_session_exact"]; ax.text(xi, v + 0.02, f"{v:.2f}席", ha="center", fontsize=9)
    ax.set_xticks(x, [f"教室{k}" for k in ks]); ax.set_ylabel("1回あたりの当日の空き席（定員10）")
    ax.set_title("当日の空き席は違う（取り消しの6割を埋め直す）", fontsize=11)
    save(fig, "a1021_classes.png", SRC)

    # 図2：教室Cの1年（7か月目から無断の半分が前日の連絡に）
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.2), sharex=True)
    ax = axes[0]
    ax.plot(ex_m.index, ex_m.lumped_pct, color=INK, marker="o", ms=4, lw=1.5, label="合わせたキャンセル率")
    ax.plot(ex_m.index, ex_m.cancel_before_pct, color=BLUE, marker="o", ms=4, lw=1.2, label="前日までの取り消し")
    ax.plot(ex_m.index, ex_m.noshow_pct, color=ORANGE, marker="o", ms=4, lw=1.2, label="当日の無断")
    ax.axvline(6.5, color=GRAY, lw=1, ls="--"); ax.set_ylabel("予約に対する割合（%）"); ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.22))
    ax = axes[1]
    ax.bar(ex_m.index, ex_m.empty_per_session, color=[GRAY] * 6 + [BLUE] * 6)
    ax.axvline(6.5, color=GRAY, lw=1, ls="--")
    ax.set_ylabel("1回あたりの空き席"); ax.set_xlabel("月（1か月8回）"); ax.set_xticks(range(1, 13))
    fig.suptitle("教室C：7か月目から、無断の半分が前日までの連絡に変わった1年の例\n（合わせた率の上下はこの年のたまたま。式では13.52%のまま）", fontsize=11, y=1.07)
    save(fig, "a1021_shift.png", SRC)

    # 図3：埋め直す割合と、B÷A の空き席の比
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for (sn, g), col in zip(grid.groupby("set", sort=False), [LIGHT, BLUE, INK]):
        ax.plot(g.refill * 100, g.B_over_A_empty, marker="o", color=col, lw=1.6, label=f"{sn}")
    ax.axhline(1, color=GRAY, lw=.8, ls="--")
    ax.set_xlabel("前日までの取り消しの枠を埋め直す割合（%）"); ax.set_ylabel("空き席の比（教室B÷教室A）")
    ax.legend(frameon=False, fontsize=9, title="2つの教室の差の置き方", title_fontsize=9)
    ax.set_title("埋め直しがなければ空き席は合わせた率どおり。埋め直すほど差が開く")
    save(fig, "a1021_refill.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print("sec", run_sec)


if __name__ == "__main__":
    main()
