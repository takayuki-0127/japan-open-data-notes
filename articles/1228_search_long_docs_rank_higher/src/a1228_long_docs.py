"""1228 長い文書ほど多くの言葉を含むとき、長い文書はどれだけ上に出やすくなるのか？（架空のデータ）

作成者が置いた架空の社内の文書の集まりと検索語（1語）。
  検索語200語。1語ごとに候補の文書1,000件、うち本当に正しい文書10件（基本は長さと関係なく選ぶ）。
  文書の長さ（語数）：中央値400語、対数の標準偏差0.8（基本）。20語より短くしない。
  正しくない文書：検索語は1語ごとに同じ見込み r（基本0.001）で出る（長いほど多く出る）。
  正しい文書：検索語について書いた部分（中央値150語、対数の標準偏差0.5、文書の長さを超えない）では1語ごとに0.02の見込みで出て、
             残りの部分では r で出る。
点の付け方：①出た回数そのまま ②出た回数÷文書の語数 ③回数を頭打ちにし、長さの分を割り引く点
  （回数×2.2÷(回数＋1.2×(0.25＋0.75×語数÷平均の語数))）。同じ点は乱数で並べる。
物差し：上位10件の正しい割合、上位10件のうち長い2割（その語の候補の中で語数の上位20%）・短い2割の文書の割合、
        長さの5つの帯ごとの上位10件に入った割合（正しい文書・正しくない文書別）。
(1) 基本を20回（各200語）
(2) 確かめ：長さの散らばり0.4・0.8・1.2 × r 0.0005・0.001・0.002 × 正しい文書の書き方（一部だけ・全体に）×
    正しさと長さの関係（なし・長いほど正しくなりやすい）＝36通り（各200語）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1228
SRC = "架空の社内の文書と検索語（作成者が置いた長さ・言葉の出る見込み・正しさからの乱数、seed 1228）"
Q, D, NREL = 200, 1000, 10
MED_L, MED_T, SIG_T, P_TOPIC = 400, 150, 0.5, 0.02
K1, B = 1.2, 0.75
BASE = dict(sig=0.8, r_bg=0.001, topic="part", corr="none")
R_MAIN = 20
SCORES = ["count", "rate", "capped"]
SNAME = {"count": "①出た回数そのまま", "rate": "②回数÷語数", "capped": "③頭打ち＋長さの割り引き"}
T0 = time.time()


def r(x, d=2):
    return round(float(x), d)


def make(rng, sig, r_bg, topic, corr):
    L = np.maximum(20, np.round(MED_L * np.exp(sig * rng.normal(size=(Q, D))))).astype(int)
    if corr == "none":
        key = rng.random((Q, D))
    else:   # 長いほど正しくなりやすい：語数の平方根に比例した重みで選ぶ
        key = rng.random((Q, D)) ** (1.0 / np.sqrt(L))
    rel = np.zeros((Q, D), bool)
    idx = np.argsort(-key, axis=1)[:, :NREL]
    np.put_along_axis(rel, idx, True, axis=1)
    if topic == "part":
        T = np.minimum(L, np.round(MED_T * np.exp(SIG_T * rng.normal(size=(Q, D))))).astype(int)
    else:
        T = L.copy()
    lam = np.where(rel, T * P_TOPIC + (L - T) * r_bg, L * r_bg)
    tf = rng.poisson(lam)
    return L, rel, tf


def scores(L, tf):
    avg = L.mean(axis=1, keepdims=True)
    return {"count": tf.astype(float), "rate": tf / L,
            "capped": tf * (K1 + 1) / (tf + K1 * (1 - B + B * L / avg))}


def evaluate(rng, L, rel, tf):
    sc = scores(L, tf)
    q80 = np.quantile(L, 0.8, axis=1, keepdims=True)
    q20 = np.quantile(L, 0.2, axis=1, keepdims=True)
    edges = np.quantile(L, [0.2, 0.4, 0.6, 0.8], axis=1).T  # (Q,4)
    band = (L[:, :, None] > edges[:, None, :]).sum(axis=2)  # 0..4
    out, bands = {}, {}
    for s in SCORES:
        v = sc[s] + 1e-9 * rng.random(L.shape)
        top = np.argsort(-v, axis=1)[:, :10]
        intop = np.zeros_like(rel)
        np.put_along_axis(intop, top, True, axis=1)
        out[f"{s}_p10"] = rel[intop].mean()
        out[f"{s}_long_share"] = (L >= q80)[intop].mean()
        out[f"{s}_short_share"] = (L <= q20)[intop].mean()
        out[f"{s}_rel_found"] = intop[rel].mean()
        out[f"{s}_topL_median"] = np.median(L[intop])
        for b in range(5):
            for t in (True, False):
                m = (band == b) & (rel == t)
                bands[(s, b, t)] = (intop[m].sum(), m.sum())
    return out, bands


def main():
    rng = np.random.default_rng(SEED)
    runs, bacc = [], {}
    for i in range(R_MAIN):
        L, rel, tf = make(rng, **BASE)
        if i == 0:
            q = 0
            sc = scores(L, tf)
            ex = pd.DataFrame({"doc_id": np.arange(D), "words": L[q], "correct": rel[q].astype(int), "hits": tf[q],
                               "score_count": sc["count"][q], "score_rate": np.round(sc["rate"][q], 6),
                               "score_capped": np.round(sc["capped"][q], 6)})
            ex.to_csv(DATA / "query0_docs.csv", index=False)
        o, b = evaluate(rng, L, rel, tf)
        runs.append(o)
        for k, (a, n) in b.items():
            x = bacc.setdefault(k, [0, 0]); x[0] += a; x[1] += n
    m = pd.DataFrame(runs).mean()
    main_rows = []
    for s in SCORES:
        main_rows.append({"score": SNAME[s], "top10_correct_pct": r(100 * m[f"{s}_p10"]),
                          "top10_long20_share_pct": r(100 * m[f"{s}_long_share"]),
                          "top10_short20_share_pct": r(100 * m[f"{s}_short_share"]),
                          "long_share_vs_20pct_times": r(m[f"{s}_long_share"] / 0.2),
                          "top10_median_words": r(m[f"{s}_topL_median"], 1)})
    mt = pd.DataFrame(main_rows)
    mt.to_csv(RES / "base_by_score.csv", index=False)
    brow = []
    bn = ["いちばん短い2割", "2番目", "真ん中", "4番目", "いちばん長い2割"]
    for s in SCORES:
        for b in range(5):
            a1, n1 = bacc[(s, b, True)]
            a0, n0 = bacc[(s, b, False)]
            brow.append({"score": SNAME[s], "length_band": bn[b], "correct_in_top10_pct": r(100 * a1 / n1),
                         "notcorrect_in_top10_pct": r(100 * a0 / n0, 3)})
    bd = pd.DataFrame(brow)
    bd.to_csv(RES / "by_length_band.csv", index=False)

    grid = []
    for sig in (0.4, 0.8, 1.2):
        for r_bg in (0.0005, 0.001, 0.002):
            for topic in ("part", "whole"):
                for corr in ("none", "longer"):
                    L, rel, tf = make(rng, sig, r_bg, topic, corr)
                    o, _ = evaluate(rng, L, rel, tf)
                    row = {"length_spread": sig, "bg_rate": r_bg, "correct_doc_topic": topic, "correct_vs_length": corr,
                           "true_long20_share_of_correct_pct": r(100 * (L >= np.quantile(L, 0.8, axis=1, keepdims=True))[rel].mean())}
                    for s in SCORES:
                        row[f"{s}_p10_pct"] = r(100 * o[f"{s}_p10"])
                        row[f"{s}_long_share_pct"] = r(100 * o[f"{s}_long_share"])
                        row[f"{s}_short_share_pct"] = r(100 * o[f"{s}_short_share"])
                    row["best_score"] = max(SCORES, key=lambda s: row[f"{s}_p10_pct"])
                    grid.append(row)
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    B_ = lambda s, b: bd[(bd.score == SNAME[s]) & (bd.length_band == bn[b])].iloc[0]
    headline = {}
    for s in SCORES:
        row = mt[mt.score == SNAME[s]].iloc[0]
        headline[f"{s}_p10_pct"] = row.top10_correct_pct
        headline[f"{s}_long_share_pct"] = row.top10_long20_share_pct
        headline[f"{s}_short_share_pct"] = row.top10_short20_share_pct
        headline[f"{s}_long_times"] = row.long_share_vs_20pct_times
        headline[f"{s}_median_words"] = row.top10_median_words
        for b in (0, 2, 4):
            headline[f"{s}_band{b}_notcorrect_pct"] = B_(s, b).notcorrect_in_top10_pct
            headline[f"{s}_band{b}_correct_pct"] = B_(s, b).correct_in_top10_pct
    headline["notcorrect_docs_per_query"] = D - NREL
    robust = {"settings": len(g),
              "true_long_share_correct_all": [g.true_long20_share_of_correct_pct.min(), g.true_long20_share_of_correct_pct.max()]}
    for s in SCORES:
        robust[f"{s}_long_share_range"] = [g[f"{s}_long_share_pct"].min(), g[f"{s}_long_share_pct"].max()]
        robust[f"{s}_short_share_range"] = [g[f"{s}_short_share_pct"].min(), g[f"{s}_short_share_pct"].max()]
        robust[f"{s}_p10_range"] = [g[f"{s}_p10_pct"].min(), g[f"{s}_p10_pct"].max()]
        robust[f"{s}_best_count"] = int((g.best_score == s).sum())
    for s in SCORES:
        dlt = g[f"{s}_long_share_pct"] - g.true_long20_share_of_correct_pct
        robust[f"{s}_long_minus_correct_long_range_pt"] = [r(dlt.min()), r(dlt.max())]
        robust[f"{s}_long_above_correct_long_settings"] = int((dlt > 0).sum())
    robust["count_long_share_over20_settings"] = int((g.count_long_share_pct > 20).sum())
    robust["rate_short_share_over20_settings"] = int((g.rate_short_share_pct > 20).sum())
    for corr in ("none", "longer"):
        gg = g[g.correct_vs_length == corr]
        robust[f"true_long_share_correct_{corr}"] = [gg.true_long20_share_of_correct_pct.min(), gg.true_long20_share_of_correct_pct.max()]
        for s in SCORES:
            robust[f"{s}_best_count_{corr}"] = int((gg.best_score == s).sum())
            robust[f"{s}_long_share_range_{corr}"] = [gg[f"{s}_long_share_pct"].min(), gg[f"{s}_long_share_pct"].max()]
    for topic in ("part", "whole"):
        gg = g[g.correct_doc_topic == topic]
        for s in SCORES:
            robust[f"{s}_best_count_{topic}"] = int((gg.best_score == s).sum())
            robust[f"{s}_long_share_range_{topic}"] = [gg[f"{s}_long_share_pct"].min(), gg[f"{s}_long_share_pct"].max()]
            robust[f"{s}_short_share_range_{topic}"] = [gg[f"{s}_short_share_pct"].min(), gg[f"{s}_short_share_pct"].max()]
            robust[f"{s}_p10_range_{topic}"] = [gg[f"{s}_p10_pct"].min(), gg[f"{s}_p10_pct"].max()]
    js = {"settings": {"queries": Q, "docs_per_query": D, "correct_per_query": NREL, "median_words": MED_L,
                       "topic_median_words": MED_T, "topic_spread": SIG_T, "topic_rate": P_TOPIC, "cap_k": K1, "cap_k_plus_1": K1 + 1, "length_b": B,
                       **BASE, "reps_main": R_MAIN, "seed": SEED},
          "headline": headline, "robust": robust}
    (RES / "a1228_main.json").write_text(json.dumps(js, ensure_ascii=False, indent=1))

    cols = {"count": ORANGE, "rate": GREEN, "capped": BLUE}
    # 図1：長さの帯ごと、正しくない文書が上位10件に入った割合
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3))
    x = np.arange(5)
    w = 0.26
    for ax, col_, ttl, d in [(axes[0], "notcorrect_in_top10_pct", "正しくない文書", 3), (axes[1], "correct_in_top10_pct", "本当に正しい文書", 2)]:
        for i, s in enumerate(SCORES):
            v = bd[bd.score == SNAME[s]][col_].values
            ax.bar(x + (i - 1) * w, v, w, color=cols[s], label=SNAME[s])
        ax.set_xticks(x, ["いちばん\n短い2割", "2番目", "真ん中", "4番目", "いちばん\n長い2割"], fontsize=9)
        ax.set_title(f"{ttl}が上位10件に入った割合", fontsize=11.5)
        ax.set_ylabel("%")
        ax.set_ylim(0, None)
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("文書の長さ（語数）の帯ごと（基本の置き方、20回×200語）", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a1228_by_length_band.png", SRC)

    # 図2：上位10件の長い2割・短い2割の割合と正しい割合
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    x = np.arange(3)
    w = 0.26
    for j, (c, lab, colr) in enumerate([("top10_long20_share_pct", "長い2割の文書の割合", ORANGE),
                                         ("top10_short20_share_pct", "短い2割の文書の割合", GREEN),
                                         ("top10_correct_pct", "本当に正しい文書の割合", BLUE)]):
        ax.bar(x + (j - 1) * w, mt[c], w, color=colr, label=lab)
        for xi, v in zip(x, mt[c]):
            ax.text(xi + (j - 1) * w, v + 1, f"{v:.2f}%", ha="center", fontsize=8.5)
    ax.axhline(20, color=GRAY, lw=0.9, ls="--", label="候補の中の長い2割・短い2割（20%）")
    ax.set_xticks(x, [SNAME[s] for s in SCORES])
    ax.set_ylabel("上位10件のうちの割合（%）")
    ax.set_ylim(0, 100)
    ax.set_title("点の付け方ごとの上位10件の中身（20回×200語の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1228_top10_mix.png", SRC)

    # 図3：36通り
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    for j, s in enumerate(SCORES):
        for i, corr in enumerate(("none", "longer")):
            v = g[g.correct_vs_length == corr][f"{s}_long_share_pct"].values
            xx = j + (i - 0.5) * 0.3 + np.linspace(-0.08, 0.08, len(v))
            ax.scatter(xx, v, s=14, color=[GRAY, ORANGE][i], alpha=0.8,
                       label=["正しさは長さと関係なし", "長い文書ほど正しくなりやすい"][i] if j == 0 else None)
    ax.axhline(20, color=INK, lw=0.8, ls="--")
    ax.set_xticks(range(3), [SNAME[s] for s in SCORES])
    ax.set_ylabel("上位10件のうち長い2割の文書の割合（%）")
    ax.set_ylim(0, 103)
    ax.set_title("36通りの置き方（長さの散らばり・言葉の出る見込み・書き方・正しさと長さ）", fontsize=11.5)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1228_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), json.dumps(robust, ensure_ascii=False), round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
