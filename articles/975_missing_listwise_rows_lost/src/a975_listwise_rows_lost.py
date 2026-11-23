"""975 項目ごとに欠けた行を除くと、件数はどれだけ減るのか？（架空のデータ）

架空の店の来店アンケート（1,000人、1〜5の項目を最大20問）。
作成者が「全員が全部に答えたときの本当の答え」を置き、そこへ空欄を入れる。
空欄が1つでもある人を除く（全部そろった人だけで数える）と、件数と平均がどう動くかを数える。
空欄の入り方は4通り：
  ① どの項目も、どの人も同じ確率で空欄（独立）
  ② 人ごとに空欄にしやすさが違う（空欄にしやすい人は、多くの項目を空欄にする）
  ③ 満足していない人ほど空欄にしやすい
  ④ ②と③の両方
どれも1項目あたりの空欄の割合の平均が同じ（基本5%）になるように合わせる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 975
SRC = "架空の店の来店アンケート（作成者が乱数で作成、seed 975）"
N = 1000
KMAX = 20
K = 10
P = 0.05
REPS = 200
RHO = 0.7          # 各項目と、その人の満足度の強さ（標準化した重み）
MODELS = {"①独立": (0.0, 0.0), "②人ごとに欠けやすさが違う": (1.5, 0.0),
          "③不満な人ほど空欄": (0.0, 0.8), "④②と③の両方": (1.5, 0.8)}
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(80)
GH_W = GH_W / GH_W.sum()


def expit(x):
    return 1 / (1 + np.exp(-x))


def calib(p, tau):
    """平均の空欄の割合が p になる切片 a（logit p = a + tau×標準正規）"""
    lo, hi = -20.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if (GH_W * expit(mid + tau * GH_X)).sum() > p:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def formula_complete(p, k, sigma, b):
    """全部そろう人の割合の式の値：E[(1−p_i)^k]（人の欠けやすさで平均）"""
    tau = np.hypot(sigma, b)
    a = calib(p, tau)
    return float((GH_W * (1 - expit(a + tau * GH_X)) ** k).sum())


def make_answers(rng, n=N, kmax=KMAX):
    z = rng.normal(0, 1, n)
    e = rng.normal(0, 1, (n, kmax))
    y = 3.5 + 0.9 * (RHO * z[:, None] + np.sqrt(1 - RHO ** 2) * e)
    return z, np.clip(np.round(y), 1, 5)


def make_missing(rng, z, kmax, p, sigma, b):
    tau = np.hypot(sigma, b)
    a = calib(p, tau)
    u = rng.normal(0, 1, len(z))
    lin = a + sigma * u - b * z           # b>0：満足度 z が低い人ほど空欄にしやすい
    return rng.random((len(z), kmax)) < expit(lin)[:, None]


def one_survey(rng, k=K, p=P, sigma=0.0, b=0.0, kmax=KMAX):
    z, y = make_answers(rng, kmax=kmax)
    miss = make_missing(rng, z, kmax, p, sigma, b)
    m = miss[:, :k]
    comp = ~m.any(1)
    q1 = y[:, 0]
    return dict(complete_share=float(comp.mean()),
                miss_rate=float(m.mean()),
                dropped_one_only=float((m.sum(1) == 1)[~comp].mean()) if (~comp).any() else np.nan,
                true_mean=float(q1.mean()), avail_mean=float(q1[~m[:, 0]].mean()),
                comp_mean=float(q1[comp].mean()),
                true_sat=float((q1 >= 4).mean()), avail_sat=float((q1[~m[:, 0]] >= 4).mean()),
                comp_sat=float((q1[comp] >= 4).mean()),
                curve=(~np.cumsum(miss, 1).astype(bool)).mean(0))


def main():
    t0 = time.time()
    res = {"setting": {"N": N, "K": K, "P": P, "REPS": REPS, "rho": RHO,
                       "answer": "round(3.5 + 0.9×(0.7z + 0.71e)) を1〜5に収める（0.71 = √(1−0.7²)）",
                       "models": {k: {"sigma": v[0], "b": v[1]} for k, v in MODELS.items()}}}

    # 例の1回分（④の置き方）を data に置く
    rng = np.random.default_rng(SEED)
    z, y = make_answers(rng)
    miss = make_missing(rng, z, KMAX, P, *MODELS["④②と③の両方"])
    ex = pd.DataFrame(y[:, :K].astype(int), columns=[f"q{i+1}" for i in range(K)])
    ex_obs = ex.astype("Int64").mask(miss[:, :K])
    ex_obs.insert(0, "respondent_id", np.arange(1, N + 1))
    ex_true = ex.add_suffix("_true")
    out_ex = pd.concat([ex_obs, ex_true], axis=1)
    out_ex["n_blank"] = miss[:, :K].sum(1)
    out_ex.to_csv(DATA / "survey_example.csv", index=False)
    res["example"] = {"model": "④②と③の両方", "complete_rows": int((out_ex.n_blank == 0).sum()),
                      "blank_cells": int(out_ex.n_blank.sum()), "cells": N * K,
                      "blank_share_pct": round(float(out_ex.n_blank.sum()) / (N * K) * 100, 2)}

    # 1) 4つの空欄の入り方（各200回）
    rows, curves = [], {}
    for mi, (name, (sg, bb)) in enumerate(MODELS.items()):
        rr = [one_survey(np.random.default_rng(SEED * 100 + mi * 1000 + r), sigma=sg, b=bb) for r in range(REPS)]
        df = pd.DataFrame([{k: v for k, v in d.items() if k != "curve"} for d in rr])
        curves[name] = np.mean([d["curve"] for d in rr], 0)
        cs = df.complete_share
        rows.append({"model": name, "sigma": sg, "b": bb,
                     "miss_rate_per_item": round(df.miss_rate.mean(), 4),
                     "complete_share": round(cs.mean(), 4), "complete_p10": round(cs.quantile(.1), 4),
                     "complete_p90": round(cs.quantile(.9), 4),
                     "formula": round(formula_complete(P, K, sg, bb), 4),
                     "dropped_with_one_blank": round(df.dropped_one_only.mean(), 4),
                     "true_mean_q1": round(df.true_mean.mean(), 4),
                     "avail_bias_q1": round((df.avail_mean - df.true_mean).mean(), 4),
                     "comp_bias_q1": round((df.comp_mean - df.true_mean).mean(), 4),
                     "true_sat_q1": round(df.true_sat.mean() * 100, 2),
                     "avail_bias_sat_pt": round((df.avail_sat - df.true_sat).mean() * 100, 2),
                     "comp_bias_sat_pt": round((df.comp_sat - df.true_sat).mean() * 100, 2)})
    models = pd.DataFrame(rows)
    models["comp_over_avail_bias"] = (models.comp_bias_q1 / models.avail_bias_q1).where(models.b > 0).round(2)
    models["diff_vs_formula_pt"] = ((models.complete_share - models.formula) * 100).round(2)
    models.to_csv(RES / "models.csv", index=False)
    res["models"] = models.to_dict("records")
    res["indep_formula_0_95_pow_10"] = round(0.95 ** 10, 4)
    res["models_max_abs_diff_vs_formula_pt"] = float(models.diff_vs_formula_pt.abs().max())

    # 2) 使う項目の数（1〜20）と、全部そろう人の割合
    cur = pd.DataFrame({"n_items": np.arange(1, KMAX + 1)})
    for name in MODELS:
        cur[name] = np.round(curves[name], 4)
    cur["式（独立）"] = np.round((1 - P) ** cur.n_items, 4)
    cur.to_csv(RES / "by_number_of_items.csv", index=False)
    res["by_items"] = {str(k): {"indep": float(cur.loc[k - 1, "①独立"]), "person": float(cur.loc[k - 1, "②人ごとに欠けやすさが違う"]),
                                "formula_indep": float(cur.loc[k - 1, "式（独立）"])} for k in [1, 3, 5, 10, 15, 20]}

    # 3) 確かめ：空欄の割合 × 項目の数 × 人ごとの差（各50回、満足度の効きはなし）
    grid = []
    gi = 0
    for p in [0.02, 0.05, 0.10, 0.20]:
        for k in [5, 10, 20]:
            for sg in [0.0, 1.0, 2.0]:
                gi += 1
                cs = [one_survey(np.random.default_rng(SEED * 7 + gi * 1000 + r), k=k, p=p, sigma=sg)["complete_share"]
                      for r in range(50)]
                grid.append({"p": p, "k": k, "sigma": sg, "complete_share": round(float(np.mean(cs)), 4),
                             "formula": round(formula_complete(p, k, sg, 0.0), 4)})
    grid = pd.DataFrame(grid)
    grid["diff_vs_formula"] = (grid.complete_share - grid.formula).round(4)
    grid.to_csv(RES / "robustness_count.csv", index=False)
    res["robust_count"] = {"n_cases": int(len(grid)), "max_abs_diff_vs_formula": float(grid.diff_vs_formula.abs().max()),
                           "range": [float(grid.complete_share.min()), float(grid.complete_share.max())],
                           "min_case": grid.loc[grid.complete_share.idxmin(), ["p", "k", "sigma"]].astype(float).to_dict(),
                           "max_case": grid.loc[grid.complete_share.idxmax(), ["p", "k", "sigma"]].astype(float).to_dict(),
                           "indep_p05_k10": float(grid.query("p==0.05 and k==10 and sigma==0").complete_share.iloc[0]),
                           "sigma2_p05_k10": float(grid.query("p==0.05 and k==10 and sigma==2").complete_share.iloc[0]),
                           "indep_p10_k20": float(grid.query("p==0.1 and k==20 and sigma==0").complete_share.iloc[0]),
                           "sigma2_p10_k20": float(grid.query("p==0.1 and k==20 and sigma==2").complete_share.iloc[0]),
                           "indep_p02_k5": float(grid.query("p==0.02 and k==5 and sigma==0").complete_share.iloc[0])}

    # 4) 確かめ：満足度の効き b × 人ごとの差 × 空欄の割合で、平均のずれ（各50回、10項目）
    bias = []
    gi = 0
    for p in [0.02, 0.05, 0.10]:
        for sg in [0.0, 1.5]:
            for bb in [0.0, 0.4, 0.8, 1.2]:
                gi += 1
                rr = [one_survey(np.random.default_rng(SEED * 11 + gi * 1000 + r), p=p, sigma=sg, b=bb) for r in range(50)]
                df = pd.DataFrame([{k: v for k, v in d.items() if k != "curve"} for d in rr])
                bias.append({"p": p, "sigma": sg, "b": bb, "complete_share": round(df.complete_share.mean(), 4),
                             "avail_bias_q1": round((df.avail_mean - df.true_mean).mean(), 4),
                             "comp_bias_q1": round((df.comp_mean - df.true_mean).mean(), 4),
                             "comp_bias_sat_pt": round((df.comp_sat - df.true_sat).mean() * 100, 2)})
    bias = pd.DataFrame(bias)
    bias["ratio_comp_to_avail"] = (bias.comp_bias_q1 / bias.avail_bias_q1).where(bias.b > 0).round(2)
    bias.to_csv(RES / "robustness_bias.csv", index=False)
    pos = bias[bias.b > 0]
    res["robust_bias"] = {"n_cases": int(len(bias)), "n_cases_b_pos": int(len(pos)), "n_cases_b0": int((bias.b == 0).sum()),
                          "b_pos_comp_bias_range": [float(pos.comp_bias_q1.min()), float(pos.comp_bias_q1.max())],
                          "b_pos_avail_bias_range": [float(pos.avail_bias_q1.min()), float(pos.avail_bias_q1.max())],
                          "b_pos_ratio_range": [float(pos.ratio_comp_to_avail.min()), float(pos.ratio_comp_to_avail.max())],
                          "b_pos_comp_sat_range": [float(pos.comp_bias_sat_pt.min()), float(pos.comp_bias_sat_pt.max())],
                          "b0_abs_max_comp_bias": float(bias[bias.b == 0].comp_bias_q1.abs().max()),
                          "all_b_pos_comp_gt_avail": bool((pos.comp_bias_q1 > pos.avail_bias_q1).all())}

    with open(RES / "a975_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：使う項目の数と、全部そろう人の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = cur.n_items
    ax.plot(x, cur["式（独立）"] * 100, color=GRAY, lw=3, alpha=.5, label="式 0.95の項目数乗（独立）")
    ax.plot(x, cur["①独立"] * 100, "o", color=BLUE, ms=4, label="①独立（数えた値）")
    ax.plot(x, cur["②人ごとに欠けやすさが違う"] * 100, "s-", color=ORANGE, ms=4, lw=1, label="②人ごとに欠けやすさが違う")
    ax.plot(x, cur["④②と③の両方"] * 100, "^--", color=GREEN, ms=4, lw=1, label="④②と③の両方")
    ax.axvline(K, color=INK, lw=.8, ls=":")
    ax.text(K + .2, 96, "基本の10項目", fontsize=9)
    ax.set_xlabel("使う項目の数（どの項目も空欄は平均5%）"); ax.set_ylabel("全部の項目がそろう人の割合（%）")
    ax.set_ylim(0, 100); ax.set_xticks([1, 5, 10, 15, 20])
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("1項目5%の空欄でも、項目を足すほど「全部そろう人」は減る（1,000人×200回）", fontsize=12)
    save(fig, "a975_items_curve.png", SRC + "。200回の平均")

    # 図2：総合満足の平均のずれ（項目ごと vs 全部そろった人だけ）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    yy = np.arange(len(models))[::-1]
    ax.barh(yy + .18, models.avail_bias_q1, height=.34, color=LIGHT, label="総合満足の空欄だけ除く")
    ax.barh(yy - .18, models.comp_bias_q1, height=.34, color=ORANGE, label="10項目すべてそろった人だけ")
    for i, (a_, c_) in enumerate(zip(models.avail_bias_q1, models.comp_bias_q1)):
        ax.text(max(a_, 0) + .003, yy[i] + .18, f"{a_:+.3f}", va="center", fontsize=9)
        ax.text(max(c_, 0) + .003, yy[i] - .18, f"{c_:+.3f}", va="center", fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels(models.model)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_xlabel("総合満足（1〜5）の平均の、本当の平均とのずれ（点）")
    ax.set_xlim(min(-0.02, models.avail_bias_q1.min() - 0.01), models.comp_bias_q1.max() * 1.25)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("不満な人ほど空欄にすると、全部そろった人だけの平均は高く出る", fontsize=12)
    save(fig, "a975_mean_bias.png", SRC + "。1項目の空欄は平均5%、200回の平均")

    # 図3：確かめ（空欄の割合と項目の数、人ごとの差）
    fig, axes = plt.subplots(1, 3, figsize=(8.6, 3.6), sharey=True)
    for ax, k in zip(axes, [5, 10, 20]):
        g = grid[grid.k == k]
        for sg, c, mk in [(0.0, BLUE, "o"), (1.0, GREEN, "s"), (2.0, ORANGE, "^")]:
            h = g[g.sigma == sg]
            ax.plot(h.p * 100, h.complete_share * 100, marker=mk, color=c, lw=1, ms=5,
                    label={0.0: "人ごとの差なし", 1.0: "差 1.0", 2.0: "差 2.0"}[sg])
        ax.set_title(f"{k}項目", fontsize=11); ax.set_xlabel("1項目の空欄（%）")
        ax.set_xticks([2, 5, 10, 20]); ax.set_ylim(0, 100)
    axes[0].set_ylabel("全部そろう人の割合（%）")
    axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("空欄が多く項目が多いほど減り、空欄にする人が偏るほど減り方はゆるい（各50回）", fontsize=12, y=1.04)
    save(fig, "a975_robustness.png", SRC + "。人ごとの差は欠けやすさ（ロジット）の標準偏差", y=-0.03)

    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
