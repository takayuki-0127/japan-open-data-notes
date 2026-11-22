"""937 評価者の数を増やすと、点の振れはどれだけ減るのか？（架空のデータ）

架空の会社の300人。人ごとに「本当の点」（100点満点、平均60・標準偏差10）を置く。
評価者40人の中から、1人につき k 人をでたらめに選んで点を付けてもらい、その平均を「評価の点」とする。
1人の評価者の点 ＝ 本当の点 ＋ 評価者の甘さ辛さ ＋ その人についての共通の見え方 ＋ その評価者だけのぶれ。
共通の見え方（目立つ仕事が多いなど）は、どの評価者にも同じに見えると置く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 937
SRC = "架空の会社の300人と評価者40人（作成者が乱数で作成、seed 937）"
N, R = 300, 40
MU, SD_P = 60.0, 10.0
BASE = {"s_c": 5.0, "s_l": 5.0, "s_e": 10.0}
KS = [1, 2, 3, 5, 8, 10, 20]


def simulate(rng, k, s_c, s_l, s_e, same_panel=False, reps=200):
    """reps 回分の指標の平均を返す"""
    sd_err, corr, hit10, pair_ok, pair_ok10, sd_err_rank, agree = [], [], [], [], [], [], []
    for _ in range(reps):
        p = rng.normal(MU, SD_P, N)
        c = rng.normal(0, s_c, N)
        lev = rng.normal(0, s_l, R)
        if same_panel:
            idx = np.tile(rng.choice(R, k, replace=False), (N, 1))
        else:
            idx = np.argsort(rng.random((N, R)), axis=1)[:, :k]
        e = rng.normal(0, s_e, (N, k))
        each = p[:, None] + c[:, None] + lev[idx] + e
        score = each.mean(1)
        err = score - p
        sd_err.append(np.sqrt((err ** 2).mean()))   # 本当の点との差の大きさ（全体のずれも含む）
        if k >= 2:
            agree.append(np.corrcoef(each[:, 0], each[:, 1])[0, 1])
        corr.append(np.corrcoef(score, p)[0, 1])
        top_t = set(np.argsort(-p)[:N // 10]); top_o = set(np.argsort(-score)[:N // 10])
        hit10.append(len(top_t & top_o) / (N // 10))
        i, j = rng.integers(0, N, 4000), rng.integers(0, N, 4000)
        d = p[i] - p[j]
        m5 = (np.abs(d) >= 4) & (np.abs(d) <= 6)
        m10 = (np.abs(d) >= 9) & (np.abs(d) <= 11)
        ok = np.sign(score[i] - score[j]) == np.sign(d)
        pair_ok.append(ok[m5].mean()); pair_ok10.append(ok[m10].mean())
        # 順位にかかわる振れ：全員に共通のずれ（平均の差）を除いた振れ
        sd_err_rank.append((err - err.mean()).std())
    f = lambda x: round(float(np.mean(x)), 4)
    return {"sd_err": f(sd_err), "sd_err_centered": f(sd_err_rank), "corr": f(corr), "top10_hit": f(hit10),
            "pair5_correct": f(pair_ok), "pair10_correct": f(pair_ok10),
            "agree_two_raters": f(agree) if agree else None}


def formula_sd(k, s_c, s_l, s_e):
    return float(np.sqrt(s_c ** 2 + (s_l ** 2 + s_e ** 2) / k))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分のデータ：1人につき10人の評価者
    p = rng.normal(MU, SD_P, N); c = rng.normal(0, BASE["s_c"], N); lev = rng.normal(0, BASE["s_l"], R)
    idx = np.argsort(rng.random((N, R)), axis=1)[:, :10]
    e = rng.normal(0, BASE["s_e"], (N, 10))
    sc = p[:, None] + c[:, None] + lev[idx] + e
    pd.DataFrame({"person": np.arange(1, N + 1), "true": p.round(2), "shared_view": c.round(2)}).to_csv(
        DATA / "people.csv", index=False)
    long = pd.DataFrame({"person": np.repeat(np.arange(1, N + 1), 10), "order": np.tile(np.arange(1, 11), N),
                         "rater": idx.ravel() + 1, "score": sc.ravel().round(2)})
    long.to_csv(DATA / "ratings.csv", index=False)
    pd.DataFrame({"rater": np.arange(1, R + 1), "leniency": lev.round(2)}).to_csv(DATA / "raters.csv", index=False)
    one = {}
    for k in [1, 3, 5, 10]:
        s = sc[:, :k].mean(1)
        one[str(k)] = {"sd_err": round(float(np.sqrt(((s - p) ** 2).mean())), 3), "corr": round(float(np.corrcoef(s, p)[0, 1]), 3)}

    # 2) 基本：k ごと（200回）
    rows = []
    for k in KS:
        r = simulate(np.random.default_rng(SEED * 100 + k), k, **BASE)
        rows.append({"k": k, **r, "formula_sd": round(formula_sd(k, **BASE), 4)})
    base = pd.DataFrame(rows)
    # 共通の見え方がなかったら（s_c=0）
    rows0 = []
    for k in KS:
        r = simulate(np.random.default_rng(SEED * 200 + k), k, 0.0, BASE["s_l"], BASE["s_e"])
        rows0.append({"k": k, **r, "formula_sd": round(formula_sd(k, 0.0, BASE["s_l"], BASE["s_e"]), 4)})
    base0 = pd.DataFrame(rows0)
    # 全員が同じ k 人に評価されるとき
    rowsp = []
    for k in KS:
        r = simulate(np.random.default_rng(SEED * 300 + k), k, **BASE, same_panel=True)
        rowsp.append({"k": k, **r})
    panel = pd.DataFrame(rowsp)
    base.to_csv(RES / "by_k_base.csv", index=False)
    base0.to_csv(RES / "by_k_no_shared.csv", index=False)
    panel.to_csv(RES / "by_k_same_panel.csv", index=False)

    # 3) 確かめ：共通の見え方 s_c × 評価者だけのぶれ s_e（9通り、k=1・3・5・10、各100回）
    grid = []
    for a, s_c in enumerate([0.0, 5.0, 10.0]):
        for b, s_e in enumerate([5.0, 10.0, 15.0]):
            for k in [1, 3, 5, 10]:
                r = simulate(np.random.default_rng(SEED * 1000 + 100 * (3 * a + b) + k), k, s_c, BASE["s_l"], s_e,
                             reps=100)
                grid.append({"s_c": s_c, "s_e": s_e, "k": k, "sd_err": r["sd_err"], "corr": r["corr"],
                             "top10_hit": r["top10_hit"], "agree_two_raters": r["agree_two_raters"], "formula_sd": round(formula_sd(k, s_c, BASE["s_l"], s_e), 4),
                             "floor_sd": s_c})
    grid = pd.DataFrame(grid)
    g1 = grid[grid.k == 1].set_index(["s_c", "s_e"]).sd_err
    g5 = grid[grid.k == 5].set_index(["s_c", "s_e"]).sd_err
    g10 = grid[grid.k == 10].set_index(["s_c", "s_e"]).sd_err
    ratio = (g5 / g1).round(3).reset_index().rename(columns={"sd_err": "ratio_k5_k1"})
    ratio["ratio_k10_k1"] = (g10 / g1).round(3).values
    ratio["agree_two_raters"] = grid[grid.k == 3].agree_two_raters.round(3).values
    ratio["corr_k10"] = grid[grid.k == 10]["corr"].round(3).values
    grid.to_csv(RES / "grid_shared_noise.csv", index=False)
    ratio.to_csv(RES / "grid_ratio.csv", index=False)

    b = base.set_index("k")
    out = {"params": {**BASE, "n_people": N, "n_raters": R, "true_mean": MU, "true_sd": SD_P},
           "by_k_base": base.to_dict("records"), "by_k_no_shared": base0.to_dict("records"),
           "by_k_same_panel": panel.to_dict("records"),
           "ratio_k5_over_k1_base": round(float(b.loc[5, "sd_err"] / b.loc[1, "sd_err"]), 3),
           "ratio_k10_over_k1_base": round(float(b.loc[10, "sd_err"] / b.loc[1, "sd_err"]), 3),
           "one_over_sqrt5": round(1 / np.sqrt(5), 3), "one_over_sqrt10": round(1 / np.sqrt(10), 3),
           "grid_ratio": ratio.to_dict("records"),
           "grid_ratio_k5_range": [float(ratio.ratio_k5_k1.min()), float(ratio.ratio_k5_k1.max())],
           "grid_ratio_k10_range": [float(ratio.ratio_k10_k1.min()), float(ratio.ratio_k10_k1.max())],
           "grid_top10_k10_range": [float(grid[grid.k == 10].top10_hit.min()), float(grid[grid.k == 10].top10_hit.max())],
           "max_abs_diff_formula_base": round(float((base.sd_err - base.formula_sd).abs().max()), 4),
           "max_abs_diff_formula_no_shared": round(float((base0.sd_err - base0.formula_sd).abs().max()), 4),
           "one_draw": one}
    json.dump(out, open(RES / "a937_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：評価者の数と振れ（基本・共通の見え方なし・式）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(base.k, base.sd_err, marker="o", color=BLUE, label=f"共通の見え方あり（標準偏差{BASE['s_c']:.0f}点）")
    ax.plot(base0.k, base0.sd_err, marker="o", color=ORANGE, ls="--", label="共通の見え方なし")
    kk = np.linspace(1, 20, 200)
    ax.plot(kk, [formula_sd(k, **BASE) for k in kk], color=GRAY, lw=.8, label="式 √(共通² ＋ (甘さ²＋ぶれ²)÷k)")
    ax.axhline(BASE["s_c"], color=BLUE, lw=.8, ls=":")
    ax.text(20, BASE["s_c"] - 0.6, "これより下がらない（共通の見え方5点）", color=BLUE, fontsize=8.5, ha="right", va="top")
    ax.set_xlabel("1人を評価する人数（k）"); ax.set_ylabel("本当の点からの外れの大きさ（点）")
    ax.set_xticks(KS); ax.set_ylim(0, 13)
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("評価者を増やすと振れは減るが、共通の見え方の分は残る")
    save(fig, "a937_sd_by_k.png", SRC)

    # 図2：上位10%の当たりと、本当に5点違う2人の順の当たり
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.8), sharex=True)
    for d, c, ls, lab in [(base, BLUE, "-", "でたらめに選んだk人（基本）"), (base0, ORANGE, "--", "共通の見え方なし"),
                          (panel, GREEN, "-.", "全員が同じk人に評価される")]:
        axs[0].plot(d.k, d.top10_hit * 100, marker="o", color=c, ls=ls, label=lab)
        axs[1].plot(d.k, d.pair5_correct * 100, marker="o", color=c, ls=ls, label=lab)
    axs[0].set_ylabel("本当の上位10%に入っていた割合（%）"); axs[0].set_ylim(0, 100)
    axs[1].set_ylabel("本当に5点違う2人の順が合う割合（%）"); axs[1].set_ylim(50, 100)
    for ax in axs:
        ax.set_xlabel("1人を評価する人数（k）"); ax.set_xticks(KS)
    axs[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("評価者を20人にしても、上位10%の当たりは頭打ちになる（各200回の平均）", fontsize=12)
    fig.tight_layout()
    save(fig, "a937_top10_pairs.png", SRC)

    # 図3：共通の見え方 × ぶれで、k=5 の振れが k=1 の何倍になるか
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xs = np.arange(3)
    for a, (s_c, c) in enumerate(zip([0.0, 5.0, 10.0], [ORANGE, BLUE, GREEN])):
        rr = ratio[ratio.s_c == s_c]
        ax.bar(xs + (a - 1) * 0.26, rr.ratio_k5_k1, width=0.25, color=c, label=f"共通の見え方 {s_c:.0f}点")
        for x, v in zip(xs + (a - 1) * 0.26, rr.ratio_k5_k1):
            ax.text(x, v + 0.01, f"{v:.2f}", ha="center", fontsize=8.5)
    ax.axhline(1 / np.sqrt(5), color=GRAY, ls="--", lw=1)
    ax.text(2.45, 1 / np.sqrt(5), " 1÷√5\n ＝0.45", color=GRAY, fontsize=8.5, ha="left", va="center")
    ax.set_xlim(-0.5, 2.8)
    ax.set_xticks(xs); ax.set_xticklabels(["評価者だけのぶれ 5点", "10点", "15点"])
    ax.set_ylabel("5人の外れ ÷ 1人の外れ"); ax.set_ylim(0, 1.15)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
    ax.set_title("5人にしたときの振れの減り方は、共通の見え方の大きさで決まる")
    save(fig, "a937_ratio.png", SRC)

    # 図4：評価者どうしのそろい方と、10人の平均が本当の点に合う度合い（9通り）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for s_c, c, mk in zip([0.0, 5.0, 10.0], [ORANGE, BLUE, GREEN], ["o", "s", "^"]):
        rr = ratio[ratio.s_c == s_c]
        ax.scatter(rr.agree_two_raters, rr.corr_k10, color=c, marker=mk, s=60, label=f"共通の見え方 {s_c:.0f}点")
        for x, y, se in zip(rr.agree_two_raters, rr.corr_k10, rr.s_e):
            ax.text(x + 0.008, y - 0.012, f"ぶれ{se:.0f}点", fontsize=8, color=c, va="top")
    ax.set_xlabel("評価者2人の点の相関（評価者どうしのそろい方）")
    ax.set_ylabel("10人の平均と本当の点の相関")
    ax.set_xlim(0.2, 0.9); ax.set_ylim(0.6, 1.0)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("評価者どうしがよくそろっても、本当の点に近いとは限らない")
    save(fig, "a937_agree_vs_truth.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
