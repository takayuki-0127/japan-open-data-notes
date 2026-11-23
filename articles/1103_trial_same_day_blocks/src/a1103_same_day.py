"""1103 同じ日の分をまとめて比べると、ばらつきはどれだけ減るのか？（架空のデータ）

架空の印刷の工房で、新しいインクといつものインクの「にじみの幅」（拡大して測った幅、μm）を比べる。
にじみは日によって（湿り気など）全体に上下し、同じ日の中でも1枚ずつ振れると作成者が置く。
同じ枚数（1日2枚×8日＝16枚）で、①インクごとに別々の日に試す、②毎日2つのインクを1枚ずつ試す、の2つの組み方で、
インクの差の見積もりの散らばりと、差があるかの判定の当たり・空振りを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1103
SRC = "架空の印刷の工房のにじみの幅（作成者が置いた日の振れと1枚の振れからの乱数、seed 1103）"
BASE = {"days": 8, "per_day": 2, "day_sd": 1.5, "print_sd": 1.0, "ink_day_sd": 0.0, "true_diff": -1.0, "level": 30.0}
REPS = 20000
GRID_REPS = 4000
# 両側5%の判定に使う境目の値（自由度ごと。差÷見積もった散らばりがこれより大きければ「差がある」）
TCRIT = {2: 4.302653, 3: 3.182446, 6: 2.446912, 7: 2.364624, 14: 2.144787, 15: 2.13145, 30: 2.042272}
ANALYSES = {"sep_print": "①別々の日・1枚ずつを別々に数えて判定", "sep_day": "①別々の日・日の平均で判定",
            "same_pair": "②同じ日・日ごとの差で判定", "same_ignore": "②同じ日・日を無視して判定"}


def r(x, d=4):
    return round(float(x), d)


def two_group(a, b, df):
    """a・b：reps×n。平均の差と判定（散らばりは2つの組をまとめて見積もる）"""
    na, nb = a.shape[1], b.shape[1]
    d = a.mean(1) - b.mean(1)
    sp = ((a.var(1, ddof=1) * (na - 1) + b.var(1, ddof=1) * (nb - 1)) / (na + nb - 2))
    se = np.sqrt(sp * (1 / na + 1 / nb))
    return d, np.abs(d / se) > TCRIT[df]


def simulate(rng, reps, days, day_sd, print_sd, ink_day_sd, true_diff):
    half = days // 2
    # ①別々の日：前半の日を新しいインク、後半の日をいつものインクにする（日の順は入れかえても同じ）
    dayeff = day_sd * rng.standard_normal((reps, days))
    inkday = ink_day_sd * rng.standard_normal((reps, days))
    y = BASE["level"] + dayeff[:, :, None] + print_sd * rng.standard_normal((reps, days, 2))
    y[:, :half, :] += true_diff + inkday[:, :half, None]
    new_p, old_p = y[:, :half, :].reshape(reps, -1), y[:, half:, :].reshape(reps, -1)
    d_sep, j_print = two_group(new_p, old_p, 2 * days - 2)
    _, j_day = two_group(y[:, :half, :].mean(2), y[:, half:, :].mean(2), days - 2)
    # ②同じ日：毎日1枚ずつ
    dayeff2 = day_sd * rng.standard_normal((reps, days))
    inkday2 = ink_day_sd * rng.standard_normal((reps, days))
    new = BASE["level"] + dayeff2 + true_diff + inkday2 + print_sd * rng.standard_normal((reps, days))
    old = BASE["level"] + dayeff2 + print_sd * rng.standard_normal((reps, days))
    dd = new - old
    d_same = dd.mean(1)
    se = dd.std(1, ddof=1) / np.sqrt(days)
    j_pair = np.abs(d_same / se) > TCRIT[days - 1]
    _, j_ign = two_group(new, old, 2 * days - 2)
    est = {"sep": d_sep, "same": d_same}
    judge = {"sep_print": j_print, "sep_day": j_day, "same_pair": j_pair, "same_ign": j_ign}
    return est, judge, (y[0], new[0], old[0])


def formula_sd(days, day_sd, print_sd, ink_day_sd):
    half = days // 2
    sep = np.sqrt(2 * (day_sd ** 2 / half + print_sd ** 2 / (2 * half)) + ink_day_sd ** 2 / half)
    same = np.sqrt((2 * print_sd ** 2 + ink_day_sd ** 2) / days)
    return sep, same


def one_case(rng, reps, days, day_sd, print_sd, ink_day_sd):
    est, judge_t, ex = simulate(rng, reps, days, day_sd, print_sd, ink_day_sd, BASE["true_diff"])
    _, judge_0, _ = simulate(rng, reps, days, day_sd, print_sd, ink_day_sd, 0.0)
    fs, fm = formula_sd(days, day_sd, print_sd, ink_day_sd)
    o = {"sep_sd": r(est["sep"].std(), 4), "same_sd": r(est["same"].std(), 4),
         "sep_mean": r(est["sep"].mean(), 4), "same_mean": r(est["same"].mean(), 4),
         "sep_sd_formula": r(fs, 4), "same_sd_formula": r(fm, 4),
         "sd_ratio": r(est["same"].std() / est["sep"].std(), 4), "sd_ratio_formula": r(fm / fs, 4),
         "sep_within05": r(100 * np.mean(np.abs(est["sep"] - BASE["true_diff"]) <= 0.5), 2),
         "same_within05": r(100 * np.mean(np.abs(est["same"] - BASE["true_diff"]) <= 0.5), 2)}
    keymap = {"sep_print": "sep_print", "sep_day": "sep_day", "same_pair": "same_pair", "same_ignore": "same_ign"}
    for k, kk in keymap.items():
        o[f"{k}_power"] = r(100 * judge_t[kk].mean(), 2)
        o[f"{k}_false"] = r(100 * judge_0[kk].mean(), 2)
    return o, ex


def main():
    rng = np.random.default_rng(SEED)
    base, ex = one_case(rng, REPS, BASE["days"], BASE["day_sd"], BASE["print_sd"], BASE["ink_day_sd"])
    tab = pd.DataFrame([{"analysis": ANALYSES[k], "detect_when_true_minus1_pct": base[f"{k}_power"], "false_alarm_when_no_diff_pct": base[f"{k}_false"]}
                        for k in ANALYSES])
    tab.to_csv(RES / "judge_base.csv", index=False)

    y, new, old = ex
    rows = []
    for d in range(BASE["days"]):
        for p in range(2):
            rows.append({"design": "separate_days", "day": d + 1, "ink": "new" if d < BASE["days"] // 2 else "usual", "blur_um": r(y[d, p], 3)})
    for d in range(BASE["days"]):
        rows.append({"design": "same_day", "day": d + 1, "ink": "new", "blur_um": r(new[d], 3)})
        rows.append({"design": "same_day", "day": d + 1, "ink": "usual", "blur_um": r(old[d], 3)})
    pd.DataFrame(rows).to_csv(DATA / "one_trial_both_designs.csv", index=False)

    grid = []
    for days in [4, 8, 16]:
        for day_sd in [0.0, 0.5, 1.0, 1.5, 3.0]:
            for ink_day_sd in [0.0, 0.5, 1.0]:
                o, _ = one_case(rng, GRID_REPS, days, day_sd, BASE["print_sd"], ink_day_sd)
                grid.append({"days": days, "day_sd": day_sd, "ink_day_sd": ink_day_sd, **o})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    g0 = grid[grid.day_sd == 0]
    gp = grid[grid.day_sd > 0]
    out = {"setting": BASE, "reps": REPS, "grid_reps": GRID_REPS, "base": base,
           "reduction_pct_base": r(100 * (1 - base["sd_ratio"]), 2), "reduction_pct_base_formula": r(100 * (1 - base["sd_ratio_formula"]), 2),
           "grid_sd_ratio_range": [r(grid.sd_ratio.min(), 4), r(grid.sd_ratio.max(), 4)],
           "grid_max_abs_ratio_minus_formula": r((grid.sd_ratio - grid.sd_ratio_formula).abs().max(), 4),
           "grid_dayzero_sd_ratio_range": [r(g0.sd_ratio.min(), 4), r(g0.sd_ratio.max(), 4)],
           "grid_dayzero_power_pair_minus_sepday": [r((g0.same_pair_power - g0.sep_day_power).min(), 2), r((g0.same_pair_power - g0.sep_day_power).max(), 2)],
           "grid_daypos_power_pair_minus_sepday": [r((gp.same_pair_power - gp.sep_day_power).min(), 2), r((gp.same_pair_power - gp.sep_day_power).max(), 2)],
           "grid_sep_print_false_range": [r(grid.sep_print_false.min(), 2), r(grid.sep_print_false.max(), 2)],
           "grid_sep_print_false_dayzero_range": [r(g0.sep_print_false.min(), 2), r(g0.sep_print_false.max(), 2)],
           "grid_sep_day_false_range": [r(grid.sep_day_false.min(), 2), r(grid.sep_day_false.max(), 2)],
           "grid_same_pair_false_range": [r(grid.same_pair_false.min(), 2), r(grid.same_pair_false.max(), 2)],
           "grid_same_ignore_false_range": [r(grid.same_ignore_false.min(), 2), r(grid.same_ignore_false.max(), 2)],
           "grid_n_cases": int(len(grid))}
    for t in [0.0, 0.5, 1.0]:
        gg = grid[(grid.days == 8) & (grid.ink_day_sd == t)]
        out[f"days8_inkday{t}_ratio_by_day_sd"] = {str(a): r(b, 4) for a, b in zip(gg.day_sd, gg.sd_ratio)}
    json.dump(out, open(RES / "a1103_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：見積もりの散らばり（基本）
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    labs = ["①インクごとに別々の日（4日ずつ）", "②毎日2つのインクを1枚ずつ（8日）"]
    vals = [base["sep_sd"], base["same_sd"]]
    form = [base["sep_sd_formula"], base["same_sd_formula"]]
    ax.barh([1, 0], vals, color=[ORANGE, BLUE], height=0.55)
    for yv, v, f in zip([1, 0], vals, form):
        ax.text(v + 0.02, yv, f"{v}（式 {f}）", va="center", fontsize=10)
    ax.set_yticks([1, 0]); ax.set_yticklabels(labs); ax.set_xlim(0, 1.6)
    ax.set_xlabel("インクの差の見積もりの散らばり（標準偏差、μm）")
    ax.set_title(f"同じ16枚：同じ日にまとめると、散らばりは{base['sd_ratio']}倍（式どおりなら{base['sd_ratio_formula']}倍）", loc="left", fontsize=12)
    save(fig, "a1103_sd.png", SRC, y=-0.06)

    # 図2：日の振れの大きさで、減り方がどう変わるか（8日）
    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    for t, c, mk in [(0.0, BLUE, "o"), (0.5, GRAY, "s"), (1.0, ORANGE, "^")]:
        gg = grid[(grid.days == 8) & (grid.ink_day_sd == t)]
        ax.plot(gg.day_sd, gg.sd_ratio, color=c, marker=mk, label=f"インクの差の日ごとの振れ {t}μm")
        ax.plot(gg.day_sd, gg.sd_ratio_formula, color=c, ls=":", lw=1)
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_ylim(0, 1.15); ax.set_xticks([0, 0.5, 1.0, 1.5, 3.0])
    ax.set_xlabel("日による振れ（標準偏差、μm）　※1枚ずつの振れは1.0μm")
    ax.set_ylabel("②の散らばり÷①の散らばり")
    ax.legend(fontsize=9, loc="upper right", title="点線は式の値", title_fontsize=8.5)
    ax.set_title("日による振れが大きいほど、同じ日にまとめると散らばりが減る（8日、式どおり）", loc="left", fontsize=12)
    save(fig, "a1103_ratio.png", SRC, y=-0.04)

    # 図3：判定の当たりと空振り（基本）
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True)
    keys = list(ANALYSES)
    yy = np.arange(4)[::-1]
    cols = [ORANGE, "#f2b38f", BLUE, LIGHT]
    for ax, suf, ttl, xmax in [(axes[0], "power", "本当の差 −1.0μm を「差がある」とした割合（%）", 100), (axes[1], "false", "本当は差がないのに「差がある」とした割合（%）", 50)]:
        v = [base[f"{k}_{suf}"] for k in keys]
        ax.barh(yy, v, color=cols)
        for y_, x in zip(yy, v):
            xt = x + xmax * 0.01 if (suf == "power" or x > 6) else 5.6
            ax.text(xt, y_, f"{x}%", va="center", fontsize=9.5)
        ax.set_xlim(0, xmax); ax.set_xlabel(ttl, fontsize=10)
    axes[1].axvline(5, color=INK, ls="--", lw=0.8); axes[1].text(5.5, 3.45, "決めた基準 5%", fontsize=8.5)
    axes[0].set_yticks(yy); axes[0].set_yticklabels([ANALYSES[k] for k in keys])
    fig.suptitle("基本の置き方（日の振れ1.5μm・1枚の振れ1.0μm、8日16枚）：組み方と数え方で判定が変わる", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, "a1103_judge.png", SRC, y=-0.03)

    print(tab.to_string()); print(json.dumps(out, ensure_ascii=False, indent=1))
    print(grid[["days", "day_sd", "ink_day_sd", "sd_ratio", "sd_ratio_formula", "sep_print_false", "sep_day_false", "same_pair_false", "same_ignore_false", "sep_day_power", "same_pair_power", "same_ignore_power"]].to_string())


if __name__ == "__main__":
    main()
