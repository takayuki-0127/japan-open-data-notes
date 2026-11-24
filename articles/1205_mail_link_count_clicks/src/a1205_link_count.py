"""1205 1通に入れるリンクの数を増やすと、クリックした人の割合とクリックの回数はどう動くのか？（架空のデータ）

架空の店の会員向けのお知らせのメール。メールを開いた6,000人について、1通に入れるリンクの数を1〜10本に変えて、
「クリックした人の割合」（1本でもクリックした人÷開いた人）と「クリックの回数」（全部のクリック÷開いた人）を数える。
1人ひとりのクリックしやすさ、リンクごとの引き、下に置くほどクリックされにくい度合い、
リンクが多いと1本ごとのクリックが減る度合い（目移り）を作成者が置く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1205
SRC = "架空の店の会員向けメール（作成者が置いたクリックしやすさとリンクの引きからの乱数、seed 1205）"
N_OPEN = 6000
KMAX = 10
BASE = dict(mean_e=0.3, conc=4.0, beta=0.6, pos=0.85, dil=0.1, repeat=0.25)
KS = np.arange(1, KMAX + 1)


def one_send(p, rng, k, e, appeal):
    """リンク k 本のメール1通。開いた人ごとのクリック（リンクごとの回数）を返す"""
    pos = p["pos"] ** np.arange(k)
    D = 1 / (1 + p["dil"] * (k - 1))
    prob = np.minimum(1, p["beta"] * e[:, None] * (appeal[:k] * pos)[None, :] * D)
    hit = rng.random(prob.shape) < prob
    times = hit * (1 + rng.poisson(p["repeat"], prob.shape))
    return hit, times, prob


def summarize(hit, times, prob):
    links = hit.sum(1)
    clicks = times.sum(1)
    clicker = links > 0
    n = len(links)
    tot = clicks.sum()
    return dict(clicker_share=clicker.mean(), links_per_opener=links.mean(), clicks_per_opener=clicks.mean(),
                clicks_per_clicker=clicks[clicker].mean() if clicker.any() else np.nan,
                multi_link_share_of_clickers=(links[clicker] >= 2).mean() if clicker.any() else np.nan,
                clicks_from_multi_link=(clicks[links >= 2].sum() / tot) if tot > 0 else np.nan,
                expected_clicker_share=(1 - np.prod(1 - prob, axis=1)).mean())


def same_person_formula(p, k, appeal):
    """全員のクリックしやすさが平均と同じだと置いたときの、クリックした人の割合（式）"""
    pos = p["pos"] ** np.arange(k)
    D = 1 / (1 + p["dil"] * (k - 1))
    pr = np.minimum(1, p["beta"] * p["mean_e"] * appeal[:k] * pos * D)
    return 1 - np.prod(1 - pr)


def run_reps(p, reps, seed0):
    rows = []
    for r in range(reps):
        rng = np.random.default_rng(seed0 + r)
        a = p["mean_e"] * p["conc"]
        e = rng.beta(a, p["conc"] - a, N_OPEN)
        appeal = rng.uniform(0.5, 1.5, KMAX)
        for k in KS:
            hit, times, prob = one_send(p, rng, k, e, appeal)
            d = summarize(hit, times, prob)
            d.update(rep=r, k=int(k), same_person_formula=same_person_formula(p, k, appeal))
            rows.append(d)
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    p = dict(BASE)
    reps = run_reps(p, 200, SEED * 1000)
    reps.round(6).to_csv(RES / "reps_base.csv", index=False)
    summ = reps.groupby("k").mean(numeric_only=True).drop(columns="rep")
    q = reps.groupby("k")[["clicker_share", "clicks_per_opener"]].quantile([0.05, 0.95]).unstack()
    summ["clicker_share_p5"] = q[("clicker_share", 0.05)]
    summ["clicker_share_p95"] = q[("clicker_share", 0.95)]
    summ["clicks_per_opener_p5"] = q[("clicks_per_opener", 0.05)]
    summ["clicks_per_opener_p95"] = q[("clicks_per_opener", 0.95)]
    summ["clicker_ratio_vs_k1"] = summ.clicker_share / summ.clicker_share.loc[1]
    summ["clicks_ratio_vs_k1"] = summ.clicks_per_opener / summ.clicks_per_opener.loc[1]
    summ.round(6).to_csv(RES / "by_k_base.csv")

    # 1回分のデータ（リンク5本）
    rng = np.random.default_rng(SEED)
    a = p["mean_e"] * p["conc"]
    e = rng.beta(a, p["conc"] - a, N_OPEN)
    appeal = rng.uniform(0.5, 1.5, KMAX)
    hit, times, prob = one_send(p, rng, 5, e, appeal)
    ex = pd.DataFrame(times, columns=[f"link{j + 1}_clicks" for j in range(5)])
    ex.insert(0, "click_ease", e.round(4))
    ex.insert(0, "opener_id", np.arange(1, N_OPEN + 1))
    ex.to_csv(DATA / "openers_example_5links.csv", index=False)

    # 確かめ：30通り（各20回）
    grid = []
    gi = 0
    for dil in [0.0, 0.05, 0.1, 0.2, 0.4]:
        for conc in [1.0, 4.0, 20.0]:
            for pos in [1.0, 0.85]:
                pp = dict(BASE, dil=dil, conc=conc, pos=pos)
                rr = run_reps(pp, 20, SEED * 100000 + gi * 100)
                s = rr.groupby("k").mean(numeric_only=True)
                grid.append(dict(dil=dil, conc=conc, pos=pos,
                                 clicker_k1=s.clicker_share.loc[1], clicker_k10=s.clicker_share.loc[10],
                                 clicks_k1=s.clicks_per_opener.loc[1], clicks_k10=s.clicks_per_opener.loc[10],
                                 clicker_ratio_10_1=s.clicker_share.loc[10] / s.clicker_share.loc[1],
                                 clicks_ratio_10_1=s.clicks_per_opener.loc[10] / s.clicks_per_opener.loc[1],
                                 best_k_clicker=int(s.clicker_share.idxmax()), best_k_clicks=int(s.clicks_per_opener.idxmax()),
                                 formula_over_sim_k10=s.same_person_formula.loc[10] / s.clicker_share.loc[10],
                                 clicks_per_clicker_k1=s.clicks_per_clicker.loc[1], clicks_per_clicker_k10=s.clicks_per_clicker.loc[10]))
                gi += 1
    grid = pd.DataFrame(grid)
    grid.round(5).to_csv(RES / "grid.csv", index=False)

    S = summ
    headline = {
        "clicker_share_pct": {int(k): round(float(S.clicker_share.loc[k]) * 100, 2) for k in KS},
        "clicks_per_100_openers": {int(k): round(float(S.clicks_per_opener.loc[k]) * 100, 2) for k in KS},
        "clicker_ratio_k5": round(float(S.clicker_ratio_vs_k1.loc[5]), 4), "clicker_ratio_k10": round(float(S.clicker_ratio_vs_k1.loc[10]), 4),
        "clicks_ratio_k5": round(float(S.clicks_ratio_vs_k1.loc[5]), 4), "clicks_ratio_k10": round(float(S.clicks_ratio_vs_k1.loc[10]), 4),
        "best_k_clicker": int(S.clicker_share.idxmax()), "best_k_clicks": int(S.clicks_per_opener.idxmax()),
        "clicks_per_clicker": {int(k): round(float(S.clicks_per_clicker.loc[k]), 3) for k in KS},
        "multi_link_share_of_clickers_pct": {int(k): round(float(S.multi_link_share_of_clickers.loc[k]) * 100, 2) for k in KS},
        "clicks_from_multi_link_pct": {int(k): round(float(S.clicks_from_multi_link.loc[k]) * 100, 2) for k in KS},
        "same_person_formula_pct": {int(k): round(float(S.same_person_formula.loc[k]) * 100, 2) for k in KS},
        "clicker_share_p5_p95_k1": [round(float(S.clicker_share_p5.loc[1]) * 100, 2), round(float(S.clicker_share_p95.loc[1]) * 100, 2)],
        "clicker_share_p5_p95_k10": [round(float(S.clicker_share_p5.loc[10]) * 100, 2), round(float(S.clicker_share_p95.loc[10]) * 100, 2)],
        "clicks_p5_p95_k1": [round(float(S.clicks_per_opener_p5.loc[1]) * 100, 2), round(float(S.clicks_per_opener_p95.loc[1]) * 100, 2)],
        "clicks_p5_p95_k10": [round(float(S.clicks_per_opener_p5.loc[10]) * 100, 2), round(float(S.clicks_per_opener_p95.loc[10]) * 100, 2)],
        "reps_clicks_up_clicker_down_k10_vs_k4_pct": round(float(
            ((reps[reps.k == 10].clicks_per_opener.values > reps[reps.k == 4].clicks_per_opener.values)
             & (reps[reps.k == 10].clicker_share.values < reps[reps.k == 4].clicker_share.values)).mean()) * 100, 2),
    }
    g = grid
    robust = {
        "n": int(len(g)),
        "clicker_ratio_10_1_range": [round(g.clicker_ratio_10_1.min(), 4), round(g.clicker_ratio_10_1.max(), 4)],
        "clicks_ratio_10_1_range": [round(g.clicks_ratio_10_1.min(), 4), round(g.clicks_ratio_10_1.max(), 4)],
        "clicks_ratio_gt_clicker_ratio_n": int((g.clicks_ratio_10_1 > g.clicker_ratio_10_1).sum()),
        "best_k_differs_n": int((g.best_k_clicker != g.best_k_clicks).sum()),
        "best_k_clicker_by_dil": {str(d): sorted(set(int(x) for x in g[g.dil == d].best_k_clicker)) for d in sorted(g.dil.unique())},
        "best_k_clicks_by_dil": {str(d): sorted(set(int(x) for x in g[g.dil == d].best_k_clicks)) for d in sorted(g.dil.unique())},
        "formula_over_sim_k10_by_conc": {str(c): [round(g[g.conc == c].formula_over_sim_k10.min(), 4), round(g[g.conc == c].formula_over_sim_k10.max(), 4)] for c in sorted(g.conc.unique())},
        "clicker_ratio_10_1_by_conc": {str(c): [round(g[g.conc == c].clicker_ratio_10_1.min(), 4), round(g[g.conc == c].clicker_ratio_10_1.max(), 4)] for c in sorted(g.conc.unique())},
        "nodil_clicker_ratio_range": [round(g[g.dil == 0].clicker_ratio_10_1.min(), 4), round(g[g.dil == 0].clicker_ratio_10_1.max(), 4)],
        "nodil_clicks_ratio_range": [round(g[g.dil == 0].clicks_ratio_10_1.min(), 4), round(g[g.dil == 0].clicks_ratio_10_1.max(), 4)],
    }
    json.dump({"base": BASE, "n_openers": N_OPEN, "headline": headline, "robust": robust},
              open(RES / "a1205_main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：リンクの数とクリックした人の割合・クリックの回数
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot(KS, S.clicker_share * 100, "o-", color=BLUE, label="クリックした人の割合")
    ax[0].plot(KS, S.same_person_formula * 100, "o--", color=GRAY, label="全員が同じクリックしやすさなら（式）")
    ax[0].set_ylim(0, 45)
    ax[0].set_xticks(KS)
    ax[0].set_xlabel("1通に入れるリンクの数")
    ax[0].set_ylabel("開いた人のうちの割合（%）")
    ax[0].set_title("クリックした人の割合は早く頭打ちになる")
    ax[0].legend(fontsize=8.5, frameon=False, loc="lower right")
    ax[1].plot(KS, S.clicks_per_opener * 100, "o-", color=ORANGE, label="開いた100人あたりのクリックの回数")
    ax[1].plot(KS, S.clicker_share * 100, "o-", color=BLUE, label="開いた100人あたりのクリックした人")
    ax[1].set_ylim(0, 75)
    ax[1].set_xticks(KS)
    ax[1].set_xlabel("1通に入れるリンクの数")
    ax[1].set_ylabel("開いた100人あたり")
    ax[1].set_title("回数は人より大きく伸びる（200回の平均）")
    ax[1].legend(fontsize=8.5, frameon=False, loc="lower right")
    save(fig, "a1205_by_k.png", SRC)

    # 図2：1本ずつと2本以上（クリックした人あたりの回数と、2本以上の人からのクリックの割合）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].bar(KS, S.clicks_per_clicker, color=ORANGE)
    for k in KS:
        ax[0].text(k, S.clicks_per_clicker.loc[k] + 0.03, f"{S.clicks_per_clicker.loc[k]:.3f}", ha="center", fontsize=7.5)
    ax[0].set_ylim(0, 2.2)
    ax[0].set_xticks(KS)
    ax[0].set_xlabel("1通に入れるリンクの数")
    ax[0].set_ylabel("クリックした人1人あたりの回数")
    ax[0].set_title("クリックした人1人あたりの回数")
    ax[1].bar(KS, S.clicks_from_multi_link * 100, color=GREEN)
    for k in KS:
        ax[1].text(k, S.clicks_from_multi_link.loc[k] * 100 + 1, f"{S.clicks_from_multi_link.loc[k] * 100:.2f}", ha="center", fontsize=7.5)
    ax[1].set_ylim(0, 70)
    ax[1].set_xticks(KS)
    ax[1].set_xlabel("1通に入れるリンクの数")
    ax[1].set_ylabel("2本以上クリックした人からのクリック（%）")
    ax[1].set_title("回数の伸びは、何本もクリックする人から来る")
    save(fig, "a1205_per_clicker.png", SRC)

    # 図3：確かめ（30通り）：10本÷1本の比
    fig, ax = plt.subplots(figsize=(8, 4.8))
    mk = {1.0: "o", 4.0: "s", 20.0: "^"}
    lab_c = {1.0: "人ごとの差が大きい", 4.0: "基本", 20.0: "人ごとの差が小さい"}
    for c in [1.0, 4.0, 20.0]:
        gg = g[g.conc == c]
        ax.scatter(gg.clicker_ratio_10_1, gg.clicks_ratio_10_1, marker=mk[c], s=30, color=BLUE, alpha=0.8, label=lab_c[c])
    lim = [0, max(g.clicks_ratio_10_1.max(), g.clicker_ratio_10_1.max()) * 1.05]
    ax.plot(lim, lim, color=GRAY, lw=0.8, ls=":")
    ax.text(lim[1] * 0.62, lim[1] * 0.58, "回数の比＝人の割合の比", fontsize=8, color=GRAY)
    ax.axvline(1, color=INK, lw=0.6, ls="--")
    ax.set_xlim(0, lim[1])
    ax.set_ylim(0, lim[1])
    ax.set_xlabel("クリックした人の割合の比（10本÷1本）")
    ax.set_ylabel("クリックの回数の比（10本÷1本）")
    ax.set_title("30通りすべてで、回数の比が人の割合の比を上回る")
    ax.text(1.05, lim[1] * 0.97, "1より左：10本で人の割合が下がる", fontsize=8, color=INK, va="top")
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    save(fig, "a1205_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False))
    print(json.dumps(robust, ensure_ascii=False))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
