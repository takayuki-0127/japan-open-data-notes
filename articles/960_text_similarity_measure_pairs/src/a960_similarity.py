"""960 「似ている度合い」の数え方で、似ている文章の組は入れ替わるのか？（架空のデータ）

作成者が乱数で語を組み合わせて作った架空の問い合わせ文300件。文章ごとに「本当の話題」（6つのどれか）を
作成者が置き、同じ話題の組を「本当に似ている組」とする。似ている度合いを4つの数え方で数え、
上位50組の顔ぶれ・同じ話題の割合・文章の長さを比べる。
語の区切りは、作成者が語のあいだに置いた空白（外部の辞書や道具は使わない）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 960
SRC = "架空の問い合わせ文（作成者が乱数で語を組み合わせて作成、seed 960）"
N_TEXT = 300
TOP = 50
REPS = 20

TOPICS = {
    "予約": ["予約", "日時", "人数", "席", "変更", "キャンセル", "空き", "当日", "個室", "電話", "時間帯", "連絡"],
    "支払い": ["支払い", "会計", "カード", "現金", "領収書", "金額", "割引", "ポイント", "請求", "返金", "レシート", "明細"],
    "配送": ["配送", "届く", "箱", "住所", "宅配", "遅れ", "到着", "追跡", "送料", "梱包", "受け取り", "不在"],
    "料理": ["料理", "味", "量", "温かい", "辛い", "甘い", "盛り付け", "品数", "塩", "麺", "スープ", "食感"],
    "接客": ["店員", "説明", "笑顔", "対応", "案内", "声", "丁寧", "態度", "待たされた", "注文", "気づかい", "言葉"],
    "営業時間": ["営業", "開店", "閉店", "定休日", "祝日", "時刻", "朝", "夜", "年末", "臨時", "休み", "平日"],
}
COMMON = ["です", "ます", "ので", "とても", "少し", "お願い", "確認", "前回", "今回", "店",
          "いつも", "ありがとう", "よろしく", "先日", "また", "もう一度", "教えて", "ください", "思います", "気になる"]
TNAMES = list(TOPICS)
VOCAB = COMMON + [w for t in TNAMES for w in TOPICS[t]]
VID = {w: i for i, w in enumerate(VOCAB)}
NC, NT, V = len(COMMON), 12, len(VOCAB)
MEASURES = ["common", "jaccard", "cos_count", "cos_tfidf"]
MLABEL = {"common": "共通する語の種類数", "jaccard": "ジャカード係数", "cos_count": "コサイン（回数）",
          "cos_tfidf": "コサイン（TF-IDF）"}


def zipf_p(n, s=1.0):
    p = 1 / np.arange(1, n + 1) ** s
    return p / p.sum()


PC, PT = zipf_p(NC), zipf_p(NT)


def make_texts(rng, n=N_TEXT, filler=0.45, len_sigma=0.6, other=0.15, len_median=15):
    """文章ごとの話題・長さ・語の回数（n×V）。filler：つなぎの語の割合、other：ほかの話題の語がまざる割合"""
    topic = rng.integers(0, len(TNAMES), n)
    if len_sigma == 0:
        L = np.full(n, len_median)
    else:
        L = np.clip(np.round(np.exp(np.log(len_median) + len_sigma * rng.standard_normal(n))), 4, 80).astype(int)
    X = np.zeros((n, V), dtype=int)
    words = []
    for i in range(n):
        ws = []
        for _ in range(L[i]):
            u = rng.random()
            if u < filler:
                k = rng.choice(NC, p=PC)
            else:
                t = topic[i] if rng.random() >= other else rng.integers(0, len(TNAMES))
                k = NC + t * NT + rng.choice(NT, p=PT)
            X[i, k] += 1
            ws.append(VOCAB[k])
        words.append(ws)
    return topic, L, X, words


def sims(X):
    """4つの数え方の n×n 行列"""
    B = (X > 0).astype(float)
    inter = B @ B.T
    sz = B.sum(1)
    union = sz[:, None] + sz[None, :] - inter
    jac = inter / union
    Xf = X.astype(float)
    nr = np.linalg.norm(Xf, axis=1)
    cc = (Xf @ Xf.T) / np.outer(nr, nr)
    df = B.sum(0)
    idf = np.where(df > 0, np.log(len(X) / np.maximum(df, 1)), 0.0)
    T = Xf * idf
    nt = np.linalg.norm(T, axis=1)
    nt[nt == 0] = 1
    ct = (T @ T.T) / np.outer(nt, nt)
    return {"common": inter, "jaccard": jac, "cos_count": cc, "cos_tfidf": ct}


def top_pairs(S, iu, rng, k=TOP):
    """上位 k 組（同点はくじで並べる）。iu は上三角の添字"""
    v = S[iu]
    tie = rng.random(len(v))
    order = np.lexsort((tie, -v))
    return order[:k]


def nearest(S, rng):
    """文章ごとにいちばん似ている相手（同点はくじ）"""
    n = len(S)
    M = S.astype(float).copy()
    M = M + rng.random(M.shape) * 1e-9 * (np.abs(M).max() + 1)  # 同点だけを崩す小さなくじ
    np.fill_diagonal(M, -np.inf)
    return M.argmax(1)


def evaluate(rng, **kw):
    topic, L, X, words = make_texts(rng, **kw)
    S = sims(X)
    n = len(topic)
    iu = np.triu_indices(n, 1)
    same = (topic[iu[0]] == topic[iu[1]])
    plen = (L[iu[0]] + L[iu[1]]) / 2
    res = {"base_same_rate": float(same.mean()), "all_pairs_len": float(plen.mean())}
    tops, nns, tord = {}, {}, {}
    for m in MEASURES:
        tp = top_pairs(S[m], iu, rng)
        tops[m] = set(tp.tolist())
        tord[m] = tp
        nn = nearest(S[m], rng)
        nns[m] = nn
        res[m] = {"top_same_topic": float(same[tp].mean()), "top_mean_len": float(plen[tp].mean()),
                  "top_min_len_median": float(np.median(np.minimum(L[iu[0]][tp], L[iu[1]][tp]))),
                  "nn_same_topic": float((topic[nn] == topic).mean())}
    allnn = np.all([nns[m] == nns["common"] for m in MEASURES], axis=0)
    res["nn_all_agree"] = float(allnn.mean())
    ovs = [len(tops[a] & tops[b]) for i, a in enumerate(MEASURES) for b in MEASURES[i + 1:]]
    res["top_overlap_min"], res["top_overlap_max"] = int(min(ovs)), int(max(ovs))
    res["top_overlap_mean"] = float(np.mean(ovs))
    return res, dict(topic=topic, L=L, X=X, words=words, S=S, iu=iu, same=same, plen=plen, tops=tops, nns=nns, tord=tord)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"settings": {"n_text": N_TEXT, "topics": TNAMES, "words_per_topic": NT, "common_words": NC,
                        "filler_share": 0.45, "other_topic_share": 0.15, "len_median": 15, "len_sigma": 0.6,
                        "len_clip": [4, 80], "top_k": TOP, "reps": REPS}}

    # 1) 1回分（基本の置き方）
    base, d = evaluate(rng)
    topic, L, X, words, S, iu = d["topic"], d["L"], d["X"], d["words"], d["S"], d["iu"]
    same, plen, tops = d["same"], d["plen"], d["tops"]
    out["base_run"] = base
    out["base_run"]["n_pairs"] = int(len(same))
    out["base_run"]["n_same_topic_pairs"] = int(same.sum())
    out["base_run"]["len_median"] = float(np.median(L))
    out["base_run"]["len_p90"] = float(np.percentile(L, 90))
    out["base_run"]["all_pairs_mean_len"] = float(plen.mean())
    ov = pd.DataFrame(index=MEASURES, columns=MEASURES, dtype=int)
    for a in MEASURES:
        for b in MEASURES:
            ov.loc[a, b] = len(tops[a] & tops[b])
    out["base_run"]["top_overlap"] = {a: {b: int(ov.loc[a, b]) for b in MEASURES} for a in MEASURES}
    sp = {}
    for i, a in enumerate(MEASURES):
        for b in MEASURES[i + 1:]:
            sp[f"{a}-{b}"] = round(float(spearmanr(S[a][iu], S[b][iu])[0]), 3)
    out["base_run"]["spearman_all_pairs"] = sp
    out["base_run"]["top_in_all4"] = int(len(set.intersection(*tops.values())))
    # 上位50組のうち、どちらかの文章が長い（40語以上）組
    long_any = (np.maximum(L[iu[0]], L[iu[1]]) >= 40)
    out["base_run"]["share_long_texts"] = float((L >= 40).mean())
    for m in MEASURES:
        tp = np.array(sorted(tops[m]))
        out["base_run"][m]["top_share_long_pair"] = float(long_any[tp].mean())
    # 50位の点と同じ点の組の数（同点の多さ）
    for m in MEASURES:
        v = np.sort(S[m][iu])[::-1]
        th = v[TOP - 1]
        out["base_run"][m]["score_at_50th"] = round(float(th), 4)
        out["base_run"][m]["pairs_at_or_above_50th"] = int((S[m][iu] >= th - 1e-12).sum())
    ov.to_csv(RES / "top50_overlap.csv")

    # 上位50組の一覧（4つの数え方）
    rows = []
    for m in MEASURES:
        tp = d["tord"][m]
        for r, k in enumerate(tp, 1):
            i, j = int(iu[0][k]), int(iu[1][k])
            rows.append({"measure": m, "rank": r, "text_a": i + 1, "text_b": j + 1, "score": round(float(S[m][i, j]), 4),
                         "len_a": int(L[i]), "len_b": int(L[j]), "topic_a": TNAMES[topic[i]], "topic_b": TNAMES[topic[j]],
                         "same_topic": int(topic[i] == topic[j])})
    pd.DataFrame(rows).to_csv(RES / "top50_pairs_base.csv", index=False)

    # 文章のデータ
    pd.DataFrame({"text_id": np.arange(1, N_TEXT + 1), "topic": [TNAMES[t] for t in topic], "n_words": L,
                  "text": [" ".join(w) for w in words]}).to_csv(DATA / "texts.csv", index=False)

    # 2) くり返し（基本の置き方で20回）と、置き方を変えた確かめ（各20回）
    grid = []
    for filler in [0.25, 0.45, 0.65]:
        for ls in [0.0, 0.3, 0.6, 0.9]:
            acc = []
            for r in range(REPS):
                g = np.random.default_rng([SEED, int(filler * 100), int(ls * 10), r])
                acc.append(evaluate(g, filler=filler, len_sigma=ls)[0])
            row = {"filler_share": filler, "len_sigma": ls, "base_same_rate": round(np.mean([a["base_same_rate"] for a in acc]), 4),
                   "all_pairs_len": round(np.mean([a["all_pairs_len"] for a in acc]), 2),
                   "nn_all_agree": round(np.mean([a["nn_all_agree"] for a in acc]), 4),
                   "top_overlap_mean": round(np.mean([a["top_overlap_mean"] for a in acc]), 2),
                   "top_overlap_min": round(np.mean([a["top_overlap_min"] for a in acc]), 2),
                   "top_overlap_max": round(np.mean([a["top_overlap_max"] for a in acc]), 2)}
            for m in MEASURES:
                row[f"{m}_top_same"] = round(np.mean([a[m]["top_same_topic"] for a in acc]), 4)
                row[f"{m}_top_len"] = round(np.mean([a[m]["top_mean_len"] for a in acc]), 2)
                row[f"{m}_nn_same"] = round(np.mean([a[m]["nn_same_topic"] for a in acc]), 4)
            grid.append(row)
    gdf = pd.DataFrame(grid)
    gdf.to_csv(RES / "robustness_grid.csv", index=False)
    out["robustness"] = grid
    var = gdf[gdf.len_sigma > 0]
    out["robustness_range_len_varies"] = {m: [float(var[f"{m}_top_same"].min()), float(var[f"{m}_top_same"].max())]
                                          for m in MEASURES}
    for k in ["nn_all_agree", "top_overlap_mean", "top_overlap_min", "top_overlap_max"]:
        out["robustness_range_len_varies"][k] = [float(var[k].min()), float(var[k].max())]
    eq = gdf[gdf.len_sigma == 0]
    out["robustness_range_len_equal"] = {m: [float(eq[f"{m}_top_same"].min()), float(eq[f"{m}_top_same"].max())]
                                         for m in MEASURES}
    for k in ["nn_all_agree", "top_overlap_mean", "top_overlap_min", "top_overlap_max"]:
        out["robustness_range_len_equal"][k] = [float(eq[k].min()), float(eq[k].max())]
    out["run_note"] = "乱数（numpy）。同点は乱数のくじで並べた"
    json.dump(out, open(RES / "a960_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：上位50組の顔ぶれの重なり
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    M = ov.values.astype(float)
    ax.imshow(M, cmap="Blues", vmin=0, vmax=TOP)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{int(M[i, j])}", ha="center", va="center", color="white" if M[i, j] > 30 else INK, fontsize=13)
    lab = ["共通する\n語の種類数", "ジャカード\n係数", "コサイン\n（回数）", "コサイン\n（TF-IDF）"]
    ax.set_xticks(range(4)); ax.set_xticklabels(lab, fontsize=9)
    ax.set_yticks(range(4)); ax.set_yticklabels(lab, fontsize=9)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("似ている上位50組のうち、2つの数え方で共通する組の数（1回分）", fontsize=11.5)
    save(fig, "a960_top50_overlap.png", SRC)

    # 図2：上位50組の「同じ話題」の割合と、組の平均の長さ（基本の置き方、20回の平均）
    b = gdf[(gdf.filler_share == 0.45) & (gdf.len_sigma == 0.6)].iloc[0]
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.0))
    cols = [GRAY, LIGHT, ORANGE, BLUE]
    y = np.arange(4)[::-1]
    v1 = [b[f"{m}_top_same"] * 100 for m in MEASURES]
    axs[0].barh(y, v1, color=cols)
    axs[0].axvline(b["base_same_rate"] * 100, color=INK, lw=1, ls="--")
    axs[0].text(b["base_same_rate"] * 100 + 1, -0.75, f"でたらめな組 {b['base_same_rate']*100:.1f}%", fontsize=8.5, va="center")
    for yy, v in zip(y, v1):
        axs[0].text(v + 1, yy, f"{v:.1f}%", va="center", fontsize=9.5)
    axs[0].set_yticks(y); axs[0].set_yticklabels([MLABEL[m] for m in MEASURES]); axs[0].set_ylim(-1.1, 3.5)
    axs[0].set_xlim(0, 115); axs[0].set_xlabel("上位50組のうち同じ話題の組（%）")
    v2 = [b[f"{m}_top_len"] for m in MEASURES]
    axs[1].barh(y, v2, color=cols)
    allm = b["all_pairs_len"]
    axs[1].axvline(allm, color=INK, lw=1, ls="--")
    axs[1].text(allm + 0.5, -0.75, f"全部の組の平均 {allm:.1f}語", fontsize=8.5, va="center")
    for yy, v in zip(y, v2):
        axs[1].text(v + 0.5, yy, f"{v:.1f}語", va="center", fontsize=9.5)
    axs[1].set_yticks(y); axs[1].set_yticklabels([]); axs[1].set_ylim(-1.1, 3.5)
    axs[1].set_xlim(0, max(v2) * 1.3); axs[1].set_xlabel("上位50組の2つの文章の平均の語数")
    fig.suptitle("数え方ごとの上位50組（基本の置き方、20回の平均）", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a960_top50_same_len.png", SRC)

    # 図3：置き方を変えた確かめ
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 3.9), sharey=True)
    for ax, f in zip(axs, [0.25, 0.45, 0.65]):
        g = gdf[gdf.filler_share == f]
        for m, c in zip(MEASURES, cols):
            ax.plot(g.len_sigma, g[f"{m}_top_same"] * 100, "o-", color=c, lw=1.8, label=MLABEL[m])
        ax.plot(g.len_sigma, g["base_same_rate"] * 100, ":", color=INK, lw=1, label="でたらめな組")
        ax.set_title(f"つなぎの語の割合 {int(f*100)}%", fontsize=11)
        ax.set_xticks([0, 0.3, 0.6, 0.9]); ax.set_xlabel("長さのばらつき（0は全部15語）")
        ax.set_ylim(0, 105)
    axs[0].set_ylabel("上位50組のうち同じ話題（%）")
    axs[2].legend(fontsize=8, loc="lower left")
    fig.suptitle("置き方を変えた確かめ（各20回の平均）", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a960_robustness.png", SRC)

    # 図4：置き方を変えたときの、上位50組の共通する組の数（6つの組み合わせの平均）
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for f, c in zip([0.25, 0.45, 0.65], [GREEN, BLUE, ORANGE]):
        g = gdf[gdf.filler_share == f]
        ax.plot(g.len_sigma, g["top_overlap_mean"], "o-", color=c, lw=1.8, label=f"つなぎの語 {int(f*100)}%")
        ax.fill_between(g.len_sigma, g["top_overlap_min"], g["top_overlap_max"], color=c, alpha=0.12)
    ax.set_ylim(0, 50); ax.set_xticks([0, 0.3, 0.6, 0.9])
    ax.set_xlabel("長さのばらつき（0は全部15語）")
    ax.set_ylabel("上位50組のうち共通する組の数")
    ax.set_title("2つの数え方の上位50組で共通する組の数\n（線は6つの組み合わせの平均、帯はいちばん少ない〜多い組み合わせ、各20回の平均）", fontsize=10.5)
    ax.legend(fontsize=9, loc="upper left")
    save(fig, "a960_overlap_robust.png", SRC)
    print(f"done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
