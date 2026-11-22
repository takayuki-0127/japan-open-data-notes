"""906 割合の差と割合の比、どちらで比べると順位が変わるのか？（架空のデータ）

架空の会社の店40店。店ごとに「前の月の購入率」（来店者のうち買った人の割合）と来店者数を置き、
施策のあとの購入率を、足し算型（どの店も何ポイントか上がる）か掛け算型（どの店も何倍かになる）で置く。
来店者のうち買う人は二項分布で引き、見かけの購入率の「差（ポイント）」と「比（倍）」で店を並べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 906
SRC = "架空の会社の店と購入率（作成者が乱数で作成、seed 906）"
N_STORE = 40
K = 5          # 上位何店を見るか
REPS = 1000


def make_stores(rng, reps, lo=0.02, hi=0.30, nscale=1.0, model="add"):
    """reps × 40店。前の購入率 p0 は lo〜hi（対数で一様）。来店者は 500〜5,000人（対数で一様）×nscale"""
    shape = (reps, N_STORE)
    if lo == hi:
        p0 = np.full(shape, lo)
    else:
        p0 = np.exp(rng.uniform(np.log(lo), np.log(hi), shape))
    n = np.round(np.exp(rng.uniform(np.log(500), np.log(5000), shape)) * (nscale if np.isfinite(nscale) else 1)).astype(int)
    if model == "add":
        eff = rng.normal(0.02, 0.01, shape)          # +2ポイント前後（標準偏差1ポイント）
        p1 = p0 + eff
    else:
        eff = np.exp(rng.normal(np.log(1.2), 0.1, shape))   # 1.2倍前後（対数で標準偏差0.1）
        p1 = p0 * eff
    p1 = np.clip(p1, 0.001, 0.99)
    if np.isfinite(nscale):
        x0 = rng.binomial(n, p0); x1 = rng.binomial(n, p1)
        r0 = x0 / n; r1 = x1 / n
    else:   # 来店者が限りなく多い＝見かけ＝本当
        r0, r1 = p0.copy(), p1.copy()
    return p0, p1, n, r0, r1, eff


def topk(score, k=K):
    return np.argsort(-score, axis=1, kind="stable")[:, :k]


def overlap(a, b):
    return np.array([len(set(x) & set(y)) for x, y in zip(a, b)])


def spearman(a, b):
    ra = np.argsort(np.argsort(a, axis=1), axis=1).astype(float)
    rb = np.argsort(np.argsort(b, axis=1), axis=1).astype(float)
    ra -= ra.mean(1, keepdims=True); rb -= rb.mean(1, keepdims=True)
    return (ra * rb).sum(1) / np.sqrt((ra ** 2).sum(1) * (rb ** 2).sum(1))


def evaluate(rng, reps, **kw):
    p0, p1, n, r0, r1, eff = make_stores(rng, reps, **kw)
    d = r1 - r0
    with np.errstate(divide="ignore", invalid="ignore"):
        rt = np.where(r0 > 0, r1 / np.where(r0 > 0, r0, 1), np.inf)
    td, tr = topk(d), topk(rt)
    true_d, true_r = p1 - p0, p1 / p0
    out = {
        "top5_overlap": float(overlap(td, tr).mean()),
        "top1_same": float((td[:, 0] == tr[:, 0]).mean()),
        "zero_before_share": float((r0 == 0).mean()),
        "spearman": float(np.nanmean(spearman(d, np.where(np.isfinite(rt), rt, 1e9)))),
        "top5_base_median_diff": float(np.median(np.take_along_axis(p0, td, 1)) * 100),
        "top5_base_median_ratio": float(np.median(np.take_along_axis(p0, tr, 1)) * 100),
        # 本当の上位5店（本当の差で並べた／本当の比で並べた）に入っていた数
        "hit_truediff_by_diff": float(overlap(td, topk(true_d)).mean()),
        "hit_truediff_by_ratio": float(overlap(tr, topk(true_d)).mean()),
        "hit_trueratio_by_diff": float(overlap(td, topk(true_r)).mean()),
        "hit_trueratio_by_ratio": float(overlap(tr, topk(true_r)).mean()),
    }
    return {k: round(v, 3) for k, v in out.items()}


def main():
    rng = np.random.default_rng(SEED)

    # 0) 1回分の40店（足し算型）を data に
    p0, p1, n, r0, r1, eff = make_stores(rng, 1, model="add")
    one = pd.DataFrame({"store_id": np.arange(1, N_STORE + 1), "visitors": n[0],
                        "true_before": p0[0], "true_after": p1[0],
                        "buy_before": np.round(r0[0] * n[0]).astype(int), "buy_after": np.round(r1[0] * n[0]).astype(int)})
    one["rate_before"] = one.buy_before / one.visitors
    one["rate_after"] = one.buy_after / one.visitors
    one["diff_pt"] = (one.rate_after - one.rate_before) * 100
    one["ratio"] = one.rate_after / one.rate_before
    one["rank_diff"] = one.diff_pt.rank(ascending=False, method="first").astype(int)
    one["rank_ratio"] = one.ratio.rank(ascending=False, method="first").astype(int)
    one.to_csv(DATA / "stores_one_draw.csv", index=False, float_format="%.4f")
    top_d = set(one.nsmallest(K, "rank_diff").store_id); top_r = set(one.nsmallest(K, "rank_ratio").store_id)
    one_res = {"top5_overlap": len(top_d & top_r),
               "top1_diff_store": int(one.loc[one.rank_diff == 1, "store_id"].iloc[0]),
               "top1_ratio_store": int(one.loc[one.rank_ratio == 1, "store_id"].iloc[0]),
               "max_abs_rank_change": int((one.rank_diff - one.rank_ratio).abs().max()),
               "median_abs_rank_change": float((one.rank_diff - one.rank_ratio).abs().median())}
    for lab, col in [("top1_diff", "rank_diff"), ("top1_ratio", "rank_ratio")]:
        r = one.loc[one[col] == 1].iloc[0]
        one_res[lab] = {"before_pct": round(r.rate_before * 100, 1), "after_pct": round(r.rate_after * 100, 1),
                        "diff_pt": round(r.diff_pt, 1), "ratio": round(r.ratio, 2),
                        "rank_other": int(r.rank_ratio if col == "rank_diff" else r.rank_diff)}

    # 1) 基本の置き方（前の購入率2〜30%、来店者500〜5,000人）で、足し算型・掛け算型
    base = {}
    for model in ["add", "mul"]:
        base[model] = {"noisy": evaluate(np.random.default_rng(SEED * 10 + (model == "mul")), REPS, model=model),
                       "no_noise": evaluate(np.random.default_rng(SEED * 20 + (model == "mul")), REPS, model=model,
                                            nscale=np.inf)}

    # 2) 確かめ：前の購入率の幅 × 来店者の多さ × 型
    ranges = [("10%でそろう", 0.10, 0.10), ("8〜12%", 0.08, 0.12), ("5〜20%", 0.05, 0.20),
              ("2〜30%（基本）", 0.02, 0.30), ("1〜50%", 0.01, 0.50)]
    nscales = [("0.2倍", 0.2), ("1倍（基本）", 1.0), ("5倍", 5.0), ("限りなく多い", np.inf)]
    rows = []
    for mi, model in enumerate(["add", "mul"]):
        for ri, (rl, lo, hi) in enumerate(ranges):
            for ni, (nl, ns) in enumerate(nscales):
                ev = evaluate(np.random.default_rng(SEED * 1000 + mi * 100 + ri * 10 + ni), 500,
                              lo=lo, hi=hi, nscale=ns, model=model)
                rows.append({"model": "足し算型" if model == "add" else "掛け算型", "base_range": rl,
                             "visitors": nl, **ev})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    g_noisy = grid[grid.visitors != "限りなく多い"]
    rng_sum = {"top5_overlap_min": float(grid.top5_overlap.min()), "top5_overlap_max": float(grid.top5_overlap.max()),
               "top1_same_min": float(grid.top1_same.min()), "top1_same_max": float(grid.top1_same.max())}
    by_range = grid.groupby("base_range", sort=False)[["top5_overlap", "top1_same"]].agg(["min", "max"]).round(3)
    by_range.columns = [f"{a}_{b}" for a, b in by_range.columns]
    # 本当の物差しと同じ並べ方が勝つか
    grid["diff_wins_on_truediff"] = grid.hit_truediff_by_diff > grid.hit_truediff_by_ratio
    grid["ratio_wins_on_trueratio"] = grid.hit_trueratio_by_ratio > grid.hit_trueratio_by_diff
    wins = {"cases": int(len(grid)),
            "diff_beats_ratio_on_true_diff": int(grid.diff_wins_on_truediff.sum()),
            "ratio_beats_diff_on_true_ratio": int(grid.ratio_wins_on_trueratio.sum()),
            "ratio_beats_diff_on_true_ratio_noisy_only": int(g_noisy.eval("hit_trueratio_by_ratio > hit_trueratio_by_diff").sum()),
            "noisy_cases": int(len(g_noisy)),
            "noisy_cases_diff_ge_ratio_on_true_ratio": g_noisy.loc[g_noisy.eval("hit_trueratio_by_diff >= hit_trueratio_by_ratio"),
                                                                 ["model", "base_range", "visitors"]].to_dict("records")}
    # 掛け算型・来店者0.2倍（雑音が大きい）での比の当たり
    sub = grid[(grid.model == "掛け算型") & (grid.base_range == "2〜30%（基本）")].set_index("visitors")
    mul_by_n = sub[["hit_trueratio_by_diff", "hit_trueratio_by_ratio", "top5_base_median_ratio"]].to_dict("index")

    # 式の例：比＝1＋差÷前の率
    formula = {f"before{b}_plus{d}pt": {"after_pct": b + d, "ratio": round((b + d) / b, 2)} for b, d in [(10, 2), (2, 3), (20, 3)]}
    out = {"formula_ratio_eq_1_plus_diff_over_before": formula, "one_draw_add": one_res, "base_1000reps": base, "sensitivity_range": rng_sum,
           "sensitivity_by_base_range": by_range.reset_index().to_dict("records"),
           "which_wins": wins, "mul_base_range_by_visitors": mul_by_n}
    json.dump(out, open(RES / "a906_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tbl = []
    for model, lab in [("add", "足し算型"), ("mul", "掛け算型")]:
        for nz, nl in [("noisy", "来店者500〜5,000人"), ("no_noise", "来店者が限りなく多い")]:
            tbl.append({"model": lab, "visitors": nl, **base[model][nz]})
    pd.DataFrame(tbl).to_csv(RES / "base_summary.csv", index=False)

    # 図1：1回分の40店。差（ポイント）と比（倍）、色は前の購入率
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    sc = ax.scatter(one.diff_pt, one.ratio, c=one.rate_before * 100, cmap="Blues", s=34, edgecolor=INK, lw=.4,
                    vmin=0, vmax=32)
    dd = one[one.store_id.isin(top_d)]; rr = one[one.store_id.isin(top_r)]
    ax.scatter(dd.diff_pt, dd.ratio, s=120, facecolor="none", edgecolor=BLUE, lw=1.6, label="差（ポイント）で上位5店")
    ax.scatter(rr.diff_pt, rr.ratio, s=120, facecolor="none", edgecolor=ORANGE, lw=1.6, label="比（倍）で上位5店")
    for k, (_, r) in enumerate(dd.sort_values("diff_pt").iterrows()):
        ax.annotate(f"前{r.rate_before*100:.1f}%", (r.diff_pt, r.ratio), xytext=(0, -14) if k != 3 else (26, 0),
                    textcoords="offset points", fontsize=7.5, color=BLUE, ha="center", va="center")
    for _, r in rr.iterrows():
        ax.annotate(f"前{r.rate_before*100:.1f}%", (r.diff_pt, r.ratio), xytext=(-9, 0), textcoords="offset points",
                    fontsize=7.5, color=ORANGE, ha="right", va="center")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    cb = fig.colorbar(sc, ax=ax, pad=0.02); cb.set_label("前の月の見かけの購入率（%）")
    ax.set_xlabel("購入率の差（ポイント）"); ax.set_ylabel("購入率の比（後÷前、倍）")
    ax.set_title(f"同じ40店でも、差の上位5店と比の上位5店で重なったのは{one_res['top5_overlap']}店（足し算型の1回分）")
    save(fig, "a906_scatter_one.png", SRC)

    # 図2：前の購入率の幅ごとの、上位5店の重なり（来店者1倍、足し算型・掛け算型）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    s = grid[grid.visitors == "1倍（基本）"]
    x = np.arange(len(ranges)); w = 0.38
    for j, (lab, col) in enumerate([("足し算型", BLUE), ("掛け算型", ORANGE)]):
        v = s[s.model == lab].top5_overlap.values
        ax.bar(x + (j - .5) * w, v, w, color=col, label=lab)
        for xi, vi in zip(x, v):
            ax.text(xi + (j - .5) * w, vi + .06, f"{vi:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(x, [r[0] for r in ranges]); ax.set_ylim(0, 5.6)
    ax.set_xlabel("40店の前の月の購入率の幅"); ax.set_ylabel("差と比の上位5店の重なり（店、500回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("前の購入率が店で違うほど、差と比の上位は入れかわる（来店者500〜5,000人）")
    save(fig, "a906_overlap_by_range.png", SRC)

    # 図3：本当の上位5店に何店入るか（基本の置き方）
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.6), sharey=True)
    for ax, (key, lab) in zip(axes, [("truediff", "本当の「差」の上位5店"), ("trueratio", "本当の「比」の上位5店")]):
        vals = []; labs = []
        for model, ml in [("add", "足し算型"), ("mul", "掛け算型")]:
            for meth, mlab in [("diff", "差で並べる"), ("ratio", "比で並べる")]:
                vals.append(base[model]["noisy"][f"hit_{key}_by_{meth}"]); labs.append(f"{ml}\n{mlab}")
        cols = [BLUE, LIGHT, ORANGE, "#f5b899"]
        ax.bar(range(4), vals, color=cols)
        for i, v in enumerate(vals):
            ax.text(i, v + .06, f"{v:.1f}", ha="center", fontsize=8.5)
        ax.set_xticks(range(4), labs, fontsize=8); ax.set_title(lab, fontsize=11); ax.set_ylim(0, 5.4)
    axes[0].set_ylabel("当たった店（5店のうち、1,000回の平均）")
    fig.suptitle("どちらの並べ方が当たるかは、何を「本当の効き目」と決めるかで決まる", fontsize=12, y=1.02)
    save(fig, "a906_hit_by_truth.png", SRC, y=-0.04)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
