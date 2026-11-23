"""1063 一定の間隔でのぞく測り方で、遅い場所の順位は入れかわるのか？（架空のデータ）

架空のアプリの処理を、作成者が置いた時間（ミリ秒）の乱数で作る（実機の計測はしない）。
アプリは10msごとのタイマーで1回ずつ動き、5つの部分（読み込み・計算・保存・画面・記録）を順に行い、
残りの時間は待つ。「いま、どの部分を動かしているか」を一定の間隔でのぞいて数え、時間のかかる部分の順位を
決める測り方（のぞき見の計測）で、のぞく間隔によって順位がどれだけ当たるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1063
SRC = "架空のアプリの処理時間（作成者が置いた分布からの乱数、seed 1063）"
NAMES = ["読み込み", "計算", "保存", "画面", "記録"]
MEANS = np.array([1.8, 2.6, 2.4, 1.2, 0.4])   # ms
BASE = {"period": 10.0, "dur_sd": 0.05, "start_sd": 0.02, "length_s": 10.0, "timer": True, "sampler_sd": 0.01}
INTERVALS = [("10ms（処理と同じ）", 10.0), ("20ms", 20.0), ("5ms", 5.0), ("4ms", 4.0), ("1ms", 1.0),
             ("9.7ms（少しずらす）", 9.7), ("でたらめ（平均10ms）", "rand")]
REPS = 500


def r(x, d=4):
    return round(float(x), d)


def program(rng, reps, period, dur_sd, start_sd, length_s, timer, **_):
    """reps 回分の処理の並び。starts, ends：(reps, K*5)、func：部分の番号"""
    L = length_s * 1000
    K = int(L / period) + 2 if timer else int(L / MEANS.sum()) + 40
    dur = MEANS[None, None, :] * np.exp(rng.normal(0, dur_sd, (reps, K, 5)))
    tot = dur.sum(2)
    if timer:
        sched = np.arange(K)[None, :] * period + rng.normal(0, start_sd, (reps, K))
        st = np.empty((reps, K))
        st[:, 0] = sched[:, 0]
        for k in range(1, K):
            st[:, k] = np.maximum(sched[:, k], st[:, k - 1] + tot[:, k - 1])
    else:  # タイマーで動かず、終わったらすぐ次を始める
        st = np.concatenate([np.zeros((reps, 1)), np.cumsum(tot, 1)[:, :-1]], 1)
    s = st[:, :, None] + np.concatenate([np.zeros((reps, K, 1)), np.cumsum(dur, 2)[:, :, :-1]], 2)
    e = s + dur
    return s.reshape(reps, -1), e.reshape(reps, -1), L


def true_share(s, e, L):
    """0〜L の間に各部分が動いていた時間の割合（動いていた時間の合計に対する割合）"""
    d = np.clip(np.minimum(e, L) - np.maximum(s, 0), 0, None)
    reps = s.shape[0]
    by = d.reshape(reps, -1, 5).sum(1)
    return by / by.sum(1, keepdims=True)


def sample(rng, s, e, L, interval, sampler_sd, **_):
    reps = s.shape[0]
    out = np.zeros((reps, 5))
    for i in range(reps):
        if interval == "rand":
            t = np.cumsum(rng.exponential(10.0, int(L / 10.0 * 1.3) + 50)) + rng.uniform(0, 10.0)
        else:
            t = rng.uniform(0, interval) + np.arange(int(L / interval) + 1) * interval + rng.normal(0, sampler_sd, int(L / interval) + 1)
        t = t[(t >= 0) & (t < L)]
        idx = np.searchsorted(s[i], t, side="right") - 1
        ok = (idx >= 0) & (t < e[i][np.clip(idx, 0, None)])
        out[i] = np.bincount(idx[ok] % 5, minlength=5)
    return out


def score(cnt, tru):
    n = cnt.sum(1, keepdims=True)
    sh = np.divide(cnt, n, out=np.zeros_like(cnt), where=n > 0)
    top_true = tru.argmax(1)
    # 同じ数のときは、順位は決まらない（当たりに数えない）
    top_s = sh.argmax(1)
    tie = (sh == sh.max(1, keepdims=True)).sum(1) > 1
    top_ok = (top_s == top_true) & ~tie
    order_ok = np.array([(np.argsort(-a, kind="stable") == np.argsort(-b, kind="stable")).all() and len(set(a)) == 5
                         for a, b in zip(sh, tru)])
    err = np.abs(sh - tru) * 100
    return {"top1_correct": float(top_ok.mean()), "order_correct": float(order_ok.mean()),
            "mean_abs_err_pt": float(err.mean()), "max_abs_err_pt_mean": float(err.max(1).mean()),
            "calc_share_p10": float(np.quantile(sh[:, 1], .1) * 100), "calc_share_p90": float(np.quantile(sh[:, 1], .9) * 100),
            "busy_samples_mean": float(n.mean()), "calc_zero_share": float((sh[:, 1] == 0).mean())}


def evaluate(seed, kw, intervals, reps):
    rng = np.random.default_rng(seed)
    s, e, L = program(rng, reps, **kw)
    tru = true_share(s, e, L)
    res = {}
    for nm, iv in intervals:
        res[nm] = score(sample(rng, s, e, L, iv, **kw), tru)
    return res, tru, (s, e, L)


def main():
    t0 = time.time()
    base, tru, (s, e, L) = evaluate(SEED, BASE, INTERVALS, REPS)
    rows = [{"interval": nm, **{k: r(v, 4) for k, v in m.items()}} for nm, m in base.items()]
    tb = pd.DataFrame(rows)
    tb.to_csv(RES / "by_interval.csv", index=False)
    true_mean = tru.mean(0)
    # タイマーで動かない（続けて回る）処理
    nt, _, _ = evaluate(SEED + 5, dict(BASE, timer=False), [INTERVALS[0], INTERVALS[-1]], REPS)
    # のぞく時間を長くした（でたらめな間隔、60秒）
    lg, _, _ = evaluate(SEED + 6, dict(BASE, length_s=60.0), [INTERVALS[-1]], 200)

    # 確かめ：部分の時間の揺れ × タイマーの揺れ × のぞく長さ（27通り、10ms とでたらめ、各200回）
    grid = []
    j = 0
    for dsd in [0.02, 0.05, 0.2]:
        for ssd in [0.02, 0.2, 2.0]:
            for ln in [2.0, 10.0, 60.0]:
                kw = dict(BASE, dur_sd=dsd, start_sd=ssd, length_s=ln)
                res, _, _ = evaluate(SEED * 100 + j, kw, [INTERVALS[0], INTERVALS[-1]], 200)
                j += 1
                a, b = res[INTERVALS[0][0]], res[INTERVALS[-1][0]]
                grid.append({"dur_sd": dsd, "start_sd_ms": ssd, "length_s": ln,
                             "top1_10ms": r(a["top1_correct"]), "top1_random": r(b["top1_correct"]),
                             "order_10ms": r(a["order_correct"]), "order_random": r(b["order_correct"]),
                             "err_10ms_pt": r(a["mean_abs_err_pt"], 3), "err_random_pt": r(b["mean_abs_err_pt"], 3)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    # data：1回分（10秒）の、10ms でのぞいた記録とでたらめな間隔でのぞいた記録
    rd = np.random.default_rng(SEED + 1)
    s1, e1, L1 = program(rd, 1, **BASE)
    recs = []
    for nm, iv in [("10ms", 10.0), ("random", "rand")]:
        if iv == "rand":
            t = np.cumsum(rd.exponential(10.0, 1400)) + rd.uniform(0, 10.0)
        else:
            t = rd.uniform(0, iv) + np.arange(int(L1 / iv) + 1) * iv + rd.normal(0, BASE["sampler_sd"], int(L1 / iv) + 1)
        t = t[(t >= 0) & (t < L1)]
        idx = np.searchsorted(s1[0], t, side="right") - 1
        ok = (idx >= 0) & (t < e1[0][np.clip(idx, 0, None)])
        part = np.where(ok, np.array(NAMES + ["待ち"])[np.where(ok, idx % 5, 5)], "待ち")
        recs.append(pd.DataFrame({"method": nm, "t_ms": t.round(3), "part": part}))
    pd.concat(recs).to_csv(DATA / "samples_one_run.csv", index=False)

    def B(nm, k):
        return base[nm][k]
    I10, I20, I5, I4, I1, I97, IR = [nm for nm, _ in INTERVALS]
    out = {"base_setting": BASE, "means_ms": dict(zip(NAMES, MEANS.tolist())), "reps": REPS,
           "true_share_mean_pct": {n: r(v * 100, 2) for n, v in zip(NAMES, true_mean)},
           "true_top_is_calc_share": r((tru.argmax(1) == 1).mean()),
           "by_interval": tb.to_dict("records"),
           "headline": {"calc_true_pct": r(true_mean[1] * 100, 2), "save_true_pct": r(true_mean[2] * 100, 2),
                        "gap_calc_save_pt": r((true_mean[1] - true_mean[2]) * 100, 2),
                        "top1_10ms_pct": r(B(I10, "top1_correct") * 100, 2), "order_10ms_pct": r(B(I10, "order_correct") * 100, 2),
                        "err_10ms_pt": r(B(I10, "mean_abs_err_pt"), 2), "calc_zero_10ms_pct": r(B(I10, "calc_zero_share") * 100, 2),
                        "top1_20ms_pct": r(B(I20, "top1_correct") * 100, 2), "top1_5ms_pct": r(B(I5, "top1_correct") * 100, 2),
                        "top1_4ms_pct": r(B(I4, "top1_correct") * 100, 2), "order_4ms_pct": r(B(I4, "order_correct") * 100, 2),
                        "top1_1ms_pct": r(B(I1, "top1_correct") * 100, 2), "order_1ms_pct": r(B(I1, "order_correct") * 100, 2),
                        "top1_97_pct": r(B(I97, "top1_correct") * 100, 2), "order_97_pct": r(B(I97, "order_correct") * 100, 2),
                        "top1_random_pct": r(B(IR, "top1_correct") * 100, 2), "order_random_pct": r(B(IR, "order_correct") * 100, 2),
                        "err_random_pt": r(B(IR, "mean_abs_err_pt"), 2),
                        "random_busy_samples": r(B(IR, "busy_samples_mean"), 1),
                        "formula_random_top1_pct_approx": None,
                        "formula_10ms_top1_pct_approx": r(MEANS[1] / BASE["period"] * 100, 2),
                        "no_timer_top1_10ms_pct": r(nt[I10]["top1_correct"] * 100, 2), "no_timer_top1_random_pct": r(nt[IR]["top1_correct"] * 100, 2),
                        "random_60s_top1_pct": r(lg[IR]["top1_correct"] * 100, 2), "random_60s_order_pct": r(lg[IR]["order_correct"] * 100, 2)},
           "no_timer": {k: {kk: r(vv, 4) for kk, vv in v.items()} for k, v in nt.items()},
           "random_60s": {k: r(v, 4) for k, v in lg[IR].items()},
           "grid_summary": {"n": int(len(g)),
                            "top1_10ms_min": r(g.top1_10ms.min()), "top1_10ms_max": r(g.top1_10ms.max()),
                            "top1_random_min": r(g.top1_random.min()), "top1_random_max": r(g.top1_random.max()),
                            "random_better_count": int((g.top1_random > g.top1_10ms).sum()),
                            "top1_10ms_start_sd_2_min": r(g[g.start_sd_ms == 2.0].top1_10ms.min()),
                            "top1_10ms_start_sd_2_max": r(g[g.start_sd_ms == 2.0].top1_10ms.max()),
                            "top1_10ms_start_sd_small_max": r(g[g.start_sd_ms < 1].top1_10ms.max())}}
    # でたらめな間隔の1位の当たりの近似（2つの割合の差÷標準誤差の正規近似、のぞいた数は平均の値）
    import math
    n = B(IR, "busy_samples_mean"); p1, p2 = true_mean[1], true_mean[2]
    z = (p1 - p2) / math.sqrt((p1 + p2 - (p1 - p2) ** 2) / n)
    out["headline"]["formula_random_top1_pct_approx"] = r(50 * (1 + math.erf(z / math.sqrt(2))), 2)
    json.dump(out, open(RES / "a1063_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回目の 0〜30ms の並びと、10ms ごとののぞく位置
    fig, ax = plt.subplots(figsize=(8.0, 2.8))
    cols = [LIGHT, ORANGE, BLUE, GREEN, GRAY]
    for a_, b_, f_ in zip(s[0], e[0], np.arange(len(s[0])) % 5):
        if a_ > 40:
            break
        ax.barh(0, b_ - a_, left=a_, color=cols[f_], edgecolor="white", height=.5)
    for f_ in range(5):
        ax.barh(0, 0, color=cols[f_], label=NAMES[f_])
    ph = 5.5
    for k in range(4):
        ax.annotate("", xy=(ph + 10 * k, .3), xytext=(ph + 10 * k, .75), arrowprops=dict(arrowstyle="->", color=INK))
    ax.text(ph + 0.4, .8, "10msごとにのぞく → いつも同じ「保存」", fontsize=9)
    ax.set_xlim(0, 40); ax.set_ylim(-.4, 1.1); ax.set_yticks([]); ax.set_xlabel("時刻（ms）")
    ax.legend(frameon=False, fontsize=8.5, ncol=5, loc="upper center", bbox_to_anchor=(.5, -.32))
    ax.set_title("10msごとに動く処理を10msごとにのぞくと、毎回同じ場所に当たる")
    save(fig, "a1063_timeline.png", SRC, y=-0.4)

    # 図2：のぞく間隔ごとの、1位の当たりと順位がすべて当たった割合（棒、0始まり）
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    xx = np.arange(len(tb)); w = .38
    ax.bar(xx - w / 2, tb.top1_correct * 100, w, color=BLUE, label="1位（計算）が当たった")
    ax.bar(xx + w / 2, tb.order_correct * 100, w, color=ORANGE, label="5つの順位がすべて当たった")
    for x_, a_, b_ in zip(xx, tb.top1_correct * 100, tb.order_correct * 100):
        ax.text(x_ - w / 2, a_ + 1.2, f"{a_:.1f}", ha="center", fontsize=7.5)
        ax.text(x_ + w / 2, b_ + 1.2, f"{b_:.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(xx); ax.set_xticklabels([n.replace("（", "\n（") for n in tb.interval], fontsize=8.5)
    ax.set_ylim(0, 110); ax.set_ylabel("当たった割合（%、500回）"); ax.set_xlabel("のぞく間隔（10秒間）")
    ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=2)
    ax.set_title("処理の周期と合う間隔でのぞくと、順位はのぞき始めの位置しだい")
    save(fig, "a1063_by_interval.png", SRC)

    # 図3：27通りの1位の当たり（10ms とでたらめ）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    mk = {2.0: "o", 10.0: "s", 60.0: "^"}
    cl = {0.02: GRAY, 0.2: BLUE, 2.0: ORANGE}
    for (ssd, ln), gg in g.groupby(["start_sd_ms", "length_s"]):
        ax.scatter(gg.top1_10ms * 100, gg.top1_random * 100, color=cl[ssd], marker=mk[ln], s=34)
    for ssd, c in cl.items():
        ax.scatter([], [], color=c, marker="o", label=f"タイマーの揺れ {ssd}ms")
    for ln, m_ in mk.items():
        ax.scatter([], [], color=INK, marker=m_, label=f"のぞく長さ {ln:.0f}秒")
    ax.plot([0, 100], [0, 100], color=INK, lw=.7, ls="--")
    ax.set_xlim(0, 105); ax.set_ylim(0, 105)
    ax.set_xlabel("10msごとにのぞいたときの1位の当たり（%）"); ax.set_ylabel("でたらめな間隔の1位の当たり（%）")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("置き方27通り：10msごとでは、どの置き方でも1位は当たりにくい")
    save(fig, "a1063_grid.png", SRC)

    print(tb.to_string()); print(json.dumps(out["headline"], ensure_ascii=False, indent=1)); print(out["true_share_mean_pct"])
    print(json.dumps(out["no_timer"], ensure_ascii=False)); print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
