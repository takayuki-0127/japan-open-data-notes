"""1080 知り合いをたどって集めた人は、全体を表しているのか？（架空のデータ）

架空の会員制の会（会員2,000人）。会員のうち「集まりによく来る人」は25%（作成者が置いた正しい答え）。
よく来る人はつながり（知り合い）が多く、よく来る人どうしがつながりやすいと置く。
最初の10人から、1人3枚の紹介券で知り合いをたどって300人を集め（雪だるま式の集め方）、
集めた人の中の「よく来る人」の割合を、そのまま数えた値・つながりの数の逆数で重みを付けた値・
会員から無作為に選んだ300人の値と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1080
SRC = "架空の会員制の会（作成者が乱数で作成、seed 1080）"
N = 2000            # 会員の数
ACTIVE = 500        # よく来る人の数（25%）
MEAN_DEG = 8.0      # つながりの数の平均（ねらい）
SIG_W = 0.5         # つながりやすさの人ごとの振れ（対数の標準偏差）
R_BASE = 2.0        # よく来る人のつながりやすさの倍率
H_BASE = 2.0        # 同じ組（よく来る人どうし・そうでない人どうし）のつながりやすさの倍率
N_SEED = 10         # 最初に頼む人数
COUPON = 3          # 1人が渡す紹介券
ACCEPT = 0.7        # 紹介された人が答える確率
TARGET = 300        # 集める人数
REPS = 200          # 基本の繰り返し
GRID_REPS = 30      # 確かめの繰り返し
MAXW = 5            # 図に描く段の上限


def make_network(rng, r=R_BASE, h=H_BASE):
    """会員の組と、つながり（隣の人の並び）を作る。
    つながりは MEAN_DEG×N/2 本を、2人のつながりやすさの積（同じ組なら h 倍）に比例する確率で引く。
    同じ2人の重なりと、自分自身へのつながりは除く。"""
    active = np.zeros(N, bool)
    active[rng.choice(N, ACTIVE, replace=False)] = True
    w = np.exp(rng.normal(0, SIG_W, N)) * np.where(active, r, 1.0)
    ia, ib = np.flatnonzero(active), np.flatnonzero(~active)
    sa, sb = w[ia].sum(), w[ib].sum()
    blocks = [(ia, ia, h * sa * sa / 2), (ib, ib, h * sb * sb / 2), (ia, ib, sa * sb)]
    tot = sum(b[2] for b in blocks)
    m = rng.multinomial(int(MEAN_DEG * N / 2), [b[2] / tot for b in blocks])
    ii, jj = [], []
    for (g1, g2, _), k in zip(blocks, m):
        ii.append(rng.choice(g1, k, p=w[g1] / w[g1].sum()))
        jj.append(rng.choice(g2, k, p=w[g2] / w[g2].sum()))
    i, j = np.concatenate(ii), np.concatenate(jj)
    lo, hi = np.minimum(i, j), np.maximum(i, j)
    keep = lo != hi
    code = np.unique(lo[keep] * N + hi[keep])
    i, j = code // N, code % N
    src = np.concatenate([i, j]); dst = np.concatenate([j, i])
    o = np.argsort(src, kind="stable")
    deg = np.bincount(src, minlength=N)
    nbr = np.split(dst[o], np.cumsum(deg)[:-1])
    return active, nbr, deg, (i, j)


def snowball(rng, active, nbr, deg, seed_rule="active", coupon=COUPON):
    """紹介券で知り合いをたどる。返り値：集めた人・段（0＝最初の人）・紹介した人"""
    invited = np.zeros(N, bool)
    order, wave, parent = [], [], []
    queue = []

    def new_seed():
        pool = np.flatnonzero((~invited) & (deg > 0) & (active if seed_rule == "active" else True))
        if pool.size == 0:
            pool = np.flatnonzero((~invited) & (deg > 0))
        s = rng.choice(pool)
        invited[s] = True
        order.append(s); wave.append(0); parent.append(-1); queue.append(s)

    for _ in range(N_SEED):
        new_seed()
    qi = 0
    while len(order) < TARGET:
        if qi >= len(queue):
            new_seed(); continue
        u = queue[qi]; qi += 1
        cand = nbr[u][~invited[nbr[u]]]
        if cand.size == 0:
            continue
        give = rng.choice(cand, min(coupon, cand.size), replace=False)
        wu = wave[order.index(u)] if u in order else 0
        for v in give:
            invited[v] = True
            if rng.random() < ACCEPT and len(order) < TARGET:
                order.append(v); wave.append(wu + 1); parent.append(u); queue.append(v)
    return np.array(order), np.array(wave), np.array(parent)


def estimates(rng, active, deg, order, report_sig=0.0):
    d = deg[order].astype(float)
    if report_sig > 0:
        d = np.maximum(1, np.round(d * np.exp(rng.normal(0, report_sig, d.size))))
    a = active[order]
    raw = a.mean()
    wt = (a / d).sum() / (1 / d).sum()
    rnd = active[rng.choice(N, TARGET, replace=False)].mean()
    return raw, wt, rnd


def one_run(rng, r=R_BASE, h=H_BASE, seed_rule="active", report_sig=0.0, keep=False, coupon=COUPON):
    active, nbr, deg, edges = make_network(rng, r, h)
    order, wave, parent = snowball(rng, active, nbr, deg, seed_rule, coupon)
    raw, wt, rnd = estimates(rng, active, deg, order, report_sig)
    out = dict(raw=raw, wt=wt, rnd=rnd,
               deg_share=(deg * active).sum() / deg.sum(),
               mean_deg_true=deg.mean(), mean_deg_sample=deg[order].mean(),
               max_wave=wave.max(), n_seed=(wave == 0).sum(),
               share_by_wave=[active[order[wave == k]].mean() if (wave == k).any() else np.nan
                              for k in range(MAXW + 1)],
               n_by_wave=[(wave == k).sum() for k in range(MAXW + 1)])
    if keep:
        out["_net"] = (active, nbr, deg, edges, order, wave, parent)
    return out


def summarize(runs, key):
    v = np.array([r[key] for r in runs]) * 100
    return dict(mean=round(v.mean(), 2), p10=round(np.percentile(v, 10), 2), p90=round(np.percentile(v, 90), 2))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res = {"true_active_pct": ACTIVE / N * 100, "N": N, "target": TARGET, "reps": REPS,
           "params": {"mean_deg_target": MEAN_DEG, "sig_w": SIG_W, "r": R_BASE, "h": H_BASE, "n_seed": N_SEED,
                      "coupon": COUPON, "accept": ACCEPT, "grid_reps": GRID_REPS}}

    # 基本：最初の10人を集まりに来た人（よく来る人）から選ぶ／会員から無作為に選ぶ
    base = {}
    rows = []
    for rule, lab in [("active", "最初の10人＝よく来る人"), ("random", "最初の10人＝会員から無作為")]:
        runs = [one_run(rng, seed_rule=rule) for _ in range(REPS)]
        base[rule] = runs
        sw = np.nanmean(np.array([r["share_by_wave"] for r in runs]), 0) * 100
        nw = np.mean(np.array([r["n_by_wave"] for r in runs]), 0)
        res[f"base_{rule}"] = {
            "label": lab,
            "random300_pct": summarize(runs, "rnd"),
            "snowball_raw_pct": summarize(runs, "raw"),
            "snowball_weighted_pct": summarize(runs, "wt"),
            "degree_weighted_share_pct": summarize(runs, "deg_share"),
            "mean_degree_true": round(float(np.mean([r["mean_deg_true"] for r in runs])), 2),
            "mean_degree_sample": round(float(np.mean([r["mean_deg_sample"] for r in runs])), 2),
            "raw_minus_true_pt": round(summarize(runs, "raw")["mean"] - ACTIVE / N * 100, 2),
            "weighted_minus_true_pt": round(summarize(runs, "wt")["mean"] - ACTIVE / N * 100, 2),
            "max_wave_median": float(np.median([r["max_wave"] for r in runs])),
            "share_by_wave_pct": [round(x, 2) for x in sw],
            "n_by_wave": [round(x, 2) for x in nw],
        }
        for m, k in [("無作為の300人", "rnd"), ("たどった300人（そのまま）", "raw"),
                     ("たどった300人（つながりの数で重み）", "wt")]:
            s = summarize(runs, k)
            rows.append(dict(seed_rule=lab, method=m, mean_pct=s["mean"], p10_pct=s["p10"], p90_pct=s["p90"]))
    pd.DataFrame(rows).to_csv(RES / "base_estimates.csv", index=False)
    wv = []
    for rule in ["active", "random"]:
        b = res[f"base_{rule}"]
        for k in range(MAXW + 1):
            wv.append(dict(seed_rule=b["label"], wave=k, share_active_pct=b["share_by_wave_pct"][k],
                           n_mean=b["n_by_wave"][k]))
    pd.DataFrame(wv).to_csv(RES / "share_by_wave.csv", index=False)

    # 答えたつながりの数がずれるとき（基本の置き方、最初の10人＝よく来る人）
    rep = []
    for sig in [0.0, 0.3, 0.6]:
        runs = [one_run(rng, seed_rule="active", report_sig=sig) for _ in range(80)]
        s = summarize(runs, "wt")
        rep.append(dict(report_sig=sig, weighted_mean_pct=s["mean"], p10_pct=s["p10"], p90_pct=s["p90"]))
    res["report_noise"] = rep
    pd.DataFrame(rep).to_csv(RES / "report_noise.csv", index=False)

    # 紹介券の枚数（最初の10人＝よく来る人）
    cp = []
    for c in [2, 3, 5]:
        runs = [one_run(rng, seed_rule="active", coupon=c) for _ in range(80)]
        cp.append(dict(coupon=c, raw_pct=summarize(runs, "raw")["mean"], weighted_pct=summarize(runs, "wt")["mean"],
                       n_seed_mean=round(float(np.mean([x["n_seed"] for x in runs])), 2),
                       max_wave_median=float(np.median([x["max_wave"] for x in runs]))))
    res["coupon"] = cp
    pd.DataFrame(cp).to_csv(RES / "coupon.csv", index=False)

    # 確かめ：つながりやすさの倍率 r × 同じ組どうしの倍率 h × 最初の10人の選び方（18通り）
    grid = []
    for r in [1.0, 2.0, 3.0]:
        for h in [1.0, 2.0, 4.0]:
            for rule in ["active", "random"]:
                runs = [one_run(rng, r=r, h=h, seed_rule=rule) for _ in range(GRID_REPS)]
                grid.append(dict(r=r, h=h, seed_rule=rule,
                                 raw_pct=round(np.mean([x["raw"] for x in runs]) * 100, 2),
                                 weighted_pct=round(np.mean([x["wt"] for x in runs]) * 100, 2),
                                 random300_pct=round(np.mean([x["rnd"] for x in runs]) * 100, 2),
                                 degree_weighted_share_pct=round(np.mean([x["deg_share"] for x in runs]) * 100, 2)))
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid_r_h_seed.csv", index=False)
    g["raw_bias"] = g.raw_pct - 25; g["wt_bias"] = g.weighted_pct - 25
    res["grid"] = {
        "n": len(g),
        "raw_bias_min": round(g.raw_bias.min(), 2), "raw_bias_max": round(g.raw_bias.max(), 2),
        "wt_bias_min": round(g.wt_bias.min(), 2), "wt_bias_max": round(g.wt_bias.max(), 2),
        "raw_min": round(g.raw_pct.min(), 2), "raw_max": round(g.raw_pct.max(), 2),
        "wt_min": round(g.weighted_pct.min(), 2), "wt_max": round(g.weighted_pct.max(), 2),
        "r1_h1_degree_weighted_share": [round(g[(g.r == 1) & (g.h == 1)].degree_weighted_share_pct.min(), 2), round(g[(g.r == 1) & (g.h == 1)].degree_weighted_share_pct.max(), 2)],
        "raw_min_case": g.loc[g.raw_pct.idxmin(), ["r", "h", "seed_rule", "raw_pct"]].to_dict(),
        "n_wt_closer": int((g.wt_bias.abs() < g.raw_bias.abs()).sum()),
        "n_wt_within2": int((g.wt_bias.abs() <= 2).sum()),
        "r1_h1_raw_range": [round(g[(g.r == 1) & (g.h == 1)].raw_pct.min(), 2), round(g[(g.r == 1) & (g.h == 1)].raw_pct.max(), 2)],
        "wt_bias_max_case": g.loc[g.wt_bias.abs().idxmax(), ["r", "h", "seed_rule", "weighted_pct"]].to_dict(),
        "random_seed_wt_bias_range": [round(g[g.seed_rule == "random"].wt_bias.min(), 2), round(g[g.seed_rule == "random"].wt_bias.max(), 2)],
        "active_seed_wt_bias_range": [round(g[g.seed_rule == "active"].wt_bias.min(), 2), round(g[g.seed_rule == "active"].wt_bias.max(), 2)],
    }

    # 例の1回（データとして置く）
    ex = one_run(np.random.default_rng(SEED + 1), keep=True)
    active, nbr, deg, (ei, ej), order, wave, parent = ex["_net"]
    pd.DataFrame(dict(member_id=np.arange(N) + 1, frequent=active.astype(int), degree=deg)).to_csv(
        DATA / "members_example.csv", index=False)
    pd.DataFrame(dict(member_a=ei + 1, member_b=ej + 1)).to_csv(DATA / "links_example.csv", index=False)
    pd.DataFrame(dict(step=np.arange(len(order)) + 1, member_id=order + 1, wave=wave,
                      invited_by=np.where(parent >= 0, parent + 1, 0),
                      frequent=active[order].astype(int), degree=deg[order])).to_csv(
        DATA / "sample_example.csv", index=False)
    res["example"] = {k: (round(float(ex[k]) * 100, 2) if k in ("raw", "wt", "rnd", "deg_share") else ex[k])
                      for k in ("raw", "wt", "rnd", "deg_share")}
    res["example"]["n_links"] = int(len(ei))

    # 図1：段ごとの「よく来る人」の割合
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ks = np.arange(MAXW + 1)
    for rule, col in [("active", ORANGE), ("random", BLUE)]:
        b = res[f"base_{rule}"]
        ax.plot(ks, b["share_by_wave_pct"], "o-", color=col, label=b["label"])
    ax.axhline(25, color=INK, lw=1, ls="--")
    ax.text(0.6, 23.5, "会員全体 25%", ha="left", va="top", fontsize=9, color=INK)
    dws = res["base_active"]["degree_weighted_share_pct"]["mean"]
    ax.axhline(dws, color=GRAY, lw=1, ls=":")
    ax.text(5.15, dws + 3.5, f"つながりの数で重みを付けた会員全体の割合 {dws}%", ha="right", va="bottom", fontsize=9, color=GRAY)
    ax.set_xlabel("段（0＝最初に頼んだ10人、1＝その人が紹介した人、…）")
    ax.set_ylabel("「よく来る人」の割合（%）"); ax.set_ylim(0, 105); ax.set_xticks(ks)
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1, 0.85))
    ax.set_title("たどるほど最初の人の影響は薄れるが、全体の25%には下りてこない")
    save(fig, "a1080_by_wave.png", SRC + f"。{REPS}回の平均", y=-0.04)

    # 図2：集め方ごとの推定（0始まり）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    est = pd.DataFrame(rows)
    labs, vals, lo, hi, cols = [], [], [], [], []
    for rule_lab in est.seed_rule.unique():
        for m, col in [("無作為の300人", GRAY), ("たどった300人（そのまま）", ORANGE),
                       ("たどった300人（つながりの数で重み）", BLUE)]:
            if m == "無作為の300人" and rule_lab != est.seed_rule.unique()[0]:
                continue
            r_ = est[(est.seed_rule == rule_lab) & (est.method == m)].iloc[0]
            labs.append(m if m == "無作為の300人" else f"{m}\n{rule_lab}")
            vals.append(r_.mean_pct); lo.append(r_.p10_pct); hi.append(r_.p90_pct); cols.append(col)
    y = np.arange(len(labs))[::-1]
    ax.barh(y, vals, color=cols, height=0.6)
    ax.errorbar(vals, y, xerr=[np.array(vals) - lo, np.array(hi) - vals], fmt="none", ecolor=INK, lw=1, capsize=3)
    for yy, v, h_ in zip(y, vals, hi):
        ax.text(h_ + 1.5, yy, f"{v}%", fontsize=9, va="center")
    ax.axvline(25, color=INK, lw=1, ls="--")
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8.5)
    ax.set_xlim(0, 100); ax.set_xlabel("「よく来る人」の割合の推定（%）。線は10〜90%の範囲")
    ax.set_title("そのまま数えると大きく出る。重みで近づくが、最初の人の選び方が残る")
    save(fig, "a1080_estimates.png", SRC + f"。{REPS}回。点線は会員全体の25%", y=-0.03)

    # 図3：確かめ（18通り）
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    g2 = g.copy()
    g2["lab"] = [f"r={a:g}・h={b:g}・{'よく来る人から' if c == 'active' else '無作為から'}"
                 for a, b, c in zip(g2.r, g2.h, g2.seed_rule)]
    y = np.arange(len(g2))[::-1]
    ax.scatter(g2.raw_pct, y, color=ORANGE, s=22, label="そのまま", zorder=3)
    ax.scatter(g2.weighted_pct, y, color=BLUE, s=22, marker="s", label="つながりの数で重み", zorder=3)
    ax.axvline(25, color=INK, lw=1, ls="--")
    ax.set_yticks(y); ax.set_yticklabels(g2.lab, fontsize=7.5)
    ax.set_xlim(0, 100); ax.set_xlabel("「よく来る人」の割合の推定（%、各30回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("置き方18通り（r：よく来る人のつながりやすさの倍率、h：同じ組どうしの倍率）", fontsize=11)
    save(fig, "a1080_robust.png", SRC + "。点線は会員全体の25%", y=-0.02)

    with open(RES / "a1080_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(res, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
