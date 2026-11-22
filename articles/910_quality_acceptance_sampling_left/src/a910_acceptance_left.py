"""910 抜き取り検査で合格したロットに、不良はどれだけ残るのか？（架空のデータ）

架空の工場の部品。1ロット1,000個。ロットごとの本当の不良率は、工程の平均のまわりで上下する
（ガンマ分布）。ロットから n 個を抜き取り、不良が c 個以下なら合格。合格したロットは、抜き取った分の
不良だけを取り除いて出荷する。不合格のロットは全数を選別し、不良をすべて取り除くと置く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import hypergeom, binom
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 910
SRC = "架空の工場の部品のロット（作成者が乱数で作成、seed 910）"
N_LOT = 1000
PLANS = [(32, 0), (80, 1), (125, 2)]
BASE_PLAN = (80, 1)
BASE_MEAN, BASE_CV = 0.005, 1.0
BAD = 0.02          # 「悪いロット」とみなす不良率
N_LOTS = 20000


def lot_rates(rng, mean, cv, size):
    if cv == 0:
        return np.full(size, mean)
    k = 1 / cv ** 2
    return np.minimum(rng.gamma(k, mean / k, size), 1.0)


def run(rng, mean, cv, plan, n_lots=N_LOTS):
    n, c = plan
    r = lot_rates(rng, mean, cv, n_lots)
    d = rng.binomial(N_LOT, r)                          # ロットの中の不良の数
    x = rng.hypergeometric(d, N_LOT - d, n)             # 抜き取った n 個の中の不良
    acc = x <= c
    left = np.where(acc, d - x, 0)                       # 出荷に残る不良
    return pd.DataFrame({"lot_rate": r, "defects": d, "sample_defects": x, "accepted": acc, "left": left})


def summarize(df):
    acc = df.accepted
    d_all = df.defects.sum()
    shipped_items = N_LOT * len(df)
    a = df[acc]
    bad = df.defects / N_LOT >= BAD
    return {
        "lots": int(len(df)),
        "accept_rate": round(float(acc.mean()), 4),
        "rate_before": round(float(d_all / shipped_items), 5),
        "rate_in_accepted_lots": round(float(a.defects.sum() / (N_LOT * len(a))), 5) if len(a) else None,
        "rate_left_in_accepted_lots": round(float(a.left.sum() / (N_LOT * len(a))), 5) if len(a) else None,
        "outgoing_rate_all": round(float(df.left.sum() / shipped_items), 5),
        "share_defects_left": round(float(df.left.sum() / d_all), 4) if d_all else None,
        "accepted_lots_with_defect": round(float((a.left > 0).mean()), 4) if len(a) else None,
        "accepted_left_mean": round(float(a.left.mean()), 3) if len(a) else None,
        "accepted_left_p90": float(a.left.quantile(.9)) if len(a) else None,
        "bad_lot_share": round(float(bad.mean()), 4),
        "bad_lots_accepted": round(float(acc[bad].mean()), 4) if bad.any() else None,
        "ratio_left_to_before": round(float(a.left.sum() / (N_LOT * len(a)) / (d_all / shipped_items)), 3) if len(a) and d_all else None,
        "share_left_from_lots_under_1pct": round(float(df.left[df.defects / N_LOT < 0.01].sum() / max(df.left.sum(), 1)), 4),
    }


def oc(p, plan):
    """ロットの不良率が p ちょうど（1,000個のうち p×1,000個）のとき合格する確率（超幾何分布の式）"""
    n, c = plan
    D = int(round(p * N_LOT))
    return float(hypergeom.cdf(c, N_LOT, D, n))


def main():
    t0 = time.time()
    out = {"settings": {"lot_size": N_LOT, "plans": PLANS, "base_plan": BASE_PLAN, "base_process_mean": BASE_MEAN,
                        "base_lot_cv": BASE_CV, "bad_lot_rate": BAD, "lots_per_setting": N_LOTS,
                        "rejected_lots": "全数選別で不良をすべて取り除く", "accepted_lots": "抜き取った分の不良だけ取り除く"}}
    k = 0

    # 1) 基本の工程で、3つの抜き取り方
    base = {}
    for plan in PLANS:
        k += 1
        df = run(np.random.default_rng(SEED * 100 + k), BASE_MEAN, BASE_CV, plan)
        base[f"n={plan[0]},c={plan[1]}"] = summarize(df)
        if plan == BASE_PLAN:
            ex = df.iloc[:2000].copy()
            ex.insert(0, "lot_id", np.arange(1, len(ex) + 1))
            ex["lot_rate"] = ex.lot_rate.round(6)
            ex.to_csv(DATA / "lots_example.csv", index=False)
            base_df = df
    out["base_by_plan"] = base
    pd.DataFrame(base).T.to_csv(RES / "by_plan.csv")

    # 2) 合格する確率の式（OC曲線）
    ocs = []
    for p in [0.001, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05]:
        row = {"lot_rate_pct": p * 100}
        for plan in PLANS:
            row[f"n={plan[0]},c={plan[1]}"] = round(oc(p, plan), 4)
        ocs.append(row)
    pd.DataFrame(ocs).to_csv(RES / "oc_formula.csv", index=False)
    out["oc_formula"] = ocs

    # 3) 確かめ：工程の平均とロットごとのばらつきを変える（基本の抜き取り方）
    rob = []
    for mean in [0.002, 0.005, 0.01, 0.02]:
        for cv in [0, 0.5, 1, 2]:
            k += 1
            s = summarize(run(np.random.default_rng(SEED * 100 + k), mean, cv, BASE_PLAN))
            n, c = BASE_PLAN
            # ばらつき0のときの式：合格率×（1−抜き取り分）×不良率 ＝ 出荷の不良率（AOQ）
            pa = float(binom.cdf(c, n, mean))
            rob.append({"process_mean_pct": mean * 100, "cv": cv, **s,
                        "formula_accept_if_cv0": round(pa, 4),
                        "formula_share_left_if_cv0": round(pa * (N_LOT - n) / N_LOT, 4)})
    rb = pd.DataFrame(rob)
    rb.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob
    out["robustness_share_left_range"] = [float(rb.share_defects_left.min()), float(rb.share_defects_left.max())]
    out["robustness_ratio_accepted_to_before"] = [
        round(float((rb.rate_left_in_accepted_lots / rb.rate_before).min()), 3),
        round(float((rb.rate_left_in_accepted_lots / rb.rate_before).max()), 3)]
    z = rb[rb.cv == 0]
    out["cv0_max_abs_diff_share_left_vs_formula"] = round(float((z.share_defects_left - z.formula_share_left_if_cv0).abs().max()), 4)
    json.dump(out, open(RES / "a910_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：ロットの不良率の分布と、合格する確率
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    rates = base_df.defects / N_LOT * 100
    bins = np.arange(-0.05, 3.06, 0.1)
    ax2 = ax.twinx()
    ax2.hist(rates.clip(upper=3.0), bins=bins, color=LIGHT, alpha=.6)
    ax2.set_yticks([]); ax2.spines["right"].set_visible(False)
    pp = np.arange(0, 31) / 1000
    for plan, col in zip(PLANS, [GRAY, BLUE, ORANGE]):
        ax.plot(pp * 100, [oc(p, plan) * 100 for p in pp], color=col, lw=2,
                label=f"{plan[0]}個を抜き取り、不良{plan[1]}個まで合格")
    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
    ax.set_xlabel("ロットの本当の不良率（%）"); ax.set_ylabel("合格する確率（%）")
    ax.set_xlim(0, 3); ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.text(1.15, 20, "薄い棒：ロットの不良率の分布\n（工程の平均0.5%、20,000ロット。\n3%以上は右端にまとめた）", fontsize=8, color=GRAY)
    ax.set_title("ロットの多くは不良率1%未満で、そこでは抜き取り検査はほぼ合格にする")
    save(fig, "a910_oc_curve.png", SRC)

    # 図2：抜き取り方ごとに、出荷に残る不良
    bp = pd.DataFrame(base).T
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    x = np.arange(len(bp)); w = .27
    ax.bar(x - w, bp.rate_before.astype(float) * 100, w, color=GRAY, label="検査の前（全ロット）")
    ax.bar(x, bp.rate_left_in_accepted_lots.astype(float) * 100, w, color=ORANGE, label="合格したロットに残る")
    ax.bar(x + w, bp.outgoing_rate_all.astype(float) * 100, w, color=BLUE, label="出荷全体（選別したロットを含む）")
    for i, (a, b, c) in enumerate(zip(bp.rate_before, bp.rate_left_in_accepted_lots, bp.outgoing_rate_all)):
        for dx, v in [(-w, a), (0, b), (w, c)]:
            ax.text(i + dx, float(v) * 100 + .01, f"{float(v)*100:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"{p[0]}個を抜き取り\n不良{p[1]}個まで合格" for p in PLANS])
    ax.set_ylabel("不良率（%）"); ax.set_ylim(0, float(bp.rate_before.max()) * 100 * 1.35)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=3, bbox_to_anchor=(1.0, 1.0))
    ax.set_title("合格したロットの不良率は、検査の前からあまり下がらない")
    save(fig, "a910_left_by_plan.png", SRC)

    # 図3：確かめ（工程の平均×ばらつき）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for cv, col in zip([0, 0.5, 1, 2], [GRAY, LIGHT, BLUE, ORANGE]):
        s = rb[rb.cv == cv]
        ax.plot(s.process_mean_pct, s.share_defects_left * 100, marker="o", color=col,
                label=f"ロットごとのばらつき（変動係数）{cv}")
    ax.set_xscale("log"); ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.set_xticks([0.2, 0.5, 1, 2]); ax.set_xticklabels(["0.2%", "0.5%", "1%", "2%"])
    ax.set_xlabel("工程の平均の不良率"); ax.set_ylabel("出荷に残った不良の割合（%）")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("80個抜き取り・1個まで合格：工程が良いほど、不良の多くが出荷に残る")
    save(fig, "a910_robustness.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
