"""920 工程を2つつなぐと、全体の良品率はどうなるのか？（架空のデータ）

架空の工場で、部品が工程1（寸法を作る）→工程2（表面を仕上げる）を通る。
工程ごとに本当の不良の確率を置く（工程1 5%、工程2 8%）。材料のロットの良し悪し z が両方の工程の不良に効く（強さ b）。
各工程の後に、その工程の不良だけを見る検査がある。不良を見つける確率 d、良品を誤って不良とする確率 f。
不良と判定された品物は捨てる（手直しはしない）。合格した品物だけが次へ進み、工程2の検査に合格した品物を出荷する。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 920
SRC = "架空の工場の2つの工程と検査（作成者が乱数で作成、seed 920）"
Q = [0.05, 0.08]
LOTS, UNITS = 200, 500
N_REP = 200


def logit(p):
    return np.log(p / (1 - p))


GH_X, GH_W = np.polynomial.hermite_e.hermegauss(60)


def intercept(q, b):
    """ロットの平均の不良の確率が q になるように切片を合わせる（z は標準正規）"""
    a = logit(q)
    for _ in range(60):
        pz = 1 / (1 + np.exp(-(a + b * GH_X)))
        m = (GH_W * pz).sum() / GH_W.sum()
        dm = (GH_W * pz * (1 - pz)).sum() / GH_W.sum()
        a -= (m - q) / dm
    return a


def run_line(rng, q, b=0.5, d=0.9, f=0.01, lots=LOTS, units=UNITS):
    """ロットの平均の不良の確率は q のまま、ロットごとの良し悪しで上下させる。返り値は全体の数（工程の数は len(q)）"""
    z = rng.normal(0, 1, lots)
    pk = np.array([1 / (1 + np.exp(-(intercept(qi, b) + b * z))) for qi in q])  # 工程×ロット
    m = len(q)
    # 品物ごとの不良の有無（工程ごとに独立、ロットの z を通じて結びつく）を、ロットごとの個数で引く
    dmat = rng.random((lots, units, m)) < pk.T[:, None, :]
    alive = np.ones((lots, units), bool)
    entered, passed = [], []
    for i in range(m):
        entered.append(int(alive.sum()))
        u = rng.random((lots, units))
        reject = np.where(dmat[:, :, i], u < d, u < f)
        alive = alive & ~reject
        passed.append(int(alive.sum()))
    allgood = ~dmat.any(2)
    n = lots * units
    shipped = int(alive.sum())
    return {"n": n, "pass_rates": [p / e for p, e in zip(passed, entered)],
            "true_good_rates": [float(1 - dmat[:, :, i].mean()) for i in range(m)],
            "all_good": float(allgood.mean()), "shipped": shipped / n,
            "shipped_defective_share": float((alive & ~allgood).sum() / max(shipped, 1)),
            "good_scrapped": float((~alive & allgood).sum() / n)}


def summarize(rs):
    pi = np.array([np.prod(r["pass_rates"]) for r in rs])
    pt = np.array([np.prod(r["true_good_rates"]) for r in rs])
    ag = np.array([r["all_good"] for r in rs])
    sd = np.array([r["shipped_defective_share"] for r in rs])
    return {"prod_pass_rates": pi.mean(), "prod_true_good": pt.mean(), "all_good": ag.mean(),
            "diff_pass_minus_allgood_pt": (pi - ag).mean() * 100,
            "diff_truegood_minus_allgood_pt": (pt - ag).mean() * 100,
            "diff_truegood_minus_allgood_pt_p10": np.quantile(pt - ag, .1) * 100,
            "diff_truegood_minus_allgood_pt_p90": np.quantile(pt - ag, .9) * 100,
            "shipped_defective_share": sd.mean(),
            "shipped_good_per_input": (pi * (1 - sd)).mean(),
            "good_scrapped": np.mean([r["good_scrapped"] for r in rs]),
            "pass1": np.mean([r["pass_rates"][0] for r in rs]), "pass2": np.mean([r["pass_rates"][1] for r in rs]) if len(rs[0]["pass_rates"]) > 1 else None}


def main():
    rng = np.random.default_rng(SEED)

    # 1) 1回分（data に置く：ロットごとの数）
    z = rng.normal(0, 1, LOTS)
    rows = []
    for lot in range(LOTS):
        p1 = 1 / (1 + np.exp(-(intercept(Q[0], 0.5) + 0.5 * z[lot])))
        p2 = 1 / (1 + np.exp(-(intercept(Q[1], 0.5) + 0.5 * z[lot])))
        d1 = rng.random(UNITS) < p1
        d2 = rng.random(UNITS) < p2
        rej1 = np.where(d1, rng.random(UNITS) < 0.9, rng.random(UNITS) < 0.01)
        a1 = ~rej1
        rej2 = np.where(d2, rng.random(UNITS) < 0.9, rng.random(UNITS) < 0.01) & a1
        a2 = a1 & ~rej2
        rows.append({"lot": lot + 1, "lot_factor": round(float(z[lot]), 4), "units": UNITS,
                     "defect_p1": int(d1.sum()), "defect_p2": int(d2.sum()), "defect_both": int((d1 & d2).sum()),
                     "pass_p1": int(a1.sum()), "pass_p2": int(a2.sum()),
                     "shipped_defective": int((a2 & (d1 | d2)).sum())})
    lots = pd.DataFrame(rows)
    lots.to_csv(DATA / "lots_one_period.csv", index=False)
    t = lots.sum()
    one = {"units": int(t.units), "pass1": round(t.pass_p1 / t.units, 4), "pass2": round(t.pass_p2 / t.pass_p1, 4),
           "prod_pass": round(t.pass_p1 / t.units * t.pass_p2 / t.pass_p1, 4), "shipped": round(t.pass_p2 / t.units, 4),
           "true_good1": round(1 - t.defect_p1 / t.units, 4), "true_good2": round(1 - t.defect_p2 / t.units, 4),
           "prod_true_good": round((1 - t.defect_p1 / t.units) * (1 - t.defect_p2 / t.units), 4),
           "all_good": round(1 - (t.defect_p1 + t.defect_p2 - t.defect_both) / t.units, 4),
           "shipped_defective_share": round(t.shipped_defective / t.pass_p2, 4)}

    # 2) 基本の置き方（b=0.5、d=0.9、f=0.01）を200回
    base = summarize([run_line(np.random.default_rng(SEED * 10 + r), Q) for r in range(N_REP)])

    # 3) ロットの効き b・見つける確率 d・誤って捨てる確率 f を変える（27通り、各100回）
    grid = []
    for b in [0.0, 0.5, 1.0]:
        for d in [1.0, 0.9, 0.7]:
            for f in [0.0, 0.01, 0.03]:
                rr = [run_line(np.random.default_rng(SEED * 1000 + int(b * 10) * 100 + int(d * 10) * 10 + int(f * 100) + 7 * r),
                               Q, b, d, f) for r in range(100)]
                grid.append({"lot_effect_b": b, "detect_d": d, "false_reject_f": f, **summarize(rr)})
    grid = pd.DataFrame(grid).round(5)
    grid.to_csv(RES / "grid_b_d_f.csv", index=False)

    # 4) 工程の数を増やす（どの工程も不良5%、b=0.5、d=0.9、f=0.01、各100回）
    steps = []
    for m in range(1, 7):
        rr = [run_line(np.random.default_rng(SEED * 5000 + m * 100 + r), [0.05] * m, lots=100) for r in range(100)]
        s = summarize(rr)
        steps.append({"processes": m, "prod_pass_rates": s["prod_pass_rates"], "prod_true_good": s["prod_true_good"],
                      "all_good": s["all_good"], "shipped_defective_share": s["shipped_defective_share"],
                      "good_scrapped": s["good_scrapped"], "formula_0_95_pow": 0.95 ** m,
                      "diff_pass_minus_allgood_pt": s["diff_pass_minus_allgood_pt"]})
    steps = pd.DataFrame(steps).round(5)
    steps.to_csv(RES / "by_number_of_processes.csv", index=False)

    ideal = grid[(grid.lot_effect_b == 0) & (grid.detect_d == 1.0) & (grid.false_reject_f == 0)].iloc[0]
    out = {"settings": {"q": Q, "lots": LOTS, "units_per_lot": UNITS, "lot_effect_b": 0.5, "detect_d": 0.9,
                        "false_reject_f": 0.01, "reps": N_REP, "formula_prod_1_minus_q": round((1 - Q[0]) * (1 - Q[1]), 4)},
           "one_period": one, "base_200reps": {k: (round(float(v), 5) if v is not None else None) for k, v in base.items()},
           "ideal_b0_d1_f0": ideal.to_dict(),
           "grid_ranges": {"diff_pass_minus_allgood_pt_min": float(grid.diff_pass_minus_allgood_pt.min()),
                           "diff_pass_minus_allgood_pt_max": float(grid.diff_pass_minus_allgood_pt.max()),
                           "diff_truegood_minus_allgood_pt_min": float(grid.diff_truegood_minus_allgood_pt.min()),
                           "diff_truegood_minus_allgood_pt_max": float(grid.diff_truegood_minus_allgood_pt.max()),
                           "shipped_defective_share_min": float(grid.shipped_defective_share.min()),
                           "shipped_defective_share_max": float(grid.shipped_defective_share.max())},
           "by_number_of_processes": steps.to_dict("records")}
    json.dump(out, open(RES / "a920_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))

    # 図1：基本の置き方で、4つの「全体の良品率」
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    labels = ["検査の合格率の掛け算\n（＝出荷できた割合）", "工程ごとの本当の\n良品率の掛け算", "本当に2つとも\n良品だった割合",
              "出荷できた良品\n（入れた数に対して）"]
    vals = [base["prod_pass_rates"], base["prod_true_good"], base["all_good"], base["shipped_good_per_input"]]
    ax.bar(range(4), np.array(vals) * 100, color=[ORANGE, LIGHT, BLUE, GREEN])
    for i, v in enumerate(vals):
        ax.text(i, v * 100 + 0.3, f"{v*100:.2f}%", ha="center", fontsize=9.5)
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(80, 92); ax.set_ylabel("入れた部品に対する割合（%）")
    ax.set_title("工程1 5%・工程2 8%の不良、検査で見つけるのは9割と置くと（200回の平均）", fontsize=11)
    ax.text(3.45, 80.3, "縦軸は80%から", fontsize=8, color=GRAY, ha="right")
    save(fig, "a920_four_rates.png", SRC)

    # 図2：見つける確率と誤って捨てる確率で、掛け算と本当の差、出荷品の不良
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 3.9))
    g = grid[grid.lot_effect_b == 0.5]
    for f, col in [(0.0, BLUE), (0.01, ORANGE), (0.03, GREEN)]:
        s = g[g.false_reject_f == f].sort_values("detect_d")
        axs[0].plot(s.detect_d * 100, s.diff_pass_minus_allgood_pt, "o-", color=col, label=f"良品を誤って捨てる確率 {f*100:.0f}%")
        axs[1].plot(s.detect_d * 100, s.shipped_defective_share * 100, "o-", color=col, label=f"良品を誤って捨てる確率 {f*100:.0f}%")
    axs[0].axhline(0, color=GRAY, lw=.8)
    axs[0].set_ylabel("合格率の掛け算 − 本当の良品率（ポイント）")
    axs[0].set_title("合格率の掛け算は、本当の良品率からずれる", fontsize=10.5)
    axs[1].set_ylabel("出荷した品物のうち不良の割合（%）")
    axs[1].set_title("見逃しの分だけ、出荷品に不良が混ざる（3本ほぼ重なる）", fontsize=10.5)
    for ax in axs:
        ax.set_xlabel("検査で不良を見つける確率（%）"); ax.set_xticks([70, 90, 100])
    axs[0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("ロットの効き b=0.5 と置いた場合（各100回の平均）", fontsize=11)
    fig.tight_layout()
    save(fig, "a920_detect_false.png", SRC)

    # 図3：工程の数（左：割合、右：出荷品の不良）
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 3.9), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axs[0]
    ax.plot(steps.processes, steps.prod_pass_rates * 100, "o-", color=ORANGE, label="検査の合格率の掛け算（出荷できた割合）")
    ax.plot(steps.processes, steps.all_good * 100, "s-", color=BLUE, label="本当にすべての工程で良品だった割合")
    ax.plot(steps.processes, steps.formula_0_95_pow * 100, ":", color=GRAY, label="0.95の工程の数乗（式）")
    ax.set_xlabel("つないだ工程の数（どの工程も不良5%）"); ax.set_ylabel("入れた部品に対する割合（%）")
    ax.set_ylim(60, 100); ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title("合格率の掛け算は、本当の良品率より低く出る", fontsize=10.5)
    ax = axs[1]
    ax.bar(steps.processes, steps.shipped_defective_share * 100, color=ORANGE, width=.6)
    for x, v in zip(steps.processes, steps.shipped_defective_share * 100):
        ax.text(x, v + 0.05, f"{v:.1f}", ha="center", fontsize=8.5)
    ax.set_xlabel("つないだ工程の数"); ax.set_ylabel("出荷品のうち不良の割合（%）"); ax.set_ylim(0, 3.6); ax.set_xticks(range(1, 7))
    ax.set_title("見逃しは工程の数だけ積み重なる", fontsize=10.5)
    fig.suptitle("見つける確率90%・誤って捨てる確率1%・ロットの効き0.5と置いた場合（各100回の平均）", fontsize=11)
    fig.tight_layout()
    save(fig, "a920_processes.png", SRC)

if __name__ == "__main__":
    main()
