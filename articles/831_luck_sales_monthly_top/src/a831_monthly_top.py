"""831 営業成績の月間1位は、何か月続くのか？（架空のデータ）

架空の営業チーム（基本20人）。人ごとに「本当の実力」（毎月の売上の見込み、万円）を置き、
毎月の売上は、実力にその月の運（正規分布の振れ）を足したもの。実力は1年のあいだ変わらない。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 831
SRC = "架空の営業チームの売上（作成者が乱数で作成、seed 831）"
rng = np.random.default_rng(SEED)
N_REP = 5000
MONTHS = 12


def simulate(rng, n_rep=N_REP, n_people=20, skill_sd=30.0, luck_sd=60.0, months=MONTHS):
    """skill: (rep, person)、sales: (rep, month, person)"""
    skill = rng.normal(300, skill_sd, (n_rep, n_people))
    sales = skill[:, None, :] + rng.normal(0, luck_sd, (n_rep, months, n_people))
    return skill, sales


def summarize(skill, sales):
    n_rep, months, n = sales.shape
    top = sales.argmax(2)                       # 月ごとの1位
    best = skill.argmax(1)                      # 本当にいちばん実力のある人
    repeat = (top[:, 1:] == top[:, :-1]).mean()  # 翌月も同じ人が1位
    distinct = np.array([len(set(r)) for r in top])
    # 1位の続いた月数（年の中で数える。年の初めと終わりで切れる）
    runs = []
    longest = []
    for r in top:
        cur, lng = 1, 1
        for a, b in zip(r[:-1], r[1:]):
            if a == b:
                cur += 1
            else:
                runs.append(cur); cur = 1
            lng = max(lng, cur)
        runs.append(cur); longest.append(lng)
    runs = np.array(runs); longest = np.array(longest)
    best_months = (top == best[:, None]).sum(1)
    annual_top = sales.sum(1).argmax(1)
    # 1位になった月の多い人（年間で最多）が本当にいちばんか
    return {
        "p_repeat_next_month": round(float(repeat), 3),
        "mean_run_months": round(float(runs.mean()), 2),
        "share_runs_ge2": round(float((runs >= 2).mean()), 3),
        "share_runs_ge3": round(float((runs >= 3).mean()), 3),
        "p_year_has_run_ge3": round(float((longest >= 3).mean()), 3),
        "mean_distinct_top_people": round(float(distinct.mean()), 2),
        "distinct_p10": int(np.quantile(distinct, .1)), "distinct_p90": int(np.quantile(distinct, .9)),
        "best_mean_months_top": round(float(best_months.mean()), 2),
        "p_best_never_top": round(float((best_months == 0).mean()), 3),
        "p_annual_total_top_is_best": round(float((annual_top == best).mean()), 3),
        "skill_share_of_variance": None,
    }, distinct, best_months


def main():
    # 1回分のチーム（data に保存）
    sk1, sa1 = simulate(rng, 1)
    order = np.argsort(-sk1[0])
    df = pd.DataFrame({"person_id": np.arange(1, 21), "skill": sk1[0]})
    for m in range(MONTHS):
        df[f"m{m+1:02d}"] = sa1[0, m]
    df["skill_rank"] = df["skill"].rank(ascending=False).astype(int)
    df["months_top"] = [(sa1[0].argmax(1) == i).sum() for i in range(20)]
    df.to_csv(DATA / "team_one_year.csv", index=False, float_format="%.1f")
    one = {"months_top_by_skill_rank": {int(r): int(m) for r, m in zip(df.skill_rank, df.months_top)},
           "distinct_top_people": int(len(set(sa1[0].argmax(1)))),
           "top_by_month_skill_rank": [int(df.skill_rank[i]) for i in sa1[0].argmax(1)]}

    # 基本と、運だけ・実力だけの目安
    base, dist_base, bm_base = summarize(*simulate(np.random.default_rng(SEED * 10 + 1)))
    base["skill_share_of_variance"] = round(30**2 / (30**2 + 60**2), 2)
    luck_only, dist_luck, _ = summarize(*simulate(np.random.default_rng(SEED * 10 + 2), skill_sd=0.0))
    luck_only["skill_share_of_variance"] = 0.0
    best_months_dist = {int(k): round(float((bm_base == k).mean()), 3) for k in range(0, 13)}

    # 確かめ：運の振れの大きさ（実力の占める割合）とチームの人数
    sens = []
    for n in [10, 20, 50]:
        for luck in [30.0, 60.0, 120.0]:
            s, d, _ = summarize(*simulate(np.random.default_rng(SEED * 100 + n + int(luck)), 3000, n, 30.0, luck))
            s["skill_share_of_variance"] = round(30**2 / (30**2 + luck**2), 2)
            s.update({"n_people": n, "luck_sd": luck})
            sens.append(s)
            if n == 20:
                if luck == 30.0:
                    dist_hi = d
                if luck == 120.0:
                    dist_lo = d
    sens_df = pd.DataFrame(sens)[["n_people", "luck_sd", "skill_share_of_variance", "p_repeat_next_month",
                                  "mean_run_months", "p_year_has_run_ge3", "mean_distinct_top_people",
                                  "best_mean_months_top", "p_best_never_top", "p_annual_total_top_is_best"]]
    sens_df.to_csv(RES / "sensitivity.csv", index=False)

    out = {"settings": {"n_people": 20, "skill_mean": 300, "skill_sd": 30, "luck_sd": 60, "months": 12,
                        "n_rep": N_REP},
           "base": base, "luck_only": luck_only, "best_person_months_top_dist": best_months_dist,
           "distinct_dist_base": {int(k): round(float((dist_base == k).mean()), 3) for k in range(1, 13)},
           "one_team": one, "sensitivity": sens_df.to_dict("records")}
    json.dump(out, open(RES / "a831_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1年分のチーム。実力の順に並べた20人が、何か月1位になったか
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    d1 = df.sort_values("skill_rank")
    ax.bar(d1.skill_rank, d1.months_top, color=[ORANGE if r == 1 else BLUE for r in d1.skill_rank])
    ax.set_xticks(range(1, 21)); ax.set_xlabel("本当の実力の順位（1＝いちばん実力がある）")
    ax.set_ylabel("月間1位になった月の数"); ax.set_yticks(range(0, int(d1.months_top.max()) + 2))
    m1 = int(d1.months_top.iloc[0])
    ax.text(1, m1 + .12, f"実力1位の人は{m1}か月", rotation=90, ha="center", va="bottom", fontsize=9, color=ORANGE)
    ax.set_ylim(0, d1.months_top.max() + 1.2)
    ax.set_title(f"ある1年（架空のチーム20人）：12か月の1位は{one['distinct_top_people']}人に分かれた")
    save(fig, "a831_one_year.png", SRC)

    # 図2：12か月で1位になった人数の分布
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ks = np.arange(1, 13)
    w = 0.27
    for off, d, c, lab in [(-w, dist_hi, GREEN, "運の振れが小さい（実力の占める割合0.5）"),
                           (0, dist_base, BLUE, "基本（実力の占める割合0.2）"),
                           (w, dist_lo, GRAY, "運の振れが大きい（実力の占める割合0.06）")]:
        ax.bar(ks + off, [(d == k).mean() * 100 for k in ks], width=w, color=c, label=lab)
    ax.set_xticks(ks); ax.set_xlabel("12か月のうちに月間1位になった人の数（20人のチーム）")
    ax.set_ylabel("割合（%）"); ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("月間1位は、1年で何人に分かれるか")
    save(fig, "a831_distinct.png", SRC)

    # 図3：翌月も同じ人が1位の確率と、実力の占める割合
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for n, c in [(10, GREEN), (20, BLUE), (50, ORANGE)]:
        s = sens_df[sens_df.n_people == n].sort_values("skill_share_of_variance")
        ax.plot(s.skill_share_of_variance, s.p_repeat_next_month * 100, "o-", color=c, label=f"{n}人のチーム")
        ax.axhline(100 / n, color=c, lw=.8, ls=":")
    ax.set_xlabel("毎月の売上の散らばりのうち、実力の差が占める割合")
    ax.set_ylabel("翌月も同じ人が1位の確率（%）"); ax.set_ylim(0, 40)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("点線は運だけのとき（1÷人数）。実力の割合が半分でも、翌月も1位は3割以下")
    save(fig, "a831_repeat.png", SRC)
    print(json.dumps({k: out[k] for k in ["base", "luck_only", "one_team"]}, ensure_ascii=False, indent=1))
    print(sens_df.to_string())


if __name__ == "__main__":
    main()
