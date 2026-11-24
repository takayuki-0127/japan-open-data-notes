"""1223 よく検索される語に重みを付けて平均するか、語ごとに同じ重みで平均するかで、改善の大きさはどう見えるのか？（架空のデータ）

架空の社内の検索で使われる検索語400語。語ごとの1か月の検索の回数は、よく使われる順に 1/順位 に比例すると置く。
語ごとに正しい文書の数（3〜50件）と、今のやり方の強さを作成者が置き、新しいやり方の強さの変化を
「よく使われる語ほど少し弱く、めったに使われない語ほど強く」なるように置く。
上位10件の正しい割合を、今と新しいやり方で語ごとに数え、2つの平均で改善を見る。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1223
SRC = "架空の社内の検索語と文書（作成者が置いた検索の回数・正しさ・点数からの乱数、seed 1223）"
DOCS, K = 1000, 10
BASE = dict(T=400, s=1.0, pattern="tail", lo=-0.4, hi=0.4, monthly=100000)
PAT_JA = {"tail": "めったに使われない語ほど良くなる", "flat": "どの語も同じだけ良くなる", "head": "よく使われる語ほど良くなる"}


def make_terms(rng, T=400, s=1.0, pattern="tail", lo=-0.4, hi=0.4):
    r = np.arange(1, T + 1)
    w = r ** -s
    w = w / w.sum()
    n = np.round(np.exp(rng.uniform(np.log(3), np.log(50), T))).astype(int)
    x = np.log(r) / np.log(T)  # 0（いちばんよく使われる語）〜1（いちばん使われない語）
    d_old = 1.5 + 0.5 * (1 - x)
    if pattern == "tail":
        dd = lo + (hi - lo) * x
    elif pattern == "flat":
        dd = np.full(T, 0.15)
    else:
        dd = hi + (lo - hi) * x
    return r, w, n, d_old, dd


def top_share(rng, n, d):
    mask = np.arange(DOCS)[None, :] < n[:, None]
    sc = rng.standard_normal((len(n), DOCS)) + d[:, None] * mask
    t = np.argpartition(-sc, K - 1, axis=1)[:, :K]
    return np.take_along_axis(mask, t, 1).mean(1)


def runs(rng, n, d_old, dd, reps):
    old = np.array([top_share(rng, n, d_old) for _ in range(reps)])
    new = np.array([top_share(rng, n, d_old + dd) for _ in range(reps)])
    return old, new


def pct(v):
    return round(float(v) * 100, 2)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    r, w, n, d_old, dd = make_terms(rng)
    T = len(r)
    old, new = runs(rng, n, d_old, dd, 200)
    diff = new - old  # (回, 語)
    tru_old, tru_new = old.mean(0), new.mean(0)
    tru = tru_new - tru_old  # 200回の平均を「本当の改善」とする
    terms = pd.DataFrame({"term_id": r, "monthly_searches": np.round(w * BASE["monthly"]).astype(int), "weight": w,
                          "n_correct": n, "old_strength": d_old, "change": dd,
                          "old_top10_share": tru_old, "new_top10_share": tru_new, "improvement": tru})
    terms.to_csv(DATA / "terms.csv", index=False, float_format="%.6f")

    eq_true, wt_true = tru.mean(), (w * tru).sum()
    eq_one, wt_one = diff.mean(1), diff @ w

    # 50語の評価用の語の選び方（200回）
    ev = {"random50": [], "log50": [], "top50": []}
    for i in range(200):
        g = np.random.default_rng([SEED, 7, i])
        pick = g.choice(T, 50, replace=False)
        ev["random50"].append(diff[i, pick].mean())
        logp = g.choice(T, 50, replace=True, p=w)  # 記録から50回の検索を抜き出す（同じ語が何回も出る）
        ev["log50"].append(diff[i, logp].mean())
        ev["top50"].append(diff[i, :50].mean())
    ev = {k: np.array(v) for k, v in ev.items()}
    rows = pd.DataFrame({"rep": np.arange(200), "all_equal": eq_one, "all_weighted": wt_one, **ev})
    rows.to_csv(RES / "reps_base.csv", index=False, float_format="%.6f")

    def summ(v):
        return {"mean_pt": pct(v.mean()), "p5_pt": pct(np.quantile(v, .05)), "p95_pt": pct(np.quantile(v, .95)),
                "share_positive": round(float((v > 0).mean()), 4)}

    head = {
        "equal_true_pt": pct(eq_true), "weighted_true_pt": pct(wt_true),
        "old_equal_pt": pct(tru_old.mean()), "new_equal_pt": pct(tru_new.mean()),
        "old_weighted_pt": pct((w * tru_old).sum()), "new_weighted_pt": pct((w * tru_new).sum()),
        "top1_weight": round(float(w[0]), 4), "top10_weight": round(float(w[:10].sum()), 4), "top50_weight": round(float(w[:50].sum()), 4),
        "terms_improved_share": round(float((tru > 0).mean()), 4),
        "searches_improved_share": round(float(w[tru > 0].sum()), 4),
        "top10_terms_improvement_pt": [pct(v) for v in tru[:10]],
        "top10_terms_contribution_pt": pct((w[:10] * tru[:10]).sum()),
        "rest_terms_contribution_pt": pct((w[10:] * tru[10:]).sum()),
        "one_run": {"all_equal": summ(eq_one), "all_weighted": summ(wt_one)},
        "eval_sets_50": {k: summ(v) for k, v in ev.items()},
    }

    # 確かめ：検索の回数の偏り×改善の付き方×語の数（各50回、語の一覧は置き方ごとに作り直す）
    grid = []
    for s in [0.8, 1.0, 1.2]:
        for pattern in ["tail", "flat", "head"]:
            for TT in [200, 400, 1000]:
                g = np.random.default_rng([SEED, int(s * 10), ["tail", "flat", "head"].index(pattern), TT])
                rr, ww, nn, do, ddd = make_terms(g, TT, s, pattern)
                o, nw = runs(g, nn, do, ddd, 50)
                tr = nw.mean(0) - o.mean(0)
                d1 = nw - o
                grid.append({"s": s, "pattern": pattern, "terms": TT, "equal_pt": pct(tr.mean()), "weighted_pt": pct((ww * tr).sum()),
                             "top10_weight": round(float(ww[:10].sum()), 4),
                             "terms_improved": round(float((tr > 0).mean()), 4), "searches_improved": round(float(ww[tr > 0].sum()), 4),
                             "one_run_weighted_sd_pt": pct((d1 @ ww).std()), "one_run_equal_sd_pt": pct(d1.mean(1).std())})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    gr["flip"] = np.sign(gr.equal_pt) != np.sign(gr.weighted_pt)
    robust = {"settings": int(len(gr)),
              "sign_flip_settings": int(gr.flip.sum()),
              "sign_flip_by_pattern": {p: int(gr[gr.pattern == p].flip.sum()) for p in PAT_JA},
              "by_pattern": {p: {"equal_pt": [float(gr[gr.pattern == p].equal_pt.min()), float(gr[gr.pattern == p].equal_pt.max())],
                                 "weighted_pt": [float(gr[gr.pattern == p].weighted_pt.min()), float(gr[gr.pattern == p].weighted_pt.max())]}
                             for p in PAT_JA},
              "top10_weight_by_s": {str(s): [float(gr[gr.s == s].top10_weight.min()), float(gr[gr.s == s].top10_weight.max())] for s in [0.8, 1.0, 1.2]},
              "one_run_sd_ratio_range": [round(float((gr.one_run_weighted_sd_pt / gr.one_run_equal_sd_pt).min()), 2),
                                         round(float((gr.one_run_weighted_sd_pt / gr.one_run_equal_sd_pt).max()), 2)]}

    out = {"headline": head, "robust": robust, "setup": {**BASE, "docs": DOCS, "top": K, "reps": 200, "grid_reps": 50}}
    json.dump(out, open(RES / "a1223_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：語ごとの改善と、検索の回数の順位
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.scatter(r, tru * 100, s=9 + 600 * w, color=np.where(tru > 0, BLUE, ORANGE), alpha=.6, lw=0)
    ax.axhline(0, color=GRAY, lw=1)
    ax.axhline(eq_true * 100, color=BLUE, lw=1.2, ls="--")
    ax.text(1.0, eq_true * 100 + 0.6, f"語ごとに同じ重み：{pct(eq_true)}ポイント", color=BLUE, fontsize=8.5, va="bottom")
    ax.axhline(wt_true * 100, color=ORANGE, lw=1.2, ls="--")
    ax.text(28, wt_true * 100 - 0.8, f"検索の回数で重み：{pct(wt_true)}ポイント", color=ORANGE, fontsize=8.5, va="top")
    ax.set_xscale("log"); ax.set_xlabel("検索の回数の順位（対数の目盛り。点の大きさは検索の回数）")
    ax.set_ylabel("上位10件の正しい割合の改善（ポイント）")
    ax.set_title("よく使われる語は悪く、めったに使われない語は良くなるように置いた例")
    save(fig, "a1223_by_rank.png", SRC)

    # 図2：どの平均・どの語の選び方で数えるか（200回の平均と5〜95%）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    labs = [("all_equal", "全400語・同じ重み"), ("random50", "でたらめに選んだ50語"), ("top50", "よく使われる上位50語"),
            ("all_weighted", "全400語・検索の回数で重み"), ("log50", "記録から抜いた50回の検索")]
    src = {"all_equal": eq_one, "all_weighted": wt_one, **ev}
    for i, (k, lab) in enumerate(labs):
        v = src[k] * 100
        m, lo5, hi95 = v.mean(), np.quantile(v, .05), np.quantile(v, .95)
        ax.plot([lo5, hi95], [i, i], color=GRAY, lw=2)
        ax.plot(m, i, "o", color=BLUE if k in ("all_equal", "random50") else (INK if k == "top50" else ORANGE), ms=7)
        ax.text(hi95 + 0.6, i, f"{m:.2f}（{lo5:.2f}〜{hi95:.2f}）", va="center", fontsize=8.5)
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_yticks(range(len(labs))); ax.set_yticklabels([l for _, l in labs]); ax.invert_yaxis()
    ax.set_xlabel("改善（ポイント、200回の平均と5〜95%の範囲）"); ax.set_xlim(-20, 25)
    ax.set_title("同じ新旧の差でも、どの平均で数えるかで向きが変わる（置いた例）")
    save(fig, "a1223_eval_sets.png", SRC)

    # 図3：確かめ27通り
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for p, c in [("tail", BLUE), ("flat", GRAY), ("head", ORANGE)]:
        sub = gr[gr.pattern == p]
        ax.scatter(sub.equal_pt, sub.weighted_pt, color=c, s=26, label=PAT_JA[p], lw=0)
    lim = [-15, 15]
    ax.plot(lim, lim, color=GRAY, lw=0.8, ls=":")
    ax.axhline(0, color=GRAY, lw=0.8); ax.axvline(0, color=GRAY, lw=0.8)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("語ごとに同じ重みの改善（ポイント）"); ax.set_ylabel("検索の回数で重みを付けた改善（ポイント）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("改善が語で偏ると、2つの平均の向きが逆になることがある（27通り、各50回）")
    save(fig, "a1223_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
