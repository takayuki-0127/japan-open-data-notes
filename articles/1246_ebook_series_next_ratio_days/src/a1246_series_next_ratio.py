"""1246 1冊目から2冊目へ進んだ割合は、出してからの日数をそろえないとどう見えるのか？（架空のデータ）

架空の電子書籍のシリーズ。1冊目を買った人のうち、本当に2冊目へ進む人の割合（進む割合）と、
1冊目を買ってから2冊目を買うまでの日数を作成者が置き、1人ずつ乱数で作る。
書き手に見えるのは、1冊目と2冊目の売れた冊数の累計だけ（誰が進んだかは見えない）と置き、
「2冊目の累計 ÷ 1冊目の累計」が、2冊目を出してからの日数でどう動くか、シリーズどうしの比べがどれだけ当たるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1246
SRC = "架空の電子書籍のシリーズ（作成者が乱数で作成、seed 1246）"
PEAK, TAU, TAIL = 40.0, 15.0, 4.0     # 1冊目の1日の売れ方：40×e^(−日/15)＋4
WAIT = 5.0                             # 2冊目を待っていた人が、出てから買うまでの日数の平均


def series(rng, p=0.30, M=30.0, G=120, end=None, a=0.04):
    """1人ずつ作る。戻り値：1冊目を買った日、2冊目を買った日（進んだ人、−1は進まない）、2冊目から入った人の買った日"""
    end = G + 730 if end is None else end
    days = np.arange(end + 1)
    n1 = rng.poisson(PEAK * np.exp(-days / TAU) + TAIL)
    buy1 = np.repeat(days, n1)
    go = rng.random(len(buy1)) < p
    want = buy1 + rng.exponential(M, len(buy1))
    buy2 = np.where(want < G, G + rng.exponential(WAIT, len(buy1)), want)
    buy2 = np.where(go, np.floor(buy2), -1).astype(int)
    d2 = days[days >= G]
    ns = rng.poisson(a * (PEAK * np.exp(-(d2 - G) / TAU) + TAIL))
    start2 = np.repeat(d2, ns)
    return buy1, buy2, start2


def counts_at(buy1, buy2, start2, T):
    c1 = int((buy1 <= T).sum())
    prog = int(((buy2 >= 0) & (buy2 <= T)).sum())
    st = int((start2 <= T).sum())
    return c1, prog + st, prog, st


def compare(rng, n=40, a=0.04, M_range=(15, 60), K_range=(7, 720), ks=(30, 180)):
    """シリーズ40本：本当の進む割合・日数・2冊目を出してからの日数を本ごとに引く"""
    p = rng.uniform(0.20, 0.40, n)
    M = rng.uniform(*M_range, n)
    G = rng.integers(14, 241, n)
    K = rng.integers(K_range[0], K_range[1] + 1, n)
    naive, al = np.zeros(n), {k: np.full(n, np.nan) for k in ks}
    for i in range(n):
        b1, b2, s2 = series(rng, p[i], M[i], int(G[i]), int(G[i] + K[i]), a)
        c1, c2, _, _ = counts_at(b1, b2, s2, G[i] + K[i])
        naive[i] = c2 / c1
        for k in ks:
            if K[i] >= k:
                c1k, c2k, _, _ = counts_at(b1, b2, s2, G[i] + k)
                al[k][i] = c2k / c1k
    return p, K, naive, al


def pair_hit(est, p):
    ok = ~np.isnan(est)
    e, q = est[ok], p[ok]
    i, j = np.triu_indices(len(e), 1)
    return float((np.sign(e[i] - e[j]) == np.sign(q[i] - q[j])).mean()), int(ok.sum())


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 1つのシリーズ：2冊目を出してからの日数で、見かけの割合が動く（本当の進む割合30%）
    G = 120
    b1, b2, s2 = series(rng, 0.30, 30.0, G, G + 730, 0.04)
    ks = [7, 14, 30, 60, 90, 180, 365, 730]
    rows = []
    for k in ks:
        c1, c2, prog, st = counts_at(b1, b2, s2, G + k)
        prog_eventual = int(((b1 <= G + k) & (b2 >= 0)).sum())
        rows.append({"days_after_book2": k, "book1_total": c1, "book2_total": c2,
                     "ratio_book2_over_book1": round(c2 / c1 * 100, 2),
                     "progressed_by_now_share": round(prog / c1 * 100, 2),
                     "will_progress_share": round(prog_eventual / c1 * 100, 2),
                     "starters_share_of_book2": round(st / max(c2, 1) * 100, 2)})
    one = pd.DataFrame(rows)
    one.to_csv(RES / "one_series_by_days.csv", index=False)
    end = G + 730
    daily = pd.DataFrame({"day": np.arange(end + 1),
                          "book1_sold": np.bincount(b1, minlength=end + 1)[: end + 1],
                          "book2_sold": (np.bincount(b2[b2 >= 0], minlength=end + 2)[: end + 1]
                                         + np.bincount(s2, minlength=end + 1)[: end + 1])})
    daily.to_csv(DATA / "one_series_daily.csv", index=False)

    # 同じ1つのシリーズの見かけの割合（毎日）
    cum1 = np.cumsum(daily.book1_sold.values); cum2 = np.cumsum(daily.book2_sold.values)
    curve = (cum2[G:] / cum1[G:] * 100)

    # 2) 入れかわりの例：本当の進む割合が低いが2冊目を出して600日のシリーズAと、高いが20日のシリーズB
    ex = {}
    for nm, p, k in [("A", 0.28, 600), ("B", 0.33, 14)]:
        r2 = np.random.default_rng(SEED * 10 + (1 if nm == "A" else 2))
        bb1, bb2, ss2 = series(r2, p, 30.0, 120, 120 + max(k, 180), 0.04)
        c1, c2, _, _ = counts_at(bb1, bb2, ss2, 120 + k)
        c1a, c2a, _, _ = counts_at(bb1, bb2, ss2, 120 + 180)
        ex[nm] = {"true_progress": p, "days_after_book2": k, "ratio_now": round(c2 / c1 * 100, 2),
                  "ratio_at_180_days": round(c2a / c1a * 100, 2)}

    # 3) シリーズ40本を比べる（200回）
    reps, pool, pairs = [], [], []
    for r in range(200):
        p, K, naive, al = compare(np.random.default_rng(SEED * 1000 + r))
        pool.append(pd.DataFrame({"K": K, "gap": naive - p}))
        h0, _ = pair_hit(naive, p)
        h30, n30 = pair_hit(al[30], p)
        h180, n180 = pair_hit(al[180], p)
        h0s, _ = pair_hit(np.where(np.isnan(al[180]), np.nan, naive), p)
        i, j = np.triu_indices(len(p), 1)
        mix = ((K[i] < 30) & (K[j] >= 180)) | ((K[j] < 30) & (K[i] >= 180))
        close = np.abs(p[i] - p[j]) < 0.05
        hit = np.sign(naive[i] - naive[j]) == np.sign(p[i] - p[j])
        ok30 = ~np.isnan(al[30][i]) & ~np.isnan(al[30][j])
        hit30 = np.where(ok30, (np.sign(al[30][i] - al[30][j]) == np.sign(p[i] - p[j])).astype(float), np.nan)
        pairs.append(pd.DataFrame({"mix": mix, "close": close, "hit": hit, "hit30": hit30,
                                   "both180": (K[i] >= 180) & (K[j] >= 180)}))
        top_true = set(np.argsort(-p)[:5]); top_naive = set(np.argsort(-naive)[:5])
        reps.append({"rep": r, "pair_hit_now": h0, "pair_hit_30": h30, "pair_hit_180": h180, "pair_hit_now_same_books_180": h0s, "n_usable_180": n180,
                     "top5_overlap_now": len(top_true & top_naive) / 5,
                     "corr_naive_days": float(np.corrcoef(naive, K)[0, 1]),
                     "corr_naive_true": float(np.corrcoef(naive, p)[0, 1])})
    reps = pd.DataFrame(reps)
    cmp_res = {c: round(float(reps[c].mean()) * (100 if c.startswith(("pair", "top5")) else 1), 3)
               for c in reps.columns if c != "rep"}
    pool = pd.concat(pool, ignore_index=True)
    cuts = [7, 30, 90, 180, 366, 721]
    names = ["7〜29日", "30〜89日", "90〜179日", "180〜365日", "366〜720日"]
    pool["band"] = pd.cut(pool.K, cuts, right=False, labels=names)
    byk = pool.groupby("band", observed=True).gap.agg(
        gap_mean=lambda v: round(float(v.mean()) * 100, 2) + 0.0, gap_p10=lambda v: round(float(v.quantile(.1)) * 100, 2),
        gap_p90=lambda v: round(float(v.quantile(.9)) * 100, 2), n="size").reset_index()
    byk.to_csv(RES / "gap_by_days.csv", index=False)
    cmp_res["gap_by_days"] = byk.to_dict("records")
    pairs = pd.concat(pairs, ignore_index=True)
    pk = []
    for nm, m in [("全部の組", np.ones(len(pairs), bool)), ("片方が出して30日未満・もう片方が180日以上", pairs.mix.values),
                  ("両方とも180日以上", pairs.both180.values)]:
        for cn, c in [("進む割合の差が5ポイント未満", pairs.close.values), ("差が5ポイント以上", ~pairs.close.values)]:
            mm = m & c
            pk.append({"pairs": nm, "true_gap": cn, "n_pairs": int(mm.sum()),
                       "hit_now": round(float(pairs.hit.values[mm].mean()) * 100, 2),
                       "hit_30_where_both_have_30days": (round(float(np.nanmean(pairs.hit30.values[mm])) * 100, 2)
                                                         if np.isfinite(pairs.hit30.values[mm]).any() else None)})
    pk = pd.DataFrame(pk)
    pk.to_csv(RES / "pair_hit_by_kind.csv", index=False)
    cmp_res["pair_hit_by_kind"] = pk.to_dict("records")

    # 4) 置き方を変えると（買うまでの日数の平均の幅 × 2冊目から入る人の多さ、9通り、各60回）
    grid = []
    for mr in [(10, 30), (15, 60), (30, 120)]:
        for a in [0.0, 0.04, 0.10]:
            hm, hb, hall, g_new, g_old = [], [], [], [], []
            for r in range(60):
                rr = np.random.default_rng(SEED * 100000 + int(mr[1]) * 100 + int(a * 100) * 7 + r)
                p, K, naive, al = compare(rr, a=a, M_range=mr)
                i, j = np.triu_indices(len(p), 1)
                close = np.abs(p[i] - p[j]) < 0.05
                hit = np.sign(naive[i] - naive[j]) == np.sign(p[i] - p[j])
                mix = ((K[i] < 30) & (K[j] >= 180)) | ((K[j] < 30) & (K[i] >= 180))
                both = (K[i] >= 180) & (K[j] >= 180)
                hm.append(hit[close & mix]); hb.append(hit[close & both]); hall.append(hit[close])
                g_new.append((naive - p)[K < 30]); g_old.append((naive - p)[K >= 366])
            grid.append({"delay_mean_range": f"{mr[0]}〜{mr[1]}日", "starter_level": a,
                         "gap_mean_under30d": round(float(np.concatenate(g_new).mean()) * 100, 2),
                         "gap_mean_366d_plus": round(float(np.concatenate(g_old).mean()) * 100, 2),
                         "close_hit_all": round(float(np.concatenate(hall).mean()) * 100, 2),
                         "close_hit_new_vs_old": round(float(np.concatenate(hm).mean()) * 100, 2),
                         "close_hit_both_180d": round(float(np.concatenate(hb).mean()) * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gr = {c: [float(grid[c].min()), float(grid[c].max())] for c in grid.columns[2:]}
    gr["new_vs_old_below_both180_count"] = int((grid.close_hit_new_vs_old < grid.close_hit_both_180d).sum())

    out = {"setup": {"book1_daily": "40×e^(−日/15)＋4", "true_progress_one_series": 0.30, "delay_mean_one_series": 30,
                     "gap_book1_to_book2_one_series": G, "wait_after_release_mean": WAIT, "starter_level": 0.04},
           "one_series": one.to_dict("records"),
           "one_series_ratio_max": {"value": round(float(curve.max()), 2), "day": int(curve.argmax())},
           "swap_example": ex, "compare_40_series_200reps": cmp_res, "grid_range": gr}
    json.dump(out, open(RES / "a1246_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    reps.round(4).to_csv(RES / "compare_reps.csv", index=False)

    # 図1：1つのシリーズの見かけの割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(np.arange(len(curve)), curve, color=BLUE, lw=2, label="2冊目の累計 ÷ 1冊目の累計")
    ax.axhline(30, color=ORANGE, lw=1.2, ls="--"); ax.text(735, 30.5, "本当の進む割合30%", color=ORANGE, fontsize=9, ha="right", va="bottom")
    ax.set_xlabel("2冊目を出してからの日数"); ax.set_ylabel("見かけの割合（%）"); ax.set_ylim(0, 40)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("同じシリーズでも、2冊目を出してからの日数で見かけの割合が動く")
    save(fig, "a1246_curve.png", SRC)

    # 図2：2冊目を出してからの日数ごとの、見かけの割合と本当の進む割合の差
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xx = np.arange(len(byk))
    ax.bar(xx, byk.gap_mean, color=[ORANGE if v < 0 else BLUE for v in byk.gap_mean], width=0.6)
    ax.errorbar(xx, byk.gap_mean, yerr=[byk.gap_mean - byk.gap_p10, byk.gap_p90 - byk.gap_mean], fmt="none",
                ecolor=INK, lw=1, capsize=3)
    for x_, v in zip(xx, byk.gap_mean):
        ax.text(x_ + 0.33, v, "0.0" if v == 0 else f"{v:+.2f}", fontsize=9, va="center")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xx); ax.set_xticklabels(byk.band)
    ax.set_xlabel("2冊目を出してからの日数"); ax.set_ylabel("見かけ − 本当（ポイント）")
    ax.set_title("出して間もないと低く、長くたつと高く見える（線は10〜90%の範囲）", fontsize=12)
    save(fig, "a1246_gap_by_days.png", SRC)

    # 図3：進む割合の差が5ポイント未満の2本を、今の累計どうしで比べたときの当たり
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    pk2 = pk[pk.true_gap == "進む割合の差が5ポイント未満"].reset_index(drop=True)
    rng_cols = ["close_hit_all", "close_hit_new_vs_old", "close_hit_both_180d"]
    labs = ["全部の組", "片方が出して30日未満、\nもう片方が180日以上", "両方とも180日以上"]
    yy = np.arange(3)[::-1]
    ax.barh(yy, pk2.hit_now, color=[LIGHT, ORANGE, BLUE], height=0.55)
    for y, v, c in zip(yy, pk2.hit_now, rng_cols):
        lo, hi = gr[c]
        ax.plot([lo, hi], [y - 0.36, y - 0.36], color=INK, lw=1.5)
        ax.text(v + 1, y + 0.05, f"{v:.2f}%", va="center", fontsize=9)
        ax.text(hi + 1, y - 0.36, f"置き方9通りで{lo:.2f}〜{hi:.2f}%", va="center", fontsize=8, color=GRAY)
    ax.axvline(50, color=GRAY, lw=1, ls=":")
    ax.set_yticks(yy); ax.set_yticklabels(labs); ax.set_xlim(0, 100)
    ax.set_xlabel("進む割合の高いほうを当てた組の割合（%）")
    ax.set_title(f"本当の差が5ポイント未満の2本：出して30日未満と180日以上の組の当たりは{pk2.hit_now[1]:.2f}%", fontsize=12)
    save(fig, "a1246_pairs.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
