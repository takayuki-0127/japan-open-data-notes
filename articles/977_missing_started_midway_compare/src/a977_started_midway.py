"""977 途中から測り始めた項目は、前の期間とどう比べるのか？（架空のデータ）

架空のチェーン20店の24か月。全部の件数（会計の件数）は1か月目から記録しているが、
「持ち帰りの件数」は13か月目から記録を始めた。記録は大きい店から順に始め（13か月目に5店、その後毎月3店ずつ、18か月目に全店）、
各店の記録の最初の3か月は記録漏れがある（記録される割合 60%・80%・95%、4か月目から100%）。
本当の持ち帰りの割合は作成者が置く（大きい店ほど少し高く、毎月0.2ポイントずつ上がる）。

(1) 記録を始めてからの見かけの伸びを、4つの読み方で本当の伸びと比べる。
(2) 1年目（記録なし）と2年目の前年比を、割合で1年目を戻す2つのやり方で見積もり、本当の前年比と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 977
SRC = "架空のチェーン20店の会計と持ち帰りの件数（作成者が乱数で作成、seed 977）"
S, T = 20, 24
START = 13
BASE = dict(shape="直線", ramp=True, order="大きい店から", size_eff=0.03, first=5, step=3)
SHAPES = {"一定": (0.0, 0.0), "直線": (0.002, 0.002), "2年目だけ伸びる": (0.0, 0.004), "1年目だけ伸びる": (0.004, 0.0)}
RAMP = [0.60, 0.80, 0.95]
REPS = 200


def make_chain(rng, shape, ramp, order, size_eff, first=5, step=3):
    size = np.exp(rng.normal(0, 0.4, S))
    zs = (np.log(size) - np.log(size).mean()) / np.log(size).std()
    if order == "大きい店から":
        rank = np.argsort(-(np.log(size) + rng.normal(0, 0.1, S)))
    else:
        rank = rng.permutation(S)
    start = np.empty(S, int)
    for i, s in enumerate(rank):
        start[s] = START + (0 if i < first else int(np.ceil((i - first + 1) / step)))
    month = np.arange(1, T + 1)
    r1, r2 = SHAPES[shape]
    path = np.where(month <= 12, r1 * (month - 1), r1 * 11 + r2 * (month - 12))  # 1年目の傾き r1、2年目の傾き r2（ポイント／月）
    share = 0.30 + size_eff * zs[:, None] + path[None, :]
    trans = rng.poisson(3000 * size[:, None] * np.ones((1, T)))
    take = rng.binomial(trans, np.clip(share, 0.01, 0.99))
    k = month[None, :] - start[:, None]          # 記録を始めてから何か月目か（0が最初の月）
    frac = np.where(k < 0, 0.0, 1.0)
    if ramp:
        for j, f in enumerate(RAMP):
            frac = np.where(k == j, f, frac)
    rec = np.where(k >= 0, rng.binomial(take, frac), -1)  # −1 は記録なし
    return dict(size=size, start=start, trans=trans, take=take, rec=rec, k=k)


def analyse(c):
    trans, take, rec, k = c["trans"], c["take"], c["rec"], c["k"]
    on = rec >= 0
    clean = k >= len(RAMP)
    m = {}
    m["true_total"] = take.sum(0).astype(float)
    m["true_share"] = take.sum(0) / trans.sum(0)
    m["a_total"] = np.where(on, rec, 0).sum(0).astype(float)
    n_on = on.sum(0)
    m["b_per_store"] = np.where(n_on > 0, m["a_total"] / np.maximum(n_on, 1), np.nan)
    m["c_share_rec"] = np.where(n_on > 0, m["a_total"] / np.maximum(np.where(on, trans, 0).sum(0), 1), np.nan)
    cn = clean.sum(0)
    m["d_share_clean"] = np.where(cn > 0, np.where(clean, rec, 0).sum(0) / np.maximum(np.where(clean, trans, 0).sum(0), 1), np.nan)
    m["n_on"] = n_on.astype(float)
    first5 = c["start"] == START
    m["e_share_first5"] = np.where(clean[first5].all(0), rec[first5].sum(0) / trans[first5].sum(0), np.nan)
    m["true_share_first5"] = take[first5].sum(0) / trans[first5].sum(0)

    # 前年比（1〜12か月目 と 13〜24か月目）
    y1 = slice(0, 12); y2 = slice(12, 24)
    true_g = take[:, y2].sum() / take[:, y1].sum() - 1
    trans_g = trans[:, y2].sum() / trans[:, y1].sum() - 1
    # やり方1：割合は一定と置く。記録漏れのない店月の割合で、それ以外の店月（1年目を含む）を埋める
    s1 = rec[clean].sum() / trans[clean].sum()
    y2_hat1 = rec[:, y2][clean[:, y2]].sum() + trans[:, y2][~clean[:, y2]].sum() * s1
    y1_hat1 = trans[:, y1].sum() * s1
    # やり方2：割合は直線で動くと置く。記録漏れのない店月で、店ごとの水準と共通の傾きを求め、1年目へ伸ばす
    month = np.arange(1, T + 1)[None, :] * np.ones((S, 1))
    w = np.where(clean, trans, 0).astype(float)
    y = np.where(clean, rec / np.maximum(trans, 1), 0.0)
    ws = w.sum(1)
    has = ws > 0
    tbar = np.where(has, (w * month).sum(1) / np.where(has, ws, 1), 0)
    ybar = np.where(has, (w * y).sum(1) / np.where(has, ws, 1), 0)
    dt = (month - tbar[:, None]) * (w > 0)
    slope = (w * dt * (y - ybar[:, None])).sum() / (w * dt ** 2).sum()
    sh2 = ybar[:, None] + slope * (month - tbar[:, None])
    y2_hat2 = rec[:, y2][clean[:, y2]].sum() + (trans * sh2)[:, y2][~clean[:, y2]].sum()
    y1_hat2 = (trans * sh2)[:, y1].sum()
    g = dict(true=true_g, m1=y2_hat1 / y1_hat1 - 1, m2=y2_hat2 / y1_hat2 - 1, trans=trans_g,
             share_y1=take[:, y1].sum() / trans[:, y1].sum(), s1=s1, slope=slope)
    return m, g


def window_change(series, a, b):
    return series[b - 1] / series[a - 1] - 1


def main():
    t0 = time.time()
    res = {"setting": {"stores": S, "months": T, "record_start_month": START, "base": BASE, "ramp_fracs": RAMP,
                       "mean_trans_per_store_month": 3000, "store_size_lognormal_sd": 0.4,
                       "share": "0.30 + size_eff×（店の大きさの標準化）+ 動き方（1年目の傾き・2年目の傾き、ポイント／月）", "shapes": SHAPES, "REPS": REPS}}

    # 例の1回分
    c = make_chain(np.random.default_rng(SEED), **BASE)
    rows = []
    for s in range(S):
        for t in range(T):
            rows.append({"store_id": s + 1, "month": t + 1, "store_size": round(float(c["size"][s]), 3),
                         "record_start_month": int(c["start"][s]), "transactions": int(c["trans"][s, t]),
                         "takeaway_true": int(c["take"][s, t]),
                         "takeaway_recorded": (int(c["rec"][s, t]) if c["rec"][s, t] >= 0 else None)})
    ex = pd.DataFrame(rows)
    ex["takeaway_recorded"] = ex["takeaway_recorded"].astype("Int64")
    ex.to_csv(DATA / "chain_example.csv", index=False)
    res["example"] = {"stores_by_start_month": {str(m): int((c["start"] == m).sum()) for m in sorted(set(c["start"]))}}

    # (1)(2) 基本の置き方（200回）
    ms, gs = [], []
    for r in range(REPS):
        m, g = analyse(make_chain(np.random.default_rng(SEED * 100 + r), **BASE))
        ms.append(m); gs.append(g)
    keys = ["true_total", "true_share", "a_total", "b_per_store", "c_share_rec", "d_share_clean", "n_on", "e_share_first5", "true_share_first5"]
    mon = pd.DataFrame({"month": np.arange(1, T + 1)})
    for kk in keys:
        mon[kk] = np.nanmean(np.array([m[kk] for m in ms]), 0)
    mon.round(5).to_csv(RES / "monthly_base.csv", index=False)

    def ch(kk, a, b):
        v = np.array([window_change(m[kk], a, b) for m in ms])
        return round(float(np.mean(v)) * 100, 2)
    first_clean = START + len(RAMP)
    win = pd.DataFrame([
        {"reading": "(a) 記録された件数の合計", "from": START, "to": T, "seen_pct": ch("a_total", START, T), "true_pct": ch("true_total", START, T)},
        {"reading": "(b) 記録した店の1店あたり", "from": START, "to": T, "seen_pct": ch("b_per_store", START, T), "true_pct": ch("true_total", START, T)},
        {"reading": "(c) 記録した店の持ち帰りの割合", "from": START, "to": T, "seen_pct": ch("c_share_rec", START, T), "true_pct": ch("true_share", START, T)},
        {"reading": "(d) (c)から記録の最初の3か月を除く", "from": first_clean, "to": T, "seen_pct": ch("d_share_clean", first_clean, T), "true_pct": ch("true_share", first_clean, T)},
        {"reading": "(e) 13か月目から記録している5店だけ（記録漏れのない16か月目から）", "from": first_clean, "to": T, "seen_pct": ch("e_share_first5", first_clean, T), "true_pct": ch("true_share", first_clean, T)},
        {"reading": "(c) 全店がそろった18か月目から", "from": 18, "to": T, "seen_pct": ch("c_share_rec", 18, T), "true_pct": ch("true_share", 18, T)},
        {"reading": "(d) 全店がそろい記録漏れもない21か月目から", "from": 21, "to": T, "seen_pct": ch("d_share_clean", 21, T), "true_pct": ch("true_share", 21, T)},
    ])
    win["gap_pt"] = (win.seen_pct - win.true_pct).round(2)
    win.to_csv(RES / "readings_base.csv", index=False)
    res["readings_base"] = win.to_dict("records")
    res["e_true_first5_16_24_pct"] = ch("true_share_first5", first_clean, T)
    res["share_level_base"] = {"true_m13": round(float(mon.true_share[START - 1]) * 100, 2),
                               "c_m13": round(float(mon.c_share_rec[START - 1]) * 100, 2),
                               "d_m16": round(float(mon.d_share_clean[first_clean - 1]) * 100, 2),
                               "true_m16": round(float(mon.true_share[first_clean - 1]) * 100, 2),
                               "true_m24": round(float(mon.true_share[T - 1]) * 100, 2),
                               "c_m24": round(float(mon.c_share_rec[T - 1]) * 100, 2)}

    G = pd.DataFrame(gs)
    res["yoy_base"] = {"true_pct": round(G.true.mean() * 100, 2),
                       "m1_pct": round(G.m1.mean() * 100, 2), "m2_pct": round(G.m2.mean() * 100, 2),
                       "trans_pct": round(G.trans.mean() * 100, 2),
                       "m1_p10_p90": [round(G.m1.quantile(.1) * 100, 2), round(G.m1.quantile(.9) * 100, 2)],
                       "m2_p10_p90": [round(G.m2.quantile(.1) * 100, 2), round(G.m2.quantile(.9) * 100, 2)],
                       "true_p10_p90": [round(G.true.quantile(.1) * 100, 2), round(G.true.quantile(.9) * 100, 2)],
                       "share_y1_true": round(G.share_y1.mean() * 100, 2), "s1": round(G.s1.mean() * 100, 2),
                       "m1_gap_pt": round((G.m1 - G.true).mean() * 100, 2), "m2_gap_pt": round((G.m2 - G.true).mean() * 100, 2),
                       "slope_pt_per_month": round(G.slope.mean() * 100, 3),
                       "slope_p10_p90": [round(G.slope.quantile(.1) * 100, 3), round(G.slope.quantile(.9) * 100, 3)]}

    # (3) 確かめ：割合の伸び × 記録漏れ × 始める順 × 店の大きさの効き（各50回）
    grid = []
    gi = 0
    for shape in SHAPES:
        for ramp in [False, True]:
            for order in ["大きい店から", "でたらめ"]:
                for se in [0.0, 0.03]:
                    gi += 1
                    mm, gg = [], []
                    for r in range(50):
                        m, g = analyse(make_chain(np.random.default_rng(SEED * 7 + gi * 1000 + r), shape, ramp, order, se))
                        mm.append(m); gg.append(g)
                    gg = pd.DataFrame(gg)
                    grid.append({"shape": shape, "ramp": "あり" if ramp else "なし", "order": order,
                                 "size_eff": se,
                                 "a_seen_13_24_pct": round(float(np.mean([window_change(m["a_total"], START, T) for m in mm])) * 100, 1),
                                 "c_seen_13_24_pt_vs_true": round(float(np.mean([window_change(m["c_share_rec"], START, T) - window_change(m["true_share"], START, T) for m in mm])) * 100, 2),
                                 "true_yoy_pct": round(gg.true.mean() * 100, 2), "m1_yoy_pct": round(gg.m1.mean() * 100, 2),
                                 "m2_yoy_pct": round(gg.m2.mean() * 100, 2), "trans_yoy_pct": round(gg.trans.mean() * 100, 2),
                                 "m2_p10": round(gg.m2.quantile(.1) * 100, 2), "m2_p90": round(gg.m2.quantile(.9) * 100, 2)})
    grid = pd.DataFrame(grid)
    grid["m1_gap_pt"] = (grid.m1_yoy_pct - grid.true_yoy_pct).round(2)
    grid["m2_gap_pt"] = (grid.m2_yoy_pct - grid.true_yoy_pct).round(2)
    grid.to_csv(RES / "robustness.csv", index=False)
    by = {}
    for sh, v in grid.groupby("shape", sort=False):
        by[sh] = {"true_yoy": [float(v.true_yoy_pct.min()), float(v.true_yoy_pct.max())],
                  "m1_gap": [float(v.m1_gap_pt.min()), float(v.m1_gap_pt.max())],
                  "m2_gap": [float(v.m2_gap_pt.min()), float(v.m2_gap_pt.max())],
                  "m2_p10_p90_widest": [float(v.m2_p10.min()), float(v.m2_p90.max())]}
    res["robust"] = {
        "n_cases": int(len(grid)),
        "a_seen_range": [float(grid.a_seen_13_24_pct.min()), float(grid.a_seen_13_24_pct.max())],
        "c_gap_range": [float(grid.c_seen_13_24_pt_vs_true.min()), float(grid.c_seen_13_24_pt_vs_true.max())],
        "c_gap_noramp_random_nosize_absmax": float(grid[(grid.ramp == "なし") & (grid.order == "でたらめ") & (grid.size_eff == 0)].c_seen_13_24_pt_vs_true.abs().max()),
        "c_gap_ramp_range": [float(grid[grid.ramp == "あり"].c_seen_13_24_pt_vs_true.min()), float(grid[grid.ramp == "あり"].c_seen_13_24_pt_vs_true.max())],
        "by_shape": by,
        "m1_minus_trans_absmax": float((grid.m1_yoy_pct - grid.trans_yoy_pct).abs().max()),
        "both_methods_gap_range": [float(min(grid.m1_gap_pt.min(), grid.m2_gap_pt.min())),
                                   float(max(grid.m1_gap_pt.max(), grid.m2_gap_pt.max()))],
    }
    with open(RES / "a977_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：月ごとの持ち帰りの件数（記録された合計と本当）
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    ax.plot(mon.month, mon.true_total / 1000, color=GRAY, lw=2.5, label="本当の持ち帰りの件数（全店）")
    mm_ = mon.month >= START
    ax.plot(mon.month[mm_], mon.a_total[mm_] / 1000, "o-", color=ORANGE, ms=4, label="記録された件数の合計")
    ax.axvspan(0.5, START - .5, color=LIGHT, alpha=.25, lw=0)
    ax.text(6.5, mon.true_total.max() / 1000 * 0.45, "1〜12か月目は\n記録なし（空欄）", ha="center", fontsize=9.5)
    for t in range(START, 19):
        ax.text(t + 0.3, mon.a_total[t - 1] / 1000 - 0.6, f"{int(round(mon.n_on[t-1]))}店", ha="left", va="top", fontsize=7.5, color=ORANGE)
    ax.set_xlabel("月"); ax.set_ylabel("持ち帰りの件数（千件）"); ax.set_xticks([1, 6, 12, 13, 18, 24])
    ax.set_ylim(0, mon.true_total.max() / 1000 * 1.15)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("記録を始めた店が増えるあいだ、合計は本当より大きく伸びて見える", fontsize=12)
    save(fig, "a977_monthly_total.png", SRC + "。200回の平均。オレンジの数字は記録している店の数")

    # 図2：持ち帰りの割合（記録のある店で割る・最初の3か月を除く・本当）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(mon.month, mon.true_share * 100, color=GRAY, lw=2.5, label="本当の持ち帰りの割合（全店）")
    ax.plot(mon.month, mon.c_share_rec * 100, "o-", color=ORANGE, ms=4, label="(c) 記録した店の割合")
    ax.plot(mon.month, mon.d_share_clean * 100, "s-", color=BLUE, ms=4, label="(d) 記録の最初の3か月を除く")
    ax.axvspan(0.5, START - .5, color=LIGHT, alpha=.25, lw=0)
    ax.set_xlabel("月"); ax.set_ylabel("持ち帰り÷会計の件数（%）"); ax.set_xticks([1, 6, 12, 13, 16, 18, 24])
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("割合にすると店の数の増え方は消えるが、記録漏れと店の顔ぶれのずれが残る", fontsize=11.5)
    save(fig, "a977_share_readings.png", SRC + "。200回の平均")

    # 図3：前年比の見積もりの、本当とのずれ（割合の動き方ごと）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    shapes = list(SHAPES)
    for i, sh in enumerate(shapes):
        g = grid[grid["shape"] == sh]
        ax.scatter(np.full(len(g), i) - 0.14, g.m1_gap_pt, color=ORANGE, marker="o", s=24, alpha=.75,
                   label="やり方1：割合は一定と置いて戻す" if i == 0 else None)
        ax.scatter(np.full(len(g), i) + 0.14, g.m2_gap_pt, color=BLUE, marker="^", s=28, alpha=.75,
                   label="やり方2：割合は直線で動くと置いて戻す" if i == 0 else None)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(range(len(shapes)))
    ax.set_xticklabels(["一定", "直線\n（0.2ポイント／月）", "2年目だけ伸びる\n（0.4ポイント／月）", "1年目だけ伸びる\n（0.4ポイント／月）"], fontsize=9.5)
    ax.set_xlabel("本当の持ち帰りの割合の動き方（記録のない1年目を含む）")
    ax.set_ylabel("見積もった前年比 − 本当の前年比（ポイント）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("前年比の当たり外れは、記録のない1年目の割合をどう置いたかで決まる\n（各点は記録漏れ・始める順・店の大きさの効きの8通り、各50回の平均）", fontsize=11.5)
    save(fig, "a977_yoy_gap.png", SRC, y=-0.07)

    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
