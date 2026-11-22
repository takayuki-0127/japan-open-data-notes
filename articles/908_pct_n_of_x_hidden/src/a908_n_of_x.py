"""908 「n人中x人」を割合だけで書くと、何が消えるのか？（架空のデータ）

架空の店300店。店ごとに「試食した人のうち買う本当の割合」を置き、試食した人数 n は 2〜1,000人（対数で一様）。
買った人 x は二項分布で引き、「x÷n」を整数の%に四捨五入して表示する。
表示の%だけからは何が分からなくなるか（人数・幅・比べた向き）を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 908
SRC = "架空の店と試食・購入の人数（作成者が乱数で作成、seed 908）"
N_STORE = 300
REPS = 200
GROUPS = [(2, 9, "2〜9人"), (10, 29, "10〜29人"), (30, 99, "30〜99人"), (100, 299, "100〜299人"), (300, 1000, "300〜1,000人")]
Z = 1.959964


def half_up(x):
    return np.floor(x + 0.5)


def show_pct(x, n):
    return half_up(x * 100 / n).astype(int)


def make(rng, reps, mean=0.3, sd=0.1, nlo=2, nhi=1000):
    v = mean * (1 - mean) / sd ** 2 - 1
    p = rng.beta(mean * v, (1 - mean) * v, (reps, N_STORE))
    n = np.round(np.exp(rng.uniform(np.log(nlo), np.log(nhi), (reps, N_STORE)))).astype(int)
    x = rng.binomial(n, p)
    return p, n, x


def wilson(x, n):
    ph = x / n
    c = (ph + Z ** 2 / (2 * n)) / (1 + Z ** 2 / n)
    h = Z * np.sqrt(ph * (1 - ph) / n + Z ** 2 / (4 * n ** 2)) / (1 + Z ** 2 / n)
    return c - h, c + h


def group_of(n):
    g = np.full(n.shape, -1)
    for i, (lo, hi, _) in enumerate(GROUPS):
        g[(n >= lo) & (n <= hi)] = i
    return g


def reversal(p, n, sh, rng, cond, k=200000):
    """表示の差が20ポイント以上ある2店の組で、本当の割合の向きが逆（表示の低い店のほうが本当は高いか同じ）の割合"""
    pf, nf, sf = p.ravel(), n.ravel(), sh.ravel()
    idx = np.where(cond(nf))[0]
    a, b = rng.choice(idx, k), rng.choice(idx, k)
    m = np.abs(sf[a] - sf[b]) >= 20
    a, b = a[m], b[m]
    hi = np.where(sf[a] > sf[b], a, b); lo = np.where(sf[a] > sf[b], b, a)
    return float((pf[lo] >= pf[hi]).mean()), int(m.sum())


def main():
    rng = np.random.default_rng(SEED)

    # 1) 表示の%から人数は戻せるか：整数の%ごとに、その表示になりうる最小の人数と、1〜100人のうちありうる人数の数
    rows = []
    for v in range(0, 101):
        ns = [nn for nn in range(1, 101) if any(show_pct(np.array([xx]), nn)[0] == v for xx in range(nn + 1))]
        rows.append({"shown_pct": v, "min_n": ns[0] if ns else None, "n_count_1_100": len(ns)})
    inv = pd.DataFrame(rows)
    inv.to_csv(RES / "shown_pct_possible_n.csv", index=False)

    # 2) 基本の置き方：店300店×200回
    p, n, x = make(np.random.default_rng(SEED * 10), REPS)
    sh = show_pct(x, n)
    err = np.abs(sh - p * 100)
    g = group_of(n)
    lo_w, hi_w = wilson(x, n)
    cover = (p >= lo_w) & (p <= hi_w)
    by_g = []
    for i, (_, _, lab) in enumerate(GROUPS):
        m = g == i
        m60 = m & (sh >= 55) & (sh <= 65)
        by_g.append({"n_group": lab, "stores": int(m.sum()),
                     "mean_abs_err_pt": round(float(err[m].mean()), 2),
                     "share_err_ge_10pt": round(float((err[m] >= 10).mean()), 4),
                     "share_shown_0_or_100": round(float(((sh[m] == 0) | (sh[m] == 100)).mean()), 4),
                     "shown_55_65_count": int(m60.sum()),
                     "shown_55_65_true_p10": round(float(np.quantile(p[m60], .1) * 100), 1),
                     "shown_55_65_true_median": round(float(np.median(p[m60]) * 100), 1),
                     "shown_55_65_true_p90": round(float(np.quantile(p[m60], .9) * 100), 1),
                     "wilson95_coverage": round(float(cover[m].mean()), 4),
                     "wilson95_width_median_pt": round(float(np.median(hi_w[m] - lo_w[m]) * 100), 1)})
    byg = pd.DataFrame(by_g)
    byg.to_csv(RES / "by_n_group.csv", index=False)

    # 表示が 0%・50%・100% など「きりのよい」値の店のうち、10人以下の割合（全体の10人以下の割合と比べる）
    small = n <= 10
    shown_tab = []
    for v in [0, 33, 50, 67, 100]:
        m = sh == v
        shown_tab.append({"shown_pct": v, "stores": int(m.sum()), "share_n_le_10": round(float(small[m].mean()), 4)})
    shown_tab.append({"shown_pct": "全体", "stores": int(sh.size), "share_n_le_10": round(float(small.mean()), 4)})
    # 表示の上位10店（各回）
    top = np.argsort(-sh, axis=1, kind="stable")[:, :10]
    true_top = np.argsort(-p, axis=1)[:, :10]
    top_n_med = float(np.median(np.take_along_axis(n, top, 1)))
    top_hit = float(np.mean([len(set(a) & set(b)) for a, b in zip(top, true_top)]))
    # 人数を書いてあれば：ウィルソンの下限で並べた上位10店
    top_w = np.argsort(-lo_w, axis=1, kind="stable")[:, :10]
    top_w_hit = float(np.mean([len(set(a) & set(b)) for a, b in zip(top_w, true_top)]))
    top_w_n_med = float(np.median(np.take_along_axis(n, top_w, 1)))

    # 3) 比べた向き：表示の差が20ポイント以上の2店
    rv = {}
    for lab, cond in [("どちらも10人未満", lambda a: a < 10), ("どちらも10〜99人", lambda a: (a >= 10) & (a < 100)),
                      ("どちらも100人以上", lambda a: a >= 100), ("人数を問わない", lambda a: a >= 0)]:
        r, cnt = reversal(p, n, sh, np.random.default_rng(SEED * 3), cond)
        rv[lab] = {"reversed": round(r, 4), "pairs": cnt}

    # 1回分の店を data に
    one = pd.DataFrame({"store_id": np.arange(1, N_STORE + 1), "true_rate": p[0].round(4), "tasted": n[0],
                        "bought": x[0], "shown_pct": sh[0],
                        "wilson95_low_pct": (lo_w[0] * 100).round(1), "wilson95_high_pct": (hi_w[0] * 100).round(1)})
    one.to_csv(DATA / "stores_one_draw.csv", index=False)

    # 4) 確かめ：本当の割合の平均・店どうしの差・人数の幅
    rows = []
    c = 0
    for mean in [0.1, 0.3, 0.5]:
        for sd in [0.05, 0.1, 0.2]:
            if sd >= np.sqrt(mean * (1 - mean)) * 0.9:
                continue
            for nlo, nhi, nlab in [(2, 1000, "2〜1,000人（基本）"), (5, 200, "5〜200人"), (20, 1000, "20〜1,000人")]:
                c += 1
                rr = np.random.default_rng(SEED * 1000 + c)
                pp, nn, xx = make(rr, 100, mean, sd, nlo, nhi)
                ss = show_pct(xx, nn); ee = np.abs(ss - pp * 100)
                lw, hw = wilson(xx, nn)
                tp = np.argsort(-ss, axis=1, kind="stable")[:, :10]; tt = np.argsort(-pp, axis=1)[:, :10]
                tw = np.argsort(-lw, axis=1, kind="stable")[:, :10]
                r_small, _ = reversal(pp, nn, ss, rr, lambda a: a < 10, 50000) if nlo < 10 else (np.nan, 0)
                r_all, _ = reversal(pp, nn, ss, rr, lambda a: a >= 0, 50000)
                rows.append({"true_mean": mean, "true_sd": sd, "n_range": nlab,
                             "share_err_ge_10pt": round(float((ee >= 10).mean()), 4),
                             "share_err_ge_10pt_n_lt_10": round(float((ee[nn < 10] >= 10).mean()), 4) if nlo < 10 else np.nan,
                             "reversed_pairs_all": round(r_all, 4),
                             "reversed_pairs_n_lt_10": round(r_small, 4) if nlo < 10 else np.nan,
                             "top10_hit_by_pct": round(float(np.mean([len(set(a) & set(b)) for a, b in zip(tp, tt)])), 2),
                             "top10_hit_by_wilson_low": round(float(np.mean([len(set(a) & set(b)) for a, b in zip(tw, tt)])), 2),
                             "top10_median_n_by_pct": float(np.median(np.take_along_axis(nn, tp, 1))),
                             "wilson95_coverage": round(float(((pp >= lw) & (pp <= hw)).mean()), 4)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    gb = grid[grid.n_range == "2〜1,000人（基本）"]
    sens = {"cases": int(len(grid)),
            "share_err_ge_10pt_n_lt_10_range": [float(gb.share_err_ge_10pt_n_lt_10.min()), float(gb.share_err_ge_10pt_n_lt_10.max())],
            "reversed_n_lt_10_range": [float(grid.reversed_pairs_n_lt_10.min()), float(grid.reversed_pairs_n_lt_10.max())],
            "top10_hit_by_pct_range": [float(grid.top10_hit_by_pct.min()), float(grid.top10_hit_by_pct.max())],
            "top10_hit_by_wilson_range": [float(grid.top10_hit_by_wilson_low.min()), float(grid.top10_hit_by_wilson_low.max())],
            "wilson_better_cases": int((grid.top10_hit_by_wilson_low > grid.top10_hit_by_pct).sum()),
            "pct_ge_wilson_cases": grid.loc[grid.top10_hit_by_pct >= grid.top10_hit_by_wilson_low,
                                            ["true_mean", "true_sd", "n_range"]].to_dict("records"),
            "wilson_coverage_range": [float(grid.wilson95_coverage.min()), float(grid.wilson95_coverage.max())]}

    sel = inv[inv.shown_pct.isin([0, 10, 20, 25, 33, 40, 50, 60, 67, 75, 80, 100, 31, 47, 58, 73, 99])]
    out = {"possible_n": sel.to_dict("records"),
           "possible_n_min_over_all_values": int(inv.min_n.max()),
           "shown_values_min_n_le_5": int((inv.min_n <= 5).sum()),
           "by_n_group": by_g, "round_values": shown_tab,
           "top10_by_pct": {"median_n": top_n_med, "true_top10_hit": round(top_hit, 2)},
           "top10_by_wilson_low": {"median_n": top_w_n_med, "true_top10_hit": round(top_w_hit, 2)},
           "reversed_pairs_diff_ge_20": rv, "sensitivity": sens}
    json.dump(out, open(RES / "a908_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：表示が55〜65%の店の、本当の割合の10〜90%の範囲（人数ごと）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    y = np.arange(len(GROUPS))[::-1]
    for yi, r in zip(y, by_g):
        ax.plot([r["shown_55_65_true_p10"], r["shown_55_65_true_p90"]], [yi, yi], color=BLUE, lw=6, solid_capstyle="butt")
        ax.plot(r["shown_55_65_true_median"], yi, "o", color=INK, ms=5)
        ax.text(r["shown_55_65_true_p90"] + 1, yi, f"{r['shown_55_65_true_p10']:.0f}〜{r['shown_55_65_true_p90']:.0f}%",
                va="center", fontsize=9)
    ax.axvspan(55, 65, color=ORANGE, alpha=.15, lw=0); ax.text(60, len(GROUPS) - .45, "表示55〜65%", ha="center",
                                                            fontsize=8.5, color=ORANGE)
    ax.set_yticks(y, [gg[2] for gg in GROUPS]); ax.set_xlim(0, 85); ax.set_ylim(-.6, len(GROUPS) - .2)
    ax.set_xlabel("本当の割合（%）。線は10〜90%の範囲、点は中央値"); ax.set_ylabel("試食した人数")
    ax.set_title("同じ「60%前後」でも、人数が少ないと本当の割合は広く散らばる")
    save(fig, "a908_same_pct_range.png", SRC)

    # 図2：表示の%と人数（1回分の300店）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.scatter(n[0], sh[0], s=10, color=BLUE, alpha=.6, lw=0)
    ax.set_xscale("log"); ax.set_xlabel("試食した人数（対数の目盛り）"); ax.set_ylabel("表示の割合（%）")
    ax.axhline(30, color=GRAY, lw=.8, ls="--"); ax.text(1.0, 0.95, "点線：本当の割合の平均30%", transform=ax.transAxes, fontsize=8.5, color=GRAY, ha="right")
    ax.set_xticks([2, 5, 10, 30, 100, 300, 1000], ["2", "5", "10", "30", "100", "300", "1,000"]); ax.minorticks_off()
    ax.set_title("0%・50%・100%のような表示は、人数の少ない店に集まる（300店）")
    save(fig, "a908_pct_vs_n.png", SRC)

    # 図3：表示の差20ポイント以上の2店で、本当の向きが逆の割合
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    labs = list(rv.keys()); v = [rv[k]["reversed"] * 100 for k in labs]
    ax.barh(labs[::-1], v[::-1], color=[GRAY, BLUE, BLUE, BLUE])
    for i, vi in enumerate(v[::-1]):
        ax.text(vi + .4, i, f"{vi:.1f}%", va="center", fontsize=9)
    ax.set_xlabel("本当は向きが逆（表示の低い店のほうが高いか同じ）だった組の割合（%）", fontsize=10); ax.set_xlim(0, max(v) * 1.25)
    ax.set_title("表示の差が20ポイントあっても、人数が少ない店どうしでは逆のことがある")
    save(fig, "a908_reversed_pairs.png", SRC, y=-0.05)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])


if __name__ == "__main__":
    main()
