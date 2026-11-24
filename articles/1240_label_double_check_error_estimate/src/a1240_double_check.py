"""1240 一部の件だけを2人で付けて確かめると、残りの件のまちがいの数はどこまで見込めるのか？（架空のデータ）

架空の製品の写真に見立てた10,000件を5つの分類（上着・シャツ・ズボン・かばん・くつ）に分ける。
件ごとに「易しい件」「紛らわしい件」を作成者が置き、付け手がまちがえる確率と、まちがえるときの付け先を置く。
1人目が全件に付け、でたらめに選んだ一部の件だけに2人目が別に付ける。2人の食い違いから、残りの件の
1人目のまちがいの数を見込み、本当の数（作成者が知っている正解と比べた数）と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1240
SRC = "架空の製品の写真に見立てた件（作成者が置いた正解と付け手のまちがい方からの乱数、seed 1240）"
CATS = ["上着", "シャツ", "ズボン", "かばん", "くつ"]
K, N = 5, 10000
P = np.array([0.25, 0.25, 0.20, 0.15, 0.15])
PARTNER = np.array([1, 0, 1, 4, 3])  # 紛らわしい件で取り違えやすい相手
BASE = dict(hard=0.2, e_easy=0.02, e_hard=0.3, same=0.8, n_check=500, copy=0.0)
METHODS = {"disagree": "①食い違いの割合をそのまま\nまちがいの割合とみなす",
           "half": "②食い違いの割合の半分",
           "review": "③食い違った件だけ見直す",
           "truth": "④確かめた件をすべて\n正解と照らす"}


def label(rng, t, hard, e_easy, e_hard, same):
    n = len(t)
    err = rng.random(n) < np.where(hard, e_hard, e_easy)
    lab = t.copy()
    # まちがえるとき：紛らわしい件は確率 same で相手の分類へ、それ以外は残りへ均等
    to_partner = hard & (rng.random(n) < same)
    shift = rng.integers(1, K, n)
    other = (t + shift) % K
    # 相手以外へ均等（紛らわしい件で相手に行かないとき）
    bad = hard & ~to_partner & (other == PARTNER[t])
    while bad.any():
        other[bad] = (t[bad] + rng.integers(1, K, bad.sum())) % K
        bad = hard & ~to_partner & (other == PARTNER[t])
    wrong = np.where(to_partner, PARTNER[t], other)
    lab[err] = wrong[err]
    return lab


def one(rng, hard=0.2, e_easy=0.02, e_hard=0.3, same=0.8, n_check=500, copy=0.0, keep=False):
    t = rng.choice(K, N, p=P)
    h = rng.random(N) < hard
    l1 = label(rng, t, h, e_easy, e_hard, same)
    idx = rng.choice(N, n_check, replace=False)
    chk = np.zeros(N, bool)
    chk[idx] = True
    l2 = label(rng, t[idx], h[idx], e_easy, e_hard, same)
    if copy > 0:  # 2人目が1人目の答えを見てから付け、確率 copy でそのまま写す
        cp = rng.random(n_check) < copy
        l2 = np.where(cp, l1[idx], l2)
    rest = N - n_check
    true_rest = int(((l1 != t) & ~chk).sum())
    d = (l1[idx] != l2)
    e1 = (l1[idx] != t[idx])
    out = {"true_rest": true_rest,
           "disagree": d.mean() * rest, "half": d.mean() / 2 * rest,
           "review": (d & e1).mean() * rest, "truth": e1.mean() * rest,
           "disagree_rate": d.mean(), "err_rate_checked": e1.mean(),
           "both_wrong_same_rate": ((l1[idx] == l2) & e1).mean()}
    if keep:
        return out, t, h, l1, chk, None, idx, l2
    return out


def formula(hard, e_easy, e_hard, same):
    """1件あたりの式：1人目のまちがい、2人の食い違い、2人がそろって同じまちがいをする確率。"""
    e = (1 - hard) * e_easy + hard * e_hard
    s_easy = e_easy ** 2 / (K - 1)  # 易しい件で同じまちがい
    q_h = [same] + [(1 - same) / (K - 2)] * (K - 2)
    s_hard = e_hard ** 2 * sum(x * x for x in q_h)
    both_same = (1 - hard) * s_easy + hard * s_hard
    disagree = 1 - ((1 - hard) * ((1 - e_easy) ** 2 + s_easy) + hard * ((1 - e_hard) ** 2 + s_hard))
    return e, disagree, both_same


def r(x, d=4):
    return round(float(x), d)


def summarize(df, cols=("disagree", "half", "review", "truth")):
    o = {"true_rest_mean": r(df.true_rest.mean(), 2)}
    for c in cols:
        ratio = df[c] / df.true_rest
        o[c] = {"mean": r(df[c].mean(), 2), "ratio_mean": r(ratio.mean()),
                "ratio_p10": r(np.percentile(ratio, 10)), "ratio_p90": r(np.percentile(ratio, 90)),
                "share_below_true": r((ratio < 1).mean())}
    return o


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分（data に置く）
    out, t, h, l1, chk, _, idx, l2 = one(rng, **BASE, keep=True)
    l2full = np.full(N, "", dtype=object)
    l2full[idx] = [CATS[i] for i in l2]
    pd.DataFrame({"item_id": np.arange(1, N + 1), "true": [CATS[i] for i in t], "confusing": h.astype(int),
                  "label1": [CATS[i] for i in l1], "checked": chk.astype(int), "label2": l2full}).to_csv(
        DATA / "items_one_set.csv", index=False)

    # 1) 基本の置き方で500回
    base = pd.DataFrame([one(np.random.default_rng([SEED, 1, i]), **BASE) for i in range(500)])
    base.to_csv(RES / "reps_base.csv", index=False, float_format="%.6f")
    e, dis, bs = formula(BASE["hard"], BASE["e_easy"], BASE["e_hard"], BASE["same"])
    rest = N - BASE["n_check"]
    head = summarize(base)
    head["formula"] = {"error_rate": r(e), "disagree_rate": r(dis), "both_wrong_same_rate": r(bs),
                       "rest_true": r(e * rest, 2), "rest_disagree": r(dis * rest, 2), "rest_half": r(dis / 2 * rest, 2),
                       "rest_review": r((e - bs) * rest, 2), "review_ratio": r((e - bs) / e),
                       "disagree_ratio": r(dis / e), "half_ratio": r(dis / 2 / e),
                       "invisible_share_of_errors": r(bs / e)}
    head["sim_disagree_rate"] = r(base.disagree_rate.mean())
    head["sim_err_rate_checked"] = r(base.err_rate_checked.mean())
    head["sim_both_wrong_same_rate"] = r(base.both_wrong_same_rate.mean())
    # 紛らわしい件に入っているまちがい（1回分）
    err1 = l1 != t
    head["one_set"] = {"errors_all": int(err1.sum()), "errors_in_confusing_share": r((err1 & h).sum() / err1.sum()),
                       "confusing_items": int(h.sum())}

    # 2) 確かめる件の数を変える
    rows = []
    for n_c in [100, 300, 500, 1000, 2000]:
        df = pd.DataFrame([one(np.random.default_rng([SEED, 2, n_c, i]), **{**BASE, "n_check": n_c}) for i in range(500)])
        s = summarize(df, ("review", "truth"))
        rows.append({"n_check": n_c, "true_rest_mean": s["true_rest_mean"],
                     **{f"{m}_{k}": s[m][k] for m in ("review", "truth") for k in ("ratio_mean", "ratio_p10", "ratio_p90")}})
    by_n = pd.DataFrame(rows)
    by_n.to_csv(RES / "by_check_size.csv", index=False)

    # 3) 2人目が1人目の答えを見てから付ける（確率0.5で写す）
    cp = pd.DataFrame([one(np.random.default_rng([SEED, 3, i]), **{**BASE, "copy": 0.5}) for i in range(500)])
    copy_s = summarize(cp)

    # 4) 確かめ：紛らわしい件の割合×紛らわしい件のまちがい×同じ相手に寄る確率＝27通り（各200回）
    grid = []
    for hd in [0.1, 0.2, 0.3]:
        for eh in [0.2, 0.3, 0.4]:
            for sm in [0.5, 0.8, 0.95]:
                kw = {**BASE, "hard": hd, "e_hard": eh, "same": sm}
                df = pd.DataFrame([one(np.random.default_rng([SEED, 4, int(hd * 100), int(eh * 100), int(sm * 100), i]), **kw)
                                   for i in range(200)])
                fe, fd, fb = formula(hd, BASE["e_easy"], eh, sm)
                row = {"hard": hd, "e_hard": eh, "same": sm, "true_rest_mean": r(df.true_rest.mean(), 2)}
                for m in ("disagree", "half", "review", "truth"):
                    row[f"{m}_ratio"] = r((df[m] / df.true_rest).mean())
                row["review_ratio_formula"] = r((fe - fb) / fe)
                row["disagree_ratio_formula"] = r(fd / fe)
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    robust = {"combos": 27}
    for m in ("disagree", "half", "review", "truth"):
        robust[m] = [r(grid[f"{m}_ratio"].min()), r(grid[f"{m}_ratio"].max())]
        robust[f"{m}_combos_below_1"] = int((grid[f"{m}_ratio"] < 1).sum())
    for sm in [0.5, 0.8, 0.95]:
        g = grid[grid.same == sm]
        robust[f"review_same_{sm}"] = [r(g.review_ratio.min()), r(g.review_ratio.max())]
    robust["review_max_abs_gap_from_formula"] = r((grid.review_ratio - grid.review_ratio_formula).abs().max())
    robust["disagree_max_abs_gap_from_formula"] = r((grid.disagree_ratio - grid.disagree_ratio_formula).abs().max())

    out = {"headline": head, "by_check_size": by_n.to_dict("records"), "copy_half": copy_s, "robust": robust,
           "setting": {**BASE, "items": N, "shares": P.tolist(), "reps": 500}}
    with open(RES / "a1240_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：見込み÷本当（基本の置き方）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ms = list(METHODS)
    vals = [head[m]["ratio_mean"] for m in ms]
    lo = [head[m]["ratio_p10"] for m in ms]
    hi = [head[m]["ratio_p90"] for m in ms]
    cols = [ORANGE, ORANGE, BLUE, GREEN]
    ax.bar(range(4), vals, color=cols, width=0.6)
    ax.errorbar(range(4), vals, yerr=[np.array(vals) - lo, np.array(hi) - vals], fmt="none", ecolor=INK, capsize=4, lw=1)
    for i, v in enumerate(vals):
        ax.text(i, 0.06, f"{v:.3f}倍", ha="center", fontsize=10, color="white")
    ax.axhline(1, color=INK, lw=0.8, ls="--")
    ax.set_xticks(range(4), [METHODS[m] for m in ms], fontsize=8.5)
    ax.set_ylim(0, 2)
    ax.set_ylabel("見込んだ数÷本当のまちがいの数（倍）")
    ax.set_title("残り9,500件のまちがいの数の見込み（500回の平均、線は10〜90%）", fontsize=12)
    save(fig, "a1240_estimates.png", SRC)

    # 図2：確かめる件の数と見込みの幅
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = by_n.n_check.values
    ax.fill_between(x, by_n.truth_ratio_p10, by_n.truth_ratio_p90, color=GREEN, alpha=0.25)
    ax.plot(x, by_n.truth_ratio_mean, "o-", color=GREEN, label="④確かめた件をすべて正解と照らす")
    ax.fill_between(x, by_n.review_ratio_p10, by_n.review_ratio_p90, color=BLUE, alpha=0.2)
    ax.plot(x, by_n.review_ratio_mean, "o-", color=BLUE, label="③食い違った件だけ見直す")
    ax.axhline(1, color=INK, lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_xticks(x, [f"{v:,}" for v in x])
    ax.set_ylim(0, 1.8)
    ax.set_xlabel("2人で付けて確かめた件の数")
    ax.set_ylabel("見込み÷本当（倍）")
    ax.set_title("確かめる件を増やすと幅は狭まるが、③の平均は1倍の下に残る", fontsize=12)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1240_check_size.png", SRC)

    # 図3：27通りの③
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    cmap = {0.1: LIGHT, 0.2: BLUE, 0.3: INK}
    for hd in [0.1, 0.2, 0.3]:
        g = grid[grid.hard == hd]
        jit = {0.2: -0.012, 0.3: 0, 0.4: 0.012}
        ax.scatter(g.same + g.e_hard.map(jit), g.review_ratio, color=cmap[hd], s=30, label=f"紛らわしい件 {int(hd*100)}%")
    ax.axhline(1, color=INK, lw=0.8, ls="--")
    ax.set_xticks([0.5, 0.8, 0.95], ["50%", "80%", "95%"])
    ax.set_ylim(0, 1.1)
    ax.set_xlabel("紛らわしい件でまちがえるとき、同じ相手の分類に寄る確率")
    ax.set_ylabel("③の見込み÷本当（倍）")
    ax.set_title("③食い違った件だけ見直す見込み（27通り、各200回）", fontsize=12)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.text(0.99, 0.05, "各まとまりの3点は、左から紛らわしい件でまちがえる確率20・30・40%", transform=ax.transAxes,
            ha="right", fontsize=8.5, color=GRAY)
    save(fig, "a1240_grid.png", SRC)
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
