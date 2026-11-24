"""1155 同じものを大勢が同時に取りに来ると、置き場所から消えた瞬間に、元のデータへ何件の問い合わせが流れるのか？（架空のデータ）

作成者が置いた架空のアプリの、よく使われる1件のデータ。手元の置き場所（キャッシュ）に60秒置き、消えたら元のデータを取りに行く。
問い合わせはでたらめな間隔で平均1秒に1,000件（1msに1件）来る。元のデータを取りに行く時間は中央値80ms・対数の標準偏差0.5（対数で正規の形）。
置き場所が空のあいだに来た問い合わせは、どれも元のデータを取りに行く（まとめない）。いずれか1件が戻った時点で置き場所が埋まる。
(1) 基本：元のデータが何件でも同時にさばける（遅くならない）とき、消えた1回あたり元のデータへ何件流れるかを2,000回数える
(2) 元のデータが同時にさばける数 c を置き、それを超えると1件あたりの進みが c÷（同時の件数）に落ちるとき（各500回）
(3) 取りに行く時間が毎回同じなら 1＋来る速さ×時間 の式どおりになることの確かめ
(4) 確かめ：問い合わせの多さ×取りに行く時間×さばける数の27通り（各40回、3,000件で打ち切り）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1155
SRC = "架空のアプリの問い合わせ（作成者が置いた来かたと取りに行く時間からの乱数、seed 1155）"
LAM = 1.0            # 1msあたりの問い合わせ（1秒に1,000件）
MED, SIG = 80.0, 0.5  # 元のデータを取りに行く時間（ms）
HOLD_S = 60           # 置いておく時間（秒）
N_BASE = 2000
N_CAP = 500
CAPS = [np.inf, 60, 40, 20, 15, 10, 7, 5]
G_LAM = [0.2, 1.0, 5.0]
G_MED = [20.0, 80.0, 300.0]
G_CAP = [np.inf, 60, 20]
N_GRID = 40
CUT = 3000


def r(x, d=4):
    return round(float(x), d)


def one_expiry(rng, lam, med, sig, c, cut):
    """消えた1回ぶん。戻り値：元のデータへの件数、埋まった時刻(ms)、打ち切りか、来た時刻、最初の1件の取りに行く時間"""
    works = rng.lognormal(np.log(med), sig, cut)
    gaps = rng.exponential(1.0 / lam, cut)
    rem = np.empty(cut)
    rem[0] = works[0]
    n, t = 1, 0.0
    na = gaps[0]
    arr = [0.0]
    while True:
        rate = 1.0 if n <= c else c / n
        tc = t + rem[:n].min() / rate
        if na < tc:
            if n == cut:
                return n, na, True, np.array(arr), works[0]
            rem[:n] -= rate * (na - t)
            t = na
            rem[n] = works[n]
            arr.append(na)
            n += 1
            na = t + gaps[n - 1]
        else:
            return n, tc, False, np.array(arr), works[0]


def ln_mean(med, sig):
    return med * np.exp(sig ** 2 / 2)


def cname(c):
    return "無制限" if np.isinf(c) else f"{int(c)}件"


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    ew = ln_mean(MED, SIG)
    out = {"setting": {"requests_per_ms": LAM, "requests_per_s": LAM * 1000, "fetch_median_ms": MED,
                       "fetch_logsd": SIG, "fetch_mean_ms": r(ew), "hold_s": HOLD_S,
                       "requests_per_hold": int(LAM * 1000 * HOLD_S), "repeats_base": N_BASE,
                       "repeats_cap": N_CAP}}

    # (1)(2) さばける数ごと
    rows, drow = [], []
    for c in CAPS:
        reps = N_BASE if np.isinf(c) else N_CAP
        cnt, fill, first100, wait_n, wait_ms, trunc = [], [], [], [], [], 0
        for i in range(reps):
            n, tf, tr, arr, w0 = one_expiry(rng, LAM, MED, SIG, c, 20000)
            trunc += tr
            cnt.append(n)
            fill.append(tf)
            first100.append(int((arr < 100).sum()))
            if np.isinf(c):
                # まとめる場合：最初の1件だけが取りに行き、それが戻るまでに来た分は待つ（別の乱数で数える）
                w1 = rng.lognormal(np.log(MED), SIG)
                ca = rng.exponential(1.0 / LAM, 4000).cumsum()
                ca = ca[ca < w1]
                wait_n.append(len(ca))
                if len(ca):
                    wait_ms.append(float((w1 - ca).mean()))
            drow.append({"origin_capacity": cname(c), "expiry_id": i + 1, "origin_requests": n,
                         "filled_ms": r(tf, 3)})
        cnt, fill = np.array(cnt), np.array(fill)
        row = {"origin_capacity": cname(c), "repeats": reps,
               "in_flight_per_capacity": None if np.isinf(c) else r(LAM * ew / c, 2), "mean": r(cnt.mean(), 2),
               "median": r(np.median(cnt), 1), "p90": r(np.quantile(cnt, 0.9), 1),
               "p99": r(np.quantile(cnt, 0.99), 1), "max": int(cnt.max()), "min": int(cnt.min()),
               "fill_ms_mean": r(fill.mean(), 2), "fill_ms_median": r(np.median(fill), 2),
               "truncated": int(trunc),
               "hit_rate_pct": r((1 - cnt.mean() / (LAM * 1000 * HOLD_S)) * 100, 3),
               "origin_per_s_avg": r(cnt.mean() / HOLD_S, 3),
               "origin_per_s_first100ms": r(np.mean(first100) * 10, 1),
               "ratio_mean_vs_unlimited": None}
        rows.append(row)
        if np.isinf(c):
            out["base"] = dict(row)
            out["base"]["guide_formula_1_plus_lam_mean"] = r(1 + LAM * ew, 2)
            out["base"]["share_ge_100_pct"] = r((cnt >= 100).mean() * 100, 2)
            out["base"]["share_ge_150_pct"] = r((cnt >= 150).mean() * 100, 2)
            out["coalesce"] = {"origin_requests": 1, "waiting_mean": r(np.mean(wait_n), 2),
                               "waiting_median": r(np.median(wait_n), 1),
                               "wait_ms_mean": r(np.mean(wait_ms), 2)}
            hist = cnt
    # 確かめ：取りに行く時間が毎回同じ（平均と同じ値）なら、目安の式どおりになるか
    cc = np.array([one_expiry(rng, LAM, ew, 0.0, np.inf, 20000)[0] for _ in range(N_BASE)])
    out["constant_fetch_check"] = {"fetch_ms": r(ew, 2), "mean": r(cc.mean(), 2), "formula": r(1 + LAM * ew, 2)}
    tb = pd.DataFrame(rows)
    base_mean = tb.iloc[0]["mean"]
    tb["ratio_mean_vs_unlimited"] = (tb["mean"] / base_mean).round(3)
    tb.to_csv(RES / "by_capacity.csv", index=False)
    out["by_capacity"] = tb.to_dict("records")
    out["peak_vs_avg_ratio"] = r(out["base"]["origin_per_s_first100ms"] / out["base"]["origin_per_s_avg"], 1)
    pd.DataFrame(drow).to_csv(DATA / "expiries.csv", index=False)

    # (3) 確かめ
    gr = []
    for lam in G_LAM:
        for med in G_MED:
            for c in G_CAP:
                cnt, tr = [], 0
                for _ in range(N_GRID):
                    n, tf, t_, arr, w0 = one_expiry(rng, lam, med, SIG, c, CUT)
                    cnt.append(n)
                    tr += t_
                cnt = np.array(cnt)
                gr.append({"requests_per_s": int(lam * 1000), "fetch_median_ms": med,
                           "origin_capacity": cname(c),
                           "in_flight_guide": r(lam * ln_mean(med, SIG), 2),
                           "guide_formula": r(1 + lam * ln_mean(med, SIG), 2),
                           "in_flight_per_capacity": None if np.isinf(c) else r(lam * ln_mean(med, SIG) / c, 2),
                           "mean": r(cnt.mean(), 2), "median": r(np.median(cnt), 1),
                           "truncated_of_40": int(tr),
                           "ratio_to_guide": r(cnt.mean() / (1 + lam * ln_mean(med, SIG)), 3)})
    gr = pd.DataFrame(gr)
    gr.to_csv(RES / "grid.csv", index=False)
    gu = gr[gr.origin_capacity == "無制限"]
    gc = gr[gr.origin_capacity != "無制限"]
    over = gc[gc.in_flight_guide > gc.origin_capacity.str.replace("件", "").astype(float)]
    under = gc[gc.in_flight_guide <= gc.origin_capacity.str.replace("件", "").astype(float)]
    out["grid"] = {"n": len(gr),
                   "unlimited_ratio_range": [float(gu.ratio_to_guide.min()), float(gu.ratio_to_guide.max())],
                   "unlimited_mean_range": [float(gu["mean"].min()), float(gu["mean"].max())],
                   "capped_over_n": len(over), "capped_over_truncated_cells": int((over.truncated_of_40 > 0).sum()),
                   "capped_over_ratio_min": float(over.ratio_to_guide.min()) if len(over) else None,
                   "capped_over_list": over[["requests_per_s", "fetch_median_ms", "origin_capacity",
                                             "in_flight_per_capacity", "mean", "truncated_of_40"]].to_dict("records"),
                   "capped_ratio_le10": [float(gc[gc.in_flight_per_capacity <= 10].ratio_to_guide.min()),
                                         float(gc[gc.in_flight_per_capacity <= 10].ratio_to_guide.max())],
                   "capped_le10_n": int((gc.in_flight_per_capacity <= 10).sum()),
                   "capped_le10_truncated": int(gc[gc.in_flight_per_capacity <= 10].truncated_of_40.sum()),
                   "capped_gt10_n": int((gc.in_flight_per_capacity > 10).sum()),
                   "capped_gt10_mean_min": float(gc[gc.in_flight_per_capacity > 10]["mean"].min()),
                   "capped_gt10_truncated_range": [int(gc[gc.in_flight_per_capacity > 10].truncated_of_40.min()),
                                                   int(gc[gc.in_flight_per_capacity > 10].truncated_of_40.max())],
                   "capped_under_n": len(under),
                   "capped_under_ratio_range": [float(under.ratio_to_guide.min()), float(under.ratio_to_guide.max())]
                   if len(under) else None}

    # 図1：基本の分布
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bins = np.arange(0, hist.max() + 6, 5)
    ax.hist(hist, bins=bins, color=BLUE)
    g = out["base"]["guide_formula_1_plus_lam_mean"]
    ax.axvline(g, color=ORANGE, lw=1.2, ls="--")
    ax.text(g - 2, ax.get_ylim()[1] * 0.92, f"目安の式（取りに行く時間が\n毎回同じなら）{g}件", color=ORANGE,
            fontsize=9, va="top", ha="right")
    ax.set_xlabel("消えた1回あたり、元のデータへ流れた問い合わせ（件）")
    ax.set_ylabel("回数（2,000回のうち）")
    ax.set_title(f"消えた瞬間の流れ込み（1秒に1,000件・平均{out['base']['mean']}件）")
    save(fig, "a1155_burst.png", SRC)

    # 図2：さばける数ごと
    fig, ax = plt.subplots(figsize=(7, 4.2))
    names = ["無制限"] + [f"{int(c)}件" for c in CAPS[1:]]
    vals = tb["mean"].tolist()
    cols = [BLUE] + [ORANGE] * (len(vals) - 1)
    ax.bar(range(len(vals)), vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.015, f"{v:,}", ha="center", fontsize=8.5)
    ax.set_xticks(range(len(vals)), names)
    ax.set_ylim(0, max(vals) * 1.15)
    tr5 = int(tb.iloc[-1]["truncated"])
    ax.text(len(vals) - 1.5, max(vals) * 1.09, f"5件は500回のうち{tr5}回を2万件で打ち切り（平均は少なめに出る）",
            fontsize=8.5, color=GRAY, ha="right")
    ax.set_xlabel("元のデータが同時にさばける数（超えると1件ずつ遅くなる）")
    ax.set_ylabel("消えた1回あたりの平均（件）")
    ax.set_title("さばける数が少ないほど流れ込みが増えた（各500回、無制限は2,000回）")
    save(fig, "a1155_capacity.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7, 4.4))
    mk = {"無制限": ("o", BLUE), "60件": ("s", GREEN), "20件": ("^", ORANGE)}
    for k, (m, col) in mk.items():
        s = gr[gr.origin_capacity == k]
        ax.scatter(s.guide_formula, s["mean"], marker=m, color=col, s=36,
                   label=f"さばける数 {k}", zorder=3)
    lo, hi = 1, CUT * 1.6
    ax.plot([lo, hi], [lo, hi], color=GRAY, lw=0.8, ls="--", label="目安の式と同じ")
    ax.axhline(CUT, color=GRAY, lw=0.8, ls=":")
    ax.text(1.3, CUT * 1.08, f"{CUT:,}件で打ち切り", fontsize=8.5, color=GRAY)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1, hi)
    ax.set_ylim(1, hi)
    tk = [1, 10, 100, 1000]
    ax.set_xticks(tk, [f"{x:,}" for x in tk])
    ax.set_yticks(tk, [f"{x:,}" for x in tk])
    ax.set_xlabel("目安の式 1＋来る速さ×取りに行く時間の平均（件）")
    ax.set_ylabel("乱数で数えた平均（件）")
    ax.set_title("置き方を変えた27通り（各40回）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    save(fig, "a1155_grid.png", SRC)

    out["run_sec"] = r(time.time() - t0, 1)
    (RES / "a1155_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                    ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:9000])
    print(gr.to_string())


if __name__ == "__main__":
    main()
