"""1243 付ける件数を付け手に均等に配るか、早い人に多く配るかで、全体のまちがいはどう変わるのか？（架空のデータ）

架空の問い合わせ文10,000件を、架空の付け手10人で分類する。付け手ごとに「速さ（1時間に付ける件数）」と
「まちがいやすさ（1件をまちがえる確率）」を作成者が置き、2つのあいだの関係（速い人ほどまちがいやすいか）も置く。
①全員に同じ件数を配る、②速さに比例して配る（全員が同じ時刻に終わる）の2つで、全体のまちがいの数・終わるまでの時間・
付け手ごとのまちがい率の平均（件数で重みを付けない）を比べる。
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1243
SRC = "架空の問い合わせ文と付け手（作成者が乱数で作成、seed 1243）"
N = 10000
J = 10
SPEED_MED = 120.0     # 1時間に付ける件数の中央値
SPEED_SD = 0.4        # 速さの対数の散らばり
ERR_MED = 0.05        # 1件をまちがえる確率の中央値
ERR_SD = 0.6          # まちがいやすさの散らばり（ロジットの物差し）
RHO = 0.5             # 速さとまちがいやすさの関係（正：速い人ほどまちがいやすい）
TEAMS = 2000


def logit(p):
    return math.log(p / (1 - p))


def make_teams(rng, teams, j, rho, speed_sd):
    zs = rng.normal(0, 1, (teams, j))
    ze = rng.normal(0, 1, (teams, j))
    speed = SPEED_MED * np.exp(speed_sd * zs)
    err = 1 / (1 + np.exp(-(logit(ERR_MED) + ERR_SD * (rho * zs + math.sqrt(1 - rho ** 2) * ze))))
    return speed, err


def allocate(speed, n=N):
    """①均等、②速さに比例（端数は大きい順に配って合計を n にそろえる）"""
    teams, j = speed.shape
    eq = np.full((teams, j), n // j)
    eq[:, : n - (n // j) * j] += 1
    raw = speed / speed.sum(1, keepdims=True) * n
    pr = np.floor(raw).astype(int)
    rest = n - pr.sum(1)
    order = np.argsort(-(raw - pr), axis=1)
    for t in range(teams):
        pr[t, order[t, :rest[t]]] += 1
    return eq, pr


def run(rng, teams, j, rho, speed_sd, n=N):
    speed, err = make_teams(rng, teams, j, rho, speed_sd)
    eq, pr = allocate(speed, n)
    e_eq = rng.binomial(eq, err)
    e_pr = rng.binomial(pr, err)
    t_eq = (eq / speed).max(1)
    t_pr = (pr / speed).max(1)
    unweighted = err.mean(1)                               # 付け手ごとのまちがい率の平均（件数の重みなし）
    fastest = speed.argmax(1)
    idx = np.arange(teams)
    return {"speed": speed, "err": err, "eq": eq, "pr": pr, "e_eq": e_eq, "e_pr": e_pr,
            "errors_eq": e_eq.sum(1), "errors_pr": e_pr.sum(1), "time_eq": t_eq, "time_pr": t_pr,
            "unweighted": unweighted,
            "exp_eq": (eq * err).sum(1), "exp_pr": (pr * err).sum(1),
            "fastest_items_share_pr": pr[idx, fastest] / n,
            "fastest_err_share_pr": e_pr[idx, fastest] / np.maximum(e_pr.sum(1), 1),
            "fastest_err_share_eq": e_eq[idx, fastest] / np.maximum(e_eq.sum(1), 1),
            "speed_err_corr": np.array([np.corrcoef(np.log(speed[t]), err[t])[0, 1] for t in range(teams)])}


def r(x, k=4):
    return round(float(x), k) + 0.0


def summary(o, n=N):
    return {"errors_equal": r(o["errors_eq"].mean(), 2), "errors_fast": r(o["errors_pr"].mean(), 2),
            "error_rate_equal_pct": r(o["errors_eq"].mean() / n * 100, 3),
            "error_rate_fast_pct": r(o["errors_pr"].mean() / n * 100, 3),
            "fast_over_equal_errors": r(o["errors_pr"].mean() / o["errors_eq"].mean()),
            "expected_fast_over_equal": r(o["exp_pr"].mean() / o["exp_eq"].mean()),
            "share_teams_fast_more_errors": r((o["errors_pr"] > o["errors_eq"]).mean()),
            "time_equal_h": r(o["time_eq"].mean(), 3), "time_fast_h": r(o["time_pr"].mean(), 3),
            "fast_over_equal_time": r(o["time_pr"].mean() / o["time_eq"].mean()),
            "unweighted_mean_err_pct": r(o["unweighted"].mean() * 100, 3),
            "fastest_items_share_fast_pct": r(o["fastest_items_share_pr"].mean() * 100, 2),
            "fastest_items_share_equal_pct": r(o["eq"][0, 0] / n * 100, 2),
            "fastest_err_share_fast_pct": r(o["fastest_err_share_pr"].mean() * 100, 2),
            "fastest_err_share_equal_pct": r(o["fastest_err_share_eq"].mean() * 100, 2),
            "unweighted_vs_fast_actual_pct_points": r((o["errors_pr"].mean() / n - o["unweighted"].mean()) * 100, 3)}


def main():
    rng = np.random.default_rng(SEED)
    base_runs = {}
    rows = []
    for rho in [-0.5, 0.0, 0.5]:
        o = run(np.random.default_rng(SEED * 10 + int((rho + 1) * 10)), TEAMS, J, rho, SPEED_SD)
        base_runs[rho] = o
        rows.append({"rho": rho, **summary(o)})
    base_df = pd.DataFrame(rows)
    base_df.to_csv(RES / "base_rho.csv", index=False)
    b = base_runs[RHO]

    # 1チームの例
    t0 = 0
    ex = pd.DataFrame({"rater": [f"付け手{i + 1}" for i in range(J)],
                       "speed_per_h": np.round(b["speed"][t0], 2), "error_prob": np.round(b["err"][t0], 4),
                       "items_equal": b["eq"][t0], "items_fast": b["pr"][t0],
                       "errors_equal": b["e_eq"][t0], "errors_fast": b["e_pr"][t0]}).sort_values("speed_per_h", ascending=False)
    ex.to_csv(DATA / "example_team.csv", index=False)
    pd.DataFrame({"team": np.arange(1, TEAMS + 1), "errors_equal": b["errors_eq"], "errors_fast": b["errors_pr"],
                  "time_equal_h": np.round(b["time_eq"], 3), "time_fast_h": np.round(b["time_pr"], 3),
                  "unweighted_err": np.round(b["unweighted"], 5)}).to_csv(DATA / "teams_base.csv", index=False)

    # 確かめ：速さとまちがいやすさの関係 × 速さの散らばり × 人数（27通り）
    grid = []
    gi = 0
    for rho in [-0.5, 0.0, 0.5]:
        for sd in [0.2, 0.4, 0.8]:
            for j in [5, 10, 20]:
                gi += 1
                o = run(np.random.default_rng(SEED * 1000 + gi), 1000, j, rho, sd)
                s = summary(o)
                grid.append({"rho": rho, "speed_sd": sd, "raters": j,
                             **{k: s[k] for k in ["fast_over_equal_errors", "expected_fast_over_equal",
                                                  "share_teams_fast_more_errors", "fast_over_equal_time",
                                                  "error_rate_equal_pct", "error_rate_fast_pct",
                                                  "unweighted_mean_err_pct", "fastest_err_share_fast_pct"]}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    def rng_of(col, sub):
        return [r(sub[col].min()), r(sub[col].max())]

    out = {"setting": {"N": N, "raters": J, "speed_median_per_h": SPEED_MED, "speed_log_sd": SPEED_SD,
                       "err_median": ERR_MED, "err_logit_sd": ERR_SD, "rho": RHO, "teams": TEAMS},
           "base": summary(b),
           "base_mean_realized_corr": r(b["speed_err_corr"].mean(), 3),
           "by_rho": base_df.to_dict("records"),
           "example_team": {"errors_equal": int(b["errors_eq"][t0]), "errors_fast": int(b["errors_pr"][t0]),
                            "time_equal_h": r(b["time_eq"][t0], 3), "time_fast_h": r(b["time_pr"][t0], 3)},
           "grid_summary": {
               str(rho): {"fast_over_equal_errors_range": rng_of("fast_over_equal_errors", grid[grid.rho == rho]),
                          "share_teams_fast_more_errors_range": rng_of("share_teams_fast_more_errors", grid[grid.rho == rho]),
                          "fast_over_equal_time_range": rng_of("fast_over_equal_time", grid[grid.rho == rho])}
               for rho in [-0.5, 0.0, 0.5]},
           "grid_max_rel_diff_sim_vs_expected": r((grid.fast_over_equal_errors / grid.expected_fast_over_equal - 1).abs().max())}
    json.dump(out, open(RES / "a1243_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：関係ごとの全体のまちがい（基本、2,000チームの平均）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    yy = np.arange(3)
    h = 0.38
    labels = {-0.5: "速い人ほどまちがえにくい", 0.0: "速さとまちがいは関係なし", 0.5: "速い人ほどまちがえやすい（基本）"}
    for i, row in base_df.iterrows():
        ax.barh(i - h / 2, row.errors_equal, h, color=BLUE, label="①全員に同じ件数" if i == 0 else None)
        ax.barh(i + h / 2, row.errors_fast, h, color=ORANGE, label="②速さに比例して配る" if i == 0 else None)
        ax.text(row.errors_equal + 6, i - h / 2, f"{row.errors_equal:.2f}件", va="center", fontsize=9)
        ax.text(row.errors_fast + 6, i + h / 2, f"{row.errors_fast:.2f}件（{row.fast_over_equal_errors:.4f}倍）",
                va="center", fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels([labels[x] for x in base_df.rho], fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, base_df[["errors_equal", "errors_fast"]].values.max() * 1.8)
    ax.set_xlabel("10,000件のうちまちがえた件数（10人、2,000チームの平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1.0, 1.0))
    ax.set_title("速い人に多く配ると、まちがいは速さとの関係しだいで増えも減りもする")
    save(fig, "a1243_errors.png", SRC)

    # 図2：時間とまちがいの数（基本の関係、チームごと）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    k = 400
    ax.scatter(b["time_eq"][:k], b["errors_eq"][:k], s=10, color=BLUE, alpha=.6, label="①全員に同じ件数")
    ax.scatter(b["time_pr"][:k], b["errors_pr"][:k], s=10, color=ORANGE, alpha=.6, label="②速さに比例して配る")
    ax.set_xlim(0, None); ax.set_ylim(0, None)
    ax.set_xlabel("全部付け終わるまでの時間（時間）")
    ax.set_ylabel("まちがえた件数（10,000件のうち）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title(f"速い人ほどまちがえやすいと、②は早く終わるが平均{summary(b)['fast_over_equal_errors']:.4f}倍まちがえる",
                 fontsize=11.5)
    ax.text(0.99, 0.99, "最初の400チーム", transform=ax.transAxes, fontsize=8.5, color=GRAY, va="top", ha="right")
    save(fig, "a1243_time_errors.png", SRC)

    # 図3：27通りの まちがいの比（②÷①）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    combos = [(sd, j) for sd in [0.2, 0.4, 0.8] for j in [5, 10, 20]]
    xx = np.arange(len(combos))
    for rho, c, mk in [(0.5, ORANGE, "o"), (0.0, GRAY, "s"), (-0.5, BLUE, "D")]:
        v = [grid[(grid.rho == rho) & (grid.speed_sd == sd) & (grid.raters == j)].fast_over_equal_errors.iloc[0]
             for sd, j in combos]
        ax.plot(xx, v, marker=mk, lw=0, ms=7, color=c, label=labels[rho].replace("（基本）", ""))
    ax.axhline(1, color=INK, lw=1, ls="--")
    ax.set_xticks(xx); ax.set_xticklabels([f"{sd}\n{j}人" for sd, j in combos], fontsize=9)
    ax.set_ylim(0.5, 1.6)
    ax.set_ylabel("まちがいの数の比（②÷①）")
    ax.set_xlabel("速さの散らばり（対数）と人数（各1,000チーム）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("関係があるときは、速さの散らばりが大きいほど比が1から離れる")
    save(fig, "a1243_grid.png", SRC)

    print(json.dumps({k: out[k] for k in ["base", "base_mean_realized_corr", "example_team", "grid_summary",
                                          "grid_max_rel_diff_sim_vs_expected"]}, ensure_ascii=False, indent=1))
    pd.set_option("display.width", 250)
    print(base_df.to_string()); print(grid.to_string()); print(ex.to_string())


if __name__ == "__main__":
    main()
