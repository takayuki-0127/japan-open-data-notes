"""1268 週ごとに見直した見込みが期の終わりほど当たって見えるのは、見込みが良くなったからか、決まった分が増えたからか？（架空のデータ）

架空の会社の法人向けの商談。期のはじめにある商談ごとに、本当の受注の確率・金額・決まる週を作成者が置き、取れる・取れないを乱数で決める。
毎週の終わりに「決まって取れた金額＋まだ決まっていない商談の確度×金額」で期の受注を見込む。
確度を見直さない付け方と、決まる週に近づくほど結果の側へ寄せて見直す付け方で、見込みの外れを、
期全体の外れと、まだ決まっていない分だけの外れに分けて週ごとに数える。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1268
SRC = "架空の会社の法人向けの商談（作成者が置いた受注の確率・金額・決まる週からの乱数、seed 1268）"
WEEKS = 13
REPS = 2000
GRID_REPS = 300
BASE = dict(n=120, mu=-0.75, spread=1.2, amt_sd=1.0, noise=0.5, learn=0.0, timing="一様")
TIMING = {
    "一様": np.ones(WEEKS),
    "期末に寄る": np.arange(1, WEEKS + 1) ** 2.0,
    "期のはじめに寄る": (WEEKS + 1 - np.arange(1, WEEKS + 1)) ** 2.0,
}
WK = np.arange(0, WEEKS)   # 0週目（期のはじめ）〜12週目の終わり


def sig(x):
    return 1 / (1 + np.exp(-x))


def simulate(p, reps, rng):
    n = p["n"]
    lq = p["mu"] + p["spread"] * rng.standard_normal((reps, n))
    q = sig(lq)
    a = np.exp(np.log(100) + p["amt_sd"] * rng.standard_normal((reps, n)))
    w = TIMING[p["timing"]]
    T = rng.choice(np.arange(1, WEEKS + 1), size=(reps, n), p=w / w.sum())
    y = (rng.random((reps, n)) < q).astype(float)
    p0 = sig(lq + p["noise"] * rng.standard_normal((reps, n)))
    return dict(q=q, a=a, T=T, y=y, p0=p0)


def weekly(p, d, learn):
    """週ごとの見込み。learn=0 は見直さない、learn>0 は決まる週に近づくほど結果の側へ寄せる"""
    a, T, y, p0 = d["a"], d["T"], d["y"], d["p0"]
    A = (a * y).sum(1)
    tot = a.sum(1)
    out = []
    for w in WK:
        dec = T <= w
        g = learn * np.where(dec, 1, w / T)
        pw = (1 - g) * p0 + g * y
        won_dec = (a * y * dec).sum(1)
        open_fc = (a * pw * ~dec).sum(1)
        open_act = (a * y * ~dec).sum(1)
        open_amt = (a * ~dec).sum(1)
        F = won_dec + open_fc
        out.append(dict(F=F, A=A, won_dec=won_dec, open_fc=open_fc, open_act=open_act, open_amt=open_amt,
                        dec_amt=(a * dec).sum(1), tot=tot, n_open=(~dec).sum(1)))
    return out


def week_table(p, d, learn):
    rows = []
    for w, o in zip(WK, weekly(p, d, learn)):
        err = np.abs(o["F"] - o["A"])
        open_err = np.abs(o["open_fc"] - o["open_act"])
        rows.append(dict(week=int(w),
                         total_err=float(err.mean() / o["A"].mean() * 100),
                         within10=float((err <= 0.1 * o["A"]).mean() * 100),
                         decided_amount_share=float((o["dec_amt"] / o["tot"]).mean() * 100),
                         decided_won_share=float((o["won_dec"] / o["A"]).mean() * 100),
                         open_deals=float(o["n_open"].mean()),
                         open_err_vs_actual=float(open_err.mean() / o["A"].mean() * 100),
                         open_err_vs_open_amt=float(open_err.mean() / o["open_amt"].mean() * 100),
                         open_bias_vs_open_amt=float((o["open_fc"] - o["open_act"]).mean() / o["open_amt"].mean() * 100)))
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    tabs = []
    scen = [("一様", 0.0), ("一様", 0.5), ("期末に寄る", 0.0), ("期末に寄る", 0.5), ("期のはじめに寄る", 0.0), ("期のはじめに寄る", 0.5)]
    data_cache = {}
    for timing in TIMING:
        p = {**BASE, "timing": timing}
        data_cache[timing] = simulate(p, REPS, rng)
    for timing, learn in scen:
        p = {**BASE, "timing": timing}
        t = week_table(p, data_cache[timing], learn)
        t.insert(0, "learn", learn)
        t.insert(0, "timing", timing)
        tabs.append(t)
    wt = pd.concat(tabs, ignore_index=True)
    wt.round(4).to_csv(RES / "weekly_summary.csv", index=False)

    # 1回分のデータ（一様、見直さない・見直す）
    d = data_cache["一様"]
    ex = pd.DataFrame({"deal_id": np.arange(1, BASE["n"] + 1), "amount_man_yen": d["a"][0].round(1),
                       "true_prob": d["q"][0].round(4), "decide_week": d["T"][0], "won": d["y"][0].astype(int),
                       "p_start": d["p0"][0].round(4)})
    ex.to_csv(DATA / "deals_example.csv", index=False)
    exw = []
    for learn in [0.0, 0.5]:
        for w, o in zip(WK, weekly(BASE, d, learn)):
            exw.append(dict(learn=learn, week=int(w), forecast=round(float(o["F"][0]), 2), actual=round(float(o["A"][0]), 2),
                            won_decided=round(float(o["won_dec"][0]), 2), open_forecast=round(float(o["open_fc"][0]), 2),
                            open_actual=round(float(o["open_act"][0]), 2)))
    pd.DataFrame(exw).to_csv(DATA / "weekly_example.csv", index=False)

    # 確かめ：置き方を変える
    grid_rows = []
    for timing, n, noise, learn in itertools.product(list(TIMING), [40, 120, 400], [0.3, 0.8], [0.0, 0.25, 0.5]):
        p = {**BASE, "timing": timing, "n": n, "noise": noise}
        dd = simulate(p, GRID_REPS, rng)
        t = week_table(p, dd, learn).set_index("week")
        grid_rows.append(dict(timing=timing, n=n, noise=noise, learn=learn,
                              total_err_w0=round(t.total_err[0], 3), total_err_w6=round(t.total_err[6], 3),
                              total_err_w10=round(t.total_err[10], 3),
                              ratio_total_w10=round(t.total_err[10] / t.total_err[0], 4),
                              open_err_amt_w0=round(t.open_err_vs_open_amt[0], 3),
                              open_err_amt_w10=round(t.open_err_vs_open_amt[10], 3),
                              ratio_open_amt_w10=round(t.open_err_vs_open_amt[10] / t.open_err_vs_open_amt[0], 4),
                              decided_amount_share_w10=round(t.decided_amount_share[10], 2)))
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False)

    # まとめ
    def W(timing, learn, w, col):
        return round(float(wt[(wt.timing == timing) & (wt.learn == learn) & (wt.week == w)][col].iloc[0]), 2)
    headline = {}
    for timing, learn in scen:
        key = f"{timing}_見直し{learn}"
        headline[key] = {f"w{w}": {c: W(timing, learn, w, c) for c in ["total_err", "within10", "decided_amount_share",
                                                                       "decided_won_share", "open_deals",
                                                                       "open_err_vs_open_amt", "open_err_vs_actual",
                                                                       "open_bias_vs_open_amt"]}
                         for w in [0, 3, 6, 9, 10, 12]}
    decomp = {}
    for timing in TIMING:
        e0 = W(timing, 0.0, 0, "total_err")
        decomp[timing] = {}
        for w in [3, 6, 9, 10]:
            en, el = W(timing, 0.0, w, "total_err"), W(timing, 0.5, w, "total_err")
            decomp[timing][f"w{w}"] = {"drop_nolearn_pt": round(e0 - en, 2), "drop_learn_pt": round(e0 - el, 2),
                                       "share_from_decided": round((e0 - en) / (e0 - el) * 100, 2)}
    headline["decompose_vs_learn05"] = decomp
    g0 = grid[grid.learn == 0]
    g5 = grid[grid.learn == 0.5]
    robust = {
        "n_grid": int(len(grid)), "grid_reps": GRID_REPS,
        "nolearn_ratio_total_w10_range": [float(g0.ratio_total_w10.min()), float(g0.ratio_total_w10.max())],
        "nolearn_ratio_open_amt_w10_range": [float(g0.ratio_open_amt_w10.min()), float(g0.ratio_open_amt_w10.max())],
        "learn05_ratio_total_w10_range": [float(g5.ratio_total_w10.min()), float(g5.ratio_total_w10.max())],
        "learn05_ratio_open_amt_w10_range": [float(g5.ratio_open_amt_w10.min()), float(g5.ratio_open_amt_w10.max())],
        "nolearn_ratio_total_w10_by_timing": {t: [float(g0[g0.timing == t].ratio_total_w10.min()), float(g0[g0.timing == t].ratio_total_w10.max())] for t in TIMING},
        "decided_amount_share_w10_by_timing": {t: [float(grid[grid.timing == t].decided_amount_share_w10.min()), float(grid[grid.timing == t].decided_amount_share_w10.max())] for t in TIMING},
        "nolearn_open_ratio_above1_n": int((g0.ratio_open_amt_w10 > 1).sum()),
        "nolearn_n": int(len(g0)),
    }
    # 13週目の終わり：すべて決まり、見込み＝実績になること
    dd = data_cache["一様"]
    dec13 = dd["T"] <= WEEKS
    F13 = (dd["a"] * dd["y"] * dec13).sum(1) + (dd["a"] * dd["p0"] * ~dec13).sum(1)
    robust["week13_all_decided"] = bool(dec13.all())
    robust["week13_max_abs_diff"] = float(np.abs(F13 - (dd["a"] * dd["y"]).sum(1)).max())
    mg = g0.merge(g5, on=["timing", "n", "noise"], suffixes=("_0", "_5"))
    mg["share_from_decided_w10"] = ((mg.total_err_w0_0 - mg.total_err_w10_0) / (mg.total_err_w0_5 - mg.total_err_w10_5) * 100).round(2)
    robust["share_from_decided_w10_by_timing"] = {t: [float(mg[mg.timing == t].share_from_decided_w10.min()), float(mg[mg.timing == t].share_from_decided_w10.max())] for t in TIMING}
    run_sec = round(time.time() - t0, 1)
    json.dump({"base": BASE, "weeks": WEEKS, "reps": REPS, "timing_weights": {k: v.tolist() for k, v in TIMING.items()},
               "headline": headline, "robust": robust},
              open(RES / "a1268_main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：一様。期全体の外れと、まだ決まっていない分の外れ（週ごと）
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.3))
    fig.subplots_adjust(wspace=0.55)
    for learn, c, lab in [(0.0, ORANGE, "見直さない"), (0.5, BLUE, "見直す（決まる週に近いほど結果の側へ）")]:
        t = wt[(wt.timing == "一様") & (wt.learn == learn)]
        ax[0].plot(t.week, t.total_err, color=c, marker="o", ms=3.5, lw=1.8, label=lab)
        ax[1].plot(t.week, t.open_err_vs_open_amt, color=c, marker="o", ms=3.5, lw=1.8, label=lab)
    t = wt[(wt.timing == "一様") & (wt.learn == 0.0)]
    ax0b = ax[0].twinx()
    ax0b.bar(t.week, t.decided_amount_share, color=GRAY, alpha=0.25, width=0.7, label="決まった商談の金額の割合（右の目盛り）")
    ax0b.set_ylim(0, 100)
    ax0b.set_ylabel("決まった商談の金額の割合（%）", color=GRAY)
    ax0b.spines["right"].set_visible(True)
    ax[0].set_zorder(ax0b.get_zorder() + 1)
    ax[0].patch.set_visible(False)
    ax[0].set_ylim(0, 30)
    ax[0].set_xlabel("週（その週の終わりに見込む）")
    ax[0].set_ylabel("期の見込みの外れ（%、実績の平均に対する）")
    ax[0].set_title("期全体の外れ：どちらも週を追って小さくなる", fontsize=11.5)
    h1, l1 = ax[0].get_legend_handles_labels()
    h2, l2 = ax0b.get_legend_handles_labels()
    ax[0].legend(h1 + h2, l1 + l2, fontsize=8, frameon=False, loc="upper left")
    ax[1].set_ylim(0, 30)
    ax[1].set_xlabel("週（その週の終わりに見込む）")
    ax[1].set_ylabel("外れ（%、まだ決まっていない商談の金額に対する）")
    ax[1].set_title("まだ決まっていない分だけの外れ：見直さないと縮まない", fontsize=11.5)
    ax[1].legend(fontsize=8, frameon=False, loc="lower left")
    for a_ in ax:
        a_.set_xticks(WK)
    save(fig, "a1268_weekly_error.png", SRC)

    # 図2：決まる週の寄り方ごと（見直さない）
    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    for timing, c in zip(TIMING, [ORANGE, GREEN, BLUE]):
        t = wt[(wt.timing == timing) & (wt.learn == 0.0)]
        ax.plot(t.week, t.total_err, color=c, marker="o", ms=3.5, lw=1.8, label=f"決まる週が{timing}")
    ax.set_ylim(0, 30)
    ax.set_xticks(WK)
    ax.set_xlabel("週（その週の終わりに見込む）")
    ax.set_ylabel("期の見込みの外れ（%、実績の平均に対する）")
    ax.set_title("確度を見直さなくても、外れの縮み方は決まる週の寄り方で決まる", fontsize=11.5)
    ax.legend(fontsize=8.5, frameon=False, loc="lower left")
    save(fig, "a1268_timing.png", SRC)

    # 図3：確かめ（10週目の外れ÷0週目の外れ）
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    mk = {"一様": "o", "期末に寄る": "^", "期のはじめに寄る": "s"}
    for learn, c in zip([0.0, 0.25, 0.5], [ORANGE, GREEN, BLUE]):
        for timing in TIMING:
            gg = grid[(grid.learn == learn) & (grid.timing == timing)]
            ax.scatter(gg.ratio_total_w10, gg.ratio_open_amt_w10, color=c, marker=mk[timing], s=28, alpha=0.85,
                       label=f"見直しの強さ{learn}・{timing}")
    ax.axhline(1, color=INK, lw=0.8, ls=":")
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, max(1.6, float(grid.ratio_open_amt_w10.max()) * 1.05))
    ax.set_xlabel("期全体の外れ：10週目÷0週目")
    ax.set_ylabel("まだ決まっていない分の外れ：10週目÷0週目")
    ax.set_title("54通り：見直さないと、まだ決まっていない分の外れは縮まない", fontsize=11.5)
    ax.legend(fontsize=7, frameon=False, loc="upper left", ncol=3, bbox_to_anchor=(0, -0.15))
    save(fig, "a1268_grid.png", SRC, y=-0.25)

    print(wt[wt.week.isin([0, 3, 6, 9, 10, 12])].round(2).to_string())
    print(json.dumps(robust, ensure_ascii=False, indent=1))
    print("run_sec", run_sec)


if __name__ == "__main__":
    main()
