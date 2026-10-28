"""F96 03b 頑健性
1. 件数：正解以外の表を 5%・10%・25%・50%・100% に間引いたとき（乱数5通り）、上位10件に正解が入る割合がどう変わるか
2. 文書の文：表題だけ ／ 表題＋政府統計名＋分類（基本）
3. 埋め込みモデル（30m／70m）と接頭辞の有無は 03 の per_query.csv にある
出力：results/robust_size.csv, results/robust_doctext.csv
"""
import numpy as np, pandas as pd
from common import DATA, RES, CACHE, MODELS, SEED
from engines import tok, BM25, CharTfidf, kw_and_mask, ranks_from_scores, rrf, metrics
from queries import NEEDS
import importlib
A = importlib.import_module("03_分析")

tab, texts, N, rel = A.tab, A.texts, A.N, A.rel
qrows = [(nd["id"], w, nd[w]) for nd in NEEDS for w in ("kw", "pro", "plain")]
qtexts = [q for _, _, q in qrows]
E30 = A.embed_docs("ruri-v3-30m")
Q30 = A.embed_q("ruri-v3-30m", qtexts)
docs_tok = [tok(s) for s in texts]
qtoks = [tok(q) for q in qtexts]

# 1. 件数
all_rel = set().union(*rel.values())
others = np.array([i for i in range(N) if i not in all_rel])
rng = np.random.default_rng(SEED)
rows = []
for frac in [0.05, 0.1, 0.25, 0.5, 1.0]:
    for rep in range(5 if frac < 1 else 1):
        keep = np.sort(np.concatenate([np.array(sorted(all_rel)), rng.choice(others, int(len(others) * frac), replace=False)]))
        sub_tok = [docs_tok[i] for i in keep]
        bm = BM25(sub_tok)
        pos = {g: j for j, g in enumerate(keep)}
        Es = E30[keep]
        for qi, (nid, w, q) in enumerate(qrows):
            R = {pos[i] for i in rel[nid]}
            r_bm = ranks_from_scores(bm.score(qtoks[qi]))
            r30 = ranks_from_scores(Es @ Q30[qi])
            r_hy = rrf([r_bm, r30], len(keep))
            for m, r in [("bm25", r_bm), ("ruri30", r30), ("hybrid", r_hy)]:
                d = metrics(r, R)
                rows.append(dict(frac=frac, rep=rep, n_docs=len(keep), need=nid, wording=w, method=m, hit10=d["hit10"], mrr=d["mrr"]))
    print("frac", frac, "done")
rs = pd.DataFrame(rows)
agg = rs.groupby(["frac", "method", "wording"]).agg(n_docs=("n_docs", "mean"), hit10=("hit10", "mean"), mrr=("mrr", "mean")).reset_index()
agg.to_csv(RES / "robust_size.csv", index=False)
print(agg.pivot_table(index=["frac"], columns=["method"], values="hit10").round(3))

# 2. 文書の文：表題だけ
titles = tab.title.tolist()
from sentence_transformers import SentenceTransformer
f = CACHE / "emb_ruri-v3-30m_titleonly.npy"
if f.exists():
    Et = np.load(f)
else:
    model = SentenceTransformer(MODELS["ruri-v3-30m"], device="cpu")
    Et = model.encode(["検索文書: " + s for s in titles], batch_size=128, normalize_embeddings=True).astype(np.float32)
    np.save(f, Et)
bmt = BM25([tok(s) for s in titles])
rows = []
for qi, (nid, w, q) in enumerate(qrows):
    R = rel[nid]
    r_bm = ranks_from_scores(bmt.score(qtoks[qi]))
    r30 = ranks_from_scores(Et @ Q30[qi])
    r_hy = rrf([r_bm, r30], N)
    for m, r in [("bm25", r_bm), ("ruri30", r30), ("hybrid", r_hy)]:
        d = metrics(r, R)
        rows.append(dict(doctext="表題だけ", need=nid, wording=w, method=m, hit10=d["hit10"], mrr=d["mrr"]))
pq = pd.read_csv(RES / "per_query.csv")
base = pq[pq.method.isin(["bm25", "ruri30", "hybrid"])][["need", "wording", "method", "hit10", "mrr"]].assign(doctext="表題＋統計名＋分類")
rd = pd.concat([pd.DataFrame(rows), base])
agg2 = rd.groupby(["doctext", "method", "wording"])[["hit10", "mrr"]].mean().reset_index()
agg2.to_csv(RES / "robust_doctext.csv", index=False)
print(agg2.pivot_table(index=["doctext", "method"], columns="wording", values="hit10").round(3))
