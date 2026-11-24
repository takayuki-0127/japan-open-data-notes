"""1167 消したはずの分が実際に空くまでに時間がかかると、空き容量の見込みはどれだけずれるのか？（架空のデータ）

作成者が置いた架空のアプリの保存領域（容量15,000GB）。
毎日の書き込み w は平均100GB・ばらつき（変動係数）0.3の対数が正規の形。書いたものは90日たつと消す決まり（消す量＝90日前の書き込み）。
最初から3,000GBの古い置き場があり、観察の365日目（通し565日目）に一度に消す（まとめて消す日）。
消したものはすぐには空かない：消してから D 日（基本7日）は戻せるように残し、そのあと片付けの処理が1日 K GB（基本150GB）まで、
消した順に空ける。見込みの空き＝容量−消していないものの量（消したらすぐ空くと見る）。実際の空き＝見込みの空き−消したのにまだ空いていない量。
(1) ふだん（まとめて消す日なし）のずれ：観察730日×500回
(2) まとめて消す日：見込みは3,000GBすぐ空くが、実際に空くまでの日数
(3) 確かめ：残す日数 D（0・3・7・14）×片付けの速さ（ふだん消す量の1.2・1.5・3倍）×書き込みのばらつき（0.3・0.6）の24通り×各200回
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1167
SRC = "架空のアプリの保存領域（作成者が置いた書き込み・消す決まり・片付けの速さからの乱数、seed 1167）"
CAP = 15_000.0
W_MEAN = 100.0
RET = 90
ARCH = 3_000.0
WARM, OBS = 200, 730
T = WARM + OBS
EVENT = WARM + 365
BASE = {"D": 7, "K": 150.0, "cv": 0.3}
RUNS, GRID_RUNS = 500, 200
T0 = time.time()


def r(x, d=2):
    return round(float(x), d)


def writes(rng, cv, runs):
    s = np.sqrt(np.log(1 + cv ** 2))
    return rng.lognormal(np.log(W_MEAN) - s ** 2 / 2, s, (T, runs))


def simulate(w, D, K, event):
    """日ごとに 消していない量・消したのに空いていない量・空けた累計 を返す（行が日、列が回）"""
    runs = w.shape[1]
    dele = np.zeros_like(w)
    dele[RET:] = w[:-RET]
    if event:
        dele[EVENT] += ARCH
    del_cum = np.cumsum(dele, axis=0)
    live = np.cumsum(w, axis=0) - del_cum + ARCH  # 古い置き場を含む
    freed = np.zeros_like(w)
    f = np.zeros(runs)
    for t in range(T):
        elig = del_cum[t - D] if t - D >= 0 else np.zeros(runs)
        f = np.minimum(f + K, elig) if np.isfinite(K) else elig.copy()
        f = np.maximum(f, freed[t - 1] if t > 0 else 0)
        freed[t] = f
    pending = del_cum - freed
    return live, pending, freed, del_cum


def steady_stats(w, D, K):
    live, pend, _, _ = simulate(w, D, K, False)
    p = pend[WARM:]
    naive = CAP - live[WARM:]
    true = naive - p
    return {"pending_mean_gb": r(p.mean(), 1), "pending_p95_gb": r(np.quantile(p, 0.95), 1),
            "pending_max_gb": r(p.max(), 1), "pending_days_of_writes": r(p.mean() / W_MEAN, 2),
            "naive_free_mean_gb": r(naive.mean(), 1), "true_free_mean_gb": r(true.mean(), 1),
            "naive_over_true_mean": r((naive / true).mean(), 4),
            "gap_pct_of_capacity": r(p.mean() / CAP * 100, 2)}


def event_stats(w, D, K):
    live, pend, freed, del_cum = simulate(w, D, K, True)
    runs = w.shape[1]
    # 古い置き場の3,000GBそのものが空いた量（その日の中では古い置き場を先に空けると数える）
    arch_freed = np.clip(freed[EVENT:] - del_cum[EVENT - 1][None, :], 0, ARCH)
    after = arch_freed >= ARCH - 1e-6
    clear = np.where(after.any(axis=0), after.argmax(axis=0), np.nan)
    # まとめて消した3,000GBのうち空いた分：同じ書き込みでまとめて消さない場合との差
    live0, pend0, _, _ = simulate(w, D, K, False)
    naive_gain = (CAP - live[EVENT:]) - (CAP - live0[EVENT:])
    true_gain = naive_gain - (pend[EVENT:] - pend0[EVENT:])
    ok = true_gain >= 0.99 * ARCH
    catch = np.where(ok.any(axis=0), ok.argmax(axis=0), np.nan)  # 空きが見込みに追いつく（99%）までの日数（消した日＝0日目）
    return clear, true_gain, naive_gain, catch, live, pend, arch_freed


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"capacity_gb": CAP, "write_mean_gb_per_day": W_MEAN, "write_cv": BASE["cv"], "retention_days": RET,
                       "archive_gb": ARCH, "hold_days": BASE["D"], "cleanup_gb_per_day": BASE["K"],
                       "cleanup_over_delete": r(BASE["K"] / W_MEAN, 2), "observe_days": OBS, "runs": RUNS,
                       "hold_only_formula_gb": BASE["D"] * W_MEAN}}
    w = writes(rng, BASE["cv"], RUNS)

    # (1) ふだんのずれ
    base = steady_stats(w, BASE["D"], BASE["K"])
    hold_only = steady_stats(w, BASE["D"], np.inf)
    out["base_steady"] = base
    out["base_hold_only"] = hold_only
    out["base_backlog_extra_gb"] = r(base["pending_mean_gb"] - hold_only["pending_mean_gb"], 1)
    live, pend, _, _ = simulate(w, BASE["D"], BASE["K"], False)
    pd.DataFrame({"day": np.arange(1, OBS + 1), "written_gb": np.round(w[WARM:, 0], 3),
                  "live_gb": np.round(live[WARM:, 0], 3), "deleted_not_freed_gb": np.round(pend[WARM:, 0], 3)}
                 ).to_csv(DATA / "run1_days.csv", index=False)

    # (2) まとめて消す日
    clear, tg, ng, catch, live_e, pend_e, af = event_stats(w, BASE["D"], BASE["K"])
    marks = [0, 7, 8, 14, 30, 60, 90]
    rows = []
    for m in marks:
        rows.append({"days_after": m, "naive_gain_gb_mean": r(ng[m].mean(), 1),
                     "true_gain_gb_mean": r(tg[m].mean(), 1),
                     "true_gain_gb_p10": r(np.quantile(tg[m], 0.1), 1),
                     "true_gain_gb_p90": r(np.quantile(tg[m], 0.9), 1),
                     "true_gain_pct_of_archive": r(tg[m].mean() / ARCH * 100, 2),
                     "archive_itself_freed_pct": r(af[m].mean() / ARCH * 100, 2)})
    pd.DataFrame(rows).to_csv(RES / "event_gain_by_day.csv", index=False)
    curve = pd.DataFrame({"days_after": np.arange(0, 181), "naive_gain_gb_mean": np.round(ng[:181].mean(axis=1), 1),
                          "true_gain_gb_mean": np.round(tg[:181].mean(axis=1), 1),
                          "archive_itself_freed_gb_mean": np.round(af[:181].mean(axis=1), 1)})
    curve.to_csv(RES / "event_curve.csv", index=False)
    out["base_event"] = {"archive_freed_days_median": r(np.median(clear), 1),
                         "archive_freed_formula": r(BASE["D"] + ARCH / BASE["K"], 1),
                         "catch_days_median": r(np.median(catch), 1), "catch_days_p10": r(np.quantile(catch, 0.1), 1),
                         "catch_days_p90": r(np.quantile(catch, 0.9), 1),
                         "catch_formula_from_mean": r(BASE["D"] + ARCH / (BASE["K"] - W_MEAN), 1),
                         "spare_gb_per_day": BASE["K"] - W_MEAN, "by_day": rows,
                         "true_free_min_after_gb_median": r(np.median((CAP - live_e[EVENT:EVENT + 30] - pend_e[EVENT:EVENT + 30]).min(axis=0)), 1),
                         "naive_free_after_gb_median": r(np.median(CAP - live_e[EVENT + 1]), 1)}
    one = pd.DataFrame({"day_from_event": np.arange(-30, 151),
                        "naive_free_gb": np.round(CAP - live_e[EVENT - 30:EVENT + 151, 0], 1),
                        "true_free_gb": np.round(CAP - live_e[EVENT - 30:EVENT + 151, 0] - pend_e[EVENT - 30:EVENT + 151, 0], 1)})
    one.to_csv(RES / "event_run1.csv", index=False)
    print("base", round(time.time() - T0, 1), flush=True)

    # (3) 24通り
    grows = []
    for cv in [0.3, 0.6]:
        wg = writes(rng, cv, GRID_RUNS)
        for D in [0, 3, 7, 14]:
            for km in [1.2, 1.5, 3.0]:
                K = km * W_MEAN
                st = steady_stats(wg, D, K)
                c, tg_, ng_, ca, _, _, _ = event_stats(wg, D, K)
                grows.append({"write_cv": cv, "hold_days": D, "cleanup_over_delete": km, **st,
                              "hold_only_formula_gb": D * W_MEAN,
                              "backlog_extra_gb": r(st["pending_mean_gb"] - D * W_MEAN, 1),
                              "archive_freed_days_median": r(np.median(c), 1),
                              "catch_days_median": r(np.median(ca), 1), "catch_days_p90": r(np.quantile(ca, 0.9), 1),
                              "catch_formula_from_mean": r(D + ARCH / (K - W_MEAN), 1),
                              "true_gain_day30_pct": r(tg_[30].mean() / ARCH * 100, 2)})
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"settings": len(grid),
                   "pending_mean_range": [r(grid.pending_mean_gb.min(), 1), r(grid.pending_mean_gb.max(), 1)],
                   "pending_p95_range": [r(grid.pending_p95_gb.min(), 1), r(grid.pending_p95_gb.max(), 1)],
                   "catch_days_range": [r(grid.catch_days_median.min(), 1), r(grid.catch_days_median.max(), 1)],
                   "gap_pct_cap_range": [r(grid.gap_pct_of_capacity.min(), 2), r(grid.gap_pct_of_capacity.max(), 2)],
                   "max_catch_formula_gap": r((grid.catch_days_median - grid.catch_formula_from_mean).abs().max(), 1)}
    for km in [1.2, 1.5, 3.0]:
        g = grid[grid.cleanup_over_delete == km]
        out["grid"][f"k{km}"] = {"backlog_extra_range": [r(g.backlog_extra_gb.min(), 1), r(g.backlog_extra_gb.max(), 1)],
                                 "catch_days_range": [r(g.catch_days_median.min(), 1), r(g.catch_days_median.max(), 1)],
                                 "archive_freed_range": [r(g.archive_freed_days_median.min(), 1), r(g.archive_freed_days_median.max(), 1)],
                                 "true_gain_day30_pct_range": [r(g.true_gain_day30_pct.min(), 2), r(g.true_gain_day30_pct.max(), 2)]}
    out["headline"] = {"pending_mean_gb": base["pending_mean_gb"], "hold_only_mean_gb": hold_only["pending_mean_gb"],
                       "catch_days_median": out["base_event"]["catch_days_median"],
                       "catch_formula_from_mean": out["base_event"]["catch_formula_from_mean"],
                       "day7_true_gain_gb": rows[1]["true_gain_gb_mean"], "day30_true_gain_gb": rows[4]["true_gain_gb_mean"],
                       "archive_freed_days_median": out["base_event"]["archive_freed_days_median"]}

    # 図1：まとめて消した前後（1回目）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(one.day_from_event, one.naive_free_gb, color=ORANGE, lw=2, label="見込みの空き（消したらすぐ空くと見る）")
    ax.plot(one.day_from_event, one.true_free_gb, color=BLUE, lw=2, label="実際の空き")
    ax.axvline(0, color=GRAY, lw=1, ls="--")
    ax.text(2, 7000, "3,000GBを\nまとめて消した日", color=INK, fontsize=9, va="top")
    ax.set_xlabel("まとめて消した日からの日数")
    ax.set_ylabel("空き（GB）")
    ax.set_ylim(0, CAP * 0.5)
    ax.set_title("見込みの空きはその日に増えるが、実際の空きは7日待ってから少しずつ増えた（1回目）")
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    save(fig, "a1167_event_run1.png", SRC)

    # 図2：ふだんの「消したのに空いていない量」（書き込みのばらつき0.3）
    g = grid[grid.write_cv == 0.3]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    Ds = [0, 3, 7, 14]
    x = np.arange(len(Ds))
    for i, (km, col) in enumerate(zip([1.2, 1.5, 3.0], [ORANGE, BLUE, GREEN])):
        v = [g[(g.hold_days == D) & (g.cleanup_over_delete == km)].pending_mean_gb.iloc[0] for D in Ds]
        ax.bar(x + (i - 1) * 0.26, v, 0.26, color=col, label=f"片付けの速さ：ふだん消す量の{km}倍")
        for xi, vi in zip(x, v):
            ax.text(xi + (i - 1) * 0.26, vi + 15, f"{vi:,.0f}", ha="center", fontsize=7.5, color=INK)
    ax.hlines([D * W_MEAN for D in Ds], x - 0.4, x + 0.4, color=INK, lw=1.5, label="残す日数×1日に消す量の平均（式）")
    ax.set_xticks(x, [f"{D}日" for D in Ds])
    ax.set_xlabel("消してから戻せるように残す日数")
    ax.set_ylabel("消したのに空いていない量の平均（GB）")
    ax.set_ylim(0, None)
    ax.set_title("ふだんのずれは、ほぼ「残す日数×1日に消す量」（式）どおりだった")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    save(fig, "a1167_steady_gap.png", SRC + "　書き込みのばらつき0.3、各200回×730日の平均")

    # 図3：まとめて消した分が空いた割合（基本の置き方）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(curve.days_after, curve.naive_gain_gb_mean / ARCH * 100, color=ORANGE, lw=2, label="見込み（消した日に100%）")
    ax.plot(curve.days_after, curve.archive_itself_freed_gb_mean / ARCH * 100, color=GRAY, lw=2, ls="--",
            label="古い置き場そのものが空いた割合")
    ax.plot(curve.days_after, curve.true_gain_gb_mean / ARCH * 100, color=BLUE, lw=2,
            label="実際の空きの増え（3,000GBに対する割合）")
    ax.set_xlabel("まとめて消した日からの日数")
    ax.set_ylabel("3,000GBに対する割合（%）")
    ax.set_ylim(0, 110)
    ax.set_title(f"古い置き場は{out['base_event']['archive_freed_days_median']:.0f}日で空いたが、空きが見込みに追いつくのは{out['base_event']['catch_days_median']:.0f}日（中央値）")
    ax.legend(fontsize=9, frameon=False, loc="lower right")
    save(fig, "a1167_event_share.png", SRC + "　残す7日・片付け1日150GB、500回の平均")

    with open(RES / "a1167_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(json.dumps(out["headline"], ensure_ascii=False), round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
