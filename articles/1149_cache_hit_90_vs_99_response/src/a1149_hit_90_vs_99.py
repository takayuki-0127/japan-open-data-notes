"""1149 当たり率90%と99%の差は、平均の応答時間で何倍の差になるのか？（架空のデータ）

作成者が置いた架空のアプリへの問い合わせ。手元の置き場所（キャッシュ）に当たれば速く、外れれば元のデータを取りに行って遅い。
当たったときの時間：中央値2ms・対数の標準偏差0.3、外れたときの時間：中央値80ms・対数の標準偏差0.5（どちらも対数で正規の形）。
(1) 当たり率ごとの平均の応答時間を式（当たり率×当たりの平均＋外れ率×外れの平均）で出し、乱数100万件で照らす
(2) 当たり率90%と99%で、平均・中央値・90%点・95%点・99%点・元のデータへの問い合わせ件数を比べる
(3) 確かめ：外れたときの遅さ（当たりの平均の何倍か）×元のデータの混み具合の置き方を変え、90%と99%の平均の比を式で出す
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK

SEED = 1149
SRC = "架空のアプリへの問い合わせ（作成者が置いた当たり・外れの時間の分布からの乱数、seed 1149）"
HIT_MED, HIT_SIG = 2.0, 0.3
MISS_MED, MISS_SIG = 80.0, 0.5
N = 1_000_000
RATES = [0.80, 0.85, 0.90, 0.95, 0.97, 0.98, 0.99, 0.995, 0.999]
CURVE = np.round(np.arange(0.80, 0.9991, 0.001), 3)
RATIOS = [5, 10, 30, 100, 300, 1000]
BUSY = [0.0, 0.3, 0.6, 0.9]      # 当たり率90%のときの元のデータの混み具合
QS = [0.5, 0.9, 0.95, 0.99]
QNAME = {0.5: "中央値", 0.9: "90%点", 0.95: "95%点", 0.99: "99%点"}


def r(x, d=4):
    return round(float(x), d)


def ln_mean(med, sig):
    return med * np.exp(sig ** 2 / 2)


def draw(rng, n, h):
    hit = rng.random(n) < h
    t = np.where(hit, rng.lognormal(np.log(HIT_MED), HIT_SIG, n), rng.lognormal(np.log(MISS_MED), MISS_SIG, n))
    return t, hit


def ratio_formula(R, h1=0.90, h2=0.99):
    """当たりの平均を1、外れの平均をRとしたときの 平均(h1)÷平均(h2)"""
    return (h1 + (1 - h1) * R) / (h2 + (1 - h2) * R)


def ratio_busy(R, rho90, h1=0.90, h2=0.99):
    """元のデータの混み具合が外れの件数に比例し、外れの時間が 1÷(1−混み具合) 倍になると置いたとき"""
    rho99 = rho90 * (1 - h2) / (1 - h1)
    m1 = h1 + (1 - h1) * R / (1 - rho90)
    m2 = h2 + (1 - h2) * R / (1 - rho99)
    return m1 / m2


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    mh, mm = ln_mean(HIT_MED, HIT_SIG), ln_mean(MISS_MED, MISS_SIG)
    out = {"setting": {"hit_median_ms": HIT_MED, "hit_logsd": HIT_SIG, "miss_median_ms": MISS_MED,
                       "miss_logsd": MISS_SIG, "hit_mean_ms": r(mh), "miss_mean_ms": r(mm),
                       "miss_over_hit": r(mm / mh), "requests": N}}

    # (1)(2) 当たり率ごと
    rows, keep = [], {}
    for h in RATES:
        t, hit = draw(rng, N, h)
        row = {"hit_rate_pct": r(h * 100, 2), "mean_formula_ms": r(h * mh + (1 - h) * mm),
               "mean_sim_ms": r(t.mean()), "hit_share_sim_pct": r(hit.mean() * 100, 3),
               "origin_per_1000": r((1 - h) * 1000, 2), "origin_sim_per_1000": r((~hit).mean() * 1000, 2)}
        for q in QS:
            row[f"p{int(q * 100)}_ms"] = r(np.quantile(t, q))
        rows.append(row)
        if h in (0.90, 0.99):
            keep[h] = (t, hit)
    rt = pd.DataFrame(rows)
    rt.to_csv(RES / "by_hit_rate.csv", index=False)
    out["by_hit_rate"] = rt.to_dict("records")

    a, b = rt[rt.hit_rate_pct == 90.0].iloc[0], rt[rt.hit_rate_pct == 99.0].iloc[0]
    comp = [{"measure": "当たり率", "at90": 90.0, "at99": 99.0, "ratio_90_over_99": r(90 / 99, 2)},
            {"measure": "外れ率（%）", "at90": 10.0, "at99": 1.0, "ratio_90_over_99": 10.0},
            {"measure": "元のデータへの問い合わせ（1,000件あたり）", "at90": a.origin_sim_per_1000,
             "at99": b.origin_sim_per_1000, "ratio_90_over_99": r(a.origin_sim_per_1000 / b.origin_sim_per_1000, 2)},
            {"measure": "平均（式）", "at90": a.mean_formula_ms, "at99": b.mean_formula_ms,
             "ratio_90_over_99": r(a.mean_formula_ms / b.mean_formula_ms, 2)},
            {"measure": "平均（乱数）", "at90": a.mean_sim_ms, "at99": b.mean_sim_ms,
             "ratio_90_over_99": r(a.mean_sim_ms / b.mean_sim_ms, 2)}]
    for q in QS:
        k = f"p{int(q * 100)}_ms"
        comp.append({"measure": QNAME[q], "at90": a[k], "at99": b[k], "ratio_90_over_99": r(a[k] / b[k], 2)})
    cp = pd.DataFrame(comp)
    cp.to_csv(RES / "compare_90_99.csv", index=False)
    out["compare_90_99"] = cp.to_dict("records")
    # 外れの分が平均に占める割合
    out["miss_share_of_mean_pct"] = {str(h): r((1 - h) * mm / (h * mh + (1 - h) * mm) * 100, 2) for h in (0.90, 0.99)}
    # 99%点が当たりの中か外れの中か
    t99, hit99 = keep[0.99]
    p99 = np.quantile(t99, 0.99)
    out["at99_p99_detail"] = {"p99_ms": r(p99), "share_slower_than_p99_that_are_miss_pct":
                              r((~hit99[t99 > p99]).mean() * 100, 2),
                              "max_hit_time_ms": r(t99[hit99].max())}

    # 曲線（式）
    cv = pd.DataFrame({"hit_rate_pct": np.round(CURVE * 100, 1),
                       "mean_formula_ms": np.round(CURVE * mh + (1 - CURVE) * mm, 4)})
    cv.to_csv(RES / "curve.csv", index=False)

    # 当たり率を1ポイントずつ上げたときの平均の縮み（式）
    steps = []
    for h in [0.90, 0.95, 0.98, 0.99]:
        m0 = h * mh + (1 - h) * mm
        m1 = (h + 0.01) * mh + (1 - h - 0.01) * mm
        steps.append({"from_pct": r(h * 100, 1), "to_pct": r((h + 0.01) * 100, 1),
                      "mean_from_ms": r(m0), "mean_to_ms": r(m1), "drop_ms": r(m0 - m1), "ratio": r(m0 / m1)})
    out["one_point_steps"] = steps

    # (3) 確かめ（式）
    gr = []
    for R in RATIOS:
        for rho in BUSY:
            gr.append({"miss_over_hit": R, "origin_busy_at90": rho,
                       "origin_busy_at99": r(rho * 0.1, 3), "mean_ratio_90_over_99": r(ratio_busy(R, rho), 2)})
    gr = pd.DataFrame(gr)
    gr.to_csv(RES / "grid.csv", index=False)
    g0 = gr[gr.origin_busy_at90 == 0]
    out["grid"] = {"n": len(gr),
                   "no_busy_range": [float(g0.mean_ratio_90_over_99.min()), float(g0.mean_ratio_90_over_99.max())],
                   "all_range": [float(gr.mean_ratio_90_over_99.min()), float(gr.mean_ratio_90_over_99.max())],
                   "limit_no_busy": 10.0,
                   "base_R_formula": r(ratio_formula(mm / mh), 2),
                   "over10_count": int((gr.mean_ratio_90_over_99 > 10).sum())}

    # データ：各2万件
    d = []
    for h in (0.90, 0.99):
        t, hit = keep[h]
        d.append(pd.DataFrame({"hit_rate_pct": int(round(h * 100)), "request_id": np.arange(1, 20001),
                               "hit": hit[:20000].astype(int), "ms": np.round(t[:20000], 3)}))
    pd.concat(d).to_csv(DATA / "requests_90_99.csv", index=False)

    # 図1：当たり率と平均の応答時間（式）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(cv.hit_rate_pct, cv.mean_formula_ms, color=BLUE)
    for h, col in ((90.0, ORANGE), (99.0, ORANGE)):
        v = rt[rt.hit_rate_pct == h].mean_formula_ms.iloc[0]
        ax.plot([h], [v], "o", color=col)
        ax.text(h - 0.4, v - 0.4, f"{h:g}%：{v}ms", fontsize=9, color=INK, ha="right", va="top")
    ax.set_ylim(0, None)
    ax.set_xlim(80, 100)
    ax.set_xlabel("当たり率（%）")
    ax.set_ylabel("平均の応答時間（ms）")
    ax.set_title("当たり率と平均の応答時間（置いた時間からの式どおり）")
    save(fig, "a1149_curve.png", SRC)

    # 図2：90%÷99%の比（物差しごと）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    names = ["当たり率", "外れ率", "平均", "中央値", "90%点", "95%点", "99%点"]
    cpi = cp.set_index("measure").ratio_90_over_99
    vals = [cpi["当たり率"], cpi["外れ率（%）"], cpi["平均（乱数）"]] + [cpi[QNAME[q]] for q in QS]
    cols = [GRAY, GRAY, BLUE, ORANGE, ORANGE, ORANGE, ORANGE]
    ax.bar(range(len(vals)), vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.4, f"{v:.2f}倍", ha="center", fontsize=9)
    ax.axhline(1, color=GRAY, lw=0.8, ls="--")
    ax.set_xticks(range(len(vals)), names)
    ax.set_ylim(0, max(vals) * 1.15)
    ax.set_ylabel("当たり率90%の値 ÷ 99%の値（倍）")
    ax.set_title("当たり率90%と99%の比（乱数100万件ずつ）")
    save(fig, "a1149_ratios.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for rho, col in zip(BUSY, [BLUE, GRAY, ORANGE, INK]):
        s = gr[gr.origin_busy_at90 == rho]
        ax.plot(s.miss_over_hit, s.mean_ratio_90_over_99, marker="o", ms=4, color=col,
                label=f"当たり率90%のときの元のデータの混み具合 {rho:g}")
    ax.axhline(10, color=GRAY, lw=0.8, ls="--", label="外れ率の比（10倍）")
    ax.set_xscale("log")
    ax.set_xticks(RATIOS, [f"{x:,}" for x in RATIOS])
    ax.set_ylim(0, None)
    ax.set_xlabel("外れたときの平均 ÷ 当たったときの平均（倍）")
    ax.set_ylabel("平均の応答時間 90% ÷ 99%（倍）")
    ax.set_title("置き方を変えた24通り（式）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1149_grid.png", SRC)

    (RES / "a1149_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:7000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
