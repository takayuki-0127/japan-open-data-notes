"""938 直近の出来事に引っぱられる評価は、年の点をどれだけ動かすのか？（架空のデータ）

架空の会社の300人。人ごとに「その年の本当の点」を、12か月の月ごとの出来の平均として置く。
評価者が直近の月ほど重く覚えている（半分の重みになるまでの月数＝半減期 h）と置き、
その重みで付けた年の点が、12か月を同じ重みで平均した点からどれだけずれるかを数える。
月ごとの出来 ＝ その人の水準 ＋ その人の伸び×月 ＋ 月ごとの振れ（前の月を少し引きずる）＋ まれな出来事。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 938
SRC = "架空の会社の300人の月ごとの出来（作成者が乱数で作成、seed 938）"
N, M = 300, 12
MU, SD_P = 60.0, 8.0
BASE = {"h": 3.0, "s_m": 8.0, "phi": 0.3, "s_tr": 0.3, "p_ev": 0.15, "ev": 20.0}
GRADES = ["S", "A", "B", "C", "D"]
CUTS = [0.10, 0.30, 0.70, 0.90]   # 上から10%・20%・40%・20%・10%


def weights(h, m=M):
    if np.isinf(h):
        w = np.ones(m)
    else:
        w = 0.5 ** ((m - np.arange(1, m + 1)) / h)
    return w / w.sum()


def months(rng, n, s_m, phi, s_tr, p_ev, ev, m=2 * M):
    """2年分（24か月）の月ごとの出来。1年目が評価の年、2年目は来年の当てに使う"""
    p = rng.normal(MU, SD_P, n)
    tr = rng.normal(0, s_tr, n)
    x = np.empty((n, m))
    x[:, 0] = rng.normal(0, s_m, n)
    for t in range(1, m):
        x[:, t] = phi * x[:, t - 1] + np.sqrt(1 - phi ** 2) * rng.normal(0, s_m, n)
    t = np.arange(1, m + 1) - (M + 1) / 2
    perf = p[:, None] + tr[:, None] * t[None, :] + x
    # まれな出来事：1年目のどこか1か月に ±ev（大きな受注／大きなやり直し）
    has = rng.random(n) < p_ev
    mon = rng.integers(0, M, n)
    sign = np.where(rng.random(n) < 0.5, 1.0, -1.0)
    perf[np.arange(n)[has], mon[has]] += sign[has] * ev
    return perf, has, mon, sign


def grade(score):
    q = np.argsort(np.argsort(-score)) / len(score)
    return np.searchsorted(CUTS, q, side="right")


def spearman(x, y):
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def evaluate(rng, h, s_m, phi, s_tr, p_ev, ev, reps):
    w = weights(h)
    keys = ["rms", "rms_ratio", "rho", "grade_changed", "grade_moved2", "top10_hit", "rho_next_equal", "rho_next_recent"]
    acc = {k: [] for k in keys}
    for _ in range(reps):
        perf, has, mon, sign = months(rng, N, s_m, phi, s_tr, p_ev, ev)
        year = perf[:, :M].mean(1)
        rec = perf[:, :M] @ w
        nxt = perf[:, M:].mean(1)
        d = rec - year
        acc["rms"].append(np.sqrt((d ** 2).mean()))
        acc["rms_ratio"].append(np.sqrt((d ** 2).mean()) / year.std())
        acc["rho"].append(spearman(rec, year))
        g0, g1 = grade(year), grade(rec)
        acc["grade_changed"].append((g0 != g1).mean())
        acc["grade_moved2"].append((np.abs(g0 - g1) >= 2).mean())
        acc["top10_hit"].append(len(set(np.argsort(-year)[:N // 10]) & set(np.argsort(-rec)[:N // 10])) / (N // 10))
        acc["rho_next_equal"].append(spearman(year, nxt))
        acc["rho_next_recent"].append(spearman(rec, nxt))
    return {k: round(float(np.mean(v)), 4) for k, v in acc.items()}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    HS = [1.0, 2.0, 3.0, 6.0, 12.0, np.inf]
    hname = lambda h: "同じ重み" if np.isinf(h) else f"{h:g}"

    # 1回分のデータ
    perf, has, mon, sign = months(rng, N, BASE["s_m"], BASE["phi"], BASE["s_tr"], BASE["p_ev"], BASE["ev"])
    df = pd.DataFrame(perf[:, :M].round(2), columns=[f"m{t:02d}" for t in range(1, M + 1)])
    df.insert(0, "person", np.arange(1, N + 1))
    df["event_month"] = np.where(has, mon + 1, 0)
    df["event_sign"] = np.where(has, sign, 0).astype(int)
    df["year_equal"] = perf[:, :M].mean(1).round(3)
    df["year_recent_h3"] = (perf[:, :M] @ weights(3.0)).round(3)
    df.to_csv(DATA / "monthly_scores.csv", index=False)
    g0, g1 = grade(df.year_equal.values), grade(df.year_recent_h3.values)
    one = {"grade_changed": round(float((g0 != g1).mean()), 3),
           "rho": round(spearman(df.year_recent_h3.values, df.year_equal.values), 3),
           "crosstab": pd.crosstab(pd.Series([GRADES[i] for i in g0], name="equal"),
                                   pd.Series([GRADES[i] for i in g1], name="recent_h3")).to_dict()}

    # 2) 重み：月ごとの重み（半減期ごと）と、出来事1つが年の点を動かす大きさ
    wrows = []
    for h in HS:
        w = weights(h)
        wrows.append({"h": hname(h), "w_month12": round(float(w[-1]), 4), "w_month1": round(float(w[0]), 4),
                      "w_last3": round(float(w[-3:].sum()), 4), "ratio_last_first": round(float(w[-1] / w[0]), 2),
                      "event20_month12": round(float(BASE["ev"] * w[-1]), 3),
                      "event20_month1": round(float(BASE["ev"] * w[0]), 3)})
    wt = pd.DataFrame(wrows)
    wt.to_csv(RES / "weights_by_halflife.csv", index=False)

    # 3) 基本：半減期ごと（200回）
    rows = []
    for i, h in enumerate(HS):
        r = evaluate(np.random.default_rng(SEED * 100 + i), h, BASE["s_m"], BASE["phi"], BASE["s_tr"],
                     BASE["p_ev"], BASE["ev"], 200)
        rows.append({"h": hname(h), **r})
    base = pd.DataFrame(rows)
    base.to_csv(RES / "by_halflife_base.csv", index=False)

    # 4) 出来事が12月目（最後の月）にあった、真ん中の人の位置（基本の分布で）
    ref = []
    for r in range(50):
        pf, *_ = months(np.random.default_rng(SEED * 500 + r), N, BASE["s_m"], BASE["phi"], BASE["s_tr"], 0.0, 0.0)
        ref.append(pf[:, :M] @ weights(3.0))
    ref = np.concatenate(ref)
    med = float(np.median(ref))
    w3 = weights(3.0)
    pos = {}
    for lab, shift in [("+20 in month12", BASE["ev"] * w3[-1]), ("+20 in month1", BASE["ev"] * w3[0]),
                       ("-20 in month12", -BASE["ev"] * w3[-1])]:
        pos[lab] = {"shift": round(float(shift), 3), "percentile_from_top": round(float((ref > med + shift).mean()), 3)}
    eq = []
    for r in range(50):
        pf, *_ = months(np.random.default_rng(SEED * 600 + r), N, BASE["s_m"], BASE["phi"], BASE["s_tr"], 0.0, 0.0)
        eq.append(pf[:, :M].mean(1))
    eq = np.concatenate(eq)
    pos["+20 equal weights"] = {"shift": round(BASE["ev"] / M, 3),
                                "percentile_from_top": round(float((eq > np.median(eq) + BASE["ev"] / M).mean()), 3)}

    # 5) 確かめ：月の振れ s_m × 引きずり phi × 伸びの差 s_tr（h=3、各100回）
    grid = []
    c = 0
    for s_m in [4.0, 8.0, 16.0]:
        for phi in [0.0, 0.3, 0.6]:
            for s_tr in [0.0, 0.3, 0.6]:
                r = evaluate(np.random.default_rng(SEED * 1000 + c), 3.0, s_m, phi, s_tr, BASE["p_ev"], BASE["ev"], 100)
                grid.append({"s_m": s_m, "phi": phi, "s_tr": s_tr, **r})
                c += 1
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_h3.csv", index=False)

    # 6) 確かめ：伸びの差と来年の当て（半減期ごと、s_tr を 0・0.3・0.6・1.0）
    nx = []
    for j, s_tr in enumerate([0.0, 0.3, 0.6, 1.0]):
        for i, h in enumerate(HS):
            r = evaluate(np.random.default_rng(SEED * 2000 + 10 * j + i), h, BASE["s_m"], BASE["phi"], s_tr,
                         BASE["p_ev"], BASE["ev"], 100)
            nx.append({"s_tr": s_tr, "h": hname(h), "rho_next": r["rho_next_recent"], "rho_year": r["rho"],
                       "grade_changed": r["grade_changed"]})
    nx = pd.DataFrame(nx)
    nx.to_csv(RES / "next_year_by_trend.csv", index=False)

    b = base.set_index("h")
    out = {"params": {**BASE, "n": N, "months": M, "level_mean": MU, "level_sd": SD_P, "grade_cuts": CUTS},
           "weights": wt.to_dict("records"), "by_halflife_base": base.to_dict("records"),
           "event_position_median_person_h3": pos,
           "grid_h3_range": {"grade_changed": [float(grid.grade_changed.min()), float(grid.grade_changed.max())],
                             "rho": [float(grid.rho.min()), float(grid.rho.max())],
                             "rms_ratio": [float(grid.rms_ratio.min()), float(grid.rms_ratio.max())]},
           "next_year": nx.to_dict("records"), "one_draw": one}
    json.dump(out, open(RES / "a938_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：月ごとの重み
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(1, M + 1)
    for h, c_, ls in zip([1.0, 3.0, 6.0, np.inf], [ORANGE, BLUE, GREEN, GRAY], ["-", "-", "--", ":"]):
        ax.plot(x, weights(h) * 100, marker="o", ms=4, color=c_, ls=ls,
                label="同じ重み（1/12）" if np.isinf(h) else f"半減期 {h:g}か月")
    ax.set_xticks(x); ax.set_xticklabels([f"{t}" for t in x])
    ax.set_xlabel("評価の期間の月（12が評価の直前の月）"); ax.set_ylabel("年の点に占める重み（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"半減期3か月なら、最後の3か月で年の点の{wt.set_index('h').loc['3', 'w_last3']*100:.0f}%が決まる")
    save(fig, "a938_weights.png", SRC)

    # 図2：半減期ごとの評価の段の入れかわり
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    lab = ["1か月", "2か月", "3か月", "6か月", "12か月", "同じ重み"]
    ax.bar(lab, base.grade_changed * 100, color=[ORANGE, ORANGE, BLUE, LIGHT, LIGHT, GRAY])
    for i, v in enumerate(base.grade_changed * 100):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_xlabel("評価者の覚え方（重みが半分になるまでの月数）")
    ax.set_ylabel("5段階の段が変わった人の割合（%）"); ax.set_ylim(0, max(base.grade_changed * 100) + 10)
    ax.set_title("同じ1年の出来でも、覚え方だけで段が変わる人がいる（各200回の平均）")
    save(fig, "a938_grade_change.png", SRC)

    # 図3：伸びの差と、来年の点の当たり
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for s_tr, c_, ls in zip([0.0, 0.3, 0.6, 1.0], [GRAY, BLUE, ORANGE, GREEN], [":", "-", "--", "-."]):
        g = nx[nx.s_tr == s_tr]
        ax.plot(lab, g.rho_next, marker="o", color=c_, ls=ls, label=f"伸びの差 {s_tr:g}点/月")
    ax.set_xlabel("評価者の覚え方（重みが半分になるまでの月数）")
    ax.set_ylabel("来年の本当の点との順位相関")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("伸びの差が大きいほど、直近を重く見た点のほうが来年を当てる")
    save(fig, "a938_next_year.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
