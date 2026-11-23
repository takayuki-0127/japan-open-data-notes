"""995 「前年比120%」の来場は、新しい人か、来る回数が増えたのか？（架空のデータ）

架空の植物園。来る可能性のある人を20万人置き、人ごとの1年に来る回数の平均（来やすさ）をガンマ分布で置く
（平均0.5回、形 k=0.5）。年ごとの来やすさは、人ごとのもとの値に、年ごとに引き直す揺れ（対数で標準偏差 σ=0.5、平均は変えない）をかける。
2年目に延べが1.2倍になる道を4つ置く：変化なし（1.0倍）、新しい人だけ（来る可能性のある人を1.2倍）、
回数だけ（全員の来やすさを1.2倍）、半々（人も来やすさも √1.2 倍）。来た人は全員見分けられる（会員証など）と置き、
前年に来た人・来ていない人に分けて数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 995
SRC = "架空の植物園の来場（作成者が乱数で作成、seed 995）"
BASE = {"N": 200000, "mu": 0.5, "k": 0.5, "sigma": 0.5}
G = 1.2
SCEN = {"変化なし": (1.0, 1.0), "新しい人だけ": (G, 1.0), "回数だけ": (1.0, G), "半々": (G ** 0.5, G ** 0.5)}
REPS = 30
GRID = {"k": [0.2, 0.5, 1.0, 2.0], "mu": [0.25, 0.5, 1.0], "sigma": [0.0, 0.5, 1.0]}
GRID_REPS = 5


def simulate(rng, N, mu, k, sigma, people_mult, rate_mult):
    """人ごとの来やすさ（もと）に、年ごとの揺れをかける。揺れは2年とも同じ分布なので、変化なしなら2年の分布は同じ"""
    n_new = int(round(N * (people_mult - 1)))
    base = rng.gamma(k, mu / k, N + n_new)
    yr = lambda: np.exp(rng.normal(0, sigma, N + n_new) - sigma ** 2 / 2) if sigma > 0 else np.ones(N + n_new)
    lam1 = base * yr()
    lam2 = base * yr() * rate_mult
    is_new = np.r_[np.zeros(N, bool), np.ones(n_new, bool)]     # 新しく来る可能性のできた人
    lam1[is_new] = 0.0
    v1 = rng.poisson(lam1)
    v2 = rng.poisson(lam2)
    return v1, v2, is_new, np.where(is_new, np.nan, lam1), lam2


def measure(v1, v2, is_new):
    tot1, tot2 = v1.sum(), v2.sum()
    u1, u2 = (v1 > 0).sum(), (v2 > 0).sum()
    came1 = v1 > 0
    fresh2 = (v2 > 0) & ~came1                      # 今年来た人のうち、前年に来ていない人
    return {"total_ratio": tot2 / tot1, "unique_ratio": u2 / u1, "per_person_ratio": (tot2 / u2) / (tot1 / u1),
            "unique_share_of_growth_pct": np.log(u2 / u1) / np.log(tot2 / tot1) * 100 if abs(np.log(tot2 / tot1)) > 0.05 else np.nan,
            "fresh_share_people_pct": fresh2.sum() / u2 * 100,
            "fresh_share_total_pct": v2[fresh2].sum() / tot2 * 100,
            "truly_new_share_people_pct": ((v2 > 0) & is_new).sum() / u2 * 100,
            "returning_cohort_ratio": v2[came1].sum() / v1[came1].sum(),
            "returning_rate_pct": (came1 & (v2 > 0)).sum() / u1 * 100,
            "fresh_total_pct_of_y1": (v2[~came1].sum()) / tot1 * 100}


def main():
    t0 = time.time()
    rows = []
    for si, (name, (pm, rm)) in enumerate(SCEN.items()):
        for r in range(REPS):
            rng = np.random.default_rng(SEED * 1000 + si * 100 + r)
            v1, v2, is_new, l1, l2 = simulate(rng, BASE["N"], BASE["mu"], BASE["k"], BASE["sigma"], pm, rm)
            rows.append({"scenario": name, "rep": r, **measure(v1, v2, is_new)})
            if name == "回数だけ" and r == 0:
                m = (v1 > 0) | (v2 > 0)
                pd.DataFrame({"person_id": np.arange(1, m.size + 1)[m], "rate_y1": np.round(l1[m], 4),
                              "rate_y2": np.round(l2[m], 4), "visits_y1": v1[m], "visits_y2": v2[m]}).to_csv(
                    DATA / "people_example_frequency_only.csv", index=False)
    sim = pd.DataFrame(rows)
    sm = sim.groupby("scenario", sort=False).mean(numeric_only=True).drop(columns="rep")
    sm.round(4).to_csv(RES / "scenarios_30reps.csv")

    # 式：回数だけ・揺れなしのときの実人数の比（ガンマ・ポアソンの式）
    k, mu = BASE["k"], BASE["mu"]
    p1 = 1 - (k / (k + mu)) ** k
    unique_formula_freq = (1 - (k / (k + G * mu)) ** k) / p1
    elam = mu - k * (mu / k) * (1 + mu / k) ** (-(k + 1))            # E[λ・1(1回以上)]
    cohort_formula_s0_sig0 = elam / mu                                   # 揺れなしのときの前年に来た人の比（変化なし）

    # 確かめ：k × 平均 × 揺れ の36通り（回数だけ・新しい人だけ・変化なし、各5回）
    grid = []
    gi = 0
    for kk in GRID["k"]:
        for mm in GRID["mu"]:
            for sg in GRID["sigma"]:
                for name in ["変化なし", "新しい人だけ", "回数だけ"]:
                    pm, rm = SCEN[name]
                    acc = [measure(*simulate(np.random.default_rng(SEED * 100000 + gi * 10 + r), 200000, mm, kk, sg, pm, rm)[:3])
                           for r in range(GRID_REPS)]
                    grid.append({"k": kk, "mu": mm, "sigma": sg, "scenario": name, **pd.DataFrame(acc).mean().to_dict()})
                    gi += 1
    grid = pd.DataFrame(grid)
    grid.round(4).to_csv(RES / "sensitivity_grid.csv", index=False)
    gf = grid[grid.scenario == "回数だけ"]
    g0 = grid[grid.scenario == "変化なし"]
    ga = grid[grid.scenario == "新しい人だけ"]
    gf0 = gf[gf.sigma == 0]
    fml = (1 - (gf0.k / (gf0.k + G * gf0.mu)) ** gf0.k) / (1 - (gf0.k / (gf0.k + gf0.mu)) ** gf0.k)

    r3 = lambda x: round(float(x), 3)
    rng_ = lambda s: [r3(s.min()), r3(s.max())]
    out = {
        "setting": {**BASE, "growth": G, "reps": REPS, "scenarios": {k_: list(v) for k_, v in SCEN.items()}},
        "scenarios_mean": {n: {c: r3(v) for c, v in row.items()} for n, row in sm.iterrows()},
        "fresh_share_gap_newonly_minus_nochange_pct": r3(sm.loc["新しい人だけ", "fresh_share_people_pct"] -
                                                         sm.loc["変化なし", "fresh_share_people_pct"]),
        "formula": {"unique_ratio_frequency_only_sigma0": r3(unique_formula_freq),
                    "returning_cohort_ratio_nochange_sigma0": r3(cohort_formula_s0_sig0),
                    "returning_cohort_ratio_frequency_only_sigma0": r3(cohort_formula_s0_sig0 * G)},
        "grid": {"n_settings": int(len(gf)),
                 "frequency_only": {c: rng_(gf[c]) for c in ["unique_ratio", "unique_share_of_growth_pct",
                                                            "fresh_share_people_pct", "fresh_share_total_pct",
                                                            "returning_cohort_ratio", "total_ratio"]},
                 "frequency_only_n_cohort_below_1": int((gf.returning_cohort_ratio < 1).sum()),
                 "frequency_only_n_cohort_below_growth": int((gf.returning_cohort_ratio < G).sum()),
                 "sigma0_k05_mu05": {n: {"returning_cohort_ratio": r3(grid[(grid.k == 0.5) & (grid.mu == 0.5) & (grid.sigma == 0) &
                                                                         (grid.scenario == n)].returning_cohort_ratio.iloc[0]),
                                         "unique_ratio": r3(grid[(grid.k == 0.5) & (grid.mu == 0.5) & (grid.sigma == 0) &
                                                                 (grid.scenario == n)].unique_ratio.iloc[0])}
                                     for n in ["変化なし", "回数だけ"]},
                 "frequency_only_sigma0_unique_formula_max_gap": r3((gf0.unique_ratio.values - fml.values).__abs__().max()),
                 "nochange": {c: rng_(g0[c]) for c in ["fresh_share_people_pct", "returning_cohort_ratio", "unique_ratio"]},
                 "new_only": {c: rng_(ga[c]) for c in ["fresh_share_people_pct", "returning_cohort_ratio", "unique_ratio",
                                                        "per_person_ratio"]},
                 "fresh_people_gap_newonly_minus_freq_pct": rng_(ga.fresh_share_people_pct.values - gf.fresh_share_people_pct.values),
                 "unique_ratio_gap_newonly_minus_freq": rng_(ga.unique_ratio.values - gf.unique_ratio.values)},
    }
    json.dump(out, open(RES / "a995_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    names = list(SCEN)
    # 図1：4つの道の、延べ・実人数・1人あたり回数の比
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    w = 0.26
    for j, (c, lab, col) in enumerate([("total_ratio", "延べ", INK), ("unique_ratio", "実人数", BLUE),
                                       ("per_person_ratio", "1人あたりの回数", ORANGE)]):
        ys = sm.loc[names, c].values
        ax.bar(np.arange(4) + (j - 1) * w, ys, w, color=col, label=lab)
        for i, y in enumerate(ys):
            ax.text(i + (j - 1) * w, y + 0.01, f"{y:.2f}", ha="center", fontsize=8)
    ax.set_xticks(np.arange(4), names); ax.set_ylim(0.9, 1.3); ax.axhline(1, color=GRAY, lw=1)
    ax.set_ylabel("2年目 ÷ 1年目（30回の平均）"); ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper left")
    ax.set_title("回数だけ増やしても、実人数は増えて見える", fontsize=12)
    save(fig, "a995_scenarios.png", SRC)

    # 図2：2年目の延べの内訳（1年目の延べ=100）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ret = sm.loc[names, "returning_cohort_ratio"].values * (100 - 0)   # 前年に来た人の延べ（1年目の延べ=100）
    fresh = sm.loc[names, "fresh_total_pct_of_y1"].values
    ax.bar(np.arange(4), ret, 0.55, color=BLUE, label="前年に来た人の延べ")
    ax.bar(np.arange(4), fresh, 0.55, bottom=ret, color=ORANGE, label="前年に来ていない人の延べ")
    ax.axhline(100, color=INK, lw=1, ls="--"); ax.text(-0.45, 102, "1年目の延べ", fontsize=9, ha="left")
    for i in range(4):
        ax.text(i, ret[i] / 2, f"{ret[i]:.1f}", ha="center", color="white", fontsize=9)
        ax.text(i, ret[i] + fresh[i] * 0.72, f"{fresh[i]:.1f}", ha="center", color="white", fontsize=9)
    ax.set_xticks(np.arange(4), names); ax.set_ylabel("1年目の延べを100としたときの2年目の延べ")
    ax.set_ylim(0, 150); ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=2)
    ax.set_title("どの道でも、前年に来た人の延べは減り、増えた分は前年に来ていない人に見える", fontsize=11)
    save(fig, "a995_split.png", SRC)

    # 図3：回数だけ1.2倍の36通りで、前年に来た人の延べの比
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    mk = {0.25: "o", 0.5: "s", 1.0: "^"}
    cl = {0.2: LIGHT, 0.5: BLUE, 1.0: GREEN, 2.0: ORANGE}
    for i, sg in enumerate(GRID["sigma"]):
        g = gf[gf.sigma == sg]
        for _, row in g.iterrows():
            ax.scatter(i + (GRID["k"].index(row.k) - 1.5) * 0.12, row.returning_cohort_ratio, marker=mk[row.mu],
                       color=cl[row.k], s=30)
    ax.axhline(G, color=INK, lw=1, ls="--"); ax.text(2.45, G + 0.01, "全員の本当の伸び（1.2倍）", fontsize=9, ha="right")
    ax.axhline(1, color=GRAY, lw=1, ls=":")
    for kk in GRID["k"]:
        ax.scatter([], [], color=cl[kk], marker="o", label=f"k={kk}")
    for mm in GRID["mu"]:
        ax.scatter([], [], color=GRAY, marker=mk[mm], label=f"平均{mm}回")
    ax.legend(frameon=False, fontsize=8.5, loc="center left", bbox_to_anchor=(1.0, 0.5))
    ax.set_xticks(range(3), [f"揺れ σ={s}" for s in GRID["sigma"]]); ax.set_xlabel("人ごとの来やすさの年ごとの揺れ")
    ax.set_ylabel("前年に来た人の延べ：2年目 ÷ 1年目"); ax.set_ylim(0.2, 1.3)
    ax.set_title("全員が1.2倍来るようになっても、前年に来た人の延べは36通りすべてで1.2倍を下回る", fontsize=10.5)
    save(fig, "a995_robust.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
