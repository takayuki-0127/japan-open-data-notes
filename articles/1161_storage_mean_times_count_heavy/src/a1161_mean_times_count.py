"""1161 1件あたりの大きさの平均に件数を掛けた見込みは、とても大きい件が少しまざるとどれだけ外れるのか？（架空のデータ）

作成者が置いた架空のアプリの保存ファイル。ふつうのファイルは大きさの対数が正規の形（中央値300KB、対数の標準偏差1.0）、
ごく一部（基本0.1%）の「とても大きいファイル」は中央値500MB（対数の標準偏差0.8）と置いた。
来年の100万件の合計を、今あるファイルから選んだ n 件（基本1,000件）の平均×100万で見込む。
(1) 正しい答え：置いた分布での100万件の合計の期待値（100万×1件の平均、式）。実際の1年の合計の振れも200年分数える
(2) 見込み÷正しい答えの分かれ方（基本10,000回）。中央値×件数、上の1%を外れとして除いた平均×件数とも比べる
(3) 確かめ：とても大きいファイルの割合（0.01・0.1・1%）×その大きさ（中央値50MB・500MB）×選ぶ件数（100・1,000・10,000件）の18通り（各2,000回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1161
SRC = "架空のアプリの保存ファイル（作成者が置いた大きさの分布からの乱数、seed 1161）"
N_YEAR = 1_000_000
MED_S, SIG_S = 300.0, 1.0          # ふつうのファイル（KB）
MED_H_BASE, SIG_H = 500_000.0, 0.8  # とても大きいファイル（KB）
P_BASE, N_BASE = 0.001, 1000
R_BASE, R_GRID, YEARS = 10_000, 2_000, 200
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def means(p, med_h):
    ms = MED_S * np.exp(SIG_S ** 2 / 2)
    mh = med_h * np.exp(SIG_H ** 2 / 2)
    return ms, mh, (1 - p) * ms + p * mh


def draw(rng, n, p, med_h):
    k = rng.binomial(n, p)
    x = rng.lognormal(np.log(MED_S), SIG_S, n)
    if k:
        x[:k] = rng.lognormal(np.log(med_h), SIG_H, k)
    return x, k


def sample_stats(rng, n, p, med_h, R):
    """R 回、n 件を選んで 平均・中央値・上1%を除いた平均・とても大きい件の数 を返す"""
    out = np.empty((R, 4))
    for i in range(R):
        x, k = draw(rng, n, p, med_h)
        xs = np.sort(x)
        cut = int(np.floor(n * 0.99))
        out[i] = [x.mean(), np.median(x), xs[:cut].mean(), k]
    return out


def summarize(st, mu, n, p):
    ratio = st[:, 0] / mu
    return {"mean_ratio": r(ratio.mean()), "median_ratio": r(np.median(ratio)),
            "p10_ratio": r(np.quantile(ratio, 0.1)), "p90_ratio": r(np.quantile(ratio, 0.9)),
            "below_0_8_pct": r((ratio < 0.8).mean() * 100, 2), "above_1_25_pct": r((ratio > 1.25).mean() * 100, 2),
            "within_20pct_pct": r(((ratio >= 0.8) & (ratio <= 1.2)).mean() * 100, 2),
            "below_1_pct": r((ratio < 1).mean() * 100, 2),
            "no_huge_in_sample_pct": r((st[:, 3] == 0).mean() * 100, 2),
            "no_huge_formula_pct": r((1 - p) ** n * 100, 2),
            "median_times_count_ratio": r(np.median(st[:, 1] / mu)),
            "trimmed_times_count_ratio": r(np.median(st[:, 2] / mu))}


def main():
    rng = np.random.default_rng(SEED)
    out = {}
    ms, mh, mu = means(P_BASE, MED_H_BASE)
    huge_share = P_BASE * mh / mu
    out["setting"] = {"n_year": N_YEAR, "normal_median_kb": MED_S, "normal_mean_kb_formula": r(ms, 2),
                      "huge_median_kb": MED_H_BASE, "huge_mean_kb_formula": r(mh, 1), "huge_share_count_pct": P_BASE * 100,
                      "mean_kb_formula": r(mu, 2), "true_total_gb": r(mu * N_YEAR / 1e6, 2),
                      "huge_share_bytes_pct_formula": r(huge_share * 100, 2)}
    # data：今あるファイルの例 10,000件
    x, k = draw(rng, 10_000, P_BASE, MED_H_BASE)
    kind = np.where(np.arange(10_000) < k, "huge", "normal")
    df = pd.DataFrame({"file_id": np.arange(1, 10_001), "kind": kind, "size_kb": np.round(x, 1)})
    df.to_csv(DATA / "files_example.csv", index=False)

    # (1) 実際の1年（100万件）の合計の振れ
    yrs = []
    for y in range(YEARS):
        xy, ky = draw(rng, N_YEAR, P_BASE, MED_H_BASE)
        s = xy.sum()
        yrs.append({"year": y + 1, "huge_files": int(ky), "total_gb": r(s / 1e6, 3),
                    "ratio_to_expected": r(s / (mu * N_YEAR)), "huge_bytes_pct": r(xy[:ky].sum() / s * 100, 2)})
    yrs = pd.DataFrame(yrs)
    yrs.to_csv(RES / "actual_years.csv", index=False)
    out["actual_years"] = {"years": YEARS, "ratio_p5": r(yrs.ratio_to_expected.quantile(0.05)),
                           "ratio_p95": r(yrs.ratio_to_expected.quantile(0.95)),
                           "ratio_min": r(yrs.ratio_to_expected.min()), "ratio_max": r(yrs.ratio_to_expected.max()),
                           "huge_bytes_pct_mean": r(yrs.huge_bytes_pct.mean(), 2),
                           "huge_files_mean": r(yrs.huge_files.mean(), 1)}
    print("years", round(time.time() - T0, 1), flush=True)

    # (2) 基本：n=1,000 件の平均×100万
    st = sample_stats(rng, N_BASE, P_BASE, MED_H_BASE, R_BASE)
    base = summarize(st, mu, N_BASE, P_BASE)
    ratios = st[:, 0] / mu
    pd.DataFrame({"rep": np.arange(1, R_BASE + 1), "huge_in_sample": st[:, 3].astype(int),
                  "estimate_ratio": np.round(ratios, 4)}).to_csv(RES / "base_estimates.csv", index=False)
    byk = []
    for kk in range(0, 5):
        m = st[:, 3] == kk if kk < 4 else st[:, 3] >= 4
        byk.append({"huge_in_sample": f"{kk}" if kk < 4 else "4以上", "share_pct": r(m.mean() * 100, 2),
                    "median_ratio": r(np.median(ratios[m]))})
    pd.DataFrame(byk).to_csv(RES / "base_by_huge_count.csv", index=False)
    # 対照：とても大きいファイルがないとき
    st0 = sample_stats(rng, N_BASE, 0.0, MED_H_BASE, R_BASE)
    mu0 = means(0.0, MED_H_BASE)[2]
    ctrl = summarize(st0, mu0, N_BASE, 0.0)
    base["expected_huge_in_sample"] = r(N_BASE * P_BASE, 2)
    out["base"] = base
    out["base_by_huge_count"] = byk
    out["control_no_huge"] = ctrl
    print("base", round(time.time() - T0, 1), flush=True)

    # (3) 18通り
    rows = []
    for p in [0.0001, 0.001, 0.01]:
        for medh in [50_000.0, 500_000.0]:
            mu_g = means(p, medh)[2]
            share = p * means(p, medh)[1] / mu_g
            for n in [100, 1000, 10000]:
                s = summarize(sample_stats(rng, n, p, medh, R_GRID), mu_g, n, p)
                rows.append({"huge_pct": p * 100, "huge_median_mb": medh / 1000, "n_sample": n,
                             "huge_bytes_pct_formula": r(share * 100, 2), **s})
            print("grid", p, medh, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"settings": len(grid),
                   "median_ratio_min": r(grid.median_ratio.min()), "median_ratio_max": r(grid.median_ratio.max()),
                   "mean_ratio_min": r(grid.mean_ratio.min()), "mean_ratio_max": r(grid.mean_ratio.max()),
                   "within_20_min": r(grid.within_20pct_pct.min(), 2), "within_20_max": r(grid.within_20pct_pct.max(), 2),
                   "below_1_min": r(grid.below_1_pct.min(), 2), "below_1_max": r(grid.below_1_pct.max(), 2),
                   "settings_below1_over_60": int((grid.below_1_pct > 60).sum()),
                   "settings_within20_over_90": int((grid.within_20pct_pct > 90).sum())}
    out["headline"] = {"huge_share_bytes_pct": out["setting"]["huge_share_bytes_pct_formula"],
                       "median_ratio": base["median_ratio"], "below_0_8_pct": base["below_0_8_pct"],
                       "within_20pct_pct": base["within_20pct_pct"], "mean_ratio": base["mean_ratio"],
                       "ctrl_within_20pct_pct": ctrl["within_20pct_pct"]}

    # 図1：見込み÷正しい答えの分かれ方
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bins = np.linspace(0, 3, 61)
    ax.hist(np.clip(ratios, 0, 3), bins=bins, color=BLUE, alpha=0.85, label="とても大きいファイル0.1%あり")
    ax.hist(np.clip(st0[:, 0] / mu0, 0, 3), bins=bins, color=GRAY, alpha=0.6, label="とても大きいファイルなし（対照）")
    ax.axvline(1, color=INK, lw=1)
    ax.axvline(base["median_ratio"], color=ORANGE, lw=1.5, ls="--")
    ax.text(base["median_ratio"] - 0.02, ax.get_ylim()[1] * 0.92, f"中央値 {base['median_ratio']:g}倍", color=ORANGE, fontsize=9, ha="right")
    ax.set_xlabel("見込み ÷ 正しい答え（3倍以上は3にまとめた）")
    ax.set_ylabel("回数（10,000回のうち）")
    ax.set_title("1,000件の平均×100万件の見込みは、多くの回で低めに出る")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1161_ratio_hist.png", SRC)

    # 図2：選んだ中のとても大きい件の数ごと
    fig, ax = plt.subplots(figsize=(7, 4.2))
    lab = [d["huge_in_sample"] for d in byk]
    ax.bar(lab, [d["median_ratio"] for d in byk], color=BLUE)
    for i, d in enumerate(byk):
        ax.text(i, d["median_ratio"] + 0.03, f"{d['median_ratio']:g}倍\n（{d['share_pct']:g}%の回）", ha="center", fontsize=8.5,
                bbox=dict(facecolor="white", edgecolor="none", pad=1))
    ax.axhline(1, color=INK, lw=1)
    ax.set_ylim(0, max(d["median_ratio"] for d in byk) * 1.25)
    ax.set_xlabel("選んだ1,000件に入っていた、とても大きいファイルの数")
    ax.set_ylabel("見込み ÷ 正しい答え（中央値）")
    ax.set_title("とても大きいファイルを何件引いたかで、見込みが決まる")
    save(fig, "a1161_by_huge_count.png", SRC)

    # 図3：18通りの「±20%に入った割合」
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    cols = {100: GRAY, 1000: BLUE, 10000: GREEN}
    labels = []
    for j, ((p, medh), g) in enumerate(grid.groupby(["huge_pct", "huge_median_mb"], sort=True)):
        labels.append(f"{p:g}%\n{medh:g}MB")
        for t, n in enumerate([100, 1000, 10000]):
            v = g[g.n_sample == n].within_20pct_pct.iloc[0]
            ax.bar(j + (t - 1) * 0.27, v, width=0.27, color=cols[n], label=f"{n:,}件を選ぶ" if j == 0 else None)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylim(0, 100)
    ax.set_xlabel("とても大きいファイルの割合（件数）と大きさ（中央値）")
    ax.set_ylabel("見込みが正しい答えの±20%に入った回（%）")
    ax.set_title("±20%に入る回の割合は、大きい件の量と選ぶ件数で大きく動く")
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    ax.set_title("±20%に入る回の割合は、大きい件の量と選ぶ件数で大きく動く", pad=28)
    save(fig, "a1161_grid_within20.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1161_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
