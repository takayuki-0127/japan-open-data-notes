"""1042 要素ごとに平均を使うか中央値を使うかで、掛けた答えはどれだけ違うのか？（架空のデータ）

架空のA町の、架空のパン屋で買う世帯4,000世帯。世帯ごとに「人数」「月の来店回数」「1回に1人あたり買う個数」を
作成者が置いた分布から乱数で作り、年の販売個数（本当の値）＝12か月×世帯ごとの掛け算の合計とする。
要素ごとの平均を掛ける・中央値を掛ける・世帯ごとに掛けてから平均する、の3つで概算し、本当の値の何倍になるかを数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1042
SRC = "架空のA町のパン屋の概算（作成者が乱数で作成、seed 1042）"
N_HH = 4000
PERSONS = np.array([1, 2, 3, 4, 5, 6])
P_PERSONS = np.array([0.30, 0.30, 0.18, 0.15, 0.05, 0.02])
BASE = {"med_visits": 2.0, "sd_visits": 0.8, "med_items": 1.5, "sd_items": 0.5, "rho": 0.0}
NS = [10, 30, 100, 300]
REPS = 5000
TOL = 1.2  # 「1.2倍以内」（作成者が置いた物差し）


def town(rng, med_visits, sd_visits, med_items, sd_items, rho, n=N_HH):
    """使う世帯 n 世帯の要素。rho：来店回数と個数の対数どうしの相関"""
    persons = rng.choice(PERSONS, size=n, p=P_PERSONS).astype(float)
    z1 = rng.standard_normal(n)
    z2 = rho * z1 + math.sqrt(1 - rho ** 2) * rng.standard_normal(n)
    visits = med_visits * np.exp(sd_visits * z1)
    items = med_items * np.exp(sd_items * z2)
    return np.column_stack([persons, visits, items])


def estimates(X, axis=0):
    """X：(…, 世帯, 3要素)。①要素ごとの平均の積 ②要素ごとの中央値の積 ③世帯ごとの積の平均 ④世帯ごとの積の中央値（年＝12倍、世帯数を掛ける前の1世帯あたり）"""
    prod = X.prod(-1)
    return {"mean_each": 12 * X.mean(axis).prod(-1), "median_each": 12 * np.median(X, axis).prod(-1),
            "mean_of_product": 12 * prod.mean(axis), "median_of_product": 12 * np.median(prod, axis)}


def evaluate(rng, kw, ns=NS, reps=REPS):
    X = town(rng, **kw)
    true_per_hh = 12 * X.prod(1).mean()
    full = {k: float(v / true_per_hh) for k, v in estimates(X).items()}
    full["true_total"] = float(true_per_hh * N_HH)
    full["median_over_mean_each"] = [float(np.median(X[:, j]) / X[:, j].mean()) for j in range(3)]
    samp = {}
    for n in ns:
        idx = rng.integers(0, N_HH, (reps, n))
        est = estimates(X[idx], axis=1)
        for k, v in est.items():
            ratio = v / true_per_hh
            lr = np.log(ratio)
            samp[(n, k)] = {"n": n, "method": k, "median_ratio": float(np.median(ratio)),
                            "p10_ratio": float(np.quantile(ratio, .1)), "p90_ratio": float(np.quantile(ratio, .9)),
                            "within_tol": float((np.abs(lr) <= math.log(TOL)).mean()),
                            "under_share": float((ratio < 1).mean())}
    return full, samp, X


def r(x, d=4):
    return round(float(x), d)


MNAME = {"mean_each": "①要素ごとの平均を掛ける", "median_each": "②要素ごとの中央値を掛ける",
         "mean_of_product": "③世帯ごとに掛けてから平均", "median_of_product": "④世帯ごとに掛けてから中央値"}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base_full, base_samp, X = evaluate(rng, BASE)
    corr_full, corr_samp, _ = evaluate(np.random.default_rng(SEED + 1), dict(BASE, rho=0.4))

    pd.DataFrame({"household": np.arange(1, N_HH + 1), "persons": X[:, 0].astype(int), "visits_per_month": X[:, 1].round(3),
                  "items_per_person_visit": X[:, 2].round(3), "items_per_year": (12 * X.prod(1)).round(2)}).to_csv(
        DATA / "households.csv", index=False)

    rows = []
    for case, samp in [("base", base_samp), ("rho0.4", corr_samp)]:
        for (n, k), v in samp.items():
            rows.append({"case": case, "method_name": MNAME[k], **{a: (r(b) if isinstance(b, float) else b) for a, b in v.items()}})
    sd = pd.DataFrame(rows)
    sd.to_csv(RES / "survey_by_n.csv", index=False)

    # 式の値（独立のとき）：中央値÷平均は 対数正規で exp(−σ²/2)
    f_v, f_i = math.exp(-BASE["sd_visits"] ** 2 / 2), math.exp(-BASE["sd_items"] ** 2 / 2)
    p_mean = float((PERSONS * P_PERSONS).sum())
    formula = {"persons_mean": r(p_mean), "persons_median": 2, "visits_median_over_mean": r(f_v), "items_median_over_mean": r(f_i), "persons_median_over_mean": r(2 / p_mean),
               "median_each_ratio_independent": r(f_v * f_i * 2 / p_mean),
               "mean_each_ratio_rho04": r(math.exp(-0.4 * BASE["sd_visits"] * BASE["sd_items"]))}

    # 確かめ：来店回数の散らばり × 相関 × 聞く世帯の数（27通り）
    grid, j = [], 0
    for sv in [0.4, 0.8, 1.2]:
        for rho in [0.0, 0.3, 0.6]:
            full, samp, _ = evaluate(np.random.default_rng(SEED * 100 + j), dict(BASE, sd_visits=sv, rho=rho), ns=[10, 30, 100], reps=2000)
            j += 1
            for n in [10, 30, 100]:
                grid.append({"sd_visits": sv, "rho": rho, "n": n,
                             "full_mean_each": r(full["mean_each"]), "full_median_each": r(full["median_each"]),
                             "within_mean_each": r(samp[(n, "mean_each")]["within_tol"]),
                             "within_median_each": r(samp[(n, "median_each")]["within_tol"]),
                             "within_mean_of_product": r(samp[(n, "mean_of_product")]["within_tol"]),
                             "medratio_median_each": r(samp[(n, "median_each")]["median_ratio"])})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    def S(case, n, m, key):
        return sd[(sd.case == case) & (sd.n == n) & (sd.method == m)][key].iloc[0]

    gf = g.drop_duplicates(["sd_visits", "rho"])
    out = {"base_setting": BASE, "n_households": N_HH, "persons_dist": dict(zip(PERSONS.tolist(), P_PERSONS.tolist())),
           "tolerance_factor": TOL, "reps": REPS,
           "full_town": {"base": {k: (r(v) if isinstance(v, float) else [r(x) for x in v]) for k, v in base_full.items()},
                         "rho0.4": {k: (r(v) if isinstance(v, float) else [r(x) for x in v]) for k, v in corr_full.items()}},
           "formula": formula,
           "headline": {"true_total": round(base_full["true_total"]),
                        "median_each_ratio": r(base_full["median_each"], 3), "mean_each_ratio": r(base_full["mean_each"], 3),
                        "median_of_product_ratio": r(base_full["median_of_product"], 3),
                        "median_each_formula": r(formula["median_each_ratio_independent"], 3),
                        "rho04_mean_each_ratio": r(corr_full["mean_each"], 3), "rho04_median_each_ratio": r(corr_full["median_each"], 3),
                        "n30_within_mean_each_pct": r(S("base", 30, "mean_each", "within_tol") * 100, 2),
                        "n30_within_median_each_pct": r(S("base", 30, "median_each", "within_tol") * 100, 2),
                        "n30_within_mean_of_product_pct": r(S("base", 30, "mean_of_product", "within_tol") * 100, 2),
                        "n10_within_mean_each_pct": r(S("base", 10, "mean_each", "within_tol") * 100, 2),
                        "n10_within_median_each_pct": r(S("base", 10, "median_each", "within_tol") * 100, 2),
                        "n300_within_mean_each_pct": r(S("base", 300, "mean_each", "within_tol") * 100, 2),
                        "n300_within_median_each_pct": r(S("base", 300, "median_each", "within_tol") * 100, 2),
                        "n10_mean_each_under_pct": r(S("base", 10, "mean_each", "under_share") * 100, 2),
                        "n10_mean_each_median_ratio": r(S("base", 10, "mean_each", "median_ratio"), 3)},
           "grid_summary": {"n_settings": int(len(gf)), "n_rows": int(len(g)),
                            "full_median_each_min": r(gf.full_median_each.min(), 3), "full_median_each_max": r(gf.full_median_each.max(), 3),
                            "full_mean_each_min": r(gf.full_mean_each.min(), 3), "full_mean_each_max": r(gf.full_mean_each.max(), 3),
                            "rows_median_beats_mean": int((g.within_median_each > g.within_mean_each).sum()),
                            "rows_product_beats_mean_each": int((g.within_mean_of_product > g.within_mean_each).sum()),
                            "rows_product_beats_mean_each_rho0": int(((g.within_mean_of_product > g.within_mean_each) & (g.rho == 0)).sum()),
                            "rows_rho0": int((g.rho == 0).sum()),
                            "rows_product_beats_mean_each_n100_rho_pos": int(((g.within_mean_of_product > g.within_mean_each) & (g.rho > 0) & (g.n == 100)).sum()),
                            "rows_n100_rho_pos": int(((g.rho > 0) & (g.n == 100)).sum()),
                            "within_median_each_max": r(g.within_median_each.max()),
                            "rows_median_beats_mean_detail": g[g.within_median_each > g.within_mean_each][["sd_visits", "rho", "n"]].to_dict("records")},
           "survey_by_n": sd.to_dict("records")}
    json.dump(out, open(RES / "a1042_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：町全体の値で掛けたときの、本当の値に対する比（0から）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    keys = ["mean_each", "median_each", "mean_of_product", "median_of_product"]
    x = np.arange(4)
    vb = [base_full[k] for k in keys]; vc = [corr_full[k] for k in keys]
    ax.bar(x - 0.2, vb, 0.4, color=BLUE, label="来店回数と個数は無関係（基本）")
    ax.bar(x + 0.2, vc, 0.4, color=ORANGE, label="来店の多い世帯ほど多く買う（相関0.4）")
    for xi, a, b in zip(x, vb, vc):
        ax.text(xi - 0.2, a + 0.02, f"{a:.3f}", ha="center", fontsize=8.5)
        ax.text(xi + 0.2, b + 0.02, f"{b:.3f}", ha="center", fontsize=8.5)
    ax.axhline(1, color=INK, lw=.8, ls="--")
    ax.set_xticks(x); ax.set_xticklabels([MNAME[k].replace("ごとの", "ごとの\n").replace("ごとに", "ごとに\n") for k in keys], fontsize=8.5)
    ax.set_ylim(0, 1.3); ax.set_ylabel("概算÷本当の値（倍）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title(f"要素ごとの中央値を掛けると、本当の{base_full['median_each']:.3f}倍")
    save(fig, "a1042_full_town.png", SRC)

    # 図2：聞く世帯の数と、1.2倍以内に入る割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cl = {"mean_each": BLUE, "median_each": ORANGE, "mean_of_product": GREEN}
    for k, c in cl.items():
        d = sd[(sd.case == "base") & (sd.method == k)]
        ax.plot(d.n, d.within_tol * 100, marker="o", color=c, label=MNAME[k])
        for x_, y_ in zip(d.n, d.within_tol * 100):
            dy = {"mean_each": 4.0, "median_each": 2.5, "mean_of_product": -6.5}[k]
            ax.text(x_ * 1.06, y_ + dy, f"{y_:.1f}%", fontsize=8, color=c)
    ax.set_xscale("log"); ax.set_xlim(8, 450); ax.set_xticks(NS); ax.set_xticklabels([str(n) for n in NS])
    ax.set_ylim(0, 105); ax.set_xlabel("聞いた世帯の数（対数の目盛り）"); ax.set_ylabel("本当の値の1.2倍以内に入る割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="center right")
    ax.set_title("中央値を掛けると、聞く世帯を増やしても当たらない")
    save(fig, "a1042_survey.png", SRC)

    # 図3：9通りの、町全体の中央値の積と平均の積
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(gf))
    ax.bar(x - 0.2, gf.full_mean_each, 0.4, color=BLUE, label="①要素ごとの平均を掛ける")
    ax.bar(x + 0.2, gf.full_median_each, 0.4, color=ORANGE, label="②要素ごとの中央値を掛ける")
    ax.axhline(1, color=INK, lw=.8, ls="--")
    ax.set_xticks(x); ax.set_xticklabels([f"{a}/{b}" for a, b in zip(gf.sd_visits, gf.rho)], fontsize=8.5)
    ax.set_xlabel("来店回数の散らばり（対数の標準偏差）／ 来店回数と個数の相関")
    ax.set_ylim(0, 1.3); ax.set_ylabel("町全体の値で掛けた概算÷本当の値（倍）")
    ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=2)
    ax.set_title("置き方9通り：散らばりが大きいほど中央値の積は小さく出る")
    save(fig, "a1042_grid.png", SRC)

    print(json.dumps(out["full_town"], ensure_ascii=False, indent=1))
    print(json.dumps(out["formula"], ensure_ascii=False, indent=1))
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, indent=1))
    print(sd.to_string()); print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
