"""998 アンケートで聞いた「初めて来た人の割合」は合うのか？（架空のデータ）

架空の体験型の展示館「C館」の1年（364日）。1年に来た人（実人数）ごとに、1年の来場回数と、
この館に初めて来た人かどうかを作成者が置く。館の中で、来場した人に「今日、初めて来ましたか」と聞く
アンケートを12日行い、「初めて」と答えた割合を、
 ・来場（延べ）のうち、初めての来場の割合
 ・1年に来た人（実人数）のうち、初めて来た人の割合
と比べる。答えやすさの違い、「初めて」の答え違い、聞く日の選び方も入れる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 998
SRC = "架空の展示館の来場者とアンケート（作成者が乱数で作成、seed 998）"
N_DAY = 364
N_PEOPLE = 20000
GROUPS = ["1回だけ", "ときどき", "常連"]
G_SHARE = {"1回だけ": 0.65, "ときどき": 0.25, "常連": 0.10}
G_VISITS = {"1回だけ": (1, 1), "ときどき": (2, 5), "常連": (6, 40)}       # 1年の来場回数（一様）
G_NEW = {"1回だけ": 0.7, "ときどき": 0.4, "常連": 0.1}                   # この館に初めて来た人の割合
G_WEEKEND_W = {"1回だけ": 3.0, "ときどき": 3.0, "常連": 1.0}            # 土日の来やすさ（平日1に対して）
SURVEY_DAYS = 12
ASK_RATE = 0.5                           # 聞く日に、来場した人の2人に1人に聞く
RESP_FIRST, RESP_OTHER = 0.50, 0.35     # 答えてくれる確率（初めての来場・それ以外）
MISREPORT = 0.2                          # 前の年までに来たことがある人が、今年の最初の来場で「初めて」と答える確率
COUNT_SD = 0.3                           # 「1年に何回くらい来ますか」の答えのずれ（対数の標準偏差）
REPS = 200
GRID_REPS = 50


def make_year(rng, regular_share=G_SHARE["常連"]):
    share = {"1回だけ": 0.65, "ときどき": 0.25, "常連": regular_share}
    s = np.array([share[g] for g in GROUPS]); s = s / s.sum()
    gi = rng.choice(3, N_PEOPLE, p=s)
    lo = np.array([G_VISITS[g][0] for g in GROUPS])[gi]
    hi = np.array([G_VISITS[g][1] for g in GROUPS])[gi]
    nv = rng.integers(lo, hi + 1)
    new = rng.random(N_PEOPLE) < np.array([G_NEW[g] for g in GROUPS])[gi]
    pid = np.repeat(np.arange(N_PEOPLE), nv)
    vg = gi[pid]
    wk = np.array([G_WEEKEND_W[g] for g in GROUPS])
    # 来る日：土日の重みで日を引く（同じ人が同じ日に2回来ることも許す）
    weekend_day = (np.arange(N_DAY) % 7 >= 5)
    day = np.empty(len(pid), int)
    for g in range(3):
        idx = np.where(vg == g)[0]
        cw = np.cumsum(np.where(weekend_day, wk[g], 1.0)); cw = cw / cw[-1]
        day[idx] = np.minimum(np.searchsorted(cw, rng.random(len(idx)), side="right"), N_DAY - 1)
    key = pid * (N_DAY + 1.0) + day + rng.random(len(pid)) * 0.5
    order = np.argsort(key, kind="stable")
    ps = pid[order]
    first_of_year = np.zeros(len(pid), bool)
    first_of_year[order[np.r_[True, ps[1:] != ps[:-1]]]] = True
    visits = {"person": pid, "group": vg, "day": day, "weekend": weekend_day[day].astype(int),
              "first_of_year": first_of_year, "first_ever": first_of_year & new[pid], "n_year": nv[pid],
              "new_person": new[pid]}
    truth = {"visits": int(len(pid)), "people": N_PEOPLE,
             "visit_share_pct": float(visits["first_ever"].mean() * 100), "people_share_pct": float(new.mean() * 100)}
    return visits, truth


def survey(rng, visits, weekend_only=False, resp=(RESP_FIRST, RESP_OTHER), mis=MISREPORT):
    wd = np.arange(N_DAY)
    cand = wd[wd % 7 >= 5] if weekend_only else wd
    days = rng.choice(cand, SURVEY_DAYS, replace=False)
    sel = np.where(np.isin(visits["day"], days))[0]
    sel = sel[rng.random(len(sel)) < ASK_RATE]
    v = {k: a[sel] for k, a in visits.items()}
    fe, fy, nn = v["first_ever"], v["first_of_year"], v["new_person"]
    answered = rng.random(len(sel)) < np.where(fe, resp[0], resp[1])
    # 問1「今日、初めて来ましたか」：前の年までに来たことがある人も、今年の最初の来場では mis の確率で「初めて」と答える
    q1 = fe | (fy & ~nn & (rng.random(len(sel)) < mis))
    # 問2「去年までに、この館に来たことがありますか」：来たことがある人も mis の確率で「ない」と答える
    q2 = nn | (~nn & (rng.random(len(sel)) < mis))
    k = v["n_year"]
    k_rep = np.maximum(1, np.round(k * np.exp(rng.normal(0, COUNT_SD, len(sel)))))
    A = answered
    out = {"asked": int(len(sel)), "answered": int(A.sum()),
           "q1_all_truthful": fe.mean() * 100,                     # 聞いた全員が答え、答え違いもないとき
           "q1_response": fe[A].mean() * 100,                      # 答えやすさの違いだけ
           "q1_full": q1[A].mean() * 100,                          # 答えやすさ＋答え違い（基本）
           "q2_plain_full": q2[A].mean() * 100,                    # 問2をそのまま
           "q2_weighted_all_truthful_truecount": np.average(nn, weights=1 / k) * 100,
           "q2_weighted_full_truecount": np.average(q2[A], weights=1 / k[A]) * 100,
           "q2_weighted_full": np.average(q2[A], weights=1 / k_rep[A]) * 100,   # 問2に、答えた回数の逆数で重み（基本）
           "regular_share_of_answers_pct": (v["group"][A] == 2).mean() * 100}
    df = pd.DataFrame({"day": v["day"], "weekend": v["weekend"], "group": v["group"], "first_ever": fe.astype(int),
                       "first_of_year": fy.astype(int), "new_person": nn.astype(int), "n_year": k,
                       "answered": A.astype(int), "q1_says_first": q1.astype(int), "q2_says_never": q2.astype(int),
                       "reported_count": k_rep.astype(int)})
    return out, df


def run(rng, reps, regular_share=G_SHARE["常連"], resp=(RESP_FIRST, RESP_OTHER), mis=MISREPORT):
    rows = []
    for _ in range(reps):
        visits, t = make_year(rng, regular_share)
        a, _ = survey(rng, visits, False, resp, mis)
        b, _ = survey(rng, visits, True, resp, mis)
        row = {"truth_visit_share_pct": t["visit_share_pct"], "truth_people_share_pct": t["people_share_pct"],
               "visits": t["visits"]}
        row.update({f"random_{k}": x for k, x in a.items()})
        row.update({f"weekend_{k}": x for k, x in b.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    sim = run(rng, REPS)
    sim.round(3).to_csv(RES / "base_200reps.csv", index=False)
    keys = ["truth_visit_share_pct", "truth_people_share_pct", "visits"] + \
        [f"{d}_{k}" for d in ["random", "weekend"] for k in
         ["asked", "answered", "q1_all_truthful", "q1_response", "q1_full", "q2_plain_full",
          "q2_weighted_all_truthful_truecount", "q2_weighted_full_truecount", "q2_weighted_full",
          "regular_share_of_answers_pct"]]
    base = {k: round(float(sim[k].mean()), 2) for k in keys}
    q = {k: [round(float(sim[k].quantile(0.1)), 2), round(float(sim[k].quantile(0.9)), 2)]
         for k in ["random_q1_full", "weekend_q1_full", "random_q2_weighted_full", "random_q2_weighted_all_truthful_truecount"]}

    # 例の1年と、その年のアンケート（ランダムな12日）
    g = np.random.default_rng(SEED * 10)
    visits, t1 = make_year(g)
    a1, ans = survey(g, visits)
    ans.assign(group=ans.group.map(dict(enumerate(GROUPS)))).to_csv(DATA / "survey_example.csv", index=False)
    by_group = []
    for gi, gname in enumerate(GROUPS):
        m = visits["group"] == gi
        npp = int(len(np.unique(visits["person"][m])))
        by_group.append({"group": gname, "people": npp, "visits": int(m.sum()),
                         "people_share_pct": round(npp / N_PEOPLE * 100, 2),
                         "visit_share_pct": round(m.sum() / len(m) * 100, 2)})
    by_group = pd.DataFrame(by_group)
    by_group.to_csv(RES / "example_people_vs_visits.csv", index=False)

    # 確かめ：常連の割合 × 答えやすさ × 答え違い（27通り、各50回）
    grid = []
    for rs in [0.05, 0.10, 0.20]:
        for rname, resp in [("初めてが答えやすい", (0.50, 0.35)), ("同じ", (0.40, 0.40)), ("初めてが答えにくい", (0.35, 0.50))]:
            for mis in [0.0, 0.2, 0.4]:
                gg = np.random.default_rng(SEED * 1000 + int(rs * 100) * 10 + int(mis * 10) + int(resp[0] * 100) * 1000)
                s = run(gg, GRID_REPS, rs, resp, mis)
                grid.append({"regular_share": rs, "response": rname, "misreport": mis,
                             **{k: round(float(s[k].mean()), 2) for k in
                                ["truth_visit_share_pct", "truth_people_share_pct", "random_q1_full", "weekend_q1_full",
                                 "random_q2_weighted_full", "random_q2_weighted_all_truthful_truecount"]}})
    grid = pd.DataFrame(grid)
    grid["gap_people_minus_survey_pt"] = (grid.truth_people_share_pct - grid.random_q1_full).round(2)
    grid["survey_minus_visit_pt"] = (grid.random_q1_full - grid.truth_visit_share_pct).round(2)
    grid["weighted_minus_people_pt"] = (grid.random_q2_weighted_full - grid.truth_people_share_pct).round(2)
    grid["weekend_minus_random_pt"] = (grid.weekend_q1_full - grid.random_q1_full).round(2)
    grid["check_weighted_truthful_minus_people_pt"] = (grid.random_q2_weighted_all_truthful_truecount
                                                       - grid.truth_people_share_pct).round(2)
    grid.to_csv(RES / "grid_regular_response_misreport.csv", index=False)

    eq0 = grid[(grid.response == "同じ") & (grid.misreport == 0.0)]
    out = {"setting": {"days": N_DAY, "people": N_PEOPLE, "group_share": G_SHARE, "group_visits": G_VISITS, "group_new": G_NEW,
                       "group_weekend_weight": G_WEEKEND_W, "survey_days": SURVEY_DAYS, "ask_rate": ASK_RATE,
                       "resp_first": RESP_FIRST, "resp_other": RESP_OTHER, "misreport": MISREPORT, "count_sd": COUNT_SD,
                       "reps": REPS},
           "base_200reps": base, "p10_p90": q,
           "first_year": {"truth": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in t1.items()},
                          "survey": {k: (round(float(v), 2)) for k, v in a1.items()}},
           "example_by_group": by_group.to_dict("records"),
           "grid_info": {"cases": int(len(grid)), "reps_each": GRID_REPS},
           "grid_range": {c: [float(grid[c].min()), float(grid[c].max())] for c in
                          ["truth_visit_share_pct", "truth_people_share_pct", "random_q1_full", "weekend_q1_full",
                           "random_q2_weighted_full", "gap_people_minus_survey_pt", "survey_minus_visit_pt",
                           "weighted_minus_people_pt", "weekend_minus_random_pt",
                           "check_weighted_truthful_minus_people_pt"]},
           "grid_equal_resp_no_mis": {c: [float(eq0[c].min()), float(eq0[c].max())] for c in
                                      ["survey_minus_visit_pt", "weighted_minus_people_pt", "gap_people_minus_survey_pt"]},
           "grid_by_regular_share": {str(rs): {c: [float(grid[grid.regular_share == rs][c].min()),
                                                   float(grid[grid.regular_share == rs][c].max())]
                                               for c in ["truth_visit_share_pct", "truth_people_share_pct", "random_q1_full"]}
                                     for rs in [0.05, 0.10, 0.20]},
           "grid_survey_below_people_cases": int((grid.random_q1_full < grid.truth_people_share_pct).sum())}
    json.dump(out, open(RES / "a998_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：実人数と延べの来場で、グループの割合が違う（例の1年）
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    cols = [LIGHT, BLUE, ORANGE]
    for row_i, (lab, col) in enumerate([("1年に来た人（実人数）", "people_share_pct"), ("来場（延べ）", "visit_share_pct")]):
        left = 0
        for gi, gname in enumerate(GROUPS):
            w = by_group.loc[gi, col]
            ax.barh(1 - row_i, w, left=left, color=cols[gi], label=gname if row_i == 0 else None, height=0.55)
            if w > 6:
                ax.text(left + w / 2, 1 - row_i, f"{gname}\n{w:.1f}%", ha="center", va="center", fontsize=9,
                        color="white" if gi > 0 else INK)
            left += w
    ax.set_yticks([1, 0]); ax.set_yticklabels(["1年に来た人\n（実人数）", "来場\n（延べ）"])
    ax.set_xlim(0, 100); ax.set_xlabel("割合（%）")
    ax.set_title("常連は人数では1割でも、来場の延べでは半分を超える（例の1年）", fontsize=12)
    save(fig, "a998_people_vs_visits.png", SRC)

    # 図2：本当の2つの割合と、アンケートの答え（200回の平均）
    fig, ax = plt.subplots(figsize=(7.6, 4.1))
    items = [("本当：実人数のうち初めて来た人", base["truth_people_share_pct"], GREEN),
             ("本当：延べの来場のうち初めての来場", base["truth_visit_share_pct"], GREEN),
             ("問1：全員が答え、答え違いなし", base["random_q1_all_truthful"], LIGHT),
             ("問1：＋答えやすさの違い", base["random_q1_response"], BLUE),
             ("問1：＋答え違い（基本）", base["random_q1_full"], ORANGE),
             ("問1：土日だけの12日で聞く", base["weekend_q1_full"], ORANGE),
             ("問2×回数の逆数：全員が答え、答え違いなし", base["random_q2_weighted_all_truthful_truecount"], LIGHT),
             ("問2×答えた回数の逆数（基本）", base["random_q2_weighted_full"], GRAY)]
    y = np.arange(len(items))[::-1]
    for yy, (lab, v, c) in zip(y, items):
        ax.barh(yy, v, color=c, height=0.6)
        ax.text(v + 0.8, yy, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels([i[0] for i in items], fontsize=9)
    ax.set_xlim(0, 85); ax.set_xlabel("「初めて」の割合（%）")
    ax.set_title("アンケートの「初めて」は、延べの来場の割合に近く、実人数の割合とは離れる\n（200回の平均）", fontsize=12)
    save(fig, "a998_shares.png", SRC)

    # 図3：確かめ。常連の割合ごとに、本当の2つの割合とアンケート（27通り）
    fig, ax = plt.subplots(figsize=(7.8, 4.1))
    xs = np.arange(3) * 1.4
    for i, rs in enumerate([0.05, 0.10, 0.20]):
        gg = grid[grid.regular_share == rs]
        x0 = xs[i]
        pv = gg.truth_people_share_pct.mean(); vv = gg.truth_visit_share_pct.mean()
        ax.plot([x0 - 0.35], [pv], "D", color=GREEN, ms=8, label="本当：実人数のうち初めて来た人" if i == 0 else None)
        ax.text(x0 - 0.35, pv + 3, f"{pv:.1f}%", ha="center", fontsize=8.5, color=GREEN)
        lo, hi = gg.random_q1_full.min(), gg.random_q1_full.max()
        ax.vlines(x0, lo, hi, color=ORANGE, lw=8, label="問1のアンケート（答えやすさ×答え違いの9通りの幅）" if i == 0 else None)
        ax.text(x0, hi + 2, f"{lo:.1f}〜{hi:.1f}%", ha="center", fontsize=8.5, color=ORANGE)
        ax.plot([x0 + 0.35], [vv], "o", color=BLUE, ms=8, label="本当：延べの来場のうち初めての来場" if i == 0 else None)
        ax.text(x0 + 0.35, vv - 5, f"{vv:.1f}%", ha="center", fontsize=8.5, color=BLUE)
    ax.set_xticks(xs); ax.set_xticklabels(["常連 5%", "常連 10%（基本）", "常連 20%"])
    ax.set_xlim(-0.8, xs[-1] + 0.8)
    ax.set_ylabel("「初めて」の割合（%）"); ax.set_ylim(0, 80)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("確かめ：答えやすさ・答え違いを変えても、アンケートは実人数の割合に届かない（各50回）", fontsize=11.5)
    save(fig, "a998_grid.png", SRC)

    print(json.dumps({k: out[k] for k in out if k not in ("setting",)}, ensure_ascii=False, indent=1))
    print(grid.to_string())


if __name__ == "__main__":
    main()
