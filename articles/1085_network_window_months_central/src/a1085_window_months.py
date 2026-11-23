"""1085 何か月分の記録でつながりを数えるかで、顔ぶれはどう変わるのか？（架空のデータ）

架空の会社200社どうしの取引を、作成者が置いた「取引の始まりやすさ・続く長さ・取引の多さ」から乱数で作る。
「今の取引先の数」（24か月目の終わりに続いている取引の相手の数）を正しい答えとして置き、
直近 W か月に1回でも取引のあった相手を数えたとき、取引先の数と「取引先の多い上位10社」の顔ぶれがどうずれるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1085
SRC = "架空の会社どうしの取引（作成者が置いた始まりやすさ・長さ・多さからの乱数、seed 1085）"
N = 200
MONTHS = 24
WS = [1, 2, 3, 6, 12, 24]
BASE = {"birth": 0.4, "dur_median": 18.0, "rate_median": 0.5, "rate_sigma": 1.0}
REPS = 200
GRID_DUR = [6.0, 18.0, 48.0]
GRID_SIG = [0.5, 1.0, 1.5]
GRID_REPS = 50
TOP = 10
BURN = 150
SIG_A, SIG_D, SIG_PAIR = 0.6, 0.7, 0.5


def r(x, d=4):
    return round(float(x), d)


def simulate(rng, birth, dur_median, rate_median, rate_sigma, keep=False):
    """会社 i は月あたり birth×a_i 件の取引を始め、相手 j は a_j に比例して選ぶ。
    続く長さは指数分布（平均は2社の置いた長さの平均）、取引の多さ λ は月あたりのポアソン回数。"""
    a = rng.lognormal(0, SIG_A, N)
    a = a / a.mean()
    dcomp = dur_median * rng.lognormal(0, SIG_D, N)
    rcomp = rate_median * rng.lognormal(0, rate_sigma, N)
    nb = rng.poisson(birth * a * (BURN + MONTHS))
    src = np.repeat(np.arange(N), nb)
    dst = rng.choice(N, size=len(src), p=a / a.sum())
    ok = src != dst
    src, dst = src[ok], dst[ok]
    start = rng.uniform(-BURN, MONTHS, len(src))
    dur = rng.exponential((dcomp[src] + dcomp[dst]) / 2)
    end = start + dur
    lam = np.sqrt(rcomp[src] * rcomp[dst]) * rng.lognormal(0, SIG_PAIR, len(src))
    live = end > 0
    src, dst, start, end, lam = src[live], dst[live], start[live], end[live], lam[live]
    # 月ごとに続いていた長さ（0〜1か月）×λ のポアソン回数
    m0 = np.arange(MONTHS)[None, :]
    ov = np.clip(np.minimum(end[:, None], m0 + 1) - np.maximum(start[:, None], m0), 0, 1)
    cnt = rng.poisson(lam[:, None] * ov)
    active_now = end > MONTHS
    lo, hi = np.minimum(src, dst), np.maximum(src, dst)
    pair = lo * N + hi
    out = {"pair": pair, "lo": lo, "hi": hi, "cnt": cnt, "active_now": active_now, "lam": lam, "ov": ov,
           "rcomp": rcomp, "dcomp": dcomp, "a": a}
    return out


def partners(pair_ids):
    u = np.unique(pair_ids)
    lo, hi = u // N, u % N
    return np.bincount(lo, minlength=N) + np.bincount(hi, minlength=N), u


def measure(sim, key):
    pair, cnt, act = sim["pair"], sim["cnt"], sim["active_now"]
    true_deg, true_pairs = partners(pair[act])
    order_true = np.lexsort((key, -true_deg))
    top_true = set(order_true[:TOP])
    best_mean = true_deg[order_true[:TOP]].mean()
    rows = []
    tops = {}
    for w in WS:
        seen = cnt[:, MONTHS - w:].sum(1) > 0
        deg, seen_pairs = partners(pair[seen])
        ended = np.setdiff1d(seen_pairs, true_pairs)
        missed = np.setdiff1d(true_pairs, seen_pairs)
        order = np.lexsort((key, -deg))
        top = order[:TOP]
        tops[w] = set(top)
        rk = lambda v: pd.Series(v).rank().values
        rows.append({"W": w, "measured_total": len(seen_pairs), "true_total": len(true_pairs),
                     "ratio_total": len(seen_pairs) / len(true_pairs),
                     "ended_share_pct": 100 * len(ended) / max(len(seen_pairs), 1),
                     "missed_share_pct": 100 * len(missed) / len(true_pairs),
                     "spearman": float(np.corrcoef(rk(deg), rk(true_deg))[0, 1]),
                     "top10_overlap": len(top_true & set(top)),
                     "top10_true_mean": true_deg[top].mean(), "top10_best_mean": best_mean,
                     "top1_same": int(order[0] == order_true[0])})
    degs = {w: partners(pair[cnt[:, MONTHS - w:].sum(1) > 0])[0] for w in (1, 24)}
    return pd.DataFrame(rows), tops, true_deg, degs


def expected_counts(sim):
    """置いた λ と続いた長さからの式：直近 W か月に1回以上取引がある確率 1−exp(−λ×続いた長さ) の合計（相手の重なりは無視）"""
    out = {}
    for w in WS:
        p = 1 - np.exp(-(sim["lam"] * sim["ov"][:, MONTHS - w:].sum(1)))
        out[w] = p.sum()
    return out


def main():
    t0 = time.time()
    allrows, between = [], []
    formula_rows = []
    typ_rows = []
    for rep in range(REPS):
        rng = np.random.default_rng(SEED * 1000 + rep)
        sim = simulate(rng, **BASE)
        key = rng.random(N)
        df, tops, true_deg, degs = measure(sim, key)
        qr = pd.qcut(sim["rcomp"], 4, labels=False)
        qd = pd.qcut(sim["dcomp"], 4, labels=False)
        ok = true_deg > 0
        for w in (1, 24):
            rel_err = np.full(N, np.nan)
            rel_err[ok] = 100 * (degs[w][ok] / true_deg[ok] - 1)
            for q in range(4):
                typ_rows.append({"rep": rep, "W": w, "by": "rate", "quartile": q + 1,
                                 "rel_err_pct": np.nanmean(rel_err[qr == q])})
                typ_rows.append({"rep": rep, "W": w, "by": "duration", "quartile": q + 1,
                                 "rel_err_pct": np.nanmean(rel_err[qd == q])})
        df["rep"] = rep
        allrows.append(df)
        between.append({"rep": rep, "W3_vs_W24": len(tops[3] & tops[24]), "W1_vs_W12": len(tops[1] & tops[12]),
                        "W6_vs_W24": len(tops[6] & tops[24]), "W12_vs_W24": len(tops[12] & tops[24])})
        ex = expected_counts(sim)
        for w in WS:
            formula_rows.append({"rep": rep, "W": w, "formula_rel": ex[w],
                                 "sim_rel": int((sim["cnt"][:, MONTHS - w:].sum(1) > 0).sum())})
        if rep == 0:
            keep = (sim, key, true_deg)
    res = pd.concat(allrows, ignore_index=True)
    summ = res.groupby("W").mean(numeric_only=True).drop(columns="rep").reset_index()
    summ["top1_same"] *= 100
    summ = summ.rename(columns={"top1_same": "top1_same_pct"}).round(4)
    summ.to_csv(RES / "by_window.csv", index=False)
    rng_rows = res.groupby("W").top10_overlap.agg(["min", "max"]).reset_index()
    btw = pd.DataFrame(between).mean().drop("rep").round(3)
    fr = pd.DataFrame(formula_rows).groupby("W").mean().drop(columns="rep").reset_index().round(2)
    fr["diff_pct"] = (100 * (fr.sim_rel / fr.formula_rel - 1)).round(3)
    fr.to_csv(RES / "formula_check.csv", index=False)
    best_w = int(summ.loc[summ.top10_overlap.idxmax(), "W"])

    # 1回分：会社ごとの数え方（データ）
    sim, key, true_deg = keep
    comp = pd.DataFrame({"company_id": np.arange(N), "true_partners_now": true_deg,
                         "activity": np.round(sim["a"], 4), "partner_rate_scale": np.round(sim["rcomp"], 4),
                         "duration_scale_months": np.round(sim["dcomp"], 3)})
    for w in WS:
        seen = sim["cnt"][:, MONTHS - w:].sum(1) > 0
        comp[f"partners_last_{w}m"] = partners(sim["pair"][seen])[0]
    comp.to_csv(DATA / "companies_one_rep.csv", index=False)
    rel = pd.DataFrame({"company_a": sim["lo"], "company_b": sim["hi"],
                        "active_at_month24_end": sim["active_now"].astype(int)})
    for m in range(MONTHS):
        rel[f"m{m + 1:02d}"] = sim["cnt"][:, m]
    rel.to_csv(DATA / "relations_monthly_counts_one_rep.csv", index=False)
    # 会社の性質（取引の多さ・続く長さの4分の1ずつ）と、数え方のずれ（200回の平均）
    typ = pd.DataFrame(typ_rows).groupby(["W", "by", "quartile"]).rel_err_pct.mean().reset_index().round(3)
    typ.to_csv(RES / "error_by_company_type.csv", index=False)
    tt = typ.set_index(["W", "by", "quartile"]).rel_err_pct
    char = {"W1_rate_q1_low": float(tt[(1, "rate", 1)]), "W1_rate_q4_high": float(tt[(1, "rate", 4)]),
            "W24_dur_q1_short": float(tt[(24, "duration", 1)]), "W24_dur_q4_long": float(tt[(24, "duration", 4)]),
            "W24_rate_q1_low": float(tt[(24, "rate", 1)]), "W24_rate_q4_high": float(tt[(24, "rate", 4)]),
            "W1_dur_q1_short": float(tt[(1, "duration", 1)]), "W1_dur_q4_long": float(tt[(1, "duration", 4)])}

    # 確かめ：続く長さ × 取引の多さの散らばり（9通り、各50回）
    rows = []
    for i, dm in enumerate(GRID_DUR):
        for j, sg in enumerate(GRID_SIG):
            for rep in range(GRID_REPS):
                rng = np.random.default_rng(SEED * 5000 + 1000 * (3 * i + j) + rep)
                sim_g = simulate(rng, BASE["birth"] * 18.0 / dm, dm, BASE["rate_median"], sg)
                df = measure(sim_g, rng.random(N))[0]
                df["dur"], df["sigma"] = dm, sg
                rows.append(df)
    grid = pd.concat(rows).groupby(["dur", "sigma", "W"]).mean(numeric_only=True).reset_index()
    grid["top1_same"] *= 100
    grid = grid.rename(columns={"top1_same": "top1_same_pct"}).round(4)
    grid.to_csv(RES / "grid.csv", index=False)
    bestg = grid.loc[grid.groupby(["dur", "sigma"]).top10_overlap.idxmax()][["dur", "sigma", "W", "top10_overlap"]]
    w24 = grid[grid.W == 24]
    w1 = grid[grid.W == 1]
    gb = grid.set_index(["dur", "sigma", "W"])
    loss = []
    for (dm, sg), sub in grid.groupby(["dur", "sigma"]):
        loss.append(sub.top10_overlap.max() - float(gb.loc[(dm, sg, 24), "top10_overlap"]))

    s = summ.set_index("W")
    headline = {
        "true_total_pairs_mean": r(s.loc[1, "true_total"], 1),
        "ratio_total": {int(w): float(s.loc[w, "ratio_total"]) for w in WS},
        "ended_share_pct": {int(w): float(s.loc[w, "ended_share_pct"]) for w in WS},
        "missed_share_pct": {int(w): float(s.loc[w, "missed_share_pct"]) for w in WS},
        "top10_overlap": {int(w): float(s.loc[w, "top10_overlap"]) for w in WS},
        "top10_overlap_min_max": {int(a): [int(b), int(c)] for a, b, c in zip(rng_rows.W, rng_rows["min"], rng_rows["max"])},
        "top1_same_pct": {int(w): float(s.loc[w, "top1_same_pct"]) for w in WS},
        "spearman": {int(w): float(s.loc[w, "spearman"]) for w in WS},
        "top10_true_mean": {int(w): float(s.loc[w, "top10_true_mean"]) for w in WS},
        "top10_best_mean": float(s.loc[1, "top10_best_mean"]),
        "best_window_base": best_w,
        "between_windows_top10_overlap": {k: float(v) for k, v in btw.items()},
        "formula_check_max_abs_diff_pct": float(fr.diff_pct.abs().max()),
        "company_type_rel_err_pct": char,
        "grid_best_window": {f"dur={a}, sigma={b}": int(c) for a, b, c in zip(bestg.dur, bestg.sigma, bestg.W)},
        "grid_best_overlap_range": [float(bestg.top10_overlap.min()), float(bestg.top10_overlap.max())],
        "grid_W24_overlap_range": [float(w24.top10_overlap.min()), float(w24.top10_overlap.max())],
        "grid_W1_overlap_range": [float(w1.top10_overlap.min()), float(w1.top10_overlap.max())],
        "grid_W24_ratio_total_range": [float(w24.ratio_total.min()), float(w24.ratio_total.max())],
        "grid_W1_ratio_total_range": [float(w1.ratio_total.min()), float(w1.ratio_total.max())],
        "grid_loss_W24_vs_best_range": [r(min(loss), 3), r(max(loss), 3)],
    }

    # 図1：数える期間ごとの取引先の数（本当を1とした比）と内訳
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.2))
    x = np.arange(len(WS))
    lab = [f"{w}か月" for w in WS]
    ax[0].bar(x, summ.ratio_total, 0.6, color=BLUE)
    ax[0].axhline(1, color=GRAY, ls="--", lw=1)
    for i, v in enumerate(summ.ratio_total):
        ax[0].text(i, v + 0.03, f"{v:.2f}倍", ha="center", fontsize=9)
    ax[0].set_xticks(x, lab)
    ax[0].set_ylim(0, max(summ.ratio_total) * 1.2)
    ax[0].set_xlabel("直近何か月の記録で数えたか")
    ax[0].set_ylabel("数えた取引のつながり ÷ 今のつながり")
    ax[0].set_title("全体の数（今のつながりを1とした比）")
    ax[1].bar(x - 0.2, summ.missed_share_pct, 0.4, color=ORANGE, label="今のつながりのうち、数えもれた割合")
    ax[1].bar(x + 0.2, summ.ended_share_pct, 0.4, color=GRAY, label="数えたつながりのうち、もう終わっていた割合")
    for i in range(len(WS)):
        ax[1].text(i - 0.2, summ.missed_share_pct[i] + 1, f"{summ.missed_share_pct[i]:.1f}", ha="center", fontsize=8)
        ax[1].text(i + 0.2, summ.ended_share_pct[i] + 1, f"{summ.ended_share_pct[i]:.1f}", ha="center", fontsize=8)
    ax[1].set_xticks(x, lab)
    ax[1].set_ylim(0, 100)
    ax[1].set_xlabel("直近何か月の記録で数えたか")
    ax[1].set_ylabel("%")
    ax[1].set_title("短いと数えもれ、長いと終わった相手がまざる")
    ax[1].legend(frameon=False, loc="upper center", fontsize=9)
    fig.suptitle("架空の会社200社の取引（200回の平均）", y=1.02)
    save(fig, "a1085_counts.png", SRC)

    # 図2：上位10社の顔ぶれ
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.bar(x, summ.top10_overlap, 0.6, color=BLUE)
    for i, v in enumerate(summ.top10_overlap):
        ax.text(i, v + 0.15, f"{v:.2f}社", ha="center", fontsize=9)
    ax.set_xticks(x, lab)
    ax.set_ylim(0, 10)
    ax.set_xlabel("直近何か月の記録で数えたか")
    ax.set_ylabel("本当の上位10社と重なった数（社）")
    ax.set_title("取引先の多い上位10社は、数える期間で入れかわる（200回の平均）")
    save(fig, "a1085_top10.png", SRC)

    # 図3：確かめ（続く長さ別、取引の多さの散らばり1.0）
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for k, sg in enumerate(GRID_SIG):
        for dm, c in zip(GRID_DUR, [ORANGE, BLUE, GREEN]):
            sub = grid[(grid.dur == dm) & (grid.sigma == sg)]
            ax[k].plot(np.arange(len(WS)), sub.top10_overlap, "o-", color=c, label=f"続く長さの目安 {dm:g}か月")
        ax[k].set_xticks(np.arange(len(WS)), [str(w) for w in WS])
        ax[k].set_ylim(0, 10)
        ax[k].set_xlabel("直近何か月（か月）")
        ax[k].set_title(f"取引の多さの散らばり σ＝{sg:g}")
    ax[0].set_ylabel("本当の上位10社と重なった数（社）")
    ax[0].legend(frameon=False, loc="lower center", fontsize=8.5)
    fig.suptitle("どの期間がいちばん当たるかは、取引の続く長さと多さで変わる（9通り、各50回）", y=1.03)
    save(fig, "a1085_grid.png", SRC)

    out = {"seed": SEED, "settings": {"companies": N, "months": MONTHS, "windows": WS, **BASE, "reps": REPS,
                                      "grid_dur_median": GRID_DUR, "grid_rate_sigma": GRID_SIG,
                                      "grid_reps": GRID_REPS, "top": TOP, "burn_in_months": BURN,
                                      "activity_log_sd": SIG_A, "duration_log_sd": SIG_D,
                                      "pair_rate_log_sd": SIG_PAIR},
           "headline": headline, "by_window": summ.to_dict("records"),
           "formula_check": fr.to_dict("records"), "grid_best": bestg.to_dict("records")}
    with open(RES / "a1085_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(headline, ensure_ascii=False, indent=1))
    print(summ.to_string())
    print(fr.to_string())
    print(bestg.to_string())
    print(typ.to_string())
    print(grid[grid.sigma == 1.0].to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
