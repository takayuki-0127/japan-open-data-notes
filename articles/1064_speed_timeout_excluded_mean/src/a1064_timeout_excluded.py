"""1064 時間切れで打ち切った処理を除くと、平均の応答時間はどう見えるのか？（架空のデータ）

架空のアプリの応答時間（ミリ秒）を、作成者が置いた分布からの乱数で作る（実機の計測はしない）。
ふつうの処理（97%）と遅い処理（3%）がまざり、時間切れ（基本1,000ms）を超えた処理は打ち切られて
応答時間が残らない。打ち切った処理を除いた平均・時間切れの値で入れた平均・本当の平均（打ち切りが
なかったときの平均）を比べ、処理が遅くなったときや時間切れを短くしたときに、除いた平均がどう動くかを数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1064
SRC = "架空のアプリの応答時間（作成者が置いた分布からの乱数、seed 1064）"
BASE = {"fast_med": 120.0, "fast_s": 0.5, "slow_share": 0.03, "slow_med": 1500.0, "slow_s": 0.6, "timeout": 1000.0}
N_BIG = 1_000_000
SCEN = [("基本", {}),
        ("遅い処理がさらに遅くなった（中央値1,500→2,500ms）", {"slow_med": 2500.0}),
        ("遅い処理が増えた（3%→6%）", {"slow_share": 0.06}),
        ("時間切れを短くした（1,000→500ms、処理は同じ）", {"timeout": 500.0})]


def r(x, d=4):
    return round(float(x), d)


def draw(rng, n, fast_med, fast_s, slow_share, slow_med, slow_s, **_):
    slow = rng.random(n) < slow_share
    x = np.where(slow, slow_med * np.exp(rng.normal(0, slow_s, n)), fast_med * np.exp(rng.normal(0, fast_s, n)))
    return x, slow


def measure(x, T):
    ok = x < T
    succ = x[ok]
    return {"true_mean": x.mean(), "true_median": np.median(x), "true_p99": np.quantile(x, .99),
            "excl_mean": succ.mean(), "excl_median": np.median(succ), "excl_p99": np.quantile(succ, .99),
            "capped_mean": np.minimum(x, T).mean(), "timeout_share": 1 - ok.mean()}


def Phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def formula(fast_med, fast_s, slow_share, slow_med, slow_s, timeout, **_):
    """対数正規の打ち切りの式：E[X; X<T] = exp(mu+s^2/2) Φ((lnT-mu-s^2)/s)、P(X<T)=Φ((lnT-mu)/s)"""
    tot, part, p = 0.0, 0.0, 0.0
    for w, med, s in [(1 - slow_share, fast_med, fast_s), (slow_share, slow_med, slow_s)]:
        mu = math.log(med)
        m = math.exp(mu + s * s / 2)
        tot += w * m
        part += w * m * Phi((math.log(timeout) - mu - s * s) / s)
        p += w * Phi((math.log(timeout) - mu) / s)
    capped = part + (1 - p) * timeout
    return {"true_mean": tot, "excl_mean": part / p, "capped_mean": capped, "timeout_share": 1 - p}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows, keep = [], {}
    for i, (nm, ch) in enumerate(SCEN):
        kw = dict(BASE, **ch)
        # 時間切れだけを変えた場面は、基本と同じ乱数（同じ処理）を使う
        x, slow = draw(np.random.default_rng(SEED * 10 + (0 if "timeout" in ch else i)), N_BIG, **kw)
        m = measure(x, kw["timeout"])
        f = formula(**kw)
        keep[nm] = (x, kw)
        rows.append({"scenario": nm, **{k: r(v, 2) if "share" not in k else r(v, 6) for k, v in m.items()},
                     "formula_true_mean": r(f["true_mean"], 2), "formula_excl_mean": r(f["excl_mean"], 2),
                     "formula_capped_mean": r(f["capped_mean"], 2), "formula_timeout_share": r(f["timeout_share"], 6)})
    sc = pd.DataFrame(rows)
    b = sc.iloc[0]
    for c in ["true_mean", "excl_mean", "capped_mean", "true_p99", "excl_p99", "timeout_share"]:
        sc[f"{c}_vs_base_pct"] = ((sc[c] / b[c] - 1) * 100).round(2)
    sc["excl_vs_true_pct"] = ((sc.excl_mean / sc.true_mean - 1) * 100).round(2)
    sc["capped_vs_true_pct"] = ((sc.capped_mean / sc.true_mean - 1) * 100).round(2)
    sc.to_csv(RES / "scenarios.csv", index=False)

    # 1日5,000件 × 前30日（基本）・後30日（遅い処理がさらに遅くなった）
    daily = []
    rd = np.random.default_rng(SEED + 1)
    for period, ch in [("before", {}), ("after", {"slow_med": 2500.0})]:
        kw = dict(BASE, **ch)
        for d in range(30):
            x, _ = draw(rd, 5000, **kw)
            m = measure(x, kw["timeout"])
            daily.append({"period": period, "day": d + 1, "excl_mean": r(m["excl_mean"], 2), "true_mean": r(m["true_mean"], 2),
                          "timeout_share": r(m["timeout_share"], 5)})
    dl = pd.DataFrame(daily)
    dl.to_csv(RES / "daily_before_after.csv", index=False)
    bef, aft = dl[dl.period == "before"], dl[dl.period == "after"]
    daily_sum = {"after_days_excl_below_before_mean": int((aft.excl_mean < bef.excl_mean.mean()).sum()),
                 "after_days_true_above_before_mean": int((aft.true_mean > bef.true_mean.mean()).sum()),
                 "after_days_timeout_above_before_max": int((aft.timeout_share > bef.timeout_share.max()).sum()),
                 "before_excl_mean_avg": r(bef.excl_mean.mean(), 2), "after_excl_mean_avg": r(aft.excl_mean.mean(), 2),
                 "before_timeout_avg_pct": r(bef.timeout_share.mean() * 100, 3), "after_timeout_avg_pct": r(aft.timeout_share.mean() * 100, 3),
                 "before_timeout_min_pct": r(bef.timeout_share.min() * 100, 3), "before_timeout_max_pct": r(bef.timeout_share.max() * 100, 3),
                 "after_timeout_min_pct": r(aft.timeout_share.min() * 100, 3), "after_timeout_max_pct": r(aft.timeout_share.max() * 100, 3)}

    # 確かめ：遅い処理の割合 × 遅い処理の中央値 × 時間切れ（27通り、各40万件）
    grid = []
    j = 0
    for ss in [0.01, 0.03, 0.06]:
        for smed in [800.0, 1500.0, 3000.0]:
            for T in [500.0, 1000.0, 2000.0]:
                kw = dict(BASE, slow_share=ss, slow_med=smed, timeout=T)
                x, _ = draw(np.random.default_rng(SEED * 100 + j), 400_000, **kw)
                j += 1
                m = measure(x, T)
                grid.append({"slow_share": ss, "slow_med": smed, "timeout": T, "true_mean": r(m["true_mean"], 2),
                             "excl_mean": r(m["excl_mean"], 2), "capped_mean": r(m["capped_mean"], 2),
                             "timeout_share": r(m["timeout_share"], 6),
                             "excl_vs_true_pct": r((m["excl_mean"] / m["true_mean"] - 1) * 100, 2),
                             "capped_vs_true_pct": r((m["capped_mean"] / m["true_mean"] - 1) * 100, 2),
                             "excl_p99_vs_true_p99_pct": r((m["excl_p99"] / m["true_p99"] - 1) * 100, 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    # 遅い処理がさらに遅くなる（中央値1,500→3,000ms）とき：除いた平均の向き（遅い処理の割合×時間切れの9通り）
    pairs = []
    for ss in [0.01, 0.03, 0.06]:
        for T in [500.0, 1000.0, 2000.0]:
            a = g[(g.slow_share == ss) & (g.timeout == T) & (g.slow_med == 1500.0)].iloc[0]
            c = g[(g.slow_share == ss) & (g.timeout == T) & (g.slow_med == 3000.0)].iloc[0]
            pairs.append({"slow_share": ss, "timeout": T,
                          "true_mean_change_pct": r((c.true_mean / a.true_mean - 1) * 100, 2),
                          "excl_mean_change_pct": r((c.excl_mean / a.excl_mean - 1) * 100, 2),
                          "capped_mean_change_pct": r((c.capped_mean / a.capped_mean - 1) * 100, 2),
                          "timeout_share_change_pt": r((c.timeout_share - a.timeout_share) * 100, 3)})
            fa, fc = formula(**dict(BASE, slow_share=ss, slow_med=1500.0, timeout=T)), formula(**dict(BASE, slow_share=ss, slow_med=3000.0, timeout=T))
            pairs[-1].update({"formula_true_mean_change_pct": r((fc["true_mean"] / fa["true_mean"] - 1) * 100, 2),
                              "formula_excl_mean_change_pct": r((fc["excl_mean"] / fa["excl_mean"] - 1) * 100, 2),
                              "formula_capped_mean_change_pct": r((fc["capped_mean"] / fa["capped_mean"] - 1) * 100, 2)})
    pr = pd.DataFrame(pairs)
    pr.to_csv(RES / "slower_pairs.csv", index=False)

    # data：基本の1日分（5,000件）
    rdd = np.random.default_rng(SEED + 2)
    x, slow = draw(rdd, 5000, **BASE)
    to = x >= BASE["timeout"]
    pd.DataFrame({"request_id": np.arange(1, 5001), "slow_path": slow.astype(int), "true_ms": x.round(1),
                  "timed_out": to.astype(int), "recorded_ms": np.where(to, np.nan, x.round(1))}).to_csv(
        DATA / "requests_one_day.csv", index=False)

    s = {row.scenario: row for row in sc.itertuples()}
    S0, S1, S2, S3 = [s[n] for n, _ in SCEN]
    out = {"base_setting": BASE, "n_big": N_BIG, "scenarios": sc.to_dict("records"),
           "headline": {
               "true_mean_ms": r(S0.true_mean, 2), "excl_mean_ms": r(S0.excl_mean, 2), "capped_mean_ms": r(S0.capped_mean, 2),
               "excl_vs_true_pct": r(S0.excl_vs_true_pct, 2), "capped_vs_true_pct": r(S0.capped_vs_true_pct, 2),
               "timeout_share_pct": r(S0.timeout_share * 100, 3),
               "true_p99_ms": r(S0.true_p99, 1), "excl_p99_ms": r(S0.excl_p99, 1),
               "slower_true_mean_change_pct": r(S1.true_mean_vs_base_pct, 2), "slower_excl_mean_change_pct": r(S1.excl_mean_vs_base_pct, 2),
               "slower_timeout_share_pct": r(S1.timeout_share * 100, 3),
               "more_slow_true_mean_change_pct": r(S2.true_mean_vs_base_pct, 2), "more_slow_excl_mean_change_pct": r(S2.excl_mean_vs_base_pct, 2),
               "more_slow_timeout_share_pct": r(S2.timeout_share * 100, 3),
               "short_timeout_excl_mean_change_pct": r(S3.excl_mean_vs_base_pct, 2),
               "short_timeout_excl_p99_change_pct": r(S3.excl_p99_vs_base_pct, 2),
               "short_timeout_timeout_share_pct": r(S3.timeout_share * 100, 3)},
           "formula_check_max_abs_diff_excl_mean_ms": r((sc.excl_mean - sc.formula_excl_mean).abs().max(), 3),
           "formula_check_max_abs_diff_true_mean_ms": r((sc.true_mean - sc.formula_true_mean).abs().max(), 3),
           "daily_before_after": daily_sum,
           "grid_summary": {"n": int(len(g)),
                            "excl_vs_true_min": r(g.excl_vs_true_pct.min(), 2), "excl_vs_true_max": r(g.excl_vs_true_pct.max(), 2),
                            "capped_vs_true_min": r(g.capped_vs_true_pct.min(), 2), "capped_vs_true_max": r(g.capped_vs_true_pct.max(), 2),
                            "excl_p99_vs_true_min": r(g.excl_p99_vs_true_p99_pct.min(), 2),
                            "excl_p99_vs_true_max": r(g.excl_p99_vs_true_p99_pct.max(), 2),
                            "timeout_share_min_pct": r(g.timeout_share.min() * 100, 3), "timeout_share_max_pct": r(g.timeout_share.max() * 100, 3)},
           "slower_pairs_summary": {"n": int(len(pr)),
                                    "true_change_min": r(pr.true_mean_change_pct.min(), 2), "true_change_max": r(pr.true_mean_change_pct.max(), 2),
                                    "excl_change_min": r(pr.excl_mean_change_pct.min(), 2), "excl_change_max": r(pr.excl_mean_change_pct.max(), 2),
                                    "excl_down_count": int((pr.excl_mean_change_pct < 0).sum()),
                                    "formula_excl_change_min": r(pr.formula_excl_mean_change_pct.min(), 2),
                                    "formula_excl_change_max": r(pr.formula_excl_mean_change_pct.max(), 2),
                                    "formula_excl_down_count": int((pr.formula_excl_mean_change_pct < 0).sum()),
                                    "capped_change_min": r(pr.capped_mean_change_pct.min(), 2), "capped_change_max": r(pr.capped_mean_change_pct.max(), 2),
                                    "capped_down_count": int((pr.capped_mean_change_pct < 0).sum())},
           "slower_pairs": pr.to_dict("records")}
    json.dump(out, open(RES / "a1064_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：応答時間の分布（対数の横軸）と時間切れ
    x0, kw0 = keep["基本"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.logspace(np.log10(10), np.log10(20000), 90)
    ax.hist(x0[x0 < 1000], bins=bins, color=LIGHT, label="記録に残る（時間切れ前に終わった）")
    ax.hist(x0[x0 >= 1000], bins=bins, color=ORANGE, label=f"時間切れで打ち切り（{S0.timeout_share*100:.2f}%）")
    ax.axvline(1000, color=INK, lw=1, ls="--"); ax.text(1060, ax.get_ylim()[1] * .9, "時間切れ 1,000ms", fontsize=9)
    ax.set_xscale("log"); ax.set_xlabel("応答時間（ms、対数の目盛り）"); ax.set_ylabel("件数（100万件のうち）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("遅い処理の山の右側が、記録から抜け落ちる")
    save(fig, "a1064_distribution.png", SRC)

    # 図2：4つの場面の平均（棒、0始まり）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    lab = ["基本", "遅い処理が\nさらに遅く", "遅い処理が\n増えた", "時間切れを\n短くした"]
    xx = np.arange(4); w = .27
    for k, (c, nm, col) in enumerate([("true_mean", "本当の平均（打ち切りなし）", INK), ("capped_mean", "時間切れを時間切れの値で入れた平均", GRAY),
                                      ("excl_mean", "打ち切りを除いた平均", ORANGE)]):
        v = sc[c].values
        ax.bar(xx + (k - 1) * w, v, w, color=col, label=nm)
        for x_, y_ in zip(xx + (k - 1) * w, v):
            ax.text(x_, y_ + 3, f"{y_:.2f}", ha="center", fontsize=7)
    ax.set_xticks(xx); ax.set_xticklabels(lab, fontsize=9); ax.set_ylim(0, sc.true_mean.max() * 1.2)
    ax.set_ylabel("平均の応答時間（ms）"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("遅くなっても、打ち切りを除いた平均はほとんど動かない（下がることもある）")
    save(fig, "a1064_scenarios.png", SRC)

    # 図3：遅い処理が1,500→3,000msに遅くなったときの変化（9通り、0を基準の棒）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    xx = np.arange(len(pr)); w = .38
    ax.bar(xx - w / 2, pr.true_mean_change_pct, w, color=INK, label="本当の平均の変化")
    ax.bar(xx + w / 2, pr.excl_mean_change_pct, w, color=ORANGE, label="打ち切りを除いた平均の変化")
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(xx); ax.set_xticklabels([f"{a*100:.0f}%\n{int(t)}ms" for a, t in zip(pr.slow_share, pr.timeout)], fontsize=8.5)
    ax.set_xlabel("上：遅い処理の割合　下：時間切れ"); ax.set_ylabel("変化（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("遅い処理が2倍遅くなっても、除いた平均は動かないか下がった（9通り）")
    save(fig, "a1064_slower_grid.png", SRC)

    print(sc.T.to_string()); print(json.dumps(daily_sum, ensure_ascii=False)); print(g.to_string()); print(pr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
