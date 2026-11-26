"""1281 5つの部品を重ねた棚の高さで、許容差をそのまま足した「最悪の幅」は、実際の高さのばらつきよりどれだけ広いのか？（架空のデータ）

作成者が置いた架空の組み立て式の棚。下から 台輪・箱A・箱B・箱C・天板 の5つの部品を重ねる。
部品ごとの寸法は、図面の寸法（真ん中）と許容差（±t）を作成者が置き、
基本では、1個ずつの寸法は真ん中を平均とし、標準偏差 t/3 の正規の乱数で作る（真ん中からのずれなし）。
棚の高さ＝5つの部品の寸法の合計。棚20万台を組み、
  ・許容差をそのまま足した最悪の幅（±Σt）
  ・許容差を二乗で足して平方根をとった幅（±√Σt²）
  ・実際に組んだ棚の高さの、真ん中99.73%が入る幅（下0.135%点〜上0.135%点）
  ・1,000台ずつ組んだときの、いちばん高い棚といちばん低い棚の差（200組の平均）
を比べる。
確かめとして、部品の数（2・5・10・20個）×許容差の組み合わせ（そろい・棚と同じ割合・1つだけ大きい）
×1個ずつの寸法の作り方（正規で標準偏差t/3・正規で標準偏差t/4・許容差の中で一様）の36通り（各20万台）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1281
SRC = "架空の組み立て式の棚（作成者が置いた部品の寸法と許容差からの乱数、seed 1281）"
NAMES = ["台輪", "箱A", "箱B", "箱C", "天板"]
NOM = np.array([60.0, 300.0, 300.0, 300.0, 20.0])
TOL = np.array([0.5, 0.8, 0.8, 0.8, 0.3])
N = 200000
BATCH = 1000
LO, HI = 0.00135, 0.99865
SHAPES = {"normal_sd_t3": "正規・標準偏差t/3", "normal_sd_t4": "正規・標準偏差t/4", "uniform_full": "許容差の中で一様"}
MIXES = {"equal": "そろい", "shelf_ratio": "棚と同じ割合", "one_big": "1つだけ大きい"}


def tol_for(mix, k):
    if mix == "equal":
        return np.full(k, 0.6)
    if mix == "shelf_ratio":
        return np.resize(TOL, k)
    t = np.full(k, 0.3)
    t[0] = 1.5
    return t


def draw(rng, tol, shape, n):
    k = len(tol)
    if shape == "normal_sd_t3":
        return rng.standard_normal((n, k)) * (tol / 3)
    if shape == "normal_sd_t4":
        return rng.standard_normal((n, k)) * (tol / 4)
    return rng.uniform(-1, 1, (n, k)) * tol


def widths(dev, tol):
    q = np.quantile(dev, [LO, HI])
    b = dev[: (len(dev) // BATCH) * BATCH].reshape(-1, BATCH)
    rng_b = b.max(1) - b.min(1)
    return {
        "worst_width_mm": float(2 * tol.sum()),
        "sq_sum_width_mm": float(2 * np.sqrt((tol ** 2).sum())),
        "actual_9973_width_mm": float(q[1] - q[0]),
        "batch1000_range_mean_mm": float(rng_b.mean()),
        "batch1000_range_max_mm": float(rng_b.max()),
        "actual_sd_mm": float(dev.std()),
    }


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 基本
    dev_parts = draw(rng, TOL, "normal_sd_t3", N)
    dev = dev_parts.sum(1)
    w = widths(dev, TOL)
    worst_half = TOL.sum()
    sq_half = np.sqrt((TOL ** 2).sum())
    base = dict(w)
    base.update({
        "nominal_height_mm": float(NOM.sum()),
        "tolerances_mm": dict(zip(NAMES, TOL.tolist())),
        "ratio_worst_to_actual_9973": round(w["worst_width_mm"] / w["actual_9973_width_mm"], 3),
        "ratio_worst_to_sq_sum": round(w["worst_width_mm"] / w["sq_sum_width_mm"], 3),
        "ratio_sq_sum_to_actual_9973": round(w["sq_sum_width_mm"] / w["actual_9973_width_mm"], 3),
        "ratio_worst_to_batch_range": round(w["worst_width_mm"] / w["batch1000_range_mean_mm"], 3),
        "share_beyond_sq_sum_pct": round(float((np.abs(dev) > sq_half).mean() * 100), 3),
        "share_beyond_half_worst_pct": round(float((np.abs(dev) > worst_half / 2).mean() * 100), 3),
        "share_beyond_worst_pct": round(float((np.abs(dev) > worst_half).mean() * 100), 3),
        "max_abs_dev_of_200000_mm": round(float(np.abs(dev).max()), 4),
        "part_out_of_tol_pct": round(float((np.abs(dev_parts) > TOL).mean() * 100), 3),
        "formula_sd_mm": round(float(np.sqrt(((TOL / 3) ** 2).sum())), 4),
        "worst_half_mm": round(float(worst_half), 4),
        "half_of_worst_half_mm": round(float(worst_half / 2), 4),
        "quantile_low_high_pct": [round(LO * 100, 3), round(HI * 100, 3)],
        "sq_sum_half_mm": round(float(sq_half), 4),
        "ratio_worst_to_sq_sum_equal5_formula": round(float(np.sqrt(5)), 3),
    })
    for key in ["worst_width_mm", "sq_sum_width_mm", "actual_9973_width_mm", "batch1000_range_mean_mm", "batch1000_range_max_mm", "actual_sd_mm"]:
        base[key] = round(base[key], 4)
    # データ：はじめの1,000台
    df = pd.DataFrame(NOM + dev_parts[:1000], columns=["base_mm", "box_a_mm", "box_b_mm", "box_c_mm", "top_mm"]).round(4)
    df.insert(0, "shelf", np.arange(1, 1001))
    df["height_mm"] = (NOM.sum() + dev[:1000]).round(4)
    df.to_csv(DATA / "shelves_first1000.csv", index=False)

    # 確かめ 36通り
    rows = []
    for shape in SHAPES:
        for mix in MIXES:
            for k in [2, 5, 10, 20]:
                tol = tol_for(mix, k)
                d = draw(rng, tol, shape, N).sum(1)
                ww = widths(d, tol)
                rows.append({
                    "part_shape": shape, "tol_mix": mix, "n_parts": k,
                    "worst_width_mm": round(ww["worst_width_mm"], 4),
                    "sq_sum_width_mm": round(ww["sq_sum_width_mm"], 4),
                    "actual_9973_width_mm": round(ww["actual_9973_width_mm"], 4),
                    "batch1000_range_mean_mm": round(ww["batch1000_range_mean_mm"], 4),
                    "ratio_worst_to_actual": round(ww["worst_width_mm"] / ww["actual_9973_width_mm"], 3),
                    "ratio_sq_sum_to_actual": round(ww["sq_sum_width_mm"] / ww["actual_9973_width_mm"], 3),
                    "ratio_worst_to_batch_range": round(ww["worst_width_mm"] / ww["batch1000_range_mean_mm"], 3),
                })
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    robust = {
        "ratio_worst_to_actual_min": float(grid.ratio_worst_to_actual.min()),
        "ratio_worst_to_actual_max": float(grid.ratio_worst_to_actual.max()),
        "ratio_sq_sum_to_actual_min": float(grid.ratio_sq_sum_to_actual.min()),
        "ratio_sq_sum_to_actual_max": float(grid.ratio_sq_sum_to_actual.max()),
        "ratio_worst_to_batch_min": float(grid.ratio_worst_to_batch_range.min()),
        "ratio_worst_to_batch_max": float(grid.ratio_worst_to_batch_range.max()),
        "by_shape": {s: {"ratio_worst_to_actual_min": float(g.ratio_worst_to_actual.min()), "ratio_worst_to_actual_max": float(g.ratio_worst_to_actual.max()),
                         "ratio_sq_sum_to_actual_min": float(g.ratio_sq_sum_to_actual.min()), "ratio_sq_sum_to_actual_max": float(g.ratio_sq_sum_to_actual.max())}
                     for s, g in grid.groupby("part_shape")},
        "by_n_parts": {int(k): {"ratio_worst_to_actual_min": float(g.ratio_worst_to_actual.min()), "ratio_worst_to_actual_max": float(g.ratio_worst_to_actual.max())}
                       for k, g in grid.groupby("n_parts")},
        "n_settings": int(len(grid)),
        "n_settings_worst_gt_actual": int((grid.ratio_worst_to_actual > 1).sum()),
    }
    # 基本の表
    tbl = pd.DataFrame([
        {"measure": "許容差をそのまま足した最悪の幅", "width_mm": base["worst_width_mm"]},
        {"measure": "許容差を二乗で足した幅", "width_mm": base["sq_sum_width_mm"]},
        {"measure": "実際の高さの真ん中99.73%の幅", "width_mm": base["actual_9973_width_mm"]},
        {"measure": "1,000台の最高と最低の差（200組の平均）", "width_mm": base["batch1000_range_mean_mm"]},
    ])
    tbl.to_csv(RES / "base_widths.csv", index=False)

    # 図1：高さのずれの分布
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.hist(dev, bins=120, color=LIGHT, edgecolor="white")
    for x, c, lab in [(worst_half, ORANGE, f"最悪の幅（±{worst_half:.1f}mm）"), (sq_half, BLUE, f"二乗で足した幅（±{round(float(sq_half), 4)}mm）")]:
        ax.axvline(x, color=c, lw=1.6, label=lab); ax.axvline(-x, color=c, lw=1.6)
    ax.set_xlabel("棚の高さの、図面の寸法（980mm）からのずれ（mm）"); ax.set_ylabel("棚の台数")
    ax.set_title("棚20万台の高さのずれ：最悪の幅の端に届く棚はなかった")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1281_hist.png", SRC)

    # 図2：幅の比べ
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    labs = ["許容差を\nそのまま足す", "二乗で足す", "実際の高さの\n真ん中99.73%", "1,000台の\n最高−最低"]
    vals = tbl.width_mm.values
    bars = ax.bar(labs, vals, color=[ORANGE, BLUE, GREEN, GRAY])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v}mm", ha="center", fontsize=10)
    ax.set_ylim(0, vals.max() * 1.15); ax.set_ylabel("幅（mm）")
    ax.set_title("棚の高さの幅（基本の置き方）")
    save(fig, "a1281_widths.png", SRC)

    # 図3：36通り
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.9), sharey=True)
    for ax, (s, lab) in zip(axes, SHAPES.items()):
        g = grid[grid.part_shape == s]
        for (mix, mlab), c in zip(MIXES.items(), [BLUE, ORANGE, GREEN]):
            h = g[g.tol_mix == mix]
            ax.plot(h.n_parts, h.ratio_worst_to_actual, marker="o", color=c, label=mlab)
        ax.axhline(1, color=GRAY, lw=0.8, ls="--")
        ax.set_title(lab, fontsize=11); ax.set_xlabel("部品の数"); ax.set_xticks([2, 5, 10, 20])
    axes[0].set_ylabel("最悪の幅 ÷ 実際の99.73%の幅（倍）"); axes[0].set_ylim(0, grid.ratio_worst_to_actual.max() * 1.1)
    axes[0].legend(frameon=False, fontsize=9, title="許容差の組み合わせ", title_fontsize=9)
    fig.suptitle("最悪の幅は実際の何倍か（36通り）", y=1.02)
    save(fig, "a1281_grid.png", SRC)

    run = round(time.time() - t0, 1)
    out = {"seed": SEED, "n_shelves": N, "batch": BATCH, "base": base, "robust": robust}
    with open(RES / "a1281_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print("sec", run)


if __name__ == "__main__":
    main()
