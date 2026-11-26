"""1282 部品の平均が許容差の中で少しずつ同じ向きにずれていると、二乗で足して見込んだ外れの割合は実際の何分の1に出るのか？（架空のデータ）

作成者が置いた架空の書類ケース。同じ形のケース5段（1段の高さ 80mm ±0.4mm）を重ね、
重ねた高さの許容差を ±0.9mm とする（図面の寸法 400mm）。
見込み：1個ずつの寸法は真ん中を平均とし、標準偏差 t/3 の正規の乱数と見て、
        二乗で足した標準偏差 √k×t/3 から、±0.9mm を外れる割合を出す（式）。
実際：部品の平均が、許容差 t の δ（基本 0.2、つまり +0.08mm）だけずれている。
  ・同じ向き：5段とも +δt
  ・向きがでたらめ：段ごとに +δt か −δt（でたらめ。2^5 通りを同じ重みで平均）
  ・交互：+δt と −δt が交互（+・−・+・−・+）
1個ずつの標準偏差は t/3 のまま。ケースを組んで、±0.9mm を外れる割合を数える（各100万台）。
確かめとして、δ（0・0.1・0.2・0.3）×段の数（3・5・10）×1個ずつの標準偏差（t/3・t/4）の24通り。
組み立ての許容差は、段の数 k のとき t×√k（5段なら 0.894mm。基本は丸めて 0.9mm）と置く。
"""
import json
import math
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1282
SRC = "架空の書類ケースの重ねた高さ（作成者が置いた寸法・許容差・平均のずれからの乱数、seed 1282）"
K, T, NOM, TA = 5, 0.4, 80.0, 0.9
DELTA = 0.2
N = 1_000_000
NG = 400_000


