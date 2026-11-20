"""895 問い合わせから契約までの割合は、どこで落ちているのか？（架空のデータ）

架空のフリーランスの人に来る問い合わせを、問い合わせ → 返信あり → 打ち合わせ → 見積もり提出 → 契約 の5段で追う。
段ごとに「次の段へ進む本当の割合」と「次の段までの日数」を作成者が置き、
数え方（同じ月の件数で割る／問い合わせの月ごとに追う）で、いちばん落ちている段を当てられるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 895
SRC = "架空の問い合わせと契約（作成者が乱数で作成、seed 895）"
STAGES = ["問い合わせ", "返信あり", "打ち合わせ", "見積もり提出", "契約"]
STEPS = ["問い合わせ→返信", "返信→打ち合わせ", "打ち合わせ→見積もり", "見積もり→契約"]
P_BASE = [0.60, 0.50, 0.85, 0.55]
LAG_BASE = [2.0, 7.0, 5.0, 15.0]  # 次の段までの日数の平均（指数分布）
WARM, WIN = 90, 180              # 前の3か月（すでに進んでいる分）と、数える6か月
D_OBS = WARM + WIN                # 数える日（6か月目の末日）
SETTLE = 60                       # 結果が出そろうまで待つ日数
METHODS = ["同じ月の件数で割る", "問い合わせの月で追う（すぐ数える）", "問い合わせの月で追う（60日待つ）"]


def rate_per_day(trend, vol, T):
    d = np.arange(T)
    if trend == "steady":
        return np.full(T, vol / 30)
    # growth：前の3か月は月 vol*0.5、数える6か月で vol*0.5 → vol*2 に増える
    lo, hi = vol * 0.5, vol * 2.0
    m = np.where(d < WARM, lo, lo + (hi - lo) * (d - WARM) / (WIN - 1))
    return m / 30


def simulate(rng, reps, vol, p, lag, trend):
    T = D_OBS
    lam = rate_per_day(trend, vol, T)
    cnt = rng.poisson(np.tile(lam, (reps, 1)))
    rep = np.repeat(np.repeat(np.arange(reps), T), cnt.ravel())
    day = np.repeat(np.tile(np.arange(T), reps), cnt.ravel()) + rng.uniform(0, 1, cnt.sum())
    n = len(day)
    times = np.full((n, 5), np.nan)
    times[:, 0] = day
    alive = np.ones(n, bool)
    t = day.copy()
    for s in range(4):
        go = alive & (rng.uniform(0, 1, n) < p[s])
        t = t + rng.exponential(lag[s], n)
        times[go, s + 1] = t[go]
        alive = go
    return rep, times


def estimate(rep, times, reps):
    """3つの数え方で段ごとの割合を出す。返り値：method -> (reps, 4)、ほかに件数"""
    out = {}
    seen = times < D_OBS                       # 数える日までに起きた出来事
    # A：同じ期間（6か月）に起きた件数で割る
    inwin = seen & (times >= WARM)
    cA = np.stack([np.bincount(rep, weights=inwin[:, s], minlength=reps) for s in range(5)], 1)
    # B：問い合わせが6か月に入った人を追い、数える日までに起きた段だけ数える
    coh = (times[:, 0] >= WARM) & (times[:, 0] < D_OBS)
    cB = np.stack([np.bincount(rep, weights=(coh & seen[:, s]), minlength=reps) for s in range(5)], 1)
    # C：問い合わせから60日以上たった人だけを追う
    cohC = (times[:, 0] >= WARM) & (times[:, 0] < D_OBS - SETTLE)
    cC = np.stack([np.bincount(rep, weights=(cohC & seen[:, s]), minlength=reps) for s in range(5)], 1)
    for name, c in zip(METHODS, [cA, cB, cC]):
        with np.errstate(invalid="ignore", divide="ignore"):
            r = c[:, 1:] / c[:, :-1]
        out[name] = np.where(np.isfinite(r), r, np.nan)  # 分母が0の段は割合を出せない
    return out, cA


def pick(r):
    """いちばん低く出た段（割合が出せない段がある回は -1）"""
    ok = ~np.isnan(r).any(1)
    return np.where(ok, np.argmin(np.where(np.isnan(r), np.inf, r), 1), -1)


def weakest_hit(r, true_idx):
    """いちばん低い段が本当にいちばん低い段か（割合が出せない段がある回は外れとする）"""
    am = pick(r)
    return float((am == true_idx).mean()), float((am >= 0).mean())


def run_case(seed, reps, vol, p, lag, trend):
    rng = np.random.default_rng(seed)
    rep, times = simulate(rng, reps, vol, p, lag, trend)
    est, cA = estimate(rep, times, reps)
    true_idx = int(np.argmin(p))
    row = {"vol": vol, "trend": trend, "p_last": p[3], "lag_scale": lag[0] / LAG_BASE[0]}
    for k, name in enumerate(METHODS):
        hit, ok = weakest_hit(est[name], true_idx)
        row[f"hit_{k}"] = hit
        row[f"computable_{k}"] = ok
        row[f"pick_last_{k}"] = float((pick(est[name]) == 3).mean())
        for s in range(4):
            row[f"est_{k}_{s}"] = float(np.nanmean(est[name][:, s]))
    drop = cA[:, :-1] - cA[:, 1:]
    row["hit_countdrop"] = float((drop.argmax(1) == true_idx).mean())
    row["countdrop_mode"] = int(np.bincount(drop.argmax(1), minlength=4).argmax())
    return row, rep, times, est


def main():
    t0 = time.time()
    REPS = 4000
    base_rows = []
    keep = {}
    for i, (vol, trend) in enumerate([(5, "steady"), (15, "steady"), (50, "steady"),
                                      (15, "growth")]):
        row, rep, times, est = run_case(SEED * 10 + i, REPS, vol, P_BASE, LAG_BASE, trend)
        base_rows.append(row)
        keep[(vol, trend)] = (rep, times, est)
    base = pd.DataFrame(base_rows)
    base.round(4).to_csv(RES / "base_cases.csv", index=False)

    # 1人の6か月（15件／月・横ばい）の月ごとの割合のぶれ（同じ月の件数で割る）
    rep, times, _ = keep[(15, "steady")]
    monthly = []
    for r in range(REPS):
        tt = times[rep == r]
        for m in range(6):
            a, b = WARM + 30 * m, WARM + 30 * (m + 1)
            c = [int(((tt[:, s] >= a) & (tt[:, s] < b)).sum()) for s in range(5)]
            monthly.append({"rep": r, "month": m + 1, **{f"n{s}": c[s] for s in range(5)}})
    monthly = pd.DataFrame(monthly)
    with np.errstate(invalid="ignore", divide="ignore"):
        last = monthly.n4 / monthly.n3
    month_stats = {"monthly_last_step_p10": round(float(last.quantile(.1)), 3),
                   "monthly_last_step_p90": round(float(last.quantile(.9)), 3),
                   "monthly_last_step_nan_share": round(float(last.isna().mean()), 3),
                   "monthly_weakest_hit": None}
    mm = monthly[["n0", "n1", "n2", "n3", "n4"]].values.astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        mr = mm[:, 1:] / mm[:, :-1]
    month_stats["monthly_weakest_hit"] = round(weakest_hit(mr, 3)[0], 3)

    # 確かめ：問い合わせの件数×日数の長さ×最後の段の割合×増え方（54通り）
    grid = []
    k = 0
    for vol in [5, 15, 50]:
        for ls in [0.5, 1.0, 2.0]:
            for pl in [0.52, 0.55, 0.65]:
                for trend in ["steady", "growth"]:
                    p = P_BASE[:3] + [pl]
                    row, *_ = run_case(SEED * 1000 + k, 1500, vol, p, [x * ls for x in LAG_BASE], trend)
                    for s in range(4):
                        for j in range(3):
                            row[f"bias_{j}_{s}"] = row[f"est_{j}_{s}"] - p[s]
                    grid.append(row)
                    k += 1
    grid = pd.DataFrame(grid)
    grid.round(4).to_csv(RES / "sensitivity_grid.csv", index=False)

    # データ：1人分（15件／月・横ばい）の問い合わせの記録
    r0 = keep[(15, "steady")]
    sel = r0[0] == 0
    d = pd.DataFrame(np.round(r0[1][sel], 2), columns=["day_inquiry", "day_reply", "day_meeting", "day_quote", "day_contract"])
    d.insert(0, "inquiry_id", np.arange(1, len(d) + 1))
    d.to_csv(DATA / "one_person_inquiries.csv", index=False)

    def est_table(row):
        return {name: [round(row[f"est_{k}_{s}"], 4) for s in range(4)] for k, name in enumerate(METHODS)}

    gsum = {}
    for j, name in enumerate(METHODS):
        gsum[name] = {"hit_min": round(float(grid[f"hit_{j}"].min()), 4), "hit_max": round(float(grid[f"hit_{j}"].max()), 4),
                      "bias_last_min": round(float(grid[f"bias_{j}_3"].min()), 4),
                      "bias_last_max": round(float(grid[f"bias_{j}_3"].max()), 4),
                      "max_abs_bias_any_step": round(float(grid[[f"bias_{j}_{s}" for s in range(4)]].abs().values.max()), 4)}
    gsum["countdrop_hit_max"] = round(float(grid.hit_countdrop.max()), 4)
    gsum["countdrop_hit_by_p_last"] = grid.groupby("p_last").hit_countdrop.agg(["min", "max"]).round(4).reset_index().to_dict("records")
    # 「すぐ数える」が「60日待つ」より当たりが低い通り
    gsum["immediate_lt_settle_count"] = int((grid.hit_1 < grid.hit_2).sum())
    gsum["immediate_lt_samemonth_count"] = int((grid.hit_1 < grid.hit_0).sum())
    gsum["hit_by_p_last"] = {f"{pl}": {f"{c}_{a}": round(float(v), 4) for c in ["hit_0", "hit_1", "hit_2", "hit_countdrop"]
                                        for a, v in grid[grid.p_last == pl][c].agg(["min", "max"]).items()}
                             for pl in sorted(grid.p_last.unique())}
    gsum["last_step_bias_by_lag_trend"] = {f"lag{ls}_{tr}": {f"bias_{j}_{a}": round(float(v), 4) for j in range(3)
                                                            for a, v in g_[f"bias_{j}_3"].agg(["min", "max"]).items()}
                                           for (ls, tr), g_ in grid.groupby(["lag_scale", "trend"])}
    gsum["growth_sameMonth_last_bias"] = grid[grid.trend == "growth"].bias_0_3.agg(["min", "max"]).round(4).to_dict()
    gsum["steady_sameMonth_last_bias"] = grid[grid.trend == "steady"].bias_0_3.agg(["min", "max"]).round(4).to_dict()
    gsum["hit_by_vol"] = grid.groupby("vol")[["hit_0", "hit_1", "hit_2"]].agg(["min", "max"]).round(4).to_dict()
    gsum["hit_by_vol"] = {f"{a}|{b}|{c}": v for (a, b), d_ in gsum["hit_by_vol"].items() for c, v in d_.items()}
    per100 = [100.0]
    for q in P_BASE:
        per100.append(per100[-1] * q)
    out = {"true_rates": dict(zip(STEPS, P_BASE)), "lag_days_mean": dict(zip(STEPS, LAG_BASE)),
           "per_100_inquiries": [round(x, 2) for x in per100],
           "drop_per_100": [round(per100[i] - per100[i + 1], 2) for i in range(4)],
           "overall_true": round(float(np.prod(P_BASE)), 4),
           "base_cases": [{**{k: v for k, v in r.items() if not k.startswith("est_")}, "estimates": est_table(r)}
                          for r in base_rows],
           "monthly_15_steady": month_stats, "grid_summary": gsum, "grid_n": len(grid)}
    out = json.loads(json.dumps(out, default=float))

    def rnd(o):
        if isinstance(o, float):
            return round(o, 4)
        if isinstance(o, dict):
            return {k: rnd(v) for k, v in o.items()}
        if isinstance(o, list):
            return [rnd(v) for v in o]
        return o
    out = rnd(out)
    json.dump(out, open(RES / "a895_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：100件の問い合わせが段ごとにどう減るか（件数の減りと割合）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.bar(range(5), per100, color=[BLUE] * 4 + [GREEN], width=0.6)
    for i in range(5):
        ax.text(i, per100[i] + 1.5, f"{per100[i]:.1f}件", ha="center", fontsize=9)
    for i in range(4):
        col = ORANGE if i == int(np.argmin(P_BASE)) else INK
        ax.annotate(f"{P_BASE[i]*100:.0f}%が進む\n（−{per100[i]-per100[i+1]:.1f}件）", xy=(i + 0.5, per100[i] + 9),
                    ha="center", va="bottom", fontsize=8.5, color=col)
    ax.set_xticks(range(5)); ax.set_xticklabels(STAGES)
    ax.set_ylabel("問い合わせ100件あたりの件数"); ax.set_ylim(0, 130); ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_title("件数がいちばん減る段と、割合がいちばん低い段は違う")
    save(fig, "a895_funnel.png", SRC)

    # 図2：数え方ごとの段の割合（15件／月、横ばい・増えている）
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True)
    for ax, (trend, ttl) in zip(axes, [("steady", "問い合わせが横ばい"), ("growth", "問い合わせが増えている")]):
        row = [r for r in base_rows if r["vol"] == 15 and r["trend"] == trend][0]
        w = 0.2
        x = np.arange(4)
        ax.bar(x - 1.5 * w, np.array(P_BASE) * 100, w, color=GRAY, label="本当の割合")
        for k, c in enumerate([BLUE, ORANGE, GREEN]):
            ax.bar(x + (k - 0.5) * w, [row[f"est_{k}_{s}"] * 100 for s in range(4)], w, color=c, label=METHODS[k])
        ax.set_xticks(x); ax.set_xticklabels(["問合→返信", "返信→打合", "打合→見積", "見積→契約"], fontsize=9)
        ax.set_title(ttl, fontsize=11); ax.set_ylim(0, 125); ax.set_yticks([0, 20, 40, 60, 80, 100])
    axes[0].set_ylabel("次の段へ進む割合（%、4,000人の平均）")
    axes[0].legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    fig.suptitle("すぐ数えると、日数のかかる最後の段が低く出る（月15件）", fontsize=13, y=1.02)
    save(fig, "a895_methods.png", SRC)

    # 図3：問い合わせの件数と、いちばん低い段を当てられた割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    st = base[base.trend == "steady"]
    x = np.arange(len(st))
    w = 0.2
    for k, c in enumerate([BLUE, ORANGE, GREEN]):
        ax.bar(x + (k - 1.5) * w, st[f"hit_{k}"] * 100, w, color=c, label=METHODS[k])
    ax.bar(x + 1.5 * w, st["hit_countdrop"] * 100, w, color=GRAY, label="件数の減りがいちばん大きい段")
    for i, v in enumerate(st["hit_2"] * 100):
        ax.text(i + 0.5 * w, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"月{v}件" for v in st.vol])
    ax.set_ylabel("いちばん低い段を当てた割合（%）"); ax.set_ylim(0, 110)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("6か月分の件数では、いちばん低い段を当てるのは難しい（横ばい）")
    save(fig, "a895_hit_by_volume.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
