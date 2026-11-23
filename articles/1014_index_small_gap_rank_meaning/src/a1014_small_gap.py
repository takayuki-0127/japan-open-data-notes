"""1014 合計点の差が小さいとき、順位の差は意味があるのか？（架空のデータ）

架空のカフェ40店。5項目（味・接客・早さ・清潔さ・居心地）を客が0〜20点の整数で付け、店ごとに平均して足した
100点満点の合計点で並べる。店ごとの「本当の合計点」（来た客全員が付けたときの平均の合計）を作成者が置き、
1か月100人の答えから出した合計点の差と順位が、本当の差と順位をどれだけ表すかを数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1014
SRC = "架空のカフェ40店の客の点（作成者が乱数で作成、seed 1014）"
ITEMS = ["味", "接客", "早さ", "清潔さ", "居心地"]
N_STORE, N_CUST = 40, 100
ITEM_BASE = np.array([14.5, 14.0, 13.0, 14.0, 13.5])   # 項目ごとの全店の中心（0〜20点）
SD_STORE, SD_ITEM = 0.5, 0.5     # 店の全体の差（5項目に共通）・項目ごとの店の差
SD_LENIENT, SD_NOISE = 1.5, 2.5  # 客の甘さ（5項目に共通）・1項目ごとの散らばり
SD_X = math.hypot(SD_LENIENT, SD_NOISE)
_erf = np.frompyfunc(math.erf, 1, 1)


def ncdf(z):
    return 0.5 * (1 + _erf(np.asarray(z, float) / math.sqrt(2)).astype(float))


def true_item(loc):
    """客の点＝ round(正規(loc, SD_X)) を0〜20で切った値。その期待値（来た客全員の平均）を式で出す"""
    k = np.arange(0, 21)
    lo = np.where(k == 0, -np.inf, k - 0.5)
    hi = np.where(k == 20, np.inf, k + 0.5)
    p = ncdf((hi[None, :] - loc.ravel()[:, None]) / SD_X) - ncdf((lo[None, :] - loc.ravel()[:, None]) / SD_X)
    return (p * k).sum(1).reshape(loc.shape)


def make_stores(rng, spread=1.0, n=N_STORE):
    a = rng.normal(0, SD_STORE * spread, (n, 1))
    b = rng.normal(0, SD_ITEM * spread, (n, 5))
    loc = ITEM_BASE[None, :] + a + b
    return loc, true_item(loc)


def survey(rng, loc, n_cust):
    """1か月分の客の答え（店×客×項目の整数）"""
    ns = loc.shape[0]
    u = rng.normal(0, SD_LENIENT, (ns, n_cust, 1))
    e = rng.normal(0, SD_NOISE, (ns, n_cust, 5))
    return np.clip(np.rint(loc[:, None, :] + u + e), 0, 20)


def rank_desc(x):
    """大きい順の順位（1位〜）"""
    r = np.empty(len(x), int)
    r[np.argsort(-x, kind="stable")] = np.arange(1, len(x) + 1)
    return r


def run_reps(rng, reps, n_cust, spread, keep_pairs=False):
    """店を作り直して reps 回。2か月分を数え、隣の順位の組と次の月の動きを集める"""
    adj_gap, adj_ok, all_gap, all_ok = [], [], [], []
    same1, rank_move, move5, top_true, err, tt = [], [], [], [], [], []
    iu = np.triu_indices(N_STORE, 1)
    for _ in range(reps):
        loc, ti = make_stores(rng, spread)
        T = ti.sum(1)
        o1 = survey(rng, loc, n_cust).mean(1).sum(1)
        o2 = survey(rng, loc, n_cust).mean(1).sum(1)
        order = np.argsort(-o1, kind="stable")
        adj_gap.append(o1[order[:-1]] - o1[order[1:]])
        adj_ok.append(T[order[:-1]] > T[order[1:]])
        if keep_pairs:
            d = o1[iu[0]] - o1[iu[1]]
            t = T[iu[0]] - T[iu[1]]
            s = np.sign(d)
            all_gap.append(np.abs(d)); all_ok.append(s * t > 0)
            err.append(o1 - T); tt.append(T - T.mean())
        r1, r2 = rank_desc(o1), rank_desc(o2)
        same1.append(order[0] == np.argmax(o2))
        top_true.append(order[0] == np.argmax(T))
        rank_move.append(np.abs(r1 - r2).mean())
        move5.append((np.abs(r1 - r2) >= 5).mean())
    out = dict(adj_gap=np.concatenate(adj_gap), adj_ok=np.concatenate(adj_ok),
               same1=np.mean(same1), top_true=np.mean(top_true),
               rank_move=np.mean(rank_move), move5=np.mean(move5))
    if keep_pairs:
        out.update(all_gap=np.concatenate(all_gap), all_ok=np.concatenate(all_ok),
                   sigma=float(np.concatenate(err).std()), tau=float(np.concatenate(tt).std()))
    return out


def d_for(p, sigma, tau):
    """店をでたらめに2つ選んだときの式：差 d のとき上の店が本当に上の確率＝Φ(dτ/(σ√(2(τ²+σ²))))。確率 p になる d"""
    z = {0.9: 1.2815516, 0.75: 0.6744898}[p]
    return z * sigma * math.sqrt(2 * (tau ** 2 + sigma ** 2)) / tau


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 1か月分（data に置く40店）
    loc, ti = make_stores(rng)
    ans = survey(rng, loc, N_CUST)
    ans2 = survey(rng, loc, N_CUST)
    T = ti.sum(1)
    o1 = ans.mean(1).sum(1)
    o2 = ans2.mean(1).sum(1)
    r1, r2, rt = rank_desc(o1), rank_desc(o2), rank_desc(T)
    cust = pd.DataFrame({"store_id": np.repeat(np.arange(1, N_STORE + 1), N_CUST),
                         "customer_no": np.tile(np.arange(1, N_CUST + 1), N_STORE)})
    for j, it in enumerate(ITEMS):
        cust[f"item{j + 1}_{it}"] = ans[:, :, j].ravel().astype(int)
    cust.to_csv(DATA / "customers_month1.csv", index=False)

    # 店ごとの順位の90%の幅（客を店の中で選び直す、1,000回）
    B = 1000
    boot_rank = np.empty((B, N_STORE), int)
    for bi in range(B):
        idx = rng.integers(0, N_CUST, (N_STORE, N_CUST))
        ob = np.take_along_axis(ans, idx[:, :, None], 1).mean(1).sum(1)
        boot_rank[bi] = rank_desc(ob)
    lo = np.percentile(boot_rank, 5, axis=0, method="lower")
    hi = np.percentile(boot_rank, 95, axis=0, method="higher")
    stores = pd.DataFrame({"store_id": np.arange(1, N_STORE + 1), "true_total": T.round(3),
                           "month1_total": o1.round(3), "month1_rank": r1,
                           "rank90_lo": lo, "rank90_hi": hi,
                           "month2_total": o2.round(3), "month2_rank": r2, "true_rank": rt})
    stores.sort_values("month1_rank").to_csv(DATA / "stores.csv", index=False)
    order = np.argsort(r1)
    gaps1 = o1[order[:-1]] - o1[order[1:]]
    width = hi - lo + 1
    top1 = order[0]
    one_month = {
        "top1_store": int(top1 + 1), "top1_total": round(float(o1[top1]), 2),
        "top2_total": round(float(o1[order[1]]), 2), "gap_1st_2nd": round(float(gaps1[0]), 2),
        "top1_true_rank": int(rt[top1]), "top1_month2_rank": int(r2[top1]),
        "top1_rank90": [int(lo[top1]), int(hi[top1])],
        "total_range": [round(float(o1.min()), 2), round(float(o1.max()), 2)],
        "adjacent_gap_median": round(float(np.median(gaps1)), 2),
        "adjacent_gap_max": round(float(gaps1.max()), 2),
        "adjacent_gap_under_0_5": int((gaps1 < 0.5).sum()),
        "rank90_width_median": float(np.median(width)),
        "rank90_width_ge10_stores": int((width >= 10).sum()),
        "stores_rank1_possible": int((lo == 1).sum()),
        "spearman_month1_month2": round(float(np.corrcoef(r1, r2)[0, 1]), 3),
        "spearman_month1_true": round(float(np.corrcoef(r1, rt)[0, 1]), 3),
        "mean_abs_rank_change": round(float(np.abs(r1 - r2).mean()), 2),
    }

    # 2) 店を作り直して2,000回（基本：1か月100人、店どうしの差1倍）
    base = run_reps(np.random.default_rng(SEED * 10), 2000, N_CUST, 1.0, keep_pairs=True)
    sigma, tau = base["sigma"], base["tau"]
    k = tau / (sigma * math.sqrt(2 * (tau ** 2 + sigma ** 2)))
    bins = [0, 0.25, 0.5, 1, 1.5, 2, 3, 5, np.inf]
    labels = ["0〜0.25点", "0.25〜0.5点", "0.5〜1点", "1〜1.5点", "1.5〜2点", "2〜3点", "3〜5点", "5点以上"]
    rows = []
    for a, b, lab in zip(bins[:-1], bins[1:], labels):
        m = (base["adj_gap"] >= a) & (base["adj_gap"] < b)
        ma = (base["all_gap"] >= a) & (base["all_gap"] < b)
        rows.append({"gap": lab, "adjacent_pairs": int(m.sum()),
                     "adjacent_share_pct": round(100 * m.mean(), 2),
                     "adjacent_truly_higher_pct": round(100 * base["adj_ok"][m].mean(), 2) if m.any() else None,
                     "all_pairs_truly_higher_pct": round(100 * base["all_ok"][ma].mean(), 2),
                     "formula_pct": round(100 * float(ncdf(k * base["all_gap"][ma]).mean()), 2)})
    gap_tab = pd.DataFrame(rows)
    gap_tab.to_csv(RES / "gap_vs_truly_higher.csv", index=False)
    formula_diff = float((gap_tab.all_pairs_truly_higher_pct - gap_tab.formula_pct).abs().max())

    # 3) 確かめ：1か月の客の人数 × 店どうしの差（12通り、各300回）
    grid = []
    for spread in [0.5, 1.0, 2.0]:
        for n in [30, 100, 300, 1000]:
            g = run_reps(np.random.default_rng(SEED * 100 + int(spread * 10) * 10000 + n), 300, n, spread,
                         keep_pairs=True)
            gk = d_for(0.9, g["sigma"], g["tau"])
            grid.append({"spread": spread, "customers": n, "tau": round(g["tau"], 2), "sigma": round(g["sigma"], 3),
                         "adjacent_gap_median": round(float(np.median(g["adj_gap"])), 3),
                         "adjacent_truly_higher_pct": round(100 * g["adj_ok"].mean(), 2),
                         "top1_same_next_month_pct": round(100 * g["same1"], 2),
                         "top1_is_true_top1_pct": round(100 * g["top_true"], 2),
                         "mean_abs_rank_change": round(g["rank_move"], 2),
                         "gap_for_90pct_formula": round(gk, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_customers_spread.csv", index=False)

    main_json = {
        "seed": SEED, "stores": N_STORE, "customers_per_month": N_CUST,
        "one_month": one_month,
        "reps_2000": {
            "tau_true_total_sd": round(tau, 2), "sigma_measure_sd": round(sigma, 3),
            "adjacent_gap_median": round(float(np.median(base["adj_gap"])), 3),
            "adjacent_gap_under_0_5_pct": round(100 * float((base["adj_gap"] < 0.5).mean()), 2),
            "adjacent_gap_under_1_pct": round(100 * float((base["adj_gap"] < 1).mean()), 2),
            "adjacent_truly_higher_pct": round(100 * float(base["adj_ok"].mean()), 2),
            "top1_same_next_month_pct": round(100 * base["same1"], 2),
            "top1_is_true_top1_pct": round(100 * base["top_true"], 2),
            "mean_abs_rank_change": round(base["rank_move"], 2),
            "stores_move_5ranks_pct": round(100 * base["move5"], 2),
            "gap_for_90pct_formula": round(d_for(0.9, sigma, tau), 2),
            "gap_for_75pct_formula": round(d_for(0.75, sigma, tau), 2),
            "formula_vs_sim_max_diff_pt": round(formula_diff, 2),
        },
        "grid_ranges": {
            "adjacent_truly_higher_pct": [float(grid.adjacent_truly_higher_pct.min()), float(grid.adjacent_truly_higher_pct.max())],
            "top1_same_next_month_pct": [float(grid.top1_same_next_month_pct.min()), float(grid.top1_same_next_month_pct.max())],
            "gap_for_90pct_formula": [float(grid.gap_for_90pct_formula.min()), float(grid.gap_for_90pct_formula.max())],
        },
    }

    # 図1：40店の合計点の順位と90%の幅
    fig, ax = plt.subplots(figsize=(7.2, 7.6))
    y = np.arange(N_STORE)
    for i, s in enumerate(order):
        ax.plot([lo[s], hi[s]], [i, i], color=LIGHT, lw=4, solid_capstyle="round")
    ax.scatter(r1[order], y, color=BLUE, s=22, zorder=3, label="1か月目の順位")
    ax.scatter(rt[order], y, color=ORANGE, marker="x", s=26, zorder=4, label="本当の合計点の順位")
    ax.set_yticks(y)
    ax.set_yticklabels([f"店{s + 1}（{o1[s]:.1f}点）" for s in order], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("順位（客を選び直したときの90%の幅を水色の帯で表示）")
    ax.set_xlim(0, N_STORE + 1)
    ax.set_title("合計点で並べた40店：隣どうしの差は中央値%.2f点" % one_month["adjacent_gap_median"], loc="left")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.grid(axis="x", color="#e6e6e6", lw=0.6)
    save(fig, "a1014_rank_interval.png", SRC + "。1か月100人の答え。帯は客を店の中で選び直した1,000回の5〜95%")

    # 図2：差の大きさと「上の店が本当に上」の割合
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    x = np.arange(len(labels))
    ax.bar(x, gap_tab.adjacent_truly_higher_pct, color=BLUE, width=0.6, label="隣の順位の2店（2,000回）")
    ax.plot(x, gap_tab.formula_pct, color=ORANGE, marker="o", lw=2, label="でたらめに選んだ2店の式の値")
    ax.axhline(50, color=GRAY, lw=0.8, ls="--", label="50%（でたらめに当てたとき）")
    for xi, v in zip(x, gap_tab.adjacent_truly_higher_pct):
        ax.text(xi, v - 7, f"{v:.0f}%", ha="center", fontsize=8.5, color="white")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylim(0, 132)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("合計点の差（100点満点）")
    ax.set_ylabel("上の店が本当に上だった割合（%）")
    ax.set_title("差が1点未満の隣どうしは、半々に近い", loc="left")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    save(fig, "a1014_gap_prob.png", SRC + "。店を作り直して2,000回、1か月100人")

    # 図3：客の人数と店どうしの差で、1位が次の月も1位の割合
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for spread, c, lab in [(0.5, GRAY, "店どうしの差 0.5倍"), (1.0, BLUE, "1倍（基本）"), (2.0, ORANGE, "2倍")]:
        g = grid[grid.spread == spread]
        ax.plot(g.customers, g.top1_same_next_month_pct, marker="o", color=c, lw=2, label=lab)
        for xx, yy in zip(g.customers, g.top1_same_next_month_pct):
            ax.text(xx, yy + 2.5, f"{yy:.0f}%", ha="center", fontsize=8, color=INK)
    ax.set_xscale("log")
    ax.set_xticks([30, 100, 300, 1000]); ax.set_xticklabels(["30人", "100人", "300人", "1,000人"])
    ax.set_ylim(0, 105)
    ax.set_xlabel("1か月に答えた客の人数（1店あたり）")
    ax.set_ylabel("1位の店が次の月も1位の割合（%）")
    ax.set_title("1位が続くかは、客の人数と店どうしの差しだい", loc="left")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1014_grid.png", SRC + "。12通り、各300回")

    main_json["run_sec"] = round(time.time() - t0, 1)
    with open(RES / "a1014_main.json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in main_json.items() if k != "run_sec"}, f, ensure_ascii=False, indent=1)
    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print(gap_tab.to_string()); print(grid.to_string())


if __name__ == "__main__":
    main()
