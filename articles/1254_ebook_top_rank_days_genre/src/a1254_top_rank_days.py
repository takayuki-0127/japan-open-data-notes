"""1254 「売れ筋の何位以内」に入った日数で本を比べると、分野ごとの競争の違いで何がずれるのか？（架空のデータ）

架空の電子書籍の販売の場。分野A〜Dの4つ。本ごとに「本当の1日の売れ方（平均の冊数）」を作成者が置き、
1日に売れた冊数はその平均の数のまわりで乱数で振れる。順位の決まりは作成者が置いたもので、
分野の中で直近3日に売れた冊数の合計の多い順（同じならでたらめ）。90日のうち分野の20位以内に入った日数を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1254
SRC = "架空の電子書籍の販売の順位（作成者が乱数で作成、seed 1254）"
GENRES = ["A", "B", "C", "D"]
BASE = {"sizes": [200, 1000, 3000, 1000], "medians": [0.5, 0.5, 0.5, 1.5], "k": 20}
SD = 1.0          # 本ごとの売れ方の散らばり（対数の標準偏差）
DAYS = 90
W = 3             # 順位に使う直近の日数
TOPN = 50         # 全体で比べる上位の冊数
PROBE_LAMS = [1, 2, 3, 5, 8, 12, 20]


def make_world(rng, sizes, medians):
    g = np.concatenate([np.full(n, i) for i, n in enumerate(sizes)])
    med = np.array(medians)[g]
    lam = med * np.exp(rng.normal(0, SD, g.size))
    sales = rng.poisson(lam[:, None], (g.size, DAYS + W - 1))
    csum = np.cumsum(np.pad(sales, ((0, 0), (1, 0))), axis=1)
    roll = csum[:, W:] - csum[:, :-W]          # 直近3日の合計（90日分）
    score = roll + rng.random(roll.shape)      # 同じ合計はでたらめに並べる
    return g, lam, sales[:, W - 1:], roll, score


def days_in_top(score, idx, k):
    """idx の本だけで順位を付け、上位 k に入った日数"""
    s = score[idx]
    k = min(k, len(idx))
    thr = -np.sort(-s, axis=0)[k - 1]
    return (s >= thr).sum(1)


def measures(g, score, sizes, k):
    n = g.size
    d_genre = np.zeros(n, int)
    d_pct = np.zeros(n, int)
    for i, sz in enumerate(sizes):
        idx = np.where(g == i)[0]
        d_genre[idx] = days_in_top(score, idx, k)
        d_pct[idx] = days_in_top(score, idx, max(1, int(np.ceil(sz * k / 1000))))
    d_all = days_in_top(score, np.arange(n), k * len(sizes))
    return d_genre, d_pct, d_all


def rank_corr(a, b):
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


def top_set(x, rng, n=TOPN):
    return np.argsort(-(x + rng.random(x.size) * 0.5))[:n]


def thresholds(g, score, roll, lam, sizes, k):
    out = []
    for i, sz in enumerate(sizes):
        idx = np.where(g == i)[0]
        s = roll[idx]
        kth = -np.sort(-s, axis=0)[k - 1]
        out.append({"genre": GENRES[i], "books": sz,
                    "needed_per_day_median": round(float(np.median(kth)) / W, 2),
                    "true_kth_lambda": round(float(-np.sort(-lam[idx])[k - 1]), 3),
                    "books_all_days_in_top": int((days_in_top(score, idx, k) == DAYS).sum()),
                    "books_zero_days": int((days_in_top(score, idx, k) == 0).sum())})
    return out


def probe(rng, g, score, sizes, k, lams, n_probe=400):
    """本当の売れ方が lam の本を1冊ずつ分野に足したとき、上位 k に入った日数"""
    rows = []
    for i, sz in enumerate(sizes):
        idx = np.where(g == i)[0]
        srt = np.sort(score[idx], axis=0)          # 昇順
        kk = min(k, sz + 1)
        for L in lams:
            s = rng.poisson(L, (n_probe, DAYS + W - 1))
            cs = np.cumsum(np.pad(s, ((0, 0), (1, 0))), axis=1)
            ps = (cs[:, W:] - cs[:, :-W]) + rng.random((n_probe, DAYS))
            above = np.stack([sz - np.searchsorted(srt[:, d], ps[:, d]) for d in range(DAYS)], 1)
            days = ((above + 1) <= kk).sum(1)
            rows.append({"genre": GENRES[i], "true_per_day": L, "days_mean": round(float(days.mean()), 2),
                         "days_p10": float(np.percentile(days, 10)), "days_p90": float(np.percentile(days, 90))})
    return rows


def compare(rng, sizes, medians, k, reps):
    res = {m: {"corr": [], "hit": [], "share": []} for m in ["genre", "pct", "all"]}
    true_share = []
    for r in range(reps):
        g, lam, sales, roll, score = make_world(rng, sizes, medians)
        dg, dp, da = measures(g, score, sizes, k)
        tt = set(np.argsort(-lam)[:TOPN])
        true_share.append(np.bincount(g[list(tt)], minlength=4) / TOPN)
        for m, d in [("genre", dg), ("pct", dp), ("all", da)]:
            ts = top_set(d.astype(float), rng)
            res[m]["corr"].append(rank_corr(d, lam))
            res[m]["hit"].append(len(tt & set(ts)) / TOPN)
            res[m]["share"].append(np.bincount(g[ts], minlength=4) / TOPN)
    out = {"true_share": np.mean(true_share, 0)}
    for m in res:
        out[m] = {"corr": float(np.mean(res[m]["corr"])), "hit": float(np.mean(res[m]["hit"])),
                  "share": np.mean(res[m]["share"], 0)}
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    sizes, medians, k = BASE["sizes"], BASE["medians"], BASE["k"]

    # 1) 1回分の場：データと分野ごとの境目
    g, lam, sales, roll, score = make_world(rng, sizes, medians)
    dg, dp, da = measures(g, score, sizes, k)
    df = pd.DataFrame({"book_id": np.arange(1, g.size + 1), "genre": np.array(GENRES)[g],
                       "true_per_day": lam.round(4), "sold_90days": sales.sum(1),
                       "days_top20_genre": dg, "days_top2pct_genre": dp, "days_top80_all": da})
    df.to_csv(DATA / "books_example.csv", index=False)
    thr = thresholds(g, score, roll, lam, sizes, k)
    pd.DataFrame(thr).to_csv(RES / "genre_threshold.csv", index=False)

    # 例：分野の20位以内に90日すべて入った本の本当の売れ方
    ex = []
    for i in range(4):
        sel = df[(df.genre == GENRES[i]) & (df.days_top20_genre == DAYS)]
        ex.append({"genre": GENRES[i], "books_90days": len(sel),
                   "true_per_day_min": round(float(sel.true_per_day.min()), 3) if len(sel) else None,
                   "true_per_day_median": round(float(sel.true_per_day.median()), 3) if len(sel) else None})
    # 同じ売れ方 2〜4冊/日の本の日数（1回分）
    band = df[df.true_per_day.between(2, 4)].groupby("genre").days_top20_genre.agg(["count", "mean"]).round(2)

    # 2) 同じ売れ方の本を分野ごとに足したとき
    pr = pd.DataFrame(probe(rng, g, score, sizes, k, PROBE_LAMS))
    pr.to_csv(RES / "probe_days.csv", index=False)

    # 3) 全部の本を日数で比べる（場を作り直して50回）
    cmpb = compare(rng, sizes, medians, k, 50)
    names = {"genre": "分野の20位以内の日数", "pct": "分野の上位2%以内の日数", "all": "全体の80位以内の日数"}
    rows = [{"measure": "本当の売れ方（作成者が置いた値）", "rank_corr": 1.0, "top50_hit": 1.0,
             **{f"share_{x}": round(float(v), 4) for x, v in zip(GENRES, cmpb["true_share"])}}]
    for m in ["genre", "pct", "all"]:
        rows.append({"measure": names[m], "rank_corr": round(cmpb[m]["corr"], 4), "top50_hit": round(cmpb[m]["hit"], 4),
                     **{f"share_{x}": round(float(v), 4) for x, v in zip(GENRES, cmpb[m]["share"])}})
    comp = pd.DataFrame(rows)
    comp.to_csv(RES / "measure_compare.csv", index=False)

    # 4) 確かめ：分野Aの本の数・分野Dの売れ方の中央値・何位以内（k）の27通り
    grid = []
    gi = 0
    for nA in [50, 200, 1000]:
        for mD in [0.5, 1.5, 4.5]:
            for kk in [10, 20, 50]:
                r2 = np.random.default_rng(SEED * 100 + gi)
                gi += 1
                sz = [nA, 1000, 3000, 1000]
                md = [0.5, 0.5, 0.5, mD]
                c = compare(r2, sz, md, kk, 10)
                gg, ll, ss, rr, sc = make_world(r2, sz, md)
                p = pd.DataFrame(probe(r2, gg, sc, sz, kk, [3], 200))
                grid.append({"books_A": nA, "median_D": mD, "k": kk,
                             "probe3_days_A": float(p[p.genre == "A"].days_mean.iloc[0]),
                             "probe3_days_C": float(p[p.genre == "C"].days_mean.iloc[0]),
                             "probe3_days_D": float(p[p.genre == "D"].days_mean.iloc[0]),
                             "genre_hit": round(c["genre"]["hit"], 4), "all_hit": round(c["all"]["hit"], 4),
                             "pct_hit": round(c["pct"]["hit"], 4),
                             "genre_corr": round(c["genre"]["corr"], 4), "all_corr": round(c["all"]["corr"], 4),
                             "true_share_A": round(float(c["true_share"][0]), 4),
                             "genre_share_A": round(float(c["genre"]["share"][0]), 4),
                             "true_share_D": round(float(c["true_share"][3]), 4),
                             "genre_share_D": round(float(c["genre"]["share"][3]), 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    main_json = {
        "base": {"genres": GENRES, **BASE, "sd_log": SD, "days": DAYS, "window": W, "topn": TOPN},
        "threshold": thr, "all_days_example": ex,
        "threshold_D_over_A": round(thr[3]["needed_per_day_median"] / thr[0]["needed_per_day_median"], 2),
        "band_2to4_example": {i: {"count": int(band.loc[i, "count"]), "mean_days": float(band.loc[i, "mean"])} for i in band.index},
        "probe": pr.to_dict("records"),
        "compare": comp.to_dict("records"),
        "grid_range": {
            "genre_hit": [float(grid.genre_hit.min()), float(grid.genre_hit.max())],
            "all_hit": [float(grid.all_hit.min()), float(grid.all_hit.max())],
            "pct_hit": [float(grid.pct_hit.min()), float(grid.pct_hit.max())],
            "all_hit_minus_genre_hit": [round(float((grid.all_hit - grid.genre_hit).min()), 4), round(float((grid.all_hit - grid.genre_hit).max()), 4)],
            "probe3_days_A": [float(grid.probe3_days_A.min()), float(grid.probe3_days_A.max())],
            "probe3_days_C": [float(grid.probe3_days_C.min()), float(grid.probe3_days_C.max())],
            "probe3_days_D": [float(grid.probe3_days_D.min()), float(grid.probe3_days_D.max())],
            "true_share_A": [float(grid.true_share_A.min()), float(grid.true_share_A.max())],
            "genre_share_A": [float(grid.genre_share_A.min()), float(grid.genre_share_A.max())],
            "n_genre_share_A_above_true": int((grid.genre_share_A > grid.true_share_A).sum()),
            "n_all_beats_genre": int((grid.all_hit > grid.genre_hit).sum()),
            "not_beats": grid[grid.all_hit <= grid.genre_hit][["books_A", "median_D", "k", "genre_hit", "all_hit"]].to_dict("records"),
        },
    }

    # 図1：分野ごとの、20位以内に入るのに要る1日の冊数
    fig, ax = plt.subplots(figsize=(7, 4))
    t = pd.DataFrame(thr)
    lab = [f"分野{x}\n（{n:,}冊）" for x, n in zip(t.genre, t.books)]
    b = ax.bar(lab, t.needed_per_day_median, color=[BLUE, BLUE, BLUE, ORANGE])
    for bb, v in zip(b, t.needed_per_day_median):
        ax.text(bb.get_x() + bb.get_width() / 2, v + 0.15, f"{v:g}冊", ha="center", va="bottom")
    ax.set_ylim(0, t.needed_per_day_median.max() * 1.18)
    ax.set_ylabel("20位の本の1日あたりの冊数（90日の中央値）")
    ax.set_title("分野の20位以内に入るのに要る売れ方（1回分の場）")
    save(fig, "a1254_threshold.png", SRC + "。分野Dは売れ方の中央値を3倍に置いた")

    # 図2：同じ売れ方の本が20位以内に入った日数
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for x, c, mk in zip(GENRES, [GREEN, BLUE, GRAY, ORANGE], ["o", "s", "^", "D"]):
        s = pr[pr.genre == x]
        ax.plot(s.true_per_day, s.days_mean, marker=mk, color=c, label=f"分野{x}")
    ax.set_xscale("log")
    ax.set_xticks(PROBE_LAMS)
    ax.set_xticklabels([str(v) for v in PROBE_LAMS])
    ax.set_ylim(0, 92)
    ax.set_xlabel("本当の1日の売れ方（冊、対数の目盛り）")
    ax.set_ylabel("90日のうち20位以内の日数（平均）")
    ax.set_title("同じ売れ方の本でも、分野で日数が違う")
    ax.legend(frameon=False)
    save(fig, "a1254_probe.png", SRC + "。各点400冊の平均")

    # 図3：日数の上位50冊の分野の内訳
    fig, ax = plt.subplots(figsize=(7.5, 4))
    lbl = ["本当の売れ方の\n上位50冊", "分野の20位以内\nの日数", "分野の上位2%\nの日数", "全体の80位以内\nの日数"]
    left = np.zeros(4)
    for x, c in zip(GENRES, [GREEN, BLUE, GRAY, ORANGE]):
        v = (comp[f"share_{x}"].to_numpy() * 100).round(2)
        ax.barh(lbl, v, left=left, color=c, label=f"分野{x}")
        for j in range(4):
            if v[j] >= 6:
                ax.text(left[j] + v[j] / 2, j, f"{v[j]:.2f}%", ha="center", va="center", color="white", fontsize=9)
        left += v
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("上位50冊に占める割合（%、50回の平均）")
    ax.set_title("並べた上位50冊は、どの分野の本か")
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    save(fig, "a1254_top50_share.png", SRC, y=-0.12)

    with open(RES / "a1254_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1, default=float)
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
