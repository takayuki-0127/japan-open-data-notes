"""1192 担当から担当へ回された問い合わせの解決を、どの担当の数字に入れるかで、担当ごとの解決率はどう変わるのか？（架空のデータ）

架空の会社の問い合わせ窓口。初めに受ける担当8人（A〜H）と、回された問い合わせだけを受ける担当2人（I・J）。
担当ごとの「本当の解く力」と「回しやすさ（どれくらい難しいと手を付けずに回すか）」を作成者が置き、
問い合わせの難しさを乱数で作って、回す・解決する・解決しないを決める。
同じ記録を、4つの数え方で担当ごとの解決率にする。
  ① 最初に受けた担当に、最後の結果（誰が解決しても）で数える
  ② 最後に持っていた担当に数える
  ③ 回された件は、回した担当と受けた担当で半分ずつ数える（件数も解決も）
  ④ 最初に受けた担当に、回さずに自分で解決した件だけを解決と数える
担当は記号だけで、人の属性は置いていない。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1192
SRC = "架空の問い合わせ窓口の担当10人（作成者が置いた解く力・回しやすさ・難しさからの乱数、seed 1192）"
FIRST = list("ABCDEFGH")
SPEC = list("IJ")
NAMES = FIRST + SPEC
Z8 = np.array([-1.53, -0.89, -0.49, -0.16, 0.16, 0.49, 0.89, 1.53])   # 8人に割り当てる標準の目盛り
N_TICKET = 4000      # 1年に来る問い合わせ
A0, B0 = 1.0, 1.5    # 解決する確率 = 1/(1+exp(-(A0 + B0×(解く力−難しさ))))
TAU0 = 1.0           # 回しやすさの中心（この難しさを超えると手を付けずに回す）
SPEC_SKILL = 1.5     # 回された件を受ける担当の解く力
SKILL_SD = 0.5
TAU_SD = 0.6
Q_PASS = 0.5         # 手を付けて解けなかったとき、回す確率（回さなければ解決しないまま閉じる）
REPS = 400
REPS_GRID = 200
RULES = ["①最初に受けた担当\n（最後の結果）", "②最後に持っていた担当", "③回した担当と\n受けた担当で半分ずつ", "④最初に受けた担当\n（自分で解決だけ）"]
RULES1 = ["①最初に受けた担当（最後の結果）", "②最後に持っていた担当", "③回した担当と受けた担当で半分ずつ", "④最初に受けた担当（自分で解決だけ）"]


def presolve(skill, d):
    return 1 / (1 + np.exp(-(A0 + B0 * (skill - d))))


def true_rate(skill, n=200001):
    """全部の問い合わせを1人で手を付けたときの解決率（難しさは標準正規）。作成者が置いた「本当の解く力」の物差し"""
    d = np.linspace(-5, 5, n)
    w = np.exp(-d ** 2 / 2); w /= w.sum()
    return float((presolve(skill, d) * w).sum())


def one_year(rng, skill, tau, q=Q_PASS, n=N_TICKET):
    """1年分の記録。skill・tau は A〜H の8人分"""
    first = rng.integers(0, 8, n)
    d = rng.normal(0, 1, n)
    s = skill[first]
    pass_now = d > tau[first]
    attempt = ~pass_now
    ok1 = attempt & (rng.random(n) < presolve(s, d))
    pass_after = attempt & ~ok1 & (rng.random(n) < q)
    passed = pass_now | pass_after
    spec = 8 + rng.integers(0, 2, n)
    ok2 = passed & (rng.random(n) < presolve(SPEC_SKILL, d))
    resolved = ok1 | ok2
    last = np.where(passed, spec, first)
    return {"first": first, "d": d, "pass_now": pass_now, "attempt": attempt, "ok1": ok1, "passed": passed,
            "spec": spec, "ok2": ok2, "resolved": resolved, "last": last}


def rates(r):
    """10人分の4つの数え方の解決率（％）と件数。数えられない担当は NaN"""
    out = np.full((4, 10), np.nan)
    cnt = np.zeros((4, 10))
    res = r["resolved"].astype(float)
    # ①
    den = np.bincount(r["first"], minlength=10); num = np.bincount(r["first"], weights=res, minlength=10)
    out[0] = np.where(den > 0, num / np.maximum(den, 1) * 100, np.nan); cnt[0] = den
    # ②
    den = np.bincount(r["last"], minlength=10); num = np.bincount(r["last"], weights=res, minlength=10)
    out[1] = np.where(den > 0, num / np.maximum(den, 1) * 100, np.nan); cnt[1] = den
    # ③ 回された件は、回した担当と受けた担当で半分ずつ（件数も解決も）
    w = np.where(r["passed"], 0.5, 1.0)
    den = np.bincount(r["first"], weights=w, minlength=10) + np.bincount(r["spec"][r["passed"]], minlength=10) * 0.5
    num = np.bincount(r["first"], weights=w * res, minlength=10) + np.bincount(r["spec"][r["passed"]], weights=0.5 * res[r["passed"]], minlength=10)
    out[2] = np.where(den > 0, num / np.maximum(den, 1e-9) * 100, np.nan); cnt[2] = den
    # ④
    den = np.bincount(r["first"], minlength=10); num = np.bincount(r["first"], weights=r["ok1"].astype(float), minlength=10)
    out[3] = np.where(den > 0, num / np.maximum(den, 1) * 100, np.nan); cnt[3] = den
    return out, cnt


def rank_corr(x, y):
    rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def evaluate(rng, reps, skill_sd=SKILL_SD, tau_sd=TAU_SD, q=Q_PASS):
    """解く力と回しやすさの組み合わせを毎回でたらめに作り直す"""
    rc = np.zeros((reps, 4)); top = np.zeros((reps, 4)); passer_rank = np.zeros((reps, 4))
    spec_vs_first = np.zeros((reps, 2)); corr_tau = np.zeros((reps, 4))
    for k in range(reps):
        skill = skill_sd * rng.permutation(Z8)
        tau = TAU0 + tau_sd * rng.permutation(Z8)
        r = one_year(rng, skill, tau, q)
        rt, _ = rates(r)
        for j in range(4):
            v = rt[j, :8]
            rc[k, j] = rank_corr(v, skill)
            corr_tau[k, j] = rank_corr(v, -tau)            # 回しやすいほど高いなら正
            top[k, j] = float(np.argmax(v) == np.argmax(skill))
            # いちばん回しやすい担当（tau が最小）の順位（1が最上位）
            passer_rank[k, j] = 1 + int(np.sum(v > v[np.argmin(tau)]))
        spec_vs_first[k, 0] = np.nanmean(rt[1, 8:]) - np.nanmean(rt[1, :8])
        spec_vs_first[k, 1] = np.nanmean(rt[2, 8:]) - np.nanmean(rt[2, :8])
    return {"rank_corr_skill": rc.mean(0), "rank_corr_passing": corr_tau.mean(0), "top_hit": top.mean(0),
            "passer_rank_mean": passer_rank.mean(0), "passer_top_share": (passer_rank == 1).mean(0),
            "spec_minus_first_rule2": float(spec_vs_first[:, 0].mean()), "spec_minus_first_rule3": float(spec_vs_first[:, 1].mean())}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 基本の組み合わせ（作成者が乱数で1つ決めたもの）
    skill = SKILL_SD * rng.permutation(Z8)
    tau = TAU0 + TAU_SD * rng.permutation(Z8)
    truth = np.array([true_rate(s) for s in skill] + [true_rate(SPEC_SKILL)] * 2) * 100
    # 同じ組み合わせで1年分を REPS 回作り直して平均
    acc = np.zeros((4, 10)); pass_share = np.zeros(10); attempt_share = np.zeros(10); dmean = np.zeros((2, 10))
    rc_fixed = np.zeros((REPS, 4))
    rank_fixed = np.zeros((REPS, 4, 10))
    for k in range(REPS):
        r = one_year(rng, skill, tau)
        rt, cnt = rates(r)
        acc += rt
        pass_share[:8] += np.bincount(r["first"], weights=r["passed"].astype(float), minlength=10)[:8] / np.bincount(r["first"], minlength=10)[:8]
        dmean[0] += np.bincount(r["last"], weights=r["d"], minlength=10) / np.bincount(r["last"], minlength=10)
        if k == 0:
            yr = pd.DataFrame({"ticket": np.arange(1, N_TICKET + 1), "first": [NAMES[i] for i in r["first"]],
                               "difficulty": np.round(r["d"], 3), "passed_without_try": r["pass_now"].astype(int),
                               "tried_and_solved": r["ok1"].astype(int), "passed": r["passed"].astype(int),
                               "passed_to": [NAMES[i] if p else "" for i, p in zip(r["spec"], r["passed"])],
                               "resolved": r["resolved"].astype(int), "last": [NAMES[i] for i in r["last"]]})
            yr.to_csv(DATA / "one_year.csv", index=False)
            one_rates = rt
        for j in range(4):
            rc_fixed[k, j] = rank_corr(rt[j, :8], skill)
            v = np.where(np.isnan(rt[j]), -1, rt[j])
            rank_fixed[k, j] = 1 + np.array([np.sum(v > v[i]) for i in range(10)])
    acc /= REPS; pass_share /= REPS; dmean /= REPS
    true_rank = 1 + np.array([np.sum(truth[:8] > truth[i]) for i in range(8)])
    tab = pd.DataFrame({"agent": NAMES, "skill": np.round(np.append(skill, [SPEC_SKILL] * 2), 3),
                        "pass_threshold": np.append(np.round(tau, 3), [np.nan, np.nan]),
                        "true_rate_pct": np.round(truth, 2),
                        "true_rank_first8": np.append(true_rank, [0, 0]),
                        "passed_share_pct": np.append(np.round(pass_share[:8] * 100, 2), [np.nan, np.nan]),
                        "mean_difficulty_last": np.round(dmean[0], 3)})
    for j, key in enumerate(["r1_first_final", "r2_last", "r3_half", "r4_first_self"]):
        tab[key + "_pct"] = np.round(acc[j], 2)
        v = acc[j].copy()
        tab[key + "_rank_first8"] = np.append(1 + np.array([np.sum(v[:8] > v[i]) for i in range(8)]), [0, 0])
    tab.to_csv(RES / "agents_base.csv", index=False)

    base = {"rank_corr_fixed_mean": [round(float(x), 3) for x in rc_fixed.mean(0)],
            "true_top": NAMES[int(np.argmax(truth[:8]))], "most_passing": NAMES[int(np.argmin(tau))],
            "least_passing": NAMES[int(np.argmax(tau))],
            "top_by_rule": [NAMES[int(np.nanargmax(acc[j, :8]))] for j in range(4)],
            "top10_by_rule": [NAMES[int(np.nanargmax(acc[j]))] for j in range(4)],
            "most_passing_rank_by_rule": [int(tab.loc[int(np.argmin(tau)), k]) for k in
                                          ["r1_first_final_rank_first8", "r2_last_rank_first8", "r3_half_rank_first8", "r4_first_self_rank_first8"]],
            "true_top_rank_by_rule": [int(tab.loc[int(np.argmax(truth[:8])), k]) for k in
                                      ["r1_first_final_rank_first8", "r2_last_rank_first8", "r3_half_rank_first8", "r4_first_self_rank_first8"]],
            "spec_rate_rule2": round(float(acc[1, 8:].mean()), 2), "first_rate_rule2_mean": round(float(acc[1, :8].mean()), 2),
            "spec_rate_rule3": round(float(acc[2, 8:].mean()), 2), "first_rate_rule3_mean": round(float(acc[2, :8].mean()), 2),
            "spec_true_rate": round(float(truth[8]), 2),
            "first_true_rate_range": [round(float(truth[:8].min()), 2), round(float(truth[:8].max()), 2)],
            "spread_by_rule_first8": [[round(float(acc[j, :8].min()), 2), round(float(acc[j, :8].max()), 2)] for j in range(4)],
            "overall_resolved_pct": None,
            "one_year_rates": [[None if np.isnan(x) else round(float(x), 2) for x in row] for row in one_rates]}
    rr = one_year(np.random.default_rng(SEED + 9), skill, tau)
    base["overall_resolved_pct"] = round(float(rr["resolved"].mean()) * 100, 2)
    base["overall_passed_pct"] = round(float(rr["passed"].mean()) * 100, 2)

    rnd = evaluate(np.random.default_rng(SEED + 1), REPS)
    rand = {"rank_corr_skill": [round(float(x), 3) for x in rnd["rank_corr_skill"]],
            "rank_corr_passing": [round(float(x), 3) for x in rnd["rank_corr_passing"]],
            "top_hit_pct": [round(float(x) * 100, 2) for x in rnd["top_hit"]],
            "passer_rank_mean": [round(float(x), 2) for x in rnd["passer_rank_mean"]],
            "passer_top_pct": [round(float(x) * 100, 2) for x in rnd["passer_top_share"]],
            "spec_minus_first_rule2_pt": round(rnd["spec_minus_first_rule2"], 2),
            "spec_minus_first_rule3_pt": round(rnd["spec_minus_first_rule3"], 2)}

    rows = []
    g = 0
    for tsd in [0.3, 0.6, 1.0]:
        for ssd in [0.25, 0.5, 0.8]:
            for q in [0.2, 0.5, 0.8]:
                g += 1
                e = evaluate(np.random.default_rng(SEED + 100 + g), REPS_GRID, skill_sd=ssd, tau_sd=tsd, q=q)
                row = {"tau_sd": tsd, "skill_sd": ssd, "q_pass": q}
                for j in range(4):
                    row[f"r{j+1}_rank_corr_skill"] = round(float(e["rank_corr_skill"][j]), 3)
                    row[f"r{j+1}_rank_corr_passing"] = round(float(e["rank_corr_passing"][j]), 3)
                    row[f"r{j+1}_top_hit_pct"] = round(float(e["top_hit"][j]) * 100, 2)
                    row[f"r{j+1}_passer_top_pct"] = round(float(e["passer_top_share"][j]) * 100, 2)
                row["spec_minus_first_rule2_pt"] = round(e["spec_minus_first_rule2"], 2)
                rows.append(row)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    gs = {"n_settings": len(grid)}
    for j in range(4):
        c = grid[f"r{j+1}_rank_corr_skill"]; p = grid[f"r{j+1}_rank_corr_passing"]
        gs[f"r{j+1}_rank_corr_skill_range"] = [float(c.min()), float(c.max())]
        gs[f"r{j+1}_rank_corr_passing_range"] = [float(p.min()), float(p.max())]
        gs[f"r{j+1}_top_hit_range"] = [float(grid[f"r{j+1}_top_hit_pct"].min()), float(grid[f"r{j+1}_top_hit_pct"].max())]
    best = grid[[f"r{j+1}_rank_corr_skill" for j in range(4)]].values.argmax(1)
    gs["n_best_rule"] = {RULES1[j]: int((best == j).sum()) for j in range(4)}
    gs["n_r1_passing_positive"] = int((grid["r1_rank_corr_passing"] > 0).sum())
    gs["n_r2_passing_positive"] = int((grid["r2_rank_corr_passing"] > 0).sum())
    gs["n_r4_passing_negative"] = int((grid["r4_rank_corr_passing"] < 0).sum())
    gs["n_spec_lower_rule2"] = int((grid["spec_minus_first_rule2_pt"] < 0).sum())
    gs["spec_minus_first_rule2_range"] = [float(grid["spec_minus_first_rule2_pt"].min()), float(grid["spec_minus_first_rule2_pt"].max())]

    out = {"settings": {"n_ticket_per_year": N_TICKET, "first_line": FIRST, "specialists": SPEC, "a0": A0, "b0": B0,
                        "tau_center": TAU0, "tau_sd": TAU_SD, "skill_sd": SKILL_SD, "spec_skill": SPEC_SKILL, "q_pass": Q_PASS,
                        "z8": Z8.tolist(), "reps": REPS, "reps_grid": REPS_GRID, "seed": SEED},
           "rules": RULES1, "base_fixed_pairing": base, "random_pairing": rand, "grid_summary": gs}
    with open(RES / "a1192_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：基本の組み合わせでの担当ごとの解決率
    order = list(np.argsort(-truth[:8])) + [8, 9]
    fig, axs = plt.subplots(1, 4, figsize=(12, 4.6), sharey=True)
    passer = int(np.argmin(tau))
    for j, ax in enumerate(axs):
        v = acc[j, order]
        cols = [ORANGE if i == passer else (GREEN if i >= 8 else BLUE) for i in order]
        ys = np.arange(len(order))[::-1]
        ax.barh(ys, np.nan_to_num(v), color=cols)
        for y, vv in zip(ys, v):
            ax.text((0 if np.isnan(vv) else vv) + 1, y, "数えない" if np.isnan(vv) else f"{vv:.2f}", va="center", fontsize=7.5)
        ax.set_xlim(0, 115); ax.set_title(RULES[j], fontsize=10)
        ax.set_xlabel("解決率（%）")
    axs[0].set_yticks(np.arange(len(order))[::-1])
    axs[0].set_yticklabels([f"{NAMES[i]}（本当{truth[i]:.2f}%）" for i in order], fontsize=8.5)
    fig.suptitle("数え方で担当の解決率の順が入れかわる（上ほど本当の解く力が高い。橙はいちばん回しやすい担当、緑は回された件を受ける担当）", fontsize=10.5)
    fig.tight_layout()
    save(fig, "a1192_agents.png", SRC)

    # 図2：本当の解く力・回しやすさとの順位の結びつき（組み合わせをでたらめに作り直した平均）
    fig, ax = plt.subplots(figsize=(8, 4.2))
    xs = np.arange(4); w = 0.38
    v1 = rand["rank_corr_skill"]; v2 = rand["rank_corr_passing"]
    ax.bar(xs - w / 2, v1, w, color=BLUE, label="本当の解く力との順位の結びつき")
    ax.bar(xs + w / 2, v2, w, color=ORANGE, label="回しやすさとの順位の結びつき")
    for x, a, b in zip(xs, v1, v2):
        ax.text(x - w / 2, a + (0.03 if a >= 0 else -0.08), f"{a:.3f}", ha="center", fontsize=8)
        ax.text(x + w / 2, b + (0.03 if b >= 0 else -0.08), f"{b:.3f}", ha="center", fontsize=8)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xs); ax.set_xticklabels(RULES, fontsize=8.5)
    ax.set_ylim(-1, 1); ax.set_ylabel("順位相関（初めに受ける8人）")
    ax.set_title(f"数え方ごとの順位の結びつき（組み合わせを{REPS}回作り直した平均）", fontsize=11.5)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    save(fig, "a1192_corr.png", SRC)

    # 図3：27通り
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, key, ttl in zip(axs, ["rank_corr_skill", "rank_corr_passing"], ["本当の解く力との順位相関", "回しやすさとの順位相関"]):
        for j, c in enumerate([GRAY, BLUE, GREEN, ORANGE]):
            ax.scatter(np.full(len(grid), j) + np.linspace(-0.25, 0.25, len(grid)), grid[f"r{j+1}_{key}"], s=12, color=c)
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_xticks(range(4)); ax.set_xticklabels(RULES, fontsize=7.5)
        ax.set_ylim(-1, 1); ax.set_title(ttl, fontsize=11)
    axs[0].set_ylabel("順位相関（初めに受ける8人、各200回の平均）")
    fig.suptitle("置き方27通り：回しやすさとの結びつきは、①②③で正・④で負（27通りとも）", fontsize=12)
    fig.tight_layout()
    save(fig, "a1192_robust.png", SRC)
    print(tab.to_string())
    print(json.dumps(base, ensure_ascii=False)[:1500]); print(json.dumps(rand, ensure_ascii=False)); print(json.dumps(gs, ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
