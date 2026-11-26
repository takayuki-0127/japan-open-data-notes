"""1283 組み立て品の許容差を部品に割り振るとき、二乗の足し算で割り振ると何倍ゆるくでき、外れる組み立て品は何%出るのか？（架空のデータ）

作成者が置いた架空の引き出し付きの小物入れ。5つの部品（底板・引き出しの段×3・天板）を重ね、
重ねた高さの許容差を ±1.0mm と先に決める。部品ごとの許容差 t を同じ大きさで割り振る。
  ・最悪の足し算で割り振る：t＝1.0÷5＝0.2mm（許容差をそのまま足して ±1.0mm）
  ・二乗の足し算で割り振る：t＝1.0÷√5＝0.4472mm（二乗で足して平方根が ±1.0mm）
ゆるくできる倍率は √5＝2.236倍（式どおり）。
部品の作られ方（1個ずつの寸法の散らばり）を4つ置き、組んで ±1.0mm を外れる割合を数える（各100万台）。
  ・正規・標準偏差 t/3（割り振りの前提どおり）
  ・正規・標準偏差 t/4（前提よりよくそろう）
  ・正規・標準偏差 t/2.5（前提より散らばる。部品の許容差を外れるものも組む）
  ・許容差の中で一様（許容差いっぱいに散らばる。部品の許容差は外れない）
平均は図面の寸法どおり（ずれなし）と置く。部品の許容差を外れた部品も除かずに組む。
確かめとして、部品の数（2・3・5・10・20個）×作られ方4つ×割り振り2つの40通り（各40万台）。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1283
SRC = "架空の引き出し付きの小物入れ（作成者が置いた部品の寸法の散らばりからの乱数、seed 1283）"
TA = 1.0
K = 5
N = 1_000_000
NG = 400_000
SHAPES = {"normal_sd_t3": "正規・標準偏差t/3", "normal_sd_t4": "正規・標準偏差t/4",
          "normal_sd_t2_5": "正規・標準偏差t/2.5", "uniform_full": "許容差の中で一様"}
ALLOC = {"worst": "最悪の足し算", "sq_sum": "二乗の足し算"}


def draw(rng, t, k, shape, n):
    if shape == "uniform_full":
        return rng.uniform(-t, t, (n, k))
    div = {"normal_sd_t3": 3, "normal_sd_t4": 4, "normal_sd_t2_5": 2.5}[shape]
    return rng.standard_normal((n, k)) * (t / div)


def part_tol(alloc, k):
    return TA / k if alloc == "worst" else TA / math.sqrt(k)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    keep = {}
    for alloc in ALLOC:
        t = part_tol(alloc, K)
        for shape in SHAPES:
            p = draw(rng, t, K, shape, N)
            s = p.sum(1)
            rows.append({"allocation": alloc, "part_shape": shape, "part_tol_mm": round(t, 4),
                         "out_pct": round(float((np.abs(s) > TA).mean() * 100), 4),
                         "part_out_of_tol_pct": round(float((np.abs(p) > t).mean() * 100), 4),
                         "height_sd_mm": round(float(s.std()), 4),
                         "height_9973_half_mm": round(float((np.quantile(s, 0.99865) - np.quantile(s, 0.00135)) / 2), 4)})
            if alloc == "sq_sum":
                keep[shape] = s[:200000]
            if alloc == "sq_sum" and shape == "normal_sd_t3":
                first = p[:1000]
    tbl = pd.DataFrame(rows)
    tbl.to_csv(RES / "base_k5.csv", index=False)
    tb = tbl.set_index(["allocation", "part_shape"])
    base = {
        "tol_assembly_mm": TA, "n_parts": K,
        "part_tol_worst_mm": round(TA / K, 4), "part_tol_sq_sum_mm": round(TA / math.sqrt(K), 4),
        "looser_times": round(math.sqrt(K), 3),
        "out_pct": {a: {s: float(tb.loc[(a, s), "out_pct"]) for s in SHAPES} for a in ALLOC},
        "part_out_of_tol_pct": {a: {s: float(tb.loc[(a, s), "part_out_of_tol_pct"]) for s in SHAPES} for a in ALLOC},
        "formula_out_pct_sq_sum_sd_t3": round(math.erfc(3 / math.sqrt(2)) * 100, 4),
        "formula_out_pct_sq_sum_sd_t2_5": round(math.erfc(2.5 / math.sqrt(2)) * 100, 4),
        "formula_out_pct_sq_sum_sd_t4": round(math.erfc(4 / math.sqrt(2)) * 100, 4),
        "uniform_sd_vs_t3_times": round(3 / math.sqrt(3), 3),
        "normal_approx_out_pct_sq_sum_uniform": round(math.erfc(math.sqrt(3) / math.sqrt(2)) * 100, 4),
        "height_sd_mm": {a: {s: float(tb.loc[(a, s), "height_sd_mm"]) for s in SHAPES} for a in ALLOC},
    }
    # 許容差いっぱいに一様に散らばる部品で、組み立ての標準偏差の3倍を ±1.0mm に合わせる割り振り
    tu = TA / math.sqrt(3 * K)
    su = rng.uniform(-tu, tu, (N, K)).sum(1)
    base["part_tol_uniform_3sd_mm"] = round(tu, 4)
    base["looser_times_uniform_3sd"] = round(tu / (TA / K), 3)
    base["out_pct_uniform_3sd"] = round(float((np.abs(su) > TA).mean() * 100), 4)
    # データ
    df = pd.DataFrame(first.round(4), columns=["bottom_dev_mm", "drawer1_dev_mm", "drawer2_dev_mm", "drawer3_dev_mm", "top_dev_mm"])
    df.insert(0, "unit", np.arange(1, 1001))
    df["height_dev_mm"] = first.sum(1).round(4)
    df["out_of_tol"] = (np.abs(first.sum(1)) > TA).astype(int)
    df.to_csv(DATA / "sq_sum_alloc_sd_t3_first1000.csv", index=False)

    # 確かめ 40通り
    g = []
    for alloc in ALLOC:
        for shape in SHAPES:
            for k in [2, 3, 5, 10, 20]:
                t = part_tol(alloc, k)
                p = draw(rng, t, k, shape, NG)
                s = p.sum(1)
                g.append({"allocation": alloc, "part_shape": shape, "n_parts": k, "part_tol_mm": round(t, 4),
                          "looser_times": round(math.sqrt(k), 3) if alloc == "sq_sum" else 1.0,
                          "out_pct": round(float((np.abs(s) > TA).mean() * 100), 4),
                          "part_out_of_tol_pct": round(float((np.abs(p) > t).mean() * 100), 4)})
    grid = pd.DataFrame(g)
    grid.to_csv(RES / "grid.csv", index=False)
    gs = grid[grid.allocation == "sq_sum"]
    gw = grid[grid.allocation == "worst"]
    robust = {
        "n_settings": int(len(grid)),
        "looser_times_by_k": {int(k): round(math.sqrt(k), 3) for k in [2, 3, 5, 10, 20]},
        "sq_sum_out_by_shape": {s: {"min": float(h.out_pct.min()), "max": float(h.out_pct.max())} for s, h in gs.groupby("part_shape")},
        "worst_out_max_pct": float(gw.out_pct.max()),
        "worst_out_by_shape_max": {s: float(h.out_pct.max()) for s, h in gw.groupby("part_shape")},
        "looser_times_uniform_3sd_by_k": {k: round(math.sqrt(k / 3), 3) for k in [2, 3, 5, 10, 20]},
        "sq_sum_uniform_by_k": {int(r.n_parts): float(r.out_pct) for r in gs[gs.part_shape == "uniform_full"].itertuples()},
    }

    # 図1：割り振る許容差
    ks = [2, 3, 5, 10, 20]
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    x = np.arange(len(ks)); w = 0.38
    vw = [TA / k for k in ks]; vs = [TA / math.sqrt(k) for k in ks]
    ax.bar(x - w / 2, vw, w, color=ORANGE, label="最悪の足し算（1.0÷部品の数）")
    ax.bar(x + w / 2, vs, w, color=BLUE, label="二乗の足し算（1.0÷√部品の数）")
    for i in range(len(ks)):
        ax.text(x[i] - w / 2, vw[i] + 0.01, f"{round(vw[i], 4)}", ha="center", fontsize=8)
        ax.text(x[i] + w / 2, vs[i] + 0.01, f"{round(vs[i], 4)}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"{k}個" for k in ks]); ax.set_ylim(0, 0.8)
    ax.set_ylabel("部品1つの許容差 ±t（mm）"); ax.set_xlabel("重ねる部品の数")
    ax.set_title("組み立ての許容差±1.0mmを割り振った部品の許容差（式どおり）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1283_part_tol.png", SRC)

    # 図2：5個での外れ
    fig, ax = plt.subplots(figsize=(8, 4.0))
    labs = ["正規\n標準偏差t/4", "正規\n標準偏差t/3", "正規\n標準偏差t/2.5", "許容差の中で\n一様"]
    order = ["normal_sd_t4", "normal_sd_t3", "normal_sd_t2_5", "uniform_full"]
    vw = [tb.loc[("worst", s), "out_pct"] for s in order]; vs = [tb.loc[("sq_sum", s), "out_pct"] for s in order]
    x = np.arange(4)
    ax.bar(x - w / 2, vw, w, color=ORANGE, label="最悪の足し算で割り振る（t＝0.2mm）")
    ax.bar(x + w / 2, vs, w, color=BLUE, label="二乗の足し算で割り振る（t＝0.4472mm）")
    for i in range(4):
        ax.text(x[i] - w / 2, vw[i] + 0.1, f"{vw[i]}%", ha="center", fontsize=8)
        ax.text(x[i] + w / 2, vs[i] + 0.1, f"{vs[i]}%", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylim(0, max(vs) * 1.2)
    ax.set_ylabel("±1.0mmを外れた割合（%）"); ax.set_xlabel("部品の作られ方（1個ずつの寸法の散らばり）")
    ax.set_title("部品5つ・100万台：外れる割合は部品の作られ方で決まる")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1283_out_k5.png", SRC, y=-0.1)

    # 図3：二乗の足し算で割り振ったときの外れ（部品の数ごと）
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for s, c in zip(order, [GREEN, BLUE, ORANGE, INK]):
        h = gs[gs.part_shape == s]
        ax.plot(h.n_parts, h.out_pct, marker="o", color=c, label=SHAPES[s])
    ax.set_xticks(ks); ax.set_ylim(0, gs.out_pct.max() * 1.15)
    ax.set_xlabel("重ねる部品の数"); ax.set_ylabel("±1.0mmを外れた割合（%）")
    ax.set_title("二乗の足し算で割り振ったときの外れ（各40万台）")
    ax.legend(frameon=False, fontsize=9, title="部品の作られ方", title_fontsize=9)
    save(fig, "a1283_grid.png", SRC)

    out = {"seed": SEED, "n_units": N, "base": base, "robust": robust}
    with open(RES / "a1283_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
