"""865 回答が少ない層の割合は、何件あれば読めるのか？（架空のデータ）

架空の通販サービスの利用者アンケート（1,000人）。年代を7つの層に分け、層ごとに
「満足と答える本当の割合」（作成者が置いた正解）を置く。層の回答数は15〜300件。
1人の答えは、その層の本当の割合で「満足」になる（二項分布）。
読めるかどうかの物差しは作成者が決めたもの：「調査の95%で、見かけの割合が正解から±10ポイント以内」。
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 865
SRC = "架空の通販サービスの利用者アンケート（作成者が乱数で作成、seed 865）"
GROUPS = ["10代", "20代", "30代", "40代", "50代", "60代", "70代以上"]
SIZES = np.array([15, 120, 260, 300, 200, 80, 25])           # 層ごとの回答数（合計1,000）
TRUE = np.array([0.61, 0.58, 0.62, 0.66, 0.60, 0.63, 0.61])  # 層ごとの本当の「満足」の割合
REPS = 20000


LF = np.concatenate([[0.0], np.cumsum(np.log(np.arange(1, 5001)))])   # log(k!)


def binom_pmf_all(n, p):
    k = np.arange(n + 1)
    lg = LF[n] - LF[k] - LF[n - k]
    with np.errstate(divide="ignore"):
        return np.exp(lg + k * np.log(p) + (n - k) * np.log1p(-p))


def p_within(n, p, w):
    """見かけの割合が正解から ±w 以内に入る確率（二項分布で正確に）"""
    k = np.arange(n + 1)
    ok = np.abs(k / n - p) <= w + 1e-12
    return float(binom_pmf_all(n, p)[ok].sum())


def n_needed(p, w, target=0.95, nmax=1500):
    """p_within が target 以上になる最小の n（その先もずっと target 以上になる最初の n）"""
    vals = np.array([p_within(n, p, w) for n in range(1, nmax + 1)])
    bad = np.where(vals < target)[0]
    return int(bad.max() + 2) if len(bad) else 1


def wald(k, n, z=1.96):
    ph = k / n
    h = z * np.sqrt(ph * (1 - ph) / n)
    return ph - h, ph + h


def wilson(k, n, z=1.96):
    ph = k / n
    c = (ph + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def coverage(n, p, f):
    k = np.arange(n + 1)
    lo, hi = f(k, n)
    inside = (lo <= p) & (p <= hi)
    return float(binom_pmf_all(n, p)[inside].sum())


def extremes(rng, sizes, true, reps):
    """調査を reps 回。返り値：見かけの割合 [reps, 層]"""
    return rng.binomial(sizes, true, size=(reps, len(sizes))) / sizes


def r3(x):
    return round(float(x), 3)


def main():
    rng = np.random.default_rng(SEED)

    # 1回分の調査（data）
    rows = []
    for g, n, p in zip(GROUPS, SIZES, TRUE):
        sat = (rng.random(n) < p).astype(int)
        rows += [{"group": g, "satisfied": s} for s in sat]
    df = pd.DataFrame(rows); df.insert(0, "id", np.arange(1, len(df) + 1))
    df.to_csv(DATA / "respondents.csv", index=False)
    one = df.groupby("group", sort=False).satisfied.agg(["size", "mean"]).reset_index()
    lo, hi = wilson(one["mean"] * one["size"], one["size"])
    one["wilson_lo"], one["wilson_hi"] = lo, hi
    one["true"] = TRUE
    one.round(4).to_csv(RES / "one_survey_by_group.csv", index=False)

    # 1) 何件あれば ±w ポイントに95%入るか（式で正確に）
    need = []
    for p in [0.5, 0.6, 0.8, 0.9]:
        for w in [0.05, 0.10, 0.15]:
            need.append({"true_share": p, "within_points": int(w * 100), "n_needed": n_needed(p, w)})
    need = pd.DataFrame(need); need.to_csv(RES / "n_needed.csv", index=False)

    # 2) 件数ごとの振れ（本当60%の層）と、前回との差が10ポイント以上になる割合
    fl = []
    for n in [10, 15, 25, 50, 100, 200, 300, 500]:
        x = rng.binomial(n, 0.6, size=(REPS, 2)) / n
        fl.append({"n": n, "within10": r3(p_within(n, 0.6, 0.10)), "p025": r3(np.quantile(x[:, 0], .025)),
                   "p975": r3(np.quantile(x[:, 0], .975)), "sd": r3(x[:, 0].std()),
                   "change_ge10": r3((np.abs(x[:, 0] - x[:, 1]) >= 0.10 - 1e-12).mean()),
                   "change_ge20": r3((np.abs(x[:, 0] - x[:, 1]) >= 0.20 - 1e-12).mean()),
                   "cover_wald": r3(coverage(n, 0.6, wald)), "cover_wilson": r3(coverage(n, 0.6, wilson)),
                   "cover_wald_p09": r3(coverage(n, 0.9, wald)), "cover_wilson_p09": r3(coverage(n, 0.9, wilson))})
    fl = pd.DataFrame(fl); fl.to_csv(RES / "by_n.csv", index=False)

    # 3) この調査（層の本当の差は最大8ポイント）で、最高・最低に見える層
    x = extremes(rng, SIZES, TRUE, REPS)
    top = x.argmax(1); bot = x.argmin(1)
    gap = x.max(1) - x.min(1)
    ext = {"top_share": {g: r3((top == i).mean()) for i, g in enumerate(GROUPS)},
           "bottom_share": {g: r3((bot == i).mean()) for i, g in enumerate(GROUPS)},
           "small_two_top_or_bottom": r3(((top == 0) | (top == 6) | (bot == 0) | (bot == 6)).mean()),
           "true_gap": r3(TRUE.max() - TRUE.min()), "obs_gap_mean": r3(gap.mean()),
           "obs_gap_ge20": r3((gap >= 0.20).mean()),
           "true_top": GROUPS[int(TRUE.argmax())], "true_bottom": GROUPS[int(TRUE.argmin())],
           "true_top_correct": r3((top == TRUE.argmax()).mean())}
    # 件数の線（30・50・100件未満は出さない）
    thr = []
    for t in [0, 20, 30, 100]:
        show = SIZES >= t
        err = np.abs(x - TRUE)[:, show]
        thr.append({"min_n": t, "groups_shown": int(show.sum()), "respondents_shown": int(SIZES[show].sum()),
                    "max_abs_err_mean": r3(err.max(1).mean()), "share_any_err_ge10": r3((err.max(1) >= 0.10).mean())})
    thr = pd.DataFrame(thr); thr.to_csv(RES / "threshold.csv", index=False)

    # 4) 確かめ：層の本当の差と小さい層の件数を変える
    rob = []
    for spread_name, tr in [("差なし（全層61%）", np.full(7, 0.61)), ("基本（最大8ポイント）", TRUE),
                            ("大きい（最大20ポイント）", np.array([0.62, 0.52, 0.66, 0.72, 0.58, 0.64, 0.60]))]:
        for small_name, sz in [("15件と25件", SIZES), ("40件と60件", np.array([40, 110, 240, 280, 190, 80, 60])),
                               ("100件と100件", np.array([100, 110, 200, 220, 170, 100, 100]))]:
            g = np.random.default_rng(SEED * 100 + len(rob))
            xx = extremes(g, sz, tr, 5000)
            t_, b_ = xx.argmax(1), xx.argmin(1)
            rob.append({"true_spread": spread_name, "small_sizes": small_name,
                        "small_two_top_or_bottom": r3(((t_ == 0) | (t_ == 6) | (b_ == 0) | (b_ == 6)).mean()),
                        "teens_top_or_bottom": r3(((t_ == 0) | (b_ == 0)).mean()),
                        "true_top_correct": r3((t_ == int(np.argmax(tr))).mean()) if tr.std() > 0 else None,
                        "obs_gap_mean": r3((xx.max(1) - xx.min(1)).mean())})
    rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)

    out = {"groups": GROUPS, "sizes": SIZES.tolist(), "true": TRUE.tolist(), "reps": REPS,
           "n_needed": need.to_dict("records"), "by_n": fl.to_dict("records"), "extremes": ext,
           "threshold": thr.to_dict("records"),
           "robust_small_two_top_or_bottom_range": [float(rob.small_two_top_or_bottom.min()),
                                                    float(rob.small_two_top_or_bottom.max())],
           "chance_two_of_seven_top_or_bottom_equal": r3(1 - 5 / 7 * 4 / 6),
           "formula_n_p06_w10": round(1.96 ** 2 * 0.6 * 0.4 / 0.1 ** 2, 1),
           "one_survey": one.round(3).to_dict("records")}
    json.dump(out, open(RES / "a865_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：件数ごとの見かけの割合の95%の範囲（本当60%）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    yy = np.arange(len(fl))
    ax.hlines(yy, fl.p025 * 100, fl.p975 * 100, color=BLUE, lw=6)
    ax.axvline(60, color=INK, lw=1); ax.axvspan(50, 70, color=LIGHT, alpha=.35, lw=0)
    for i, r in fl.iterrows():
        ax.text(r.p975 * 100 + 1.5, i, f"{r.p025*100:.0f}〜{r.p975*100:.0f}%", va="center", fontsize=8.5)
    ax.set_yticks(yy); ax.set_yticklabels([f"{n}件" for n in fl.n]); ax.invert_yaxis()
    ax.set_xlim(20, 105); ax.set_xlabel("見かけの「満足」の割合（%）、調査の95%が入る範囲")
    ax.set_ylim(len(fl) - 0.2, -0.6)
    ax.text(60.8, len(fl) - 0.45, "本当 60%（薄い帯は±10ポイント）", fontsize=8.5)
    ax.set_title("本当は満足6割の層でも、15件なら33〜87%のどこにでも出る")
    save(fig, "a865_range_by_n.png", SRC)

    # 図2：最高・最低に見えた層
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    xs = np.arange(7); w = 0.38
    ax.bar(xs - w / 2, [ext["top_share"][g] * 100 for g in GROUPS], w, color=ORANGE, label="いちばん高く見えた")
    ax.bar(xs + w / 2, [ext["bottom_share"][g] * 100 for g in GROUPS], w, color=BLUE, label="いちばん低く見えた")
    ax.set_xticks(xs); ax.set_xticklabels([f"{g}\n{n}件\n本当{p*100:.0f}%" for g, n, p in zip(GROUPS, SIZES, TRUE)],
                                          fontsize=8)
    ax.set_ylabel("調査のうちの割合（%）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"15件と25件の層が、{ext['small_two_top_or_bottom']*100:.0f}%の調査で最高か最低に見えた（本当の差は最大8ポイント）",
                 fontsize=11.5)
    save(fig, "a865_extremes.png", SRC)

    # 図3：何件あれば ±10ポイントに95%入るか
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    sub = need[need.within_points == 10]
    ax.bar([f"本当{int(p*100)}%" for p in sub.true_share], sub.n_needed, color=BLUE)
    for i, v in enumerate(sub.n_needed):
        ax.text(i, v + 2, f"{v}件", ha="center", fontsize=9)
    ax.set_ylabel("要る件数"); ax.set_ylim(0, sub.n_needed.max() * 1.18)
    ax.set_title("±10ポイントに95%入るのに要る件数（本当の割合しだい）")
    save(fig, "a865_n_needed.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
