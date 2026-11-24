"""1232 上位の順番が1つ入れかわっただけで、良さの点数はどれだけ動くのか？（架空のデータ）

架空の社内の文書検索。検索語ごとに候補200件のうち正しい文書 R 件を置き、
検索の点＝（正しければ+μ）＋揺れ で並べる。上位の隣どうし（k 位と k+1 位）を1組だけ入れかえたとき、
4つの良さの点数がどれだけ動くかを数える。
  p10      : 上位10件の正しい割合
  first    : いちばん上の正しい文書の順位の逆数（上位10件になければ0）
  weighted : k 位に 1/log2(k+1) の重みを付けて正しい文書の重みを足し、いちばん良い並びの値で割ったもの
  hitavg   : 上位10件で正しい文書が出るたびに、そこまでの正しい割合を数え、足して R で割ったもの
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1232
SRC = "架空の社内の文書検索の順位（作成者が乱数で作成、seed 1232）"
NC, L, K = 200, 11, 10
W = 1 / np.log2(np.arange(2, K + 2))
MET = ["p10", "first", "weighted", "hitavg"]
JP = {"p10": "上位10件の正しい割合", "first": "いちばん上の正しい文書の順位の逆数",
      "weighted": "順位で重みを付けた点", "hitavg": "正しい文書ごとの割合の平均"}


def scores(rel, R):
    r = rel[:, :K].astype(float)
    p10 = r.mean(1)
    has = r.any(1)
    first = np.where(has, 1 / (np.argmax(r, 1) + 1), 0.0)
    ideal = np.array([W[:min(int(x), K)].sum() for x in np.atleast_1d(R)])
    weighted = (r * W).sum(1) / ideal
    prec = np.cumsum(r, 1) / np.arange(1, K + 1)
    hitavg = (r * prec).sum(1) / np.asarray(R, float)
    return {"p10": p10, "first": first, "weighted": weighted, "hitavg": hitavg}


def gen(rng, q, R, mu):
    out = []
    for s in range(0, q, 5000):
        m = min(5000, q - s)
        sc = rng.normal(0, 1, (m, NC))
        sc[:, :R] += mu
        idx = np.argsort(-sc, 1)[:, :L]
        out.append((idx < R).astype(int))
    return np.vstack(out)


def swap_deltas(rel, R):
    """各検索語で k 位と k+1 位（k=1..10）を入れかえたときの点の変化（後−前）。形は (検索語, 10)"""
    base = scores(rel, np.full(len(rel), R))
    d = {m: np.zeros((len(rel), K)) for m in MET}
    for k in range(K):
        r2 = rel.copy()
        r2[:, [k, k + 1]] = r2[:, [k + 1, k]]
        s2 = scores(r2, np.full(len(rel), R))
        for m in MET:
            d[m][:, k] = s2[m] - base[m]
    return base, d


def main():
    t0 = time.time()
    # 1) 例：1つの検索語（正しい文書4件。上位11件の並び）
    ex_rel = np.array([[0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1]])
    R_ex = 4
    base_ex, d_ex = swap_deltas(ex_rel, R_ex)
    rows = []
    for k in range(K):
        rows.append({"swap": f"{k+1}-{k+2}", "rel_before": f"{ex_rel[0,k]}{ex_rel[0,k+1]}",
                     **{m: round(float(d_ex[m][0, k]), 4) for m in MET}})
    ex = pd.DataFrame(rows)
    ex.to_csv(RES / "example_swaps.csv", index=False)
    ex_base = {m: round(float(base_ex[m][0]), 4) for m in MET}

    # 2) 基本：正しい文書5件・μ=1.5 の検索語40,000語
    R0, MU0, Q = 5, 1.5, 40000
    rng = np.random.default_rng(SEED)
    relA = gen(rng, Q, R0, MU0)
    pd.DataFrame(relA[:2000], columns=[f"rank{i}" for i in range(1, L + 1)]).assign(query=np.arange(1, 2001)) \
        [["query"] + [f"rank{i}" for i in range(1, L + 1)]].to_csv(DATA / "top11_example.csv", index=False)
    baseA, dA = swap_deltas(relA, R0)
    by_pos = []
    for k in range(K):
        diff = relA[:, k] != relA[:, k + 1]
        row = {"swap": f"{k+1}-{k+2}", "share_differ_pct": round(diff.mean() * 100, 2)}
        for m in MET:
            row[f"{m}_mean_abs_when_differ"] = round(float(np.abs(dA[m][diff, k]).mean()), 4)
            row[f"{m}_changed_pct"] = round(float((np.abs(dA[m][:, k]) > 1e-12).mean() * 100), 2)
        by_pos.append(row)
    by_pos = pd.DataFrame(by_pos)
    by_pos.to_csv(RES / "by_position.csv", index=False)
    summ = {}
    for m in MET:
        allabs = np.abs(dA[m])
        summ[m] = {"mean_score": round(float(baseA[m].mean()), 4),
                   "sd_between_queries": round(float(baseA[m].std()), 4),
                   "random_swap_mean_abs": round(float(allabs.mean()), 4),
                   "random_swap_changed_pct": round(float((allabs > 1e-12).mean() * 100), 2),
                   "max_abs": round(float(allabs.max()), 4),
                   "top_swap_mean_abs_when_differ": by_pos.loc[0, f"{m}_mean_abs_when_differ"],
                   "max_abs_over_sd": round(float(allabs.max() / baseA[m].std()), 4)}

    # 3) 2つの検索の比べ：A（μ=1.5）と B（μ=1.7）を同じ数の検索語で比べ、B の1語の1組を入れかえる
    def flip_study(R, mu, nq, nsets, seed, gap=0.2):
        rg = np.random.default_rng(seed)
        a = gen(rg, nq * nsets, R, mu)
        b = gen(rg, nq * nsets, R, mu + gap)
        sa = scores(a, np.full(len(a), R)); sb, db = swap_deltas(b, R)
        res = {}
        for m in MET:
            ma = sa[m].reshape(nsets, nq).mean(1); mb = sb[m].reshape(nsets, nq).mean(1)
            d = mb - ma
            worst = db[m].reshape(nsets, nq * K).min(1)            # B を最も下げる1組
            rnd_k = rg.integers(0, nq * K, nsets)
            rnd = db[m].reshape(nsets, nq * K)[np.arange(nsets), rnd_k]
            pos = d > 0
            res[m] = {"mean_gap": round(float(d.mean()), 4), "B_ahead_pct": round(float(pos.mean() * 100), 2),
                      "flip_worst_pct": round(float((d[pos] + worst[pos] / nq <= 0).mean() * 100), 2),
                      "flip_random_pct": round(float((d[pos] + rnd[pos] / nq <= 0).mean() * 100), 2),
                      "worst_swap_mean": round(float(worst.mean()), 4)}
        return res

    flips = {}
    frows = []
    for nq in [20, 50, 200]:
        fr = flip_study(R0, MU0, nq, 1000 if nq < 200 else 400, SEED * 10 + nq)
        flips[str(nq)] = fr
        for m in MET:
            frows.append({"queries": nq, "metric": m, **fr[m]})
    pd.DataFrame(frows).to_csv(RES / "flip_by_queries.csv", index=False)

    # 4) 確かめ：正しい文書の数 × 検索の良さ
    grows = []
    for R in [1, 3, 5, 10]:
        for mu in [1.0, 1.5, 2.5]:
            rg = np.random.default_rng(SEED * 100 + R * 10 + int(mu * 2))
            rel = gen(rg, 10000, R, mu)
            b, d = swap_deltas(rel, R)
            fr = flip_study(R, mu, 50, 400, SEED * 1000 + R * 10 + int(mu * 2))
            for m in MET:
                diff = rel[:, 0] != rel[:, 1]
                grows.append({"correct_docs": R, "score_gap": mu, "metric": m,
                              "mean_score": round(float(b[m].mean()), 4),
                              "random_swap_mean_abs": round(float(np.abs(d[m]).mean()), 4),
                              "random_swap_changed_pct": round(float((np.abs(d[m]) > 1e-12).mean() * 100), 2),
                              "top_swap_mean_abs_when_differ": round(float(np.abs(d[m][diff, 0]).mean()), 4) if diff.any() else None,
                              "flip_worst_pct_50q": fr[m]["flip_worst_pct"], "flip_random_pct_50q": fr[m]["flip_random_pct"],
                              "B_ahead_pct_50q": fr[m]["B_ahead_pct"]})
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    robust = {}
    for m in MET:
        g = grid[grid.metric == m]
        robust[m] = {"random_swap_changed_pct_min": float(g.random_swap_changed_pct.min()),
                     "random_swap_changed_pct_max": float(g.random_swap_changed_pct.max()),
                     "flip_worst_min": float(g.flip_worst_pct_50q.min()), "flip_worst_max": float(g.flip_worst_pct_50q.max()),
                     "flip_random_min": float(g.flip_random_pct_50q.min()), "flip_random_max": float(g.flip_random_pct_50q.max())}
    piv = grid.pivot_table(index=["correct_docs", "score_gap"], columns="metric", values="flip_worst_pct_50q")
    robust["first_is_largest_flip_worst_count"] = int((piv["first"] >= piv[["p10", "weighted", "hitavg"]].max(1)).sum())
    robust["first_equals_hitavg_when_one_correct"] = bool(
        (grid[(grid.correct_docs == 1) & (grid.metric == "first")].mean_score.values ==
         grid[(grid.correct_docs == 1) & (grid.metric == "hitavg")].mean_score.values).all())
    json.dump({"example": {"rel_top11": ex_rel[0].tolist(), "correct_docs": R_ex, "scores": ex_base},
               "base": summ, "flips": flips, "robust": robust,
               "setup": {"candidates": NC, "correct_docs": R0, "score_gap": MU0, "queries": Q, "B_extra_gap": 0.2}},
              open(RES / "a1232_main.json", "w"), ensure_ascii=False, indent=1)

    cols = {"p10": GRAY, "first": ORANGE, "weighted": BLUE, "hitavg": GREEN}
    # 図1：例の検索語で、入れかえた位置ごとの変化
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(K)
    for i, m in enumerate(MET):
        ax.bar(x + (i - 1.5) * 0.2, ex[m], 0.2, color=cols[m], label=JP[m])
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x, [f"{s}\n({r[0]}→{r[1]})" for s, r in zip(ex.swap, ex.rel_before)])
    ax.set_xlabel("入れかえた順位（括弧：入れかえる前の上側→下側の正しさ、1が正しい）")
    ax.set_ylabel("点の変化（入れかえ後−前）")
    ax.set_title("例の検索語：同じ1組の入れかえでも、点ごとに動く場所と大きさが違う")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower right")
    save(fig, "a1232_example.png", SRC, y=-0.09)

    # 図2：入れかえた位置ごとの変化の大きさ（正しさの違う2件を入れかえたとき）
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for m in MET:
        ax.plot(np.arange(1, K + 1), by_pos[f"{m}_mean_abs_when_differ"], marker="s" if m == "p10" else "o",
                ms=9 if m == "p10" else 6, color=cols[m], label=JP[m], zorder=1 if m == "p10" else 2)
    ax.set_xticks(np.arange(1, K + 1), by_pos.swap)
    ax.set_ylim(0, None)
    ax.set_xlabel("入れかえた順位"); ax.set_ylabel("点の変化の大きさ（平均）")
    ax.set_title("正しさの違う2件を入れかえたときの変化（正しい文書5件、4万語）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1232_by_position.png", SRC)

    # 図3：50語で比べたとき、1組の入れかえで上下が入れかわる割合
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(MET))
    f50 = flips["50"]
    v1 = [f50[m]["flip_worst_pct"] for m in MET]; v2 = [f50[m]["flip_random_pct"] for m in MET]
    b1 = ax.bar(x - 0.2, v1, 0.4, color=ORANGE, label="B をいちばん下げる1組を入れかえる")
    b2 = ax.bar(x + 0.2, v2, 0.4, color=GRAY, label="でたらめな1組を入れかえる")
    for bars, vals in [(b1, v1), (b2, v2)]:
        for bb, v in zip(bars, vals):
            ax.text(bb.get_x() + bb.get_width() / 2, v + max(v1) * 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_ylim(0, max(v1) * 1.2)
    ax.set_xticks(x, [JP[m].replace("いちばん上の", "いちばん上の\n").replace("ごとの", "ごとの\n") for m in MET], fontsize=9)
    ax.set_ylabel("B が上だった組のうち、逆になった割合（%）")
    ax.set_title("50語で比べたとき、B の1語の1組の入れかえで上下が入れかわった割合")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1232_flip.png", SRC)
    print(json.dumps(summ, ensure_ascii=False)); print(json.dumps(flips)); print(json.dumps(robust)); print(f"{time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
