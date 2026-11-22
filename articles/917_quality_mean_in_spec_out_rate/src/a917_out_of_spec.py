"""917 寸法の平均が規格の中でも、外れる品物は何%あるのか？（架空のデータ）

架空の工場の樹脂部品の長さ。規格は 50.00 ± 0.10 mm（49.90〜50.10 mm）。
平均と標準偏差、分布の形を作成者が置き、規格から外れる品物の割合を数える。
"""
import json
from statistics import NormalDist
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 917
SRC = "架空の部品の長さ（作成者が乱数で作成、seed 917）"
LSL, USL, NOM = 49.90, 50.10, 50.00
BASE_MEAN, BASE_SD = 50.02, 0.04
ND = NormalDist()
SHAPES = ["山が1つ（正規分布）", "機械2台の混ざり", "すそが重い", "片側に長い"]


def out_normal(mean, sd):
    return ND.cdf((LSL - mean) / sd) + 1 - ND.cdf((USL - mean) / sd)


def cpk(mean, sd):
    return min(USL - mean, mean - LSL) / (3 * sd)


def draw(rng, shape, n, mean=BASE_MEAN, sd=BASE_SD):
    """平均 mean・標準偏差 sd にそろえた4つの形"""
    if shape == SHAPES[0]:
        z = rng.standard_normal(n)
    elif shape == SHAPES[1]:
        # 2台の機械の平均が ±0.75σ ずれ、1台ごとのばらつきは小さい
        d = 0.75
        z = rng.choice([-d, d], n) + rng.normal(0, np.sqrt(1 - d ** 2), n)
    elif shape == SHAPES[2]:
        df = 4
        z = rng.standard_t(df, n) / np.sqrt(df / (df - 2))
    else:
        k = 4.0  # ガンマ分布（形4）：平均 k、分散 k
        z = (rng.gamma(k, 1.0, n) - k) / np.sqrt(k)
    return mean + sd * z


def out_rate(x):
    return float(((x < LSL) | (x > USL)).mean())


