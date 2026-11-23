"""1062 短い時間の計測で、動かすほどだんだん遅くなる処理は見つかるのか？（架空のデータ）

架空のサーバーの処理時間（ミリ秒）を、作成者が置いた分布からの乱数で作る（実機の計測はしない）。
処理は呼ぶたびに少しずつ遅くなる（基本：1万回ごとに+1%、100万回で2倍）。N 回だけ測って
「だんだん遅くなっている」と言えるかを、①1件ずつの傾き ②20区切りの平均の傾き の2つの確かめ方で数える。
サーバーの混み具合の波（1,000回ごとに変わる）があると、遅くなっていなくても「遅くなっている」と出る回を数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1062
SRC = "架空のサーバーの処理時間（作成者が置いた分布からの乱数、seed 1062）"
BASE = {"med": 20.0, "sigma": 0.25, "p_hiccup": 0.005, "hiccup_mean": 80.0, "drift": 0.01, "wave_sd": 0.05, "wave_len": 1000}
NS = [1000, 3000, 10000, 30000, 100000]
REPS = 400
Z1 = 1.6448536       # 片側5%（1件ずつの傾き、件数が多いので正規分布で近づける）
T18 = 1.7340636      # 片側5%、自由度18（20区切りの平均の傾き）
NB = 20


def r(x, d=4):
    return round(float(x), d)


def gen(rng, reps, n, med, sigma, p_hiccup, hiccup_mean, drift, wave_sd, wave_len, **_):
    """reps × n の処理時間。drift：1万回ごとに増える割合"""
    i = np.arange(n)
    main = med * np.exp(rng.normal(0, sigma, (reps, n)))
    if wave_sd > 0:
        off = rng.integers(0, wave_len, reps)[:, None]
        seg = (i[None, :] + off) // wave_len
        lv = np.exp(rng.normal(0, wave_sd, (reps, int(seg.max()) + 1)))
        main = main * np.take_along_axis(lv, seg, axis=1)
    main = main * (1 + drift * i / 10000)[None, :]
    hic = rng.random((reps, n)) < p_hiccup
    return main + np.where(hic, rng.exponential(hiccup_mean, (reps, n)), 0.0)


def tests(y):
    """①1件ずつの傾きの t、②20区切りの平均の傾きの t（どちらも行ごと）"""
    reps, n = y.shape
    x = np.arange(n) - (n - 1) / 2
    sxx = (x ** 2).sum()
    b = y @ x / sxx
    yc = y - y.mean(1, keepdims=True)
    res = ((yc ** 2).sum(1) - b ** 2 * sxx) / (n - 2)
    t1 = b / np.sqrt(res / sxx)
    bm = y[:, : n // NB * NB].reshape(reps, NB, -1).mean(2)
    xb = np.arange(NB) - (NB - 1) / 2
    sb = (xb ** 2).sum()
    b2 = bm @ xb / sb
    bmc = bm - bm.mean(1, keepdims=True)
    res2 = ((bmc ** 2).sum(1) - b2 ** 2 * sb) / (NB - 2)
    t2 = b2 / np.sqrt(res2 / sb)
    return t1, t2


def run(seed, n, reps, kw, chunk=50):
    rng = np.random.default_rng(seed)
    a1, a2 = [], []
    for s in range(0, reps, chunk):
        t1, t2 = tests(gen(rng, min(chunk, reps - s), n, **kw))
        a1.append(t1); a2.append(t2)
    t1, t2 = np.concatenate(a1), np.concatenate(a2)
    return float((t1 > Z1).mean()), float((t2 > T18).mean())


def Phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def formula(n, med, sigma, p_hiccup, hiccup_mean, drift, **_):
    """波がないときの①の見つかる割合（傾きの推定が正規分布に従うとした式）"""
    c = med * math.exp(sigma ** 2 / 2)
    var = c ** 2 * (math.exp(sigma ** 2) - 1) + p_hiccup * 2 * hiccup_mean ** 2 - (p_hiccup * hiccup_mean) ** 2
    b = c * drift / 10000
    se = math.sqrt(var) * math.sqrt(12 / (n * (n * n - 1)))
    return Phi(b / se - Z1), c, math.sqrt(var)


def n80(med, sigma, p_hiccup, hiccup_mean, drift, **_):
    _, c, sd = formula(1000, med, sigma, p_hiccup, hiccup_mean, drift)
    b = c * drift / 10000
    return (2.4864 * sd * math.sqrt(12) / b) ** (2 / 3)


def main():
    t0 = time.time()
    rows = []
    j = 0
    for wave in [0.0, BASE["wave_sd"]]:
        for n in NS:
            kw_d = dict(BASE, wave_sd=wave)
            kw_0 = dict(kw_d, drift=0.0)
            d1, d2 = run(SEED * 100 + j, n, REPS, kw_d); j += 1
            f1, f2 = run(SEED * 100 + j, n, REPS, kw_0); j += 1
            rows.append({"wave_sd": wave, "n_calls": n, "rise_over_run_pct": r(BASE["drift"] * (n - 1) / 10000 * 100, 3),
                         "detect_slope_each": r(d1), "detect_block_means": r(d2),
                         "false_alarm_slope_each": r(f1), "false_alarm_block_means": r(f2),
                         "formula_detect_slope_each_no_wave": r(formula(n, **BASE)[0])})
    tb = pd.DataFrame(rows)
    tb.to_csv(RES / "detect_by_n.csv", index=False)
    N80 = n80(**BASE)
    n80r = int(round(N80, -2))
    c80_1, c80_2 = run(SEED * 7, n80r, REPS, dict(BASE, wave_sd=0.0))

    # 確かめ：遅くなる速さ × 1回ごとの振れ × 混み具合の波（27通り、30,000回、各150回）
    grid = []
    for d in [0.005, 0.01, 0.02]:
        for sg in [0.15, 0.25, 0.4]:
            for wv in [0.0, 0.05, 0.10]:
                kw = dict(BASE, drift=d, sigma=sg, wave_sd=wv)
                d1, d2 = run(SEED * 1000 + j, 30000, 150, kw); j += 1
                f1, f2 = run(SEED * 1000 + j, 30000, 150, dict(kw, drift=0.0)); j += 1
                grid.append({"drift_per_10000": d, "sigma": sg, "wave_sd": wv, "detect_slope_each": r(d1), "detect_block_means": r(d2),
                             "false_alarm_slope_each": r(f1), "false_alarm_block_means": r(f2),
                             "formula_detect_no_wave": r(formula(30000, **kw)[0]), "formula_n80_no_wave": int(round(n80(**kw), -2))})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    # data：基本の置き方で30,000回を1回分
    y = gen(np.random.default_rng(SEED + 1), 1, 30000, **BASE)[0]
    pd.DataFrame({"call": np.arange(1, 30001), "ms": y.round(2)}).to_csv(DATA / "calls_30000.csv", index=False)

    def row(w, n):
        return tb[(tb.wave_sd == w) & (tb.n_calls == n)].iloc[0]
    nw, ww = 0.0, BASE["wave_sd"]
    g0, gw = g[g.wave_sd == 0], g[g.wave_sd > 0]
    out = {"base_setting": BASE, "reps": REPS, "n_blocks": NB, "critical": {"slope_each_z": Z1, "block_t18": T18},
           "headline": {
               "rise_1000_pct": r(row(nw, 1000).rise_over_run_pct, 3), "rise_at_1m_pct": 100.0,
               "no_wave_detect_1000_pct": r(row(nw, 1000).detect_slope_each * 100, 2),
               "no_wave_false_1000_pct": r(row(nw, 1000).false_alarm_slope_each * 100, 2),
               "formula_detect_1000_pct": r(row(nw, 1000).formula_detect_slope_each_no_wave * 100, 2),
               "no_wave_detect_10000_pct": r(row(nw, 10000).detect_slope_each * 100, 2),
               "no_wave_detect_30000_pct": r(row(nw, 30000).detect_slope_each * 100, 2),
               "formula_detect_10000_pct": r(row(nw, 10000).formula_detect_slope_each_no_wave * 100, 2),
               "formula_detect_30000_pct": r(row(nw, 30000).formula_detect_slope_each_no_wave * 100, 2),
               "formula_n80": r(N80, 0), "n80_rounded": n80r, "n80_rise_pct": r(BASE["drift"] * n80r / 10000 * 100, 2),
               "check_detect_at_n80_slope_each_pct": r(c80_1 * 100, 2), "check_detect_at_n80_block_pct": r(c80_2 * 100, 2),
               "wave_false_slope_each_1000_pct": r(row(ww, 1000).false_alarm_slope_each * 100, 2),
               "wave_false_slope_each_10000_pct": r(row(ww, 10000).false_alarm_slope_each * 100, 2),
               "wave_false_slope_each_30000_pct": r(row(ww, 30000).false_alarm_slope_each * 100, 2),
               "wave_false_block_3000_pct": r(row(ww, 3000).false_alarm_block_means * 100, 2),
               "wave_false_block_30000_pct": r(row(ww, 30000).false_alarm_block_means * 100, 2),
               "wave_detect_block_30000_pct": r(row(ww, 30000).detect_block_means * 100, 2),
               "wave_detect_block_100000_pct": r(row(ww, 100000).detect_block_means * 100, 2)},
           "detect_by_n": tb.to_dict("records"),
           "grid_summary": {"n": int(len(g)),
                            "no_wave_false_each_min": r(g0.false_alarm_slope_each.min()), "no_wave_false_each_max": r(g0.false_alarm_slope_each.max()),
                            "wave_false_each_min": r(gw.false_alarm_slope_each.min()), "wave_false_each_max": r(gw.false_alarm_slope_each.max()),
                            "wave_false_block_min": r(gw.false_alarm_block_means.min()), "wave_false_block_max": r(gw.false_alarm_block_means.max()),
                            "formula_n80_min": int(g.formula_n80_no_wave.min()), "formula_n80_max": int(g.formula_n80_no_wave.max()),
                            "no_wave_detect_each_min": r(g0.detect_slope_each.min()), "no_wave_detect_each_max": r(g0.detect_slope_each.max()),
                            "max_abs_diff_formula_no_wave": r((g0.detect_slope_each - g0.formula_detect_no_wave).abs().max())}}
    json.dump(out, open(RES / "a1062_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の記録（最初の1,000回と、30,000回の1,000回ごとの中央値）
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.9), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axs[0]
    ax.scatter(np.arange(1, 1001), y[:1000], s=2, color=BLUE, alpha=.5)
    ax.set_ylim(0, 60); ax.set_xlabel("呼んだ回数（最初の1,000回）"); ax.set_ylabel("処理時間（ms）")
    ax.set_title("1,000回では、0.1%の遅れは見えない", fontsize=11)
    ax = axs[1]
    med = np.median(y.reshape(30, 1000), axis=1)
    ax.plot(np.arange(30) * 1000 + 500, med, marker="o", ms=3, color=ORANGE, label="1,000回ごとの中央値（波あり）")
    true_med = BASE["med"] * (1 + BASE["drift"] * (np.arange(30) * 1000 + 500) / 10000)
    ax.plot(np.arange(30) * 1000 + 500, true_med, color=INK, lw=1, ls="--", label="波がないときの中央値（置いた値）")
    ax.set_ylim(0, 25); ax.set_xlabel("呼んだ回数"); ax.set_ylabel("処理時間の中央値（ms）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("30,000回で+3%。混み具合の波と同じくらいの大きさ", fontsize=11)
    fig.suptitle("1万回ごとに+1%遅くなる処理の、1回分の記録", fontsize=13, y=1.04)
    save(fig, "a1062_one_run.png", SRC)

    # 図2：波がないとき、①で見つかる割合（式と乱数）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    t0w = tb[tb.wave_sd == 0]
    nn = np.logspace(3, 5, 60)
    ax.plot(nn, [formula(int(v), **BASE)[0] * 100 for v in nn], color=GRAY, lw=1.2, label="式（傾きが正規分布に従うとした値）")
    ax.plot(t0w.n_calls, t0w.detect_slope_each * 100, "o", color=BLUE, label="乱数（遅くなる処理）")
    ax.plot(t0w.n_calls, t0w.false_alarm_slope_each * 100, "s", color=ORANGE, label="乱数（遅くならない処理）")
    for x_, y_ in zip(t0w.n_calls, t0w.detect_slope_each * 100):
        if y_ > 50:  # 式の線と重ならないよう、高い点は左下に置く
            ax.text(x_ / 1.1, y_ - 4, f"{y_:.2f}%", fontsize=8, color=BLUE, ha="right", va="top")
        else:
            ax.text(x_ * 1.08, y_ + 3, f"{y_:.2f}%", fontsize=8, color=BLUE)
    ax.axhline(80, color=INK, lw=.7, ls=":"); ax.axhline(5, color=INK, lw=.7, ls=":")
    ax.set_xscale("log"); ax.set_ylim(0, 105); ax.set_xlabel("測った回数（対数の目盛り）")
    ax.set_ylabel("「遅くなっている」と出た割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="center left")
    ax.set_title(f"波がないとき：8割見つけるには約{N80:,.0f}回（式どおり）")
    save(fig, "a1062_detect_n.png", SRC)

    # 図3：波があるとき、遅くならない処理で「遅くなっている」と出た割合（棒、0始まり）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    tw = tb[tb.wave_sd > 0]
    xx = np.arange(len(tw)); w = .38
    ax.bar(xx - w / 2, tw.false_alarm_slope_each * 100, w, color=ORANGE, label="①1件ずつの傾き")
    ax.bar(xx + w / 2, tw.false_alarm_block_means * 100, w, color=BLUE, label="②20区切りの平均の傾き")
    for x_, a_, b_ in zip(xx, tw.false_alarm_slope_each * 100, tw.false_alarm_block_means * 100):
        ax.text(x_ - w / 2, a_ + 1, f"{a_:.2f}", ha="center", fontsize=7.5)
        ax.text(x_ + w / 2, b_ + 1, f"{b_:.2f}", ha="center", fontsize=7.5)
    ax.axhline(5, color=INK, lw=.7, ls=":", label="本来の5%")
    ax.set_xticks(xx); ax.set_xticklabels([f"{n:,}回" for n in tw.n_calls])
    ax.set_ylim(0, 100); ax.set_ylabel("遅くならない処理で\n「遅くなっている」と出た割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("混み具合の波があると、遅くなっていなくても「遅くなる」と出る")
    save(fig, "a1062_wave_false.png", SRC)

    print(tb.to_string()); print(g.to_string()); print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
