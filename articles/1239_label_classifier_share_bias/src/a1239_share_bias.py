"""1239 分類する仕組みで数えた「当てはまる件の割合」は、見逃しと取り違えでどちらにずれるのか？（架空のデータ）

架空の問い合わせ文を6つの分類（配送・返品・支払い・会員登録・使い方・その他）に分ける。
本当の分類の割合と、分類する仕組みがどの分類をどの分類と取り違えるか（取り違えの表）を作成者が置き、
1か月5,000件の判定を乱数で作る。見かけの割合（仕組みが付けた分類で数えた割合）を本当の割合と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1239
SRC = "架空の問い合わせ文（作成者が置いた分類の割合と取り違えの表からの乱数、seed 1239）"
CATS = ["配送", "返品", "支払い", "会員登録", "使い方", "その他"]
K, N = 6, 5000
P_BASE = np.array([0.34, 0.24, 0.16, 0.12, 0.09, 0.05])
P_FLAT = np.array([0.22, 0.20, 0.17, 0.15, 0.14, 0.12])
P_STEEP = np.array([0.50, 0.20, 0.12, 0.08, 0.06, 0.04])
PAIR = {0: 1, 1: 0, 2: 3, 3: 2, 4: 5, 5: 4}  # 近い分類どうし
PAT_NAME = {"even": "均等", "near": "近い分類に寄る", "other": "「その他」に寄る"}
SHARE_NAME = {"flat": "偏り小", "base": "基本", "steep": "偏り大"}


def conf(acc=0.88, pattern="near", w=0.6):
    """取り違えの表 C[本当, 付けた分類]。正しく付ける確率 acc、まちがい方 pattern。"""
    C = np.zeros((K, K))
    for j in range(K):
        others = [k for k in range(K) if k != j]
        if pattern == "even":
            for k in others:
                C[j, k] = (1 - acc) / (K - 1)
        elif pattern == "near":
            for k in others:
                C[j, k] = (1 - acc) * ((w if k == PAIR[j] else (1 - w) / (K - 2)))
        elif pattern == "other":
            if j == K - 1:
                for k in others:
                    C[j, k] = (1 - acc) / (K - 1)
            else:
                for k in others:
                    C[j, k] = (1 - acc) * (0.5 if k == K - 1 else 0.5 / (K - 2))
        C[j, j] = acc
    return C


def month(rng, p, C, n=N):
    """1か月分の件（本当の分類と付けた分類）を作る。"""
    t = rng.choice(K, size=n, p=p)
    u = rng.random(n)
    cum = np.cumsum(C, axis=1)[t]
    pred = (u[:, None] > cum).sum(1)
    pred = np.minimum(pred, K - 1)
    return t, pred


def shares(x):
    return np.bincount(x, minlength=K) / len(x)


def correct(q, sample_t, sample_p):
    """見本（本当の分類が分かった件）で取り違えの表を見積もり、見かけの割合を割り戻す。"""
    M = np.zeros((K, K))
    np.add.at(M, (sample_t, sample_p), 1)
    Ch = np.eye(K)
    rows = M.sum(1)
    for j in range(K):
        if rows[j] > 0:
            Ch[j] = M[j] / rows[j]
    try:
        p = np.linalg.solve(Ch.T, q)
    except np.linalg.LinAlgError:
        p = np.linalg.pinv(Ch.T) @ q
    raw = p.copy()
    p = np.clip(p, 0, None)
    p = p / p.sum() if p.sum() > 0 else np.full(K, 1 / K)
    return p, raw


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    C = conf()

    # 1回分（data に置く）
    t, pr = month(rng, P_BASE, C)
    pd.DataFrame({"item_id": np.arange(1, N + 1), "true": [CATS[i] for i in t], "pred": [CATS[i] for i in pr]}).to_csv(
        DATA / "month_one.csv", index=False)

    # 1) 基本の置き方で200か月
    seen = np.array([shares(month(np.random.default_rng([SEED, 1, i]), P_BASE, C)[1]) for i in range(200)])
    formula = P_BASE @ C
    missed = P_BASE * (1 - np.diag(C))
    incoming = formula - P_BASE * np.diag(C)
    rows = []
    for k in range(K):
        rows.append({"category": CATS[k], "true": r(P_BASE[k]), "missed": r(missed[k]), "incoming": r(incoming[k]),
                     "seen_formula": r(formula[k]), "seen_mean": r(seen[:, k].mean()),
                     "seen_p10": r(np.percentile(seen[:, k], 10)), "seen_p90": r(np.percentile(seen[:, k], 90)),
                     "ratio": r(seen[:, k].mean() / P_BASE[k]),
                     "share_months_over": r((seen[:, k] > P_BASE[k]).mean())})
    base_tab = pd.DataFrame(rows)
    base_tab.to_csv(RES / "base_by_category.csv", index=False)
    cross_even = 1 / K  # 均等のまちがい方で、上にずれるか下にずれるかの境目（式どおり）
    one_acc = r(float((t == pr).mean()))

    # 2) 1つの分類が1.5倍に増えた月との比べ
    def change(k, mult, reps=200):
        p2 = P_BASE.copy()
        p2[k] = P_BASE[k] * mult
        others = [j for j in range(K) if j != k]
        p2[others] = P_BASE[others] * (1 - p2[k]) / P_BASE[others].sum()
        f1, f2 = (P_BASE @ C)[k], (p2 @ C)[k]
        a, b = [], []
        for i in range(reps):
            a.append(shares(month(np.random.default_rng([SEED, 2, k, i]), P_BASE, C)[1])[k])
            b.append(shares(month(np.random.default_rng([SEED, 3, k, i]), p2, C)[1])[k])
        a, b = np.array(a), np.array(b)
        return {"category": CATS[k], "true_before": r(P_BASE[k]), "true_after": r(p2[k]),
                "true_ratio": r(p2[k] / P_BASE[k]), "true_points": r((p2[k] - P_BASE[k]) * 100, 3),
                "seen_before_formula": r(f1), "seen_after_formula": r(f2),
                "seen_ratio_formula": r(f2 / f1), "seen_points_formula": r((f2 - f1) * 100, 3),
                "seen_ratio_mean": r((b / a).mean()), "seen_ratio_p10": r(np.percentile(b / a, 10)),
                "seen_ratio_p90": r(np.percentile(b / a, 90)),
                "share_pairs_seen_ratio_below_true": r(((b / a) < p2[k] / P_BASE[k]).mean())}
    changes = [change(4, 1.5), change(5, 1.5), change(0, 1.5 ** -1)]
    pd.DataFrame(changes).to_csv(RES / "month_change.csv", index=False)

    # 3) 見本で取り違えの表を見積もって割り戻す（その他と配送）
    corr_rows = []
    for n_s in [100, 300, 1000]:
        est = {"naive": [], "fixed": [], "sample_only": [], "raw_neg": []}
        for i in range(500):
            g = np.random.default_rng([SEED, 4, n_s, i])
            tt, pp = month(g, P_BASE, C)
            idx = g.choice(N, n_s, replace=False)
            q = shares(pp)
            fx, raw = correct(q, tt[idx], pp[idx])
            est["naive"].append(q)
            est["fixed"].append(fx)
            est["sample_only"].append(shares(tt[idx]))
            est["raw_neg"].append(raw < 0)
        for m in ["naive", "fixed", "sample_only"]:
            a = np.array(est[m])
            for k in [0, 5]:
                corr_rows.append({"check_items": n_s, "method": m, "category": CATS[k], "true": r(P_BASE[k]),
                                  "mean": r(a[:, k].mean()), "p10": r(np.percentile(a[:, k], 10)),
                                  "p90": r(np.percentile(a[:, k], 90)),
                                  "mean_abs_error_points": r(np.abs(a[:, k] - P_BASE[k]).mean() * 100, 3),
                                  "share_raw_below_zero": r(np.array(est["raw_neg"])[:, k].mean()) if m == "fixed" else None})
    corr = pd.DataFrame(corr_rows)
    corr.to_csv(RES / "correction.csv", index=False)

    # 4) 確かめ：正しく付ける確率×まちがい方×本当の割合の偏り＝27通り（式で出す）
    grid = []
    for acc in [0.80, 0.88, 0.95]:
        for pat in ["even", "near", "other"]:
            for sh, p in [("flat", P_FLAT), ("base", P_BASE), ("steep", P_STEEP)]:
                f = p @ conf(acc, pat)
                for k in range(K):
                    grid.append({"acc": acc, "pattern": pat, "shares": sh, "category": CATS[k], "rank": k + 1,
                                 "true": r(p[k]), "seen": r(f[k]), "ratio": r(f[k] / p[k])})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g_small = grid[grid["rank"] == 6]
    g_large = grid[grid["rank"] == 1]
    n_over = grid.assign(o=grid.ratio > 1).groupby(["acc", "pattern", "shares"])["o"].sum()
    even = grid[grid.pattern == "even"]
    even_rule_ok = bool(((even.ratio > 1) == (even.true < cross_even)).all())

    robust = {
        "grid_combos": 27,
        "smallest_ratio_min": r(g_small.ratio.min()), "smallest_ratio_max": r(g_small.ratio.max()),
        "smallest_over_combos": int((g_small.ratio > 1).sum()),
        "largest_ratio_min": r(g_large.ratio.min()), "largest_ratio_max": r(g_large.ratio.max()),
        "largest_under_combos": int((g_large.ratio < 1).sum()),
        "categories_over_min": int(n_over.min()), "categories_over_max": int(n_over.max()),
        "even_pattern_over_iff_true_below_one_sixth": even_rule_ok,
        "smallest_ratio_by_acc": {str(a): [r(g_small[g_small.acc == a].ratio.min()), r(g_small[g_small.acc == a].ratio.max())]
                                  for a in [0.80, 0.88, 0.95]},
        "other_pattern_sonota_ratio": [r(grid[(grid.pattern == "other") & (grid["rank"] == 6)].ratio.min()),
                                       r(grid[(grid.pattern == "other") & (grid["rank"] == 6)].ratio.max())],
        "near_pattern_sonota_ratio": [r(grid[(grid.pattern == "near") & (grid["rank"] == 6)].ratio.min()),
                                      r(grid[(grid.pattern == "near") & (grid["rank"] == 6)].ratio.max())],
        "even_pattern_sonota_ratio": [r(grid[(grid.pattern == "even") & (grid["rank"] == 6)].ratio.min()),
                                      r(grid[(grid.pattern == "even") & (grid["rank"] == 6)].ratio.max())],
    }
    # 少ない分類ほど上にずれるか：見かけ÷本当と本当の割合の順位が逆か（27通りのうち完全に逆順の数）
    mono = 0
    for _, gg in grid.groupby(["acc", "pattern", "shares"]):
        mono += int((np.diff(gg.sort_values("true").ratio.values) <= 1e-12).all())
    robust["combos_ratio_falls_with_true_share"] = mono

    base_rows = {row["category"]: row for row in rows}
    headline = {
        "items_per_month": N, "months": 200, "acc_each_category": 0.88, "one_month_correct_share": one_acc,
        "by_category": base_rows,
        "even_pattern_threshold_share": r(cross_even),
        "change": {c["category"]: c for c in changes},
        "correction": corr[corr.category == "その他"].to_dict("records"),
        "correction_haisou": corr[corr.category == "配送"].to_dict("records"),
    }
    out = {"headline": headline, "robust": robust}

    # 図1：本当の割合と見かけの割合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = np.arange(K)
    ax.bar(x - 0.2, P_BASE * 100, 0.4, color=GRAY, label="本当の割合")
    ax.bar(x + 0.2, seen.mean(0) * 100, 0.4, color=BLUE, label="仕組みが付けた分類で数えた割合")
    for i in range(K):
        ax.text(i - 0.2, P_BASE[i] * 100 + 0.6, f"{P_BASE[i]*100:.0f}", ha="center", fontsize=9, color=INK)
        ax.text(i + 0.2, seen[:, i].mean() * 100 + 0.6, f"{seen[:, i].mean()*100:.2f}", ha="center", fontsize=9, color=BLUE)
    ax.set_xticks(x, CATS)
    ax.set_ylim(0, 40)
    ax.set_ylabel("割合（%）")
    ax.set_title("いちばん多い「配送」は少なく、いちばん少ない「その他」は多く数えられた", fontsize=12)
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1239_true_vs_seen.png", SRC)

    # 図2：27通りの見かけ÷本当
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    cols = {"even": GRAY, "near": BLUE, "other": ORANGE}
    for pat in ["even", "near", "other"]:
        gg = grid[grid.pattern == pat]
        ax.scatter(gg.true * 100, gg.ratio, s=16, color=cols[pat], alpha=0.75, label=f"まちがい方：{PAT_NAME[pat]}")
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_xlabel("本当の割合（%）")
    ax.set_ylabel("見かけ÷本当（倍）")
    ax.set_title("見かけ÷本当（27通り×6分類、式どおり）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1239_ratio_grid.png", SRC)

    # 図3：「その他」の割合の見積もり
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    sub = corr[corr.category == "その他"].reset_index(drop=True)
    order = [("naive", 300), ("fixed", 100), ("fixed", 300), ("fixed", 1000), ("sample_only", 100),
             ("sample_only", 300), ("sample_only", 1000)]
    lab = {"naive": "そのまま", "fixed": "見本で\n割り戻す", "sample_only": "見本だけ\nで数える"}
    for i, (m, n_s) in enumerate(order):
        rw = sub[(sub.method == m) & (sub.check_items == n_s)].iloc[0]
        c = {"naive": ORANGE, "fixed": BLUE, "sample_only": GREEN}[m]
        ax.plot([i, i], [rw.p10 * 100, rw.p90 * 100], color=c, lw=3)
        ax.plot(i, rw["mean"] * 100, "o", color=c)
    ax.axhline(P_BASE[5] * 100, color=INK, lw=0.8, ls="--")
    ax.text(0.5, P_BASE[5] * 100 - 0.6, "本当 5%", ha="center", fontsize=9)
    ax.set_xticks(range(len(order)), [lab[m] if m == "naive" else f"{lab[m]}\n{n_s}件" for m, n_s in order], fontsize=8)
    ax.set_ylim(0, 12)
    ax.set_ylabel("「その他」の割合（%）")
    ax.set_title("「その他」の割合の見積もり（点は平均、線は10〜90%、各500回）")
    save(fig, "a1239_correction.png", SRC)

    with open(RES / "a1239_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
