"""1301 決まった長さの棒から長さの違う部品を切り出すと、余りの割合は、部品の長さの組み合わせしだいでどれだけ変わるのか？（架空のデータ）

作成者が置いた架空の通販。長さを指定して注文できる棒を、長さ400cmの材料の棒から切り出して発送する。
1日の注文は部品60本（基本）。切るときの刃の幅（切りしろ）は0と置く。1本の材料の棒の残りは、その日のうちに
ほかの部品に使えなければ余りとする（次の日に持ち越さない）。
余りの割合＝（使った材料の棒の本数×400−部品の長さの合計）÷（使った材料の棒の本数×400）。
①部品が1つの長さだけ（30〜400cm、1cmきざみ）：1本から取れる数で決まる（式どおり）
②部品が2つの長さ（30〜250cm、10cmきざみの組、各30本）：いちばん少ない本数（すべての切り方を調べた）と、長さごとに別々に切ったときの本数
③部品の長さが k 通り（1・2・3・5・10・20通り、30〜250cmの整数から乱数）：大きい順に並べてから、入る最初の棒から切る。
   下限は切り上げ（部品の長さの合計÷400）。500日分。
確かめ：材料の長さ（300・400・600cm）×1日の本数（30・60・120本）×部品の長さの範囲（30〜150・30〜250・100〜300cm）の27通り。
"""
import json
import time
from functools import lru_cache
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1301
SRC = "架空の通販の棒の切り出し（作成者が置いた部品の長さ・本数と材料の長さからの乱数、seed 1301）"
L = 400
N_PARTS = 60
KS = [1, 2, 3, 5, 10, 20]
DAYS = 500
DAYS_GRID = 200


def pack_sorted(lengths, cap):
    order = np.argsort(-np.asarray(lengths), kind="stable")
    rem = []
    for i in order:
        s = lengths[i]
        for j in range(len(rem)):
            if rem[j] >= s:
                rem[j] -= s
                break
        else:
            rem.append(cap - s)
    return len(rem)


def waste_pct(rods, total, cap):
    return 100 * (rods * cap - total) / (rods * cap)


