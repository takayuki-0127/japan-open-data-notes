"""1095 リリースを細かく分けると、1回あたりの障害は減って見えるのか？（架空のデータ）

架空のアプリの開発チーム。半年（26週）に入れる変更の数を同じ1,200件に置き、
リリースの回数を月1回（6回）・2週に1回（13回）・週1回（26回）・毎営業日（130回）に変える。
変更1件ごとに、作成者が置いた確率で障害（リリースのあとに見つかる不具合）を起こす。
「1回あたりの障害」「障害のあった回の割合」「変更100件あたりの障害」「半年の障害の合計」を数える。
さらに、リリース1回ごとに起きる障害（作業の手順の分）と、同じ回に入った変更どうしの組み合わせで起きる障害を足し、
半年の合計が回数を増やすと増えるか減るかを確かめる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1095
SRC = "架空のアプリの開発チームの変更と障害（作成者が置いた起こしやすさからの乱数、seed 1095）"
N_CHANGES = 1200                  # 半年に入れる変更の数
CADENCES = {6: "月1回", 13: "2週に1回", 26: "週1回", 130: "毎営業日"}
P = 0.02                          # 変更1件が障害を起こす確率
Q_BASE, R_BASE = 0.03, 0.00005    # 1回ごとの障害の確率、同じ回の変更の組1組あたりの障害の起きやすさ
REPS = 4000
Q_GRID = [0.0, 0.01, 0.03, 0.1]
R_GRID = [0.0, 0.00002, 0.00005, 0.0002]
GRID_REPS = 4000
# 2つのアプリ：X は週1回で変更1件あたり2.5%、Y は月1回で2%
APP_X = {"k": 26, "p": 0.025}
APP_Y = {"k": 6, "p": 0.02}
RATIO_GRID = [1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0]
APP_REPS = 4000


def r(x, d=4):
    return round(float(x), d)


def simulate(rng, k, p, q, rr, reps, n=N_CHANGES):
    """reps 回の半年。各回の変更の数 m（多項分布）、障害の数（変更の分・回ごとの分・組み合わせの分）を返す"""
    m = rng.multinomial(n, np.ones(k) / k, size=reps)                  # (reps, k)
    inc_c = rng.binomial(m, p)
    inc_r = rng.binomial(1, q, size=m.shape) if q > 0 else np.zeros_like(m)
    inc_i = rng.poisson(rr * m * (m - 1) / 2) if rr > 0 else np.zeros_like(m)
    return m, inc_c, inc_r, inc_i


def summarize(m, inc, k, n=N_CHANGES):
    tot = inc.sum(1)
    return {"per_release": float(inc.mean()), "share_release_with_incident": float((inc > 0).mean()),
            "total_per_period": float(tot.mean()), "per_100_changes": float(tot.mean() / n * 100),
            "total_p10": float(np.percentile(tot, 10)), "total_p90": float(np.percentile(tot, 90)),
            "changes_per_release": float(m.mean())}


def expected_total(k, p, q, rr, n=N_CHANGES):
    """式どおりの半年の合計：n p + k q + rr × n(n−1)/(2k)"""
    return n * p + k * q + rr * n * (n - 1) / (2 * k)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 1) 変更1件ごとの障害だけ（基本）と、回ごと・組み合わせの分も足したとき
    rows = []
    keep = {}
    for scen, (q, rr) in {"change_only": (0.0, 0.0), "with_release_and_pairs": (Q_BASE, R_BASE)}.items():
        for k, lab in CADENCES.items():
            m, ic, ir, ii = simulate(rng, k, P, q, rr, REPS)
            inc = ic + ir + ii
            s = summarize(m, inc, k)
            s.update({"scenario": scen, "releases": k, "cadence": lab,
                      "formula_per_release": expected_total(k, P, q, rr) / k,
                      "formula_total": expected_total(k, P, q, rr),
                      "formula_share_with_incident_change_only": float(np.mean(1 - (1 - P) ** m)) if scen == "change_only" else None,
                      "from_changes": float(ic.sum(1).mean()), "from_release_steps": float(ir.sum(1).mean()),
                      "from_pairs": float(ii.sum(1).mean())})
            rows.append(s)
            if scen == "with_release_and_pairs" and k == 26:
                keep = {"m": m[0], "ic": ic[0], "ir": ir[0], "ii": ii[0]}
    cad = pd.DataFrame(rows)
    cols = ["scenario", "releases", "cadence", "changes_per_release", "per_release", "formula_per_release",
            "share_release_with_incident", "total_per_period", "formula_total", "total_p10", "total_p90",
            "per_100_changes", "from_changes", "from_release_steps", "from_pairs"]
    cad = cad[cols]
    cad.round(4).to_csv(RES / "by_cadence.csv", index=False)
    base = cad[cad.scenario == "change_only"].set_index("releases")
    mech = cad[cad.scenario == "with_release_and_pairs"].set_index("releases")

    # 半年ごとに「月1回の半年」と「週1回の半年」を比べたとき（変更だけの基本）
    rng2 = np.random.default_rng(SEED + 1)
    m6, a6, _, _ = simulate(rng2, 6, P, 0, 0, REPS)
    m26, a26, _, _ = simulate(rng2, 26, P, 0, 0, REPS)
    pr6, pr26 = a6.mean(1), a26.mean(1)
    t6, t26 = a6.sum(1), a26.sum(1)
    pair_cmp = {"share_per_release_lower_weekly": r(np.mean(pr26 < pr6)),
                "share_total_lower_weekly": r(np.mean(t26 < t6)),
                "share_total_equal": r(np.mean(t26 == t6)),
                "share_total_higher_weekly": r(np.mean(t26 > t6)),
                "median_per_release_ratio_weekly_to_monthly": r(np.median(pr26 / pr6)),
                "note": "どちらも変更1件あたり2%で、本当の起こしやすさは同じ"}

    # 2) 2つのアプリ：X（週1回、2.5%）と Y（月1回、2%）
    rng3 = np.random.default_rng(SEED + 2)
    mx, ax_, _, _ = simulate(rng3, APP_X["k"], APP_X["p"], 0, 0, APP_REPS)
    my, ay, _, _ = simulate(rng3, APP_Y["k"], APP_Y["p"], 0, 0, APP_REPS)
    apps = {"X": {**APP_X, "per_release": r(ax_.mean()), "per_100_changes": r(ax_.sum(1).mean() / N_CHANGES * 100),
                  "share_release_with_incident": r((ax_ > 0).mean())},
            "Y": {**APP_Y, "per_release": r(ay.mean()), "per_100_changes": r(ay.sum(1).mean() / N_CHANGES * 100),
                  "share_release_with_incident": r((ay > 0).mean())},
            "share_X_looks_better_per_release": r(np.mean(ax_.mean(1) < ay.mean(1))),
            "share_X_looks_better_share_with_incident": r(np.mean((ax_ > 0).mean(1) < (ay > 0).mean(1))),
            "share_Y_better_per_100_changes": r(np.mean(ay.sum(1) < ax_.sum(1))),
            "share_tie_per_100_changes": r(np.mean(ay.sum(1) == ax_.sum(1))),
            "formula_per_release_X": r(N_CHANGES * APP_X["p"] / APP_X["k"]),
            "formula_per_release_Y": r(N_CHANGES * APP_Y["p"] / APP_Y["k"]),
            "formula_ratio_limit": r(APP_X["k"] / APP_Y["k"])}
    # X の起こしやすさを Y の何倍に置くかを変える
    arow = []
    for ratio in RATIO_GRID:
        px = APP_Y["p"] * ratio
        g = np.random.default_rng(SEED * 10 + int(ratio * 100))
        _, bx, _, _ = simulate(g, APP_X["k"], px, 0, 0, APP_REPS)
        _, by, _, _ = simulate(g, APP_Y["k"], APP_Y["p"], 0, 0, APP_REPS)
        arow.append({"p_ratio_X_to_Y": ratio, "p_X": r(px), "per_release_X": r(bx.mean()), "per_release_Y": r(by.mean()),
                     "share_X_looks_better_per_release": r(np.mean(bx.mean(1) < by.mean(1))),
                     "share_X_better_per_100_changes": r(np.mean(bx.sum(1) < by.sum(1))),
                     "share_Y_better_per_100_changes": r(np.mean(by.sum(1) < bx.sum(1)))})
    apps_grid = pd.DataFrame(arow)
    apps_grid.to_csv(RES / "two_apps.csv", index=False)

    # 3) 確かめ：回ごとの障害 q × 組み合わせの起きやすさ r（16通り）
    grid = []
    for q in Q_GRID:
        for rr in R_GRID:
            row = {"q_per_release": q, "r_per_pair": rr}
            g = np.random.default_rng(SEED * 1000 + Q_GRID.index(q) * 10 + R_GRID.index(rr))
            for k in CADENCES:
                m, ic, ir, ii = simulate(g, k, P, q, rr, GRID_REPS)
                inc = ic + ir + ii
                row[f"per_release_k{k}"] = r(inc.mean())
                row[f"total_k{k}"] = r(inc.sum(1).mean())
                row[f"formula_total_k{k}"] = r(expected_total(k, P, q, rr))
            row["per_release_ratio_k26_k6"] = r(row["per_release_k26"] / row["per_release_k6"])
            row["total_ratio_k26_k6"] = r(row["total_k26"] / row["total_k6"])
            row["total_ratio_k130_k6"] = r(row["total_k130"] / row["total_k6"])
            row["formula_total_ratio_k26_k6"] = r(row["formula_total_k26"] / row["formula_total_k6"])
            grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # data：週1回・しくみを足した半年の1回分
    one = pd.DataFrame({"release": [f"R{i:02d}" for i in range(1, 27)], "changes": keep["m"],
                        "incidents_from_changes": keep["ic"], "incidents_from_release_steps": keep["ir"],
                        "incidents_from_pairs": keep["ii"]})
    one["incidents"] = one.incidents_from_changes + one.incidents_from_release_steps + one.incidents_from_pairs
    one.to_csv(DATA / "weekly_one_period.csv", index=False)

    out = {
        "settings": {"n_changes_half_year": N_CHANGES, "cadences": CADENCES, "p_per_change": P,
                     "q_per_release_base": Q_BASE, "r_per_pair_base": R_BASE, "reps": REPS,
                     "q_grid": Q_GRID, "r_grid": R_GRID, "grid_reps": GRID_REPS, "app_X": APP_X, "app_Y": APP_Y,
                     "ratio_grid": RATIO_GRID, "app_reps": APP_REPS, "seed": SEED},
        "change_only": {int(k): {c: r(v) for c, v in row.items() if c != "scenario" and not isinstance(v, str) and v is not None}
                        for k, row in base.iterrows()},
        "change_only_per_release_ratio_k26_to_k6": r(base.loc[26, "per_release"] / base.loc[6, "per_release"]),
        "formula_per_release_ratio_k26_to_k6": r(6 / 26),
        "formula_per_release_ratio_k130_to_k6": r(6 / 130),
        "with_pairs_total_ratio_k26_to_k6": r(mech.loc[26, "total_per_period"] / mech.loc[6, "total_per_period"]),
        "with_pairs_total_ratio_k130_to_k6": r(mech.loc[130, "total_per_period"] / mech.loc[6, "total_per_period"]),
        "change_only_per_release_ratio_k130_to_k6": r(base.loc[130, "per_release"] / base.loc[6, "per_release"]),
        "with_release_and_pairs": {int(k): {c: r(v) for c, v in row.items() if c != "scenario" and not isinstance(v, str) and v is not None}
                                   for k, row in mech.iterrows()},
        "monthly_vs_weekly_period_compare": pair_cmp,
        "two_apps": apps,
        "two_apps_grid": apps_grid.to_dict("records"),
        "grid_16": grid.to_dict("records"),
        "grid_ranges": {k: [r(grid[k].min()), r(grid[k].max())] for k in
                        ["per_release_ratio_k26_k6", "total_ratio_k26_k6", "total_ratio_k130_k6"]},
        "grid_counts": {"per_release_lower_k26": int((grid.per_release_ratio_k26_k6 < 1).sum()),
                        "total_lower_k26": int((grid.total_ratio_k26_k6 < 0.99).sum()),
                        "total_higher_k26": int((grid.total_ratio_k26_k6 > 1.01).sum()),
                        "total_within_1pct_k26": int(((grid.total_ratio_k26_k6 >= 0.99) & (grid.total_ratio_k26_k6 <= 1.01)).sum()),
                        "n": len(grid)},
        "grid_max_abs_diff_total_vs_formula": r(max(abs(grid[f"total_k{k}"] - grid[f"formula_total_k{k}"]).max() for k in CADENCES)),
    }
    json.dump(out, open(RES / "a1095_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：変更だけの基本で、1回あたりと変更100件あたり
    ks = list(CADENCES)
    labs = [f"{CADENCES[k]}\n（{k}回）" for k in ks]
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 4.0))
    x = np.arange(len(ks))
    v1 = base.loc[ks, "per_release"].values
    v2 = base.loc[ks, "share_release_with_incident"].values * 100
    v3 = base.loc[ks, "per_100_changes"].values
    for ax, v, c, fmt, yl, tt in [
            (axs[0], v1, ORANGE, "{:.2f}件", "1回あたりの障害（件）", "1回あたりの障害は回数に反比例して減る"),
            (axs[1], v2, ORANGE, "{:.1f}%", "障害のあった回の割合（%）", "障害のあった回の割合も下がる"),
            (axs[2], v3, BLUE, "{:.2f}件", "変更100件あたりの障害（件）", "変更100件あたりは変わらない")]:
        ax.bar(x, v, color=c, width=0.6)
        for i, y in enumerate(v):
            ax.text(i, y * 1.02 + 0.01 * max(v), fmt.format(y), ha="center", va="bottom", fontsize=8.5)
        ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=8.5); ax.set_ylim(0, max(v) * 1.22)
        ax.set_ylabel(yl); ax.set_title(tt, fontsize=11)
    axs[2].set_ylim(0, 4)
    fig.suptitle(f"半年に同じ1,200件の変更・変更1件あたり{P*100:.0f}%で障害（{REPS:,}回の平均）：月1回{v1[0]:.2f}件→週1回{v1[2]:.2f}件（式どおり）",
                 fontsize=12, y=1.03)
    save(fig, "a1095_per_release.png", SRC, y=-0.03)

    # 図2：2つのアプリ。X の起こしやすさを Y の何倍に置くか
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    xr = np.arange(len(apps_grid))
    wdt = 0.38
    ax.bar(xr - wdt / 2, apps_grid.share_X_looks_better_per_release * 100, wdt, color=ORANGE,
           label="「1回あたりの障害」で X のほうが少なく出た半年")
    ax.bar(xr + wdt / 2, apps_grid.share_X_better_per_100_changes * 100, wdt, color=BLUE,
           label="「変更100件あたり」で X のほうが少なく出た半年")
    for i, row in apps_grid.iterrows():
        ax.text(i - wdt / 2, row.share_X_looks_better_per_release * 100 + 1.5, f"{row.share_X_looks_better_per_release*100:.1f}",
                ha="center", fontsize=7.5)
        ax.text(i + wdt / 2, row.share_X_better_per_100_changes * 100 + 1.5, f"{row.share_X_better_per_100_changes*100:.1f}",
                ha="center", fontsize=7.5)
    ax.set_xticks(xr); ax.set_xticklabels([f"{v:g}倍" for v in apps_grid.p_ratio_X_to_Y])
    ax.set_xlabel("X（週1回）の変更1件あたりの起こしやすさ ÷ Y（月1回）の起こしやすさ（Y は2%）")
    ax.set_ylabel("半年の割合（%、各4,000回）"); ax.set_ylim(0, 120); ax.set_yticks(range(0, 101, 20))
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("週1回の X は、Y より起こしやすくても「1回あたり」では少なく出やすい（式では4.33倍まで）", fontsize=11)
    save(fig, "a1095_two_apps.png", SRC, y=-0.06)

    # 図3：確かめ（16通り）。週1回÷月1回の比（対数の目盛り、1倍が「同じ」）
    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    xg = np.arange(len(grid))
    ax.axhline(1, color=GRAY, lw=1)
    ax.plot(xg, grid.per_release_ratio_k26_k6, "o", color=ORANGE, label="1回あたりの障害（週1回÷月1回）")
    ax.plot(xg, grid.total_ratio_k26_k6, "s", color=BLUE, label="半年の障害の合計（週1回÷月1回）")
    ax.set_yscale("log")
    ax.set_yticks([0.15, 0.2, 0.3, 0.5, 1, 1.5, 2]); ax.set_yticklabels(["0.15", "0.2", "0.3", "0.5", "1", "1.5", "2"]); ax.set_ylim(0.12, 2.2); ax.minorticks_off()
    ax.set_xticks(xg)
    ax.set_xticklabels([f"q={row.q_per_release:g}\nr={row.r_per_pair*1e5:g}" for row in grid.itertuples()], fontsize=7.2)
    ax.set_xlabel("q：1回ごとに手順で障害が起きる確率　r：同じ回の変更の組1組あたりの起きやすさ（×10万分の1）")
    ax.set_ylabel("週1回 ÷ 月1回（倍、対数の目盛り）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("16通りの置き方：1回あたりはどれも下がるが、合計は置き方で上にも下にも動く", fontsize=11.5)
    save(fig, "a1095_grid.png", SRC, y=-0.08)

    print(cad.round(4).to_string())
    print(json.dumps({k: out[k] for k in ["monthly_vs_weekly_period_compare", "two_apps", "grid_ranges", "grid_counts",
                                          "grid_max_abs_diff_total_vs_formula"]}, ensure_ascii=False, indent=1))
    print(apps_grid.to_string()); print(grid[["q_per_release", "r_per_pair", "per_release_ratio_k26_k6", "total_ratio_k26_k6",
                                               "formula_total_ratio_k26_k6", "total_ratio_k130_k6"]].to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
