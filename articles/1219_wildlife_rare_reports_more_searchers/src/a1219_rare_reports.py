"""1219 珍しい種の報告が増えたのは、種が増えたからか、探す人が増えたからか？（架空のデータ）

架空の森「B森」の珍しい種Rと、よく見られる種C。生き物を見に来る人（観察する人）が10年で増え、
あとから来た人は初めは見つけるのが下手で、続けるうちに上手になる、と作成者が置く。
観察1回ごとに、種R・種Cが見つかったかを記録する（見つかったら必ず報告する）。
報告の数え方5つで、種Rの10年の変化がどう見えるかを、本当の変化（横ばい・+30%・−30%）と比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1219
SRC = "架空の森と観察の記録（作成者が乱数で作成、seed 1219）"
YEARS = 10
M0 = 40              # 1年目の観察する人
A_R, A_C = 0.06, 0.8  # 見つけやすさ（種R・種C）：1回で見つかる確率 = 1 − exp(−a × 数 × 腕前)
CAP = 1.5            # 上手になる上限（初めの腕前の倍）
MEASURES = {"m1_reports": "①報告の件数",
            "m2_per_person": "②1人あたりの報告",
            "m3_per_visit": "③観察1回あたりの報告",
            "m4_ratio_common": "④種Cが見つかった回に対する種Rの割合",
            "m5_founders": "⑤1年目からいる人だけの1回あたり"}


def simulate(rng, reps, growth=4.0, new_skill=0.7, learn=0.06, true_change=0.0, target=0.0):
    """年ごとの集計（reps×年）を返す"""
    m_end = int(round(M0 * growth))
    M = np.round(M0 + (m_end - M0) * np.arange(YEARS) / (YEARS - 1)).astype(int)
    P = m_end
    join = np.zeros(P, int)
    for y in range(1, YEARS):
        join[M[y - 1]:M[y]] = y
    founder = join == 0
    s0 = np.exp(rng.normal(0, 0.4, (reps, P)) - 0.08)          # 平均がほぼ1
    s0 = np.where(founder[None, :], s0, s0 * new_skill)
    vrate = np.exp(rng.normal(np.log(10) - 0.08, 0.4, (reps, P)))  # 1年の観察の回数の見込み（平均ほぼ10回）
    D = (1 + true_change) ** (np.arange(YEARS) / (YEARS - 1))      # 種Rの本当の数（1年目を1）
    out = {k: np.zeros((reps, YEARS)) for k in ["R", "C", "V", "M", "Rf", "Vf"]}
    for y in range(YEARS):
        act = join <= y
        t = np.clip(y - join, 0, None)
        s = s0 * np.minimum(CAP, (1 + learn) ** t)[None, :]
        v = rng.poisson(vrate) * act[None, :]
        pr = 1 - np.exp(-A_R * D[y] * s)
        if target > 0 and y >= 5:
            # 6年目から、あとから来た人の観察のうち target の割合は、報告のあった場所をねらう（見つかりやすさ3倍）
            pr_t = 1 - np.exp(-A_R * 3 * D[y] * s)
            pr = np.where(founder[None, :], pr, (1 - target) * pr + target * pr_t)
        pc = 1 - np.exp(-A_C * s)
        r_ = rng.binomial(v, pr)
        c_ = rng.binomial(v, pc)
        out["R"][:, y] = r_.sum(1); out["C"][:, y] = c_.sum(1); out["V"][:, y] = v.sum(1)
        out["M"][:, y] = act.sum(); out["Rf"][:, y] = r_[:, founder].sum(1); out["Vf"][:, y] = v[:, founder].sum(1)
    return out, D, M


def measures(o):
    return {"m1_reports": o["R"], "m2_per_person": o["R"] / o["M"], "m3_per_visit": o["R"] / o["V"],
            "m4_ratio_common": o["R"] / o["C"], "m5_founders": o["Rf"] / o["Vf"]}


def change(x):
    """終わりの2年の平均 ÷ 初めの2年の平均 − 1"""
    return x[:, -2:].mean(1) / x[:, :2].mean(1) - 1


def r(x, k=4):
    return round(float(x), k)


def main():
    REPS = 400
    rows = []
    ex_saved = None
    for sc, tc in [("横ばい", 0.0), ("+30%", 0.3), ("−30%", -0.3)]:
        o, D, M = simulate(np.random.default_rng(SEED + int(tc * 100) + 30), REPS, true_change=tc)
        if ex_saved is None:
            ex_saved = (o, D, M)
        truth = D[-2:].mean() / D[:2].mean() - 1
        for k, x in measures(o).items():
            ch = change(x)
            rows.append({"scenario": sc, "true_change": r(truth), "measure": MEASURES[k], "key": k,
                         "change_mean": r(ch.mean()), "change_p10": r(np.quantile(ch, .1)),
                         "change_p90": r(np.quantile(ch, .9)), "p_up10": r((ch > 0.10).mean()),
                         "p_down10": r((ch < -0.10).mean())})
    main_tab = pd.DataFrame(rows)
    main_tab.to_csv(RES / "by_scenario.csv", index=False)

    # 腕前の中身：横ばいで、③と⑤の平均の腕前（観察の回数の重み）の変化の式どおりの見込み
    # 見つかる確率が小さいとき、1回あたりの報告は「数×平均の腕前」にほぼ比例する
    o, D, M = ex_saved

    # 見つけるのが上手になる・あとから来る人の腕前・人の増え方（27通り、横ばい）
    grid = []
    gi = 0
    for gr in [1.0, 2.0, 4.0]:
        for ns in [0.4, 0.7, 1.0]:
            for le in [0.0, 0.03, 0.06]:
                gi += 1
                oo, _, _ = simulate(np.random.default_rng(SEED * 100 + gi), 200, growth=gr, new_skill=ns, learn=le)
                row = {"growth": gr, "new_skill": ns, "learn": le}
                for k, x in measures(oo).items():
                    row[k] = r(change(x).mean())
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_flat.csv", index=False)

    # 報告のあった場所をねらう人がまざる（横ばい・+30%）
    trows = []
    for tg in [0.0, 0.1, 0.2]:
        for sc, tc in [("横ばい", 0.0), ("+30%", 0.3)]:
            oo, D2, _ = simulate(np.random.default_rng(SEED * 1000 + int(tg * 100) + int(tc * 10)), 300, true_change=tc, target=tg)
            for k, x in measures(oo).items():
                trows.append({"target_share": tg, "scenario": sc, "true_change": r(D2[-2:].mean() / D2[:2].mean() - 1),
                              "measure": MEASURES[k], "change_mean": r(change(x).mean())})
    target = pd.DataFrame(trows)
    target.to_csv(RES / "targeting.csv", index=False)

    # data：横ばいの例の1回の年ごとの集計
    ex = pd.DataFrame({"year": np.arange(1, YEARS + 1), "true_number_R": np.round(D, 4), "people": M,
                       "visits": o["V"][0].astype(int), "reports_R": o["R"][0].astype(int),
                       "found_C": o["C"][0].astype(int), "founder_visits": o["Vf"][0].astype(int),
                       "founder_reports_R": o["Rf"][0].astype(int)})
    ex.to_csv(DATA / "example_flat_by_year.csv", index=False)
    # 横ばいの400回の年ごとの平均（5つの数え方、1年目を1とした値）
    mm = measures(o)
    avg = pd.DataFrame({"year": np.arange(1, YEARS + 1)})
    for k, x in mm.items():
        avg[k] = np.round((x / x[:, :1]).mean(0), 4)
    avg.to_csv(RES / "flat_by_year_index.csv", index=False)

    flat = main_tab[main_tab.scenario == "横ばい"].set_index("key")
    g = grid
    gstat = {}
    for k in MEASURES:
        gstat[k] = {"min": r(g[k].min()), "max": r(g[k].max()), "n_within_10": int((g[k].abs() <= 0.10).sum())}
    gsub = g[(g.growth > 1)]
    out = {"setting": {"years": YEARS, "people_year1": M0, "people_year10": int(M[-1]), "visits_mean_per_person": 10,
                       "new_skill": 0.7, "learn_per_year": 0.06, "learn_cap": CAP, "reps": REPS},
           "by_scenario": main_tab.to_dict("records"),
           "grid_flat_27": gstat,
           "grid_flat_growth_gt1_18": {k: {"min": r(gsub[k].min()), "max": r(gsub[k].max())} for k in MEASURES},
           "grid_flat_learn0_9": {k: {"min": r(g[g.learn == 0][k].min()), "max": r(g[g.learn == 0][k].max())} for k in MEASURES},
           "grid_m4_closer_than_m3": int((g.m4_ratio_common.abs() < g.m3_per_visit.abs()).sum()),
           "targeting": target.to_dict("records")}
    json.dump(out, open(RES / "a1219_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：横ばいでの5つの数え方の年ごとの見え方
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    cols = [ORANGE, GRAY, BLUE, GREEN, INK]
    for (k, name), c in zip(MEASURES.items(), cols):
        ax.plot(avg.year, avg[k], marker="o", ms=4, color=c, label=name)
    ax.axhline(1, color=GRAY, lw=1, ls="--")
    ax.text(9.9, 0.94, "本当（横ばい）", fontsize=8.5, color=GRAY, va="top", ha="right")
    ax.set_yscale("log"); ax.set_yticks([0.5, 1, 2, 4]); ax.set_yticklabels(["0.5", "1", "2", "4"])
    ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xticks(avg.year); ax.set_xlabel("年"); ax.set_ylabel("1年目を1とした値（対数の目盛り、400回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("種Rは本当は横ばい：観察する人が4倍になると、数え方ごとに違って見える")
    save(fig, "a1219_flat_years.png", SRC)

    # 図2：3つの本当の変化と、5つの数え方の10年の変化
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    scs = ["−30%", "横ばい", "+30%"]
    w = 0.15
    for i, (k, name) in enumerate(MEASURES.items()):
        vals = [main_tab[(main_tab.scenario == s) & (main_tab.key == k)].change_mean.iloc[0] * 100 for s in scs]
        ax.bar(np.arange(3) + (i - 2) * w, vals, width=w, color=cols[i], label=name)
    tv = [main_tab[main_tab.scenario == s].true_change.iloc[0] * 100 for s in scs]
    for j, v in enumerate(tv):
        ax.hlines(v, j - 2.6 * w, j + 2.6 * w, color=INK, lw=1.6, ls="--")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(range(3)); ax.set_xticklabels([f"本当は{s}" if s != "横ばい" else "本当は横ばい" for s in scs])
    ax.set_ylabel("初めの2年から終わりの2年への変化（%、400回の平均）")
    ax.set_ylim(-50, 480)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("点線が本当の変化：報告の件数は、どの場合も大きく増えて見える")
    save(fig, "a1219_scenarios.png", SRC)

    # 図3：27通り（横ばい）での③と④と⑤
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for i, k in enumerate(["m3_per_visit", "m4_ratio_common", "m5_founders"]):
        ax.scatter(np.full(len(g), i) + np.linspace(-0.25, 0.25, len(g)), g[k] * 100, s=16,
                   color=[BLUE, GREEN, INK][i])
    ax.axhline(0, color=ORANGE, lw=1.2, ls="--"); ax.text(-0.45, -4, "本当（0%）", color=ORANGE, fontsize=8.5, ha="left", va="top")
    ax.set_xticks(range(3)); ax.set_xticklabels(["③観察1回あたりの報告", "④種Cが見つかった回に\n対する種Rの割合", "⑤1年目からいる人\nだけの1回あたり"],
                                                fontsize=8.5)
    ax.set_ylabel("10年の変化（%、各200回の平均）")
    ax.set_title("本当は横ばい・置き方27通り：どの数え方も0%からずれる通りがある")
    save(fig, "a1219_grid.png", SRC)
    pd.set_option("display.width", 250)
    print(main_tab.to_string()); print(json.dumps(gstat, ensure_ascii=False)); print(out["grid_flat_growth_gt1_18"],
                                                                                     out["grid_m4_closer_than_m3"])
    print(target.to_string()); print(avg.to_string())


if __name__ == "__main__":
    main()
