"""962 「よく一緒に出る言葉」は、本当に関係があるのか？（架空のデータ）

作成者が乱数で語を組み合わせて作った架空の問い合わせ文。数える語60語のうち、本当に関係のある組を
8組だけ作成者が置く（Aが出た文章には、40%でBを書き足す）。ほかの組は、文章の長さを決めれば互いに関係しない。
「一緒に出た件数」「リフト」「件数5件以上のリフト」「長さでそろえた比」の4つで上位20組を取り、
本当の8組がいくつ入るかを数える。語の区切りは作成者が置いた空白。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 962
SRC = "架空の問い合わせ文（作成者が乱数で語を組み合わせて作成、seed 962）"
WORDS = ["予約", "変更", "時間", "確認", "注文", "商品", "連絡", "電話", "店舗", "料金",
         "返品", "交換", "支払い", "配送", "メール", "在庫", "サイズ", "色", "会員", "ポイント",
         "カード", "領収書", "住所", "送料", "営業", "割引", "クーポン", "駐車場", "ギフト", "包装",
         "キャンセル", "遅れ", "不具合", "説明書", "修理", "保証", "部品", "電池", "充電", "アプリ",
         "ログイン", "パスワード", "登録", "退会", "通知", "画面", "写真", "請求", "明細", "年末",
         "祝日", "子供", "メニュー", "持ち帰り", "席", "個室", "箱", "傷", "宅配", "店員"]
FILLER = ["です", "ます", "お願い", "します", "について", "ので", "でしょうか", "教えて", "ください", "先日"]
V = len(WORDS)
TRUE_PAIRS = [(0, 1), (10, 11), (26, 25), (28, 29), (34, 35), (37, 38), (40, 41), (55, 54)]  # A→B
P_ADD = 0.4
ZIPF_S = 1.3
FILL_SHARE = 0.6
TOPK = 20
MINC = 5
MEASURES = ["count", "lift", "lift_min5", "len_adj"]
MLABEL = {"count": "①一緒に出た件数", "lift": "②リフト", "lift_min5": "③リフト（5件以上）",
          "len_adj": "④長さでそろえた比（5件以上）"}
PZ = 1 / np.arange(1, V + 1) ** ZIPF_S
PZ = PZ / PZ.sum()


def simulate(rng, n=3000, len_median=12, len_sigma=0.6, p_add=P_ADD, keep_tokens=False):
    """文章ごとの語の有無（n×V の 0/1）と長さ。
    語 w は、文章の長さ L のとき 1−(1−p_w)^(0.4L) の確率で、ほかの語と関係なく出る（p_w は1位の語ほど大きい）。
    本当の8組だけ、A が出た文章に p_add の確率で B を書き足す。keep_tokens なら文章の語の並びも返す"""
    if len_sigma == 0:
        L = np.full(n, len_median)
    else:
        L = np.clip(np.round(np.exp(np.log(len_median) + len_sigma * rng.standard_normal(n))), 3, 80).astype(int)
    slots = (1 - FILL_SHARE) * L
    q = 1 - (1 - PZ[None, :]) ** slots[:, None]
    P = rng.random((n, V)) < q
    added = []
    for a, b in TRUE_PAIRS:
        add = P[:, a] & ~P[:, b] & (rng.random(n) < p_add)
        added.append(add)
        P[add, b] = True
    toks = None
    if keep_tokens:
        toks = []
        for i in range(n):
            ws = [WORDS[j] for j in np.where(P[i])[0]]
            nf = max(int(L[i]) - len(ws), 0)
            ws += [FILLER[k] for k in rng.integers(0, len(FILLER), nf)]
            toks.append([ws[k] for k in rng.permutation(len(ws))])
    return P, L, toks


def pair_table(P, L, nbins=10):
    """全部の組の物差し"""
    n = len(P)
    X = P.astype(float)
    nA = X.sum(0)
    C = X.T @ X
    with np.errstate(divide="ignore", invalid="ignore"):
        lift = C * n / np.outer(nA, nA)
    # 長さの層（10等分）ごとの語の出る割合から、関係がないときに一緒に出る件数の見込みを作る
    edges = np.unique(np.quantile(L, np.linspace(0, 1, nbins + 1)))
    bi = np.clip(np.searchsorted(edges, L, side="right") - 1, 0, len(edges) - 2)
    E = np.zeros((P.shape[1], P.shape[1]))
    for b in np.unique(bi):
        m = bi == b
        r = X[m].mean(0)
        E += m.sum() * np.outer(r, r)
    with np.errstate(divide="ignore", invalid="ignore"):
        adj = C / E
    iu = np.triu_indices(P.shape[1], 1)
    df = pd.DataFrame({"a": iu[0], "b": iu[1], "nA": nA[iu[0]], "nB": nA[iu[1]], "count": C[iu],
                       "lift": lift[iu], "expected_len": E[iu], "len_adj": adj[iu]})
    df["expected_indep"] = df.nA * df.nB / n
    df["lift"] = df["lift"].fillna(0)
    df["len_adj"] = df["len_adj"].fillna(0)
    df["lift_min5"] = np.where(df["count"] >= MINC, df["lift"], -np.inf)
    df["len_adj"] = np.where(df["count"] >= MINC, df["len_adj"], -np.inf)
    tp = set(tuple(sorted(p)) for p in TRUE_PAIRS)
    df["true"] = [int((a, b) in tp) for a, b in zip(df.a, df.b)]
    return df


def top(df, m, rng, k=TOPK):
    tie = rng.random(len(df))
    order = np.lexsort((tie, -df[m].values))
    return df.iloc[order[:k]]


def evaluate(rng, **kw):
    P, L, _ = simulate(rng, **kw)
    df = pair_table(P, L)
    res = {}
    for m in MEASURES:
        t = top(df, m, rng)
        res[m] = {"hits_top20": int(t["true"].sum()), "median_count_top20": float(t["count"].median()),
                  "hits_top8": int(t["true"].values[:8].sum())}
    ind = df[(df.true == 0) & (df.expected_indep >= 5)]
    res["indep_pairs_n"] = int(len(ind))
    res["indep_lift_gt1"] = float((ind.lift > 1).mean())
    res["indep_lift_median"] = float(ind.lift.median())
    res["indep_adj_gt1"] = float((ind.len_adj > 1).mean())
    res["indep_adj_median"] = float(ind.len_adj.median())
    return res, df, P, L


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"settings": {"n_text": 3000, "words": V, "filler_share": FILL_SHARE, "zipf_s": ZIPF_S, "len_median": 12,
                        "len_sigma": 0.6, "len_clip": [3, 80], "true_pairs": [[WORDS[a], WORDS[b]] for a, b in TRUE_PAIRS],
                        "p_add": P_ADD, "top_k": TOPK, "min_count": MINC, "len_bins": 10, "reps": 30}}

    # 1) 1回分（基本の置き方）
    P, L, toks = simulate(rng, keep_tokens=True)
    df = pair_table(P, L)
    base = {"n_pairs": int(len(df)), "n_true": int(df.true.sum()), "len_median": float(np.median(L))}
    share = P.mean(0)
    base["word_share_max"] = round(float(share.max()), 4)
    base["word_share_min"] = round(float(share.min()), 4)
    tops = {}
    rk = np.random.default_rng(SEED + 1)
    rows = []
    for m in MEASURES:
        t = top(df, m, rk)
        tops[m] = t
        base[m] = {"hits_top20": int(t["true"].sum()), "median_count_top20": float(t["count"].median()),
                   "min_count_top20": int(t["count"].min()), "max_count_top20": int(t["count"].max())}
        for r, (_, x) in enumerate(t.iterrows(), 1):
            rows.append({"measure": m, "rank": r, "word_a": WORDS[int(x.a)], "word_b": WORDS[int(x.b)],
                         "count": int(x["count"]), "texts_a": int(x.nA), "texts_b": int(x.nB),
                         "lift": round(float(x.lift), 3), "len_adj": round(float(x.len_adj), 3) if np.isfinite(x.len_adj) else "",
                         "true_pair": int(x.true)})
    pd.DataFrame(rows).to_csv(RES / "top20_pairs_base.csv", index=False)
    # 本当の8組の物差し
    tr = df[df.true == 1]
    base["true_pairs"] = [{"pair": f"{WORDS[int(x.a)]}・{WORDS[int(x.b)]}", "count": int(x["count"]),
                           "lift": round(float(x.lift), 3), "len_adj": round(float(x.len_adj), 3) if np.isfinite(x.len_adj) else None,
                           "rank_count": int((df["count"] > x["count"]).sum() + 1),
                           "rank_lift": int((df["lift"] > x.lift).sum() + 1),
                           "rank_len_adj": int((df["len_adj"] > x.len_adj).sum() + 1) if np.isfinite(x.len_adj) else None}
                          for _, x in tr.iterrows()]
    ind = df[(df.true == 0) & (df.expected_indep >= 5)]
    base["indep_pairs_n"] = int(len(ind))
    base["indep_lift_gt1"] = float((ind.lift > 1).mean())
    base["indep_lift_median"] = float(ind.lift.median())
    base["indep_adj_gt1"] = float((ind.len_adj > 1).mean())
    base["indep_adj_median"] = float(ind.len_adj.median())
    # リフトの上位が「件数の少ない組」であること
    base["lift_top20_count_le2"] = int((tops["lift"]["count"] <= 2).sum())
    out["base_run"] = base
    # 文章のデータ
    pd.DataFrame({"text_id": np.arange(1, len(L) + 1), "n_tokens": [len(t) for t in toks],
                  "text": [" ".join(t) for t in toks]}).to_csv(DATA / "texts.csv", index=False)
    pd.DataFrame({"word": WORDS, "texts_with_word": P.sum(0).astype(int), "share": np.round(share, 4)}).to_csv(
        DATA / "word_counts.csv", index=False)

    # 2) 置き方を変えた確かめ（各30回）
    R = 30
    grid = []
    for n in [500, 3000, 10000]:
        for ls in [0.0, 0.3, 0.6, 0.9]:
            acc = [evaluate(np.random.default_rng([SEED, n, int(ls * 10), r]), n=n, len_sigma=ls)[0] for r in range(R)]
            row = {"n_text": n, "len_sigma": ls}
            for m in MEASURES:
                row[f"{m}_hits20"] = round(float(np.mean([a[m]["hits_top20"] for a in acc])), 3)
                row[f"{m}_hits8"] = round(float(np.mean([a[m]["hits_top8"] for a in acc])), 3)
                row[f"{m}_med_count"] = round(float(np.mean([a[m]["median_count_top20"] for a in acc])), 2)
            for f in ["indep_lift_gt1", "indep_lift_median", "indep_adj_gt1", "indep_adj_median"]:
                row[f] = round(float(np.mean([a[f] for a in acc])), 4)
            grid.append(row)
    gdf = pd.DataFrame(grid)
    gdf.to_csv(RES / "robustness_grid.csv", index=False)
    out["robustness"] = grid
    out["robustness_range"] = {c: [float(gdf[c].min()), float(gdf[c].max())] for c in gdf.columns
                               if c not in ["n_text", "len_sigma"]}
    lv = gdf[gdf.len_sigma > 0]
    out["robustness_range_len_varies"] = {c: [float(lv[c].min()), float(lv[c].max())] for c in
                                          ["count_hits20", "lift_hits20", "lift_min5_hits20", "len_adj_hits20",
                                           "indep_lift_gt1", "indep_adj_gt1"]}
    out["run_note"] = "乱数（numpy）。同点は乱数のくじで並べた"
    json.dump(out, open(RES / "a962_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：一緒に出た件数とリフト（1回分、全部の組）
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    d0 = df[(df["count"] > 0) & (df.true == 0)]
    d1 = df[df.true == 1]
    ax.scatter(d0["count"], d0["lift"], s=7, color=GRAY, alpha=0.45, lw=0, label="関係を置いていない組")
    ax.scatter(d1["count"], d1["lift"], s=36, color=ORANGE, zorder=3, label="本当に関係を置いた8組")
    tl = tops["lift"]
    ax.scatter(tl["count"], tl["lift"], s=40, facecolors="none", edgecolors=BLUE, lw=1.2, zorder=4, label="②リフトの上位20組")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks([1, 10, 100, 1000]); ax.set_xticklabels(["1", "10", "100", "1,000"])
    ax.set_yticks([0.5, 1, 2, 5, 10]); ax.set_yticklabels(["0.5", "1", "2", "5", "10"])
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.axhline(1, color=INK, lw=0.8, ls=":")
    ax.set_xlabel("2つの語が一緒に出た文章の数（対数の目盛り）")
    ax.set_ylabel("リフト（対数の目盛り。1なら関係なし並み）")
    ax.set_title("全部の組の、一緒に出た件数とリフト（3,000件、1回分）", fontsize=12)
    ax.legend(fontsize=8.5, loc="upper right")
    save(fig, "a962_count_vs_lift.png", SRC)

    # 図2：上位20組に入った本当の組の数（基本の置き方、30回の平均）
    b = gdf[(gdf.n_text == 3000) & (gdf.len_sigma == 0.6)].iloc[0]
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    cols = [GRAY, LIGHT, BLUE, ORANGE]
    yy = np.arange(4)[::-1]
    v = [b[f"{m}_hits20"] for m in MEASURES]
    ax.barh(yy, v, color=cols)
    for a_, x_ in zip(yy, v):
        ax.text(x_ + 0.1, a_, f"{x_:.2f}組", va="center", fontsize=10)
    ax.set_yticks(yy); ax.set_yticklabels([MLABEL[m] for m in MEASURES])
    ax.set_xlim(0, 8.8); ax.axvline(8, color=INK, lw=0.8, ls=":")
    ax.text(7.9, 3.45, "本当の組は8組", ha="right", fontsize=8.5)
    ax.set_xlabel("上位20組に入った本当の組の数（8組中）")
    ax.set_title("数え方ごとの上位20組（3,000件、30回の平均）", fontsize=12)
    save(fig, "a962_hits.png", SRC, y=-0.06)

    # 図3：置き方を変えた確かめ
    fig, axs = plt.subplots(1, 2, figsize=(10.6, 4.0))
    for n, c in zip([500, 3000, 10000], [LIGHT, BLUE, INK]):
        g = gdf[gdf.n_text == n]
        axs[0].plot(g.len_sigma, g["indep_lift_gt1"] * 100, "o-", color=c, lw=1.8, label=f"リフト（{n:,}件）")
        axs[0].plot(g.len_sigma, g["indep_adj_gt1"] * 100, "s--", color=c, lw=1.4, label=f"長さでそろえた比（{n:,}件）")
    axs[0].axhline(50, color=GRAY, lw=0.8, ls=":")
    axs[0].set_ylim(0, 105); axs[0].set_xticks([0, 0.3, 0.6, 0.9])
    axs[0].set_xlabel("長さのばらつき（0は全部12語）"); axs[0].set_ylabel("1を超えた組の割合（%）")
    axs[0].set_title("関係を置いていない組のうち、1を超えた割合", fontsize=11)
    axs[0].legend(fontsize=7.5, loc="lower right")
    for m, c, st in zip(MEASURES, cols, ["o-", "o-", "o-", "s--"]):
        g = gdf[gdf.len_sigma == 0.6]
        axs[1].plot(g.n_text, g[f"{m}_hits20"], st, color=c, lw=1.8, ms=7 if m == "lift_min5" else 5, label=MLABEL[m])
    axs[1].set_xscale("log"); axs[1].set_xticks([500, 3000, 10000]); axs[1].set_xticklabels(["500", "3,000", "10,000"])
    axs[1].xaxis.set_minor_locator(plt.NullLocator())
    axs[1].set_ylim(0, 8.5); axs[1].set_xlabel("文章の数（長さのばらつき0.6）")
    axs[1].set_ylabel("上位20組に入った本当の組（8組中）")
    axs[1].set_title("文章の数と、上位20組の当たり（③と④はほぼ重なる）", fontsize=11)
    axs[1].legend(fontsize=7.8, loc="center right")
    fig.suptitle("置き方を変えた確かめ（各30回の平均）", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a962_robustness.png", SRC)
    print(f"done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
