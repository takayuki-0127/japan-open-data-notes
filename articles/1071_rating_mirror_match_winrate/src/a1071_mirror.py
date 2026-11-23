"""1071 同じキャラクターどうしの対戦を数に入れると、勝率はどう見えるのか？（架空のデータ）

架空の対戦ゲームのリーグ（キャラクター12体）。キャラクターの使われる割合と、キャラクターどうしの
本当の勝ちやすさを作成者が置く。両方の側が同じキャラクターを選ぶ「同キャラ戦」を、
  ① 両方の側を1勝1敗として数に入れる
  ② 「そのキャラクターが出た試合のうち、そのキャラクターが勝った試合」と試合単位で数える（同キャラ戦は必ず勝ち）
  ③ 同キャラ戦を外す（本当の勝率＝ほかのキャラクターとの対戦の勝率）
の3つで数え、勝率と順位がどれだけずれるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1071
SRC = "架空の対戦ゲームのリーグ（作成者が乱数で作成、seed 1071）"
K = 12
N_MATCH = 30000          # 1週間の試合数
N_LEAGUE = 2000          # リーグを作り直す回数
BASE = {"zipf": 0.8, "sd": 0.2, "rho": 0.5, "matchup_sd": 0.15}
NAMES = [chr(ord("A") + i) for i in range(K)]


def usage(a):
    p = np.arange(1, K + 1, dtype=float) ** (-a)
    return p / p.sum()


def make_league(rng, a, sd, rho, msd):
    """使われる割合 p（A がいちばん多い）、強さ s、勝つ確率の表 P[i,j]（i が j に勝つ確率）"""
    p = usage(a)
    z = -(np.arange(K) - (K - 1) / 2) / np.std(np.arange(K))   # 使われる順の標準化（A が大きい）
    s = sd * (rho * z + np.sqrt(1 - rho ** 2) * rng.standard_normal(K))
    e = rng.normal(0, msd, (K, K)); e = np.triu(e, 1); e = e - e.T
    P = 1 / (1 + np.exp(-(s[:, None] - s[None, :] + e)))
    np.fill_diagonal(P, 0.5)
    return p, s, P


def formulas(p, P):
    """式：③ 本当の勝率（同キャラ戦を外す）、① 両側を1勝1敗、② 試合単位"""
    off = P.copy(); np.fill_diagonal(off, 0)
    q = p[None, :].repeat(K, 0); np.fill_diagonal(q, 0)
    w3 = (off * q).sum(1) / (1 - p)
    w1 = (1 - p) * w3 + p * 0.5
    w2 = (2 * (1 - p) * w3 + p) / (2 - p)
    return w3, w1, w2


def simulate(rng, p, P, n=N_MATCH):
    a = rng.choice(K, n, p=p); b = rng.choice(K, n, p=p)
    a_win = rng.random(n) < P[a, b]
    return a, b, a_win


def count(a, b, a_win):
    """乱数の試合から ①②③ を数える"""
    w1 = np.zeros(K); w2 = np.zeros(K); w3 = np.zeros(K)
    for i in range(K):
        sa, sb = a == i, b == i
        wins_side = (sa & a_win).sum() + (sb & ~a_win).sum()
        sides = sa.sum() + sb.sum()
        w1[i] = wins_side / sides
        mir = sa & sb
        w3[i] = (wins_side - mir.sum()) / (sides - 2 * mir.sum())
        played = sa | sb
        won = (sa & a_win) | (sb & ~a_win)
        w2[i] = won.sum() / played.sum()
    return w3, w1, w2


def spearman(x, y):
    rx = pd.Series(x).rank().values; ry = pd.Series(y).rank().values
    return float(np.corrcoef(rx, ry)[0, 1])


def league_stats(w_true, w_est):
    order_true = np.argsort(-w_true)
    top_true = order_true[0]
    est_top = int(np.argmax(w_est))
    pairs = [(i, j) for i in range(K) for j in range(i + 1, K)]
    flips = np.mean([(w_true[i] - w_true[j]) * (w_est[i] - w_est[j]) < 0 for i, j in pairs])
    top3 = len(set(order_true[:3]) & set(np.argsort(-w_est)[:3])) / 3
    return {"top_miss": est_top != top_true, "pair_flip": flips, "spearman": spearman(w_true, w_est), "top3_hit": top3}


def r2(x):
    return round(float(x), 2)


def main():
    t0 = time.time()
    b = BASE
    res = {"setting": {"characters": K, **b, "matches_per_week": N_MATCH, "leagues": N_LEAGUE,
                       "usage_base_pct": [r2(v * 100) for v in usage(b["zipf"])]}}

    # 例の1リーグ（式と、1週間3万試合の乱数）
    rng = np.random.default_rng(SEED)
    p, s, P = make_league(rng, b["zipf"], b["sd"], b["rho"], b["matchup_sd"])
    w3, w1, w2 = formulas(p, P)
    a, bb, aw = simulate(rng, p, P)
    m3, m1, m2 = count(a, bb, aw)
    ex = pd.DataFrame({"character": NAMES, "usage_pct": np.round(p * 100, 2), "strength": np.round(s, 3),
                       "true_winrate_pct": np.round(w3 * 100, 2), "mirror_in_pct_formula": np.round(w1 * 100, 2),
                       "per_match_pct_formula": np.round(w2 * 100, 2),
                       "true_winrate_pct_week": np.round(m3 * 100, 2), "mirror_in_pct_week": np.round(m1 * 100, 2),
                       "per_match_pct_week": np.round(m2 * 100, 2),
                       "mirror_share_of_sides_pct_week": [r2(((a == i) & (bb == i)).sum() * 2 / ((a == i).sum() + (bb == i).sum()) * 100) for i in range(K)]})
    for c, w in [("rank_true", w3), ("rank_mirror_in", w1), ("rank_per_match", w2)]:
        ex[c] = pd.Series(-w).rank(method="min").astype(int).values
    ex.to_csv(RES / "example_league.csv", index=False)
    pd.DataFrame({"match": np.arange(1, N_MATCH + 1), "char_side1": np.array(NAMES)[a], "char_side2": np.array(NAMES)[bb],
                  "winner_side": np.where(aw, 1, 2)}).to_csv(DATA / "matches_example_week.csv", index=False)
    top = ex.iloc[0]
    res["example"] = {
        "top_usage_char": "A", "top_usage_pct": float(top.usage_pct),
        "A_true": float(top.true_winrate_pct), "A_mirror_in": float(top.mirror_in_pct_formula), "A_per_match": float(top.per_match_pct_formula),
        "A_mirror_share_week": float(top.mirror_share_of_sides_pct_week),
        "true_top": NAMES[int(np.argmax(w3))], "mirror_in_top": NAMES[int(np.argmax(w1))], "per_match_top": NAMES[int(np.argmax(w2))],
        "max_abs_week_minus_formula_pt": {"true": r2(np.abs(m3 - w3).max() * 100), "mirror_in": r2(np.abs(m1 - w1).max() * 100),
                                         "per_match": r2(np.abs(m2 - w2).max() * 100)},
        "usage_weighted_mean_mirror_in_pct": r2((p * w1).sum() * 100),
        "spearman_true_vs_mirror_in": r2(spearman(w3, w1)), "spearman_true_vs_per_match": r2(spearman(w3, w2)),
    }

    # 2,000リーグ：式の値どうし（数え方だけのずれ）と、1週間3万試合の乱数（数え方＋振れ）
    rows = []
    for L in range(N_LEAGUE):
        r = np.random.default_rng(SEED * 1000 + L)
        p, s, P = make_league(r, b["zipf"], b["sd"], b["rho"], b["matchup_sd"])
        w3, w1, w2 = formulas(p, P)
        a, bb, aw = simulate(r, p, P)
        m3, m1, m2 = count(a, bb, aw)
        row = {"league": L}
        for key, est in [("f_mirror_in", w1), ("f_per_match", w2), ("wk_true", m3), ("wk_mirror_in", m1), ("wk_per_match", m2)]:
            for k2, v in league_stats(w3, est).items():
                row[f"{key}_{k2}"] = float(v)
        row["A_true"] = w3[0] * 100; row["A_mirror_in"] = w1[0] * 100; row["A_per_match"] = w2[0] * 100
        row["A_is_true_top"] = bool(np.argmax(w3) == 0)
        rows.append(row)
    lg = pd.DataFrame(rows)
    lg.round(4).to_csv(RES / "leagues_base.csv", index=False)
    summ = {}
    for key in ["f_mirror_in", "f_per_match", "wk_true", "wk_mirror_in", "wk_per_match"]:
        summ[key] = {"top_miss_pct": r2(lg[f"{key}_top_miss"].mean() * 100), "pair_flip_pct": r2(lg[f"{key}_pair_flip"].mean() * 100),
                     "spearman_mean": round(float(lg[f"{key}_spearman"].mean()), 3), "top3_hit_pct": r2(lg[f"{key}_top3_hit"].mean() * 100)}
    res["leagues_base"] = summ
    res["A_mean"] = {"true": r2(lg.A_true.mean()), "mirror_in": r2(lg.A_mirror_in.mean()), "per_match": r2(lg.A_per_match.mean()),
                     "A_true_top_pct": r2(lg.A_is_true_top.mean() * 100)}
    at = lg[lg.A_is_true_top]
    res["when_A_true_top"] = {"leagues": int(len(at)), "mirror_in_top_miss_pct": r2(at.f_mirror_in_top_miss.mean() * 100),
                              "per_match_top_miss_pct": r2(at.f_per_match_top_miss.mean() * 100)}
    na = lg[~lg.A_is_true_top]
    res["when_A_not_true_top"] = {"leagues": int(len(na)), "mirror_in_top_miss_pct": r2(na.f_mirror_in_top_miss.mean() * 100),
                                  "per_match_top_miss_pct": r2(na.f_per_match_top_miss.mean() * 100)}

    # 確かめ：使われ方の偏り×強さの差×人気と強さの相関（27通り、各500リーグ、式の値）
    grid = []; j = 0
    for za in [0.4, 0.8, 1.2]:
        for sd in [0.1, 0.2, 0.35]:
            for rho in [0.0, 0.5, 0.8]:
                st = {"f_mirror_in": [], "f_per_match": []}
                for L in range(500):
                    r = np.random.default_rng(SEED * 100000 + j * 1000 + L)
                    p, s, P = make_league(r, za, sd, rho, b["matchup_sd"])
                    w3, w1, w2 = formulas(p, P)
                    st["f_mirror_in"].append(league_stats(w3, w1)); st["f_per_match"].append(league_stats(w3, w2))
                j += 1
                g = {"zipf": za, "top_usage_pct": r2(usage(za)[0] * 100), "strength_sd": sd, "rho": rho}
                for key, lst in st.items():
                    d = pd.DataFrame(lst)
                    g[f"{key}_top_miss_pct"] = r2(d.top_miss.mean() * 100)
                    g[f"{key}_pair_flip_pct"] = r2(d.pair_flip.mean() * 100)
                grid.append(g)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    res["grid_range"] = {k: [float(grid[k].min()), float(grid[k].max())] for k in
                         ["f_mirror_in_top_miss_pct", "f_per_match_top_miss_pct", "f_mirror_in_pair_flip_pct", "f_per_match_pair_flip_pct"]}
    res["grid_range"]["n_cases"] = int(len(grid))
    res["grid_range"]["per_match_worse_than_mirror_in_cases"] = int((grid.f_per_match_top_miss_pct > grid.f_mirror_in_top_miss_pct).sum())
    res["grid_by_zipf_mirror_in_top_miss_mean"] = {str(z): r2(grid[grid.zipf == z].f_mirror_in_top_miss_pct.mean()) for z in [0.4, 0.8, 1.2]}
    res["grid_by_sd_mirror_in_top_miss_mean"] = {str(z): r2(grid[grid.strength_sd == z].f_mirror_in_top_miss_pct.mean()) for z in [0.1, 0.2, 0.35]}
    with open(RES / "a1071_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：例のリーグ。使われる割合と、3つの数え方の勝率
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    x = ex.usage_pct.values
    ax.axhline(50, color=GRAY, lw=1)
    for i in range(K):
        ax.plot([x[i], x[i]], [ex.true_winrate_pct[i], ex.per_match_pct_formula[i]], color=LIGHT, lw=1, zorder=1)
    ax.scatter(x, ex.true_winrate_pct, color=INK, s=40, label="③ 同キャラ戦を外す（本当の勝率）", zorder=3)
    ax.scatter(x, ex.mirror_in_pct_formula, color=BLUE, s=40, marker="s", label="① 同キャラ戦を両側1勝1敗で入れる", zorder=3)
    ax.scatter(x, ex.per_match_pct_formula, color=ORANGE, s=40, marker="^", label="② 試合単位（同キャラ戦は必ず勝ち）", zorder=3)
    for i in [0, 1, 2]:
        ax.text(x[i] + 0.4, ex.true_winrate_pct[i], NAMES[i], fontsize=9, color=INK, va="center")
    ax.set_xlabel("使われる割合（%）"); ax.set_ylabel("勝率（%、式の値）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("例のリーグ：よく使われるキャラクターほど、①は50%へ、②は上へずれる")
    save(fig, "a1071_example.png", SRC)

    # 図2：1位が本当の1位でなかったリーグの割合（棒、0始まり）
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    labs = ["③ 同キャラ戦を外す\n（1週間3万試合）", "① 両側1勝1敗\n（式の値）", "① 両側1勝1敗\n（1週間3万試合）",
            "② 試合単位\n（式の値）", "② 試合単位\n（1週間3万試合）"]
    vals = [summ["wk_true"]["top_miss_pct"], summ["f_mirror_in"]["top_miss_pct"], summ["wk_mirror_in"]["top_miss_pct"],
            summ["f_per_match"]["top_miss_pct"], summ["wk_per_match"]["top_miss_pct"]]
    cols = [INK, LIGHT, BLUE, "#f5b89c", ORANGE]
    ax.bar(range(5), vals, color=cols, width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.8, f"{v:.2f}%", ha="center", fontsize=9)
    ax.set_xticks(range(5)); ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylabel("勝率の1位が本当の1位でなかった割合（%）"); ax.set_ylim(0, max(vals) * 1.2)
    ax.set_title(f"{N_LEAGUE:,}リーグ：1位を取り違えた割合（数え方だけのずれと、試合数の振れ）")
    save(fig, "a1071_topmiss.png", SRC, y=-0.07)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    xs = np.arange(len(grid))
    ax.bar(xs - 0.2, grid.f_mirror_in_top_miss_pct, 0.4, color=BLUE, label="① 両側1勝1敗")
    ax.bar(xs + 0.2, grid.f_per_match_top_miss_pct, 0.4, color=ORANGE, label="② 試合単位")
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{r.top_usage_pct:.0f}/{r.strength_sd}/{r.rho}" for r in grid.itertuples()], rotation=90, fontsize=7)
    ax.set_xlabel("いちばん使われるキャラクターの割合（%、整数に丸め）/ 強さの差（標準偏差）/ 人気と強さの相関")
    ax.set_ylabel("1位を取り違えた割合（%、式の値）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("置き方を変えた27通り（各500リーグ）：使われ方が偏るほど取り違える（②は強さの差が小さいほど）")
    save(fig, "a1071_grid.png", SRC, y=-0.2)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
