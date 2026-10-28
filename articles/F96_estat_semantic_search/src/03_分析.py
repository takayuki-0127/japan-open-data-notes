"""F96 03 分析：統計表の一覧を5通りのしくみで検索し、正解の表が上位に来るかを比べる
出力：cache/emb_*.npy（埋め込みのキャッシュ）, results/per_query.csv, results/summary.csv, results/rel_counts.csv
"""
import json, re, time
import numpy as np, pandas as pd
from common import DATA, RES, CACHE, MODELS, SEED
from engines import tok, BM25, CharTfidf, kw_and_mask, ranks_from_scores, rrf, metrics
from queries import NEEDS

tab = pd.read_csv(DATA / "tables.csv.gz", dtype={"id": str})
texts = tab.text.tolist()
N = len(tab)
print("表の数", N)

# 正解
rel = {}
rows = []
for nd in NEEDS:
    m = (tab.toukei == nd["toukei"]).values
    for pat in nd["title"]:
        m &= tab.title.str.contains(pat, regex=True).values
    for pat in nd.get("path", []):
        m &= tab.path.str.contains(pat, regex=True).values
    rel[nd["id"]] = set(np.where(m)[0])
    rows.append(dict(id=nd["id"], toukei=nd["toukei"], title=" & ".join(nd["title"]), path=" & ".join(nd.get("path", [])), n_rel=int(m.sum()),
                     n_toukei=int((tab.toukei == nd["toukei"]).sum())))
rc = pd.DataFrame(rows)
rc.to_csv(RES / "rel_counts.csv", index=False)
print(rc.to_string())
assert (rc.n_rel > 0).all(), "正解が0件の探しものがある"


def embed_docs(name, prefix="検索文書: "):
    tag = name + ("" if prefix else "_noprefix")
    f = CACHE / f"emb_{tag}.npy"
    if f.exists():
        e = np.load(f)
        if len(e) == N:
            return e
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODELS[name], device="cpu")
    t = time.time()
    e = model.encode([prefix + s for s in texts], batch_size=128, normalize_embeddings=True, show_progress_bar=False).astype(np.float32)
    print(name, "文書の埋め込み", e.shape, f"{time.time()-t:.0f}秒")
    np.save(f, e)
    return e


def embed_q(name, qs, prefix="検索クエリ: "):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODELS[name], device="cpu")
    return model.encode([prefix + q for q in qs], batch_size=64, normalize_embeddings=True).astype(np.float32)


if __name__ == "__main__":
    t0 = time.time()
    docs_tok = [tok(s) for s in texts]
    bm = BM25(docs_tok)
    ch = CharTfidf(texts)
    print("索引", f"{time.time()-t0:.0f}秒")
    E = {n: embed_docs(n) for n in MODELS}
    E_np = embed_docs("ruri-v3-30m", prefix="")

    qrows = [(nd["id"], w, nd[w]) for nd in NEEDS for w in ("kw", "pro", "plain")]
    qtexts = [q for _, _, q in qrows]
    QE = {n: embed_q(n, qtexts) for n in MODELS}
    QE_np = embed_q("ruri-v3-30m", qtexts, prefix="")

    out = []
    RANKS = {}
    for qi, (nid, w, q) in enumerate(qrows):
        R = rel[nid]
        qt = tok(q)
        s_bm = bm.score(qt)
        r_bm = ranks_from_scores(s_bm)
        mask = kw_and_mask(qt, texts)
        r_kw = ranks_from_scores(s_bm, mask)
        r_ch = ranks_from_scores(ch.score(q))
        r30 = ranks_from_scores(E["ruri-v3-30m"] @ QE["ruri-v3-30m"][qi])
        r70 = ranks_from_scores(E["ruri-v3-70m"] @ QE["ruri-v3-70m"][qi])
        r30np = ranks_from_scores(E_np @ QE_np[qi])
        r_hy = rrf([r_bm, r30], N)
        methods = {"kw_and": r_kw, "bm25": r_bm, "char": r_ch, "ruri30": r30, "ruri70": r70, "hybrid": r_hy, "ruri30_noprefix": r30np}
        for mname, r in methods.items():
            d = metrics(r, R)
            d.update(need=nid, wording=w, query=q, method=mname, n_rel=len(R), q_tokens=" ".join(qt))
            out.append(d)
            RANKS[(nid, w, mname)] = r[:50]
    pq = pd.DataFrame(out)
    pq.to_csv(RES / "per_query.csv", index=False)
    np.save(RES / "top50.npy", {f"{a}|{b}|{c}": v for (a, b, c), v in RANKS.items()}, allow_pickle=True)

    # 集計（探しもの単位のブートストラップ 95% 区間）
    rng = np.random.default_rng(SEED)
    needs = pq.need.unique()
    B = 2000
    boot_idx = rng.integers(0, len(needs), (B, len(needs)))
    summ = []
    for (mname, w), g in pq.groupby(["method", "wording"]):
        g = g.set_index("need").loc[needs]
        for met in ["hit10", "mrr", "ndcg10", "p10"]:
            v = g[met].values
            bs = v[boot_idx].mean(1)
            summ.append(dict(method=mname, wording=w, metric=met, mean=v.mean(), lo=np.quantile(bs, .025), hi=np.quantile(bs, .975)))
        summ.append(dict(method=mname, wording=w, metric="zero_hit", mean=(g.n_ret == 0).mean(), lo=np.nan, hi=np.nan))
    sm = pd.DataFrame(summ)
    sm.to_csv(RES / "summary.csv", index=False)
    piv = sm[sm.metric.isin(["hit10", "mrr", "zero_hit"])].pivot_table(index="method", columns=["metric", "wording"], values="mean")
    print(piv.round(3).to_string())

    # 手法どうしの差（対応のあるブートストラップ）
    diffs = []
    for w in ["kw", "pro", "plain", "all"]:
        sub = pq if w == "all" else pq[pq.wording == w]
        P = sub.pivot_table(index=["need", "wording"], columns="method", values="hit10")
        Pm = sub.pivot_table(index=["need", "wording"], columns="method", values="mrr")
        keys = P.index.get_level_values(0).unique()
        for a, b in [("ruri30", "bm25"), ("hybrid", "bm25"), ("hybrid", "ruri30"), ("ruri70", "ruri30"), ("ruri30", "kw_and"), ("char", "bm25"), ("ruri30", "ruri30_noprefix")]:
            for met, M in [("hit10", P), ("mrr", Pm)]:
                dv = (M[a] - M[b]).groupby(level=0).mean().loc[keys].values
                bs = dv[rng.integers(0, len(dv), (B, len(dv)))].mean(1)
                diffs.append(dict(wording=w, a=a, b=b, metric=met, diff=dv.mean(), lo=np.quantile(bs, .025), hi=np.quantile(bs, .975)))
    pd.DataFrame(diffs).to_csv(RES / "diffs.csv", index=False)
    print(pd.DataFrame(diffs).round(3).to_string())
    json.dump(dict(N=N, needs=len(NEEDS), queries=len(qrows), sec=round(time.time() - t0)), open(RES / "run_info.json", "w"))
