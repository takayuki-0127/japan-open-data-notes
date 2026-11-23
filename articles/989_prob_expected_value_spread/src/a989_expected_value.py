"""989 平均で考えると、どのくじが得に見えるのか？（期待値と振れ）（架空のデータ）

架空の商店街の福引き（買い物1回につき1回、無料で引ける）。景品はポイント。3種類の福引きを置く。
  A：必ず10ポイント
  B：10%で120ポイント、外れは0
  C：0.1%で15,000ポイント、外れは0
1回あたりの平均（期待値）は A 10・B 12・C 15（式どおり）。引く回数ごとに、もらうポイントの真ん中・幅・
A より多くなる人の割合を数え、「平均」「真ん中」「A より多くなる割合」「少人数で見た平均」で、
どれが得に見えるかの順がどう入れかわるかを数える。どの福引きを選ぶべきか・引くべきかの助言はしない。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 989
SRC = "架空の商店街の福引き（作成者が乱数で作成、seed 989）"
LOTS = {"A": (1.0, 10), "B": (0.10, 120), "C": (0.001, 15000)}   # 当たる確率, 当たりのポイント
KS = [1, 10, 100, 1000]
COL = {"A": GRAY, "B": BLUE, "C": ORANGE}


def pmf(k, p):
    """二項分布の確率（0〜k回当たる）"""
    if p >= 1:
        v = np.zeros(k + 1); v[k] = 1.0
        return v
    j = np.arange(k + 1)
    lg = np.array([math.lgamma(k + 1) - math.lgamma(i + 1) - math.lgamma(k - i + 1) for i in j])
    return np.exp(lg + j * math.log(p) + (k - j) * math.log1p(-p))


def quant(vals, probs, q):
    c = np.cumsum(probs)
    return float(vals[np.searchsorted(c, q - 1e-12)])


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) くじ × 引く回数：式の値と乱数20万人
    rows = []
    for name, (p, prize) in LOTS.items():
        for k in KS:
            w = pmf(k, p); v = np.arange(k + 1) * prize
            a_total = 10 * k
            mean = k * p * prize
            sd = prize * math.sqrt(k * p * (1 - p))
            sim = rng.binomial(k, p, 200_000) * prize
            rows.append({"lot": name, "draws": k, "mean_formula": round(mean, 2), "sd_formula": round(sd, 2),
                         "median": quant(v, w, 0.5), "q10": quant(v, w, 0.1), "q90": quant(v, w, 0.9),
                         "p_zero_pct": round(float(w[0]) * 100, 2),
                         "p_more_than_A_pct": round(float(w[v > a_total].sum()) * 100, 2),
                         "p_at_least_mean_pct": round(float(w[v >= mean - 1e-9].sum()) * 100, 2),
                         "sim_mean": round(float(sim.mean()), 2), "sim_median": float(np.median(sim)),
                         "sim_more_than_A_pct": round(float((sim > a_total).mean()) * 100, 2)})
    t1 = pd.DataFrame(rows)
    t1.to_csv(RES / "by_draws.csv", index=False)

    # 2) 少人数で見た平均：G人が1回ずつ引いた結果の平均で、どれが得に見えるか（各10万組）
    rows = []
    for G in [100, 1000, 10000]:
        obs = {n: rng.binomial(G, p, 100_000) * prize / G for n, (p, prize) in LOTS.items()}
        exact_c_zero = (1 - LOTS["C"][0]) ** G
        top = np.select([(obs["C"] > obs["B"]) & (obs["C"] > obs["A"]), (obs["B"] >= obs["C"]) & (obs["B"] > obs["A"])],
                        ["C", "B"], "A")
        rows.append({"people": G, "C_below_A_pct": round(float((obs["C"] < 10).mean()) * 100, 2),
                     "C_zero_pct": round(float((obs["C"] == 0).mean()) * 100, 2),
                     "C_zero_formula_pct": round(exact_c_zero * 100, 2),
                     "B_below_A_pct": round(float((obs["B"] < 10).mean()) * 100, 2),
                     "order_C_B_A_pct": round(float(((obs["C"] > obs["B"]) & (obs["B"] > obs["A"])).mean()) * 100, 2),
                     "top_A_pct": round(float((top == "A").mean()) * 100, 2),
                     "top_B_pct": round(float((top == "B").mean()) * 100, 2),
                     "top_C_pct": round(float((top == "C").mean()) * 100, 2),
                     "C_obs_q10": float(np.quantile(obs["C"], 0.1)), "C_obs_q90": float(np.quantile(obs["C"], 0.9))})
    t2 = pd.DataFrame(rows)
    t2.to_csv(RES / "observed_mean_groups.csv", index=False)

    # 3) 確かめ：平均（15ポイント）は同じで、当たりの確率と大きさだけ変える
    rows = []
    for p, prize in [(0.10, 150), (0.01, 1500), (0.001, 15000), (0.0001, 150000)]:
        for k in KS:
            w = pmf(k, p); v = np.arange(k + 1) * prize
            rows.append({"p_pct": p * 100, "prize": prize, "draws": k, "mean_formula": round(k * p * prize, 2),
                         "median": quant(v, w, 0.5), "p_zero_pct": round(float(w[0]) * 100, 2),
                         "p_more_than_A_pct": round(float(w[v > 10 * k].sum()) * 100, 2),
                         "p_at_least_mean_pct": round(float(w[v >= k * p * prize - 1e-9].sum()) * 100, 2)})
    t3 = pd.DataFrame(rows)
    t3.to_csv(RES / "same_mean_variants.csv", index=False)

    # 10回引いたときのポイントの分布（式、0.05%以上の値だけ）
    rows = []
    for name, (p, prize) in LOTS.items():
        w = pmf(10, p)
        for j in range(11):
            if w[j] > 5e-4:
                rows.append({"lot": name, "wins": j, "points": j * prize, "share_pct": round(float(w[j]) * 100, 2)})
    t4 = pd.DataFrame(rows)
    t4.to_csv(RES / "dist_10draws.csv", index=False)

    # 1回分のデータ：1,000人が10回ずつ引く
    n_people, k = 1000, 10
    d = pd.DataFrame({"person": np.arange(1, n_people + 1), "A_total": 10 * k})
    for name in ["B", "C"]:
        p, prize = LOTS[name]
        wins = rng.binomial(1, p, (n_people, k)).sum(1)
        d[f"{name}_wins"] = wins; d[f"{name}_total"] = wins * prize
    d.to_csv(DATA / "people_10draws.csv", index=False)
    one = {"people": n_people, "draws": k,
           "mean_total": {"A": float(d.A_total.mean()), "B": float(d.B_total.mean()), "C": float(d.C_total.mean())},
           "median_total": {"A": float(d.A_total.median()), "B": float(d.B_total.median()), "C": float(d.C_total.median())},
           "more_than_A_pct": {"B": round(float((d.B_total > 100).mean()) * 100, 1), "C": round(float((d.C_total > 100).mean()) * 100, 1)},
           "C_winners": int((d.C_wins > 0).sum()), "B_zero_pct": round(float((d.B_wins == 0).mean()) * 100, 1)}

    def g(t, lot, k, col):
        return float(t[(t.lot == lot) & (t.draws == k)][col].iloc[0])

    out = {"setup": {"lots": {n: {"p": p, "prize": z, "mean_per_draw": p * z} for n, (p, z) in LOTS.items()},
                     "draws": KS, "sim_people": 200_000, "groups": 100_000},
           "per_draw_mean_formula": {n: p * z for n, (p, z) in LOTS.items()},
           "per_draw_sd_formula": {n: round(z * math.sqrt(p * (1 - p)), 2) for n, (p, z) in LOTS.items()},
           "draws10": {n: {"median": g(t1, n, 10, "median"), "p_more_than_A_pct": g(t1, n, 10, "p_more_than_A_pct"),
                           "p_zero_pct": g(t1, n, 10, "p_zero_pct"), "p_at_least_mean_pct": g(t1, n, 10, "p_at_least_mean_pct")}
                       for n in ["B", "C"]},
           "max_abs_sim_minus_formula_mean": round(float((t1.sim_mean - t1.mean_formula).abs().max()), 2),
           "max_abs_sim_minus_formula_more_than_A_pts": round(float((t1.sim_more_than_A_pct - t1.p_more_than_A_pct).abs().max()), 2),
           "groups": t2.to_dict("records"),
           "same_mean_draws100_more_than_A_range_pct": [float(t3[t3.draws == 100].p_more_than_A_pct.min()),
                                                        float(t3[t3.draws == 100].p_more_than_A_pct.max())],
           "one_draw": one}
    json.dump(out, open(RES / "a989_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：10回引いたときのもらうポイントの分布
    fig, axs = plt.subplots(1, 3, figsize=(10.0, 3.6), sharey=True)
    for a, name in zip(axs, ["A", "B", "C"]):
        q = t4[t4.lot == name]
        xs = np.arange(len(q))
        a.bar(xs, q.share_pct, color=COL[name], width=0.6)
        a.set_xticks(xs); a.set_xticklabels([f"{int(x):,}" for x in q.points], fontsize=8, rotation=0 if name != "B" else 45)
        for xx, yy in zip(xs, q.share_pct):
            a.text(xx, yy + 1.5, f"{yy:g}", ha="center", fontsize=7.5)
        m = g(t1, name, 10, "mean_formula")
        a.set_title(f"{name}（平均 {m:g}・真ん中 {g(t1, name, 10, 'median'):g}）", fontsize=10.5)
        a.set_xlabel("10回でもらうポイント")
    axs[0].set_ylabel("人の割合（%、式）"); axs[0].set_ylim(0, 110)
    fig.suptitle("平均は C が最も大きいが、C の99%の人は0ポイント", y=1.03)
    save(fig, "a989_ten_draws.png", SRC)

    # 図2：引く回数ごとの「A より多くもらう人」の割合
    fig, ax = plt.subplots(figsize=(7.0, 3.9))
    for name in ["B", "C"]:
        x = t1[t1.lot == name]
        ax.plot(x.draws, x.p_more_than_A_pct, marker="o", color=COL[name], label=f"{name}（1回の平均 {LOTS[name][0]*LOTS[name][1]:g}）")
        for xx, yy in zip(x.draws, x.p_more_than_A_pct):
            ax.text(xx, yy + 3, f"{yy:g}%", ha="center", fontsize=8, color=COL[name])
    ax.set_xscale("log"); ax.set_xticks(KS); ax.set_xticklabels([f"{k:,}回" for k in KS])
    ax.set_ylim(0, 105); ax.set_xlabel("1人が引く回数"); ax.set_ylabel("A（必ず10）より多くもらう人の割合（%、式）")
    ax.legend(frameon=False, fontsize=9, loc="center right")
    ax.set_title("平均が大きくても、回数が少ないうちは A を上回る人は少ない")
    save(fig, "a989_more_than_a.png", SRC)

    # 図3：少人数で見た平均で、いちばん得に見えるくじ
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    y = np.arange(len(t2))[::-1]
    left = np.zeros(len(t2))
    for col, name in [("top_A_pct", "A"), ("top_B_pct", "B"), ("top_C_pct", "C")]:
        ax.barh(y, t2[col], left=left, color=COL[name], height=0.55, label=f"{name} がいちばん大きく見えた")
        for yy, l, v in zip(y, left, t2[col]):
            if v >= 4:
                ax.text(l + v / 2, yy, f"{v:g}%", ha="center", va="center", fontsize=8.5, color="white" if name != "A" else INK)
        left += t2[col].values
    ax.set_yticks(y); ax.set_yticklabels([f"{g_:,}人" for g_ in t2.people])
    ax.set_xlim(0, 100); ax.set_xlabel("1人1回ずつ引いた結果の平均で、いちばん大きく見えた福引き（%、各10万組）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=3)
    ax.set_title("式の平均は C > B > A でも、見た平均では C がいちばんとは限らない")
    save(fig, "a989_observed_mean.png", SRC, y=-0.2)

    print(json.dumps({k: out[k] for k in out if k != "setup"}, ensure_ascii=False, indent=1))
    print(t1.to_string()); print(t2.to_string()); print(t3.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
