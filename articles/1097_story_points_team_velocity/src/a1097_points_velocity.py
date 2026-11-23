"""1097 ストーリーポイントで数えた「速さ」は、チームどうしで比べられるのか？（架空のデータ）

架空のアプリの開発チーム8つ（A〜H、記号だけ）。チームごとに、2週間の区切りで終える本当の作業量と、
「1ポイント」がどれだけの作業量にあたるか（ポイントの物差し）を作成者が置く。
作業1件の本当の大きさを乱数で作り、チームは自分の物差しと見積もりのぶれでポイントを付け、
1・2・3・5・8・13・21 の目盛りに丸める。区切りごとの「速さ」（終えた作業のポイントの合計）で、
 ① チームどうしの本当の作業量の順が当たるか
 ② 終えた件数で比べるとどうか
 ③ 全チームが同じ見本の作業10件にポイントを付け、その合計の比で物差しをそろえるとどうか
 ④ 同じチームの前半と後半を比べて、本当に増えたチームを当てられるか（速さを目標にした後、ポイントが少しずつ大きく付く場合も）
を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1097
SRC = "架空のアプリの開発チームの作業とポイント（作成者が置いた作業量・ポイントの物差しからの乱数、seed 1097）"
TEAMS = list("ABCDEFGH")
N_PERIODS = 20
SCALE = np.array([1, 2, 3, 5, 8, 13, 21])
BASE = {"work_mean": 100.0, "cv_work": 0.25, "period_noise": 0.10, "task_median": 4.0, "task_sigma": 0.7,
        "sigma_scale": 0.5, "sigma_est": 0.35, "sigma_slicing": 0.3, "n_ref": 10}
REPS = 1000
GRID_SIGMA_SCALE = [0.0, 0.25, 0.5, 0.8]
GRID_CV_WORK = [0.1, 0.25, 0.5]
GRID_REPS = 300
# 後半（11〜20回目）：半分のチームは本当の作業量を+10%。速さを目標にすると、ポイントは1回ごとに最大 d だけ大きく付く
UP = 0.10
DRIFT_GRID = [0.0, 0.01, 0.02, 0.04]
JUDGE = 1.05      # 後半÷前半が1.05以上なら「増えた」と読む
WITHIN_REPS = 1000


def r(x, d=4):
    return round(float(x), d)


def snap(x):
    """対数の上でいちばん近い目盛りに丸める"""
    lx = np.log(np.maximum(x, 1e-9))[..., None]
    return SCALE[np.abs(lx - np.log(SCALE)).argmin(-1)]


def spearman(x, y):
    return float(pd.Series(x).rank().corr(pd.Series(y).rank()))


def team_run(rng, work, scale, slicing, drift=0.0, up=0.0, n_periods=N_PERIODS, est=BASE["sigma_est"]):
    """1チームの区切りごとの本当の作業量・ポイント・件数。work は区切りの本当の作業量の平均。
    slicing は作業の切り方（1件の大きさの倍率）。後半は作業量を (1+up) 倍、ポイントは (1+drift)^(回−10) 倍で付く"""
    mult = np.ones(n_periods); mult[10:] = 1 + up
    target = work * mult * np.exp(rng.normal(0, BASE["period_noise"], n_periods))
    infl = np.ones(n_periods); infl[10:] = (1 + drift) ** np.arange(1, n_periods - 9)
    pts, cnt, done = np.zeros(n_periods), np.zeros(n_periods, int), np.zeros(n_periods)
    need = int(target.sum() / (BASE["task_median"] * slicing) * 1.2) + 50
    size = BASE["task_median"] * slicing * np.exp(rng.normal(0, BASE["task_sigma"], need))
    noise = np.exp(rng.normal(0, est, need))
    cs = np.cumsum(size)
    edges = np.searchsorted(cs, np.cumsum(target))
    start = 0
    for t in range(n_periods):
        end = min(edges[t] + 1, need)
        sl = slice(start, end)
        p = snap(size[sl] * scale * infl[t] * noise[sl] / BASE["task_median"] * 2)   # 物差し1なら中くらいの作業が2ポイント前後
        pts[t], cnt[t], done[t] = p.sum(), end - start, size[sl].sum()
        start = end
    return pts, cnt, done


def make_teams(rng, sigma_scale=BASE["sigma_scale"], cv_work=BASE["cv_work"]):
    k = 1 / cv_work ** 2
    work = rng.gamma(k, BASE["work_mean"] / k, len(TEAMS))
    scale = np.exp(rng.normal(0, sigma_scale, len(TEAMS))) if sigma_scale > 0 else np.ones(len(TEAMS))
    slicing = np.exp(rng.normal(0, BASE["sigma_slicing"], len(TEAMS)))
    return work, scale, slicing


def reference_factor(rng, scale):
    """全チームが同じ見本の作業10件にポイントを付ける。各チームの合計 ÷ 全チームの平均 を物差しの比とする"""
    ref = BASE["task_median"] * np.exp(rng.normal(0, BASE["task_sigma"], BASE["n_ref"]))
    tot = np.array([snap(ref * s * np.exp(rng.normal(0, BASE["sigma_est"], len(ref))) / BASE["task_median"] * 2).sum()
                    for s in scale])
    return tot / tot.mean(), ref


def cross_team_once(rng, sigma_scale=BASE["sigma_scale"], cv_work=BASE["cv_work"], keep=False):
    work, scale, slicing = make_teams(rng, sigma_scale, cv_work)
    runs = [team_run(rng, w, s, sl, n_periods=10) for w, s, sl in zip(work, scale, slicing)]
    vel = np.array([x[0].mean() for x in runs])
    cnt = np.array([x[1].mean() for x in runs])
    true = np.array([x[2].mean() for x in runs])        # 本当に終えた作業量（10回の平均）
    fac, ref = reference_factor(rng, scale)
    cal = vel / fac
    res = {}
    for name, v in [("points", vel), ("task_count", cnt), ("points_calibrated", cal)]:
        res[f"rho_{name}"] = spearman(v, true)
        res[f"top1_{name}"] = float(np.argmax(v) == np.argmax(true))
    res["rho_points_scale"] = spearman(vel, scale)
    res["max_min_ratio_points_per_true"] = float((vel / true).max() / (vel / true).min())
    if keep:
        return res, {"work": work, "scale": scale, "slicing": slicing, "vel": vel, "cnt": cnt, "true": true,
                     "fac": fac, "cal": cal, "runs": runs, "ref": ref}
    return res


def within_once(rng, drift_max):
    work, scale, slicing = make_teams(rng)
    up_team = np.zeros(len(TEAMS), bool); up_team[rng.permutation(len(TEAMS))[:4]] = True
    drift = rng.uniform(0, drift_max, len(TEAMS)) if drift_max > 0 else np.zeros(len(TEAMS))
    out = []
    for i in range(len(TEAMS)):
        p, c, d = team_run(rng, work[i], scale[i], slicing[i], drift=drift[i], up=UP if up_team[i] else 0.0)
        out.append({"up": up_team[i], "ratio_points": p[10:].mean() / p[:10].mean(),
                    "ratio_true": d[10:].mean() / d[:10].mean(), "drift": drift[i]})
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 1) チームどうしの比べ（基本の置き方、1,000回）
    rows = []
    keep = None
    for rep in range(REPS):
        if rep == 0:
            res, keep = cross_team_once(rng, keep=True)
        else:
            res = cross_team_once(rng)
        rows.append(res)
    ct = pd.DataFrame(rows)
    cross = {}
    for name in ["points", "task_count", "points_calibrated"]:
        cross[name] = {"rank_corr_mean": r(ct[f"rho_{name}"].mean()), "rank_corr_p10": r(ct[f"rho_{name}"].quantile(0.1)),
                       "rank_corr_p90": r(ct[f"rho_{name}"].quantile(0.9)), "top1_hit": r(ct[f"top1_{name}"].mean())}
    cross_df = pd.DataFrame(cross).T
    cross_df.to_csv(RES / "cross_team.csv")
    extra = {"rank_corr_points_vs_scale_mean": r(ct.rho_points_scale.mean()),
             "max_min_ratio_points_per_true_median": r(ct.max_min_ratio_points_per_true.median()),
             "max_min_ratio_points_per_true_p10": r(ct.max_min_ratio_points_per_true.quantile(0.1)),
             "max_min_ratio_points_per_true_p90": r(ct.max_min_ratio_points_per_true.quantile(0.9)),
             "top1_random": r(1 / len(TEAMS))}

    # 2) 確かめ：物差しの散らばり × チームどうしの作業量の差（12通り、各300回）
    grid = []
    for ss in GRID_SIGMA_SCALE:
        for cv in GRID_CV_WORK:
            g = np.random.default_rng(SEED * 1000 + GRID_SIGMA_SCALE.index(ss) * 10 + GRID_CV_WORK.index(cv))
            d = pd.DataFrame([cross_team_once(g, ss, cv) for _ in range(GRID_REPS)])
            grid.append({"sigma_scale": ss, "cv_work": cv,
                         **{f"rank_corr_{n}": r(d[f"rho_{n}"].mean()) for n in ["points", "task_count", "points_calibrated"]},
                         **{f"top1_{n}": r(d[f"top1_{n}"].mean()) for n in ["points", "task_count", "points_calibrated"]}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # 3) 同じチームの前半と後半（ポイントが少しずつ大きく付く d の最大を4通り、各1,000回）
    wrows = []
    for dm in DRIFT_GRID:
        g = np.random.default_rng(SEED * 10 + DRIFT_GRID.index(dm))
        allt = [x for _ in range(WITHIN_REPS) for x in within_once(g, dm)]
        w = pd.DataFrame(allt)
        judged = w.ratio_points >= JUDGE
        wrows.append({"drift_max_per_period": dm,
                      "share_up_teams_judged_up": r(judged[w.up].mean()),
                      "share_flat_teams_judged_up": r(judged[~w.up].mean()),
                      "share_correct": r((judged == w.up).mean()),
                      "mean_ratio_points_up": r(w.ratio_points[w.up].mean()),
                      "mean_ratio_points_flat": r(w.ratio_points[~w.up].mean()),
                      "mean_ratio_true_up": r(w.ratio_true[w.up].mean()),
                      "mean_ratio_true_flat": r(w.ratio_true[~w.up].mean())})
    within = pd.DataFrame(wrows)
    within.to_csv(RES / "within_team.csv", index=False)

    # data：基本の1回目の8チーム（前半10回）と見本の作業
    rows = []
    for i, tname in enumerate(TEAMS):
        p, c, d = keep["runs"][i]
        for t in range(10):
            rows.append({"team": tname, "period": t + 1, "true_work_done": round(float(d[t]), 3), "points": int(p[t]),
                         "tasks_done": int(c[t])})
    pd.DataFrame(rows).to_csv(DATA / "teams_one_run.csv", index=False)
    teams_one = pd.DataFrame({"team": TEAMS, "true_work_per_period": np.round(keep["true"], 3),
                              "points_per_period": np.round(keep["vel"], 3), "tasks_per_period": np.round(keep["cnt"], 3),
                              "point_scale_set": np.round(keep["scale"], 4), "task_slicing_set": np.round(keep["slicing"], 4),
                              "reference_factor": np.round(keep["fac"], 4),
                              "points_calibrated": np.round(keep["cal"], 3)})
    teams_one.to_csv(RES / "teams_summary_one_run.csv", index=False)

    out = {
        "settings": {**BASE, "teams": TEAMS, "n_periods": N_PERIODS, "point_scale_steps": SCALE.tolist(), "reps": REPS,
                     "grid_sigma_scale": GRID_SIGMA_SCALE, "grid_cv_work": GRID_CV_WORK, "grid_reps": GRID_REPS,
                     "up_second_half": UP, "drift_grid": DRIFT_GRID, "judge_ratio": JUDGE,
                     "within_reps": WITHIN_REPS, "seed": SEED},
        "cross_team_base": cross, "cross_team_extra": extra,
        "teams_one_run": {"rank_corr_points": r(spearman(keep["vel"], keep["true"])),
                          "rank_corr_calibrated": r(spearman(keep["cal"], keep["true"])),
                          "points_top_team": TEAMS[int(np.argmax(keep["vel"]))],
                          "true_top_team": TEAMS[int(np.argmax(keep["true"]))],
                          "true_rank_of_points_top": int(pd.Series(-keep["true"]).rank().iloc[int(np.argmax(keep["vel"]))])},
        "grid_12": grid.to_dict("records"),
        "grid_ranges": {c: [r(grid[c].min()), r(grid[c].max())] for c in grid.columns if c.startswith(("rank_corr", "top1"))},
        "grid_calibrated_above_points": int((grid.rank_corr_points_calibrated > grid.rank_corr_points).sum()),
        "grid_sigma0": grid[grid.sigma_scale == 0].to_dict("records"),
        "within_team": within.to_dict("records"),
    }
    json.dump(out, open(RES / "a1097_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の8チーム。速さ（ポイント）と本当の作業量
    fig, axs = plt.subplots(1, 2, figsize=(11.4, 4.2))
    order = np.argsort(-keep["true"])
    x = np.arange(len(TEAMS))
    axs[0].bar(x, keep["true"][order], color=GRAY, width=0.6)
    axs[0].set_xticks(x); axs[0].set_xticklabels([TEAMS[i] for i in order])
    axs[0].set_ylabel("本当に終えた作業量（作成者の置いた単位）"); axs[0].set_ylim(0, keep["true"].max() * 1.2)
    axs[0].set_title("本当の作業量の順（左から多い順）", fontsize=11)
    axs[1].bar(x, keep["vel"][order], color=ORANGE, width=0.6)
    axs[1].set_xticks(x); axs[1].set_xticklabels([TEAMS[i] for i in order])
    axs[1].set_ylabel("速さ（終えたポイントの合計）"); axs[1].set_ylim(0, keep["vel"].max() * 1.2)
    axs[1].set_title("同じ並びで見た「速さ」", fontsize=11)
    for ax, v in [(axs[0], keep["true"][order]), (axs[1], keep["vel"][order])]:
        for i, y in enumerate(v):
            ax.text(i, y + v.max() * 0.02, f"{y:.0f}", ha="center", fontsize=8.5)
    fig.suptitle(f"基本の置き方の1回分（2週間の区切り10回の平均）：速さの順と本当の作業量の順の相関は{out['teams_one_run']['rank_corr_points']:.2f}",
                 fontsize=12, y=1.02)
    save(fig, "a1097_one_run.png", SRC, y=-0.03)

    # 図2：確かめ（12通り）の順位の相関
    fig, ax = plt.subplots(figsize=(10.0, 4.4))
    xg = np.arange(len(grid))
    ax.axhline(0, color=GRAY, lw=1)
    ax.plot(xg, grid.rank_corr_points, "o", color=ORANGE, label="速さ（ポイント）")
    ax.plot(xg, grid.rank_corr_task_count, "^", color=GREEN, label="終えた件数")
    ax.plot(xg, grid.rank_corr_points_calibrated, "s", color=BLUE, label="見本の作業10件で物差しをそろえた速さ")
    ax.set_xticks(xg)
    ax.set_xticklabels([f"{row.sigma_scale:g}\n{row.cv_work:g}" for row in grid.itertuples()], fontsize=8.5)
    ax.set_xlabel("上：チームごとのポイントの物差しの散らばり　下：チームどうしの本当の作業量の差")
    ax.set_ylabel("本当の作業量の順との順位の相関（各300回の平均）"); ax.set_ylim(-0.1, 1.15)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=3)
    ax.set_title("物差しの散らばりが大きく、作業量の差が小さいほど、速さの順は当たらない", fontsize=11.5)
    save(fig, "a1097_grid.png", SRC, y=-0.08)

    # 図3：同じチームの前半と後半
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    xw = np.arange(len(within)); wdt = 0.38
    ax.bar(xw - wdt / 2, within.share_up_teams_judged_up * 100, wdt, color=BLUE, label="本当に+10%のチームで「増えた」と出た割合")
    ax.bar(xw + wdt / 2, within.share_flat_teams_judged_up * 100, wdt, color=ORANGE, label="本当は変わらないチームで「増えた」と出た割合")
    for i, row in within.iterrows():
        ax.text(i - wdt / 2, row.share_up_teams_judged_up * 100 + 1.5, f"{row.share_up_teams_judged_up*100:.1f}", ha="center", fontsize=8)
        ax.text(i + wdt / 2, row.share_flat_teams_judged_up * 100 + 1.5, f"{row.share_flat_teams_judged_up*100:.1f}", ha="center", fontsize=8)
    ax.set_xticks(xw); ax.set_xticklabels([f"最大{d*100:g}%" for d in within.drift_max_per_period])
    ax.set_xlabel("後半に、ポイントが1回ごとに大きく付いていく度合い（チームごとに0〜最大の間）")
    ax.set_ylabel(f"後半÷前半が{JUDGE}以上の割合（%）"); ax.set_ylim(0, 120); ax.set_yticks(range(0, 101, 20))
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("ポイントが少しずつ大きく付くと、変わらないチームも「増えた」と出る", fontsize=11.5)
    save(fig, "a1097_within.png", SRC, y=-0.07)

    print(cross_df.to_string()); print(json.dumps(extra, ensure_ascii=False)); print(json.dumps(out["teams_one_run"], ensure_ascii=False))
    print(teams_one.to_string()); print(grid.to_string()); print(within.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
