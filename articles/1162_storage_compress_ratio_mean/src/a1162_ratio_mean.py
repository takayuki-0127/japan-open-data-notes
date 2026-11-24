"""1162 ファイルごとの圧縮率を平均すると、全体の縮み方とどれだけ違うのか？（架空のデータ）

作成者が置いた架空のアプリの保存ファイル5万件。大きさは対数が正規の形（中央値50KB、対数の標準偏差1.5）。
圧縮後の大きさ＝決まった上乗せ H（基本0.5KB）＋中身の縮み q×元の大きさ。圧縮して小さくならないファイルは元のまま置く。
q は中央値0.35（対数の標準偏差0.3、1が上限）で、基本は大きさと関係なし。圧縮率＝圧縮後÷圧縮前（小さいほどよく縮む）。
(1) 全体の圧縮率（圧縮後の合計÷圧縮前の合計）＝正しい答え と、ファイルごとの率の平均・中央値を比べる
(2) 減る量の見込み（(1−率の平均)×圧縮前の合計）÷実際に減る量
(3) 一部（200件）を試しに圧縮して見込む：率の平均と、合計÷合計（2,000回）
(4) 確かめ：上乗せ H（0・0.3・1・3KB）×大きさの散らばり（1.0・1.5・2.0）×大きさと縮み方の関係（なし・大きいほど縮まない・大きいほど縮む）の36通り
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1162
SRC = "架空のアプリの保存ファイル（作成者が置いた大きさと縮み方からの乱数、seed 1162）"
N = 50_000
MED_S = 50.0
Q_MED, Q_SIG = 0.35, 0.3
BASE = {"H": 0.5, "sig": 1.5, "b": 0.0}
RELS = {"なし": 0.0, "大きいほど縮まない": 0.5, "大きいほど縮む": -0.5}
SAMPLE_N, SAMPLE_R = 200, 2000
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def make(rng, H, sig, b, n=N):
    s = rng.lognormal(np.log(MED_S), sig, n)
    z = (np.log(s) - np.log(MED_S)) / sig
    q = np.minimum(np.exp(np.log(Q_MED) + b * z + rng.normal(0, Q_SIG, n)), 1.0)
    c = np.minimum(H + q * s, s)
    return s, c


def stats(s, c):
    ratio = c / s
    tot = c.sum() / s.sum()
    mr = ratio.mean()
    cov = np.mean((ratio - mr) * (s - s.mean()))
    saved_true = s.sum() - c.sum()
    saved_est = (1 - mr) * s.sum()
    return {"total_ratio_pct": r(tot * 100, 2), "mean_ratio_pct": r(mr * 100, 2),
            "median_ratio_pct": r(np.median(ratio) * 100, 2),
            "weighted_mean_ratio_pct": r(np.average(ratio, weights=s) * 100, 2),
            "diff_points": r((mr - tot) * 100, 2),
            "diff_formula_points": r(-cov / s.mean() * 100, 2),
            "saved_est_over_true": r(saved_est / saved_true),
            "saved_true_pct": r((1 - tot) * 100, 2), "saved_est_pct": r((1 - mr) * 100, 2),
            "not_smaller_pct": r((c >= s).mean() * 100, 2)}


def main():
    rng = np.random.default_rng(SEED)
    out = {}
    s, c = make(rng, BASE["H"], BASE["sig"], BASE["b"])
    base = stats(s, c)
    ratio = c / s
    small = s < 10
    base.update({"files": N, "size_median_kb": r(np.median(s), 2), "size_mean_kb": r(s.mean(), 2),
                 "small_under_10kb_count_pct": r(small.mean() * 100, 2),
                 "small_under_10kb_bytes_pct": r(s[small].sum() / s.sum() * 100, 2),
                 "small_under_10kb_mean_ratio_pct": r(ratio[small].mean() * 100, 2),
                 "over_1mb_count_pct": r((s >= 1000).mean() * 100, 2),
                 "over_1mb_bytes_pct": r(s[s >= 1000].sum() / s.sum() * 100, 2),
                 "over_1mb_mean_ratio_pct": r(ratio[s >= 1000].mean() * 100, 2),
                 "total_before_gb": r(s.sum() / 1e6, 3), "total_after_gb": r(c.sum() / 1e6, 3),
                 "saved_true_gb": r((s.sum() - c.sum()) / 1e6, 3),
                 "saved_est_gb": r((1 - ratio.mean()) * s.sum() / 1e6, 3)})
    out["base"] = base
    pd.DataFrame({"file_id": np.arange(1, 5001), "size_kb": np.round(s[:5000], 3),
                  "compressed_kb": np.round(c[:5000], 3)}).to_csv(DATA / "files_example.csv", index=False)

    # 大きさの区分ごと
    edges = [0, 1, 10, 100, 1000, np.inf]
    labs = ["1KB未満", "1〜10KB", "10〜100KB", "100KB〜1MB", "1MB以上"]
    rows = []
    for lo, hi, lb in zip(edges[:-1], edges[1:], labs):
        m = (s >= lo) & (s < hi)
        rows.append({"size_band": lb, "count_pct": r(m.mean() * 100, 2), "bytes_pct": r(s[m].sum() / s.sum() * 100, 2),
                     "mean_ratio_pct": r(ratio[m].mean() * 100, 2), "total_ratio_pct": r(c[m].sum() / s[m].sum() * 100, 2)})
    bands = pd.DataFrame(rows)
    bands.to_csv(RES / "base_by_size.csv", index=False)
    out["base_by_size"] = rows

    # 関係の3通り（ほかは基本。「なし」は基本の5万件そのもの）
    rel_rows = []
    rel_data = {}
    for name, b in RELS.items():
        ss, cc = (s, c) if b == BASE["b"] else make(rng, BASE["H"], BASE["sig"], b)
        st = stats(ss, cc)
        rel_rows.append({"relation": name, "b": b, **st})
        rel_data[name] = (ss, cc)
    rel = pd.DataFrame(rel_rows)
    rel.to_csv(RES / "relation_three.csv", index=False)
    out["relation_three"] = rel_rows

    # (3) 200件を試しに圧縮
    srows = []
    for name in RELS:
        ss, cc = rel_data[name]
        tot = cc.sum() / ss.sum()
        est_mean, est_pool = [], []
        for _ in range(SAMPLE_R):
            idx = rng.integers(0, N, SAMPLE_N)
            est_mean.append((cc[idx] / ss[idx]).mean())
            est_pool.append(cc[idx].sum() / ss[idx].sum())
        em, ep = np.array(est_mean), np.array(est_pool)
        srows.append({"relation": name, "true_total_ratio_pct": r(tot * 100, 2),
                      "mean_method_median_pct": r(np.median(em) * 100, 2),
                      "mean_method_within_3pt_pct": r((np.abs(em - tot) <= 0.03).mean() * 100, 2),
                      "pooled_method_median_pct": r(np.median(ep) * 100, 2),
                      "pooled_method_p10_pct": r(np.quantile(ep, 0.1) * 100, 2),
                      "pooled_method_p90_pct": r(np.quantile(ep, 0.9) * 100, 2),
                      "pooled_method_within_3pt_pct": r((np.abs(ep - tot) <= 0.03).mean() * 100, 2)})
    samp = pd.DataFrame(srows)
    samp.to_csv(RES / "sample_200.csv", index=False)
    out["sample_200"] = srows
    print("sample", round(time.time() - T0, 1), flush=True)

    # (4) 36通り
    grows = []
    for H in [0.0, 0.3, 1.0, 3.0]:
        for sig in [1.0, 1.5, 2.0]:
            for name, b in RELS.items():
                ss, cc = make(rng, H, sig, b)
                grows.append({"overhead_kb": H, "size_sigma": sig, "relation": name, **stats(ss, cc)})
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"settings": len(grid), "diff_min": r(grid.diff_points.min(), 2), "diff_max": r(grid.diff_points.max(), 2),
                   "max_abs_formula_gap": r((grid.diff_points - grid.diff_formula_points).abs().max(), 2),
                   "max_abs_weighted_gap": r((grid.weighted_mean_ratio_pct - grid.total_ratio_pct).abs().max(), 2),
                   "total_ratio_range": [r(grid.total_ratio_pct.min(), 2), r(grid.total_ratio_pct.max(), 2)],
                   "mean_ratio_range": [r(grid.mean_ratio_pct.min(), 2), r(grid.mean_ratio_pct.max(), 2)]}
    for name in RELS:
        g = grid[grid.relation == name]
        out["grid"][name] = {"diff_min": r(g.diff_points.min(), 2), "diff_max": r(g.diff_points.max(), 2),
                             "saved_ratio_min": r(g.saved_est_over_true.min()), "saved_ratio_max": r(g.saved_est_over_true.max()),
                             "positive": int((g.diff_points > 0).sum()), "negative": int((g.diff_points < 0).sum())}
    g0 = grid[(grid.relation == "なし") & (grid.overhead_kb == 0)]
    out["grid"]["none_H0_diff_range"] = [r(g0.diff_points.min(), 2), r(g0.diff_points.max(), 2)]
    out["headline"] = {"total_ratio_pct": base["total_ratio_pct"], "mean_ratio_pct": base["mean_ratio_pct"],
                       "diff_points": base["diff_points"], "saved_est_over_true": base["saved_est_over_true"],
                       "big_less": rel_rows[1], "big_more": rel_rows[2]}

    # 図1：大きさと圧縮率
    fig, ax = plt.subplots(figsize=(7, 4.2))
    k = 3000
    ax.scatter(s[:k], ratio[:k] * 100, s=4, color=BLUE, alpha=0.35, lw=0)
    ax.set_xscale("log")
    ax.axhline(base["mean_ratio_pct"], color=ORANGE, lw=1.5, ls="--")
    ax.axhline(base["total_ratio_pct"], color=INK, lw=1.5)
    ax.text(0.12, base["mean_ratio_pct"] + 2, f"ファイルごとの率の平均 {base['mean_ratio_pct']:g}%", color=ORANGE, fontsize=9,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1))
    ax.text(0.12, base["total_ratio_pct"] - 6, f"全体（合計÷合計） {base['total_ratio_pct']:g}%", color=INK, fontsize=9,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1))
    ax.set_ylim(0, 105)
    ax.set_xlabel("元の大きさ（KB、対数の目盛り）")
    ax.set_ylabel("圧縮率（圧縮後÷圧縮前、%）")
    ax.set_title("小さいファイルほど縮まず、率の平均は全体より高く出る（基本の置き方）")
    save(fig, "a1162_size_vs_ratio.png", SRC)

    # 図2：関係の3通り
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(3)
    ax.bar(x - 0.2, rel.mean_ratio_pct, width=0.4, color=ORANGE, label="ファイルごとの率の平均")
    ax.bar(x + 0.2, rel.total_ratio_pct, width=0.4, color=INK, label="全体（合計÷合計）")
    for i, row in rel.iterrows():
        ax.text(i - 0.2, row.mean_ratio_pct + 1.5, f"{row.mean_ratio_pct:g}%", ha="center", fontsize=9)
        ax.text(i + 0.2, row.total_ratio_pct + 1.5, f"{row.total_ratio_pct:g}%", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"大きさと縮み方の関係：\n{n}" for n in rel.relation], fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_ylabel("圧縮率（%）")
    ax.set_title("ずれの向きは、大きさと縮み方の関係で入れかわる")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1162_three_relations.png", SRC)

    # 図3：36通りのずれ
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    cols = {"なし": GRAY, "大きいほど縮まない": BLUE, "大きいほど縮む": GREEN}
    for t, name in enumerate(RELS):
        g = grid[grid.relation == name].reset_index(drop=True)
        xs = np.arange(len(g)) + (t - 1) * 0.27
        ax.bar(xs, g.diff_points, width=0.27, color=cols[name], label=f"関係：{name}")
    g = grid[grid.relation == "なし"].reset_index(drop=True)
    ax.set_xticks(range(len(g)))
    ax.set_xticklabels([f"{h:g}KB\n{sg:g}" for h, sg in zip(g.overhead_kb, g.size_sigma)], fontsize=8)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xlabel("上乗せの大きさ（上）と大きさの散らばり（下：対数の標準偏差）")
    ax.set_ylabel("率の平均 − 全体の率（ポイント）")
    ax.set_title("36通りの、率の平均と全体の率の差", pad=28)
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, title=None)
    save(fig, "a1162_grid_diff.png", SRC)

    (RES / "a1162_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print("sec", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
