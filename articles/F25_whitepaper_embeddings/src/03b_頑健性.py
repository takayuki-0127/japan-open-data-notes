"""03b 頑健性：設定を変えても「テーマの移り変わり」と「語の検索の推移」が同じになるか。

1. テーマの数 k を 8・16 に変える → 基本（k=12）との一致（ARI）と、年ごとの構成の変化の大きさ
2. 表現を変える：埋め込みの代わりに TF-IDF（名詞）＋SVD（256次元）＝単語ベース → ARI
3. 別のクラスタリング：UMAP（10次元）＋HDBSCAN → 外れ（ノイズ）の割合と ARI
4. 埋め込みの前置き（トピック: ／検索文書: ）
5. チャンクの長さを 1,000字に変える、近いとみなす閾値を上位0.5%・2%に変える → 語の検索の年ごとの割合の相関
"""
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score as ARI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from common import DATA, RES, SEED
from textutil import nouns
import importlib
an = importlib.import_module("03_分析")


def year_turnover(ch, lab):
    """年ごとのテーマ構成の、前半（〜2004）と後半（2005〜）の違い（総変動距離, %pt）"""
    sh = pd.crosstab(ch.year, lab, normalize="index")
    a = sh[sh.index <= 2004].mean()
    b = sh[sh.index >= 2005].mean()
    return 50 * (a - b).abs().sum()


def main():
    ch = pd.read_parquet(DATA / "chunks_500.parquet")
    E = np.load(DATA / "emb_topic_500.npy").astype(np.float32)
    base = pd.read_csv(RES / "chunk_themes.csv").theme.values
    rows = [dict(setting="基本（ruri・k=12・KMeans）", ari=1.0, turnover=year_turnover(ch, base), noise=np.nan)]
    for k in (8, 16):
        lab = KMeans(k, n_init=20, random_state=SEED).fit_predict(E)
        rows.append(dict(setting=f"k={k}", ari=ARI(base, lab), turnover=year_turnover(ch, lab), noise=np.nan))
    for s in (1, 2):
        lab = KMeans(12, n_init=20, random_state=SEED + s).fit_predict(E)
        rows.append(dict(setting=f"乱数の種を変える({s})", ari=ARI(base, lab), turnover=year_turnover(ch, lab), noise=np.nan))
    # 単語ベース
    docs = [" ".join(nouns(t)) for t in ch.text]
    X = TfidfVectorizer(token_pattern=r"[^ ]+", min_df=3, max_df=0.5, sublinear_tf=True).fit_transform(docs)
    Z = TruncatedSVD(256, random_state=SEED).fit_transform(X)
    Z /= np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9
    lab_lsa = KMeans(12, n_init=20, random_state=SEED).fit_predict(Z)
    rows.append(dict(setting="単語ベース（TF-IDF＋SVD）", ari=ARI(base, lab_lsa), turnover=year_turnover(ch, lab_lsa), noise=np.nan))
    np.save(DATA / "lsa_labels.npy", lab_lsa)
    # UMAP + HDBSCAN
    import umap, hdbscan
    U = umap.UMAP(n_neighbors=30, n_components=10, min_dist=0.0, metric="cosine", random_state=SEED).fit_transform(E)
    hl = hdbscan.HDBSCAN(min_cluster_size=60, min_samples=10).fit_predict(U)
    m = hl >= 0
    rows.append(dict(setting=f"UMAP＋HDBSCAN（{hl.max() + 1}テーマ）", ari=ARI(base[m], hl[m]), turnover=np.nan, noise=100 * (1 - m.mean())))
    # 前置きを「検索文書: 」にした埋め込み
    model = an.load_model()
    E0 = np.load(DATA / "emb_doc_500.npy").astype(np.float32)
    lab0 = KMeans(12, n_init=20, random_state=SEED).fit_predict(E0)
    rows.append(dict(setting="前置きを変えた埋め込み", ari=ARI(base, lab0), turnover=year_turnover(ch, lab0), noise=np.nan))
    pd.DataFrame(rows).round(3).to_csv(RES / "robust_clusters.csv", index=False)

    # チャンクの長さと語の検索
    base_q = pd.read_csv(RES / "query_share_by_year.csv")
    qrows = []
    for L in (1000,):
        c2 = pd.read_parquet(DATA / f"chunks_{L}.parquet")
        E2 = an.embed(model, list(c2.text), "検索文書: ")
        q2, _ = an.query_share(model, E2, c2.year.values)
        mg = base_q.merge(q2, on=["query", "year"], suffixes=("", f"_{L}"))
        for q, g in mg.groupby("query"):
            qrows.append(dict(query=q, length=L, corr=g["share"].corr(g[f"share_{L}"]),
                              peak_base=int(g.loc[g["share"].idxmax(), "year"]), peak_alt=int(g.loc[g[f"share_{L}"].idxmax(), "year"])))
    # 閾値を上位0.5%・2%に
    for thr in (0.995, 0.98):
        E_doc = np.load(DATA / "emb_doc_500.npy").astype(np.float32)
        q3, _ = an.query_share(model, E_doc, ch.year.values, thr_q=thr)
        mg = base_q.merge(q3, on=["query", "year"], suffixes=("", "_t"))
        for q, g in mg.groupby("query"):
            qrows.append(dict(query=q, length=f"上位{100 - thr * 100:.1f}%", corr=g["share"].corr(g["share_t"]),
                              peak_base=int(g.loc[g["share"].idxmax(), "year"]), peak_alt=int(g.loc[g["share_t"].idxmax(), "year"])))
    pd.DataFrame(qrows).round(3).to_csv(RES / "robust_queries.csv", index=False)
    print(pd.DataFrame(rows).round(3).to_string())
    print(pd.DataFrame(qrows).round(3).to_string())


if __name__ == "__main__":
    main()
