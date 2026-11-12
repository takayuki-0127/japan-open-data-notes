"""458 件数が少ないとき、割合の「95%の幅」は正解を何%含むか
本当の割合 p と件数 n を決めると、当たりの数 k は二項分布で出る。
k ごとに幅を作り、p が入るかを確率で足し合わせる（乱数を使わない正確な計算）。確かめに乱数でも試す。seed 458"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 458
Z = stats.norm.ppf(0.975)
PS = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50]
NS = [10, 20, 30, 50, 100, 200, 500, 1000]
SRC = "二項分布による計算（確かめの乱数は seed 458）"


def wald(k, n):
    p = k / n; h = Z * np.sqrt(p * (1 - p) / n)
    return np.clip(p - h, 0, 1), np.clip(p + h, 0, 1)


def wilson(k, n):
    p = k / n; d = 1 + Z**2 / n
    c = (p + Z**2 / (2 * n)) / d; h = Z * np.sqrt(p * (1 - p) / n + Z**2 / (4 * n**2)) / d
    return c - h, c + h


def agresti_coull(k, n):
    nn = n + Z**2; p = (k + Z**2 / 2) / nn; h = Z * np.sqrt(p * (1 - p) / nn)
    return np.clip(p - h, 0, 1), np.clip(p + h, 0, 1)


def clopper(k, n):
    lo = np.where(k == 0, 0.0, stats.beta.ppf(0.025, k, n - k + 1))
    hi = np.where(k == n, 1.0, stats.beta.ppf(0.975, k + 1, n - k))
    return lo, hi


METHODS = {"ふつうの式": wald, "ウィルソン": wilson, "アグレスティ・クール": agresti_coull, "正確な方法": clopper}


def exact(p, n):
    k = np.arange(n + 1); w = stats.binom.pmf(k, n, p); out = {}
    for name, f in METHODS.items():
        lo, hi = f(k, n)
        out[name] = dict(coverage=float(w[(lo <= p) & (p <= hi)].sum()), width=float((w * (hi - lo)).sum()),
                         miss_low=float(w[hi < p].sum()), miss_high=float(w[lo > p].sum()))
    return out


def main():
    rows = []
    for p in PS:
        for n in NS:
            r = exact(p, n)
            for m, v in r.items():
                rows.append(dict(p=p, n=n, expected_hits=n * p, method=m, coverage_pct=v["coverage"] * 100, mean_width_pt=v["width"] * 100,
                                 miss_true_above_pct=v["miss_low"] * 100, miss_true_below_pct=v["miss_high"] * 100,
                                 zero_width_pct=((1 - p) ** n + p ** n) * 100 if m == "ふつうの式" else 0.0))
    df = pd.DataFrame(rows); df.round(5).to_csv(RES / "coverage_table.csv", index=False)

    # 件数を1件ずつ変えたとき（のこぎりの形）
    rows = []
    for p in (0.02, 0.05, 0.20):
        for n in range(5, 501):
            r = exact(p, n)
            rows.append(dict(p=p, n=n, **{m: r[m]["coverage"] * 100 for m in METHODS}))
    saw = pd.DataFrame(rows); saw.round(4).to_csv(RES / "coverage_by_n_fine.csv", index=False)

    # 目安「当たりと外れが両方5件（10件）以上」を満たす組み合わせでの、ふつうの式の当たり方
    fine = []
    for p in np.round(np.r_[np.arange(0.005, 0.1, 0.005), np.arange(0.1, 0.501, 0.02)], 3):
        for n in list(range(10, 100, 5)) + list(range(100, 1001, 50)):
            r = exact(p, n); fine.append(dict(p=p, n=n, np=n * p, **{m: r[m]["coverage"] * 100 for m in METHODS}))
    fine = pd.DataFrame(fine); fine.round(4).to_csv(RES / "coverage_grid_fine.csv", index=False)
    rule = []
    for lab, lo, hi in (("5件未満", 0, 5), ("5〜10件", 5, 10), ("10〜20件", 10, 20), ("20〜50件", 20, 50), ("50件以上", 50, 1e9)):
        s = fine[(fine.np >= lo) & (fine.np < hi)]
        rule.append(dict(expected_hits=lab, cells=len(s), **{f"{m}_min": s[m].min() for m in METHODS}, **{f"{m}_mean": s[m].mean() for m in METHODS},
                         wald_below_90_share=(s["ふつうの式"] < 90).mean() * 100, wald_below_93_share=(s["ふつうの式"] < 93).mean() * 100))
    rule = pd.DataFrame(rule); rule.round(3).to_csv(RES / "rule_of_thumb.csv", index=False)

    # 乱数での確かめ（p=5%、n=50、10万回）
    rng = np.random.default_rng(SEED); k = rng.binomial(50, 0.05, 100000)
    sim = {m: float(np.mean((f(k, 50)[0] <= 0.05) & (0.05 <= f(k, 50)[1])) * 100) for m, f in METHODS.items()}
    ex = pd.DataFrame({"hits": np.arange(0, 11)})
    for m, f in METHODS.items():
        lo, hi = f(ex.hits.values, 50); ex[m + "_下"] = np.round(lo * 100, 2); ex[m + "_上"] = np.round(hi * 100, 2)
    ex.to_csv(DATA / "example_intervals_n50.csv", index=False)

    W = df[df.method == "ふつうの式"]
    main_js = dict(
        coverage={m: {f"{p}": {str(n): round(float(df[(df.method == m) & (df.p == p) & (df.n == n)].coverage_pct.iloc[0]), 1) for n in NS} for p in PS} for m in METHODS},
        width={m: {f"{p}": {str(n): round(float(df[(df.method == m) & (df.p == p) & (df.n == n)].mean_width_pt.iloc[0]), 2) for n in NS} for p in PS} for m in METHODS},
        wald_cells_below_90=int((W.coverage_pct < 90).sum()), wald_cells_below_93=int((W.coverage_pct < 93).sum()), cells=int(len(W)),
        other_min={m: float(df[df.method == m].coverage_pct.min()) for m in METHODS},
        other_mean={m: float(df[df.method == m].coverage_pct.mean()) for m in METHODS},
        zero_width={f"{p}": {str(n): round(float(W[(W.p == p) & (W.n == n)].zero_width_pct.iloc[0]), 1) for n in NS} for p in PS},
        rule=rule.round(2).to_dict("records"), sim_p05_n50=sim, exact_p05_n50={m: exact(0.05, 50)[m]["coverage"] * 100 for m in METHODS},
        saw_p05_range_n100_500={m: [float(saw[(saw.p == 0.05) & (saw.n >= 100)][m].min()), float(saw[(saw.p == 0.05) & (saw.n >= 100)][m].max())] for m in METHODS})
    json.dump(main_js, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：ふつうの式とウィルソンの当たり方（表）
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for a, m in zip(ax, ("ふつうの式", "ウィルソン")):
        M = df[df.method == m].pivot(index="p", columns="n", values="coverage_pct").loc[PS, NS].values
        a.imshow(M, cmap="RdYlBu", vmin=80, vmax=100, aspect="auto")
        for i in range(len(PS)):
            for j in range(len(NS)):
                a.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=9, color=INK if 86 < M[i, j] < 98.5 else "white", fontweight="bold" if M[i, j] < 90 else None)
        a.set_xticks(range(len(NS))); a.set_xticklabels([f"{n:,}" for n in NS]); a.set_xlabel("件数")
        a.set_yticks(range(len(PS))); a.set_yticklabels([f"{p*100:g}%" for p in PS]); a.set_title(m, loc="left")
        for s_ in a.spines.values(): s_.set_visible(False)
    ax[0].set_ylabel("本当の割合")
    fig.suptitle("95%の幅が、本当の割合を含んだ割合（%）", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(); save(fig, "a458_coverage_heatmap.png", SRC)

    # 図2：件数を1件ずつ変えたとき（p=5%）
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for a, p in zip(ax, (0.05, 0.20)):
        s = saw[saw.p == p]
        for m, col in (("ふつうの式", ORANGE), ("ウィルソン", BLUE), ("正確な方法", GRAY)):
            a.plot(s.n, s[m], color=col, lw=1.1, label=m)
        a.axhline(95, color=INK, lw=0.8, ls=":"); a.set_ylim(75, 100.5); a.set_xlabel("件数"); a.set_title(f"本当の割合が{p*100:.0f}%のとき", loc="left")
    ax[0].set_ylabel("95%の幅が本当の割合を含んだ割合（%）"); ax[0].legend(fontsize=8.5, frameon=False, loc="lower right")
    fig.tight_layout(); save(fig, "a458_coverage_sawtooth.png", SRC)

    # 図3：幅の長さと、幅が0になる割合
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for m, col in (("ふつうの式", ORANGE), ("ウィルソン", BLUE), ("アグレスティ・クール", GREEN), ("正確な方法", GRAY)):
        s = df[(df.method == m) & (df.p == 0.05)]
        ax[0].plot(range(len(NS)), s.mean_width_pt, "-o", color=col, lw=1.6, ms=4, label=m)
    ax[0].set_xticks(range(len(NS))); ax[0].set_xticklabels([f"{n:,}" for n in NS]); ax[0].set_yscale("log")
    ax[0].set_xlabel("件数"); ax[0].set_ylabel("幅の長さの平均（ポイント）"); ax[0].set_title("幅の長さ（本当の割合が5%のとき）", loc="left"); ax[0].legend(fontsize=8.5, frameon=False)
    for p, col in zip((0.005, 0.01, 0.02, 0.05, 0.10), (INK, GRAY, LIGHT, BLUE, ORANGE)):
        s = W[W.p == p]; ax[1].plot(range(len(NS)), s.zero_width_pct, "-o", color=col, lw=1.6, ms=4, label=f"本当の割合 {p*100:g}%")
    ax[1].set_xticks(range(len(NS))); ax[1].set_xticklabels([f"{n:,}" for n in NS]); ax[1].set_xlabel("件数")
    ax[1].set_ylabel("当たりが0件で、ふつうの式の幅が0になる割合（%）"); ax[1].set_title("「0件だから0%、幅も0」になる割合", loc="left"); ax[1].legend(fontsize=8.5, frameon=False)
    fig.tight_layout(); save(fig, "a458_width_and_zero.png", SRC)

    for m in METHODS:
        print(m); print(df[df.method == m].pivot(index="p", columns="n", values="coverage_pct").round(1).to_string())
    print(df[df.p == 0.05].pivot(index="method", columns="n", values="mean_width_pt").round(2).to_string())
    print(W.pivot(index="p", columns="n", values="zero_width_pct").round(1).to_string())
    print(rule.round(1).T.to_string()); print(sim, main_js["exact_p05_n50"], main_js["saw_p05_range_n100_500"])
    print({k: main_js[k] for k in ("wald_cells_below_90", "wald_cells_below_93", "cells", "other_min", "other_mean")})
    print(ex.to_string())
    print(df[(df.method == "ふつうの式")].pivot(index="p", columns="n", values="miss_true_above_pct").round(1).to_string())


if __name__ == "__main__":
    main()
