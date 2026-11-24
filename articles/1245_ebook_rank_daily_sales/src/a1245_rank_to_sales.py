"""1245 販売の順位から、1日に何冊売れたかはどこまで読めるのか？（架空のデータ）

架空の電子書籍の売り場（2万冊）。本ごとに「ふだんの1日の売れ方」（平均の冊数）を作成者が置き、
毎日の冊数は乱数で引く。順位は作成者が置いた決まり（数日分の冊数を、古い日ほど軽くして足した点の大きい順）で付ける。
作成者は本当の冊数を知っているので、「順位だけから読める最良の換算表」（その順位の本がその日に売れた冊数の平均）を作り、
別に作り直した売り場で、その換算表で読んだ冊数が、その日の冊数・ふだんの売れ方にどれだけ合うかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1245
SRC = "架空の電子書籍の売り場（作成者が乱数で作成、seed 1245）。順位の決まりは作成者が置いたもの"
N_BOOK = 20000
MU = -3.0
BANDS = [(1, 10), (11, 100), (101, 1000), (1001, 10000), (10001, 20000)]
BAND_NAMES = ["1〜10位", "11〜100位", "101〜1,000位", "1,001〜10,000位", "10,001〜20,000位"]


def simulate(rng, sigma=1.6, half=2.0, burn=60, days=60, n=N_BOOK):
    """毎日の冊数と順位を作る。戻り値：lam（ふだんの売れ方）、x[日, 本]、rank[日, 本]、score[日, 本]"""
    lam = np.exp(rng.normal(MU, sigma, n))
    d = 0.5 ** (1.0 / half)
    s = np.zeros(n)
    xs, rs, ss = [], [], []
    for t in range(burn + days):
        g = rng.gamma(2.0, 0.5, n)          # 日ごとのむら（平均1）
        x = rng.poisson(lam * g)
        s = s * d + x
        tie = rng.random(n)                  # 同じ点の本の並びはでたらめ
        order = np.lexsort((tie, -s))
        r = np.empty(n, dtype=np.int64)
        r[order] = np.arange(1, n + 1)
        if t >= burn:
            xs.append(x); rs.append(r); ss.append(s.copy())
    return lam, np.array(xs), np.array(rs), np.array(ss)


def rank_bins(n=N_BOOK):
    e = np.unique(np.round(np.logspace(0, np.log10(n), 46)).astype(int))
    return np.append(e, n + 1)


def make_table(x, r, edges):
    """順位の区切りごとに、その日に売れた冊数の平均（順位だけから読める最良の換算表）"""
    idx = np.searchsorted(edges, r.ravel(), side="right") - 1
    tab = np.bincount(idx, weights=x.ravel(), minlength=len(edges) - 1) / np.maximum(
        np.bincount(idx, minlength=len(edges) - 1), 1)
    return tab[: len(edges) - 1]


def read_rank(tab, edges, r):
    idx = np.searchsorted(edges, r, side="right") - 1
    return tab[np.clip(idx, 0, len(tab) - 1)]


def within2(est, ref):
    ok = (ref > 0) & (est >= ref / 2) & (est <= ref * 2)
    return ok


def evaluate(lam, x, r, tab, edges):
    est = read_rank(tab, edges, r)                     # [日, 本]
    L = np.broadcast_to(lam, x.shape)
    rows = []
    # 7日分：7日ごとに区切り、7日の換算の平均と、7日の冊数の平均をくらべる（帯は7日目の順位）
    nd = x.shape[0] // 7 * 7
    x7 = x[:nd].reshape(-1, 7, x.shape[1]).mean(1)
    e7 = est[:nd].reshape(-1, 7, x.shape[1]).mean(1)
    r7 = r[6:nd:7]
    L7 = np.broadcast_to(lam, x7.shape)
    for (a, b), nm in zip(BANDS, BAND_NAMES):
        m = (r >= a) & (r <= b)
        m7 = (r7 >= a) & (r7 <= b)
        xv, ev, lv = x[m], est[m], L[m]
        rows.append({
            "band": nm,
            "read_mean": round(float(ev.mean()), 3),
            "actual_mean": round(float(xv.mean()), 3),
            "share_zero_day": round(float((xv == 0).mean()) * 100, 2),
            "actual_p10": float(np.percentile(xv, 10)), "actual_p90": float(np.percentile(xv, 90)),
            "day_within2_of_day": round(float(within2(ev, xv).mean()) * 100, 2),
            "day_within2_of_usual": round(float(within2(ev, lv).mean()) * 100, 2),
            "week_within2_of_week": round(float(within2(e7[m7], x7[m7]).mean()) * 100, 2),
            "week_within2_of_usual": round(float(within2(e7[m7], L7[m7]).mean()) * 100, 2),
        })
    return pd.DataFrame(rows)


def spike(rng, lam, x, r, s, half=2.0, base=0.3, extra=15, day=20):
    """ふだん0.3冊の本に、ある1日だけ15冊が上乗せされたとき（他の本の順位は動かさずに数える）"""
    d = 0.5 ** (1.0 / half)
    sc = base / (1 - d)                        # ふだんの売れ方での点（期待値）から始める
    out = []
    for t in range(x.shape[0]):
        v = int(rng.poisson(base * rng.gamma(2.0, 0.5)))
        if t == day:
            v += extra
        sc = sc * d + v
        rank = int((s[t] > sc).sum()) + 1
        out.append({"day": t - day, "sales": v, "rank": rank})
    return pd.DataFrame(out)


def main():
    t0 = time.time()
    rngA = np.random.default_rng(SEED)
    rngB = np.random.default_rng(SEED + 1)
    edges = rank_bins()
    lamA, xA, rA, _ = simulate(rngA)
    tab = make_table(xA, rA, edges)
    lamB, xB, rB, sB = simulate(rngB)
    base = evaluate(lamB, xB, rB, tab, edges)
    base.to_csv(RES / "bands_base.csv", index=False)

    table_df = pd.DataFrame({"rank_from": edges[:-1], "rank_to": edges[1:] - 1, "read_sales_per_day": np.round(tab, 4)})
    table_df.to_csv(RES / "rank_table.csv", index=False)

    # 1日分のデータ（作り直した売り場の最終日）
    day = pd.DataFrame({"book_id": np.arange(1, N_BOOK + 1), "usual_per_day": np.round(lamB, 4),
                        "rank_last_day": rB[-1], "sales_last_day": xB[-1],
                        "sales_last7_total": xB[-7:].sum(0)})
    day.to_csv(DATA / "books_one_day.csv", index=False)

    # 同じ順位でも、その日の冊数はどれだけ違うか（いくつかの順位の前後）
    spot = []
    for rk in [10, 100, 1000, 3000, 10000]:
        m = (rB >= rk * 0.9) & (rB <= rk * 1.1)
        xv = xB[m]
        spot.append({"rank_around": rk, "read": round(float(read_rank(tab, edges, np.array([rk]))[0]), 3),
                     "share_0": round(float((xv == 0).mean()) * 100, 2),
                     "share_1": round(float((xv == 1).mean()) * 100, 2),
                     "share_2plus": round(float((xv >= 2).mean()) * 100, 2),
                     "usual_p10": round(float(np.percentile(lamB[np.nonzero(m)[1]], 10)), 3),
                     "usual_p90": round(float(np.percentile(lamB[np.nonzero(m)[1]], 90)), 3)})

    # 1日だけ多く売れた本
    sp = spike(np.random.default_rng(SEED + 2), lamB, xB, rB, sB)
    sp["read"] = np.round(read_rank(tab, edges, sp["rank"].values), 3)
    nb = spike(np.random.default_rng(SEED + 2), lamB, xB, rB, sB, extra=0)   # 同じ乱数で、上乗せなし
    nb["read"] = np.round(read_rank(tab, edges, nb["rank"].values), 3)
    sp["read_no_extra"] = nb["read"]; sp["sales_no_extra"] = nb["sales"]
    sp.to_csv(RES / "spike.csv", index=False)
    after = sp[sp.day > 0]
    sp_res = {"usual": 0.3, "extra_on_day": 15,
              "rank_day_before": int(sp.loc[sp.day == -1, "rank"].iloc[0]),
              "rank_on_day": int(sp.loc[sp.day == 0, "rank"].iloc[0]),
              "read_on_day": float(sp.loc[sp.day == 0, "read"].iloc[0]),
              "sales_on_day": int(sp.loc[sp.day == 0, "sales"].iloc[0]),
              "read_day_after": float(sp.loc[sp.day == 1, "read"].iloc[0]),
              "sales_day_after": int(sp.loc[sp.day == 1, "sales"].iloc[0]),
              "read_sum_days1to14": round(float(after[after.day <= 14].read.sum()), 2),
              "sales_sum_days1to14": int(after[after.day <= 14].sales.sum()),
              "read_sum_days1to14_no_extra": round(float(nb[(nb.day > 0) & (nb.day <= 14)].read.sum()), 2),
              "sales_sum_days1to14_no_extra": int(nb[(nb.day > 0) & (nb.day <= 14)].sales.sum())}

    # 置き方を変えると（順位の決まりの半減の日数 × 本ごとの売れ方の散らばり、9通り）
    grid = []
    for half in [1.0, 2.0, 5.0]:
        for sig in [1.2, 1.6, 2.0]:
            k = int(half * 10 + sig * 100)
            la, xa, ra, _ = simulate(np.random.default_rng(SEED * 100 + k), sig, half, 40, 28)
            tb = make_table(xa, ra, edges)
            lb, xb, rb, _ = simulate(np.random.default_rng(SEED * 100 + k + 1), sig, half, 40, 28)
            ev = evaluate(lb, xb, rb, tb, edges).set_index("band")
            for nm in BAND_NAMES[1:4]:
                g = ev.loc[nm]
                grid.append({"half_life_days": half, "spread": sig, "band": nm,
                             "share_zero_day": g.share_zero_day,
                             "day_within2_of_day": g.day_within2_of_day,
                             "day_within2_of_usual": g.day_within2_of_usual,
                             "week_within2_of_usual": g.week_within2_of_usual})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gr = {}
    for nm in BAND_NAMES[1:4]:
        g = grid[grid.band == nm]
        gr[nm] = {c: [float(g[c].min()), float(g[c].max())] for c in
                  ["share_zero_day", "day_within2_of_day", "day_within2_of_usual", "week_within2_of_usual"]}
        gr[nm]["week_usual_better_than_day_usual_count"] = int((g.week_within2_of_usual > g.day_within2_of_usual).sum())
        gr[nm]["week_usual_better_than_day_day_count"] = int((g.week_within2_of_usual > g.day_within2_of_day).sum())

    out = {"setup": {"books": N_BOOK, "usual_median_per_day": round(float(np.exp(MU)), 4), "spread_log": 1.6,
                     "half_life_days": 2.0, "burn_in_days": 60, "days_measured": 60},
           "bands_base": base.to_dict("records"), "rank_spots": spot, "spike": sp_res, "grid_range": gr,
           "store_total_per_day_mean": round(float(xB.sum(1).mean()), 1),
           "books_with_sale_per_day_mean": round(float((xB > 0).sum(1).mean()), 1),
           "last_day_books_with_sale": int((xB[-1] > 0).sum()),
           "last_day_zero_share_below_that": round(float((xB[-1][rB[-1] > (xB[-1] > 0).sum()] == 0).mean()) * 100, 2)}
    json.dump(out, open(RES / "a1245_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：順位とその日の冊数（1日分）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    jit = np.random.default_rng(SEED + 3).uniform(-0.18, 0.18, N_BOOK)
    ax.scatter(rB[-1], xB[-1] + jit, s=4, color=BLUE, alpha=.3, lw=0, label="本ごとのその日の冊数（重なりを少しずらした）")
    mid = np.sqrt(edges[:-1] * np.maximum(edges[1:] - 1, edges[:-1]))
    ax.plot(mid, tab, color=ORANGE, lw=2, label="順位から読む冊数（換算表）")
    ax.set_xscale("log"); ax.set_yscale("symlog", linthresh=1)
    ax.set_xlabel("その日の順位（対数の目盛り）"); ax.set_ylabel("その日に売れた冊数")
    ax.set_ylim(-0.3, None)
    ax.set_yticks([0, 1, 2, 5, 10, 20]); ax.set_yticklabels(["0", "1", "2", "5", "10", "20"])
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_xticks([1, 10, 100, 1000, 10000]); ax.set_xticklabels(["1", "10", "100", "1,000", "10,000"])
    nsold = int((xB[-1] > 0).sum())
    ax.axvline(nsold, color=GRAY, lw=1, ls="--")
    zsh = (xB[-1][rB[-1] > nsold] == 0).mean() * 100
    ax.set_title(f"この日1冊でも売れた本は{nsold:,}冊。それより下の順位の{zsh:.2f}%はその日0冊", fontsize=12)
    save(fig, "a1245_scatter.png", SRC)

    # 図2：帯ごとの当たり（1日分と7日分）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    yy = np.arange(len(base))[::-1]
    ax.barh(yy + 0.2, base.day_within2_of_day, 0.38, color=GRAY, label="1日分の順位で、その日の冊数の2倍以内")
    ax.barh(yy - 0.2, base.week_within2_of_usual, 0.38, color=BLUE, label="7日分の順位で、ふだんの売れ方の2倍以内")
    for y, v1, v2 in zip(yy, base.day_within2_of_day, base.week_within2_of_usual):
        ax.text(v1 + 1, y + 0.2, f"{v1:.2f}%", va="center", fontsize=8.5)
        ax.text(v2 + 1, y - 0.2, f"{v2:.2f}%", va="center", fontsize=8.5)
    ax.set_yticks(yy); ax.set_yticklabels(base.band)
    ax.set_xlim(0, 100); ax.set_xlabel("順位から読んだ冊数が2倍以内に入った割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("1,001〜10,000位では、その日の冊数はほぼ読めず、7日の売れ方は半分ほど", fontsize=12)
    save(fig, "a1245_bands.png", SRC)

    # 図3：1日だけ多く売れた本
    s2 = sp[(sp.day >= -5) & (sp.day <= 20)]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(s2.day, s2.sales, color=LIGHT, label="その日に売れた冊数")
    ax.plot(s2.day, s2.read, color=ORANGE, marker="o", ms=3, lw=1.5, label="順位から読む冊数")
    ax.plot(s2.day, s2.read_no_extra, color=GRAY, lw=1, ls=":", label="上乗せがなかったときの、順位から読む冊数")
    ax.axhline(0.3, color=GRAY, lw=1, ls="--"); ax.text(-5.8, 0.33, "ふだん0.3冊", color=GRAY, fontsize=8.5, va="bottom")
    ax.set_yscale("symlog", linthresh=1); ax.set_ylim(0, 30)
    ax.set_yticks([0, 0.5, 1, 2, 5, 10, 20]); ax.set_yticklabels(["0", "0.5", "1", "2", "5", "10", "20"])
    ax.set_xlabel("多く売れた日からの日数"); ax.set_ylabel("冊数")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("1日だけ15冊多く売れると、順位はその後も数日「売れている」と読める")
    save(fig, "a1245_spike.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