def tail(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def out_formula(mu, sd, ta):
    return tail((ta - mu) / sd) + tail((ta + mu) / sd)


def sim_out(rng, means, sd, ta, n):
    k = len(means)
    s = (rng.standard_normal((n, k)) * sd + means).sum(1)
    return float((np.abs(s) > ta).mean()), s


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    sd = T / 3
    pred = out_formula(0, sd * math.sqrt(K), TA)
    sh = DELTA * T
    cases = {}
    # 同じ向き
    p_same, s_same = sim_out(rng, np.full(K, sh), sd, TA, N)
    # 向きがでたらめ：1台ごとではなく、工場ごとに向きが決まる。2^5通りを同じ重みで（各通り N/32 台）
    signs = np.array(list(itertools.product([1, -1], repeat=K)))
    outs, f_outs = [], []
    for sg in signs:
        p, _ = sim_out(rng, sg * sh, sd, TA, N // len(signs))
        outs.append(p); f_outs.append(out_formula(sg.sum() * sh, sd * math.sqrt(K), TA))
    p_rand = float(np.mean(outs))
    # 交互（+・−・+・−・+）
    alt = np.array([1, -1, 1, -1, 1]) * sh
    p_alt, _ = sim_out(rng, alt, sd, TA, N)
    p_none, s_none = sim_out(rng, np.zeros(K), sd, TA, N)
    # 部品1個の外れ（ずれあり）
    part = rng.standard_normal(N) * sd + sh
    part_out = float((np.abs(part) > T).mean())
    rows = [
        {"case": "no_shift", "label": "ずれなし", "shift_sum_mm": 0.0, "out_sim_pct": p_none * 100, "out_formula_pct": pred * 100},
        {"case": "same_direction", "label": "5段とも同じ向き", "shift_sum_mm": K * sh, "out_sim_pct": p_same * 100, "out_formula_pct": out_formula(K * sh, sd * math.sqrt(K), TA) * 100},
        {"case": "random_direction", "label": "向きがでたらめ", "shift_sum_mm": float(np.mean(np.abs(signs.sum(1)))) * sh, "out_sim_pct": p_rand * 100, "out_formula_pct": float(np.mean(f_outs)) * 100},
        {"case": "alternate", "label": "交互", "shift_sum_mm": float(alt.sum()), "out_sim_pct": p_alt * 100, "out_formula_pct": out_formula(alt.sum(), sd * math.sqrt(K), TA) * 100},
    ]
    tbl = pd.DataFrame(rows)
    tbl["times_of_predicted"] = (tbl.out_sim_pct / (pred * 100)).round(2)
    tbl["out_sim_pct"] = tbl.out_sim_pct.round(3); tbl["out_formula_pct"] = tbl.out_formula_pct.round(3)
    tbl["shift_sum_mm"] = tbl.shift_sum_mm.round(4)
    tbl.to_csv(RES / "base_by_direction.csv", index=False)
    # 向きがでたらめのときの内訳（ずれの合計ごと）
    sums = signs.sum(1)
    dist = pd.DataFrame({"shift_sum_mm": (sums * sh).round(3), "out_sim_pct": np.array(outs) * 100}).groupby("shift_sum_mm").agg(
        n_patterns=("out_sim_pct", "size"), out_sim_pct=("out_sim_pct", "mean")).reset_index()
    dist["share_of_patterns_pct"] = (dist.n_patterns / len(signs) * 100).round(3)
    dist["out_sim_pct"] = dist.out_sim_pct.round(3)
    dist.to_csv(RES / "random_direction_by_sum.csv", index=False)

    base = {
        "n_cases": K, "tol_part_mm": T, "nominal_part_mm": NOM, "tol_assembly_mm": TA, "delta_share_of_tol": DELTA,
        "shift_per_part_mm": round(sh, 4), "shift_sum_same_mm": round(K * sh, 4),
        "predicted_out_pct": round(pred * 100, 3),
        "same_direction_out_pct": round(p_same * 100, 3),
        "same_direction_times_predicted": round(p_same / pred, 2),
        "predicted_share_of_actual": f"1/{p_same / pred:.1f}",
        "random_direction_out_pct": round(p_rand * 100, 3),
        "random_direction_times_predicted": round(p_rand / pred, 2),
        "alternate_out_pct": round(p_alt * 100, 3),
        "no_shift_out_pct": round(p_none * 100, 3),
        "part_out_of_tol_pct_with_shift": round(part_out * 100, 3),
        "part_out_of_tol_pct_no_shift": round((2 * tail(3)) * 100, 3),
        "part_mean_with_shift_mm": round(NOM + sh, 3),
        "same_direction_mean_height_mm": round(float(NOM * K + s_same.mean()), 4),
        "same_direction_sd_mm": round(float(s_same.std()), 4),
        "formula_sd_mm": round(sd * math.sqrt(K), 4),
        "same_direction_out_high_pct": round(float((s_same > TA).mean() * 100), 3),
    }
    # データ：同じ向きの1,000台
    d1 = rng.standard_normal((1000, K)) * sd + sh
    df = pd.DataFrame((NOM + d1).round(4), columns=[f"case{i+1}_mm" for i in range(K)])
    df.insert(0, "unit", np.arange(1, 1001))
    df["height_mm"] = (NOM * K + d1.sum(1)).round(4)
    df["out_of_tol"] = (np.abs(d1.sum(1)) > TA).astype(int)
    df.to_csv(DATA / "same_direction_first1000.csv", index=False)

    # 確かめ 24通り
    rows = []
    for c in [3, 4]:
        for k in [3, 5, 10]:
            for dl in [0.0, 0.1, 0.2, 0.3]:
                sdk = T / c
                ta = T * math.sqrt(k)
                pr = out_formula(0, sdk * math.sqrt(k), ta)
                ps, _ = sim_out(rng, np.full(k, dl * T), sdk, ta, NG)
                part_o = out_formula(dl * T, sdk, T)
                rows.append({"part_sd_div": c, "n_cases": k, "delta_share_of_tol": dl,
                             "tol_assembly_mm": round(ta, 4), "predicted_out_pct": round(pr * 100, 4),
                             "same_direction_out_pct": round(ps * 100, 4),
                             "same_direction_formula_pct": round(out_formula(k * dl * T, sdk * math.sqrt(k), ta) * 100, 4),
                             "times_predicted_formula": round(out_formula(k * dl * T, sdk * math.sqrt(k), ta) / pr, 2),
                             "times_predicted_sim": round(ps / pr, 2),
                             "part_out_of_tol_formula_pct": round(part_o * 100, 4)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    g = grid[grid.delta_share_of_tol > 0]
    robust = {
        "n_settings": int(len(grid)),
        "times_predicted_min_shift": float(g.times_predicted_formula.min()),
        "times_predicted_max_shift": float(g.times_predicted_formula.max()),
        "times_predicted_sd3_min_shift": float(g[g.part_sd_div == 3].times_predicted_formula.min()),
        "times_predicted_sd3_max_shift": float(g[g.part_sd_div == 3].times_predicted_formula.max()),
        "times_predicted_sd4_min_shift": float(g[g.part_sd_div == 4].times_predicted_formula.min()),
        "times_predicted_sd4_max_shift": float(g[g.part_sd_div == 4].times_predicted_formula.max()),
        "same_direction_out_min_pct": float(g.same_direction_formula_pct.min()),
        "same_direction_out_max_pct": float(g.same_direction_formula_pct.max()),
        "n_settings_shift_times_gt2": int((g.times_predicted_formula > 2).sum()),
        "n_settings_shift": int(len(g)),
        "max_abs_diff_sim_vs_formula_pct": round(float((grid.same_direction_out_pct - grid.same_direction_formula_pct).abs().max()), 4),
        "part_out_max_pct": float(g.part_out_of_tol_formula_pct.max()),
    }

    # 図1：分布
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bins = np.linspace(-1.6, 2.0, 121)
    ax.hist(s_none, bins=bins, histtype="step", color=GRAY, lw=1.6, label="ずれなし（見込みの前提）")
    ax.hist(s_same, bins=bins, histtype="step", color=ORANGE, lw=1.6, label="5段とも+0.08mmずれ")
    for x in [TA, -TA]:
        ax.axvline(x, color=INK, lw=1, ls="--")
    ax.text(TA + 0.03, ax.get_ylim()[1] * 0.9, "許容差 ±0.9mm", fontsize=9)
    ax.set_xlabel("重ねた高さの、図面の寸法（400mm）からのずれ（mm）"); ax.set_ylabel("台数（100万台中）")
    ax.set_title("1段の平均が+0.08mmずつずれると、高さの分布ごと+0.4mm動く")
    ax.legend(frameon=False, fontsize=9, loc="center right")
    save(fig, "a1282_hist.png", SRC)

    # 図2：向きごとの外れ
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    labs = ["二乗で足した\n見込み", "ずれなし", "5段とも\n同じ向き", "向きが\nでたらめ", "交互\n（＋−＋−＋）"]
    vals = [pred * 100, p_none * 100, p_same * 100, p_rand * 100, p_alt * 100]
    bars = ax.bar(labs, vals, color=[GRAY, LIGHT, ORANGE, BLUE, GREEN])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{v:.3f}%", ha="center", fontsize=10)
    ax.set_ylim(0, max(vals) * 1.15); ax.set_ylabel("±0.9mmを外れた割合（%）")
    ax.set_title("1段の平均のずれ+0.08mm（許容差の2割）の向きと外れの割合")
    save(fig, "a1282_by_direction.png", SRC)

    # 図3：24通り
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, c in zip(axes, [3, 4]):
        h = grid[grid.part_sd_div == c]
        for k, col in zip([3, 5, 10], [BLUE, ORANGE, GREEN]):
            hh = h[h.n_cases == k]
            ax.plot(hh.delta_share_of_tol, hh.times_predicted_formula, marker="o", color=col, label=f"{k}段")
        ax.set_yscale("log"); ax.set_xticks([0, 0.1, 0.2, 0.3])
        ax.set_xlabel("1段の平均のずれ（許容差に対する割合）"); ax.set_title(f"1個ずつの標準偏差 t/{c}", fontsize=11)
    axes[0].set_ylabel("実際の外れ ÷ 見込み（倍、式、対数の目盛り）")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("同じ向きにずれたときの、見込みに対する実際の外れ（24通り）", y=1.02)
    save(fig, "a1282_grid.png", SRC)

    out = {"seed": SEED, "n_units": N, "base": base, "robust": robust}
    with open(RES / "a1282_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
