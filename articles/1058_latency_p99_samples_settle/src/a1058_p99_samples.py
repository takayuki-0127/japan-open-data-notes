"""1058 99パーセンタイルの応答時間は、何件測れば落ち着くのか？（架空のデータ）

架空のサーバーの応答時間（ミリ秒）。ふだんの処理（97%）と、まれに通る遅い処理（3%）の混ざりを作成者が置く。
本当の99パーセンタイル（p99）は置いた分布の式から求める。n件測ってp99を出すことを何回もくり返し、
「9割の回で本当の値の±10%に入る」（作成者が置いた物差し）のに何件要るかを数える。
遅い処理がかたまって来る（混む1分間がある）と、続けて測ったn件ではどうなるかも数える。
実機の計測はしていない。すべて作成者が置いた分布からの乱数。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import binom
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1058
SRC = "架空のサーバーの応答時間（作成者が置いた分布からの乱数、seed 1058）"
BASE = {"fast_median_ms": 40.0, "fast_sigma": 0.35, "slow_median_ms": 250.0, "slow_sigma": 0.5, "slow_share": 0.03}
SIZES = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000]
TRIALS = 2000
TOL = 0.10      # ±10%（作成者が置いた物差し）
COVER = 0.90    # 9割の回（作成者が置いた物差し）
RPS = 20        # 1秒あたりの件数（混む1分間のモデル）


def r(x, d=4):
    return round(float(x), d)


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def mix_cdf(x, kw):
    if x <= 0:
        return 0.0
    f = ncdf(math.log(x / kw["fast_median_ms"]) / kw["fast_sigma"])
    s = ncdf(math.log(x / kw["slow_median_ms"]) / kw["slow_sigma"])
    return (1 - kw["slow_share"]) * f + kw["slow_share"] * s


def mix_q(p, kw):
    lo, hi = 1e-3, 1e6
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if mix_cdf(mid, kw) < p:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def draw(rng, shape, slow_share, kw):
    slow = rng.random(shape) < slow_share
    z = rng.standard_normal(shape)
    return np.where(slow, kw["slow_median_ms"] * np.exp(kw["slow_sigma"] * z),
                    kw["fast_median_ms"] * np.exp(kw["fast_sigma"] * z))


def formula_cover(n, p, kw, tol=TOL):
    """上からの順位で取る p 分位（nearest rank：k=ceil(n p) 番目）が真の値の±tol に入る確率（二項分布の式）"""
    q = mix_q(p, kw)
    k = math.ceil(n * p)
    f_hi, f_lo = mix_cdf(q * (1 + tol), kw), mix_cdf(q * (1 - tol), kw)
    # X_(k) <= x ⇔ x以下の件数 >= k
    return float(binom.sf(k - 1, n, f_hi) - binom.sf(k - 1, n, f_lo))


def n_needed(p, kw, tol=TOL, cover=COVER, nmax=2_000_000):
    """式で、それより大きい n（約2%刻みで調べる）でもずっと cover 以上になる最小の n"""
    ns = np.unique(np.round(np.exp(np.arange(np.log(20), np.log(nmax), 0.02))).astype(int))
    ok = np.array([formula_cover(int(n), p, kw, tol) >= cover for n in ns])
    if ok[-1] == False:
        return None
    bad = np.where(~ok)[0]
    return int(ns[bad[-1] + 1]) if len(bad) else int(ns[0])


def sim_independent(rng, n, trials, kw, true99):
    out_lin, out_nr = [], []
    left = trials
    while left > 0:
        b = min(left, max(1, 4_000_000 // n))
        x = draw(rng, (b, n), kw["slow_share"], kw)
        out_lin.append(np.quantile(x, 0.99, axis=1))
        out_nr.append(np.quantile(x, 0.99, axis=1, method="inverted_cdf"))
        left -= b
    lin, nr = np.concatenate(out_lin), np.concatenate(out_nr)
    return lin, nr


def sim_burst(rng, n, trials, kw, p_busy, busy_min, normal_share):
    """混む時間（長さ busy_min 分）がでたらめに入る。続けて n 件測る。全体の遅い割合は slow_share と同じになるように置く"""
    busy_share = (kw["slow_share"] - (1 - p_busy) * normal_share) / p_busy
    per_block = RPS * 60 * busy_min      # 1区切りの件数
    out = []
    left = trials
    while left > 0:
        b = min(left, max(1, 4_000_000 // n))
        nblk = n // per_block + 2
        busy = rng.random((b, nblk)) < p_busy
        off = rng.integers(0, per_block, b)
        idx = (off[:, None] + np.arange(n)[None, :]) // per_block
        state = np.take_along_axis(busy, idx, axis=1)
        share = np.where(state, busy_share, normal_share)
        slow = rng.random((b, n)) < share
        z = rng.standard_normal((b, n))
        x = np.where(slow, kw["slow_median_ms"] * np.exp(kw["slow_sigma"] * z),
                     kw["fast_median_ms"] * np.exp(kw["fast_sigma"] * z))
        out.append(np.quantile(x, 0.99, axis=1))
        left -= b
    return np.concatenate(out), busy_share


def summarize(v, true):
    rel = v / true - 1
    return {"median_ms": r(np.median(v), 2), "p05_ms": r(np.quantile(v, .05), 2), "p95_ms": r(np.quantile(v, .95), 2),
            "within10_share": r((np.abs(rel) <= TOL).mean()), "mean_rel_bias_pct": r(rel.mean() * 100, 2),
            "below_true_share": r((v < true).mean())}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    kw = BASE
    true = {p: mix_q(p, kw) for p in [0.5, 0.9, 0.99, 0.999]}
    true99 = true[0.99]
    mean_true = (1 - kw["slow_share"]) * kw["fast_median_ms"] * math.exp(kw["fast_sigma"] ** 2 / 2) + \
        kw["slow_share"] * kw["slow_median_ms"] * math.exp(kw["slow_sigma"] ** 2 / 2)

    # 1回分のデータ（1,000件）
    one = draw(np.random.default_rng(SEED + 1), 1000, kw["slow_share"], kw)
    pd.DataFrame({"request_id": np.arange(1, 1001), "ms": np.round(one, 3)}).to_csv(DATA / "requests_1000.csv", index=False)

    # 1) 独立に測るとき：件数ごとの p99 の散らばり
    rows = []
    for n in SIZES:
        lin, nr = sim_independent(rng, n, TRIALS, kw, true99)
        s = summarize(lin, true99)
        s2 = summarize(nr, true99)
        rows.append({"n": n, "tail_count": r(n * 0.01, 1), **{f"lin_{k}": v for k, v in s.items()},
                     "nr_within10_share": s2["within10_share"], "nr_median_ms": s2["median_ms"],
                     "formula_nr_within10": r(formula_cover(n, 0.99, kw))})
    ind = pd.DataFrame(rows)
    ind.to_csv(RES / "p99_by_n_independent.csv", index=False)
    max_gap_formula = float((ind.nr_within10_share - ind.formula_nr_within10).abs().max())

    # 2) 分位ごとに要る件数（式、nearest rank）
    need = []
    for p in [0.5, 0.9, 0.99, 0.999]:
        nn = n_needed(p, kw)
        need.append({"p": p, "true_ms": r(true[p], 2), "n_needed": nn, "tail_count_at_needed": r(nn * (1 - p), 1)})
    need = pd.DataFrame(need)
    need.to_csv(RES / "n_needed_by_percentile.csv", index=False)
    n99 = int(need.loc[need.p == 0.99, "n_needed"].iloc[0])

    # 3) 置き方を変えると（式）：遅い処理の割合 × 遅い処理の散らばり × 物差しの幅
    grid = []
    for ss in [0.015, 0.03, 0.06]:
        for sg in [0.3, 0.5, 0.8]:
            for tol in [0.05, 0.10, 0.20]:
                k2 = dict(kw, slow_share=ss, slow_sigma=sg)
                nn = n_needed(0.99, k2, tol)
                grid.append({"slow_share": ss, "slow_sigma": sg, "tol": tol, "true_p99_ms": r(mix_q(0.99, k2), 2),
                             "n_needed": nn, "tail_count_at_needed": r(nn * 0.01, 1)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_formula.csv", index=False)
    g10 = grid[grid.tol == 0.10]

    def ratio(t):
        a = grid[grid.tol == t].n_needed.values
        return a / g10.n_needed.values

    # 4) 遅い処理がかたまって来るとき：続けて n 件測る
    BURST_SIZES = [1000, 5000, 20000, 100000]
    burst_rows = []
    for bm in [1, 5]:
        for pb in [0.05, 0.10, 0.20]:
            for n in BURST_SIZES:
                tr = 400 if n < 100000 else 200
                v, bsh = sim_burst(rng, n, tr, kw, pb, bm, 0.01)
                s = summarize(v, true99)
                burst_rows.append({"busy_minutes": bm, "p_busy": pb, "busy_slow_share": r(bsh), "n": n,
                                   "minutes_measured": r(n / RPS / 60, 2), "trials": tr, **s})
    burst = pd.DataFrame(burst_rows)
    burst.to_csv(RES / "p99_by_n_burst.csv", index=False)
    bbase = burst[(burst.busy_minutes == 1) & (burst.p_busy == 0.10)]

    def bw(n, df=bbase):
        return float(df.loc[df.n == n, "within10_share"].iloc[0])

    def iw(n):
        return float(ind.loc[ind.n == n, "lin_within10_share"].iloc[0])

    n_tail = need.set_index("p")
    out = {"base_setting": BASE, "sizes": SIZES, "trials": TRIALS, "tol": TOL, "cover": COVER, "rps_burst_model": RPS,
           "true_ms": {str(p): r(v, 3) for p, v in true.items()}, "true_mean_ms": r(mean_true, 3),
           "independent": ind.to_dict("records"),
           "formula_vs_sim_max_gap_nearest_rank": r(max_gap_formula),
           "lin_vs_nr_within10_max_gap": r((ind.lin_within10_share - ind.nr_within10_share).abs().max()),
           "formula_nr_within10_n100000": r(formula_cover(100000, 0.99, kw)),
           "grid_ratio_tol05_over_tol10": [r(v, 2) for v in [ratio(0.05).min(), ratio(0.05).max()]],
           "grid_ratio_tol20_over_tol10": [r(v, 3) for v in [ratio(0.20).min(), ratio(0.20).max()]],
           "n_needed_by_percentile": need.to_dict("records"),
           "grid_tol10_n_needed_range": [int(g10.n_needed.min()), int(g10.n_needed.max())],
           "grid_tol10_tail_count_range": [r(g10.tail_count_at_needed.min(), 1), r(g10.tail_count_at_needed.max(), 1)],
           "grid_all_n_needed_range": [int(grid.n_needed.min()), int(grid.n_needed.max())],
           "burst_base": bbase.to_dict("records"),
           "burst_all_within10_at_20000_range": [r(burst[burst.n == 20000].within10_share.min()),
                                                 r(burst[burst.n == 20000].within10_share.max())],
           "burst_all_within10_at_100000_range": [r(burst[burst.n == 100000].within10_share.min()),
                                                  r(burst[burst.n == 100000].within10_share.max())],
           "headline": {"true_p99_ms": r(true99, 1), "true_p50_ms": r(true[0.5], 1), "true_mean_ms": r(mean_true, 1),
                        "n100_within10_pct": r(iw(100) * 100, 1),
                        "n100_p05_p95_ms": [r(ind.lin_p05_ms[0], 1), r(ind.lin_p95_ms[0], 1)],
                        "n1000_within10_pct": r(iw(1000) * 100, 1),
                        "n_needed_p99": n99, "tail_count_p99": r(n99 * 0.01, 1),
                        "n_needed_p999": int(n_tail.loc[0.999, "n_needed"]),
                        "n_needed_p50": int(n_tail.loc[0.5, "n_needed"]),
                        "grid_tol10_n_needed_range": [int(g10.n_needed.min()), int(g10.n_needed.max())],
                        "burst_n20000_within10_pct": r(bw(20000) * 100, 1),
                        "indep_n20000_within10_pct": r(iw(20000) * 100, 1),
                        "burst_n100000_within10_pct": r(bw(100000) * 100, 1),
                        "burst_n1000_within10_pct": r(bw(1000) * 100, 1)},
           }
    json.dump(out, open(RES / "a1058_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：件数ごとのp99の散らばり（独立に測るとき）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    x = ind.n.values
    ax.fill_between(x, ind.lin_p05_ms, ind.lin_p95_ms, color=LIGHT, alpha=.8, label="測り直したときの5〜95%の範囲")
    ax.plot(x, ind.lin_median_ms, color=BLUE, marker="o", ms=4, label="中央値")
    ax.axhline(true99, color=INK, lw=1)
    ax.axhspan(true99 * (1 - TOL), true99 * (1 + TOL), color=ORANGE, alpha=.12, label="本当の値の±10%")
    ax.text(x[-1], true99 * 1.015, f"本当のp99 {true99:.1f}ms", ha="right", va="bottom", fontsize=9)
    ax.set_xscale("log"); ax.set_ylim(0, None)
    ax.set_xlabel("測った件数（対数の目盛り）"); ax.set_ylabel("測ったp99（ms）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", bbox_to_anchor=(1, 0.93))
    ax.set_title("件数が少ないと、測ったp99は大きく振れる（独立に測る、各2,000回）")
    save(fig, "a1058_spread.png", SRC)

    # 図2：±10%に入る割合（独立 対 かたまって来る、続けて測る）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ns = BURST_SIZES
    w = 0.38
    pos = np.arange(len(ns))
    v1 = [iw(n) * 100 if n in SIZES else np.nan for n in ns]
    # 独立の 100000 は式で補う
    v1 = [v if not np.isnan(v) else formula_cover(n, 0.99, kw) * 100 for v, n in zip(v1, ns)]
    v2 = [bw(n) * 100 for n in ns]
    ax.bar(pos - w / 2, v1, w, color=BLUE, label="1件ずつ独立に測る（10万件は式）")
    ax.bar(pos + w / 2, v2, w, color=ORANGE, label="遅い処理がかたまって来る中で、続けて測る")
    for i in range(len(ns)):
        ax.text(pos[i] - w / 2, v1[i] + 1.5, f"{v1[i]:.0f}%", ha="center", fontsize=8.5)
        ax.text(pos[i] + w / 2, v2[i] + 1.5, f"{v2[i]:.0f}%", ha="center", fontsize=8.5)
    ax.axhline(90, color=GRAY, ls="--", lw=1); ax.text(len(ns) - .5, 91, "9割", color=GRAY, fontsize=8.5, ha="right")
    ax.set_xticks(pos, [f"{n:,}件\n（{n / RPS / 60:.1f}分）" for n in ns])
    ax.set_ylim(0, 110); ax.set_ylabel("本当のp99の±10%に入った割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("混む1分間がでたらめに来ると、続けて2万件測っても落ち着かない")
    save(fig, "a1058_burst.png", SRC)

    # 図3：分位ごとに要る件数と、その上側の件数
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    lab = ["p50（中央値）", "p90", "p99", "p99.9"]
    ax.barh(lab[::-1], need.n_needed[::-1], color=[GRAY, GRAY, BLUE, GRAY][::-1])
    for i, (nn, tc) in enumerate(zip(need.n_needed[::-1], need.tail_count_at_needed[::-1])):
        ax.text(nn + need.n_needed.max() * 0.015, i, f"{nn:,}件（上側に{tc:,.1f}件）", va="center", fontsize=9)
    ax.set_xlim(0, need.n_needed.max() * 1.45)
    ax.set_xlabel("9割の回で±10%に入るのに要る件数（式）")
    ax.set_title(f"中央値は{need.n_needed[0]:,}件で落ち着くが、p99には{n99:,}件要った")
    save(fig, "a1058_need.png", SRC)
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
