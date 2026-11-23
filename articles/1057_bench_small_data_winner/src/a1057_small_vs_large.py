"""1057 小さいデータで速かった方法は、大きいデータでも速いのか？（架空のデータ）

架空のアプリで、同じ結果を出す2つの方法の処理時間（ミリ秒）を、作成者が置いた式から作る。
処理時間＝準備の時間＋1件あたりの時間×件数（件数とともに1件あたりも伸びることがある）
　　　　　＋件数が「速く読める量」の境目を超えた分の上乗せ。
小さい件数で測って速かった方を、大きい件数（100万件）でも速いとみなすと、何回に1回まちがえるかを数える。
測るときの振れ（1回ごとに約10%、5回測った中央値）を入れる。実機の計測はしていない。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1057
SRC = "架空の2つの方法の処理時間（作成者が置いた式と乱数、seed 1057）"
TARGET = 1_000_000
TESTS = [1_000, 10_000, 100_000, 300_000]
NOISE = 0.10
REPS = 5
NPAIR = 4000
BASE = {"c0_range_ms": [0.01, 10.0], "c1_range_ms": [1e-4, 1e-2], "alpha_max": 1.3, "cache_prob": 0.5,
        "cache_jump_range": [0.5, 4.0], "cache_K_range": [1e4, 1e6]}


def r(x, d=4):
    return round(float(x), d)


def logu(rng, lo, hi, n):
    return np.exp(rng.uniform(np.log(lo), np.log(hi), n))


def make_methods(rng, n, kw):
    c0 = logu(rng, *kw["c0_range_ms"], n)
    c1 = logu(rng, *kw["c1_range_ms"], n)
    alpha = rng.uniform(1.0, kw["alpha_max"], n)
    has = rng.random(n) < kw["cache_prob"]
    jump = np.where(has, rng.uniform(*kw["cache_jump_range"], n), 0.0)
    K = logu(rng, *kw["cache_K_range"], n)
    return pd.DataFrame({"c0": c0, "c1": c1, "alpha": alpha, "jump": jump, "K": K})


def tfun(m, size):
    size = np.asarray(size, float)
    grow = (size / 1000.0) ** (m["alpha"].values[:, None] - 1) if size.ndim else (size / 1000.0) ** (m["alpha"].values - 1)
    if size.ndim:
        s = size[None, :]
        c0, c1, j, K = (m[c].values[:, None] for c in ["c0", "c1", "jump", "K"])
    else:
        s = size
        c0, c1, j, K = (m[c].values for c in ["c0", "c1", "jump", "K"])
    return c0 + c1 * grow * (s + j * np.maximum(0, s - K))


def measure(rng, true_t):
    """5回測った中央値（1回ごとに対数で標準偏差 NOISE の振れ）"""
    x = true_t[..., None] * np.exp(rng.normal(0, NOISE, true_t.shape + (REPS,)))
    return np.median(x, axis=-1)


def evaluate(rng, kw, npair=NPAIR):
    A, B = make_methods(rng, npair, kw), make_methods(rng, npair, kw)
    sizes = np.array(TESTS + [TARGET])
    tA, tB = tfun(A, sizes), tfun(B, sizes)
    mA, mB = measure(rng, tA), measure(rng, tB)
    true_win = tA[:, -1] < tB[:, -1]                      # True なら A が100万件で速い
    gap = np.maximum(tA[:, -1], tB[:, -1]) / np.minimum(tA[:, -1], tB[:, -1])
    big = gap >= 1.2
    res = {}
    for i, s in enumerate(TESTS):
        pick = mA[:, i] < mB[:, i]
        pick0 = tA[:, i] < tB[:, i]
        res[f"flip_{s}"] = float((pick != true_win).mean())
        res[f"flip_{s}_gap12"] = float((pick != true_win)[big].mean())
        res[f"flip_nonoise_{s}"] = float((pick0 != true_win).mean())
    # 小さい件数の差が大きくても入れかわるか（1,000件で2倍以上の差）
    ratio1k = np.maximum(mA[:, 0], mB[:, 0]) / np.minimum(mA[:, 0], mB[:, 0])
    pick1k = mA[:, 0] < mB[:, 0]
    res["share_ratio1k_ge2"] = float((ratio1k >= 2).mean())
    res["flip_1000_when_ratio_ge2"] = float((pick1k != true_win)[ratio1k >= 2].mean())
    res["flip_1000_when_ratio_lt12"] = float((pick1k != true_win)[ratio1k < 1.2].mean())
    # 見込み方：1,000件と1万件の2点で「準備＋1件あたり×件数」の直線を引く／3点（1,000・1万・10万件）で対数の直線を引く
    lin = {}
    for nm, (mm) in [("A", mA), ("B", mB)]:
        s1, s2 = TESTS[0], TESTS[1]
        slope = (mm[:, 1] - mm[:, 0]) / (s2 - s1)
        icpt = np.maximum(mm[:, 0] - slope * s1, 0)
        lin[nm + "_line2"] = icpt + slope * TARGET
        x = np.log(np.array(TESTS[:3], float))
        y = np.log(mm[:, :3])
        b = ((x - x.mean()) * (y - y.mean(1, keepdims=True))).sum(1) / ((x - x.mean()) ** 2).sum()
        a = y.mean(1) - b * x.mean()
        lin[nm + "_loglog3"] = np.exp(a + b * np.log(TARGET))
        lin[nm + "_prop1k"] = mm[:, 0] * TARGET / TESTS[0]
    for k in ["prop1k", "line2", "loglog3"]:
        pick = lin["A_" + k] < lin["B_" + k]
        res[f"flip_pred_{k}"] = float((pick != true_win).mean())
        err = np.r_[lin["A_" + k] / tA[:, -1], lin["B_" + k] / tB[:, -1]]
        res[f"pred_{k}_median_abs_log10"] = float(np.median(np.abs(np.log10(err))))
        res[f"pred_{k}_median_fold"] = float(10 ** np.median(np.abs(np.log10(err))))
        res[f"pred_{k}_within2x"] = float(((err >= 0.5) & (err <= 2)).mean())
        res[f"pred_{k}_under_share"] = float((err < 1).mean())
    res["share_gap12"] = float(big.mean())
    # 10万件で試したときの取りちがえ：10万件より上に境目のある上乗せを持つ組か
    hidden = ((A["jump"].values > 0) & (A["K"].values > TESTS[2])) | ((B["jump"].values > 0) & (B["K"].values > TESTS[2]))
    flip100k = (mA[:, 2] < mB[:, 2]) != true_win
    res["share_hidden_cache_pairs"] = float(hidden.mean())
    res["flip_100000_hidden_cache"] = float(flip100k[hidden].mean())
    res["flip_100000_no_hidden_cache"] = float(flip100k[~hidden].mean())
    res["flip_100000_from_hidden_share"] = float((flip100k & hidden).sum() / flip100k.sum())
    return res, A, B, tA, tB, mA, mB


def main():
    rng = np.random.default_rng(SEED)
    kw = BASE

    # 1) 例：準備のない方法 A と、準備に2msかかる方法 B（式どおりの値）
    sizes_ex = np.unique(np.round(np.logspace(2, 7, 61)).astype(int))
    def ex_A(n):
        return 0.0005 * n + 0.0015 * np.maximum(0, n - 50000)
    def ex_B(n):
        return 2.0 + 0.0009 * n
    nn = np.arange(1000, 2_000_000)
    cross = int(nn[np.argmax(ex_A(nn) > ex_B(nn))])
    ex = {"A_1000": r(ex_A(1000), 3), "B_1000": r(ex_B(1000), 3), "A_1e6": r(ex_A(TARGET), 1),
          "B_1e6": r(ex_B(TARGET), 1), "ratio_1000_B_over_A": r(ex_B(1000) / ex_A(1000), 2),
          "ratio_1e6_A_over_B": r(ex_A(TARGET) / ex_B(TARGET), 2), "crossover_n": cross, "crossover_formula_n": 77000 / 1.1,
          "A_prop_from_1000": r(ex_A(1000) * 1000, 1), "B_prop_from_1000": r(ex_B(1000) * 1000, 1),
          "A_prop_over_true": r(ex_A(1000) * 1000 / ex_A(TARGET), 3), "B_prop_over_true": r(ex_B(1000) * 1000 / ex_B(TARGET), 3)}
    pd.DataFrame({"n": sizes_ex, "A_ms": np.round(ex_A(sizes_ex), 4), "B_ms": np.round(ex_B(sizes_ex), 4)}).to_csv(
        RES / "example_two_methods.csv", index=False)

    # 2) 基本：方法の組4,000組
    res, A, B, tA, tB, mA, mB = evaluate(rng, kw)
    pairs = pd.DataFrame({"pair_id": np.arange(1, NPAIR + 1)})
    for nm, m, t, mm in [("A", A, tA, mA), ("B", B, tB, mB)]:
        for c in ["c0", "c1", "alpha", "jump", "K"]:
            pairs[f"{nm}_{c}"] = m[c].round(6).values
        for i, s in enumerate(TESTS + [TARGET]):
            pairs[f"{nm}_true_{s}"] = np.round(t[:, i], 4)
        for i, s in enumerate(TESTS):
            pairs[f"{nm}_meas_{s}"] = np.round(mm[:, i], 4)
    pairs.to_csv(DATA / "method_pairs.csv", index=False)
    base = pd.DataFrame([{"test_n": s, "flip": r(res[f"flip_{s}"]), "flip_gap12": r(res[f"flip_{s}_gap12"]),
                          "flip_nonoise": r(res[f"flip_nonoise_{s}"])} for s in TESTS])
    base.to_csv(RES / "flip_by_test_size.csv", index=False)
    preds = pd.DataFrame([{"method": k, "flip": r(res[f"flip_pred_{k}"]),
                           "median_abs_log10_err": r(res[f"pred_{k}_median_abs_log10"]),
                           "median_fold_err": r(res[f"pred_{k}_median_fold"], 3),
                           "within2x": r(res[f"pred_{k}_within2x"]), "under_share": r(res[f"pred_{k}_under_share"])}
                          for k in ["prop1k", "line2", "loglog3"]])
    preds.to_csv(RES / "prediction_methods.csv", index=False)

    # 3) 置き方を変えると（27通り）
    grid = []
    gi = 0
    for am in [1.0, 1.3, 1.6]:
        for cp in [0.0, 0.5, 1.0]:
            for c0max in [1.0, 10.0, 100.0]:
                g = dict(kw, alpha_max=am + 1e-9, cache_prob=cp, c0_range_ms=[0.01, c0max])
                rr, *_ = evaluate(np.random.default_rng(SEED * 100 + gi), g, 3000)
                gi += 1
                grid.append({"alpha_max": am, "cache_prob": cp, "c0_max_ms": c0max,
                             **{f"flip_{s}": r(rr[f"flip_{s}"]) for s in TESTS},
                             "flip_pred_loglog3": r(rr["flip_pred_loglog3"]), "flip_pred_line2": r(rr["flip_pred_line2"])})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    def rng_of(c):
        return [r(grid[c].min()), r(grid[c].max())]

    nolin = grid[(grid.alpha_max == 1.0) & (grid.cache_prob == 0.0)]
    oth = grid.drop(nolin.index)
    out = {"base_setting": BASE, "target_n": TARGET, "tests": TESTS, "noise_log_sd": NOISE, "reps_median": REPS,
           "n_pairs": NPAIR, "grid_pairs": 3000, "example": ex, "base": {k: r(v) for k, v in res.items()},
           "grid_ranges": {c: rng_of(c) for c in ["flip_1000", "flip_10000", "flip_100000", "flip_300000",
                                                   "flip_pred_loglog3", "flip_pred_line2"]},
           "grid_linear_nocache_flip_1000": rng_of_sub(nolin, "flip_1000"),
           "grid_loglog_better_than_1k_count": int((grid.flip_pred_loglog3 < grid.flip_1000).sum()),
           "grid_linear_nocache_line2": rng_of_sub(nolin, "flip_pred_line2"),
           "grid_other24_line2_worse_than_loglog_count": int((oth.flip_pred_line2 > oth.flip_pred_loglog3).sum()),
           "headline": {"ex_ratio_1000": ex["ratio_1000_B_over_A"], "ex_ratio_1e6": ex["ratio_1e6_A_over_B"],
                        "ex_cross": cross,
                        "flip_1000_pct": r(res["flip_1000"] * 100, 1), "flip_100000_pct": r(res["flip_100000"] * 100, 1),
                        "flip_1000_gap12_pct": r(res["flip_1000_gap12"] * 100, 1),
                        "flip_1000_ratio_ge2_pct": r(res["flip_1000_when_ratio_ge2"] * 100, 1),
                        "flip_loglog3_pct": r(res["flip_pred_loglog3"] * 100, 1),
                        "grid_flip_1000_pct": [r(grid.flip_1000.min() * 100, 1), r(grid.flip_1000.max() * 100, 1)]}}
    json.dump(out, open(RES / "a1057_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の2つの方法
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    ax.plot(sizes_ex, ex_A(sizes_ex), color=BLUE, lw=2, label="方法A（準備なし、5万件を超えると1件あたり4倍）")
    ax.plot(sizes_ex, ex_B(sizes_ex), color=ORANGE, lw=2, label="方法B（準備2ms＋1件あたり0.0009ms）")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.axvline(cross, color=GRAY, ls="--", lw=1)
    ax.text(cross * 1.1, 0.08, f"入れかわる件数\n約{round(cross, -3):,}件", color=GRAY, fontsize=9)
    for s in [1000, TARGET]:
        ax.scatter([s, s], [ex_A(s), ex_B(s)], color=[BLUE, ORANGE], zorder=3, s=25)
    ax.text(1000, ex_B(1000) * 2.4, f"1,000件：Aが{ex['ratio_1000_B_over_A']}倍速い", ha="center", fontsize=9)
    ax.text(TARGET, ex_A(TARGET) * 1.8, f"100万件：Bが{ex['ratio_1e6_A_over_B']}倍速い", ha="center", fontsize=9)
    ax.set_xlabel("件数（対数の目盛り）"); ax.set_ylabel("処理時間（ms、対数の目盛り）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("1,000件で速かったAは、100万件ではBより遅い（式どおり）")
    save(fig, "a1057_example.png", SRC)

    # 図2：試した件数ごとの入れかわり
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    pos = np.arange(len(TESTS)); w = 0.38
    v1, v2 = base.flip * 100, base.flip_gap12 * 100
    ax.bar(pos - w / 2, v1, w, color=BLUE, label="すべての組")
    ax.bar(pos + w / 2, v2, w, color=ORANGE, label="100万件で1.2倍以上の差がある組")
    for i in range(len(TESTS)):
        ax.text(pos[i] - w / 2, v1[i] + 0.6, f"{v1[i]:.1f}%", ha="center", fontsize=8.5)
        ax.text(pos[i] + w / 2, v2[i] + 0.6, f"{v2[i]:.1f}%", ha="center", fontsize=8.5)
    ax.set_xticks(pos, [f"{s:,}件で試す" for s in TESTS])
    ax.set_ylim(0, max(v1.max(), v2.max()) * 1.25)
    ax.set_ylabel("100万件での速い方とちがった割合（%）")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("試す件数が本番から遠いほど、速い方を取りちがえる（4,000組）")
    save(fig, "a1057_flip.png", SRC)

    # 図3：見込み方ごとの取りちがえ（27通りの範囲つき）
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    labs = ["1,000件だけで比べる", "1,000件と1万件の2点で\n準備＋件数の直線", "1,000・1万・10万件の\n3点で対数の直線"]
    vals = [res["flip_1000"] * 100, res["flip_pred_line2"] * 100, res["flip_pred_loglog3"] * 100]
    lo = [grid.flip_1000.min() * 100, grid.flip_pred_line2.min() * 100, grid.flip_pred_loglog3.min() * 100]
    hi = [grid.flip_1000.max() * 100, grid.flip_pred_line2.max() * 100, grid.flip_pred_loglog3.max() * 100]
    y = np.arange(3)[::-1]
    ax.barh(y, vals, color=[GRAY, LIGHT, BLUE])
    ax.errorbar(vals, y, xerr=[np.array(vals) - lo, np.array(hi) - vals], fmt="none", ecolor=INK, capsize=4, lw=1)
    for yy, v, h in zip(y, vals, hi):
        ax.text(h + 0.8, yy, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_yticks(y, labs, fontsize=9)
    ax.set_xlim(0, max(hi) * 1.25)
    ax.set_xlabel("100万件での速い方とちがった割合（%、棒は基本、線は27通りの範囲）")
    ax.set_title("大きい件数まで何点か測って見込むと、取りちがえは減る")
    save(fig, "a1057_predict.png", SRC)
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(base); print(preds); print(json.dumps(out["grid_ranges"]))


def rng_of_sub(df, c):
    return [r(df[c].min()), r(df[c].max())]


if __name__ == "__main__":
    main()
