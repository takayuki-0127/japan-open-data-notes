"""916 「不良0件」の月は、不良率0%と言えるのか？（架空のデータ）

架空の工場の部品ライン。ラインごとに「本当の不良率」と「月に検査する個数」を置き、
月ごとの不良の件数は二項分布から引く。検査で見つけた件数だけが記録に残る。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 916
SRC = "架空のラインと検査（作成者が乱数で作成、seed 916）"
N_LINE = 100           # ラインの数
MONTHS = 12
P_MED = 0.001          # 本当の不良率の中央値（0.1%）
P_SD = 0.8             # 本当の不良率の散らばり（対数の標準偏差）
N_LO, N_HI = 200, 20000  # 月の検査個数（対数で一様）
N_REP = 400


def upper95(n, k=0):
    """0件のときの不良率の95%上限（片側、正確な値）。k=0 のみ"""
    return 1 - 0.05 ** (1 / n)


def make_lines(rng, n_line=N_LINE, p_sd=P_SD, n_lo=N_LO, n_hi=N_HI, detect=1.0):
    p = np.clip(P_MED * np.exp(rng.normal(0, p_sd, n_line)), 0, 0.5)
    n = np.round(np.exp(rng.uniform(np.log(n_lo), np.log(n_hi), n_line))).astype(int)
    k = rng.binomial(n[:, None], p[:, None] * detect, (n_line, MONTHS))
    return p, n, k


def spearman(a, b):
    ra = pd.Series(a).rank().values; rb = pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def evaluate(rng, reps, **kw):
    """0件の月の中身・ラインの並べ方の当たり"""
    zero_true_ge, zero_cnt, cover_bad = 0, 0, 0
    rho_zero, rho_pool, top10_zero, top10_pool, share_zero_months = [], [], [], [], []
    for _ in range(reps):
        p, n, k = make_lines(rng, **kw)
        z = k == 0
        pz = np.repeat(p[:, None], MONTHS, 1)[z]
        nz = np.repeat(n[:, None], MONTHS, 1)[z]
        zero_cnt += z.sum(); zero_true_ge += (pz >= P_MED).sum()
        cover_bad += (pz > upper95(nz)).sum()
        share_zero_months.append(z.mean())
        n_zero = z.sum(1)
        pooled = k.sum(1) / (n * MONTHS)
        # 「良い」ほど上：0件の月が多いほど良い／合計の不良率が低いほど良い。本当の不良率が低いほど良い
        rho_zero.append(spearman(n_zero, -p))
        rho_pool.append(spearman(-pooled, -p))
        true_best = set(np.argsort(p)[:10])
        # 同点は検査個数の少ない順（並べる側に有利な扱いはしない：でたらめに崩す）
        tie = rng.random(len(p)) * 1e-6
        top10_zero.append(len(true_best & set(np.argsort(-(n_zero + tie))[:10])) / 10)
        top10_pool.append(len(true_best & set(np.argsort(pooled + tie)[:10])) / 10)
    return {"share_zero_months": round(float(np.mean(share_zero_months)), 4),
            "zero_months_true_ge_0_1pct": round(float(zero_true_ge / zero_cnt), 4),
            "zero_months_true_above_upper95": round(float(cover_bad / zero_cnt), 4),
            "spearman_zero_months": round(float(np.mean(rho_zero)), 3),
            "spearman_pooled_rate": round(float(np.mean(rho_pool)), 3),
            "top10_hit_zero_months": round(float(np.mean(top10_zero)), 3),
            "top10_hit_pooled_rate": round(float(np.mean(top10_pool)), 3)}


def main():
    rng = np.random.default_rng(SEED)

    # 1) 本当の不良率0.1%で、月の検査個数ごとの「0件の月」の割合と、0件のときの95%上限
    table1 = []
    for n in [300, 1000, 3000, 10000]:
        sim = rng.binomial(n, P_MED, 200000)
        table1.append({"n_per_month": n, "p_zero_formula": round((1 - P_MED) ** n, 6),
                       "p_zero_sim": round(float((sim == 0).mean()), 4),
                       "upper95_if_zero": round(upper95(n), 5), "rule_of_three": round(3 / n, 5),
                       "zero_months_per_year": round(12 * (1 - P_MED) ** n, 2)})
    t1 = pd.DataFrame(table1)
    t1.to_csv(RES / "zero_month_by_volume.csv", index=False)

    # 2) 2つのライン：小さくて不良率の高いX と 大きくて不良率の低いY
    X = {"n": 500, "p": 0.003}; Y = {"n": 5000, "p": 0.0005}
    reps = 20000
    kx = rng.binomial(X["n"], X["p"], (reps, MONTHS)); ky = rng.binomial(Y["n"], Y["p"], (reps, MONTHS))
    zx, zy = (kx == 0).sum(1), (ky == 0).sum(1)
    pool_x, pool_y = kx.sum(1) / (X["n"] * MONTHS), ky.sum(1) / (Y["n"] * MONTHS)
    pair = {"X": X, "Y": Y,
            "zero_months_mean_X": round(float(zx.mean()), 2), "zero_months_mean_Y": round(float(zy.mean()), 2),
            "P_X_more_zero_months": round(float((zx > zy).mean()), 4),
            "P_tie_zero_months": round(float((zx == zy).mean()), 4),
            "P_X_lower_pooled_rate": round(float((pool_x < pool_y).mean()), 4),
            "defects_per_year_X": round(float(kx.sum(1).mean()), 2), "defects_per_year_Y": round(float(ky.sum(1).mean()), 2)}
    pd.DataFrame({"zero_months": np.arange(13),
                  "X_share": [round(float((zx == m).mean()), 4) for m in range(13)],
                  "Y_share": [round(float((zy == m).mean()), 4) for m in range(13)]}).to_csv(RES / "pair_zero_months_dist.csv", index=False)

    # 3) ライン100本：0件の月の中身と、並べ方の当たり
    base = evaluate(np.random.default_rng(SEED * 10), N_REP)

    # 1回分（data）
    p1, n1, k1 = make_lines(np.random.default_rng(SEED * 100))
    rows = []
    for i in range(N_LINE):
        for m in range(MONTHS):
            rows.append({"line_id": i + 1, "month": m + 1, "inspected": int(n1[i]), "defects": int(k1[i, m]),
                         "true_rate": round(float(p1[i]), 6)})
    pd.DataFrame(rows).to_csv(DATA / "lines_monthly.csv", index=False)

    # 4) 確かめ：不良率の散らばり × 検査個数の幅 × 検査の見逃し
    grid = []
    for p_sd in [0.4, 0.8, 1.2]:
        for (lo, hi) in [(200, 20000), (1000, 5000)]:
            for det in [1.0, 0.7]:
                r = evaluate(np.random.default_rng(SEED * 1000 + int(p_sd * 10) * 100 + lo // 100 + int(det * 10)),
                             150, p_sd=p_sd, n_lo=lo, n_hi=hi, detect=det)
                grid.append({"p_sd": p_sd, "n_range": f"{lo}-{hi}", "detect": det, **r})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    rg = lambda c, g=grid: [round(float(g[c].min()), 4), round(float(g[c].max()), 4)]
    sens = {"n_settings": len(grid),
            "pooled_beats_zero_spearman": int((grid.spearman_pooled_rate > grid.spearman_zero_months).sum()),
            "pooled_beats_zero_top10": int((grid.top10_hit_pooled_rate > grid.top10_hit_zero_months).sum()),
            "zero_true_ge_range": rg("zero_months_true_ge_0_1pct"),
            "above_upper95_range_detect1": rg("zero_months_true_above_upper95", grid[grid.detect == 1.0]),
            "above_upper95_range_detect07": rg("zero_months_true_above_upper95", grid[grid.detect == 0.7]),
            "above_upper95_gt5pct_detect07": int((grid[grid.detect == 0.7].zero_months_true_above_upper95 > 0.05).sum()),
            "spearman_zero_range": rg("spearman_zero_months"), "spearman_pooled_range": rg("spearman_pooled_rate"),
            "share_zero_months_range": rg("share_zero_months")}

    out = {"settings": {"n_line": N_LINE, "months": MONTHS, "p_median": P_MED, "p_sd_log": P_SD, "n_range": [N_LO, N_HI],
                        "n_rep": N_REP, "formula_check_draws": 200000, "pair_years": reps, "grid_reps": 150},
           "by_volume_true_0_1pct": t1.to_dict("records"), "pair_X_small_Y_large": pair,
           "lines100_base": base, "sensitivity": sens,
           "one_draw": {"zero_months": int((k1 == 0).sum()), "line_months": int(k1.size),
                        "lines_with_6plus_zero_months": int(((k1 == 0).sum(1) >= 6).sum()),
                        "lines_6plus_zero_true_ge_0_1pct": int((((k1 == 0).sum(1) >= 6) & (p1 >= P_MED)).sum()),
                        "spearman_zero_months_vs_low_volume": round(spearman((k1 == 0).sum(1), -n1), 3),
                        "spearman_zero_months_vs_low_true_rate": round(spearman((k1 == 0).sum(1), -p1), 3)}}
    json.dump(out, open(RES / "a916_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：検査個数ごとの0件の月の割合と、0件のときの95%上限
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    nn = np.exp(np.linspace(np.log(100), np.log(20000), 200))
    axes[0].plot(nn, (1 - P_MED) ** nn * 100, color=BLUE)
    for r_ in table1:
        axes[0].plot(r_["n_per_month"], r_["p_zero_formula"] * 100, "o", color=BLUE)
        lab = f"{r_['p_zero_formula']*100:.1f}%" if r_["p_zero_formula"] >= 0.001 else "ほぼ0%"
        axes[0].text(r_["n_per_month"] * 1.12, r_["p_zero_formula"] * 100 + 2, lab, fontsize=8.5)
    axes[0].set_xscale("log"); axes[0].set_xlabel("月に検査する個数（対数の目盛り）"); axes[0].set_ylabel("%")
    axes[0].set_title("本当の不良率0.1%で「0件の月」になる確率", fontsize=10.5); axes[0].set_ylim(0, 100)
    axes[1].plot(nn, upper95(nn) * 100, color=ORANGE)
    axes[1].axhline(P_MED * 100, color=INK, lw=1, ls="--"); axes[1].text(110, 0.115, "0.1%", fontsize=8.5)
    for r_ in table1:
        axes[1].plot(r_["n_per_month"], r_["upper95_if_zero"] * 100, "o", color=ORANGE)
        axes[1].text(r_["n_per_month"] * 1.12, r_["upper95_if_zero"] * 100 * 1.12, f"{r_['upper95_if_zero']*100:.2f}%", fontsize=8.5)
    axes[1].set_xscale("log"); axes[1].set_yscale("log"); axes[1].set_xlabel("月に検査する個数（対数の目盛り）")
    axes[1].set_ylabel("%（対数の目盛り）")
    from matplotlib.ticker import NullLocator
    for ax in axes:
        ax.set_xticks([100, 300, 1000, 3000, 10000]); ax.set_xticklabels(["100", "300", "1,000", "3,000", "10,000"])
        ax.xaxis.set_minor_locator(NullLocator())
    axes[1].set_yticks([0.01, 0.03, 0.1, 0.3, 1, 3]); axes[1].set_yticklabels(["0.01", "0.03", "0.1", "0.3", "1", "3"])
    axes[1].yaxis.set_minor_locator(NullLocator())
    axes[1].set_title("0件だったときに言える不良率の上限（95%）", fontsize=10.5)
    fig.suptitle("0件の月は、検査する個数が少ないほど出やすく、言える上限は高い", fontsize=11.5, y=1.02)
    fig.tight_layout()
    save(fig, "a916_by_volume.png", SRC)

    # 図2：XとYの0件の月の数
    d2 = pd.read_csv(RES / "pair_zero_months_dist.csv")
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    w = 0.4
    ax.bar(d2.zero_months - w / 2, d2.X_share * 100, w, color=ORANGE,
           label=f"X：月{X['n']}個・本当の不良率{X['p']*100:.1f}%")
    ax.bar(d2.zero_months + w / 2, d2.Y_share * 100, w, color=BLUE,
           label=f"Y：月{Y['n']:,}個・本当の不良率{Y['p']*100:.2f}%")
    ax.set_xticks(range(13)); ax.set_xlabel("1年のうち「不良0件」だった月の数"); ax.set_ylabel("年の割合（%）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"不良率が6倍のXのほうが、0件の月が多い年が{pair['P_X_more_zero_months']*100:.0f}%（2万年分）")
    save(fig, "a916_pair.png", SRC)

    # 図3：1回分のライン100本：0件の月の数 と 本当の不良率
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    nz1 = (k1 == 0).sum(1)
    sc = ax.scatter(p1 * 100, nz1 + rng.uniform(-0.18, 0.18, N_LINE), c=np.log10(n1), cmap="Blues", s=26,
                    edgecolor=INK, lw=0.3, vmin=np.log10(N_LO) - 0.6, vmax=np.log10(N_HI))
    cb = fig.colorbar(sc, ax=ax); cb.set_label("月の検査個数（対数）")
    cb.set_ticks(np.log10([200, 1000, 5000, 20000])); cb.set_ticklabels(["200", "1,000", "5,000", "20,000"])
    ax.set_xscale("log"); ax.set_xlabel("本当の不良率（%、対数の目盛り）"); ax.set_ylabel("1年のうち0件だった月の数")
    ax.text(0.99, 0.99, "点は重ならないよう上下に少しずらした", transform=ax.transAxes, ha="right", va="top", fontsize=8, color=GRAY)
    from matplotlib.ticker import NullLocator
    ax.set_xticks([0.02, 0.05, 0.1, 0.2, 0.5]); ax.set_xticklabels(["0.02", "0.05", "0.1", "0.2", "0.5"])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.axvline(P_MED * 100, color=GRAY, lw=1, ls="--")
    ax.set_title("0件の月の数は、不良率より検査個数で決まっていた（ライン100本・1回分）", fontsize=12)
    save(fig, "a916_lines.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
