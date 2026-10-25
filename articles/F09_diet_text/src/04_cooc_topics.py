"""04 一緒に語られた言葉（年代別の特徴語・共起ネットワーク）と、トピックモデル（LDA）"""
import gzip, json, itertools
from collections import Counter
import numpy as np, pandas as pd, networkx as nx
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from common import DATA, RES, SEED, PERIODS, period_of

docs = [json.loads(l) for l in gzip.open(DATA / "tokens.jsonl.gz", "rt", encoding="utf-8")]
d = pd.DataFrame(docs)
d["period"] = d.y.map(period_of)
KW = {"賃上げ": {"賃上げ", "賃金"}, "物価": {"物価"}}
print(d.groupby(["k", "period"]).size())
d.groupby(["k", "period"]).size().rename("n_speeches").to_csv(RES / "sample_sizes.csv")


def log_odds(cnt_a, cnt_b, prior, a0):
    """重み付き対数オッズ比（Monroe ほか 2008、事前分布つき）。z 値を返す"""
    na, nb = sum(cnt_a.values()), sum(cnt_b.values())
    out = {}
    for w in set(cnt_a) | set(cnt_b):
        ya, yb, aw = cnt_a.get(w, 0), cnt_b.get(w, 0), prior[w] * a0
        da = np.log((ya + aw) / (na + a0 - ya - aw)); db = np.log((yb + aw) / (nb + a0 - yb - aw))
        var = 1 / (ya + aw) + 1 / (yb + aw)
        out[w] = (da - db) / np.sqrt(var)
    return out


rows = []
for k in KW:
    sub = d[d.k == k]
    allc = Counter(w for t in sub.toks for w in set(t) if w not in KW[k])
    tot = sum(allc.values()); prior = {w: c / tot for w, c in allc.items()}
    for _, _, lab in PERIODS:
        a = Counter(w for t in sub[sub.period == lab].toks for w in set(t) if w not in KW[k])
        b = Counter(w for t in sub[sub.period != lab].toks for w in set(t) if w not in KW[k])
        z = log_odds(a, b, prior, a0=500)
        n = (sub.period == lab).sum()
        top = sorted([w for w in z if a.get(w, 0) >= 8], key=lambda w: -z[w])[:12]
        for r, w in enumerate(top, 1):
            rows.append({"keyword": k, "period": lab, "rank": r, "word": w, "z": round(z[w], 2),
                         "share_of_speeches": round(a[w] / n, 3)})
pd.DataFrame(rows).to_csv(RES / "distinctive_words_by_period.csv", index=False)

# 共起ネットワーク（「賃上げ」の抜粋。1985〜94年と2015〜26年）
net = {}
for lab in ["1985〜94年", "2015〜26年"]:
    sub = d[(d.k == "賃上げ") & (d.period == lab)]
    sets = [set(t) - KW["賃上げ"] for t in sub.toks]
    df_ = Counter(w for s in sets for w in s)
    nodes = [w for w, _ in df_.most_common(30)]
    co = Counter()
    for s in sets:
        for a, b in itertools.combinations(sorted(s & set(nodes)), 2):
            co[(a, b)] += 1
    edges = []
    for (a, b), n in co.items():
        jac = n / (df_[a] + df_[b] - n)
        edges.append((a, b, jac))
    edges = sorted(edges, key=lambda e: -e[2])[:45]
    net[lab] = {"nodes": {w: df_[w] for w in nodes}, "edges": edges, "n": len(sets)}
json.dump(net, open(RES / "cooc_network.json", "w"), ensure_ascii=False, indent=1)

# トピックモデル（LDA）：賃上げ・物価の抜粋をまとめて
texts = [" ".join(t) for t in d.toks]


def fit(K, seed):
    vec = CountVectorizer(tokenizer=str.split, lowercase=False, min_df=10, max_df=0.4, token_pattern=None)
    X = vec.fit_transform(texts)
    lda = LatentDirichletAllocation(n_components=K, random_state=seed, learning_method="batch", max_iter=60,
                                    doc_topic_prior=0.1, topic_word_prior=0.05)
    th = lda.fit_transform(X)
    vocab = np.array(vec.get_feature_names_out())
    tops = [list(vocab[np.argsort(-lda.components_[j])[:15]]) for j in range(K)]
    return th, tops, lda.perplexity(X), X.shape


th, tops, ppl, shp = fit(8, SEED)
print("matrix", shp, "perplexity", round(ppl, 1))
pd.DataFrame({"topic": range(8), "top_words": [" ".join(t) for t in tops]}).to_csv(RES / "lda_k8_topics.csv", index=False)
T = pd.DataFrame(th, columns=[f"t{j}" for j in range(8)])
T["y"], T["k"] = d.y.values, d.k.values
T.groupby(["k", "y"]).mean().round(4).to_csv(RES / "lda_k8_share_by_year.csv")
T.groupby("y").mean(numeric_only=True).round(4).to_csv(RES / "lda_k8_share_by_year_all.csv")

# 頑健性：トピック数・乱数の種を変えて、K=8 の各トピックに最も近いトピック（上位15語の Jaccard）と
#        年ごとの構成比の相関を見る
rob = []
base_share = T.groupby("y").mean(numeric_only=True)
for K, seed in [(6, SEED), (10, SEED), (8, SEED + 1), (8, SEED + 2)]:
    th2, tops2, ppl2, _ = fit(K, seed)
    sh2 = pd.DataFrame(th2).assign(y=d.y.values).groupby("y").mean()
    for j in range(8):
        jac = [len(set(tops[j]) & set(t)) / len(set(tops[j]) | set(t)) for t in tops2]
        m = int(np.argmax(jac))
        rob.append({"K": K, "seed": seed, "topic_k8": j, "best_match": m, "jaccard": round(jac[m], 2),
                    "share_corr": round(base_share[f"t{j}"].corr(sh2[m]), 3)})
pd.DataFrame(rob).to_csv(RES / "lda_robustness.csv", index=False)
print(pd.DataFrame(rob).groupby(["K", "seed"])[["jaccard", "share_corr"]].median())
for j, t in enumerate(tops):
    print(j, " ".join(t[:12]))

# 頑健性（トピックモデルを使わない確認）：「賃上げ」の抜粋のうち、労使系の語・政策系の語を含む割合
groups = {"労使系（春闘・労使・組合・交渉）": {"春闘", "労使", "組合", "交渉"},
          "政策系（税制・支援・補助・助成）": {"税制", "支援", "補助", "助成"}}
rows = []
for lab in [p[2] for p in PERIODS]:
    sub = d[(d.k == "賃上げ") & (d.period == lab)]
    for g, ws in groups.items():
        rows.append({"period": lab, "group": g, "share": round(np.mean([bool(set(t) & ws) for t in sub.toks]), 3), "n": len(sub)})
kb = pd.DataFrame(rows); kb.to_csv(RES / "keyword_group_share.csv", index=False); print(kb.to_string())
