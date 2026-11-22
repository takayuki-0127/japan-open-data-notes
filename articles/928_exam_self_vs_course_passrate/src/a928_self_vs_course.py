"""928 「独学の人の合格率」と「講座の人の合格率」は比べられるのか？（架空のデータ）

架空の大人向けの資格試験。受験を考えた人ごとに「もとの力」を置き、講座を選ぶかどうかが、もとの力とどれだけ結びつくか、
講座の本当の効き目（点の上乗せ）、講座を途中でやめる人を合格率の分母から外すかを作成者が置く。
全員が講座を受けたときと全員が独学のときの合格率の差（本当の差）と、見かけの合格率の差を比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 928
SRC = "架空の資格試験の受験者（作成者が乱数で作成、seed 928）"
N = 20000
REPS = 40
MU, SD, NOISE, PASS = 55.0, 12.0, 6.0, 65.0
COURSE_SHARE = 0.4
BASE = {"sel": 0.5, "effect": 3.0, "drop": 0.8, "pre_noise": 0.7}


def logistic(x):
    return 1 / (1 + np.exp(-x))


_CACHE = {}


def intercept_for(share, slope_, z):
    """講座を選ぶ人がおよそ share になる切片（二分法、z は標準正規の見本）"""
    if (share, slope_) in _CACHE:
        return _CACHE[(share, slope_)]
    lo, hi = -10.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if logistic(mid + slope_ * z).mean() < share:
            lo = mid
        else:
            hi = mid
    _CACHE[(share, slope_)] = mid
    return mid


ZREF = np.random.default_rng(1).standard_normal(200000)


def world(rng, sel=BASE["sel"], effect=BASE["effect"], drop=BASE["drop"], pre_noise=BASE["pre_noise"], n=N):
    z = rng.standard_normal(n)
    eps = NOISE * rng.standard_normal(n)
    s_self = MU + SD * z + eps
    s_course = s_self + effect
    a = intercept_for(COURSE_SHARE, sel, ZREF)
    course = rng.random(n) < logistic(a + sel * z)
    # 講座を途中でやめる確率：力の低い人ほどやめやすい（drop=0 なら全員同じ15%）
    b = intercept_for(0.15, -drop, ZREF)
    quit_ = course & (rng.random(n) < logistic(b - drop * z))
    # 途中でやめた人は、それまでの分として効き目の半分を受けて受験する
    score = np.where(course & ~quit_, s_course, np.where(quit_, s_self + effect / 2, s_self))
    pre = z + pre_noise * rng.standard_normal(n)   # 最初の練習テスト（もとの力の目安）
    return pd.DataFrame({"z": z, "course": course, "quit": quit_, "score": score, "pre": pre,
                         "pass": score >= PASS, "pass_all_self": s_self >= PASS, "pass_all_course": s_course >= PASS})


def measures(d):
    fin = d[d.course & ~d.quit]
    slf = d[~d.course]
    course_rate = fin["pass"].mean()             # 講座の発表：修了して受験した人の合格率
    course_all_rate = d[d.course]["pass"].mean()  # 途中でやめた人も入れた合格率
    self_rate = slf["pass"].mean()
    true = d.pass_all_course.mean() - d.pass_all_self.mean()
    # 練習テストの5つの段に分けて、段ごとの差を全体の人数で重み付け（修了者で比べる）
    q = pd.qcut(d.pre, 5, labels=False)
    diffs, w = [], []
    for k in range(5):
        m = q == k
        a = d[m & d.course & ~d.quit]["pass"].mean()
        b = d[m & ~d.course]["pass"].mean()
        diffs.append(a - b); w.append(m.mean())
    strat = float(np.nansum(np.array(diffs) * np.array(w)) / np.sum(w))
    return {"course_rate": course_rate, "course_all_rate": course_all_rate, "self_rate": self_rate,
            "naive_diff": course_rate - self_rate, "naive_diff_incl_quit": course_all_rate - self_rate,
            "true_diff": true, "strat_diff": strat,
            "course_mean_z": d[d.course].z.mean(), "self_mean_z": slf.z.mean(),
            "quit_share": d[d.course].quit.mean(), "rate_all_self": d.pass_all_self.mean(),
            "rate_all_course": d.pass_all_course.mean()}


def cell(key, **kw):
    rows = [measures(world(np.random.default_rng([SEED, key, r]), **kw)) for r in range(REPS)]
    t = pd.DataFrame(rows)
    res = {k: round(float(t[k].mean()) * (100 if k not in ("course_mean_z", "self_mean_z") else 1), 2) for k in t}
    res["naive_diff_p10"] = round(float(t.naive_diff.quantile(.1)) * 100, 2)
    res["naive_diff_p90"] = round(float(t.naive_diff.quantile(.9)) * 100, 2)
    res.update(kw)
    return res


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    d = world(rng)
    one = d.sample(3000, random_state=SEED).sort_index()
    out_df = pd.DataFrame({"person_id": one.index + 1, "ability_z": one.z.round(3), "course": one.course.astype(int),
                           "quit": one.quit.astype(int), "pretest": one.pre.round(3), "score": one.score.round(1),
                           "passed": one["pass"].astype(int)})
    out_df.to_csv(DATA / "candidates.csv", index=False)

    # 確かめの格子：選び方 × 本当の効き目 × 途中でやめる人の偏り（練習テストの誤差は基本）
    rows = []
    key = 1
    for sel in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        for eff in [0.0, 3.0, 6.0]:
            for drop in [0.0, 0.8]:
                rows.append(cell(key, sel=sel, effect=eff, drop=drop, pre_noise=BASE["pre_noise"])); key += 1
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "robustness.csv", index=False)
    base = grid[(grid.sel == BASE["sel"]) & (grid.effect == BASE["effect"]) & (grid["drop"] == BASE["drop"])].iloc[0].to_dict()

    # 練習テストの誤差を変えると、段に分けた比べ方はどこまで戻るか（選び方1.0・効き目3・やめる偏りなし）
    pre_rows = []
    for j, pn in enumerate([0.0, 0.35, 0.7, 1.4]):
        r = cell(200 + j, sel=1.0, effect=3.0, drop=0.0, pre_noise=pn)
        pre_rows.append(r)
    pre_df = pd.DataFrame(pre_rows)
    pre_df.to_csv(RES / "pretest_noise.csv", index=False)

    # 練習テストの段ごとの合格率（基本の置き方・1回分）
    q = pd.qcut(d.pre, 5, labels=False)
    strata = []
    for k in range(5):
        m = q == k
        strata.append({"stratum": k + 1, "course_finished_rate": round(float(d[m & d.course & ~d.quit]["pass"].mean()) * 100, 1),
                       "self_rate": round(float(d[m & ~d.course]["pass"].mean()) * 100, 1),
                       "course_share": round(float(d[m].course.mean()) * 100, 1)})
    strata = pd.DataFrame(strata)
    strata.to_csv(RES / "strata_one_draw.csv", index=False)

    flips = grid[(grid.effect > 0) & (grid.naive_diff < 0)]
    zero = grid[grid.effect == 0]
    out = {"settings": {"n_people": N, "reps": REPS, "ability_mean": MU, "ability_sd": SD, "noise_sd": NOISE,
                        "pass_line": PASS, "course_share": COURSE_SHARE, "quit_share": 0.15, **{f"base_{k}": v for k, v in BASE.items()}},
           "base": base, "grid": grid.to_dict("records"), "pretest_noise": pre_df.to_dict("records"),
           "strata_one_draw": strata.to_dict("records"),
           "summary": {"naive_minus_true_range": [round(float((grid.naive_diff - grid.true_diff).min()), 2),
                                                  round(float((grid.naive_diff - grid.true_diff).max()), 2)],
                       "naive_when_effect0_range": [float(zero.naive_diff.min()), float(zero.naive_diff.max())],
                       "naive_when_effect3_range": [float(grid[grid.effect == 3].naive_diff.min()),
                                                    float(grid[grid.effect == 3].naive_diff.max())],
                       "naive_when_effect6_range": [float(grid[grid.effect == 6].naive_diff.min()),
                                                    float(grid[grid.effect == 6].naive_diff.max())],
                       "true_diff_by_effect": {str(e): [float(v.true_diff.min()), float(v.true_diff.max())]
                                               for e, v in grid.groupby("effect")},
                       "strat_when_effect0_range": [float(zero.strat_diff.min()), float(zero.strat_diff.max())],
                       "n_cells": int(len(grid)), "n_cells_effect_pos": int((grid.effect > 0).sum()),
                       "n_cells_effect_pos_naive_negative": int(len(flips)),
                       "strat_minus_true_range": [round(float((grid.strat_diff - grid.true_diff).min()), 2),
                                                  round(float((grid.strat_diff - grid.true_diff).max()), 2)],
                       "quit_effect_range": [round(float((grid.naive_diff - grid.naive_diff_incl_quit).min()), 2),
                                             round(float((grid.naive_diff - grid.naive_diff_incl_quit).max()), 2)]}}
    json.dump(out, open(RES / "a928_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：基本の置き方での合格率（見かけと、全員がそうしたとき）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    labs = ["講座（修了して受験）", "独学", "全員が講座なら", "全員が独学なら"]
    vals = [base["course_rate"], base["self_rate"], base["rate_all_course"], base["rate_all_self"]]
    cols = [ORANGE, BLUE, LIGHT, LIGHT]
    ax.barh(labs[::-1], vals[::-1], color=cols[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_xlim(0, max(vals) * 1.25); ax.set_xlabel("合格率（%、40回の平均）")
    ax.set_title(f"見かけの差は{base['naive_diff']:.1f}ポイント、本当の差は{base['true_diff']:.1f}ポイント（基本の置き方）")
    save(fig, "a928_rates.png", SRC)

    # 図2：選び方ごとの見かけの差と本当の差
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 4.2), sharey=True)
    for ax, eff in zip(axes, [0.0, 3.0, 6.0]):
        g = grid[grid.effect == eff]
        for drop, col, lab in [(0.0, BLUE, "やめる人に偏りなし"), (0.8, ORANGE, "力の低い人ほどやめる")]:
            gg = g[g["drop"] == drop]
            ax.plot(gg.sel, gg.naive_diff, marker="o", color=col, label="見かけの差：" + lab)
        ax.plot(g[g["drop"] == 0].sel, g[g["drop"] == 0].strat_diff, marker="s", color=GREEN, ls=":",
                label="練習テストの段に分けた差（偏りなし）")
        ax.plot(g[g["drop"] == 0].sel, g[g["drop"] == 0].true_diff, color=INK, lw=2, ls="--", label="本当の差")
        ax.axhline(0, color=GRAY, lw=.8)
        ax.set_title(f"本当の効き目 +{eff:.0f}点", fontsize=11)
        ax.set_xticks([-1, -0.5, 0, 0.5, 1])
    axes[0].set_ylabel("講座−独学の合格率の差（ポイント）")
    axes[1].set_xlabel("講座の選び方（負：力の低い人ほど講座を選ぶ、正：力の高い人ほど選ぶ）")
    axes[0].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(1.6, -0.17), ncol=2)
    fig.suptitle("見かけの差は、誰が講座を選ぶかで本当の差の上にも下にもずれる（各40回の平均）", fontsize=13, y=1.03)
    save(fig, "a928_diff_by_selection.png", SRC, y=-0.13)

    # 図3：練習テストの段ごとの合格率（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(5)
    ax.bar(x - 0.2, strata.course_finished_rate, 0.4, color=ORANGE, label="講座（修了して受験）")
    ax.bar(x + 0.2, strata.self_rate, 0.4, color=BLUE, label="独学")
    ax.set_xticks(x, [f"{k}段目" for k in range(1, 6)])
    ax.set_xlabel("最初の練習テストの点で5つに分けた段（1段目が低い）")
    ax.set_ylabel("合格率（%）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"同じ段の中でも差は残る（本当の差は{base['true_diff']:.1f}ポイント、基本の置き方・1回分）", fontsize=12)
    save(fig, "a928_strata.png", SRC)
    print(json.dumps(out["base"], ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
