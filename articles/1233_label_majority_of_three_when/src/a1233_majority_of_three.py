"""1233 1件を3人で見て多い方の判定に決めると、1人で見るより正しくなるのは、どんなときか？（架空のデータ）

架空の問い合わせ文1,000件。件ごとに本当の分類（「返品の相談」か「それ以外」か）と難しさを作成者が置く。
付け手3人が1件ずつ判定し、付け手 r が件 i を正しく判定する確率は 1/(1+exp(-(a_r - d_i)))。
a_r は付け手の力、d_i は件の難しさ（3人に共通）。難しい件は3人とも外しやすい。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1233
SRC = "架空の問い合わせ文と付け手（作成者が置いた力と難しさからの乱数、seed 1233）"
N_ITEM = 1000
N_REP = 200
PREV = 0.3
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(80)   # 正規分布の平均を数えるための点と重み
GH_W = GH_W / GH_W.sum()


def sig(x):
    return 1 / (1 + np.exp(-x))


def mean_acc(a, sd):
    """力 a の付け手1人の、難しさの散らばり sd の件全体での正しさ（式）"""
    return float((sig(a - sd * GH_X) * GH_W).sum())


def solve_a(target, sd):
    """1人の正しさが target になる力 a を求める（二分法）"""
    lo, hi = -10.0, 15.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if mean_acc(mid, sd) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def maj_formula(accs, sd):
    """3人の多数決の正しさ（式）：件ごとに3人が独立に当たるとして、難しさで平均"""
    a = [solve_a(t, sd) for t in accs]
    p = [sig(ai - sd * GH_X) for ai in a]
    m = p[0] * p[1] * p[2] + p[0] * p[1] * (1 - p[2]) + p[0] * (1 - p[1]) * p[2] + (1 - p[0]) * p[1] * p[2]
    return float((m * GH_W).sum())


def simulate(rng, accs, sd, n=N_ITEM):
    a = np.array([solve_a(t, sd) for t in accs])
    y = (rng.random(n) < PREV).astype(int)
    d = rng.normal(0, sd, n)
    p = sig(a[None, :] - d[:, None])                    # 件×付け手の正しい確率
    correct = rng.random(p.shape) < p
    lab = np.where(correct, y[:, None], 1 - y[:, None])
    maj = (lab.sum(1) >= 2).astype(int)
    acc_r = (lab == y[:, None]).mean(0)
    return {"y": y, "d": d, "lab": lab, "maj": maj, "p_item": p.mean(1),
            "acc_r": acc_r, "acc_maj": float((maj == y).mean()),
            "pos_true": float(y.mean()), "pos_maj": float(maj.mean()), "pos_single": float(lab.mean())}


SCEN = [("①同じ力・難しさの差なし", (0.8, 0.8, 0.8), 0.0),
        ("②同じ力・難しさの差あり", (0.8, 0.8, 0.8), 1.5),
        ("③力に差・難しさの差なし", (0.9, 0.7, 0.7), 0.0),
        ("④力に差・難しさの差あり", (0.9, 0.7, 0.7), 1.5)]


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分のデータ（②の置き方）
    one = simulate(np.random.default_rng(SEED), SCEN[1][1], SCEN[1][2])
    pd.DataFrame({"item_id": np.arange(1, N_ITEM + 1), "true_label": one["y"], "difficulty": one["d"].round(4),
                  "p_correct_one_rater": one["p_item"].round(4),
                  "rater1": one["lab"][:, 0], "rater2": one["lab"][:, 1], "rater3": one["lab"][:, 2],
                  "majority": one["maj"]}).to_csv(DATA / "items_one_set.csv", index=False)

    # 1) 4つの置き方（200回）
    rows, reps = [], []
    for k, (name, accs, sd) in enumerate(SCEN):
        r = [simulate(np.random.default_rng(SEED * 100 + k * 1000 + i), accs, sd) for i in range(N_REP)]
        single = np.array([x["acc_r"] for x in r])          # 回×付け手
        maj = np.array([x["acc_maj"] for x in r])
        best = single[:, 0]                                  # 付け手1が置いた力のいちばん高い人（③④）
        mean1 = single.mean(1)
        hard = float(np.mean([(x["p_item"] < 0.5).mean() for x in r]))
        rows.append({"scenario": name, "rater_acc_set": "・".join(f"{t:.0%}" for t in accs), "difficulty_sd": sd,
                     "single_mean": round(float(mean1.mean()) * 100, 2),
                     "single_best": round(float(best.mean()) * 100, 2),
                     "majority": round(float(maj.mean()) * 100, 2),
                     "majority_formula": round(maj_formula(accs, sd) * 100, 2),
                     "maj_minus_mean": round(float((maj - mean1).mean()) * 100, 2),
                     "maj_minus_best": round(float((maj - best).mean()) * 100, 2),
                     "share_reps_maj_lt_best": round(float((maj < best).mean()) * 100, 1),
                     "share_items_p_lt_half": round(hard * 100, 2),
                     "pos_share_true": round(float(np.mean([x["pos_true"] for x in r])) * 100, 2),
                     "pos_share_single": round(float(np.mean([x["pos_single"] for x in r])) * 100, 2),
                     "pos_share_majority": round(float(np.mean([x["pos_maj"] for x in r])) * 100, 2)})
        for i, x in enumerate(r):
            reps.append({"scenario": name, "rep": i, "acc_r1": x["acc_r"][0], "acc_r2": x["acc_r"][1],
                         "acc_r3": x["acc_r"][2], "acc_majority": x["acc_maj"]})
    scen = pd.DataFrame(rows)
    scen.to_csv(RES / "scenarios.csv", index=False)
    pd.DataFrame(reps).round(4).to_csv(RES / "reps_scenarios.csv", index=False)

    # 2) 件の難しさで分けると（②の200回をまとめて）
    allp, allok_single, allok_maj = [], [], []
    for i in range(N_REP):
        x = simulate(np.random.default_rng(SEED * 100 + 1000 + i), SCEN[1][1], SCEN[1][2])
        allp.append(x["p_item"]); allok_single.append((x["lab"] == x["y"][:, None]).mean(1)); allok_maj.append(x["maj"] == x["y"])
    allp, allok_single, allok_maj = np.concatenate(allp), np.concatenate(allok_single), np.concatenate(allok_maj)
    bins = [0, 0.3, 0.5, 0.7, 0.9, 1.0001]
    lab_b = ["30%未満", "30〜50%", "50〜70%", "70〜90%", "90%以上"]
    cut = pd.cut(allp, bins, right=False, labels=lab_b)
    byd = pd.DataFrame({"bin": cut, "single": allok_single, "maj": allok_maj}).groupby("bin", observed=False).agg(
        share_items=("single", "size"), single=("single", "mean"), majority=("maj", "mean")).reset_index()
    byd["share_items"] = (byd.share_items / len(allp) * 100).round(2)
    byd["single"] = (byd.single * 100).round(2); byd["majority"] = (byd.majority * 100).round(2)
    byd["maj_minus_single"] = (byd.majority - byd.single).round(2)
    byd.to_csv(RES / "by_difficulty_scen2.csv", index=False)

    # 3) 確かめ：難しさの散らばり × 付け手の力の組（各50回）
    grid = []
    sds = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    pairs = [(s, w) for s in (0.8, 0.85, 0.9, 0.95) for w in (0.6, 0.7, 0.8) if s >= w]
    for gi, sd in enumerate(sds):
        for pj, (s, w) in enumerate(pairs):
            accs = (s, w, w)
            r = [simulate(np.random.default_rng(SEED * 7 + gi * 10000 + pj * 100 + i), accs, sd) for i in range(50)]
            single = np.array([x["acc_r"] for x in r]); maj = np.array([x["acc_maj"] for x in r])
            grid.append({"difficulty_sd": sd, "strong_acc": s, "weak_acc": w,
                         "single_mean": round(float(single.mean()) * 100, 2),
                         "single_best": round(float(single[:, 0].mean()) * 100, 2),
                         "majority": round(float(maj.mean()) * 100, 2),
                         "majority_formula": round(maj_formula(accs, sd) * 100, 2),
                         "maj_minus_mean": round(float((maj - single.mean(1)).mean()) * 100, 2),
                         "maj_minus_best": round(float((maj - single[:, 0]).mean()) * 100, 2),
                         "share_items_p_lt_half_mean_rater": round(float(np.mean(
                             [(x["p_item"] < 0.5).mean() for x in r])) * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # 同じ力（80%・80%・80%）で難しさの散らばりだけを変えた線（式）
    eq_line = [{"difficulty_sd": sd, "single": 80.0, "majority_formula": round(maj_formula((0.8,) * 3, sd) * 100, 2)}
               for sd in np.round(np.arange(0, 3.01, 0.25), 2)]
    gap_line = [{"difficulty_sd": sd, "best": 90.0, "majority_formula": round(maj_formula((0.9, 0.7, 0.7), sd) * 100, 2)}
                for sd in np.round(np.arange(0, 3.01, 0.25), 2)]

    eq = grid[grid.strong_acc == grid.weak_acc]
    gap = grid[grid.strong_acc > grid.weak_acc]
    robust = {
        "n_settings": int(len(grid)),
        "n_equal_skill": int(len(eq)),
        "equal_maj_minus_mean_range": [float(eq.maj_minus_mean.min()), float(eq.maj_minus_mean.max())],
        "n_gap": int(len(gap)),
        "gap_n_maj_lt_best": int((gap.maj_minus_best < 0).sum()),
        "gap_maj_minus_best_range": [float(gap.maj_minus_best.min()), float(gap.maj_minus_best.max())],
        "all_n_maj_lt_mean": int((grid.maj_minus_mean < 0).sum()),
        "max_abs_sim_minus_formula": round(float((grid.majority - grid.majority_formula).abs().max()), 2),
        "scen_max_abs_sim_minus_formula": round(float((scen.majority - scen.majority_formula).abs().max()), 2),
        "gap_sd0_n_maj_lt_best": int((gap[gap.difficulty_sd == 0].maj_minus_best < 0).sum()),
        "gap_sd0_n": int((gap.difficulty_sd == 0).sum()),
        "gap_sd3_n_maj_lt_best": int((gap[gap.difficulty_sd == 3.0].maj_minus_best < 0).sum()),
        "gap_sd3_n": int((gap.difficulty_sd == 3.0).sum()),
        "maj_ge_best_list": gap[gap.maj_minus_best >= 0][["difficulty_sd", "strong_acc", "weak_acc", "maj_minus_best"]].to_dict("records"),
    }
    one_summary = {"acc_r": [round(float(v) * 100, 2) for v in one["acc_r"]], "acc_majority": round(one["acc_maj"] * 100, 2),
                   "share_items_all3_wrong": round(float((one["lab"] != one["y"][:, None]).all(1).mean()) * 100, 2),
                   "share_items_all3_right": round(float((one["lab"] == one["y"][:, None]).all(1).mean()) * 100, 2),
                   "share_items_p_lt_half": round(float((one["p_item"] < 0.5).mean()) * 100, 2)}
    out = {"scenarios_200reps": scen.to_dict("records"), "by_difficulty_scen2": byd.astype({"bin": str}).to_dict("records"),
           "equal_skill_line_formula": eq_line, "gap_line_formula": gap_line, "robust": robust, "one_set_scen2": one_summary}
    json.dump(out, open(RES / "a1233_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：4つの置き方
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    xs = np.arange(len(scen)); w_ = 0.26
    for j, (col, lab, c) in enumerate([("single_mean", "1人（3人の平均）", LIGHT), ("single_best", "付け手1（③④では力90%の人）", GRAY),
                                       ("majority", "3人の多い方", BLUE)]):
        ax.bar(xs + (j - 1) * w_, scen[col], w_, color=c, label=lab)
        for xx, v in zip(xs, scen[col]):
            ax.text(xx + (j - 1) * w_, v + 1, f"{v:.2f}", ha="center", fontsize=6.5)
    ax.set_xticks(xs); ax.set_xticklabels([s.replace("・", "\n", 1) for s in scen.scenario], fontsize=9)
    ax.set_ylim(0, 105); ax.set_ylabel("正しく判定した件の割合（%、200回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", ncol=3, bbox_to_anchor=(0, 1.0))
    ax.set_title("3人の多い方は、力が同じなら1人より上がり、力に差があると最も力のある1人に届かない", fontsize=10.5, pad=24)
    save(fig, "a1233_scenarios.png", SRC + "。③④の力は90%・70%・70%、①②は80%・80%・80%")

    # 図2：難しさの散らばりと多い方の正しさ（式）
    el, gl = pd.DataFrame(eq_line), pd.DataFrame(gap_line)
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(el.difficulty_sd, el.majority_formula, color=BLUE, marker="o", ms=4, label="3人の多い方（力80%・80%・80%）")
    ax.axhline(80, color=BLUE, ls="--", lw=1); ax.text(3.05, 80.25, "1人 80%", color=BLUE, fontsize=8.5, va="bottom")
    ax.plot(gl.difficulty_sd, gl.majority_formula, color=ORANGE, marker="o", ms=4, label="3人の多い方（力90%・70%・70%）")
    ax.axhline(90, color=ORANGE, ls="--", lw=1); ax.text(3.05, 90.25, "力90%の1人", color=ORANGE, fontsize=8.5, va="bottom")
    ax.set_xlabel("件の難しさの散らばり（3人に共通、0は散らばりなし）"); ax.set_ylabel("正しく判定した件の割合（%、式）")
    ax.set_ylim(75, 92); ax.set_xlim(-0.1, 3.5)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("3人が同じ件で外しやすいほど、多い方にしたときの上がり幅は縮む（1人の正しさはそろえた）", fontsize=10.5)
    save(fig, "a1233_by_difficulty_sd.png", SRC + "。どの点も1人の正しさを件全体で80%（または90%・70%）にそろえた式の値")

    # 図3：件の難しさで分けた正しさ（②）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xs = np.arange(len(byd))
    ax.bar(xs - 0.2, byd.single, 0.4, color=LIGHT, label="1人（3人の平均）")
    ax.bar(xs + 0.2, byd.majority, 0.4, color=BLUE, label="3人の多い方")
    for xx, a_, b_, s_ in zip(xs, byd.single, byd.majority, byd.share_items):
        ax.text(xx - 0.2, a_ + 1.5, f"{a_:.2f}", ha="center", fontsize=7.5)
        ax.text(xx + 0.2, b_ + 1.5, f"{b_:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"{b}\n（件の{s_:.2f}%）" for b, s_ in zip(byd.bin.astype(str), byd.share_items)], fontsize=9)
    ax.set_xlabel("その件を1人が正しく判定する確率（置いた値）"); ax.set_ylim(0, 110)
    ax.set_ylabel("正しく判定した割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("②で、1人が五分より外しやすい件では、多い方にするとかえって下がる", fontsize=11)
    save(fig, "a1233_items_by_p.png", SRC + "。②の置き方の200回（20万件）をまとめた", y=-0.07)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
