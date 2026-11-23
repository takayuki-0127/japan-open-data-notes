"""1092 千行あたりのバグ数で、チームどうしを比べてよいのか？（架空のデータ）

架空のアプリを8つのチーム（A〜H）が分けて作る。チームごとに、担当する機能の数・1機能を書くのに使う行数（書き方）・
1機能あたりに作りこまれるバグの数（作りの確かさ）・テストで見つかる確率を作成者が置き、乱数でバグの数を作る。
作成者が置いた「1機能あたりの作りこまれたバグ」を正しい答えとし、4つの物差しで並べたときの当たりを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1092
SRC = "架空のアプリの開発チーム（作成者が置いた機能の数・行数・バグの数・見つかる確率からの乱数、seed 1092）"
TEAMS = list("ABCDEFGH")
NT = len(TEAMS)
BASE = {"feat_mean": 60, "sd_lines": 0.3, "p_lo": 0.55, "p_hi": 0.85, "sd_bug": 0.3}
LINES_PER_FEAT = 250   # 1機能あたりの行数の中央（書き方の係数1のとき）
BUG_PER_FEAT = 0.5     # 1機能あたりの作りこまれたバグの中央
REPS = 1000
GRID_REPS = 400
MEASURES = [("found_per_kloc", "① 見つかったバグ÷千行"), ("true_per_kloc", "② 作りこまれたバグ÷千行"),
            ("found_per_feat", "③ 見つかったバグ÷機能の数"), ("true_per_feat", "④ 作りこまれたバグ÷機能の数")]


def r(x, d=4):
    return round(float(x), d)


def teams(rng, reps, feat_mean, sd_lines, p_lo, p_hi, sd_bug):
    """reps 回 × 8チームを一度に作る"""
    sh = (reps, NT)
    feat = np.maximum(5, np.round(feat_mean * np.exp(rng.normal(0, 0.5, sh) - 0.125))).astype(int)
    v = np.exp(rng.normal(0, sd_lines, sh))
    kloc = feat * LINES_PER_FEAT * v / 1000
    b = BUG_PER_FEAT * np.exp(rng.normal(0, sd_bug, sh))
    true = rng.poisson(b * feat)
    p = rng.uniform(p_lo, p_hi, sh)
    found = rng.binomial(true, p)
    return {"feat": feat, "v": v, "kloc": kloc, "b": b, "p": p, "true": true, "found": found,
            "found_per_kloc": found / kloc, "true_per_kloc": true / kloc,
            "found_per_feat": found / feat, "true_per_feat": true / feat}


def rank_rows(x):
    return pd.DataFrame(x).rank(axis=1).values


def score(t):
    """各物差しで並べたときの当たり（正しい答えは b：1機能あたりの作りこまれたバグの置いた値）"""
    rb = rank_rows(t["b"])
    best = t["b"].argmin(1)
    iu = np.triu_indices(NT, 1)
    db = (t["b"][:, :, None] - t["b"][:, None, :])[:, iu[0], iu[1]]
    out = {}
    for key, _ in MEASURES:
        x = t[key]
        rx = rank_rows(x)
        rc = np.mean([np.corrcoef(rb[i], rx[i])[0, 1] for i in range(len(x))])
        lo = x.min(1, keepdims=True)
        hit = np.mean((x[np.arange(len(x)), best] == lo[:, 0]) / (x == lo).sum(1))  # 同じ値のときは等分
        dx = (x[:, :, None] - x[:, None, :])[:, iu[0], iu[1]]
        pair = np.mean(np.sign(dx) == np.sign(db))
        out[key] = {"rank_corr": r(rc), "best_hit": r(hit), "pair_right": r(pair)}
    return out


def main():
    rng = np.random.default_rng(SEED)
    # 1) 1回分の8チーム
    one = teams(rng, 1, **BASE)
    df = pd.DataFrame({"team": TEAMS, "features": one["feat"][0], "lines_factor": one["v"][0].round(4),
                       "kloc": one["kloc"][0].round(3), "bug_rate_set": one["b"][0].round(4),
                       "find_prob_set": one["p"][0].round(4), "true_bugs": one["true"][0],
                       "found_bugs": one["found"][0]})
    df["found_per_kloc"] = (df.found_bugs / df.kloc).round(4)
    df["true_per_feat"] = (df.true_bugs / df.features).round(4)
    df.to_csv(DATA / "teams_one_draw.csv", index=False)
    rb = df.bug_rate_set.rank().astype(int)
    rk = df.found_per_kloc.rank().astype(int)
    one_res = {"rank_by_set_rate": dict(zip(TEAMS, rb.tolist())), "rank_by_found_per_kloc": dict(zip(TEAMS, rk.tolist())),
               "best_true": TEAMS[int(df.bug_rate_set.idxmin())], "best_by_found_per_kloc": TEAMS[int(df.found_per_kloc.idxmin())],
               "rank_corr": r(np.corrcoef(rb, rk)[0, 1]),
               "teams": df.drop(columns=["true_per_feat"]).assign(found_per_kloc=df.found_per_kloc.round(2),
                                                                   kloc=df.kloc.round(2)).to_dict("records")}

    # 2) 基本の置き方で1000回
    t = teams(np.random.default_rng(SEED * 10), REPS, **BASE)
    base = score(t)
    # 千行あたりの比は「バグの比×見つかる確率の比÷行数の係数の比」（期待値の式どおり）の確かめ：1チームを大きくして
    big = teams(np.random.default_rng(SEED * 11), 2000, **{**BASE, "feat_mean": 20000})
    lhs = np.log(big["found_per_kloc"][:, 0] / big["found_per_kloc"][:, 1])
    rhs = np.log((big["b"][:, 0] / big["b"][:, 1]) * (big["p"][:, 0] / big["p"][:, 1]) / (big["v"][:, 0] / big["v"][:, 1]))
    formula = {"max_abs_log_gap": r(np.abs(lhs - rhs).max()), "median_abs_log_gap": r(np.median(np.abs(lhs - rhs)))}

    # 3) 全チームの作りの確かさが同じ（sd_bug=0）でも、千行あたりはどれだけ離れるか
    same = teams(np.random.default_rng(SEED * 12), REPS, **{**BASE, "sd_bug": 0.0})
    ratio = same["found_per_kloc"].max(1) / np.maximum(same["found_per_kloc"].min(1), 1e-9)
    ratio_f = same["true_per_feat"].max(1) / np.maximum(same["true_per_feat"].min(1), 1e-9)
    same_res = {"max_over_min_found_per_kloc_median": r(np.median(ratio), 2), "p10": r(np.quantile(ratio, .1), 2),
                "p90": r(np.quantile(ratio, .9), 2), "share_ge_1_5": r((ratio >= 1.5).mean()),
                "max_over_min_true_per_feat_median": r(np.median(ratio_f), 2)}

    # 4) 置き方を変えた確かめ：行数の書き方の差 × 見つかる確率の差 × 機能の数
    rows = []
    gi = 0
    for sd_l in [0.0, 0.3, 0.5]:
        for (plo, phi) in [(0.7, 0.7), (0.55, 0.85), (0.4, 1.0)]:
            for fm in [15, 60, 240]:
                gi += 1
                g = teams(np.random.default_rng(SEED * 100 + gi), GRID_REPS,
                          feat_mean=fm, sd_lines=sd_l, p_lo=plo, p_hi=phi, sd_bug=BASE["sd_bug"])
                s = score(g)
                rows.append({"sd_lines": sd_l, "find_prob": f"{plo}-{phi}", "feat_mean": fm,
                             **{f"{k}_rank_corr": s[k]["rank_corr"] for k, _ in MEASURES},
                             **{f"{k}_best_hit": s[k]["best_hit"] for k, _ in MEASURES}})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    # 作りの確かさの差（sd_bug）を変えると
    spread = {}
    for i, sb in enumerate([0.15, 0.3, 0.6]):
        g = teams(np.random.default_rng(SEED * 200 + i), GRID_REPS, **{**BASE, "sd_bug": sb})
        s = score(g)
        spread[str(sb)] = {k: s[k] for k, _ in MEASURES}

    tab = pd.DataFrame([{"measure": lab, **base[k]} for k, lab in MEASURES])
    tab.to_csv(RES / "measures_base.csv", index=False)
    out = {"base_setting": BASE, "random_pick_best_hit": r(1 / NT), "same_quality_ratio_threshold": 1.5, "lines_per_feature_center": LINES_PER_FEAT, "bugs_per_feature_center": BUG_PER_FEAT,
           "one_draw": one_res, "base_1000reps": base, "formula_check_large_teams": formula,
           "same_quality_all_teams": same_res,
           "grid_range": {k: {"rank_corr_min": r(grid[f"{k}_rank_corr"].min()), "rank_corr_max": r(grid[f"{k}_rank_corr"].max()),
                              "best_hit_min": r(grid[f"{k}_best_hit"].min()), "best_hit_max": r(grid[f"{k}_best_hit"].max())}
                          for k, _ in MEASURES},
           "grid_found_per_kloc_below_found_per_feat": int((grid.found_per_kloc_rank_corr < grid.found_per_feat_rank_corr).sum()),
           "grid_found_per_kloc_below_true_per_kloc": int((grid.found_per_kloc_rank_corr < grid.true_per_kloc_rank_corr).sum()),
           "grid_n": int(len(grid)),
           "grid_with_lines_gap_n": int((grid.sd_lines > 0).sum()),
           "grid_with_lines_gap_found_per_kloc_below_found_per_feat": int(((grid.sd_lines > 0) & (grid.found_per_kloc_rank_corr < grid.found_per_feat_rank_corr)).sum()),
           "grid_no_lines_gap_found_per_kloc_equal_found_per_feat": int(((grid.sd_lines == 0) & (grid.found_per_kloc_rank_corr == grid.found_per_feat_rank_corr)).sum()),
           "by_quality_spread": spread}
    json.dump(out, open(RES / "a1092_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の8チーム（置いた1機能あたりのバグ と 見つかったバグ÷千行）
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(df.bug_rate_set, df.found_per_kloc, s=60, color=BLUE, zorder=3)
    xr, yr = df.bug_rate_set.max(), df.found_per_kloc.max()
    placed = []
    for _, row in df.sort_values("bug_rate_set").iterrows():
        near = any(abs(row.bug_rate_set - a) < 0.08 * xr and abs(row.found_per_kloc - b) < 0.1 * yr for a, b in placed)
        ax.annotate(row.team, (row.bug_rate_set, row.found_per_kloc), xytext=(0, -15 if near else 8),
                    textcoords="offset points", ha="center", fontsize=10, color=INK)
        placed.append((row.bug_rate_set, row.found_per_kloc))
    lines = ["チーム  行数の係数  見つかる確率"] + [f"   {t.team}        {t.lines_factor:.2f}倍        {t.find_prob_set*100:.0f}%"
                                         for _, t in df.iterrows()]
    ax.text(0.99, 0.02, "\n".join(lines), transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color=INK,
            bbox=dict(facecolor="white", edgecolor=GRAY, lw=0.5))
    ax.set_xlabel("置いた1機能あたりの作りこまれたバグ（正しい答え、小さいほど確か）")
    ax.set_ylabel("見つかったバグ÷千行")
    ax.set_xlim(0, df.bug_rate_set.max() * 1.6); ax.set_ylim(0, df.found_per_kloc.max() * 1.15)
    ax.set_title(f"1回分の8チーム：本当にいちばん確かなのは{one_res['best_true']}、千行あたりでいちばん少ないのは{one_res['best_by_found_per_kloc']}")
    save(fig, "a1092_one_draw.png", SRC)

    # 図2：物差しごとのいちばん確かなチームの当たり（1000回）
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    labs = [lab for _, lab in MEASURES][::-1]
    vals = [base[k]["best_hit"] * 100 for k, _ in MEASURES][::-1]
    ax.barh(labs, vals, color=[GREEN, LIGHT, LIGHT, ORANGE])
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:.2f}%", va="center", fontsize=9)
    ax.axvline(100 / NT, color=GRAY, lw=1, ls="--"); ax.text(100 / NT + 1, 3.55, "でたらめに選ぶと12.5%", color=GRAY, fontsize=8); ax.set_ylim(-0.6, 3.85)
    ax.set_xlim(0, 100); ax.set_xlabel("いちばん確かなチームを当てた割合（%、8チーム×1000回）")
    ax.set_title("基本の置き方では、千行あたりで選ぶと当たりが下がる")
    save(fig, "a1092_best_hit.png", SRC)

    # 図3：置き方27通りの順位相関（①と③④）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(grid))
    ax.plot(x, grid.found_per_kloc_rank_corr, "o", color=ORANGE, label="① 見つかったバグ÷千行")
    ax.plot(x, grid.found_per_feat_rank_corr, "s", color=BLUE, ms=4, label="③ 見つかったバグ÷機能の数")
    ax.plot(x, grid.true_per_feat_rank_corr, "^", color=GREEN, ms=4, label="④ 作りこまれたバグ÷機能の数")
    for k in range(1, 3):
        ax.axvline(k * 9 - 0.5, color=GRAY, lw=0.6)
    for k, s in enumerate(["行数の差なし", "行数の差 0.3", "行数の差 0.5"]):
        ax.text(k * 9 + 4, 1.03, s, ha="center", fontsize=8, color=INK)
    ax.set_ylim(0, 1.08); ax.set_xticks([])
    ax.set_xlabel("置き方27通り（各区切りの中は、見つかる確率の差3通り×機能の数15・60・240）")
    ax.set_ylabel("正しい答えとの順位相関（400回の平均）")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title("行数の書き方に差を置くと、千行あたりの並びは③④より正しい答えから離れる")
    save(fig, "a1092_robust.png", SRC)


if __name__ == "__main__":
    main()
