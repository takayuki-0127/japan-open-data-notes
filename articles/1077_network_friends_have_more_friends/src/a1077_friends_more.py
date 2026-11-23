"""1077 「自分の知り合いは、自分より知り合いが多い」と感じるのはなぜか？（架空のデータ）

架空の会員コミュニティ（会員2,000人）の知り合いのつながりを、作成者が置いた「知り合いの作りやすさ」から
乱数で作る。会員から1人選んだときの知り合いの数と、知り合いから1人選んだときの知り合いの数を比べ、
「知り合いの平均が自分より多い」会員の割合を数える。人ごとの作りやすさの差の大きさを変えて確かめる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1077
SRC = "架空の会員コミュニティの知り合い（作成者が置いた作りやすさからの乱数、seed 1077）"
N = 2000
BASE = {"mean": 8.0, "cv": 1.0}
REPS = 50
GRID_CV = [0.0, 0.5, 1.0, 1.5]
GRID_MEAN = [4.0, 8.0, 16.0]
GRID_REPS = 10
BINS = [(0, 0), (1, 2), (3, 5), (6, 10), (11, 20), (21, 40), (41, 10 ** 6)]


def r(x, d=4):
    return round(float(x), d)


def network(rng, mean, cv):
    """作りやすさ w（平均 mean、変動係数 cv のガンマ分布）から、i と j が知り合いの確率 min(1, w_i w_j / Σw)"""
    if cv == 0:
        w = np.full(N, mean)
    else:
        k = 1 / cv ** 2
        w = rng.gamma(k, mean / k, N)
    p = np.minimum(1.0, np.outer(w, w) / w.sum())
    u = rng.random((N, N))
    a = np.triu(u < p, 1)
    a = a | a.T
    return a.astype(np.int32), w


def measure(a):
    d = a.sum(1).astype(float)
    m = d > 0
    fm = np.zeros(N)
    fm[m] = (a @ d)[m] / d[m]
    more_frac = np.zeros(N)
    # 知り合いのうち、自分より知り合いの多い人の割合
    hi = (d[None, :] > d[:, None]).astype(np.int32)
    more_frac[m] = (a * hi).sum(1)[m] / d[m]
    srt = np.sort(d)[::-1]
    return {"mean_deg": d.mean(), "var_deg": d.var(), "median_deg": np.median(d),
            "isolated_share": 1 - m.mean(),
            "pooled_friend_mean": (d ** 2).sum() / d.sum(),
            "formula_mean_plus_var_over_mean": d.mean() + d.var() / d.mean(),
            "person_avg_friend_mean": fm[m].mean(), "median_friend_mean": np.median(fm[m]),
            "share_friends_more": (fm[m] > d[m]).mean(), "share_friends_equal": (fm[m] == d[m]).mean(),
            "share_friends_less": (fm[m] < d[m]).mean(),
            "share_friends_more_above_mean": (fm[d > d.mean()] > d[d > d.mean()]).mean(),
            "avg_share_of_friends_with_more": more_frac[m].mean(),
            "share_majority_friends_more": (more_frac[m] > 0.5).mean(),
            "top10pct_tie_end_share": srt[: N // 10].sum() / d.sum(),
            "max_deg": d.max()}, d, fm, more_frac


def pick_dist(d):
    """会員から1人選んだとき／つながりの端から1人選んだとき（知り合いから1人選ぶ）の、知り合いの数の分布"""
    pm, pt = [], []
    for lo, hi in BINS:
        s = (d >= lo) & (d <= hi)
        pm.append(s.mean())
        pt.append(d[s].sum() / d.sum())
    return np.array(pm), np.array(pt)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows, dists = [], []
    first = None
    for i in range(REPS):
        a, w = network(rng, **BASE)
        met, d, fm, mf = measure(a)
        rows.append({"rep": i, **{k: r(v, 4) for k, v in met.items()}})
        dists.append(pick_dist(d))
        if first is None:
            first = (a, w, d, fm, mf)
    br = pd.DataFrame(rows)
    br.to_csv(RES / "base_reps.csv", index=False)
    pm = np.mean([x[0] for x in dists], 0)
    pt = np.mean([x[1] for x in dists], 0)
    labels = ["0人" if lo == hi == 0 else (f"{lo}〜{hi}人" if hi < 10 ** 6 else f"{lo}人以上") for lo, hi in BINS]
    pdist = pd.DataFrame({"bin": labels, "pick_member_pct": (pm * 100).round(2), "pick_friend_pct": (pt * 100).round(2)})
    pdist.to_csv(RES / "pick_distribution.csv", index=False)

    # 確かめ：作りやすさの差（変動係数）× 平均の知り合いの数（12通り、各10回）
    grid = []
    j = 0
    for cv in GRID_CV:
        for mean in GRID_MEAN:
            g_rng = np.random.default_rng(SEED * 100 + j)
            j += 1
            ms = [measure(network(g_rng, mean, cv)[0])[0] for _ in range(GRID_REPS)]
            avg = {k: float(np.mean([x[k] for x in ms])) for k in ms[0]}
            grid.append({"cv": cv, "mean_set": mean, "mean_deg": r(avg["mean_deg"], 3),
                         "pooled_friend_mean": r(avg["pooled_friend_mean"], 3),
                         "ratio_pooled": r(avg["pooled_friend_mean"] / avg["mean_deg"], 3),
                         "person_avg_friend_mean": r(avg["person_avg_friend_mean"], 3),
                         "ratio_person_avg": r(avg["person_avg_friend_mean"] / avg["mean_deg"], 3),
                         "share_friends_more_pct": r(avg["share_friends_more"] * 100, 2),
                         "share_friends_less_pct": r(avg["share_friends_less"] * 100, 2),
          "avg_share_of_friends_with_more_pct": r(avg["avg_share_of_friends_with_more"] * 100, 2),
                         "isolated_pct": r(avg["isolated_share"] * 100, 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    # data：1回分の会員と知り合いのつながり
    a, w, d, fm, mf = first
    pd.DataFrame({"member_id": [f"M{i:04d}" for i in range(N)], "ease_set": w.round(3), "n_acquaintances": d.astype(int),
                  "friends_mean": fm.round(3), "share_friends_with_more": mf.round(4)}).to_csv(DATA / "members_one_run.csv", index=False)
    ii, jj = np.nonzero(np.triu(a, 1))
    pd.DataFrame({"member_a": [f"M{i:04d}" for i in ii], "member_b": [f"M{k:04d}" for k in jj]}).to_csv(DATA / "ties_one_run.csv", index=False)

    M = br.mean(numeric_only=True)
    poisson = g[g.cv == 0]
    hl = {"mean_deg": r(M.mean_deg, 2), "median_deg": r(M.median_deg, 2), "var_deg": r(M.var_deg, 2),
          "isolated_pct": r(M.isolated_share * 100, 2),
          "pooled_friend_mean": r(M.pooled_friend_mean, 2),
          "formula_mean_plus_var_over_mean": r(M.formula_mean_plus_var_over_mean, 2),
          "max_abs_diff_pooled_vs_formula": r((br.pooled_friend_mean - br.formula_mean_plus_var_over_mean).abs().max(), 4),
          "ratio_pooled": r(M.pooled_friend_mean / M.mean_deg, 3),
          "person_avg_friend_mean": r(M.person_avg_friend_mean, 2),
          "ratio_person_avg": r(M.person_avg_friend_mean / M.mean_deg, 3),
          "median_friend_mean": r(M.median_friend_mean, 2),
          "share_friends_more_pct": r(M.share_friends_more * 100, 2),
          "share_friends_equal_pct": r(M.share_friends_equal * 100, 2),
          "share_friends_less_pct": r(M.share_friends_less * 100, 2),
          "share_friends_more_min_pct": r(br.share_friends_more.min() * 100, 2),
          "share_friends_more_max_pct": r(br.share_friends_more.max() * 100, 2),
          "share_friends_more_above_mean_pct": r(M.share_friends_more_above_mean * 100, 2),
          "avg_share_of_friends_with_more_pct": r(M.avg_share_of_friends_with_more * 100, 2),
          "share_majority_friends_more_pct": r(M.share_majority_friends_more * 100, 2),
          "top10pct_tie_end_share_pct": r(M.top10pct_tie_end_share * 100, 2),
          "pick_member_ge11_pct": r(pm[4:].sum() * 100, 2), "pick_friend_ge11_pct": r(pt[4:].sum() * 100, 2),
          "pick_member_le2_pct": r(pm[:2].sum() * 100, 2), "pick_friend_le2_pct": r(pt[:2].sum() * 100, 2),
          "grid_share_more_min_pct": r(g.share_friends_more_pct.min(), 2),
          "grid_share_more_max_pct": r(g.share_friends_more_pct.max(), 2),
          "grid_ratio_pooled_min": r(g.ratio_pooled.min(), 3), "grid_ratio_pooled_max": r(g.ratio_pooled.max(), 3),
          "cv0_share_more_min_pct": r(poisson.share_friends_more_pct.min(), 2),
          "cv0_share_more_max_pct": r(poisson.share_friends_more_pct.max(), 2),
          "cv0_pooled_minus_mean_min": r((poisson.pooled_friend_mean - poisson.mean_deg).min(), 3),
          "cv0_pooled_minus_mean_max": r((poisson.pooled_friend_mean - poisson.mean_deg).max(), 3),
          "cv0_mean8_share_more_pct": r(poisson[poisson.mean_set == 8].share_friends_more_pct.iloc[0], 2),
          "cv0_mean8_ratio_pooled": r(poisson[poisson.mean_set == 8].ratio_pooled.iloc[0], 3),
          "grid_share_more_gt50_count": int((g.share_friends_more_pct > 50).sum()),
          "grid_more_gt_less_count": int((g.share_friends_more_pct > g.share_friends_less_pct).sum())}
    out = {"base_setting": dict(BASE, n_members=N), "reps": REPS, "grid_reps": GRID_REPS, "headline": hl,
           "pick_distribution": pdist.to_dict("records"), "grid": g.to_dict("records")}
    json.dump(out, open(RES / "a1077_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：会員から選ぶか、知り合いから選ぶかで、知り合いの数の分布（棒、0始まり）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    xx = np.arange(len(BINS)); wd = .38
    ax.bar(xx - wd / 2, pm * 100, wd, color=GRAY, label="会員から1人選ぶ")
    ax.bar(xx + wd / 2, pt * 100, wd, color=BLUE, label="誰かの知り合いから1人選ぶ（つながりの端）")
    for x_, a_, b_ in zip(xx, pm * 100, pt * 100):
        ax.text(x_ - wd / 2, a_ + .6, f"{a_:.1f}", ha="center", fontsize=7.5)
        ax.text(x_ + wd / 2, b_ + .6, f"{b_:.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(xx); ax.set_xticklabels(labels)
    ax.set_ylim(0, max(pm.max(), pt.max()) * 100 * 1.18)
    ax.set_xlabel("その人の知り合いの数"); ax.set_ylabel("選ばれた人の割合（%、50回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"知り合いから選ぶと、知り合いの多い人ほど選ばれやすい（平均{hl['mean_deg']}人→{hl['pooled_friend_mean']}人）")
    save(fig, "a1077_two_picks.png", SRC)

    # 図2：1回分の、自分の知り合いの数と、知り合いの知り合いの数の平均
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    m = d > 0
    jit = np.random.default_rng(SEED + 7).uniform(-.25, .25, N)
    c = np.where(fm[m] > d[m], BLUE, np.where(fm[m] < d[m], ORANGE, GRAY))
    ax.scatter(d[m] + jit[m], fm[m], s=6, c=c, alpha=.45, lw=0)
    lim = max(d.max(), fm.max()) * 1.3
    ax.plot([0.7, lim], [0.7, lim], color=INK, lw=.8, ls="--")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.7, lim); ax.set_ylim(0.7, lim)
    tk = [1, 2, 5, 10, 20, 50]
    ax.set_xticks(tk); ax.set_xticklabels([str(t) for t in tk]); ax.set_yticks(tk); ax.set_yticklabels([str(t) for t in tk])
    ax.minorticks_off()
    ax.scatter([], [], color=BLUE, s=14, label="知り合いの平均が自分より多い")
    ax.scatter([], [], color=ORANGE, s=14, label="知り合いの平均が自分より少ない")
    ax.text(lim / 1.6, lim / 1.35, "同じ", fontsize=8.5, ha="right")
    ax.set_xlabel("自分の知り合いの数（対数の目盛り）"); ax.set_ylabel("自分の知り合いの、知り合いの数の平均（対数の目盛り）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("1回分の会員2,000人：点線より上の会員が多い")
    save(fig, "a1077_scatter.png", SRC)

    # 図3：確かめの12通り（棒、0始まり）
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    wd = .26
    cols = {4.0: LIGHT, 8.0: BLUE, 16.0: INK}
    for k_, mean in enumerate(GRID_MEAN):
        sub = g[g.mean_set == mean]
        xs = np.arange(len(GRID_CV)) + (k_ - 1) * wd
        ax.bar(xs, sub.share_friends_more_pct, wd, color=cols[mean], label=f"平均の知り合い {mean:.0f}人")
        for x_, v in zip(xs, sub.share_friends_more_pct):
            ax.text(x_, v + 1.2, f"{v:.1f}", ha="center", fontsize=7.2)
    ax.axhline(50, color=GRAY, lw=.8, ls="--")
    ax.set_xticks(np.arange(len(GRID_CV)))
    ax.set_xticklabels(["0（全員同じ）", "0.5", "1.0（基本）", "1.5"])
    ax.set_ylim(0, 105); ax.set_xlabel("人ごとの知り合いの作りやすさの差（変動係数）")
    ax.set_ylabel("知り合いの平均が自分より多い会員（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
    ax.set_title("12通り（各10回）：作りやすさが全員同じでも半分を超えた")
    save(fig, "a1077_grid.png", SRC)

    print(json.dumps(hl, ensure_ascii=False, indent=1)); print(pdist.to_string()); print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
