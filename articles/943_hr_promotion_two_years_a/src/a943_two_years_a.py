"""943 昇格の基準を「2年連続でA」にすると、誰が残るのか？（架空のデータ）

架空の会社の1,000人（上司100人、1チーム10人で始まる）。人ごとに「本当の実力」（3年間変わらない）を置き、
上司ごとに「甘さ」（点を上に付ける癖）を置く。年の評価点＝本当の実力＋上司の甘さ＋その年のぶれ。
毎年、会社全体で点の上位20%を「A」とする。毎年30%の人は別の上司の下に移る。
「2年連続でA」の人は誰か（本当の実力・上司の甘さ・上司が変わったか）を、ほかの決め方と比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 943
SRC = "架空の会社の評価（作成者が乱数で作成、seed 943）"
N_BOSS, TEAM = 100, 10
N = N_BOSS * TEAM
BASE = dict(sl=0.4, se=0.7, pc=0.3)
RULES = ["1年目にA", "2年連続でA", "2年の平均点の上位（同じ人数）", "上司ごとにそろえて2年連続でA", "3年連続でA"]


def one_company(rng, sl, se, pc, years=3):
    a = rng.standard_normal(N)
    len_b = rng.normal(0, sl, N_BOSS) if sl > 0 else np.zeros(N_BOSS)
    boss = np.zeros((N, years), int)
    boss[:, 0] = np.repeat(np.arange(N_BOSS), TEAM)
    for y in range(1, years):
        mv = rng.random(N) < pc
        new = (boss[:, y - 1] + rng.integers(1, N_BOSS, N)) % N_BOSS   # 別の上司
        boss[:, y] = np.where(mv, new, boss[:, y - 1])
    score = a[:, None] + len_b[boss] + rng.normal(0, se, (N, years))
    # 上司ごとにそろえた点：その年のその上司の下の人の平均を引く
    adj = np.empty_like(score)
    for y in range(years):
        s = pd.Series(score[:, y]).groupby(boss[:, y]).transform("mean").values
        adj[:, y] = score[:, y] - s
    return a, len_b, boss, score, adj


def top(x, q=0.2):
    return x >= np.quantile(x, 1 - q)


def rules(a, len_b, boss, score, adj):
    A = np.column_stack([top(score[:, y]) for y in range(score.shape[1])])
    Aadj = np.column_stack([top(adj[:, y]) for y in range(adj.shape[1])])
    two = A[:, 0] & A[:, 1]
    k = int(two.sum())
    avg = np.zeros(N, bool)
    if k > 0:
        avg[np.argsort(-(score[:, 0] + score[:, 1]))[:k]] = True
    return {RULES[0]: A[:, 0], RULES[1]: two, RULES[2]: avg, RULES[3]: Aadj[:, 0] & Aadj[:, 1],
            RULES[4]: A[:, 0] & A[:, 1] & A[:, 2]}


def measure(rng, sl, se, pc, reps):
    acc = {r: dict(n=0, true_top20=0, true_mean=0.0, lenient_both=0, moved=0) for r in RULES}
    tot = dict(n=0, true_top10=0, lenient_both=0, moved=0)
    rec = {r: 0 for r in RULES}
    for _ in range(reps):
        a, len_b, boss, score, adj = one_company(rng, sl, se, pc)
        tt20, tt10 = top(a, 0.2), top(a, 0.1)
        lenient = len_b >= np.quantile(len_b, 0.75) if sl > 0 else np.zeros(N_BOSS, bool)
        lb = lenient[boss[:, 0]] & lenient[boss[:, 1]]
        mv = boss[:, 0] != boss[:, 1]
        tot["n"] += N; tot["true_top10"] += tt10.sum(); tot["lenient_both"] += lb.sum(); tot["moved"] += mv.sum()
        for r, m in rules(a, len_b, boss, score, adj).items():
            acc[r]["n"] += m.sum(); acc[r]["true_top20"] += (m & tt20).sum(); acc[r]["true_mean"] += a[m].sum()
            acc[r]["lenient_both"] += (m & lb).sum(); acc[r]["moved"] += (m & mv).sum()
            rec[r] += (m & tt10).sum()
    rows = []
    for r in RULES:
        c, n = acc[r], max(acc[r]["n"], 1)
        rows.append({"rule": r, "kept_pct": round(100 * c["n"] / tot["n"], 1),
                     "true_top20_among_kept_pct": round(100 * c["true_top20"] / n, 1),
                     "true_mean_z": round(c["true_mean"] / n, 2),
                     "true_top10_kept_pct": round(100 * rec[r] / tot["true_top10"], 1),
                     "lenient_both_among_kept_pct": round(100 * c["lenient_both"] / n, 1),
                     "moved_among_kept_pct": round(100 * c["moved"] / n, 1)})
    base = {"lenient_both_all_pct": round(100 * tot["lenient_both"] / tot["n"], 1),
            "moved_all_pct": round(100 * tot["moved"] / tot["n"], 1)}
    return rows, base


def main():
    rng = np.random.default_rng(SEED)

    # 0) 1社分を data に置く
    a, len_b, boss, score, adj = one_company(rng, **BASE)
    rl = rules(a, len_b, boss, score, adj)
    df = pd.DataFrame({"staff_id": np.arange(1, N + 1), "true_ability": a,
                       "boss_y1": boss[:, 0] + 1, "boss_y2": boss[:, 1] + 1, "boss_y3": boss[:, 2] + 1,
                       "leniency_y1": len_b[boss[:, 0]], "leniency_y2": len_b[boss[:, 1]],
                       "score_y1": score[:, 0], "score_y2": score[:, 1], "score_y3": score[:, 2],
                       "A_y1": top(score[:, 0]).astype(int), "A_y2": top(score[:, 1]).astype(int),
                       "A_y3": top(score[:, 2]).astype(int), "two_years_A": rl[RULES[1]].astype(int)})
    df.to_csv(DATA / "company_1000.csv", index=False, float_format="%.3f")
    one = {"two_years_A_count": int(rl[RULES[1]].sum()), "three_years_A_count": int(rl[RULES[4]].sum()),
           "two_years_A_true_top20": int((rl[RULES[1]] & top(a)).sum())}

    # 1) 基本の置き方（1,000人の会社を300回）
    base_rows, base_all = measure(np.random.default_rng(SEED * 10), **BASE, reps=300)
    pd.DataFrame(base_rows).to_csv(RES / "base_rules.csv", index=False)

    # 2) 確かめ：上司の甘さ・年のぶれ・上司が変わる割合（27通り、各100回）
    grid = []
    for sl in [0.0, 0.4, 0.8]:
        for se in [0.4, 0.7, 1.0]:
            for pc in [0.0, 0.3, 0.6]:
                rr, ba = measure(np.random.default_rng(SEED * 1000 + int(sl * 10) * 100 + int(se * 10) * 10 + int(pc * 10)),
                                 sl, se, pc, reps=100)
                d = {x["rule"]: x for x in rr}
                two, avg, adjr = d[RULES[1]], d[RULES[2]], d[RULES[3]]
                grid.append({"leniency_sd": sl, "noise_sd": se, "move_rate": pc,
                             "two_kept_pct": two["kept_pct"],
                             "two_true_top20_pct": two["true_top20_among_kept_pct"],
                             "avg_true_top20_pct": avg["true_top20_among_kept_pct"],
                             "adj_true_top20_pct": adjr["true_top20_among_kept_pct"],
                             "two_lenient_both_pct": two["lenient_both_among_kept_pct"],
                             "adj_lenient_both_pct": adjr["lenient_both_among_kept_pct"],
                             "all_lenient_both_pct": ba["lenient_both_all_pct"],
                             "two_moved_pct": two["moved_among_kept_pct"],
                             "all_moved_pct": ba["moved_all_pct"]})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid_27.csv", index=False)
    gl = g[g.leniency_sd > 0]
    gm = g[(g.leniency_sd > 0) & (g.move_rate > 0)]
    g0 = g[g.leniency_sd == 0]
    gsum = {"two_kept_range": [float(g.two_kept_pct.min()), float(g.two_kept_pct.max())],
            "two_true_top20_range": [float(g.two_true_top20_pct.min()), float(g.two_true_top20_pct.max())],
            "lenient_ratio_range_sl_pos": [round(float((gl.two_lenient_both_pct / gl.all_lenient_both_pct).min()), 2),
                                           round(float((gl.two_lenient_both_pct / gl.all_lenient_both_pct).max()), 2)],
            "moved_ratio_range_sl_pos_pc_pos": [round(float((gm.two_moved_pct / gm.all_moved_pct).min()), 2),
                                                round(float((gm.two_moved_pct / gm.all_moved_pct).max()), 2)],
            "moved_ratio_range_sl0_pc_pos": [round(float((g0[g0.move_rate > 0].two_moved_pct / g0[g0.move_rate > 0].all_moved_pct).min()), 2),
                                             round(float((g0[g0.move_rate > 0].two_moved_pct / g0[g0.move_rate > 0].all_moved_pct).max()), 2)],
            "n_settings_sl_pos": int(len(gl)),
            "n_two_lenient_above_all": int((gl.two_lenient_both_pct > gl.all_lenient_both_pct).sum()),
            "n_moved_below_all": int((gm.two_moved_pct < gm.all_moved_pct).sum()), "n_settings_moved": int(len(gm)),
            "n_avg_ge_two_precision": int((g.avg_true_top20_pct >= g.two_true_top20_pct).sum()),
            "avg_minus_two_precision_range": [round(float((g.avg_true_top20_pct - g.two_true_top20_pct).min()), 1),
                                              round(float((g.avg_true_top20_pct - g.two_true_top20_pct).max()), 1)],
            "n_adj_gt_two_precision_sl_pos": int((gl.adj_true_top20_pct > gl.two_true_top20_pct).sum()),
            "n_adj_lt_two_precision_sl0": int((g0.adj_true_top20_pct < g0.two_true_top20_pct).sum()),
            "adj_minus_two_precision_sl0_range": [round(float((g0.adj_true_top20_pct - g0.two_true_top20_pct).min()), 1),
                                                  round(float((g0.adj_true_top20_pct - g0.two_true_top20_pct).max()), 1)],
            "n_settings": int(len(g))}

    out = {"base_rules_300reps": base_rows, "base_all_staff": base_all, "one_company": one, "grid_27": gsum}
    json.dump(out, open(RES / "a943_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    b = pd.DataFrame(base_rows)
    # 図1：残った人のうち、両年とも甘い上司の下にいた人・上司が変わった人
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.9), sharey=True)
    yy = np.arange(len(b))[::-1]
    for ax, col, allv, ttl in [(axes[0], "lenient_both_among_kept_pct", base_all["lenient_both_all_pct"], "2年とも甘い上司（上位4分の1）の下"),
                               (axes[1], "moved_among_kept_pct", base_all["moved_all_pct"], "1年目から2年目に上司が変わった")]:
        ax.barh(yy, b[col], color=[GRAY, ORANGE, LIGHT, BLUE, GRAY][:len(b)])
        ax.axvline(allv, color=INK, lw=1, ls="--")
        for i, v in enumerate(b[col]):
            ax.text(v - 0.6, yy[i], f"{v:.1f}%", va="center", ha="right", fontsize=9, color="white")
        ax.set_title(f"{ttl}\n（点線：全員では{allv:.1f}%）", fontsize=11); ax.set_xlabel("残った人のうちの割合（%）")
        ax.set_xlim(0, max(b[col].max(), allv) * 1.3)
    axes[0].set_yticks(yy); axes[0].set_yticklabels(b.rule)
    fig.suptitle("「2年連続でA」に残るのは、甘い上司の下に居続けた人に寄る（1,000人×300回）", fontsize=12, y=1.1)
    save(fig, "a943_who_stays.png", SRC, y=-0.03)

    # 図2：残った人のうち本当の上位20%の割合と、残った人数
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.barh(yy, b.true_top20_among_kept_pct, color=[GRAY, ORANGE, LIGHT, BLUE, GRAY][:len(b)])
    for i, (v, k) in enumerate(zip(b.true_top20_among_kept_pct, b.kept_pct)):
        ax.text(v + 1, yy[i], f"{v:.1f}%（残ったのは全体の{k:.1f}%）", va="center", fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels(b.rule); ax.set_xlim(0, 125)
    ax.set_xlabel("残った人のうち、本当の実力が上位20%だった人の割合（%）")
    ax.set_title("同じ人数なら、2年の平均点で選ぶほうが当たりは少し高い")
    save(fig, "a943_precision.png", SRC)

    # 図3：上司の甘さの大きさ別、両年とも甘い上司の下にいた人の割合（2年連続A／全員）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    sub = g[(g.noise_sd == 0.7) & (g.move_rate == 0.3)]
    x = np.arange(len(sub))
    ax.bar(x - 0.27, sub.all_lenient_both_pct, 0.26, color=GRAY, label="全員")
    ax.bar(x, sub.two_lenient_both_pct, 0.26, color=ORANGE, label="2年連続でA")
    ax.bar(x + 0.27, sub.adj_lenient_both_pct, 0.26, color=BLUE, label="上司ごとにそろえて2年連続でA")
    for i, (u, v, w) in enumerate(zip(sub.all_lenient_both_pct, sub.two_lenient_both_pct, sub.adj_lenient_both_pct)):
        ax.text(i - 0.27, u + 0.6, f"{u:.1f}", ha="center", fontsize=9)
        ax.text(i, v + 0.6, f"{v:.1f}", ha="center", fontsize=9)
        ax.text(i + 0.27, w + 0.6, f"{w:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([("上司の甘さ 0（差なし）" if s == 0 else f"上司の甘さ {s}") for s in sub.leniency_sd])
    ax.set_xlabel("（年のぶれ0.7・上司が変わる割合30%、各100回）", fontsize=9)
    ax.set_ylabel("2年とも甘い上司の下にいた人（%）")
    ax.set_ylim(0, sub.two_lenient_both_pct.max() * 1.35)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("上司の甘さの差が大きいほど、2年連続のAは甘い上司の下に集まる")
    save(fig, "a943_by_leniency.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
