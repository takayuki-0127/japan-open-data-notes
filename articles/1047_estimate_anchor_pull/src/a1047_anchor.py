"""1047 先に聞いた数字に、概算はどれだけ引き寄せられるのか？（架空のデータ）

架空の A町で1年に頼まれるエアコンの掃除の件数（本当の値は作成者が置いた 1,900.8件）を、
架空の人たちが4つの要素（世帯数・エアコンのある世帯の割合・1世帯あたりの台数・1年に掃除を頼む割合）
を掛けて概算する。要素ごとの見込みは本当の値のまわりに対数正規で散らばる。
概算の前に「ある数字」（本当の値の a 倍）を聞くと、その人の概算は対数の上で強さ w だけその数字へ寄る：
  log(概算) = (1−w)×log(自分の概算) + w×log(聞いた数字)
w は人ごとに違い、ベータ分布（平均0.3）から引く。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1047
SRC = "架空の A町と架空の概算（作成者が乱数で作成、seed 1047）"
FACT = {"households": 12000, "share_ac": 0.9, "units": 2.2, "rate": 0.08}
TRUE = float(np.prod(list(FACT.values())))   # 1900.8件
SIG_F = 0.35        # 要素ごとの見込みの誤差（対数の標準偏差）
W_MEAN = 0.3        # 引き寄せの強さの平均
W_K = 10.0          # ベータ分布の a+b（人ごとのばらつき）
N_P = 20000
ANCH = [0.1, 1 / 3, 0.5, 1.0, 2.0, 3.0, 10.0]
GROUP_M = [1, 3, 5, 10, 20, 50]
N_GROUP = 4000


def people(rng, n=N_P, sig_f=SIG_F, w_mean=W_MEAN):
    e = rng.normal(0, sig_f, (n, 4))                       # 要素ごとの見込みの誤差（対数）
    own = np.log(TRUE) + e.sum(1)                          # 自分の概算（対数）
    w = rng.beta(w_mean * W_K, (1 - w_mean) * W_K, n)
    return own, w, e


def estimate(own, w, a):
    return (1 - w) * own + w * np.log(TRUE * a)


def miss(logest):
    """外れ（何倍）：本当の値の何倍、または何分の1か（1以上の倍率）"""
    return np.exp(np.abs(logest - np.log(TRUE)))


def crossover(own, w):
    """聞いた数字が本当の値のどこまでなら、外れ（中央値）が聞かないときより小さいか"""
    base = float(np.median(miss(own)))
    grid = 10 ** np.linspace(0, 1.5, 601)
    hi = np.array([np.median(miss(estimate(own, w, a))) for a in grid])
    lo = np.array([np.median(miss(estimate(own, w, 1 / a))) for a in grid])
    def first_over(v):
        i = np.argmax(v > base)
        if v[i] <= base:
            return float("nan")
        # 直線でつなぐ
        x0, x1, y0, y1 = np.log(grid[i - 1]), np.log(grid[i]), v[i - 1], v[i]
        return float(np.exp(x0 + (base - y0) / (y1 - y0) * (x1 - x0)))
    return base, first_over(hi), first_over(lo), grid, hi, lo


def group_within(rng, own, w, a, m, n=N_GROUP, lim=2.0):
    idx = rng.integers(0, len(own), (n, m))
    g = estimate(own[idx], w[idx], a).mean(1)                  # 対数の平均＝幾何平均
    r = miss(g)
    return float((r <= lim).mean()), float(np.median(np.exp(g - np.log(TRUE))))


def main():
    rng = np.random.default_rng(SEED)
    own, w, e = people(rng)

    # 1) 1人ずつの概算：聞いた数字ごと
    rows = []
    for a in [None] + ANCH:
        lg = own if a is None else estimate(own, w, a)
        ratio = np.exp(lg - np.log(TRUE))
        rows.append({"anchor_times_true": "なし" if a is None else round(a, 4),
                     "median_ratio": round(float(np.median(ratio)), 3),
                     "formula_median_ratio": None if a is None else round(float(a ** W_MEAN), 3),
                     "pull_share_of_gap": None if a in (None, 1.0) else round(float(np.median(np.log(ratio)) / np.log(a)), 3),
                     "within2_pct": round(float(((ratio >= .5) & (ratio <= 2)).mean()) * 100, 2),
                     "median_miss_times": round(float(np.median(miss(lg))), 3),
                     "p90_miss_times": round(float(np.quantile(miss(lg), .9)), 3)})
    indiv = pd.DataFrame(rows)
    indiv.to_csv(RES / "individual_by_anchor.csv", index=False)

    # 2) 近い数字なら外れが縮むか（聞かないときとの境目）
    base_miss, a_hi, a_lo, grid, hi, lo = crossover(own, w)
    pd.DataFrame({"anchor_times": np.round(grid, 4), "median_miss_high": np.round(hi, 4),
                  "median_miss_low": np.round(lo, 4)}).to_csv(RES / "crossover_curve.csv", index=False)

    # 3) 何人かの幾何平均でまとめる
    g_rows = []
    for a in [None, 1 / 3, 3.0, 10.0]:
        for m in GROUP_M:
            if a is None:
                idx = rng.integers(0, N_P, (N_GROUP, m)); gl = own[idx].mean(1)
                p2, med = float((miss(gl) <= 2).mean()), float(np.median(np.exp(gl - np.log(TRUE))))
            else:
                p2, med = group_within(rng, own, w, a, m)
            g_rows.append({"anchor_times_true": "なし" if a is None else round(a, 4), "people": m,
                           "within2_pct": round(p2 * 100, 2), "median_ratio": round(med, 3)})
    grp = pd.DataFrame(g_rows)
    grp.to_csv(RES / "group_by_people.csv", index=False)

    # 4) 確かめ：引き寄せの強さと要素の誤差を変える（15通り）
    s_rows = []
    for wm in [0.1, 0.2, 0.3, 0.4, 0.5]:
        for sf in [0.2, 0.35, 0.5]:
            r2 = np.random.default_rng(SEED * 100 + int(wm * 100) + int(sf * 1000))
            o2, w2, _ = people(r2, 10000, sf, wm)
            b2, h2, l2, *_ = crossover(o2, w2)
            l10 = estimate(o2, w2, 10.0)
            p20, _ = group_within(r2, o2, w2, 10.0, 20, 2000)
            p20n = float((miss(o2[r2.integers(0, 10000, (2000, 20))].mean(1)) <= 2).mean())
            s_rows.append({"w_mean": wm, "sig_factor": sf, "own_total_sd": round(sf * 2, 2),
                           "median_ratio_anchor10": round(float(np.median(np.exp(l10 - np.log(TRUE)))), 3),
                           "within2_pct_none": round(float((miss(o2) <= 2).mean()) * 100, 2),
                           "within2_pct_anchor10": round(float((miss(l10) <= 2).mean()) * 100, 2),
                           "group20_within2_pct_none": round(p20n * 100, 2),
                           "group20_within2_pct_anchor10": round(p20 * 100, 2),
                           "median_miss_none": round(b2, 3),
                           "helps_up_to_high_times": round(h2, 3), "helps_down_to_low_times": round(l2, 3)})
    sens = pd.DataFrame(s_rows)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    pd.DataFrame({"person": np.arange(1, 2001), "own_estimate": np.round(np.exp(own[:2000]), 1),
                  "pull_w": np.round(w[:2000], 4),
                  "est_anchor_x10": np.round(np.exp(estimate(own[:2000], w[:2000], 10.0)), 1),
                  "est_anchor_x0_1": np.round(np.exp(estimate(own[:2000], w[:2000], 0.1)), 1)}
                 ).to_csv(DATA / "people_2000.csv", index=False)

    def rng_of(col):
        return [round(float(sens[col].min()), 3), round(float(sens[col].max()), 3)]
    out = {"true_count": round(TRUE, 1), "factors": FACT, "sig_factor": SIG_F, "factor_error_times_1sd": round(float(np.exp(SIG_F)), 3), "own_total_sd": SIG_F * 2,
           "w_mean_set": W_MEAN, "w_mean_drawn": round(float(w.mean()), 4), "w_median_drawn": round(float(np.median(w)), 4),
           "own_median_ratio": round(float(np.median(np.exp(own - np.log(TRUE)))), 3),
           "individual": indiv.to_dict("records"),
           "crossover": {"median_miss_none": round(base_miss, 3), "helps_up_to_high_times": round(a_hi, 3),
                         "helps_down_to_low_times": round(a_lo, 3),
                         "median_miss_at_true": round(float(np.median(miss(estimate(own, w, 1.0)))), 3)},
           "group": grp.to_dict("records"),
           "sensitivity_range_15": {c: rng_of(c) for c in ["median_ratio_anchor10", "within2_pct_anchor10",
                                                            "group20_within2_pct_anchor10", "group20_within2_pct_none",
                                                            "helps_up_to_high_times", "helps_down_to_low_times"]},
           "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a1047_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：聞いた数字ごとの、概算の中央値（本当の値の何倍か）
    lab = ["聞かない", "1/10倍", "1/3倍", "1/2倍", "同じ", "2倍", "3倍", "10倍"]
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    v = indiv.median_ratio.values
    col = [GRAY] + [BLUE if x < 1 else (GRAY if x == 1 else ORANGE) for x in ANCH]
    ax.bar(lab, v, color=col)
    for i, x in enumerate(v):
        ax.text(i, x + 0.03, f"{x:.2f}倍", ha="center", fontsize=9)
    ax.axhline(1, color=INK, lw=.8)
    ax.set_ylim(0, max(v) * 1.15); ax.set_ylabel("概算の中央値（本当の値の何倍か）")
    ax.set_xlabel("先に聞いた数字（本当の値の何倍か）")
    ax.set_title("聞いた数字の方向へ、概算の中央値が動く（引き寄せの強さ 平均0.3）")
    save(fig, "a1047_median_by_anchor.png", SRC, y=-0.04)

    # 図2：近い数字なら外れが縮む（境目）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    xs = np.concatenate([1 / grid[::-1], grid[1:]]); ys = np.concatenate([lo[::-1], hi[1:]])
    ax.plot(xs, ys, color=BLUE, lw=2, label="先に数字を聞いた")
    ax.axhline(base_miss, color=ORANGE, ls="--", lw=1.2, label=f"聞かない（{base_miss:.2f}倍）")
    ax.axvline(a_hi, color=GRAY, lw=.8, ls=":"); ax.axvline(1 / a_lo, color=GRAY, lw=.8, ls=":")
    ax.text(a_hi * 1.05, base_miss * 0.92, f"{a_hi:.2f}倍", fontsize=9, color=INK)
    ax.text(0.95 / a_lo, base_miss * 0.92, f"{a_lo:.2f}分の1", fontsize=9, color=INK, ha="right")
    ax.set_xscale("log"); ax.set_xlim(1 / 31.6, 31.6); ax.set_ylim(1, max(ys) * 1.05)
    ax.set_xticks([1 / 30, 0.1, 1 / 3, 1, 3, 10, 30]); ax.set_xticklabels(["1/30", "1/10", "1/3", "1", "3", "10", "30"])
    ax.set_xlabel("先に聞いた数字（本当の値の何倍か、対数の目盛り）"); ax.set_ylabel("1人の概算の外れの中央値（何倍）")
    ax.legend(frameon=False, fontsize=9, loc="upper center")
    ax.set_title("聞いた数字が本当の値に近ければ外れは縮み、遠ければ広がる")
    save(fig, "a1047_crossover.png", SRC, y=-0.04)

    # 図3：何人まとめても、引き寄せは残る
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    names = {"なし": ("聞かない", GRAY), 3.0: ("3倍を聞いた", LIGHT), 10.0: ("10倍を聞いた", ORANGE),
             0.3333: ("1/3倍を聞いた", BLUE)}
    for key, (nm, c) in names.items():
        d = grp[grp.anchor_times_true == key]
        ax.plot(d.people, d.median_ratio, marker="o", color=c, lw=2, label=nm)
        ax.text(52, d.median_ratio.iloc[-1], f"{d.median_ratio.iloc[-1]:.2f}倍", va="center", fontsize=9)
    ax.set_xscale("log"); ax.set_xticks(GROUP_M); ax.set_xticklabels([str(m) for m in GROUP_M])
    ax.set_ylim(0, 2.4); ax.set_xlim(0.8, 75); ax.set_xlabel("まとめた人数（幾何平均、対数の目盛り）")
    ax.set_ylabel("まとめた概算の中央値（本当の値の何倍か）")
    ax.axhline(1, color=INK, lw=.8)
    ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=2)
    ax.set_title("人数を増やしても、10倍の数字に引き寄せられた分は消えない")
    save(fig, "a1047_group.png", SRC, y=-0.04)
    print(json.dumps({k: out[k] for k in ["individual", "crossover", "sensitivity_range_15"]}, ensure_ascii=False, indent=1))
    print(grp)


if __name__ == "__main__":
    main()
