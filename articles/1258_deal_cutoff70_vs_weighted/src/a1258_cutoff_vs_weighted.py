"""1258 確度70%以上の商談の金額だけを足した見込みは、確度を掛けて足した見込みと比べて、実績より多く出るのか少なく出るのか？（架空のデータ）

架空の会社の法人向けの商談。期ごとに40件の商談を作り、金額と記録の確度（10〜90%の5段階）を置く。
本当の受注の確率は、記録の確度どおり・確度が高すぎる（楽観）・低すぎる（慎重）の3通り。
取れる・取れないを乱数で決め、2つの見込み（確度を掛けて足す／確度70%以上の金額だけ足す）を期の実績と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1258
SRC = "架空の会社の商談の記録（作成者が乱数で作成、seed 1258）"
LEVELS = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
MIX = {"low": [0.35, 0.3, 0.2, 0.1, 0.05], "lowish": [0.3, 0.25, 0.2, 0.15, 0.1], "even": [0.2] * 5,
       "highish": [0.1, 0.15, 0.2, 0.25, 0.3], "high": [0.05, 0.1, 0.2, 0.3, 0.35]}
MIXJ = {"low": "低い確度が多い", "lowish": "やや低い確度が多い", "even": "均等", "highish": "やや高い確度が多い", "high": "高い確度が多い"}
CAL = {"honest": "確度どおり", "optimistic": "確度が高すぎる（本当は0.75倍）", "cautious": "確度が低すぎる（取れない確率が0.75倍）"}
N_DEALS, Q = 40, 5000


def true_prob(rec, cal):
    if cal == "honest":
        return rec
    if cal == "optimistic":
        return rec * 0.75
    return 1 - (1 - rec) * 0.75


def simulate(rng, mix, cal, q=Q, n=N_DEALS):
    am = np.exp(np.log(300.0) + 1.0 * rng.standard_normal((q, n)))
    am = np.maximum(10.0, np.round(am / 10) * 10)
    rec = LEVELS[rng.choice(5, size=(q, n), p=MIX[mix])]
    pt = true_prob(rec, cal)
    won = rng.random((q, n)) < pt
    actual = (won * am).sum(axis=1)
    f = {"weighted": (rec * am).sum(axis=1)}
    for t in [0.5, 0.7, 0.9]:
        f[f"cut{int(t * 100)}"] = (am * (rec >= t - 1e-9)).sum(axis=1)
    return am, rec, pt, won, actual, f


def metrics(actual, F):
    return {"bias": round(float(F.mean() / actual.mean() - 1), 4),
            "share_over_actual": round(float((F > actual).mean()), 4),
            "mae_rel": round(float(np.abs(F - actual).mean() / actual.mean()), 4)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 例の1期（確度が均等・確度どおり）
    am, rec, pt, won, actual, f = simulate(rng, "even", "honest", q=1)
    ex = pd.DataFrame({"deal_id": np.arange(1, N_DEALS + 1), "amount_man_yen": am[0].astype(int), "kakudo": rec[0],
                       "won": won[0].astype(int)})
    ex.to_csv(DATA / "example_quarter.csv", index=False)
    lt70 = rec[0] < 0.7 - 1e-9
    example = {"weighted": float(f["weighted"][0]), "cut70": float(f["cut70"][0]), "actual": float(actual[0]),
               "won_below70_amount": float((am[0] * won[0] * lt70).sum()),
               "lost_70plus_amount": float((am[0] * (~won[0]) * (~lt70)).sum()),
               "n_below70": int(lt70.sum()), "n_70plus": int((~lt70).sum())}
    # 50%の商談のうちいちばん大きい1件が70%に上がったら
    i50 = np.where(np.isclose(rec[0], 0.5))[0]
    k = int(i50[np.argmax(am[0][i50])])
    example["move_one_50_to_70"] = {"deal_id": k + 1, "amount": float(am[0][k]),
                                    "cut70_change": float(am[0][k]), "weighted_change": round(float(am[0][k] * 0.2), 1)}

    # 2) 基本：確度が均等・確度どおり、5,000期
    am, rec, pt, won, actual, f = simulate(np.random.default_rng(SEED + 1), "even", "honest")
    base = {k: metrics(actual, v) for k, v in f.items()}
    base["actual_mean"] = round(float(actual.mean()), 1)
    base["weighted_mean"] = round(float(f["weighted"].mean()), 1)
    base["cut70_mean"] = round(float(f["cut70"].mean()), 1)
    lt = rec < 0.7 - 1e-9
    base["won_below70_mean"] = round(float((am * won * lt).sum(axis=1).mean()), 1)
    base["lost_70plus_mean"] = round(float((am * (~won) * (~lt)).sum(axis=1).mean()), 1)
    # 式：E[cut70]/E[actual]（金額と確度が無関係なら、確度の分かれ方と確率だけで決まる）
    def formula_ratio(mix, cal, t=0.7):
        w = np.array(MIX[mix]); p = true_prob(LEVELS, cal)
        return float((w * (LEVELS >= t - 1e-9)).sum() / (w * p).sum())
    base["formula_cut70_over_actual"] = round(formula_ratio("even", "honest"), 4)
    per_q = pd.DataFrame({"quarter": np.arange(1, Q + 1), "actual": actual, "weighted": f["weighted"], "cut70": f["cut70"]})
    per_q.round(1).to_csv(RES / "base_quarters.csv", index=False)

    # 3) 確かめ：確度の分かれ方5通り×確度の当たり方3通り×しきい値3通り＝45通り
    rows = []
    gi = 0
    for cal in CAL:
        for mix in MIX:
            r = np.random.default_rng(SEED * 100 + gi)
            gi += 1
            am, rec, pt, won, actual, f = simulate(r, mix, cal)
            mw = metrics(actual, f["weighted"])
            for t in [50, 70, 90]:
                mc = metrics(actual, f[f"cut{t}"])
                rows.append({"calibration": cal, "mix": mix, "threshold": t,
                             "weighted_bias": mw["bias"], "weighted_mae_rel": mw["mae_rel"],
                             "weighted_share_over": mw["share_over_actual"],
                             "cut_bias": mc["bias"], "cut_mae_rel": mc["mae_rel"], "cut_share_over": mc["share_over_actual"],
                             "cut_formula_ratio": round(formula_ratio(mix, cal, t / 100), 4),
                             "cut_closer": int(mc["mae_rel"] < mw["mae_rel"])})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    g70 = grid[grid.threshold == 70]

    main_json = {
        "setting": {"n_deals_per_quarter": N_DEALS, "quarters": Q, "amount_median_man_yen": 300, "amount_log_sd": 1.0,
                    "kakudo_levels": LEVELS.tolist(), "mix": MIX, "calibration": CAL},
        "example_quarter": example,
        "base_even_honest": base,
        "grid_n": int(len(grid)),
        "cut70_bias_by_mix_cal": {f"{c}|{m}": float(g70[(g70.calibration == c) & (g70.mix == m)].cut_bias.iloc[0])
                                  for c in CAL for m in MIX},
        "weighted_bias_by_cal": {c: [float(g70[g70.calibration == c].weighted_bias.min()),
                                     float(g70[g70.calibration == c].weighted_bias.max())] for c in CAL},
        "cut70_n_over": int((g70.cut_bias > 0).sum()), "cut70_n_under": int((g70.cut_bias < 0).sum()),
        "cut70_closer_n": int(g70.cut_closer.sum()), "cut70_n": int(len(g70)),
        "cut_closer_all_n": int(grid.cut_closer.sum()),
        "honest_cut_closer_n": int(grid[grid.calibration == "honest"].cut_closer.sum()),
        "honest_n": int((grid.calibration == "honest").sum()),
        "cut70_closer_cases": g70[g70.cut_closer == 1][["calibration", "mix", "cut_bias", "cut_mae_rel", "weighted_bias",
                                                         "weighted_mae_rel"]].to_dict("records"),
        "max_abs_bias_minus_formula": round(float(((1 + grid.cut_bias) - grid.cut_formula_ratio).abs().max()), 4),
        "cut_bias_range": [float(grid.cut_bias.min()), float(grid.cut_bias.max())],
        "weighted_mae_honest_range": [float(g70[g70.calibration == "honest"].weighted_mae_rel.min()),
                                      float(g70[g70.calibration == "honest"].weighted_mae_rel.max())],
    }
    with open(RES / "a1258_main.json", "w", encoding="utf-8") as fh:
        json.dump(main_json, fh, ensure_ascii=False, indent=1)

    # 図1：基本の置き方で、4つの見込みの偏り（平均で見た、実績に対する多い・少ない）
    fig, ax = plt.subplots(figsize=(7.5, 4))
    labs = ["確度を掛けて足す", "確度50%以上の金額", "確度70%以上の金額", "確度90%の金額"]
    vals = [base["weighted"]["bias"], base["cut50"]["bias"], base["cut70"]["bias"], base["cut90"]["bias"]]
    cols = [BLUE, GRAY, ORANGE, GRAY]
    ax.bar(range(4), np.array(vals) * 100, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v * 100 + (2 if v >= 0 else -2), f"{v * 100:+.2f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(range(4))
    ax.set_xticklabels(labs, fontsize=9.5)
    ax.set_ylim(-80, 80)
    ax.set_ylabel("見込みの平均 ÷ 実績の平均 − 1（%）")
    ax.set_title("確度が均等で確度どおりに取れるとき、70%以上だけ足すと少なく出た")
    save(fig, "a1258_bias_base.png", SRC + "。1期40件×5,000期、確度10〜90%の5段階が均等")

    # 図2：確度の分かれ方と、70%以上だけ足した見込みの偏り（3つの当たり方）
    fig, ax = plt.subplots(figsize=(8, 4.2))
    xs = np.arange(len(MIX))
    for cal, c, mk in [("honest", BLUE, "o"), ("optimistic", ORANGE, "s"), ("cautious", GREEN, "^")]:
        q = g70[g70.calibration == cal].set_index("mix").loc[list(MIX)]
        ax.plot(xs, q.cut_bias * 100, mk + "-", color=c, label=f"70%以上だけ：{CAL[cal]}")
        ax.plot(xs, q.weighted_bias * 100, mk + ":", color=c, alpha=0.6, label=f"掛けて足す：{CAL[cal]}")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([MIXJ[m] for m in MIX], fontsize=9)
    ax.set_xlabel("記録の確度の分かれ方")
    ax.set_ylabel("見込みの平均 ÷ 実績の平均 − 1（%）")
    ax.set_title("70%以上だけ足す見込みの多い・少ないは、確度の分かれ方と当たり方で決まる", fontsize=12)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=2)
    ax.set_ylim(-80, 110)
    save(fig, "a1258_bias_by_mix.png", SRC + "。1期40件×5,000期")

    # 図3：外れの大きさ（掛けて足す vs 70%以上だけ）
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for cal, c, mk in [("honest", BLUE, "o"), ("optimistic", ORANGE, "s"), ("cautious", GREEN, "^")]:
        q = g70[g70.calibration == cal]
        ax.scatter(q.weighted_mae_rel * 100, q.cut_mae_rel * 100, color=c, marker=mk, s=40, label=CAL[cal])
    lim = max(g70.weighted_mae_rel.max(), g70.cut_mae_rel.max()) * 100 * 1.1
    ax.plot([0, lim], [0, lim], color=GRAY, ls="--", lw=0.8)
    ax.text(lim * 0.62, lim * 0.15, "この線より下は\n70%以上だけのほうが近い", fontsize=8.5, color=GRAY)
    ax.set_xlim(0, lim); ax.set_ylim(0, lim * 1.3)
    ax.set_xlabel("掛けて足した見込みの外れ（実績の平均に対する%）")
    ax.set_ylabel("70%以上だけ足した見込みの外れ（%）")
    ax.set_title("1期ごとの外れの大きさ（15通り）", fontsize=12)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    save(fig, "a1258_mae.png", SRC + "。外れは｜見込み−実績｜の平均÷実績の平均")
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
