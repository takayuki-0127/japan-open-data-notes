"""1168 小さなファイルがたくさんあると、大きさの合計と実際に使う量はどれだけ違うのか？（架空のデータ）

作成者が置いた架空のアプリの保存ファイル100万件。大きさ（バイト）は対数が正規の形（中央値2,000バイト、対数の標準偏差2.0）を整数に切り上げたもの（1バイト以上）。
保存の場所は決まった大きさの区画（ブロック、基本4,096バイト）単位で使い、1件ごとに「大きさ÷区画」を切り上げた区画の数だけ使うと置いた。
実際に使う量＝Σ 切り上げた区画の数×区画の大きさ（式どおりに決まる）。大きさの合計＝Σ 大きさ。
(1) 基本の置き方で、使う量÷大きさの合計、大きさの帯ごとの内訳
(2) 「合計＋件数×区画の半分」の目安と実際の使う量
(3) 確かめ：中央値（500〜100万バイトの6通り）×区画（1,024〜65,536バイトの4通り）×散らばり（1.0・2.0）の48通り（各20万件）
1GB＝10億バイトで数えた。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1168
SRC = "架空のアプリの保存ファイル（作成者が置いた大きさの分布からの乱数、seed 1168）"
N = 1_000_000
BASE = {"median": 2_000, "sigma": 2.0, "block": 4_096}
MEDS = [500, 2_000, 8_000, 32_000, 128_000, 1_000_000]
BLOCKS = [1_024, 4_096, 16_384, 65_536]
SIGS = [1.0, 2.0]
GN = 200_000
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def sizes(rng, med, sig, n):
    return np.maximum(np.ceil(rng.lognormal(np.log(med), sig, n)), 1).astype(np.int64)


def used_of(s, b):
    return (-(-s // b)) * b


def stats(s, b):
    u = used_of(s, b)
    tot, ut = s.sum(), u.sum()
    half = tot + len(s) * b / 2
    return {"files": int(len(s)), "size_total_gb": r(tot / 1e9, 4), "used_total_gb": r(ut / 1e9, 4),
            "used_over_size": r(ut / tot, 4), "extra_pct_of_size": r((ut / tot - 1) * 100, 2),
            "under_block_count_pct": r((s < b).mean() * 100, 2),
            "under_block_size_pct": r(s[s < b].sum() / tot * 100, 2),
            "under_block_used_pct": r(u[s < b].sum() / ut * 100, 2),
            "half_rule_over_used": r(half / ut, 4),
            "mean_waste_per_file_over_block": r((ut - tot) / len(s) / b, 4)}


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"files": N, "median_bytes": BASE["median"], "log_sigma": BASE["sigma"], "block_bytes": BASE["block"],
                       "mean_bytes_formula": r(BASE["median"] * np.exp(BASE["sigma"] ** 2 / 2), 1)}}
    s = sizes(rng, BASE["median"], BASE["sigma"], N)
    b = BASE["block"]
    u = used_of(s, b)
    base = stats(s, b)
    base.update({"size_median_bytes": float(np.median(s)), "size_mean_bytes": r(s.mean(), 1),
                 "used_mean_bytes": r(u.mean(), 1)})
    out["base"] = base
    pd.DataFrame({"file_id": np.arange(1, 10_001), "size_bytes": s[:10_000], "used_bytes": u[:10_000]}
                 ).to_csv(DATA / "files_example.csv", index=False)

    # (1) 帯ごと
    edges = [0, 512, 4_096, 65_536, 1_048_576, np.inf]
    labs = ["512バイト未満", "512〜4,096", "4,096〜65,536", "65,536〜約100万", "約100万以上"]
    rows = []
    for lo, hi, lb in zip(edges[:-1], edges[1:], labs):
        m = (s >= lo) & (s < hi)
        rows.append({"size_band": lb, "count_pct": r(m.mean() * 100, 2), "size_pct": r(s[m].sum() / s.sum() * 100, 2),
                     "used_pct": r(u[m].sum() / u.sum() * 100, 2), "used_over_size": r(u[m].sum() / s[m].sum(), 3)})
    pd.DataFrame(rows).to_csv(RES / "base_by_band.csv", index=False)
    out["base_by_band"] = rows

    # 区画の大きさだけを変える（同じ100万件）
    brows = []
    for bb in BLOCKS:
        brows.append({"block_bytes": bb, **stats(s, bb)})
    pd.DataFrame(brows).to_csv(RES / "base_by_block.csv", index=False)
    out["base_by_block"] = brows

    # (3) 48通り
    grows = []
    for sig in SIGS:
        for med in MEDS:
            ss = sizes(rng, med, sig, GN)
            for bb in BLOCKS:
                grows.append({"log_sigma": sig, "median_bytes": med, "block_bytes": bb, "median_over_block": r(med / bb, 4),
                              **stats(ss, bb)})
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"settings": len(grid),
                   "used_over_size_range": [r(grid.used_over_size.min(), 4), r(grid.used_over_size.max(), 4)],
                   "half_rule_range": [r(grid.half_rule_over_used.min(), 4), r(grid.half_rule_over_used.max(), 4)],
                   "half_rule_within5_count": int(((grid.half_rule_over_used - 1).abs() <= 0.05).sum()),
                   "half_rule_under_count": int((grid.half_rule_over_used < 1).sum())}
    for lo, hi, key in [(0, 0.5, "median_under_half_block"), (0.5, 4, "median_half_to_4_blocks"), (4, np.inf, "median_over_4_blocks")]:
        g = grid[(grid.median_over_block >= lo) & (grid.median_over_block < hi)]
        out["grid"][key] = {"settings": len(g),
                            "used_over_size_range": [r(g.used_over_size.min(), 4), r(g.used_over_size.max(), 4)],
                            "half_rule_range": [r(g.half_rule_over_used.min(), 4), r(g.half_rule_over_used.max(), 4)]}
    # 同じ中央値・区画で、散らばりだけ変える
    p = grid.pivot_table(index=["median_bytes", "block_bytes"], columns="log_sigma", values="used_over_size")
    out["grid"]["sigma2_lower_count"] = int((p[2.0] < p[1.0]).sum())
    out["headline"] = {"used_over_size": base["used_over_size"], "under_block_count_pct": base["under_block_count_pct"],
                       "under_block_size_pct": base["under_block_size_pct"], "under_block_used_pct": base["under_block_used_pct"],
                       "half_rule_over_used": base["half_rule_over_used"]}

    # 図1：帯ごとの件数・大きさ・使う量の割合
    bd = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    x = np.arange(len(bd))
    for i, (col, c, lb) in enumerate([("count_pct", GRAY, "件数の割合"), ("size_pct", BLUE, "大きさの合計に占める割合"),
                                      ("used_pct", ORANGE, "実際に使う量に占める割合")]):
        ax.bar(x + (i - 1) * 0.27, bd[col], 0.27, color=c, label=lb)
        for xi, v in zip(x, bd[col]):
            ax.text(xi + (i - 1) * 0.27, v + 1, f"{v:.2f}", ha="center", fontsize=6.5, color=INK)
    ax.set_xticks(x, bd.size_band, fontsize=9)
    ax.set_xlabel("ファイルの大きさ（バイト）")
    ax.set_ylabel("%")
    ax.set_ylim(0, max(bd[["count_pct", "size_pct", "used_pct"]].max()) * 1.3)
    ax.set_title(f"区画より小さいファイルは大きさで{base['under_block_size_pct']:.2f}%、使う量で{base['under_block_used_pct']:.2f}%（区画4,096バイト）")
    ax.legend(fontsize=9, frameon=False, loc="upper left", ncol=3)
    save(fig, "a1168_by_band.png", SRC + "　100万件、中央値2,000バイト・対数の標準偏差2.0")

    # 図2：中央値と区画で、使う量÷大きさの合計（散らばり2.0）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    for bb, c in zip(BLOCKS, [GREEN, BLUE, ORANGE, INK]):
        g = grid[(grid.log_sigma == 2.0) & (grid.block_bytes == bb)]
        ax.plot(g.median_bytes, g.used_over_size, "o-", color=c, label=f"区画{bb:,}バイト")
    ax.set_xscale("log")
    ax.set_xticks(MEDS, [f"{m:,}" for m in MEDS], fontsize=8.5)
    ax.set_xlabel("ファイルの大きさの中央値（バイト、対数の目盛り）")
    ax.set_ylabel("使う量÷大きさの合計（倍）")
    ax.set_ylim(0, None)
    ax.axhline(1, color=GRAY, lw=1, ls="--")
    ax.set_title("中央値が区画に比べて小さいほど、使う量は大きさの合計を上回った")
    ax.legend(fontsize=9, frameon=False)
    save(fig, "a1168_grid_ratio.png", SRC + "　対数の標準偏差2.0の24通り（各20万件）")

    # 図3：「合計＋件数×区画の半分」の目安÷実際の使う量（48通り）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    for sig, mk in zip(SIGS, ["o", "s"]):
        g = grid[grid.log_sigma == sig]
        ax.scatter(g.median_over_block, g.half_rule_over_used, marker=mk, s=28,
                   color=BLUE if sig == 2.0 else ORANGE, label=f"対数の標準偏差{sig}")
    ax.set_xscale("log")
    tk = [0.01, 0.1, 1, 10, 100, 1000]
    ax.set_xticks(tk, [f"{t:g}" for t in tk])
    ax.minorticks_off()
    ax.axhline(1, color=GRAY, lw=1, ls="--")
    ax.set_xlabel("中央値÷区画の大きさ（対数の目盛り）")
    ax.set_ylabel("目安÷実際の使う量（倍）")
    ax.set_ylim(0, 1.2)
    ax.set_title("「合計＋件数×区画の半分」は、中央値が区画より小さいと低く出た（48通り）")
    ax.legend(fontsize=9, frameon=False, loc="lower right")
    save(fig, "a1168_half_rule.png", SRC + "　各20万件")

    with open(RES / "a1168_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(json.dumps(out["headline"], ensure_ascii=False), round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
