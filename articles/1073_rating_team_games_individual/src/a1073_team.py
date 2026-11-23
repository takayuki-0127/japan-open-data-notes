"""1073 チーム戦の勝ち負けから、1人ひとりの強さはどこまで分かるのか？（架空のデータ）

架空の対戦ゲームのリーグ（100人）。1人ひとりの本当の強さを作成者が置き、チームの強さは
メンバーの強さの合計、勝つ確率は2チームの強さの差のロジスティック関数と置く。
試合ごとにメンバーをでたらめに組むときと、いつも同じ顔ぶれで組むときに、
  ① 1人ひとりの勝率
  ② チームの強さを合計と置いた回帰（ロジスティック回帰、弱い縮め付き）
で強さを見積もり、本当の強さとの順位の相関・上位10人の当たりを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1073
SRC = "架空の対戦ゲームのチーム戦リーグ（作成者が乱数で作成、seed 1073）"
N_PLAYER = 100
SD = 0.3            # 1人の強さの標準偏差（ロジット、チームの強さは合計）
G_LIST = [10, 25, 50, 100, 200, 400, 800]
SIZES = [1, 3, 5]
REP = 20
LAM = 1.0           # 回帰の縮め（強さ0への弱い引き寄せ）


def rank(x):
    return pd.Series(x).rank().values


def spearman(x, y):
    return float(np.corrcoef(rank(x), rank(y))[0, 1])


def make_games(rng, n, k, G, fixed_share=0.0, teams=None):
    """試合の表：X は（試合×人）で A側+1・B側−1"""
    n_games = int(round(n * G / (2 * k)))
    X = np.zeros((n_games, n), dtype=np.int8)
    for g in range(n_games):
        if teams is not None and rng.random() < fixed_share:
            t = rng.choice(len(teams), 2, replace=False)
            X[g, teams[t[0]]] = 1; X[g, teams[t[1]]] = -1
        else:
            m = rng.choice(n, 2 * k, replace=False)
            X[g, m[:k]] = 1; X[g, m[k:]] = -1
    return X


def play(rng, X, skill, scale=1.0):
    p = 1 / (1 + np.exp(-(X @ skill) * scale))
    return (rng.random(len(p)) < p).astype(float)


def winrate(X, y):
    win = ((X == 1) * y[:, None] + (X == -1) * (1 - y)[:, None]).sum(0)
    played = (X != 0).sum(0)
    return np.where(played > 0, win / np.maximum(played, 1), 0.5)


def fit(X, y, lam=LAM, it=12, scale=1.0):
    Xf = X.astype(float) * scale; b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-(Xf @ b)))
        g = Xf.T @ (y - p) - lam * b
        H = (Xf * (p * (1 - p))[:, None]).T @ Xf + lam * np.eye(X.shape[1])
        step = np.linalg.solve(H, g); b += step
        if np.abs(step).max() < 1e-6:
            break
    return b


def scores(skill, est):
    top_true = set(np.argsort(-skill)[:10]); top_est = set(np.argsort(-est)[:10])
    return spearman(skill, est), len(top_true & top_est) / 10


def within_team_correct(skill, est, teams):
    """同じチームの2人の組で、強いほうを強いと見積もった割合（同点は半分）"""
    ok = []
    for t in teams:
        for a in range(len(t)):
            for b in range(a + 1, len(t)):
                i, j = t[a], t[b]
                d = (skill[i] - skill[j]) * (est[i] - est[j])
                ok.append(0.5 if abs(est[i] - est[j]) < 1e-9 else float(d > 0))
    return float(np.mean(ok))


def r3(x):
    return round(float(x), 3)


def main():
    t0 = time.time()
    res = {"setting": {"players": N_PLAYER, "skill_sd": SD, "games_per_player": G_LIST, "team_sizes": SIZES, "reps": REP, "ridge": LAM}}

    # 1. 人数（1対1・3対3・5対5）×1人あたりの試合数×チームの強さの置き方（合計・平均）
    rows = []
    for model in ["sum", "mean"]:
        for k in SIZES:
            if model == "mean" and k == 1:
                continue   # 1対1では合計と平均は同じ
            sc = 1.0 if model == "sum" else 1.0 / k
            for G in G_LIST:
                for r in range(REP):
                    rng = np.random.default_rng(SEED * 10000 + (model == "mean") * 5000 + k * 1000 + G * 3 + r)
                    skill = rng.normal(0, SD, N_PLAYER)
                    X = make_games(rng, N_PLAYER, k, G); y = play(rng, X, skill, sc)
                    s1, t1 = scores(skill, winrate(X, y)); s2, t2 = scores(skill, fit(X, y, scale=sc))
                    rows.append({"model": model, "team_size": k, "games_per_player": G, "rep": r, "winrate_spearman": s1, "winrate_top10": t1,
                                 "reg_spearman": s2, "reg_top10": t2})
    a = pd.DataFrame(rows)
    one = a[(a.model == "sum") & (a.team_size == 1)].copy(); one["model"] = "mean"
    a = pd.concat([a, one], ignore_index=True)
    allsz = a.groupby(["model", "team_size", "games_per_player"]).mean(numeric_only=True).drop(columns="rep").reset_index()
    allsz["winrate_top10"] *= 100; allsz["reg_top10"] *= 100
    allsz = allsz.round(3)
    allsz.to_csv(RES / "by_size_games.csv", index=False)
    szm = allsz[allsz.model == "mean"]
    res["by_size_games_mean_model"] = {f"{int(r.team_size)}v{int(r.team_size)}_G{int(r.games_per_player)}":
                                       {"winrate_spearman": r.winrate_spearman, "reg_spearman": r.reg_spearman,
                                        "reg_top10_pct": round(r.reg_top10, 1)} for r in szm.itertuples()}
    sz = allsz[allsz.model == "sum"].drop(columns="model").copy()
    res["by_size_games"] = {f"{int(r.team_size)}v{int(r.team_size)}_G{int(r.games_per_player)}":
                            {"winrate_spearman": r.winrate_spearman, "reg_spearman": r.reg_spearman,
                             "winrate_top10_pct": round(r.winrate_top10, 1), "reg_top10_pct": round(r.reg_top10, 1)} for r in sz.itertuples()}

    def need(df, col, thr):
        d = df[df[col] >= thr]
        return None if d.empty else int(d.games_per_player.min())
    res["games_needed_reg_spearman_0.8"] = {f"{k}v{k}": need(sz[sz.team_size == k], "reg_spearman", 0.8) for k in SIZES}
    res["games_needed_reg_top10_50pct"] = {f"{k}v{k}": need(sz[sz.team_size == k], "reg_top10", 50) for k in SIZES}
    res["mean_model_games_needed_reg_spearman_0.8"] = {f"{k}v{k}": need(szm[szm.team_size == k], "reg_spearman", 0.8) for k in SIZES}

    # 2. いつも同じ顔ぶれで組む割合（5対5、1人100試合）
    fx = []
    teams = [list(range(i, i + 5)) for i in range(0, N_PLAYER, 5)]
    for fs in [0.0, 0.5, 0.8, 0.95, 1.0]:
        for r in range(REP):
            rng = np.random.default_rng(SEED * 20000 + int(fs * 100) * 100 + r)
            skill = rng.normal(0, SD, N_PLAYER)
            X = make_games(rng, N_PLAYER, 5, 100, fixed_share=fs, teams=teams); y = play(rng, X, skill)
            wr, rg = winrate(X, y), fit(X, y)
            s1, t1 = scores(skill, wr); s2, t2 = scores(skill, rg)
            fx.append({"fixed_share": fs, "rep": r, "winrate_spearman": s1, "reg_spearman": s2, "winrate_top10": t1 * 100, "reg_top10": t2 * 100,
                       "winrate_within_team_correct": within_team_correct(skill, wr, teams) * 100,
                       "reg_within_team_correct": within_team_correct(skill, rg, teams) * 100})
    fx = pd.DataFrame(fx).groupby("fixed_share").mean(numeric_only=True).drop(columns="rep").reset_index().round(3)
    fx.to_csv(RES / "fixed_teams.csv", index=False)
    res["fixed_teams_5v5_G100"] = fx.set_index("fixed_share").to_dict(orient="index")

    # 3. 確かめ：強さの差×人数（9通り、5対5）
    grid = []; j = 0
    for sd in [0.15, 0.3, 0.5]:
        for n in [50, 100, 200]:
            for G in [25, 50, 100, 200, 400]:
                ss = []
                for r in range(10):
                    rng = np.random.default_rng(SEED * 50000 + j * 100 + r)
                    skill = rng.normal(0, sd, n)
                    X = make_games(rng, n, 5, G); y = play(rng, X, skill)
                    s1, _ = scores(skill, winrate(X, y)); s2, _ = scores(skill, fit(X, y))
                    ss.append((s1, s2))
                j += 1
                m = np.mean(ss, 0)
                grid.append({"skill_sd": sd, "players": n, "games_per_player": G, "winrate_spearman": r3(m[0]), "reg_spearman": r3(m[1])})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    g100 = grid[grid.games_per_player == 100]
    res["grid_5v5"] = {"n_cases": 9,
                       "reg_spearman_G100_range": [float(g100.reg_spearman.min()), float(g100.reg_spearman.max())],
                       "winrate_spearman_G100_range": [float(g100.winrate_spearman.min()), float(g100.winrate_spearman.max())],
                       "games_needed_reg_spearman_0.8": {f"sd{sd}_n{n}": need(grid[(grid.skill_sd == sd) & (grid.players == n)], "reg_spearman", 0.8)
                                                         for sd in [0.15, 0.3, 0.5] for n in [50, 100, 200]},
                       "reg_minus_winrate_G100_range": [r3((g100.reg_spearman - g100.winrate_spearman).min()), r3((g100.reg_spearman - g100.winrate_spearman).max())]}

    # 例の1リーグ（5対5、1人50試合）のデータ
    rng = np.random.default_rng(SEED)
    skill = rng.normal(0, SD, N_PLAYER)
    X = make_games(rng, N_PLAYER, 5, 50); y = play(rng, X, skill)
    wr, rg = winrate(X, y), fit(X, y)
    pd.DataFrame({"game": np.arange(1, len(y) + 1),
                  "team_a": [" ".join(str(i + 1) for i in np.where(x == 1)[0]) for x in X],
                  "team_b": [" ".join(str(i + 1) for i in np.where(x == -1)[0]) for x in X],
                  "team_a_won": y.astype(int)}).to_csv(DATA / "games_example_5v5.csv", index=False)
    pl = pd.DataFrame({"player": np.arange(1, N_PLAYER + 1), "true_skill": np.round(skill, 4), "games": (X != 0).sum(0),
                       "winrate_pct": np.round(wr * 100, 2), "reg_estimate": np.round(rg, 4)})
    pl.to_csv(DATA / "players_example_5v5.csv", index=False)
    s1, t1 = scores(skill, wr); s2, t2 = scores(skill, rg)
    res["example_5v5_G50"] = {"games": int(len(y)), "winrate_spearman": r3(s1), "reg_spearman": r3(s2), "winrate_top10_pct": t1 * 100, "reg_top10_pct": t2 * 100,
                              "true_top_player_winrate_rank": int(pd.Series(-wr).rank(method="min").values[int(np.argmax(skill))])}
    with open(RES / "a1073_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：1人あたりの試合数と順位の相関（回帰）
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.4), sharey=True)
    for ax, model, ttl in [(axes[0], "sum", "チームの強さ＝メンバーの強さの合計"), (axes[1], "mean", "チームの強さ＝メンバーの強さの平均")]:
        for k, c, mk in [(1, INK, "o"), (3, BLUE, "s"), (5, ORANGE, "^")]:
            d = allsz[(allsz.model == model) & (allsz.team_size == k)]
            ax.plot(d.games_per_player, d.reg_spearman, color=c, marker=mk, label=f"{k}対{k}")
        ax.set_xscale("log"); ax.set_xticks(G_LIST); ax.set_xticklabels([str(g) for g in G_LIST])
        ax.set_ylim(0, 1); ax.axhline(0.8, color=GRAY, ls="--", lw=1)
        ax.set_xlabel("1人あたりの試合数"); ax.set_title(ttl, fontsize=11)
    axes[0].set_ylabel("本当の強さと回帰の見積もりの順位の相関")
    axes[1].legend(frameon=False, fontsize=9, loc="lower right")
    fig.suptitle(f"同じ試合数で分かる度合いは、チームの強さの置き方で大きく変わる（{N_PLAYER}人、各{REP}回の平均）", fontsize=12)
    save(fig, "a1073_games.png", SRC)

    # 図2：上位10人の当たり（5対5、棒、0始まり）
    d = sz[sz.team_size == 5]
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    x = np.arange(len(d)); w = 0.38
    ax.bar(x - w / 2, d.winrate_top10, w, color=LIGHT, label="① 1人ひとりの勝率")
    ax.bar(x + w / 2, d.reg_top10, w, color=ORANGE, label="② チームの合計と置いた回帰")
    for xi, v1, v2 in zip(x, d.winrate_top10, d.reg_top10):
        ax.text(xi - w / 2, v1 + 1, f"{v1:.1f}", ha="center", fontsize=8.5); ax.text(xi + w / 2, v2 + 1, f"{v2:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{g}試合" for g in d.games_per_player])
    ax.set_ylim(0, 100); ax.set_ylabel("本当の上位10人に入っていた割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("5対5：上位10人の当たり（でたらめな組み方、1人あたりの試合数ごと）")
    save(fig, "a1073_top10.png", SRC)

    # 図3：同じ顔ぶれで組む割合
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    xx = np.arange(len(fx)); w = 0.38
    ax.bar(xx - w / 2, fx.winrate_within_team_correct, w, color=LIGHT, label="① 1人ひとりの勝率")
    ax.bar(xx + w / 2, fx.reg_within_team_correct, w, color=ORANGE, label="② 回帰")
    for xi, v1, v2 in zip(xx, fx.winrate_within_team_correct, fx.reg_within_team_correct):
        ax.text(xi - w / 2, v1 + 1, f"{v1:.1f}", ha="center", fontsize=8.5); ax.text(xi + w / 2, v2 + 1, f"{v2:.1f}", ha="center", fontsize=8.5)
    ax.axhline(50, color=GRAY, ls="--", lw=1, label="でたらめに当てた場合（50%）")
    ax.set_xticks(xx); ax.set_xticklabels([f"{int(f * 100)}%" for f in fx.fixed_share])
    ax.set_xlabel("いつも同じ5人で組んで出た試合の割合")
    ax.set_ylim(0, 110); ax.set_ylabel("同じチームの2人のうち強いほうを当てた割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=3)
    ax.set_title("いつも同じ顔ぶれだと、チームの中の強さの順は分からない（5対5、1人100試合）")
    save(fig, "a1073_fixed.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