def main():
    rng = np.random.default_rng(SEED)

    # 1) 正規分布：平均のずれ × 標準偏差 → 外れる割合（式）
    t1 = []
    for off in [0.00, 0.02, 0.04, 0.06]:
        for sd in [0.02, 0.03, 0.04, 0.05]:
            t1.append({"mean": round(NOM + off, 2), "sd": sd, "out_pct": round(out_normal(NOM + off, sd) * 100, 3),
                       "cpk": round(cpk(NOM + off, sd), 2)})
    t1 = pd.DataFrame(t1)
    t1.to_csv(RES / "normal_out_by_mean_sd.csv", index=False)

    # 2) 形が違うと：平均50.02・標準偏差0.04をそろえた4つの形（各200万個）
    shapes = []
    big = {}
    for i, s in enumerate(SHAPES):
        x = draw(np.random.default_rng(SEED * 10 + i), s, 2_000_000)
        big[s] = x
        shapes.append({"shape": s, "mean": round(float(x.mean()), 4), "sd": round(float(x.std()), 4),
                       "out_pct": round(out_rate(x) * 100, 3), "below_pct": round(float((x < LSL).mean()) * 100, 3),
                       "above_pct": round(float((x > USL).mean()) * 100, 3)})
    shapes = pd.DataFrame(shapes)
    shapes.to_csv(RES / "out_by_shape.csv", index=False)

    # 3) 抜き取り（30個・100個）で読むと：4,000回
    samp = []
    for i, s in enumerate(SHAPES):
        true_out = shapes.loc[i, "out_pct"] / 100
        for n in [30, 100]:
            g = np.random.default_rng(SEED * 100 + i * 10 + n)
            x = np.array([draw(g, s, n) for _ in range(4000)])
            m, sd = x.mean(1), x.std(1, ddof=1)
            cnt = ((x < LSL) | (x > USL)).mean(1)
            est = np.array([out_normal(a, b) for a, b in zip(m, sd)])
            samp.append({"shape": s, "n": n, "true_out_pct": round(true_out * 100, 3),
                         "mean_in_spec_pct": round(float(((m > LSL) & (m < USL)).mean()) * 100, 2),
                         "zero_out_in_sample_pct": round(float((cnt == 0).mean()) * 100, 2),
                         "count_est_mean_pct": round(float(cnt.mean()) * 100, 3),
                         "normal_est_median_pct": round(float(np.median(est)) * 100, 3),
                         "normal_est_p10_pct": round(float(np.quantile(est, .1)) * 100, 3),
                         "normal_est_p90_pct": round(float(np.quantile(est, .9)) * 100, 3),
                         "normal_est_mean_pct": round(float(est.mean()) * 100, 3)})
    samp = pd.DataFrame(samp)
    samp.to_csv(RES / "sample_estimates.csv", index=False)

    # 4) 確かめ：平均のずれ（0・0.02・0.04）× 標準偏差（0.03・0.04・0.05）× 形 で、正規の式と本当の割合
    grid = []
    for off in [0.00, 0.02, 0.04]:
        for sd in [0.03, 0.04, 0.05]:
            for i, s in enumerate(SHAPES):
                x = draw(np.random.default_rng(SEED * 1000 + i + int(off * 100) * 10 + int(sd * 100) * 100), s, 1_000_000,
                         NOM + off, sd)
                grid.append({"mean": round(NOM + off, 2), "sd": sd, "shape": s, "true_out_pct": round(out_rate(x) * 100, 3),
                             "normal_formula_pct": round(out_normal(NOM + off, sd) * 100, 3)})
    grid = pd.DataFrame(grid)
    grid["ratio_true_over_formula"] = (grid.true_out_pct / grid.normal_formula_pct).round(2)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    sens = {"n_settings": int(len(grid) // len(SHAPES)),
            "by_shape_ratio_range": {s: [float(grid[grid["shape"] == s].ratio_true_over_formula.min()),
                                         float(grid[grid["shape"] == s].ratio_true_over_formula.max())] for s in SHAPES},
            "by_shape_true_out_range": {s: [float(grid[grid["shape"] == s].true_out_pct.min()),
                                            float(grid[grid["shape"] == s].true_out_pct.max())] for s in SHAPES},
            "formula_out_range": [float(grid.normal_formula_pct.min()), float(grid.normal_formula_pct.max())]}

    # 1回分（data）：形ごとに1,000個
    rows = []
    for i, s in enumerate(SHAPES):
        x = draw(np.random.default_rng(SEED * 7 + i), s, 1000)
        rows += [{"piece_id": j + 1, "shape": s, "length_mm": round(float(v), 4)} for j, v in enumerate(x)]
    pd.DataFrame(rows).to_csv(DATA / "pieces_by_shape.csv", index=False)

    out = {"settings": {"mix_shift_sd": 0.75, "t_df": 4, "gamma_shape": 4.0, "n_normal_table": int(len(t1)),
                        "pieces_by_shape": 2_000_000, "pieces_grid": 1_000_000, "sample_reps": 4000, "sample_sizes": [30, 100]},
           "spec": {"LSL": LSL, "USL": USL}, "base": {"mean": BASE_MEAN, "sd": BASE_SD,
                                                      "out_pct_normal_formula": round(out_normal(BASE_MEAN, BASE_SD) * 100, 3),
                                                      "below_pct_formula": round(ND.cdf((LSL - BASE_MEAN) / BASE_SD) * 100, 3),
                                                      "above_pct_formula": round((1 - ND.cdf((USL - BASE_MEAN) / BASE_SD)) * 100, 3),
                                                      "cpk": round(cpk(BASE_MEAN, BASE_SD), 3)},
           "normal_table": t1.to_dict("records"), "by_shape": shapes.to_dict("records"),
           "sample_estimates": samp.to_dict("records"), "sensitivity": sens}
    json.dump(out, open(RES / "a917_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：4つの形と規格の線
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 6.0), sharex=True)
    bins = np.linspace(49.80, 50.26, 93)
    for ax, (i, s) in zip(axes.ravel(), enumerate(SHAPES)):
        x = big[s][:400000]
        h, e = np.histogram(x, bins=bins, density=True)
        c = np.where((e[:-1] < LSL) | (e[1:] > USL), ORANGE, BLUE)
        ax.bar(e[:-1], h, width=np.diff(e), align="edge", color=c, lw=0)
        for v in (LSL, USL):
            ax.axvline(v, color=INK, lw=1, ls="--")
        ax.axvline(BASE_MEAN, color=GRAY, lw=1)
        ax.set_title(f"{s}：外れる {shapes.loc[i, 'out_pct']:.2f}%", fontsize=10.5)
        ax.set_yticks([])
    for ax in axes[1]:
        ax.set_xlabel("長さ（mm）。点線が規格 49.90・50.10、灰色の線が平均 50.02")
    fig.suptitle("平均50.02mm・標準偏差0.04mmをそろえても、形で外れる割合が変わる", fontsize=12, y=1.0)
    fig.tight_layout()
    save(fig, "a917_shapes.png", SRC)

    # 図2：正規分布で、平均のずれと標準偏差ごとの外れる割合
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    cols = [LIGHT, BLUE, ORANGE, INK]
    for off, c in zip([0.00, 0.02, 0.04, 0.06], cols):
        sds = np.linspace(0.02, 0.05, 80)
        ax.plot(sds, [out_normal(NOM + off, s_) * 100 for s_ in sds], color=c, label=f"平均 {NOM + off:.2f} mm")
        tt = t1[np.isclose(t1["mean"], NOM + off)]
        ax.plot(tt.sd, tt.out_pct, "o", color=c, ms=4)
    ax.plot(BASE_SD, out_normal(BASE_MEAN, BASE_SD) * 100, "o", color=BLUE)
    ax.annotate(xy=(BASE_SD, out_normal(BASE_MEAN, BASE_SD) * 100), xytext=(0.0408, -0.4),
                arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.8), text=
            f"基本（平均50.02・標準偏差0.04）：{out_normal(BASE_MEAN, BASE_SD)*100:.2f}%", fontsize=9, color=BLUE)
    ax.set_xlabel("標準偏差（mm）"); ax.set_ylabel("規格から外れる割合（%）")
    ax.legend(frameon=False, fontsize=9, title="どの平均も規格の中", title_fontsize=9)
    ax.set_title(f"平均が規格の中でも、外れる割合はほぼ0%から{t1.out_pct.max():.0f}%まで動いた（正規分布の式、表の16通り）", fontsize=11)
    save(fig, "a917_mean_sd.png", SRC)

    # 図3：30個の抜き取りで推定した外れる割合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    s30 = samp[samp.n == 30].reset_index(drop=True)
    y = np.arange(len(s30))[::-1]
    ax.hlines(y, s30.normal_est_p10_pct, s30.normal_est_p90_pct, color=BLUE, lw=5, alpha=.5, label="正規の式で推定（10〜90%の範囲）")
    ax.plot(s30.normal_est_median_pct, y, "|", color=BLUE, ms=14, mew=2, label="正規の式で推定（中央値）")
    ax.plot(s30.true_out_pct, y, "D", color=ORANGE, ms=7, label="本当の外れる割合")
    for yy, z in zip(y, s30.zero_out_in_sample_pct):
        ax.text(9.2, yy, f"30個に外れ0個：{z:.0f}%", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(s30["shape"]); ax.set_xlim(0, 12.5)
    ax.set_xlabel("規格から外れる割合（%）"); ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.45, -0.17), ncol=3)
    ax.set_title("30個の抜き取りでは、推定の幅が広く、形がずれると式は外れる（4,000回）", fontsize=11.5)
    save(fig, "a917_sample30.png", SRC, y=-0.15)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
