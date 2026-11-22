"""933 甘い評価者と辛い評価者の点を、そのまま比べてよいのか？（架空のデータ）

架空の会社の社員200人。評価者（上司）20人が、自分のチームの10人ずつに100点満点で点を付ける。
社員ごとに「本当の実力の点」を置き、評価者ごとに「甘さ」（全員に同じだけ足す点）を置く。
チームごとの本当の実力の平均にも差を置ける。本当の点が分かっているので、
点のまま・評価者ごとの平均を引く・ほかの評価者にも見てもらった人から甘さを見積もって引く、の3つで
本当の上位20人をどれだけ当てるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 933
SRC = "架空の会社の人事評価（作成者が乱数で作成、seed 933）"
N_EV, TEAM = 20, 10
N = N_EV * TEAM
TOP = 20
SD_TRUE = 10.0     # 本当の実力の点の標準偏差（平均60点）
SD_NOISE = 6.0     # 1回の評価のぶれ（点）
BASE_LEN = 5.0     # 評価者の甘さの差（標準偏差、点）
BASE_TEAM = 3.0    # チームの本当の実力の平均の差（標準偏差、点）
BASE_LINK = 0.3    # ほかのチームの評価者にも見てもらう人の割合
N_REP = 300
METHODS = ["点のまま", "評価者ごとの平均を引く", "2人目の評価から甘さを見積もって引く"]


def make_company(rng, sd_len=BASE_LEN, sd_team=BASE_TEAM, link=BASE_LINK):
    ev = np.repeat(np.arange(N_EV), TEAM)
    team_mean = rng.normal(0, sd_team, N_EV)
    sd_ind = np.sqrt(max(SD_TRUE ** 2 - sd_team ** 2, 1e-9))
    true = 60 + team_mean[ev] + rng.normal(0, sd_ind, N)
    len_ = rng.normal(0, sd_len, N_EV)
    own = true + len_[ev] + rng.normal(0, SD_NOISE, N)
    has2 = rng.random(N) < link
    ev2 = (ev + rng.integers(1, N_EV, N)) % N_EV          # 自分のチーム以外の評価者
    sec = np.where(has2, true + len_[ev2] + rng.normal(0, SD_NOISE, N), np.nan)
    return {"ev": ev, "true": true, "len": len_, "own": own, "has2": has2, "ev2": ev2, "sec": sec,
            "team_mean": team_mean}


def est_leniency(c):
    """全員の点（本人の評価者＋2人目）から、社員の実力と評価者の甘さを同時に見積もる（リッジ付き最小二乗）。
    社員の実力は平均60・標準偏差10、ぶれは6点と分かっているとして置く。甘さは弱い制約（標準偏差50点）だけ。"""
    rows_p, rows_e, y = list(range(N)), list(c["ev"]), list(c["own"])
    idx = np.where(c["has2"])[0]
    rows_p += list(idx); rows_e += list(c["ev2"][idx]); y += list(c["sec"][idx])
    m = len(y)
    rp, re_ = np.array(rows_p), N + np.array(rows_e)
    # 正規方程式（X'X/σ² + 事前の重み）x = X'y/σ² を直接作って解く
    P = np.zeros((N + N_EV, N + N_EV))
    np.add.at(P, (rp, rp), 1.0); np.add.at(P, (re_, re_), 1.0)
    np.add.at(P, (rp, re_), 1.0); np.add.at(P, (re_, rp), 1.0)
    P /= SD_NOISE ** 2
    P[np.arange(N), np.arange(N)] += 1 / SD_TRUE ** 2
    P[N + np.arange(N_EV), N + np.arange(N_EV)] += 1 / 50.0 ** 2
    yy = (np.array(y) - 60) / SD_NOISE ** 2
    rhs = np.zeros(N + N_EV)
    np.add.at(rhs, rp, yy); np.add.at(rhs, re_, yy)
    sol = np.linalg.solve(P, rhs)
    return sol[N:]


def scores(c):
    own, ev = c["own"], c["ev"]
    ev_mean = pd.Series(own).groupby(ev).transform("mean").values
    return {METHODS[0]: own, METHODS[1]: own - ev_mean + own.mean(),
            METHODS[2]: own - est_leniency(c)[ev]}


def spearman(a, b):
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def evaluate(c):
    top_true = set(np.argsort(-c["true"])[:TOP])
    lenient4 = set(np.argsort(-c["len"])[:4])
    out = {}
    for k, s in scores(c).items():
        top = np.argsort(-s)[:TOP]
        out[k] = {"precision20": len(top_true & set(top)) / TOP, "spearman": spearman(s, c["true"]),
                  "share_from_lenient4": float(np.isin(c["ev"][top], list(lenient4)).mean())}
    return out


def run_reps(n_rep, base_seed, **kw):
    rec = []
    for r in range(n_rep):
        c = make_company(np.random.default_rng(base_seed + r), **kw)
        for k, v in evaluate(c).items():
            rec.append({"rep": r, "method": k, **v})
    return pd.DataFrame(rec)


def main():
    rng = np.random.default_rng(SEED)

    # 1) 1社分（data に置く）
    c = make_company(rng)
    df = pd.DataFrame({"person_id": np.arange(1, N + 1), "evaluator": c["ev"] + 1,
                       "true_score": c["true"].round(2), "own_rating": c["own"].round(2),
                       "second_evaluator": np.where(c["has2"], c["ev2"] + 1, 0),
                       "second_rating": np.round(c["sec"], 2)})
    df.to_csv(DATA / "ratings_one_company.csv", index=False)
    evs = pd.DataFrame({"evaluator": np.arange(1, N_EV + 1), "leniency": c["len"].round(2),
                        "team_true_mean_offset": c["team_mean"].round(2),
                        "mean_rating": pd.Series(c["own"]).groupby(c["ev"]).mean().round(2).values,
                        "est_leniency": est_leniency(c).round(2)})
    evs.to_csv(RES / "evaluators_one_company.csv", index=False)
    e1 = evaluate(c)
    one = {"leniency_max": round(float(c["len"].max()), 2), "leniency_min": round(float(c["len"].min()), 2),
           "leniency_max_minus_min": round(float(c["len"].max() - c["len"].min()), 2),
           "n_second": int(c["has2"].sum()),
           "corr_est_true_leniency": round(float(np.corrcoef(evs.leniency, evs.est_leniency)[0, 1]), 3),
           "by_method": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in e1.items()}}

    # 2) 基本の置き方で300社
    base = run_reps(N_REP, SEED * 1000)
    bsum = base.groupby("method", sort=False)[["precision20", "spearman", "share_from_lenient4"]].mean().round(3)
    bsum.to_csv(RES / "methods_base.csv")

    # 3) 確かめ：甘さの差 × チームの実力差
    grid = []
    for i, sl in enumerate([0.0, 2.5, 5.0, 10.0]):
        for j, st in enumerate([0.0, 3.0, 6.0]):
            sd_ = SEED * 1000 if (sl, st) == (BASE_LEN, BASE_TEAM) else SEED * 100000 + i * 10000 + j * 1000
            d = run_reps(N_REP, sd_, sd_len=sl, sd_team=st)   # 基本の置き方の升は2)と同じ300社
            m = d.groupby("method", sort=False)[["precision20", "spearman", "share_from_lenient4"]].mean().round(3)
            for k in METHODS:
                grid.append({"sd_leniency": sl, "sd_team": st, "method": k,
                             **{kk: round(float(v), 3) for kk, v in m.loc[k].items()}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness_leniency_team.csv", index=False)

    # 4) 確かめ：2人目に見てもらう人の割合
    links = []
    for i, lk in enumerate([0.0, 0.1, 0.3, 0.6]):
        d = base if lk == BASE_LINK else run_reps(N_REP, SEED * 7000 + i * 500, link=lk)
        m = d.groupby("method", sort=False)["precision20"].mean().round(3)
        links.append({"link_share": lk, **{k: round(float(m[k]), 3) for k in METHODS}})
    links = pd.DataFrame(links)
    links.to_csv(RES / "robustness_link_share.csv", index=False)

    g = grid.pivot_table(index=["sd_leniency", "sd_team"], columns="method", values="precision20")
    best = g.idxmax(axis=1)
    out = {"setup": {"n_people": N, "n_evaluators": N_EV, "team_size": TEAM, "top": TOP, "sd_true": SD_TRUE,
                     "sd_noise": SD_NOISE, "sd_leniency": BASE_LEN, "sd_team": BASE_TEAM, "link_share": BASE_LINK,
                     "n_rep": N_REP},
           "one_company": one,
           "base_300reps": {k: {kk: float(vv) for kk, vv in bsum.loc[k].items()} for k in METHODS},
           "grid_precision20_range": {k: [float(grid[grid.method == k].precision20.min()),
                                          float(grid[grid.method == k].precision20.max())] for k in METHODS},
           "grid_best_method": {f"len{a}_team{b}": v for (a, b), v in best.items()},
           "raw_minus_centered_when_len0": {f"team{st}": round(float(g.loc[(0.0, st), METHODS[0]] - g.loc[(0.0, st), METHODS[1]]), 3)
                                             for st in [0.0, 3.0, 6.0]},
           "link_share": links.to_dict("records")}
    json.dump(out, open(RES / "a933_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1社分の評価者ごとの点（甘さの順）
    order = np.argsort(c["len"])
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for x, e in enumerate(order):
        m = c["ev"] == e
        ax.scatter(np.full(m.sum(), x) + rng.uniform(-.18, .18, m.sum()), c["own"][m], s=12, color=BLUE, alpha=.6, lw=0)
        ax.scatter(np.full(m.sum(), x) + .3, c["true"][m], s=6, color=GRAY, alpha=.6, lw=0)
    ax.set_xticks(range(N_EV)); ax.set_xticklabels([str(e + 1) for e in order], fontsize=8)
    ax.set_xlabel("評価者（左ほど辛く、右ほど甘く置いた）"); ax.set_ylabel("点（100点満点）")
    ax.scatter([], [], s=12, color=BLUE, label="付いた点"); ax.scatter([], [], s=6, color=GRAY, label="本当の実力の点")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"同じ会社でも、評価者の甘さで点の高さがずれる（甘さは{c['len'].min():+.1f}〜{c['len'].max():+.1f}点）", fontsize=11.5)
    save(fig, "a933_one_company.png", SRC)

    # 図2：基本の置き方で、3つの数え方の当たりと、甘い4人の部下の占める割合
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4), sharey=True)
    lab = ["点のまま", "評価者ごとの\n平均を引く", "2人目の評価から\n甘さを見積もって引く"]
    for ax, key, xl in [(axes[0], "share_from_lenient4", "上位20人のうち、甘い4人の部下の割合（%）"),
                        (axes[1], "precision20", "上位20人のうち、本当の上位20人の割合（%）")]:
        v = [bsum.loc[k, key] * 100 for k in METHODS]
        ax.barh(lab[::-1], v[::-1], color=[GREEN, BLUE, GRAY])
        for i, x in enumerate(v[::-1]):
            ax.text(x + 1, i, f"{x:.1f}%", va="center", fontsize=9)
        ax.set_xlim(0, 100); ax.set_xlabel(xl, fontsize=9.5)
    axes[0].axvline(20, color=ORANGE, lw=1, ls="--"); axes[0].text(21, 2.42, "部下の数の割合20%", color=ORANGE, fontsize=8)
    fig.suptitle("甘さを直すと甘い4人の部下への偏りは消えるが、当たりはあまり変わらない（300社の平均）", fontsize=12, y=1.03)
    save(fig, "a933_methods.png", SRC, y=-0.06)

    # 図3：甘さの差とチームの差を変えると
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.6), sharey=True)
    cols = {METHODS[0]: GRAY, METHODS[1]: BLUE, METHODS[2]: GREEN}
    for ax, st in zip(axes, [0.0, 3.0, 6.0]):
        for k in METHODS:
            d = grid[(grid.sd_team == st) & (grid.method == k)]
            ax.plot(d.sd_leniency, d.precision20 * 100, marker="o", ms=4, lw=2, color=cols[k], label=k)
        ax.set_title(f"チームの実力の差 {st:.0f}点", fontsize=11)
        ax.set_xlabel("評価者の甘さの差（点）"); ax.set_xticks([0, 2.5, 5, 10])
    axes[0].set_ylabel("本当の上位20人に入っていた割合（%）")
    axes[0].set_ylim(0, 80)
    axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("どの数え方が当たるかは、甘さの差とチームの実力の差の置き方で入れかわる", fontsize=12, y=1.02)
    save(fig, "a933_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
