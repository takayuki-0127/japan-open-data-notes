"""926 1回の試験の点は、実力からどれだけ振れるのか？（架空のデータ）

架空の大人向けの社内試験。問題は1,000問の問題の集まり（難しさ・見分ける力を作成者が置く）から
毎回50問を選び、1問2点の100点満点。受ける人ごとに「本当の点」（問題の集まり全体を解いたときの
正答率×100）を置き、1回の点が本当の点からどれだけ振れるかを数える。
振れの元は、①1問ごとの当たり外れ、②どの50問が出るか、③当日の調子、の3つ。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 926
SRC = "架空の社内試験と受ける人（作成者が乱数で作成、seed 926）"
N_POOL, N_ITEM, COND_SD = 1000, 50, 0.2
PASS = 60


def make_pool(rng, n=N_POOL, b_sd=1.0):
    b = rng.normal(0.0, b_sd, n)
    a = rng.uniform(0.7, 1.5, n)
    return a, b


def prob(theta, a, b):
    """theta: (...,1) と a,b: (..., k) → 正答の確率（2パラメータのロジスティック）"""
    return 1.0 / (1.0 + np.exp(-1.7 * a * (theta - b)))


def true_score(theta, a, b):
    th = np.atleast_1d(theta)[:, None]
    return 100 * prob(th, a[None, :], b[None, :]).mean(1)


def theta_for_true(target, a, b):
    lo, hi = -4.0, 4.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if true_score(mid, a, b)[0] < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sit(rng, theta, a, b, n_item=N_ITEM, cond_sd=COND_SD, fixed_form=None):
    """theta: (m,) の人がそれぞれ1回受ける → 点（m,）"""
    m = len(theta)
    if fixed_form is None:
        idx = np.argsort(rng.random((m, len(a))), axis=1)[:, :n_item]
    else:
        idx = np.broadcast_to(fixed_form, (m, n_item))
    th = theta + (rng.normal(0, cond_sd, m) if cond_sd > 0 else 0.0)
    p = prob(th[:, None], a[idx], b[idx])
    return 100 * (rng.random(p.shape) < p).sum(1) / n_item


def r3(x):
    return round(float(x), 3)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    a, b = make_pool(rng)

    # 1) 本当の点 30〜90 の人が、1回の試験を 5,000回受けたら
    levels = [30, 40, 50, 60, 70, 80, 90]
    by_level, hist_keep = [], {}
    for T in levels:
        th = theta_for_true(T, a, b)
        x = sit(rng, np.full(5000, th), a, b)
        d = x - T
        by_level.append({"true_score": T, "theta": r3(th), "mean_obs": r3(x.mean()), "sd": r3(d.std()),
                         "p10": r3(np.quantile(d, .1)), "p90": r3(np.quantile(d, .9)),
                         "share_abs_ge10": r3((np.abs(d) >= 10).mean()),
                         "binom_sd_formula": r3(100 * np.sqrt(T / 100 * (1 - T / 100) / N_ITEM))})
        if T in (40, 60, 80):
            hist_keep[T] = x
    by_level = pd.DataFrame(by_level)
    by_level.to_csv(RES / "swing_by_true_score.csv", index=False)

    # 2) 本当の点60の人で、振れの元を1つずつ足すと
    th60 = theta_for_true(60, a, b)
    form0 = rng.choice(N_POOL, N_ITEM, replace=False)
    T60_form0 = float(100 * prob(th60, a[form0], b[form0]).mean())
    parts = []
    for name, kw in [("①1問ごとの当たり外れだけ（同じ50問）", dict(cond_sd=0, fixed_form=form0)),
                     ("①＋②どの50問が出るか", dict(cond_sd=0)),
                     ("①＋②＋③当日の調子（基本）", dict(cond_sd=COND_SD))]:
        x = sit(rng, np.full(20000, th60), a, b, **kw)
        d = x - 60
        parts.append({"sources": name, "sd": r3(d.std()), "mean_minus_true": r3(d.mean()),
                      "p10": r3(np.quantile(d, .1)), "p90": r3(np.quantile(d, .9))})

    # 3) 1,000人が2回受けたら（data に保存）
    th_pop = rng.normal(0.3, 1.0, 1000)
    T_pop = true_score(th_pop, a, b)
    x1, x2 = sit(rng, th_pop, a, b), sit(rng, th_pop, a, b)
    pop = pd.DataFrame({"person_id": np.arange(1, 1001), "theta": th_pop.round(4), "true_score": T_pop.round(3),
                        "score_1st": x1, "score_2nd": x2})
    pop.to_csv(DATA / "examinees_two_sittings.csv", index=False)
    r12 = float(np.corrcoef(x1, x2)[0, 1])
    sem_emp = float((x1 - T_pop).std())
    sem_formula = float(x1.std() * np.sqrt(1 - r12))
    pass1, pass2, passT = x1 >= PASS, x2 >= PASS, T_pop >= PASS
    near = np.abs(T_pop - PASS) <= 5
    two = {"n": 1000, "corr_1st_2nd": r3(r12), "sd_score": r3(x1.std()), "sd_true": r3(T_pop.std()),
           "sem_empirical": r3(sem_emp), "sem_formula_sd_sqrt_1_minus_r": r3(sem_formula),
           "share_abs_diff_ge10": r3((np.abs(x1 - x2) >= 10).mean()),
           "share_abs_diff_ge20": r3((np.abs(x1 - x2) >= 20).mean()),
           "mean_abs_diff": r3(np.abs(x1 - x2).mean()),
           "pass_line": PASS, "share_pass_flip": r3((pass1 != pass2).mean()),
           "share_pass_wrong_vs_true": r3((pass1 != passT).mean()),
           "near_line_n": int(near.sum()), "near_line_share_pass_flip": r3((pass1 != pass2)[near].mean()),
           "far_line_share_pass_flip": r3((pass1 != pass2)[~near].mean())}

    # 4) 本当の点が 5点・10点ちがう2人で、低い人が同点以上を取る確率
    rev = []
    for gap in [2, 5, 10, 15]:
        lo, hi = theta_for_true(60 - gap / 2, a, b), theta_for_true(60 + gap / 2, a, b)
        xl, xh = sit(rng, np.full(20000, lo), a, b), sit(rng, np.full(20000, hi), a, b)
        rev.append({"true_gap": gap, "p_low_ge_high": r3((xl >= xh).mean()), "p_low_gt_high": r3((xl > xh).mean())})

    # 5) 確かめ：問題数・当日の調子・問題の難しさの散らばりを変えると（本当の点60の人、各5,000回）
    grid = []
    for b_sd in [1.0, 0.5, 1.5]:
        ga, gb = (a, b) if b_sd == 1.0 else make_pool(np.random.default_rng(SEED + int(b_sd * 10)), b_sd=b_sd)
        th = theta_for_true(60, ga, gb)
        for n_item in ([20, 50, 100] if b_sd == 1.0 else [50]):
            for c in ([0.0, 0.2, 0.4] if b_sd == 1.0 else [0.2]):
                x = sit(rng, np.full(5000, th), ga, gb, n_item=n_item, cond_sd=c)
                d = x - 60
                grid.append({"item_difficulty_sd": b_sd, "n_items": n_item, "condition_sd": c, "sd": r3(d.std()),
                             "p10": r3(np.quantile(d, .1)), "p90": r3(np.quantile(d, .9)),
                             "share_abs_ge10": r3((np.abs(d) >= 10).mean()),
                             "binom_sd_formula": r3(100 * np.sqrt(.6 * .4 / n_item))})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness.csv", index=False)
    rng_sd = (float(grid.sd.min()), float(grid.sd.max()))
    rng_w = (float(grid.p10.min()), float(grid.p90.max()))

    out = {"setting": {"pool_items": N_POOL, "items_per_test": N_ITEM, "points_per_item": 100 / N_ITEM,
                       "condition_sd_theta": COND_SD, "pass_line": PASS,
                       "true_score_of_fixed_form_for_true60": r3(T60_form0)},
           "swing_by_true_score_5000": by_level.to_dict("records"),
           "true60_sources": parts, "two_sittings_1000": two, "reversal_true60_center": rev,
           "robustness": grid.to_dict("records"),
           "robustness_sd_range": [r3(rng_sd[0]), r3(rng_sd[1])],
           "robustness_p10_min_p90_max": [r3(rng_w[0]), r3(rng_w[1])]}

    # 図1：本当の点40・60・80の人の1回の点
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.arange(-1, 102, 2)
    for T, col in [(40, GRAY), (60, BLUE), (80, ORANGE)]:
        ax.hist(hist_keep[T], bins=bins, color=col, alpha=.55, density=True, label=f"本当の点{T}点の人")
        ax.axvline(T, color=col, lw=1.2, ls="--")
    ax.set_xlabel("1回の試験の点（50問・100点満点）"); ax.set_ylabel("割合"); ax.set_yticks([])
    ax.set_xlim(0, 100); ax.legend(frameon=False, fontsize=9, loc="upper left")
    s60 = by_level.set_index("true_score").loc[60]
    ax.set_title(f"本当の点60点の人でも、1回の点は10〜90%で{60 + s60.p10:.0f}〜{60 + s60.p90:.0f}点に散らばる（各5,000回）")
    save(fig, "a926_swing.png", SRC)

    # 図2：1,000人が2回受けたとき
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    jit = rng.uniform(-0.6, 0.6, (2, 1000))
    flip = pass1 != pass2
    ax.scatter(x1[~flip] + jit[0][~flip], x2[~flip] + jit[1][~flip], s=7, color=BLUE, alpha=.4, lw=0,
               label="2回とも合否が同じ")
    ax.scatter(x1[flip] + jit[0][flip], x2[flip] + jit[1][flip], s=9, color=ORANGE, alpha=.8, lw=0,
               label=f"合否が入れかわった（{flip.mean()*100:.1f}%）")
    ax.axvline(PASS, color=GRAY, lw=1, ls="--"); ax.axhline(PASS, color=GRAY, lw=1, ls="--")
    ax.plot([0, 100], [0, 100], color=GRAY, lw=.8)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xlabel("1回目の点"); ax.set_ylabel("2回目の点（同じ人・実力は同じ）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"同じ人が2回受けると、点の相関は{r12:.2f}（1,000人、合格60点）", fontsize=12)
    save(fig, "a926_two_sittings.png", SRC)

    # 図3：問題数と当日の調子で、振れ（標準偏差）がどう変わるか
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    base = grid[grid.item_difficulty_sd == 1.0]
    xs = np.arange(3)
    for k, (c, col) in enumerate([(0.0, LIGHT), (0.2, BLUE), (0.4, ORANGE)]):
        v = base[base.condition_sd == c].sort_values("n_items").sd.values
        ax.bar(xs + (k - 1) * 0.26, v, width=0.26, color=col, label=f"当日の調子の振れ {c}")
        for xx, vv in zip(xs + (k - 1) * 0.26, v):
            ax.text(xx, vv + 0.2, f"{vv:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels(["20問", "50問（基本）", "100問"])
    ax.set_ylabel("1回の点の振れ（標準偏差、点）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("問題を増やすと振れは減るが、当日の調子の分は残る（本当の点60点の人）")
    save(fig, "a926_settings.png", SRC)

    json.dump(out, open(RES / "a926_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
