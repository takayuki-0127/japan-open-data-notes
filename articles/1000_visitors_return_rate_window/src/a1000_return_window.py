"""1000 再来場率は、何日以内で数えるかでどう変わるのか？（架空のデータ）

架空の施設の初来場者。来た人ごとに「次に来るまでの日数」を作成者が置く。
二度と来ない人（割合 q）、すぐ戻る人（平均 near 日の指数分布）、しばらくして戻る人（平均 far 日の指数分布）の3種類。
本当の「W日以内の再来場率」は置いた分布から式で決まる：(1-q)*(s*(1-exp(-W/near)) + (1-s)*(1-exp(-W/far)))。
数える日数 W・データの締め日・施設の並べ方で、再来場率の読み方がどう動くかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1000
SRC = "架空の施設の初来場者と再来場（作成者が乱数で作成、seed 1000）"
WS = [7, 14, 30, 60, 90, 180, 365]
BASE = {"q": 0.55, "s": 0.4, "near": 14.0, "far": 150.0}   # 施設A
N_A = 20000
DAYS = 365.0             # データの期間（1年目の0日〜365日）
N_FAC, N_PER, REPS = 40, 2000, 200


def formula(W, q, s, near, far):
    W = np.asarray(W, float)
    return (1 - q) * (s * (1 - np.exp(-W / near)) + (1 - s) * (1 - np.exp(-W / far)))


def draw_T(rng, n, q, s, near, far):
    """次に来るまでの日数（二度と来ない人は inf）"""
    u = rng.uniform(size=n)
    t = np.where(u < s, rng.exponential(near, n), rng.exponential(far, n))
    return np.where(rng.uniform(size=n) < q, np.inf, t)


def fac_params(rng, n, near_rng=(7, 30), far_rng=(90, 300), q_rng=(0.4, 0.8)):
    return pd.DataFrame({"q": rng.uniform(*q_rng, n), "s": rng.uniform(0.1, 0.9, n),
                         "near": rng.uniform(*near_rng, n), "far": rng.uniform(*far_rng, n)})


def fac_rates(rng, par, Ws, n_per=N_PER):
    """施設ごとに n_per 人の初来場者を作り、W日以内の再来場率（観測）を返す"""
    k = len(par)
    u = rng.uniform(size=(k, n_per))
    s = par.s.values[:, None]
    t = np.where(u < s, rng.exponential(1.0, (k, n_per)) * par.near.values[:, None],
                 rng.exponential(1.0, (k, n_per)) * par.far.values[:, None])
    t = np.where(rng.uniform(size=(k, n_per)) < par.q.values[:, None], np.inf, t)
    return {W: (t <= W).mean(1) for W in Ws}


def top_overlap(a, b, k=10):
    return len(set(np.argsort(-a)[:k]) & set(np.argsort(-b)[:k]))


def compare(ra, rb):
    return {"spearman": float(spearmanr(ra, rb)[0]), "top10": top_overlap(ra, rb),
            "same_first": int(np.argmax(ra) == np.argmax(rb))}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 施設A：数える日数で再来場率はどう変わるか（全員を365日以上追える場合）
    T = draw_T(rng, N_A, **BASE)
    curve = pd.DataFrame({"W": WS, "observed_pct": [round(100 * (T <= w).mean(), 2) for w in WS],
                          "formula_pct": [round(100 * float(formula(w, **BASE)), 2) for w in WS]})
    curve["diff_pt"] = (curve.observed_pct - curve.formula_pct).round(2)
    curve.to_csv(RES / "curve_facility_a.csv", index=False)
    # 再来場した人（365日以内）のうち、30日以内に戻った人の割合
    ever365 = T <= 365
    share30_in365 = round(100 * float((T <= 30).sum() / ever365.sum()), 2)
    never_formula = round(100 * BASE["q"], 2)

    # 2) データの締め日：1年分のデータで、初来場の月ごとに数えると
    rng2 = np.random.default_rng(SEED + 1)
    first = rng2.uniform(0, DAYS, N_A)
    Tc = draw_T(rng2, N_A, **BASE)
    ret = first + Tc
    seen = ret <= DAYS
    month = np.minimum((first // (DAYS / 12)).astype(int), 11) + 1
    rows = []
    for m in range(1, 13):
        g = month == m
        full = m * DAYS / 12 <= DAYS - 90      # 月の全員が90日を追えるか
        elig = g & full
        rows.append({"month": m, "people": int(g.sum()),
                     "naive_any_pct": round(100 * float(seen[g].mean()), 2),
                     "naive_90_pct": round(100 * float((seen & (Tc <= 90))[g].mean()), 2),
                     "complete_90_pct": (round(100 * float((Tc[elig] <= 90).mean()), 2) if elig.sum() > 0 else None),
                     "complete_90_people": int(elig.sum())})
    coh = pd.DataFrame(rows)
    coh.to_csv(RES / "cohort_by_month.csv", index=False)
    elig_all = first <= DAYS - 90
    censor = {"truth90_pct": round(100 * float(formula(90, **BASE)), 2),
              "truth365_pct": round(100 * float(formula(365, **BASE)), 2),
              "naive_any_all_pct": round(100 * float(seen.mean()), 2),
              "naive_90_all_pct": round(100 * float((seen & (Tc <= 90)).mean()), 2),
              "complete_90_all_pct": round(100 * float((Tc[elig_all] <= 90).mean()), 2),
              "complete_90_people": int(elig_all.sum()),
              # 式：初来場が一様なら、締め日までに再来場が見える割合の期待値
              "naive_any_formula_pct": round(100 * float(np.mean(formula(DAYS - np.linspace(0, DAYS, 100001), **BASE))), 2)}
    pd.DataFrame({"visitor_id": np.arange(1, N_A + 1), "first_day": first.round(2),
                  "return_day": np.where(seen, ret, np.nan).round(2)}).to_csv(
        DATA / "facility_a_first_visits.csv", index=False)

    # 3) 施設40か所を、30日以内と365日以内で並べると
    rng3 = np.random.default_rng(SEED + 2)
    pairs = [(7, 30), (30, 90), (30, 180), (30, 365), (90, 365)]
    rec = {p: [] for p in pairs}
    noise, true_cmp, keep = [], [], []
    for r in range(REPS):
        par = fac_params(rng3, N_FAC)
        obs = fac_rates(rng3, par, [7, 30, 90, 180, 365])
        obs2 = fac_rates(rng3, par, [30])
        for p in pairs:
            rec[p].append(compare(obs[p[0]], obs[p[1]]))
        noise.append(compare(obs[30], obs2[30]))
        true_cmp.append(compare(formula(30, par.q.values, par.s.values, par.near.values, par.far.values),
                                formula(365, par.q.values, par.s.values, par.near.values, par.far.values)))
        keep.append((par, obs[30], obs[365]))
    sp = np.array([x["spearman"] for x in rec[(30, 365)]])
    pick = int(np.argmin(np.abs(sp - sp.mean())))      # 順位相関が平均にいちばん近い回
    if True:
        par, o30, o365 = keep[pick]
        if True:
            d = par.copy()
            d.insert(0, "facility", [f"施設{i + 1:02d}" for i in range(N_FAC)])
            d["rate30_pct"] = (100 * o30).round(2)
            d["rate365_pct"] = (100 * o365).round(2)
            d["rank30"] = (-d.rate30_pct).rank(method="min").astype(int)
            d["rank365"] = (-d.rate365_pct).rank(method="min").astype(int)
            d.round(4).to_csv(DATA / "facilities_one_rep.csv", index=False)
            fac1 = d

    def summ(lst):
        df = pd.DataFrame(lst)
        return {"spearman_mean": round(float(df.spearman.mean()), 3), "top10_mean": round(float(df.top10.mean()), 2),
                "same_first_pct": round(100 * float(df.same_first.mean()), 1)}

    rank_pairs = pd.DataFrame([{"W_short": p[0], "W_long": p[1], **summ(rec[p])} for p in pairs])
    rank_pairs.to_csv(RES / "rank_pairs.csv", index=False)
    noise_s, true_s = summ(noise), summ(true_cmp)

    # 4) 確かめ：すぐ戻る人・しばらくして戻る人の日数の置き方（9通り、各100回）
    rng4 = np.random.default_rng(SEED + 3)
    grid = []
    for nl, nr in [("3〜10日", (3, 10)), ("7〜30日", (7, 30)), ("20〜60日", (20, 60))]:
        for fl, fr in [("60〜150日", (60, 150)), ("90〜300日", (90, 300)), ("200〜600日", (200, 600))]:
            a, b = [], []
            for r in range(100):
                par = fac_params(rng4, N_FAC, nr, fr)
                obs = fac_rates(rng4, par, [30, 365])
                obs2 = fac_rates(rng4, par, [30])
                a.append(compare(obs[30], obs[365])); b.append(compare(obs[30], obs2[30]))
            sa, sb = summ(a), summ(b)
            grid.append({"near": nl, "far": fl, "spearman_30_365": sa["spearman_mean"], "top10_30_365": sa["top10_mean"],
                         "same_first_pct": sa["same_first_pct"],
                         "spearman_resample30": sb["spearman_mean"], "top10_resample30": sb["top10_mean"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_near_far.csv", index=False)

    out = {"facility_a": BASE, "curve": curve.to_dict("records"), "share30_among_return365_pct": share30_in365,
           "never_return_pct": never_formula, "ever_return_pct": round(100 - never_formula, 2), "censor": censor,
           "cohort": coh.to_dict("records"),
           "rank_pairs": rank_pairs.to_dict("records"), "rank_resample30": noise_s, "rank_formula_30_365": true_s,
           "facilities": {"n": N_FAC, "people_each": N_PER, "reps": REPS},
           "shown_rep": {"rep": pick + 1, "first30": fac1.loc[fac1.rank30 == 1, "facility"].iloc[0],
                    "first30_rank365": int(fac1.loc[fac1.rank30 == 1, "rank365"].iloc[0]),
                    "first365": fac1.loc[fac1.rank365 == 1, "facility"].iloc[0],
                    "first365_rank30": int(fac1.loc[fac1.rank365 == 1, "rank30"].iloc[0]),
                    "max_rank_move": int((fac1.rank30 - fac1.rank365).abs().max()),
                    "spearman": round(float(spearmanr(fac1.rate30_pct, fac1.rate365_pct)[0]), 3)},
           "grid": grid.to_dict("records"),
           "grid_range": {"spearman_30_365": [float(grid.spearman_30_365.min()), float(grid.spearman_30_365.max())],
                          "top10_30_365": [float(grid.top10_30_365.min()), float(grid.top10_30_365.max())],
                          "same_first_pct": [float(grid.same_first_pct.min()), float(grid.same_first_pct.max())],
                          "spearman_resample30": [float(grid.spearman_resample30.min()), float(grid.spearman_resample30.max())],
                          "top10_resample30": [float(grid.top10_resample30.min()), float(grid.top10_resample30.max())]}}
    json.dump(out, open(RES / "a1000_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：数える日数と再来場率（施設A）
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    Wf = np.linspace(0, 365, 400)
    ax.plot(Wf, 100 * formula(Wf, **BASE), color=GRAY, lw=1.5, label="置いた分布からの式の値")
    ax.plot(curve.W, curve.observed_pct, "o", color=BLUE, ms=6, label="数えた値（初来場者2万人）")
    for w, v in zip(curve.W, curve.observed_pct):
        if w in (7, 30, 90, 180, 365):
            ax.text(w + 4, v - 3.2, f"{w}日以内\n{v:.1f}%", fontsize=8.5, color=INK)
    ax.axhline(100 * (1 - BASE["q"]), color=ORANGE, lw=1, ls="--")
    ax.text(5, 100 * (1 - BASE["q"]) + 1.0, f"いつかは戻る人の割合（置いた値 {100 * (1 - BASE['q']):.0f}%）", color=ORANGE, fontsize=8.5)
    ax.set_xlim(0, 400); ax.set_ylim(0, 52)
    ax.set_xlabel("再来場を数える日数（初めて来た日から）"); ax.set_ylabel("再来場率（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("同じ施設の同じ人たちでも、何日以内で数えるかで再来場率は変わる")
    save(fig, "a1000_curve.png", SRC)

    # 図2：初来場の月ごとの再来場率（1年分のデータで締めた場合）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = coh.month
    ax.plot(x, coh.naive_any_pct, "o-", color=ORANGE, label="締め日までに再来場した割合")
    ax.plot(x, coh.naive_90_pct, "s-", color=BLUE, label="90日以内（まだ90日たっていない人も入れる）")
    ok = coh.complete_90_pct.notna()
    ax.plot(x[ok], coh.complete_90_pct[ok], "D-", color=GREEN, label="90日以内（90日たった人だけ）")
    ax.axhline(censor["truth90_pct"], color=GRAY, lw=1, ls="--")
    ax.text(12.3, censor["truth90_pct"] + 0.8, f"本当の90日以内\n{censor['truth90_pct']:.1f}%", fontsize=8.5, va="bottom", color=INK)
    ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月目" for m in range(1, 13)], fontsize=8.5)
    ax.set_xlim(0.5, 13.6); ax.set_ylim(0, 45)
    ax.set_xlabel("初めて来た月（データは12月目の終わりで締める）"); ax.set_ylabel("再来場率（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("本当の再来場率はどの月も同じでも、後の月ほど低く見える")
    save(fig, "a1000_cohort.png", SRC)

    # 図3：施設40か所の30日以内と365日以内（1回目）
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    ax.scatter(fac1.rate30_pct, fac1.rate365_pct, s=28, color=BLUE, alpha=.8)
    top30 = fac1.nsmallest(10, "rank30"); top365 = fac1.nsmallest(10, "rank365")
    ax.scatter(top30.rate30_pct, top30.rate365_pct, s=70, facecolors="none", edgecolors=ORANGE, lw=1.4,
               label="30日以内の上位10か所")
    ax.scatter(top365.rate30_pct, top365.rate365_pct, s=14, marker="x", color=INK, label="365日以内の上位10か所")
    ax.set_xlabel("30日以内の再来場率（%）"); ax.set_ylabel("365日以内の再来場率（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title(f"架空の施設40か所：30日と365日の順位相関 {out['shown_rep']['spearman']:.2f}（{pick + 1}回目）", fontsize=12)
    save(fig, "a1000_rank.png", SRC)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps({k: out[k] for k in ["curve", "censor", "rank_pairs", "rank_resample30", "rank_formula_30_365", "shown_rep", "grid_range", "run_sec", "share30_among_return365_pct"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
