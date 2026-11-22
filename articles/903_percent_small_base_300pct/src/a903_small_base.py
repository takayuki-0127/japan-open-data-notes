"""903 小さい数からの「300%増」は、どこまで意味があるのか？（架空のデータ）

架空の会社の商品2,000品目。品目ごとに「本当の月の売れる速さ」（前年）と「本当の伸び」を作成者が置き、
前年と今年の同じ月の販売個数は、その速さのポアソン分布から引く。本当に伸びた品目（伸びる品目）は5%と置く。
「前年比+300%以上」（今年が前年の4倍以上）の品目に、伸びる品目がどれだけ入っているかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 903
SRC = "架空の商品と販売個数（作成者が乱数で作成、seed 903）"
N_ITEM, REPS = 2000, 50
BASE_MED, BASE_SDLOG = 20.0, 1.2      # 前年の月の売れる速さ（個）：中央値20・対数で標準偏差1.2
P_GROW = 0.05                         # 伸びる品目の割合
GROW_MED, GROW_SDLOG = 3.0, 0.4       # 伸びる品目の本当の倍率（中央値3倍＝+200%）
FLAT_SDLOG = 0.1                      # ほかの品目の本当の倍率（中央値1倍）
BUCKETS = [(1, 1, "1個"), (2, 3, "2〜3個"), (4, 9, "4〜9個"), (10, 29, "10〜29個"), (30, 10**9, "30個以上")]


def make_items(rng, n=N_ITEM, base_med=BASE_MED, p_grow=P_GROW):
    lam0 = np.clip(base_med * np.exp(rng.normal(0, BASE_SDLOG, n)), 0.3, 3000)
    grower = rng.uniform(0, 1, n) < p_grow
    g = np.where(grower, GROW_MED * np.exp(rng.normal(0, GROW_SDLOG, n)), np.exp(rng.normal(0, FLAT_SDLOG, n)))
    y0 = rng.poisson(lam0)
    y1 = rng.poisson(lam0 * g)
    y2 = rng.poisson(lam0 * g)          # 翌年：今年の本当の速さのまま（伸びは続かず、戻りもしない）
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = np.where(y0 > 0, (y1 - y0) / y0 * 100, np.nan)
    return pd.DataFrame({"item_id": np.arange(1, n + 1), "lam0": lam0, "true_ratio": g, "grower": grower.astype(int),
                         "y0": y0, "y1": y1, "y2": y2, "pct": pct})


def flag(df):
    return df["pct"] >= 300


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    one = make_items(np.random.default_rng(SEED * 10))
    one.to_csv(DATA / "items.csv", index=False, float_format="%.4f")

    reps = [make_items(np.random.default_rng(SEED * 1000 + r)).assign(rep=r) for r in range(REPS)]
    al = pd.concat(reps, ignore_index=True)
    f = al[flag(al)]

    # 1) 「+300%以上」の品目の中身
    main_ = {
        "items_per_rep": N_ITEM, "reps": REPS,
        "flag_per_rep": round(len(f) / REPS, 2),
        "flag_share_y0_le3": round(float((f.y0 <= 3).mean()), 4),
        "flag_median_y0": float(f.y0.median()),
        "flag_share_grower": round(float(f.grower.mean()), 4),
        "flag_median_true_pct": round(float((f.true_ratio.median() - 1) * 100), 1),
        "grower_share_flagged": round(float(flag(al[al.grower == 1]).mean()), 4),
        "nongrower_flag_per_rep": round(float(((f.grower == 0).sum()) / REPS), 2),
        "y0_zero_share": round(float((al.y0 == 0).mean()), 4),
        "y0_zero_y1_pos_share": round(float(((al.y0 == 0) & (al.y1 > 0)).mean()), 4),
        "grower_share_all": round(float(al.grower.mean()), 4),
    }
    # 前年10個以上に絞ると
    f10 = f[f.y0 >= 10]
    main_["flag_y0ge10_per_rep"] = round(len(f10) / REPS, 2)
    main_["flag_y0ge10_share_grower"] = round(float(f10.grower.mean()), 4)
    main_["grower_share_flagged_y0ge10"] = round(float((flag(al) & (al.y0 >= 10) & (al.grower == 1)).sum()
                                                       / (al.grower == 1).sum()), 4)

    # 2) 前年の個数ごと
    rows = []
    for lo, hi, lab in BUCKETS:
        b = al[al.y0.between(lo, hi)]
        fb = b[flag(b)]
        rows.append({"y0_bucket": lab, "items_per_rep": round(len(b) / REPS, 1),
                     "flag_per_rep": round(len(fb) / REPS, 2),
                     "flag_rate": round(float(flag(b).mean()), 4),
                     "flag_share_grower": round(float(fb.grower.mean()), 4) if len(fb) else None,
                     "nongrower_flag_rate": round(float(flag(b[b.grower == 0]).mean()), 4)})
    by_base = pd.DataFrame(rows)
    by_base.to_csv(RES / "by_base.csv", index=False)

    # 3) 本当は横ばい（倍率1）の品目で、前年比がどれだけ振れるか
    flat = []
    for lam in [1, 2, 3, 5, 10, 30, 100]:
        y0 = rng.poisson(lam, 200000)
        y1 = rng.poisson(lam, 200000)
        ok = y0 > 0
        p = (y1[ok] - y0[ok]) / y0[ok] * 100
        flat.append({"rate": lam, "y0_zero": round(float((~ok).mean()), 4),
                     "ge300_among_computable": round(float((p >= 300).mean()), 4),
                     "pct_p10": round(float(np.percentile(p, 10)), 1), "pct_p90": round(float(np.percentile(p, 90)), 1)})
    flat = pd.DataFrame(flat)
    flat.to_csv(RES / "flat_item_swing.csv", index=False)

    # 4) 並べ方：上位20品目のうち伸びる品目の割合（50回の平均）
    rk = []
    for r, g in al.groupby("rep"):
        gg = g[g.y0 > 0]
        for name, sc in [("前年比（%）の大きい順", gg.pct),
                         ("増えた個数の多い順", (gg.y1 - gg.y0).astype(float)),
                         ("前年・今年に5個ずつ足した比", (gg.y1 + 5) / (gg.y0 + 5)),
                         ("前年10個以上に絞って前年比の順", gg.pct.where(gg.y0 >= 10, -np.inf))]:
            top = sc.sort_values(ascending=False, kind="mergesort").index[:20]
            rk.append({"rep": r, "method": name, "top20_share_grower": float(gg.loc[top, "grower"].mean()),
                       "top20_median_y0": float(gg.loc[top, "y0"].median())})
    rk = pd.DataFrame(rk).groupby("method", sort=False).mean(numeric_only=True).drop(columns="rep").round(3)
    rk.to_csv(RES / "ranking_top20.csv")

    # 5) 翌年：+300%以上の品目の翌年の個数
    nxt = {}
    for lab, s in [("伸びる品目", f[f.grower == 1]), ("ほかの品目", f[f.grower == 0])]:
        nxt[lab] = {"n": int(len(s)), "median_y2_over_y1": round(float((s.y2 / s.y1).median()), 3),
                    "share_y2_lt_y1": round(float((s.y2 < s.y1).mean()), 4),
                    "share_y2_ge300_vs_y0": round(float(((s.y2 - s.y0) / s.y0 >= 3).mean()), 4)}
    nxt["全体"] = {"n": int(len(f)), "median_y2_over_y1": round(float((f.y2 / f.y1).median()), 3),
                  "share_y2_lt_y1": round(float((f.y2 < f.y1).mean()), 4),
                  "share_y2_ge300_vs_y0": round(float(((f.y2 - f.y0) / f.y0 >= 3).mean()), 4)}

    # 6) 確かめ：伸びる品目の割合 × 前年の速さの中央値（9通り × 20回）
    sens = []
    for pg in [0.01, 0.05, 0.10]:
        for bm in [5.0, 20.0, 80.0]:
            d = pd.concat([make_items(np.random.default_rng(SEED * 77 + r + int(pg * 1000) * 100 + int(bm) * 7), N_ITEM, bm, pg)
                           for r in range(20)], ignore_index=True)
            fd = d[flag(d)]
            sens.append({"p_grow": pg, "base_median": bm, "flag_per_2000": round(len(fd) / 20, 2),
                         "flag_share_grower": round(float(fd.grower.mean()), 4),
                         "flag_share_y0_le3": round(float((fd.y0 <= 3).mean()), 4),
                         "grower_share_flagged": round(float(flag(d[d.grower == 1]).mean()), 4)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_grid.csv", index=False)

    fo = one[flag(one)]
    one_draw = {"flag_n": int(len(fo)), "flag_grower_n": int(fo.grower.sum()), "flag_y0_le3_n": int((fo.y0 <= 3).sum()),
                "grower_n": int(one.grower.sum()), "y0_zero_n": int((one.y0 == 0).sum()),
                "max_pct": float(np.nanmax(one.pct)), "max_pct_y0": int(one.loc[one.pct.idxmax(), "y0"]),
                "max_pct_y1": int(one.loc[one.pct.idxmax(), "y1"]),
                "max_pct_grower": int(one.loc[one.pct.idxmax(), "grower"])}

    out = {"flagged_300": main_, "by_base": by_base.to_dict("records"), "flat_item_swing": flat.to_dict("records"),
           "ranking_top20": rk.reset_index().to_dict("records"), "next_year": nxt,
           "sensitivity": {"rows": sens.to_dict("records"),
                           "flag_share_grower_min": float(sens.flag_share_grower.min()),
                           "flag_share_grower_max": float(sens.flag_share_grower.max()),
                           "flag_share_y0_le3_min": float(sens.flag_share_y0_le3.min()),
                           "flag_share_y0_le3_max": float(sens.flag_share_y0_le3.max()),
                           "grower_share_flagged_min": float(sens.grower_share_flagged.min()),
                           "grower_share_flagged_max": float(sens.grower_share_flagged.max())},
           "one_draw": one_draw}
    json.dump(out, open(RES / "a903_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：前年の個数と前年比（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    o = one[one.y0 > 0]
    jit = np.random.default_rng(1).uniform(-0.15, 0.15, len(o))
    x = o.y0 * np.exp(jit * 0.3)
    ax.scatter(x[o.grower == 0], o.pct[o.grower == 0], s=7, color=GRAY, alpha=.45, lw=0, label="ほかの品目（本当は横ばい前後）")
    ax.scatter(x[o.grower == 1], o.pct[o.grower == 1], s=12, color=ORANGE, alpha=.9, lw=0, label="伸びる品目（本当に約3倍）")
    ax.set_xscale("log"); ax.set_yscale("symlog", linthresh=100)
    ax.axhline(300, color=BLUE, lw=1, ls="--"); ax.text(1300, 215, "+300%", color=BLUE, fontsize=9)
    ax.set_xlabel("前年の販売個数（対数の目盛り）"); ax.set_ylabel("前年比（%、+100%から上は対数の目盛り）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("前年が数個の品目では、横ばいの品目も+300%を超える（2,000品目・1回分）")
    save(fig, "a903_scatter.png", SRC)

    # 図2：前年の個数ごとの「+300%以上」のうち伸びる品目の割合
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bb = by_base.dropna(subset=["flag_share_grower"])
    ax.bar(bb.y0_bucket, bb.flag_share_grower * 100, color=[GRAY, GRAY, LIGHT, BLUE, BLUE][:len(bb)])
    for i, (v, n) in enumerate(zip(bb.flag_share_grower * 100, bb.flag_per_rep)):
        ax.text(i, v + 2, f"{v:.0f}%\n（{n:.1f}品目）", ha="center", fontsize=8.5)
    ax.set_ylim(0, 118); ax.set_ylabel("+300%以上のうち、伸びる品目の割合（%）")
    ax.set_xlabel("前年の販売個数（かっこは2,000品目あたりの+300%以上の品目数、50回の平均）")
    ax.set_title("前年が少ない品目の「+300%」ほど、本当の伸びではない")
    save(fig, "a903_by_base.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = 0.26
    for k, (bm, col) in enumerate([(5.0, LIGHT), (20.0, BLUE), (80.0, INK)]):
        s = sens[sens.base_median == bm]
        xs = np.arange(3) + (k - 1) * w
        ax.bar(xs, s.flag_share_grower * 100, w, color=col, label=f"前年の速さの中央値 {bm:.0f}個")
        for xx, v in zip(xs, s.flag_share_grower * 100):
            ax.text(xx, v + 1.5, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(np.arange(3)); ax.set_xticklabels(["伸びる品目 1%", "5%（基本）", "10%"])
    ax.set_ylabel("+300%以上のうち、伸びる品目の割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("当たりの割合は、置き方（伸びる品目の多さ・前年の個数）で動く")
    save(fig, "a903_sensitivity.png", SRC)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
