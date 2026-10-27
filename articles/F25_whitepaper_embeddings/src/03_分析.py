"""03 分析：チャンクを文埋め込みにし、テーマに分け、年ごとの移り変わりと検索を行う。

- 埋め込み：ruri-v3-30m（Apache-2.0、256次元）。クラスタ用は「トピック: 」、検索の文書側は「検索文書: 」、
  質問側は「検索クエリ: 」を先頭に付ける（モデルの説明どおり）
- テーマ：正規化した埋め込みを KMeans（k=12）。名前は c-TF-IDF（テーマごとに特徴的な名詞）で付ける
- 2次元の地図：UMAP（コサイン距離）
- 年どうしの近さ：年ごとの平均ベクトル（全体の平均を引いたもの）のコサイン類似度
- 語の検索：質問文に近いチャンク（全体の上位1%の近さ）が、その年のチャンクの何%か
"""
import json
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
from common import DATA, RES, MODEL, SEED
from textutil import nouns

K = 12
QUERIES = {
    "物価": "物価の上昇とインフレ",
    "デフレ": "デフレからの脱却",
    "賃金": "賃金の引上げと所得の増加",
    "少子化・人口減少": "少子化と人口減少",
    "財政赤字": "財政赤字と政府債務の増加",
    "不良債権": "不良債権の処理と金融システム",
    "デジタル・AI": "デジタル化と人工知能（AI）",
    "環境・脱炭素": "地球温暖化対策と脱炭素",
}


def load_model():
    from sentence_transformers import SentenceTransformer
    import os
    path = os.environ.get("RURI_PATH", MODEL)
    return SentenceTransformer(path, device="cpu")


def embed(model, texts, prefix, bs=32):
    e = model.encode([prefix + t for t in texts], batch_size=bs, normalize_embeddings=True, show_progress_bar=True)
    return e.astype(np.float32)


def ctfidf_names(texts, labels, k, topn=8):
    toks = [" ".join(nouns(t)) for t in texts]  # 1チャンクずつ形態素解析（長い文字列を一度に渡すと fugashi が落ちる）
    toks = np.array(toks, dtype=object)
    docs = [" ".join(toks[labels == c]) for c in range(k)]
    cv = CountVectorizer(token_pattern=r"[^ ]+", min_df=1)
    X = cv.fit_transform(docs).toarray().astype(float)
    tf = X / X.sum(1, keepdims=True)
    idf = np.log(1 + X.sum() / (X.sum(0) + 1))
    s = tf * idf
    vocab = np.array(cv.get_feature_names_out())
    return [list(vocab[np.argsort(-s[c])[:topn]]) for c in range(k)]


def query_share(model, emb_doc, years, thr_q=0.99):
    rows, qv = [], {}
    for name, q in QUERIES.items():
        v = embed(model, [q], "検索クエリ: ")[0]
        sim = emb_doc @ v
        thr = np.quantile(sim, thr_q)
        hit = sim >= thr
        s = pd.Series(hit).groupby(years).mean() * 100
        for y, val in s.items():
            rows.append(dict(query=name, year=int(y), share=val))
        qv[name] = sim
    return pd.DataFrame(rows), qv


def main():
    ch = pd.read_parquet(DATA / "chunks_500.parquet")
    ch["heading"] = ch.heading.where(ch.heading.str.len() > 0, ch.page_title)
    texts = ch.text.values
    model = load_model()
    if (DATA / "emb_doc_500.npy").exists():  # 計算済みなら読み込む（CPU で約45分かかる）
        E_topic = np.load(DATA / "emb_topic_500.npy").astype(np.float32)
        E_doc = np.load(DATA / "emb_doc_500.npy").astype(np.float32)
    else:
        E_topic = embed(model, list(texts), "トピック: ")
        E_doc = embed(model, list(texts), "検索文書: ")
        np.save(DATA / "emb_topic_500.npy", E_topic.astype(np.float16))
        np.save(DATA / "emb_doc_500.npy", E_doc.astype(np.float16))

    km = KMeans(K, n_init=20, random_state=SEED).fit(E_topic)
    lab = km.labels_
    ch["theme"] = lab
    names = ctfidf_names(texts, lab, K)
    # 年ごとの構成比
    share = pd.crosstab(ch.year, ch.theme, normalize="index") * 100
    share.to_csv(RES / "theme_share_by_year.csv")
    # テーマの情報（名前の候補・大きさ・よく出る年・代表的な見出し）
    info = []
    for c in range(K):
        idx = np.where(lab == c)[0]
        d = E_topic[idx] @ km.cluster_centers_[c] / np.linalg.norm(km.cluster_centers_[c])
        top = ch.iloc[idx[np.argsort(-d)[:8]]]
        yrs = ch.year[lab == c]
        info.append(dict(theme=c, n=len(idx), words=" ".join(names[c]), mean_year=round(yrs.mean(), 1),
                         peak_year=int(share[c].idxmax()), peak_share=round(share[c].max(), 1),
                         headings=" ／ ".join(dict.fromkeys(f"{r.year}:{r.heading[:30]}" for r in top.itertuples()))))
    pd.DataFrame(info).to_csv(RES / "themes.csv", index=False)
    ch[["year", "url", "heading", "i", "n_chars", "theme"]].to_csv(RES / "chunk_themes.csv", index=False)

    # UMAP 2次元
    import umap
    xy = umap.UMAP(n_neighbors=30, min_dist=0.1, metric="cosine", random_state=SEED).fit_transform(E_topic)
    pd.DataFrame(dict(x=xy[:, 0], y=xy[:, 1], year=ch.year, theme=lab)).to_csv(RES / "umap_2d.csv", index=False)

    # 年どうしの近さ（平均ベクトル）
    yrs = sorted(ch.year.unique())
    M = np.vstack([E_topic[ch.year.values == y].mean(0) for y in yrs])
    M = M - E_topic.mean(0)  # 全体の平均を引く（どの年も「経済の文章」なので、そのままだと類似度が0.98以上にそろう）
    M = M / np.linalg.norm(M, axis=1, keepdims=True)
    S = pd.DataFrame(M @ M.T, index=yrs, columns=yrs)
    S.to_csv(RES / "year_similarity.csv")
    # 前の年との近さ（話題の入れ替わりの大きさ）
    pd.DataFrame(dict(year=yrs[1:], sim_prev=[S.loc[yrs[i], yrs[i - 1]] for i in range(1, len(yrs))])).to_csv(RES / "year_sim_prev.csv", index=False)

    # 語の検索
    qs, qv = query_share(model, E_doc, ch.year.values)
    qs.to_csv(RES / "query_share_by_year.csv", index=False)
    # 検索デモ：上位の見出し（本文は出さない）
    demo = []
    for name, sim in qv.items():
        used = set()
        for j in np.argsort(-sim):
            r = ch.iloc[j]
            if r.url in used:
                continue
            used.add(r.url)
            demo.append(dict(query=name, rank=len(used), year=int(r.year), heading=r.heading, sim=round(float(sim[j]), 3), url=r.url))
            if len(used) == 5:
                break
    pd.DataFrame(demo).to_csv(RES / "search_demo.csv", index=False)
    json.dump(dict(n_chunks=len(ch), n_pages=int(ch.url.nunique()), years=[int(yrs[0]), int(yrs[-1])], K=K),
              open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
    print(pd.DataFrame(info)[["theme", "n", "words", "mean_year", "peak_year", "peak_share"]].to_string())


if __name__ == "__main__":
    main()
