"""1289 中身の重さが表示よりわずかに多い小袋を10袋まとめて1箱にすると、箱の表示の重さを下回る箱の割合は、1袋で表示を下回る割合からどう変わるのか？（架空のデータ）

架空の事務用品（クリップ）の小袋。1袋の表示は100g、10袋入りの箱の表示は1,000g（袋の表示×袋の数）。
1袋の中身の重さ＝100g＋平均の上乗せ d ＋その箱に共通のずれ＋袋ごとのずれ（正規分布）。
袋どうしのばらつき（標準偏差）σ のうち、分散の割合 ρ を「同じ箱の袋に共通のずれ」（同じ時間に続けて詰めた袋のそろい）とする。
箱の中身＝袋の和。箱が表示を下回る割合と、1袋が表示を下回る割合を比べる。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1289
SRC = "架空のクリップの小袋の重さ（作成者が乱数で作成、seed 1289）"
LABEL = 100.0
BASE_D, BASE_S, BASE_N = 1.0, 1.5, 10
DS = [-0.5, -0.2, 0.0, 0.2, 0.5, 1.0, 2.0]
SS = [1.0, 1.5, 2.5]
NS = [1, 2, 5, 10, 20]
RHOS = [0.0, 0.05, 0.1, 0.3, 0.5]
BOXES = 100_000


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def formula_box(d, s, n, rho):
    sd = s * math.sqrt(n * (1 - rho) + n * n * rho)
    return ncdf(-n * d / sd)


def sim(rng, d, s, n, rho, boxes=BOXES):
    common = rng.normal(0, s * math.sqrt(rho), (boxes, 1)) if rho > 0 else 0.0
    bags = LABEL + d + common + rng.normal(0, s * math.sqrt(1 - rho), (boxes, n))
    box = bags.sum(axis=1)
    return bags, box


CACHE = {}


def rates(rng, d, s, n, rho):
    """同じ置き方は1回だけ数える（表ごとに乱数の値が食い違わないように）"""
    key = (d, s, n, rho)
    if key not in CACHE:
        bg, bx = sim(rng, d, s, n, rho)
        CACHE[key] = (round(float((bg < LABEL).mean() * 100), 2), round(float((bx < LABEL * n).mean() * 100), 2))
    return CACHE[key]


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 基本：d=+1.0g・σ=1.5g・10袋・そろいなし
    bags, box = sim(rng, BASE_D, BASE_S, BASE_N, 0.0)
    base = {
        "d": BASE_D, "sd": BASE_S, "n": BASE_N, "rho": 0.0, "boxes": BOXES,
        "bag_below_pct": round(float((bags < LABEL).mean() * 100), 2),
        "bag_below_formula_pct": round(ncdf(-BASE_D / BASE_S) * 100, 2),
        "box_below_pct": round(float((box < LABEL * BASE_N).mean() * 100), 2),
        "box_below_formula_pct": round(formula_box(BASE_D, BASE_S, BASE_N, 0.0) * 100, 2),
        "box_has_light_bag_pct": round(float((bags < LABEL).any(axis=1).mean() * 100), 2),
        "box_has_light_bag_formula_pct": round((1 - (1 - ncdf(-BASE_D / BASE_S)) ** BASE_N) * 100, 2),
        "light_bags_per_box_mean": round(float((bags < LABEL).sum(axis=1).mean()), 3),
        "box_mean_g": round(float(box.mean()), 3), "box_sd_g": round(float(box.std(ddof=1)), 3),
        "box_sd_formula_g": round(BASE_S * math.sqrt(BASE_N), 3),
    }
    CACHE[(BASE_D, BASE_S, BASE_N, 0.0)] = (base["bag_below_pct"], base["box_below_pct"])
    CACHE[(BASE_D, BASE_S, 1, 0.0)] = (base["bag_below_pct"], base["bag_below_pct"])   # 袋1つ＝基本の袋の割合
    pd.DataFrame(np.round(bags[:1000], 3), columns=[f"bag{i + 1}_g" for i in range(BASE_N)]).assign(
        box_g=np.round(box[:1000], 3)).to_csv(DATA / "boxes_base_first1000.csv", index_label="box_no")
    # 箱の中の軽い袋の数の分布
    k = (bags < LABEL).sum(axis=1)
    kd = pd.DataFrame({"light_bags": np.arange(BASE_N + 1)})
    kd["boxes_pct"] = [round(float((k == j).mean() * 100), 2) for j in kd.light_bags]
    kd["box_below_pct_within"] = [round(float((box[k == j] < LABEL * BASE_N).mean() * 100), 2) if (k == j).any() else np.nan
                                  for j in kd.light_bags]
    kd.to_csv(RES / "light_bags_in_box.csv", index=False)

    # 確かめ1：上乗せ d × ばらつき σ × 袋の数 n（そろいなし）
    g1 = []
    for s in SS:
        for d in DS:
            for n in NS:
                bb_, bx_ = rates(rng, d, s, n, 0.0)
                g1.append({"d": d, "sd": s, "n": n,
                           "bag_below_pct": bb_,
                           "bag_below_formula_pct": round(ncdf(-d / s) * 100, 2),
                           "box_below_pct": bx_,
                           "box_below_formula_pct": round(formula_box(d, s, n, 0.0) * 100, 2)})
    g1 = pd.DataFrame(g1)
    g1.to_csv(RES / "grid_d_sd_n.csv", index=False)

    # 確かめ2：同じ箱の袋のそろい ρ × 上乗せ d（σ=1.5g、10袋）
    g2 = []
    for rho in RHOS:
        for d in DS:
            bb_, bx_ = rates(rng, d, BASE_S, BASE_N, rho)
            g2.append({"rho": rho, "d": d, "sd": BASE_S, "n": BASE_N,
                       "bag_below_pct": bb_,
                       "box_below_pct": bx_,
                       "box_below_formula_pct": round(formula_box(d, BASE_S, BASE_N, rho) * 100, 2)})
    g2 = pd.DataFrame(g2)
    g2.to_csv(RES / "grid_rho.csv", index=False)

    pos = g1[g1.d > 0]
    neg = g1[g1.d < 0]
    n10 = g1[g1.n == 10]
    r10 = g2[g2.d == BASE_D]
    main_json = {
        "base": base,
        "base_rho": {f"rho{int(r * 100)}": float(r10[r10.rho == r].box_below_pct.iloc[0]) for r in RHOS},
        "base_rho_formula": {f"rho{int(r * 100)}": float(r10[r10.rho == r].box_below_formula_pct.iloc[0]) for r in RHOS},
        "range": {
            "n_settings_grid1": int(len(g1)), "n_settings_grid2": int(len(g2)),
            "pos_box_le_bag_all": bool((pos[pos.n > 1].box_below_pct <= pos[pos.n > 1].bag_below_pct).all()),
            "neg_box_ge_bag_all": bool((neg[neg.n > 1].box_below_pct >= neg[neg.n > 1].bag_below_pct).all()),
            "n10_pos_bag_min": float(n10[n10.d > 0].bag_below_pct.min()), "n10_pos_bag_max": float(n10[n10.d > 0].bag_below_pct.max()),
            "n10_pos_box_min": float(n10[n10.d > 0].box_below_pct.min()), "n10_pos_box_max": float(n10[n10.d > 0].box_below_pct.max()),
            "n10_neg_bag_min": float(n10[n10.d < 0].bag_below_pct.min()), "n10_neg_bag_max": float(n10[n10.d < 0].bag_below_pct.max()),
            "n10_neg_box_min": float(n10[n10.d < 0].box_below_pct.min()), "n10_neg_box_max": float(n10[n10.d < 0].box_below_pct.max()),
            "n10_zero_box_min": float(n10[n10.d == 0].box_below_pct.min()), "n10_zero_box_max": float(n10[n10.d == 0].box_below_pct.max()),
            "sim_minus_formula_maxabs_grid1": round(float((g1.box_below_pct - g1.box_below_formula_pct).abs().max()), 2),
            "sim_minus_formula_maxabs_grid2": round(float((g2.box_below_pct - g2.box_below_formula_pct).abs().max()), 2),
        },
    }
    with open(RES / "a1289_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：袋の数を増やすと（σ=1.5g、d=+1.0・+0.2・−0.2）
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for d, c in [(1.0, BLUE), (0.2, GREEN), (-0.2, ORANGE)]:
        x = g1[(g1.sd == BASE_S) & (g1.d == d)]
        ax.plot(x.n, x.box_below_pct, marker="o", color=c, label=f"平均の上乗せ{d:+.1f}g")
        for n_, v in zip(x.n, x.box_below_pct):
            ax.text(n_ + (0.3 if n_ == 2 else 0), v + 2.5, f"{v:.2f}%", ha="left" if n_ == 2 else "center", fontsize=8, color=c)
    ax.set_xticks(NS)
    ax.set_xlabel("1箱にまとめる袋の数（1は袋1つ）")
    ax.set_ylabel("表示の重さを下回る割合（%）")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("平均が表示より多ければ袋をまとめるほど下回る箱は減り、\n少なければ増えた（袋どうしのばらつき1.5g、そろいなし）", fontsize=11)
    save(fig, "a1289_by_n.png", SRC)

    # 図2：基本の置き方で1袋・箱（そろいの割合ごと）を棒で
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    labs = ["1袋"] + [f"10袋の箱\nそろい{int(r * 100)}%" for r in RHOS]
    vals = [base["bag_below_pct"]] + [float(r10[r10.rho == r].box_below_pct.iloc[0]) for r in RHOS]
    cols = [GRAY] + [BLUE] * len(RHOS)
    ax.bar(range(len(vals)), vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.5, f"{v:.2f}%", ha="center", fontsize=9)
    ax.set_xticks(range(len(vals))); ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylabel("表示の重さを下回る割合（%）")
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_title("同じ箱の袋のずれがそろうほど、下回る箱は増えた\n（平均の上乗せ+1.0g・ばらつき1.5g。そろい＝ばらつきのうち箱に共通の分の割合）", fontsize=11)
    save(fig, "a1289_rho.png", SRC, y=-0.03)

    # 図3：箱の中の軽い袋の数
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar(kd.light_bags, kd.boxes_pct, color=LIGHT)
    for j, v in zip(kd.light_bags, kd.boxes_pct):
        if v >= 0.01:
            ax.text(j, v + 0.4, f"{v:.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(kd.light_bags)
    ax.set_xlabel("1箱10袋のうち、表示100gを下回る袋の数")
    ax.set_ylabel("箱の割合（%）")
    ax.set_ylim(0, kd.boxes_pct.max() * 1.2)
    ax.set_title(f"軽い袋が1つ以上入った箱は{base['box_has_light_bag_pct']:.2f}%、"
                 f"箱として下回ったのは{base['box_below_pct']:.2f}%", fontsize=11)
    save(fig, "a1289_light_bags.png", SRC)

    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print(kd.to_string())
    print(f"{time.time() - t0:.1f} 秒")


if __name__ == "__main__":
    main()
