"""F96 検索のしくみ（5通り）
- kw_and   : キーワード全部一致（サイトの「表題を検索」に近い）。質問を単語に分け、全部を含む表だけを BM25 の順で並べる
- bm25     : 単語の BM25（fugashi＋unidic-lite で分かち書き）
- char     : 文字2〜3グラムの TF-IDF のコサイン類似度（分かち書きに頼らない）
- ruri30/70: 文埋め込み（ruri-v3-30m / 70m）のコサイン類似度。文書は「検索文書: 」、質問は「検索クエリ: 」を前に付ける
- hybrid   : BM25 と ruri-v3-30m の順位を Reciprocal Rank Fusion（k=60）で合わせる
"""
import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
import fugashi

_tagger = None
STOP_POS = {"助詞", "助動詞", "補助記号", "記号", "空白"}
STOP_WORDS = {"する", "ある", "いる", "なる", "れる", "られる", "こと", "もの", "よう", "ため", "知る", "たい", "どの", "どれ", "くらい", "ぐらい", "いる", "見る", "調べる", "の", "か", "?", "？"}


def tok(s):
    global _tagger
    if _tagger is None:
        _tagger = fugashi.Tagger()
    out = []
    for w in _tagger(s):
        pos = w.feature.pos1
        if pos in STOP_POS:
            continue
        lemma = w.feature.lemma if (pos in ("動詞", "形容詞") and w.feature.lemma) else w.surface
        lemma = lemma.split("-")[0]
        if lemma in STOP_WORDS:
            continue
        out.append(lemma)
    return out


class BM25:
    def __init__(self, docs_tok, k1=1.2, b=0.75):
        self.cv = CountVectorizer(analyzer=lambda x: x)
        X = self.cv.fit_transform(docs_tok).tocsc().astype(np.float32)
        n = X.shape[0]
        df = np.diff(X.indptr)
        self.idf = np.log(1 + (n - df + 0.5) / (df + 0.5)).astype(np.float32)
        dl = np.asarray(X.sum(1)).ravel()
        X = X.tocoo()
        denom = X.data + k1 * (1 - b + b * dl[X.row] / dl.mean())
        W = sp.csr_matrix((X.data * (k1 + 1) / denom, (X.row, X.col)), shape=X.shape)
        self.W = W.tocsc()
        self.vocab = self.cv.vocabulary_

    def score(self, q_tok):
        s = np.zeros(self.W.shape[0], np.float32)
        for t in set(q_tok):
            j = self.vocab.get(t)
            if j is not None:
                s += self.idf[j] * self.W[:, j].toarray().ravel()
        return s


def kw_and_mask(q_tok, docs_text):
    terms = [t for t in dict.fromkeys(q_tok) if len(t) >= 1]
    m = np.ones(len(docs_text), bool)
    for t in terms:
        m &= np.fromiter((t in d for d in docs_text), bool, len(docs_text))
    return m


class CharTfidf:
    def __init__(self, docs_text):
        self.v = TfidfVectorizer(analyzer="char", ngram_range=(2, 3), sublinear_tf=True, min_df=1)
        self.X = self.v.fit_transform(docs_text)

    def score(self, q):
        return (self.X @ self.v.transform([q]).T).toarray().ravel()


def ranks_from_scores(s, mask=None):
    """スコアの高い順の index。mask があれば mask の中だけ"""
    if mask is not None:
        idx = np.where(mask)[0]
        return idx[np.argsort(-s[idx], kind="stable")]
    return np.argsort(-s, kind="stable")


def rrf(rank_lists, n, k=60, depth=1000):
    s = np.zeros(n)
    for r in rank_lists:
        r = r[:depth]
        s[r] += 1.0 / (k + np.arange(1, len(r) + 1))
    return np.argsort(-s, kind="stable")


def metrics(ranked, rel, K=10):
    """ranked: 並べた index、rel: 正解の index の集合"""
    top = ranked[:K]
    hits = np.array([i in rel for i in top], float)
    hit = float(hits.any())
    # 最初の正解の順位（1000位まで）
    rr = 0.0
    first = None
    for j, i in enumerate(ranked[:1000]):
        if i in rel:
            rr, first = 1.0 / (j + 1), j + 1
            break
    dcg = (hits / np.log2(np.arange(2, len(top) + 2))).sum()
    ideal = (1 / np.log2(np.arange(2, min(len(rel), K) + 2))).sum()
    return dict(hit10=hit, mrr=rr, ndcg10=dcg / ideal if ideal > 0 else 0.0, p10=hits.sum() / K,
                first=first if first else np.nan, n_ret=len(ranked))
