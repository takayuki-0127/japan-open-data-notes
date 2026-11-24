"""1257 確度を掛けて足した見込みの合計は、1件ずつ取れるか取れないかの振れで、期の実績とどれだけ外れるのか？（架空のデータ）

架空の会社の法人向けの商談（1期分）。商談ごとに金額と確度を作成者が置き、
確度は本当の受注の確率と同じ（確度どおりに取れる）と置く。取れる・取れないを乱数で決め、
「確度×金額」を足した見込みと、取れた商談の金額の合計（期の実績）を比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1257
SRC = "架空の会社の商談の記録（作成者が乱数で作成、seed 1257）"
LEVELS = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
MIX = {"low": [0.35, 0.3, 0.2, 0.1, 0.05], "even": [0.2] * 5, "high": [0.05, 0.1, 0.2, 0.3, 0.35]}
MIXJ = {"low": "低い確度が多い", "even": "確度が均等", "high": "高い確度が多い"}
R_BASE = 20000


def make_amounts(rng, n, sigma, median=300.0):
    a = np.exp(np.log(median) + sigma * rng.standard_normal(n))
    return np.maximum(10.0, np.round(a / 10) * 10)   # 万円、10万円単位


def summarize(amount, prob, rng, R=R_BASE):
    E = float((amount * prob).sum())
    won = rng.random((R, len(amount))) < prob
    actual = (won * amount).sum(axis=1)
    ratio = actual / E
    sd_formula = float(np.sqrt((prob * (1 - prob) * amount ** 2).sum()) / E)
    return {
        "n_deals": int(len(amount)),
        "pipeline_total": float(amount.sum()),
        "weighted_forecast": round(E, 1),
        "largest_share_of_forecast": round(float((amount * prob).max() / E), 4),
        "effective_n_by_amount": round(float(amount.sum() ** 2 / (amount ** 2).sum()), 2),
        "mean_ratio": round(float(ratio.mean()), 4),
        "sd_ratio_sim": round(float(ratio.std()), 4),
        "sd_ratio_formula": round(sd_formula, 4),
        "p10_ratio": round(float(np.quantile(ratio, 0.1)), 4),
        "median_ratio": round(float(np.median(ratio)), 4),
        "p90_ratio": round(float(np.quantile(ratio, 0.9)), 4),
        "within10": round(float((np.abs(ratio - 1) <= 0.1).mean()), 4),
        "within20": round(float((np.abs(ratio - 1) <= 0.2).mean()), 4),
        "actual_ge_forecast": round(float((ratio >= 1).mean()), 4),
        "ratio_below_0_7": round(float((ratio < 0.7).mean()), 4),
    }, ratio


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 基本の1期：40件、金額の中央値300万円・対数の散らばり1.0、確度は5段階に8件ずつ
    n = 40
    amount = make_amounts(rng, n, 1.0)
    prob = np.repeat(LEVELS, n // 5)
    rng.shuffle(prob)
    deals = pd.DataFrame({"deal_id": np.arange(1, n + 1), "amount_man_yen": amount.astype(int),
                          "kakudo": prob, "kakudo_x_amount": np.round(amount * prob, 1)})
    deals.to_csv(DATA / "deals_base.csv", index=False)

    scen = {}
    ratios = {}
    scen["base"], ratios["base"] = summarize(amount, prob, np.random.default_rng(SEED + 1))
    big = int(np.argmax(amount))
    keep = np.arange(n) != big
    scen["drop_largest"], ratios["drop_largest"] = summarize(amount[keep], prob[keep], np.random.default_rng(SEED + 2))
    # 同じ見込みの合計を、金額のそろった40件にした（確度は同じ並び）
    eq = np.full(n, (amount * prob).sum() / prob.sum())
    scen["equal_amounts"], ratios["equal_amounts"] = summarize(eq, prob, np.random.default_rng(SEED + 3))
    # 確度50%・3,000万円の商談を1件足した
    a2, p2 = np.r_[amount, 3000.0], np.r_[prob, 0.5]
    scen["add_big_3000"], ratios["add_big_3000"] = summarize(a2, p2, np.random.default_rng(SEED + 4))
    sc = pd.DataFrame([{"scenario": k, **v} for k, v in scen.items()])
    sc.to_csv(RES / "scenarios.csv", index=False)

    # 実績が見込みを下回る回の内訳：大きい順の3件
    order = np.argsort(-amount)[:3]
    top3 = [{"deal_id": int(i + 1), "amount_man_yen": int(amount[i]), "kakudo": float(prob[i]),
             "share_of_variance": round(float(prob[i] * (1 - prob[i]) * amount[i] ** 2 /
                                              (prob * (1 - prob) * amount ** 2).sum()), 4)} for i in order]

    # 2) 確かめ：件数5通り×金額の散らばり3通り×確度の分かれ方3通り＝45通り。各100期（期ごとに商談を作り直す）×400回
    rows = []
    per_pipe = []
    gi = 0
    for mix in ["low", "even", "high"]:
        for sigma in [0.3, 1.0, 1.5]:
            for N in [10, 20, 40, 80, 160]:
                r = np.random.default_rng(SEED * 100 + gi)
                gi += 1
                P, R = 100, 400
                am = np.exp(np.log(300.0) + sigma * r.standard_normal((P, N)))
                am = np.maximum(10.0, np.round(am / 10) * 10)
                pr = LEVELS[r.choice(5, size=(P, N), p=MIX[mix])]
                E = (am * pr).sum(axis=1)
                won = r.random((P, R, N)) < pr[:, None, :]
                act = (won * am[:, None, :]).sum(axis=2)
                ratio = act / E[:, None]
                w10 = (np.abs(ratio - 1) <= 0.1).mean(axis=1)
                ge = (ratio >= 1).mean(axis=1)
                neff = am.sum(axis=1) ** 2 / (am ** 2).sum(axis=1)
                sdf = np.sqrt((pr * (1 - pr) * am ** 2).sum(axis=1)) / E
                rows.append({"mix": mix, "sigma": sigma, "n_deals": N,
                             "within10_mean": round(float(w10.mean()), 4),
                             "within10_p10": round(float(np.quantile(w10, 0.1)), 4),
                             "within10_p90": round(float(np.quantile(w10, 0.9)), 4),
                             "within20_mean": round(float((np.abs(ratio - 1) <= 0.2).mean()), 4),
                             "actual_ge_forecast_mean": round(float(ge.mean()), 4),
                             "sd_ratio_formula_median": round(float(np.median(sdf)), 4),
                             "effective_n_median": round(float(np.median(neff)), 2),
                             "pooled_ratio_mean": round(float(ratio.mean()), 4)})
                for k in range(P):
                    per_pipe.append({"mix": mix, "sigma": sigma, "n_deals": N, "effective_n": round(float(neff[k]), 3),
                                     "within10": round(float(w10[k]), 4), "actual_ge_forecast": round(float(ge[k]), 4)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    pp = pd.DataFrame(per_pipe)
    pp.to_csv(RES / "grid_per_pipeline.csv", index=False)

    # 実質の件数で区切った ±10% に入る割合
    bins = [0, 5, 10, 20, 40, 80, 200]
    pp["neff_bin"] = pd.cut(pp.effective_n, bins)
    by_neff = pp.groupby("neff_bin", observed=True).agg(n_pipelines=("within10", "size"),
                                                         within10_mean=("within10", "mean")).round(4).reset_index()
    by_neff["neff_bin"] = by_neff.neff_bin.astype(str)
    by_neff.to_csv(RES / "within10_by_effective_n.csv", index=False)

    main_json = {
        "base_setting": {"n_deals": n, "amount_median_man_yen": 300, "amount_log_sd": 1.0, "kakudo_levels": LEVELS.tolist(),
                         "deals_per_level": n // 5, "outcome_draws": R_BASE, "kakudo_equals_true_probability": True},
        "scenarios": scen,
        "base_top3_by_amount": top3,
        "base_top3_share_of_variance": round(sum(t["share_of_variance"] for t in top3), 4),
        "scenarios_max_abs_sd_sim_minus_formula": round(float((sc.sd_ratio_sim - sc.sd_ratio_formula).abs().max()), 4),
        "grid_n": int(len(grid)),
        "grid_within10_range": [float(grid.within10_mean.min()), float(grid.within10_mean.max())],
        "grid_within20_range": [float(grid.within20_mean.min()), float(grid.within20_mean.max())],
        "grid_actual_ge_range": [float(grid.actual_ge_forecast_mean.min()), float(grid.actual_ge_forecast_mean.max())],
        "grid_n_actual_ge_below_half": int((grid.actual_ge_forecast_mean < 0.5).sum()),
        "grid_pooled_ratio_mean_range": [float(grid.pooled_ratio_mean.min()), float(grid.pooled_ratio_mean.max())],
        "grid_within10_n160_sigma03": grid[(grid.n_deals == 160) & (grid.sigma == 0.3)].set_index("mix").within10_mean.to_dict(),
        "grid_within10_n10_sigma15": grid[(grid.n_deals == 10) & (grid.sigma == 1.5)].set_index("mix").within10_mean.to_dict(),
        "grid_n_within10_ge_half": int((grid.within10_mean >= 0.5).sum()),
    }
    with open(RES / "a1257_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：基本の40件で、実績÷見込みの散らばり
    fig, ax = plt.subplots(figsize=(7.5, 4))
    rb = ratios["base"]
    bins_h = np.arange(0.3, 1.75, 0.025)
    ax.hist(np.clip(rb, 0.3, 1.725), bins=bins_h, color=LIGHT, edgecolor="white")
    ax.axvspan(0.9, 1.1, color=BLUE, alpha=0.12, lw=0)
    ax.axvline(1, color=INK, lw=1)
    s = scen["base"]
    ax.text(1.0, ax.get_ylim()[1] * 0.97, f"  見込みどおり（±10%に入った回 {s['within10'] * 100:.2f}%）", va="top", fontsize=9)
    ax.text(0.32, ax.get_ylim()[1] * 0.8, f"10%点 {s['p10_ratio']:.4f}倍\n中央値 {s['median_ratio']:.4f}倍\n90%点 {s['p90_ratio']:.4f}倍",
            fontsize=9, va="top")
    ax.set_xlabel("期の実績 ÷ 確度を掛けて足した見込み（倍）")
    ax.set_ylabel("回数（2万回のうち）")
    ax.set_title("確度どおりに取れると置いても、実績÷見込みは散らばる（基本の40件）")
    save(fig, "a1257_ratio_hist.png", SRC + "。金額の中央値300万円、確度10〜90%の5段階に8件ずつ")

    # 図2：件数ごとの ±10% に入った割合（確度が均等）
    fig, ax = plt.subplots(figsize=(8, 4.2))
    g = grid[grid.mix == "even"]
    Ns = [10, 20, 40, 80, 160]
    w = 0.26
    for j, (sigma, c, lab) in enumerate([(0.3, BLUE, "金額がそろい気味（対数の散らばり0.3）"),
                                          (1.0, ORANGE, "基本（1.0）"), (1.5, GRAY, "金額の差が大きい（1.5）")]):
        vals = [float(g[(g.sigma == sigma) & (g.n_deals == N)].within10_mean.iloc[0]) for N in Ns]
        xs = np.arange(len(Ns)) + (j - 1) * w
        ax.bar(xs, np.array(vals) * 100, width=w, color=c, label=lab)
        for xx, v in zip(xs, vals):
            ax.text(xx, v * 100 + 1, f"{v * 100:.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(np.arange(len(Ns)))
    ax.set_xticklabels([f"{N}件" for N in Ns])
    ax.set_ylim(0, 100)
    ax.set_xlabel("その期の商談の件数")
    ax.set_ylabel("実績が見込みの±10%に入った回（%）")
    ax.set_title("件数が多く金額がそろうほど、見込みの±10%に入りやすい（確度が均等）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1257_within10_by_n.png", SRC + "。件数・金額の散らばりごとに商談を100期作り、各400回の平均")

    # 図3：実質の件数と ±10% に入った割合（4,500期）
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for mix, c in [("low", ORANGE), ("even", BLUE), ("high", GREEN)]:
        q = pp[pp.mix == mix]
        ax.scatter(q.effective_n, q.within10 * 100, s=5, alpha=0.35, color=c, label=MIXJ[mix])
    ax.set_xscale("log")
    ax.set_ylim(0, 100)
    ax.set_xlabel("金額で見た実質の件数（金額の合計の2乗÷金額の2乗の合計、対数の目盛り）")
    ax.set_ylabel("実績が見込みの±10%に入った回（%）")
    ax.set_title("金額で見た実質の件数が多いほど±10%に入りやすい（確度の分かれ方でも上下）", fontsize=12)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", markerscale=3)
    save(fig, "a1257_effective_n.png", SRC + "。45通り×100期＝4,500期、各400回")
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