def single(cap, n):
    rows = []
    for p in range(30, cap + 1):
        m = cap // p
        rods = -(-n // m)
        rows.append({"part_cm": p, "per_rod": m, "rods": rods, "leftover_pct": round(waste_pct(rods, p * n, cap), 3)})
    return pd.DataFrame(rows)


def pair_exact(p1, p2, n1, n2, cap):
    pats = []
    for a in range(cap // p1 + 1):
        b = (cap - a * p1) // p2
        if a + b > 0:
            pats.append((a, b))          # 1本の棒で、p1 を a 本取ったあと p2 を取れるだけ取る切り方（ほかの切り方はこれより少ない）

    @lru_cache(maxsize=None)
    def f(x, y):
        if x <= 0 and y <= 0:
            return 0
        best = 10 ** 9
        for a, b in pats:
            # 取れる本数より要る本数が少なければ、その分は切らない（短く切るだけなので本数は変わらない）
            if (a > 0 and x > 0) or (b > 0 and y > 0):
                best = min(best, 1 + f(max(x - a, 0), max(y - b, 0)))
        return best
    return f(n1, n2)


def mixture_day(rng, k, n, lo, hi, cap):
    lens = rng.integers(lo, hi + 1, k)
    cnt = rng.multinomial(n, np.full(k, 1 / k))
    parts = np.repeat(lens, cnt)
    tot = int(parts.sum())
    rods = pack_sorted(parts, cap)
    lb = -(-tot // cap)
    return waste_pct(rods, tot, cap), waste_pct(lb, tot, cap), rods - lb


def mixture(k, n, lo, hi, cap, days, seed):
    rng = np.random.default_rng(seed)
    r = np.array([mixture_day(rng, k, n, lo, hi, cap) for _ in range(days)])
    return {"k": k, "leftover_mean_pct": round(float(r[:, 0].mean()), 2),
            "leftover_p10_pct": round(float(np.percentile(r[:, 0], 10)), 2),
            "leftover_p90_pct": round(float(np.percentile(r[:, 0], 90)), 2),
            "lower_bound_leftover_mean_pct": round(float(r[:, 1].mean()), 2),
            "rods_over_lower_bound_mean": round(float(r[:, 2].mean()), 3),
            "days_at_lower_bound_pct": round(float(100 * (r[:, 2] == 0).mean()), 1)}


def main():
    t0 = time.time()
    # ① 1つの長さ
    s1 = single(L, N_PARTS)
    s1.to_csv(RES / "single_length.csv", index=False)
    ex = {str(p): s1[s1.part_cm == p].iloc[0].to_dict() for p in [100, 101, 133, 134, 200, 201]}
    ex = {k: {kk: (float(v) if kk == "leftover_pct" else int(v)) for kk, v in d.items()} for k, d in ex.items()}
    s1r = s1[s1.part_cm <= 250]
    single_sum = {"range_30_400": [float(s1.leftover_pct.min()), float(s1.leftover_pct.max())],
                  "range_30_250": [float(s1r.leftover_pct.min()), float(s1r.leftover_pct.max())],
                  "share_over_10pct_30_250": round(float(100 * (s1r.leftover_pct > 10).mean()), 2),
                  "mean_30_250": round(float(s1r.leftover_pct.mean()), 2), "examples": ex}

    # ② 2つの長さ（各30本）
    rows = []
    L2 = list(range(30, 251, 10))
    for i, p1 in enumerate(L2):
        for p2 in L2[i + 1:]:
            hi, lo_ = max(p1, p2), min(p1, p2)
            best = pair_exact(hi, lo_, 30, 30, L)
            sep = -(-30 // (L // p1)) + -(-30 // (L // p2))
            parts = np.array([p1] * 30 + [p2] * 30)
            f = pack_sorted(parts, L)
            tot = 30 * (p1 + p2)
            rows.append({"p1_cm": p1, "p2_cm": p2, "rods_best": best, "rods_separate": sep, "rods_sorted": f,
                         "leftover_best_pct": round(waste_pct(best, tot, L), 3),
                         "leftover_separate_pct": round(waste_pct(sep, tot, L), 3),
                         "leftover_sorted_pct": round(waste_pct(f, tot, L), 3),
                         "lower_bound_rods": -(-tot // L)})
    pr = pd.DataFrame(rows)
    pr.to_csv(RES / "pair_lengths.csv", index=False)
    pair_sum = {"pairs": len(pr),
                "leftover_best_pct": [float(pr.leftover_best_pct.min()), float(pr.leftover_best_pct.max())],
                "leftover_best_median_pct": round(float(pr.leftover_best_pct.median()), 3),
                "leftover_separate_pct": [float(pr.leftover_separate_pct.min()), float(pr.leftover_separate_pct.max())],
                "leftover_separate_median_pct": round(float(pr.leftover_separate_pct.median()), 3),
                "best_lt_separate_share_pct": round(float(100 * (pr.rods_best < pr.rods_separate).mean()), 2),
                "best_over_10pct_share_pct": round(float(100 * (pr.leftover_best_pct > 10).mean()), 2),
                "sorted_eq_best_share_pct": round(float(100 * (pr.rods_sorted == pr.rods_best).mean()), 2),
                "sorted_minus_best_max": int((pr.rods_sorted - pr.rods_best).max()),
                "best_eq_lower_bound_share_pct": round(float(100 * (pr.rods_best == pr.lower_bound_rods).mean()), 2)}
    worst = pr.sort_values(["leftover_best_pct", "p1_cm"], ascending=[False, True]).head(3)
    pair_sum["worst3"] = worst[["p1_cm", "p2_cm", "rods_best", "leftover_best_pct"]].to_dict("records")
    p130 = pr[(pr.p1_cm == 130) & (pr.p2_cm == 140)]
    p210 = pr[(pr.p1_cm == 200) & (pr.p2_cm == 210)]
    pair_sum["ex_130_140"] = p130.iloc[0].to_dict()
    pair_sum["ex_200_210"] = p210.iloc[0].to_dict()

    # ③ k 通りの長さをまぜた日
    mx = pd.DataFrame([mixture(k, N_PARTS, 30, 250, L, DAYS, SEED * 10 + k) for k in KS])
    mx.to_csv(RES / "mixture_by_k.csv", index=False)

    # 1日目（k=5）の部品と切り方
    rng = np.random.default_rng(SEED)
    lens = rng.integers(30, 251, 5); cnt = rng.multinomial(N_PARTS, np.full(5, 0.2))
    parts = np.repeat(lens, cnt)
    pd.DataFrame({"part": np.arange(1, len(parts) + 1), "length_cm": parts}).to_csv(DATA / "day_k5_parts.csv", index=False)
    tot5 = int(parts.sum()); rods5 = pack_sorted(parts, L); lb5 = -(-tot5 // L)
    example_day = {"lengths_cm": [int(v) for v in lens], "counts": [int(v) for v in cnt], "total_cm": tot5,
                   "rods_sorted": int(rods5), "rods_lower_bound": int(lb5),
                   "leftover_sorted_pct": round(waste_pct(rods5, tot5, L), 2),
                   "leftover_lower_bound_pct": round(waste_pct(lb5, tot5, L), 2)}

    # 確かめ：27通り（k=1 と k=5）
    grid = []
    i = 0
    for cap in [300, 400, 600]:
        for n in [30, 60, 120]:
            for lo, hi in [(30, 150), (30, 250), (100, 300)]:
                r1 = mixture(1, n, lo, hi, cap, DAYS_GRID, SEED * 1000 + i)
                r5 = mixture(5, n, lo, hi, cap, DAYS_GRID, SEED * 1000 + 500 + i)
                i += 1
                grid.append({"rod_cm": cap, "parts_per_day": n, "length_range_cm": f"{lo}〜{hi}",
                             "k1_leftover_mean_pct": r1["leftover_mean_pct"], "k1_p10_pct": r1["leftover_p10_pct"],
                             "k1_p90_pct": r1["leftover_p90_pct"],
                             "k5_leftover_mean_pct": r5["leftover_mean_pct"], "k5_p10_pct": r5["leftover_p10_pct"],
                             "k5_p90_pct": r5["leftover_p90_pct"],
                             "k5_lower_bound_mean_pct": r5["lower_bound_leftover_mean_pct"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    mm = lambda c, g=grid: [float(g[c].min()), float(g[c].max())]
    rob = {"settings": len(grid), "k1_leftover_mean_pct": mm("k1_leftover_mean_pct"),
           "k5_leftover_mean_pct": mm("k5_leftover_mean_pct"),
           "k1_p90_pct_max": float(grid.k1_p90_pct.max()), "k5_p90_pct_max": float(grid.k5_p90_pct.max()),
           "k5_lt_k1_settings": int((grid.k5_leftover_mean_pct < grid.k1_leftover_mean_pct).sum()),
           "k1_by_range": {r: mm("k1_leftover_mean_pct", g) for r, g in grid.groupby("length_range_cm", sort=False)},
           "k5_by_range": {r: mm("k5_leftover_mean_pct", g) for r, g in grid.groupby("length_range_cm", sort=False)},
           "k5_by_rod": {str(r): mm("k5_leftover_mean_pct", g) for r, g in grid.groupby("rod_cm")},
           "k5_by_parts": {str(r): mm("k5_leftover_mean_pct", g) for r, g in grid.groupby("parts_per_day")}}

    out = {"setting": {"rod_cm": L, "parts_per_day": N_PARTS, "kerf_cm": 0},
           "example_day_k5": example_day, "single_length": single_sum, "pair_lengths": pair_sum,
           "mixture_by_k": mx.to_dict("records"), "robust": rob}
    json.dump(out, open(RES / "a1301_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)

    # 図1：1つの長さ
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(s1.part_cm, s1.leftover_pct, color=BLUE, lw=1)
    for p in [101, 134, 201]:
        v = float(s1[s1.part_cm == p].leftover_pct.iloc[0])
        ax.plot([p], [v], "o", color=ORANGE, ms=4)
        ax.text(p + 4, v + 1, f"{p}cm：{v:.2f}%", fontsize=8.5, color=ORANGE)
    ax.set_xlabel("部品の長さ（cm、1日60本すべて同じ長さ）"); ax.set_ylabel("余りの割合（%）")
    ax.set_ylim(0, 60); ax.set_xlim(30, 400)
    ax.set_title("1つの長さだけなら、余りは400cmから何本取れるかで決まる（式どおり）")
    save(fig, "a1301_single.png", SRC)

    # 図2：2つの長さの組（いちばん少ない本数での余り）
    M = np.full((len(L2), len(L2)), np.nan)
    for r in pr.itertuples():
        a, b = L2.index(r.p1_cm), L2.index(r.p2_cm)
        M[b, a] = r.leftover_best_pct
    fig, ax = plt.subplots(figsize=(7.0, 5.6))
    im = ax.imshow(M, origin="lower", cmap="Blues", vmin=0, vmax=np.nanmax(M))
    ax.set_xticks(range(0, len(L2), 2)); ax.set_xticklabels(L2[::2], fontsize=8)
    ax.set_yticks(range(0, len(L2), 2)); ax.set_yticklabels(L2[::2], fontsize=8)
    ax.set_xlabel("短いほうの部品（cm、30本）"); ax.set_ylabel("長いほうの部品（cm、30本）")
    cb = fig.colorbar(im, ax=ax, shrink=0.8); cb.set_label("いちばん少ない本数で切ったときの余り（%）")
    ax.set_title("2つの長さの組ごとの余り（すべての切り方を調べた最小）", fontsize=12)
    save(fig, "a1301_pair.png", SRC)

    # 図3：長さの種類の数ごと
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(mx))
    ax.bar(x, mx.leftover_mean_pct, color=BLUE, label="大きい順に切った余り（平均）")
    ax.errorbar(x, mx.leftover_mean_pct, yerr=[mx.leftover_mean_pct - mx.leftover_p10_pct,
                                              mx.leftover_p90_pct - mx.leftover_mean_pct],
                fmt="none", ecolor=INK, capsize=3, lw=1, label="10〜90%の日")
    ax.plot(x, mx.lower_bound_leftover_mean_pct, "o", color=ORANGE, label="下限（長さの合計÷400の切り上げ）")
    for xi, v in zip(x, mx.leftover_mean_pct):
        ax.text(xi + 0.12, v + 0.6, f"{v:.2f}%", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{k}通り" for k in mx.k])
    ax.set_xlabel("1日の部品60本の長さの種類（30〜250cmから乱数）"); ax.set_ylabel("余りの割合（%）")
    ax.set_ylim(0, max(mx.leftover_p90_pct) * 1.15)
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title(f"長さの種類が増えるほど、余りの平均も日ごとの振れも小さくなった（{DAYS}日）", fontsize=12)
    save(fig, "a1301_by_k.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
