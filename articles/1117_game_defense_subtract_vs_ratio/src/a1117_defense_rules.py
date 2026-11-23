"""1117 防御を引き算で効かせるか割合で効かせるかで、弱い攻撃と強い攻撃の差はどう変わるのか？（架空のデータ）

作成者が置いた架空のゲームで、1発が小さい「連撃」（130を4発、素の合計520）と、1発が大きい「強撃」（480を1発）を、
敵の防御の効かせ方（引き算・割合）を変えて比べる。1発のダメージは毎回0.9〜1.1倍に振れ、どの決まりでも最低1は通ると置く。
架空の敵200体（防御0〜120）に、1回の行動で与えるダメージの平均を、乱数の行動（1体あたり2,000回）と式（振れの幅を細かく刻んだ平均）で数える。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1117
SRC = "架空のゲームの攻撃と敵の防御（作成者が置いた決まりと乱数、seed 1117）"
WEAK_HIT, WEAK_N = 130.0, 4
STRONG_HIT = 480.0
SWING = 0.10
MIN_DMG = 1.0
N_ENEMY, D_MAX = 200, 120
ACTS = 2000
U_GRID = np.linspace(1 - SWING, 1 + SWING, 2001)


def rule_fn(name):
    if name == "引き算":
        return lambda x, d: np.maximum(x - d, MIN_DMG)
    if name == "割合（基準240）":
        return lambda x, d: np.maximum(x * (240.0 - d) / 240.0, MIN_DMG)
    if name == "割合（基準480）":
        return lambda x, d: np.maximum(x * (480.0 - d) / 480.0, MIN_DMG)
    if name == "割合（なだらか）":
        return lambda x, d: np.maximum(x * 100.0 / (100.0 + d), MIN_DMG)
    raise ValueError(name)


RULES_MAIN = ["引き算", "割合（基準240）"]
RULES_ALL = ["引き算", "割合（基準240）", "割合（基準480）", "割合（なだらか）"]


def r(x, d=2):
    return round(float(x), d)


def exact_per_hit(rule, hit, d):
    """1発のダメージの平均（振れ 0.9〜1.1倍を細かく刻んで平均した式の値）"""
    f = rule_fn(rule)
    return float(f(hit * U_GRID, d).mean())


def exact_action(rule, hit, n, d):
    return n * exact_per_hit(rule, hit, d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 架空の敵200体（防御は0〜120の整数で一様）
    D = np.sort(rng.integers(0, D_MAX + 1, N_ENEMY))
    rows = []
    for i, d in enumerate(D):
        rec = {"enemy": i + 1, "defense": int(d)}
        for rule in RULES_ALL:
            f = rule_fn(rule)
            uw = rng.uniform(1 - SWING, 1 + SWING, (ACTS, WEAK_N))
            us = rng.uniform(1 - SWING, 1 + SWING, ACTS)
            w = f(WEAK_HIT * uw, d).sum(axis=1).mean()
            s = f(STRONG_HIT * us, d).mean()
            tag = {"引き算": "sub", "割合（基準240）": "ratio240", "割合（基準480）": "ratio480", "割合（なだらか）": "ratio_soft"}[rule]
            rec[f"{tag}_weak_sim"] = r(w, 2); rec[f"{tag}_strong_sim"] = r(s, 2)
            rec[f"{tag}_weak_exact"] = r(exact_action(rule, WEAK_HIT, WEAK_N, d), 2)
            rec[f"{tag}_strong_exact"] = r(exact_action(rule, STRONG_HIT, 1, d), 2)
        rows.append(rec)
    en = pd.DataFrame(rows)
    en.to_csv(DATA / "enemies.csv", index=False)
    tags = {"引き算": "sub", "割合（基準240）": "ratio240", "割合（基準480）": "ratio480", "割合（なだらか）": "ratio_soft"}
    enemy_sum = {}
    for rule in RULES_ALL:
        t = tags[rule]
        ratio = en[f"{t}_weak_exact"] / en[f"{t}_strong_exact"]
        enemy_sum[rule] = {"weak_better_share": r((en[f"{t}_weak_exact"] > en[f"{t}_strong_exact"]).mean() * 100, 1),
                           "weak_better_share_sim": r((en[f"{t}_weak_sim"] > en[f"{t}_strong_sim"]).mean() * 100, 1),
                           "weak_over_strong_median": r(ratio.median(), 3),
                           "weak_over_strong_min": r(ratio.min(), 3), "weak_over_strong_max": r(ratio.max(), 3),
                           "max_abs_sim_minus_exact": r(max((en[f"{t}_weak_sim"] - en[f"{t}_weak_exact"]).abs().max(),
                                                            (en[f"{t}_strong_sim"] - en[f"{t}_strong_exact"]).abs().max()), 2)}

    # 2) 防御ごとの、1発どうしの差と、1回の行動どうしの比（式の値）
    drows = []
    for d in range(0, 201, 10):
        rec = {"defense": d}
        for rule in RULES_ALL:
            t = tags[rule]
            w1 = exact_per_hit(rule, WEAK_HIT, d); s1 = exact_per_hit(rule, STRONG_HIT, d)
            rec[f"{t}_weak_hit"] = r(w1, 2); rec[f"{t}_strong_hit"] = r(s1, 2)
            rec[f"{t}_strong_over_weak_hit"] = r(s1 / w1, 2)
            rec[f"{t}_weak4_over_strong"] = r(WEAK_N * w1 / s1, 3)
        drows.append(rec)
    byd = pd.DataFrame(drows)
    byd.to_csv(RES / "by_defense.csv", index=False)
    # 引き算で連撃と強撃が並ぶ防御（式：4×(130−D)=480−D → D=40/3）
    even_sub = (WEAK_N * WEAK_HIT - STRONG_HIT) / (WEAK_N - 1)
    # 引き算で、連撃の1発が最低の1になりはじめる防御（130×0.9）、いつも1になる防御（130×1.1−1）
    floor_start = WEAK_HIT * (1 - SWING) - MIN_DMG
    floor_all = WEAK_HIT * (1 + SWING) - MIN_DMG

    # 3) 確かめ：連撃の発数（素の合計520は同じ）×敵の防御の上限×決まり（36通り）
    grid = []
    for k, dmax, rule in itertools.product([2, 4, 8], [60, 120, 200], RULES_ALL):
        hit = 520.0 / k
        ds = np.arange(0, dmax + 1)
        w = np.array([exact_action(rule, hit, k, d) for d in ds])
        s = np.array([exact_action(rule, STRONG_HIT, 1, d) for d in ds])
        grid.append({"weak_hits": k, "weak_hit": r(hit, 1), "defense_max": dmax, "rule": rule,
                     "weak_better_share": r((w > s).mean() * 100, 1),
                     "weak_over_strong_median": r(np.median(w / s), 3), "weak_over_strong_min": r((w / s).min(), 3),
                     "strong_over_weak_hit_at_max": r(exact_per_hit(rule, STRONG_HIT, dmax) / exact_per_hit(rule, hit, dmax), 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gsub = grid[grid.rule == "引き算"]
    grat = grid[grid.rule != "引き算"]

    pick = {}
    for d in [0, 40, 80, 100, 120]:
        row = byd[byd.defense == d].iloc[0]
        pick[str(d)] = {rule: {"weak_hit": float(row[f"{tags[rule]}_weak_hit"]), "strong_hit": float(row[f"{tags[rule]}_strong_hit"]),
                               "strong_over_weak_hit": float(row[f"{tags[rule]}_strong_over_weak_hit"]),
                               "weak4_over_strong": float(row[f"{tags[rule]}_weak4_over_strong"])} for rule in RULES_ALL}

    out = {"weak": {"hit": WEAK_HIT, "hits": WEAK_N, "raw_total": WEAK_HIT * WEAK_N}, "strong": {"hit": STRONG_HIT, "hits": 1},
           "raw_strong_over_weak_hit": r(STRONG_HIT / WEAK_HIT, 2), "raw_weak_over_strong": r(WEAK_HIT * WEAK_N / STRONG_HIT, 3),
           "swing": SWING, "min_damage": MIN_DMG, "enemies": N_ENEMY, "defense_range": [0, D_MAX], "acts_per_enemy": ACTS,
           "enemy_defense_median": float(np.median(D)),
           "enemy_summary": enemy_sum, "by_defense_pick": pick,
           "sub_even_defense_formula": r(even_sub, 2),
           "sub_enemies_defense_le_13": int((D <= 13).sum()),
           "sub_weak_floor_starts_at_defense": r(floor_start, 1), "sub_weak_floor_always_at_defense": r(floor_all, 1),
           "grid_sub_weak_better_share_range": [r(gsub.weak_better_share.min(), 1), r(gsub.weak_better_share.max(), 1)],
           "grid_sub_weak_over_strong_median_range": [r(gsub.weak_over_strong_median.min(), 3), r(gsub.weak_over_strong_median.max(), 3)],
           "grid_ratio_weak_better_share_range": [r(grat.weak_better_share.min(), 1), r(grat.weak_better_share.max(), 1)],
           "grid_ratio_weak_over_strong_median_range": [r(grat.weak_over_strong_median.min(), 3), r(grat.weak_over_strong_median.max(), 3)],
           "grid_sub_strong_over_weak_hit_at_max_range": [r(gsub.strong_over_weak_hit_at_max.min(), 2), r(gsub.strong_over_weak_hit_at_max.max(), 2)],
           "grid_count": len(grid)}
    json.dump(out, open(RES / "a1117_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：防御ごとの1発のダメージ（連撃の1発・強撃の1発）
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    dd = byd[byd.defense <= 160]
    for ax, rule in zip(axes, RULES_MAIN):
        t = tags[rule]
        ax.plot(dd.defense, dd[f"{t}_strong_hit"], color=ORANGE, lw=2, marker="o", ms=3, label="強撃の1発（素の480）")
        ax.plot(dd.defense, dd[f"{t}_weak_hit"], color=BLUE, lw=2, marker="o", ms=3, label="連撃の1発（素の130）")
        for d in [40, 100]:
            row = byd[byd.defense == d].iloc[0]
            ax.annotate(f"防御{d}：{row[f'{t}_strong_over_weak_hit']:.2f}倍", xy=(d, row[f"{t}_weak_hit"]),
                        xytext=(d + 5, row[f"{t}_weak_hit"] + 95), fontsize=9, arrowprops=dict(arrowstyle="->", color=INK, lw=0.7))
        ax.set_title(f"{rule}：" + ("ダメージ＝攻撃−防御" if rule == "引き算" else "ダメージ＝攻撃×（240−防御）÷240"), loc="left", fontsize=10.5)
        ax.set_xlabel("敵の防御"); ax.set_ylim(0, 560)
    axes[0].set_ylabel("1発のダメージ（平均、式の値）")
    axes[0].legend(frameon=False, fontsize=9, loc="upper right")
    fig.suptitle("強撃の1発は連撃の1発の何倍か：引き算では防御が上がるほど差が開き、割合では3.69倍のまま", x=0.01, y=1.03, ha="left", fontsize=12)
    save(fig, "a1117_per_hit.png", SRC)

    # 図2：架空の敵200体で、連撃（4発）÷強撃（1発）
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    cols = {"引き算": ORANGE, "割合（基準240）": BLUE, "割合（基準480）": GREEN, "割合（なだらか）": GRAY}
    for rule in RULES_ALL:
        t = tags[rule]
        ax.plot(en.defense, en[f"{t}_weak_sim"] / en[f"{t}_strong_sim"], "o", ms=3.5, color=cols[rule], alpha=0.8,
                label=f"{rule}（連撃が上の敵 {enemy_sum[rule]['weak_better_share']:.1f}%）")
    ax.axhline(1, color=INK, lw=0.8, ls=":")
    ax.text(121, 1.02, "同じ", fontsize=9)
    ax.set_ylim(0, 1.25); ax.set_xlabel("敵の防御"); ax.set_ylabel("連撃（4発）÷強撃（1発）\n（1体あたり2,000回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.suptitle("架空の敵200体：割合ではどの敵にも連撃が上、引き算では防御13までの敵だけ", x=0.01, y=1.02, ha="left", fontsize=12)
    save(fig, "a1117_enemies.png", SRC)

    # 図3：確かめ（引き算）：連撃の発数×防御の上限で、連撃が上の敵の割合
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(3); wbar = 0.25
    for j, (dmax, col) in enumerate(zip([60, 120, 200], [LIGHT, BLUE, INK])):
        vals = [float(gsub[(gsub.weak_hits == k) & (gsub.defense_max == dmax)].weak_better_share.iloc[0]) for k in [2, 4, 8]]
        bars = ax.bar(x + (j - 1) * wbar, vals, wbar, color=col, label=f"防御0〜{dmax}")
        for bb, v in zip(bars, vals):
            ax.text(bb.get_x() + bb.get_width() / 2, v + 1, f"{v:.1f}%", ha="center", fontsize=8.5)
    ax.axhline(100, color=GREEN, lw=1.2, ls="--")
    ax.text(2.45, 101.5, "割合の3つの決まりでは\nどれも100%", fontsize=8.5, color=GREEN, ha="right", va="bottom")
    ax.set_xticks(x); ax.set_xticklabels(["2発×260", "4発×130", "8発×65"])
    ax.set_ylim(0, 118); ax.set_ylabel("連撃が強撃より上だった防御の割合（%）")
    ax.set_xlabel("連撃の分け方（素の合計はどれも520、強撃は480）")
    ax.legend(frameon=False, fontsize=9, loc="center right")
    fig.suptitle("確かめ（36通り）：引き算では、発数が多く防御の高い敵が多いほど連撃が上の割合は下がる", x=0.01, y=1.03, ha="left", fontsize=12)
    save(fig, "a1117_robust.png", SRC)

    print(json.dumps(enemy_sum, ensure_ascii=False, indent=0))
    print(json.dumps(pick, ensure_ascii=False))
    print(grid.to_string())
    print({k: out[k] for k in out if k.startswith("grid_") or k.startswith("sub_")})
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
