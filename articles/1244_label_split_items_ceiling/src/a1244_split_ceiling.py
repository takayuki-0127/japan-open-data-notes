"""1244 付け手の意見が割れた件を「難しい件」として別に数えると、分類の正解率の上限はどう見えるのか？（架空のデータ）

架空の問い合わせ文10,000件を「急ぎ」か「急ぎでない」かに分ける。本当の分類と、文ごとの見分けやすさ
（付け手1人が正しく付ける確率）を作成者が置く。1件を3人が付け、多い方の判定を「正解ラベル」とする。
3人がそろわなかった件を「難しい件」として別に数え、
・本当の分類をいつも当てる仕組み（いちばん良い仕組み）が、正解ラベルと比べて何%に見えるか（上限）
・付け手どうしの一致率
・ふつうの仕組み（難しい文ほど外す）の、測った正解率と本当の正解率
を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1244
SRC = "架空の問い合わせ文と付け手（作成者が乱数で作成、seed 1244）"
N = 10000
POS = 0.30          # 「急ぎ」の本当の割合
HARD = 0.20         # 本当に見分けにくい文の割合
Q_EASY = 0.95       # 見分けやすい文を付け手1人が正しく付ける確率
Q_HARD = 0.65       # 見分けにくい文を付け手1人が正しく付ける確率
M_EASY = 0.97       # ふつうの仕組みが見分けやすい文を当てる確率
M_HARD = 0.75       # ふつうの仕組みが見分けにくい文を当てる確率
K = 3               # 1件を付ける人数
REPS = 200


def majority_correct(q, k):
    """k人（奇数）の多い方が正しい確率（式）"""
    from math import comb
    return sum(comb(k, i) * q ** i * (1 - q) ** (k - i) for i in range(k // 2 + 1, k + 1))


def unanimous_prob(q, k):
    return q ** k + (1 - q) ** k


def one_round(rng, n, hard, q_easy, q_hard, k, m_easy=M_EASY, m_hard=M_HARD):
    y = rng.random(n) < POS
    is_hard = rng.random(n) < hard
    q = np.where(is_hard, q_hard, q_easy)
    correct = rng.random((n, k)) < q[:, None]                 # 付け手ごとに正しく付けたか
    labels = np.where(correct, y[:, None], ~y[:, None])
    votes = labels.sum(1)
    maj = votes * 2 > k
    split = (votes > 0) & (votes < k)
    perfect = y                                                # いちばん良い仕組み：本当の分類
    model = np.where(rng.random(n) < np.where(is_hard, m_hard, m_easy), y, ~y)
    extra = np.where(rng.random(n) < q, y, ~y)                 # もう1人の付け手
    # 付け手どうしの一致率（組ごと）
    pair = []
    for a in range(k):
        for b in range(a + 1, k):
            pair.append(labels[:, a] == labels[:, b])
    pair = np.mean(pair, axis=0)
    return dict(y=y, is_hard=is_hard, maj=maj, split=split, perfect=perfect, model=model, extra=extra, pair=pair,
                labels=labels)


def acc(pred, ref, mask):
    return float((pred[mask] == ref[mask]).mean()) if mask.any() else float("nan")


def round_stats(o):
    allm = np.ones_like(o["y"])
    s, u = o["split"], ~o["split"]
    st = {}
    for gname, m in [("all", allm), ("split", s), ("unanimous", u)]:
        st[gname] = {"share": float(m.mean()),
                     "label_correct": acc(o["maj"], o["y"], m),
                     "perfect_measured": acc(o["perfect"], o["maj"], m),
                     "model_measured": acc(o["model"], o["maj"], m), "model_true": acc(o["model"], o["y"], m),
                     "extra_rater_measured": acc(o["extra"], o["maj"], m),
                     "pair_agreement": float(o["pair"][m].mean()) if m.any() else float("nan"),
                     "hard_share_in_group": float(o["is_hard"][m].mean()) if m.any() else float("nan")}
    st["hard_caught_in_split"] = float(o["split"][o["is_hard"]].mean())
    st["easy_in_split"] = float(o["split"][~o["is_hard"]].mean())
    st["unanimous_wrong_share"] = float((u & (o["maj"] != o["y"])).sum() / max(u.sum(), 1))
    st["hard_unanimous_wrong_share"] = float((u & o["is_hard"] & (o["maj"] != o["y"])).sum() / max((u & o["is_hard"]).sum(), 1))
    return st


def mean_stats(stats):
    def avg(path):
        vals = []
        for st in stats:
            v = st
            for p in path:
                v = v[p]
            vals.append(v)
        return float(np.nanmean(vals))
    out = {}
    for g in ["all", "split", "unanimous"]:
        out[g] = {k: avg([g, k]) for k in stats[0][g]}
    for k in ["hard_caught_in_split", "easy_in_split", "unanimous_wrong_share", "hard_unanimous_wrong_share"]:
        out[k] = avg([k])
    return out


def r(x, k=4):
    return round(float(x), k) + 0.0


def rr(d, k=4):
    if isinstance(d, dict):
        return {kk: rr(v, k) for kk, v in d.items()}
    return r(d, k)


def formula(hard, q_easy, q_hard, k):
    w = {"easy": 1 - hard, "hard": hard}
    q = {"easy": q_easy, "hard": q_hard}
    p_split = {g: 1 - unanimous_prob(q[g], k) for g in w}
    split_share = sum(w[g] * p_split[g] for g in w)
    ceiling_all = sum(w[g] * majority_correct(q[g], k) for g in w)
    # 割れた件の中で多い方が正しい確率
    def maj_correct_split(qq):
        from math import comb
        num = sum(comb(k, i) * qq ** i * (1 - qq) ** (k - i) for i in range(k // 2 + 1, k))
        den = 1 - unanimous_prob(qq, k)
        return num / den
    ceiling_split = sum(w[g] * p_split[g] * maj_correct_split(q[g]) for g in w) / split_share
    ceiling_unan = sum(w[g] * q[g] ** k for g in w) / sum(w[g] * unanimous_prob(q[g], k) for g in w)
    pair_all = sum(w[g] * (q[g] ** 2 + (1 - q[g]) ** 2) for g in w)
    return {"split_share": split_share, "ceiling_all": ceiling_all, "ceiling_split": ceiling_split,
            "ceiling_unanimous": ceiling_unan, "pair_agreement_all": pair_all,
            "hard_share_in_split": w["hard"] * p_split["hard"] / split_share,
            "hard_caught_in_split": p_split["hard"]}


def main():
    rng = np.random.default_rng(SEED)
    stats = [round_stats(one_round(rng, N, HARD, Q_EASY, Q_HARD, K)) for _ in range(REPS)]
    base = rr(mean_stats(stats))
    f_base = rr(formula(HARD, Q_EASY, Q_HARD, K))

    rows = []
    for g in ["all", "split", "unanimous"]:
        rows.append({"group": g, **base[g]})
    pd.DataFrame(rows).to_csv(RES / "base_groups.csv", index=False)

    # 5人で付けたとき（基本のほかは同じ）
    rng5 = np.random.default_rng(SEED + 5)
    base5 = rr(mean_stats([round_stats(one_round(rng5, N, HARD, Q_EASY, Q_HARD, 5)) for _ in range(REPS)]))
    f5 = rr(formula(HARD, Q_EASY, Q_HARD, 5))

    # 確かめ：見分けにくい文の割合 × 見分けにくい文の正しく付ける確率 × 人数（18通り）
    grid = []
    gi = 0
    for hard in [0.1, 0.2, 0.4]:
        for qh in [0.6, 0.7, 0.8]:
            for k in [3, 5]:
                gi += 1
                g_rng = np.random.default_rng(SEED * 100 + gi)
                ms = mean_stats([round_stats(one_round(g_rng, N, hard, Q_EASY, qh, k)) for _ in range(40)])
                f = formula(hard, Q_EASY, qh, k)
                grid.append({"hard_share": hard, "q_hard": qh, "raters": k,
                             "split_share": r(ms["split"]["share"]),
                             "ceiling_all": r(ms["all"]["perfect_measured"]),
                             "ceiling_split": r(ms["split"]["perfect_measured"]),
                             "ceiling_unanimous": r(ms["unanimous"]["perfect_measured"]),
                             "pair_agreement_all": r(ms["all"]["pair_agreement"]),
                             "hard_share_in_split": r(ms["split"]["hard_share_in_group"]),
                             "hard_caught_in_split": r(ms["hard_caught_in_split"]),
                             "model_true_split": r(ms["split"]["model_true"]),
                             "model_measured_split": r(ms["split"]["model_measured"]),
                             "model_true_all": r(ms["all"]["model_true"]),
                             "model_measured_all": r(ms["all"]["model_measured"]),
                             "formula_ceiling_all": r(f["ceiling_all"]), "formula_ceiling_split": r(f["ceiling_split"])})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # data：例の1回の最初の2,000件
    ex = one_round(np.random.default_rng(SEED + 9), N, HARD, Q_EASY, Q_HARD, K)
    pd.DataFrame({"item": np.arange(1, 2001), "true_urgent": ex["y"][:2000].astype(int),
                  "hard_by_design": ex["is_hard"][:2000].astype(int),
                  "rater1": ex["labels"][:2000, 0].astype(int), "rater2": ex["labels"][:2000, 1].astype(int),
                  "rater3": ex["labels"][:2000, 2].astype(int), "majority": ex["maj"][:2000].astype(int),
                  "split": ex["split"][:2000].astype(int), "model": ex["model"][:2000].astype(int)}).to_csv(
        DATA / "example_items_first2000.csv", index=False)

    gs = {"ceiling_all_range": [r(grid.ceiling_all.min()), r(grid.ceiling_all.max())],
          "ceiling_split_range": [r(grid.ceiling_split.min()), r(grid.ceiling_split.max())],
          "ceiling_unanimous_range": [r(grid.ceiling_unanimous.min()), r(grid.ceiling_unanimous.max())],
          "hard_share_in_split_range": [r(grid.hard_share_in_split.min()), r(grid.hard_share_in_split.max())],
          "hard_caught_in_split_range": [r(grid.hard_caught_in_split.min()), r(grid.hard_caught_in_split.max())],
          "pair_minus_ceiling_all_range": [r((grid.pair_agreement_all - grid.ceiling_all).min()),
                                           r((grid.pair_agreement_all - grid.ceiling_all).max())],
          "model_split_true_minus_measured_range": [r((grid.model_true_split - grid.model_measured_split).min()),
                                                    r((grid.model_true_split - grid.model_measured_split).max())],
          "n_model_split_measured_lt_true": int((grid.model_measured_split < grid.model_true_split).sum()),
          "n_model_measured_all_gt_pair_agreement": int((grid.model_measured_all > grid.pair_agreement_all).sum()),
          "model_measured_all_minus_pair_range": [r((grid.model_measured_all - grid.pair_agreement_all).min()),
                                                  r((grid.model_measured_all - grid.pair_agreement_all).max())],
          "max_abs_diff_formula_all": r((grid.ceiling_all - grid.formula_ceiling_all).abs().max()),
          "max_abs_diff_formula_split": r((grid.ceiling_split - grid.formula_ceiling_split).abs().max())}
    out = {"setting": {"N": N, "urgent_share": POS, "hard_share": HARD, "q_easy": Q_EASY, "q_hard": Q_HARD,
                       "model_easy": M_EASY, "model_hard": M_HARD, "raters": K, "reps": REPS},
           "base": base, "base_formula": f_base, "five_raters": base5, "five_raters_formula": f5,
           "grid_summary": gs}
    json.dump(out, open(RES / "a1244_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：グループごとの「上限」（いちばん良い仕組みの測った正解率）と付け手どうしの一致率
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    groups = [("all", "全体"), ("unanimous", "3人がそろった件"), ("split", "割れた件（難しい件）")]
    yy = np.arange(3)
    h = 0.38
    v1 = [base[g]["perfect_measured"] * 100 for g, _ in groups]
    v2 = [base[g]["pair_agreement"] * 100 for g, _ in groups]
    ax.barh(yy - h / 2, v1, h, color=BLUE, label="本当の分類をいつも当てる仕組みの、測った正解率")
    ax.barh(yy + h / 2, v2, h, color=GRAY, label="付け手どうしの一致率")
    for i in range(3):
        ax.text(v1[i] + 1, i - h / 2, f"{v1[i]:.2f}%", va="center", fontsize=9)
        ax.text(v2[i] + 1, i + h / 2, f"{v2[i]:.2f}%", va="center", fontsize=9)
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{nm}\n（{base[g]['share'] * 100:.2f}%の件）" for g, nm in groups], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 125); ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel(f"%（10,000件×{REPS}回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title(f"割れた件では、本当の分類を当てても正解ラベルと合うのは{v1[2]:.2f}%")
    save(fig, "a1244_groups.png", SRC)

    # 図2：割れた件の中身（本当に見分けにくい文の割合）と、見分けにくい文のうち割れた件に入った割合
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    labels2 = ["割れた件のうち、\n本当に見分けにくい文", "本当に見分けにくい文のうち、\n割れた件に入った文",
               "3人がそろった見分けにくい文のうち、\nそろってまちがえた文"]
    vals = [base["split"]["hard_share_in_group"] * 100, base["hard_caught_in_split"] * 100,
            base["hard_unanimous_wrong_share"] * 100]
    yy = np.arange(3)
    ax.barh(yy, vals, color=[ORANGE, ORANGE, BLUE], height=0.55)
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:.2f}%", va="center", fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels(labels2, fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, 110); ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel(f"%（見分けにくい文は全体の{int(HARD * 100)}%と置いた、{REPS}回の平均）")
    ax.set_title("「割れた件」と「本当に見分けにくい文」はずれる")
    save(fig, "a1244_overlap.png", SRC)

    # 図3：18通りの、割れた件での上限
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    combos = [(hd, qh) for hd in [0.1, 0.2, 0.4] for qh in [0.6, 0.7, 0.8]]
    xx = np.arange(len(combos))
    for k, c, mk in [(3, BLUE, "o"), (5, GREEN, "s")]:
        sub = grid[grid.raters == k]
        v = [sub[(sub.hard_share == hd) & (sub.q_hard == qh)].ceiling_split.iloc[0] * 100 for hd, qh in combos]
        v2 = [sub[(sub.hard_share == hd) & (sub.q_hard == qh)].ceiling_all.iloc[0] * 100 for hd, qh in combos]
        ax.plot(xx, v, marker=mk, lw=0, ms=7, color=c, label=f"{k}人で付けた：割れた件")
        ax.plot(xx, v2, marker=mk, lw=0, ms=7, mfc="white", color=c, label=f"{k}人で付けた：全体")
    ax.set_ylim(0, 105); ax.set_yticks(range(0, 101, 20))
    ax.set_xticks(xx); ax.set_xticklabels([f"{int(hd * 100)}%\n{qh}" for hd, qh in combos], fontsize=9)
    ax.set_xlabel("見分けにくい文の割合と、その文を1人が正しく付ける確率（各40回）")
    ax.set_ylabel("本当の分類を当てる仕組みの正解率（%）", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="lower left", ncol=2)
    ax.set_title("割れた件の上限は、18通りすべてで全体の上限より低い")
    save(fig, "a1244_grid.png", SRC)

    print(json.dumps({k: out[k] for k in ["base", "base_formula", "five_raters", "five_raters_formula", "grid_summary"]},
                     ensure_ascii=False, indent=1))
    pd.set_option("display.width", 250)
    print(grid.to_string())


if __name__ == "__main__":
    main()
