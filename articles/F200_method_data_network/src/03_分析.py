"""記事×手法×データのつながりを集計する（手法の頻度・組み合わせ・使われていない組み合わせ・時期・頑健性）"""
import os, json, itertools, random
import numpy as np, pandas as pd, networkx as nx
from scipy import stats
D = os.path.join(os.path.dirname(__file__), '..', 'data'); R = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(R, exist_ok=True)
dic = json.load(open(os.path.join(D, 'dictionaries.json'), encoding='utf-8'))
FAM, DG = dic['families'], dic['data_groups']
art = pd.read_csv(os.path.join(D, 'articles.csv'))
em = {k: pd.read_csv(os.path.join(D, f'article_method_{k}.csv')) for k in ['main', 'full', 'title']}
ed = pd.read_csv(os.path.join(D, 'article_dataset.csv'))
man = pd.read_csv(os.path.join(D, 'manual_primary_family.csv'))
N = len(art)
TOOLS = ['ブートストラップ', '標本誤差・不確かさ', '置換検定', 'モンテカルロ・擬似データ', '交差検証・予測の評価']
META = [100, 118, 119, 120, 121, 122, 123, 124, 125, 161, 162, 163, 164, 165]  # 記事どうしを振り返る記事
S = {'n_articles': N, 'commit': 'de38ce51a03d811f05262a534e9c6662545f1d90'}

# ---- 1. 手法の頻度 ----
m = em['main']
cnt = m.groupby(['method', 'family']).article.nunique().reset_index(name='articles').sort_values('articles', ascending=False)
cnt['is_tool'] = cnt.method.isin(TOOLS).astype(int)
cnt.to_csv(os.path.join(R, 'method_counts.csv'), index=False)
fam_art = m.groupby('family').article.nunique().reindex(FAM).fillna(0).astype(int)
per_art = m.groupby('article').method.nunique().reindex(art.article).fillna(0)
nontool = m[~m.method.isin(TOOLS)]
S.update(n_edges=int(len(m)), n_methods_used=int(m.method.nunique()), n_methods_dict=len(dic['methods']),
         methods_once=int((cnt.articles == 1).sum()), methods_le2=int((cnt.articles <= 2).sum()),
         per_article_mean=round(float(per_art.mean()), 2), per_article_median=float(per_art.median()),
         per_article_nontool_mean=round(float(nontool.groupby('article').method.nunique().reindex(art.article).fillna(0).mean()), 2),
         top10=cnt.head(10)[['method', 'articles']].values.tolist(),
         top10_nontool=cnt[cnt.is_tool == 0].head(10)[['method', 'articles']].values.tolist(),
         family_articles=fam_art.to_dict(),
         tool_any=int(m[m.method.isin(TOOLS)].article.nunique()))
# 上位の集中：上位10手法がつながりの何割か
S['top10_share_edges'] = round(float(cnt.head(10).articles.sum() / cnt.articles.sum()), 3)
S['top10_nontool_share_edges'] = round(float(cnt[cnt.is_tool == 0].head(10).articles.sum() / cnt[cnt.is_tool == 0].articles.sum()), 3)

# ---- 2. 主な手法の区分：辞書（題名3点＋手法の節1点、道具は除く）と手作業 ----
mt = em['title']
def rule_primary(a):
    sc = {}
    for f in FAM: sc[f] = 0
    for _, x in nontool[nontool.article == a].iterrows(): sc[x.family] += 1
    for _, x in mt[(mt.article == a) & (~mt.method.isin(TOOLS))].iterrows(): sc[x.family] += 3
    best = max(sc.values())
    if best == 0:  # 道具しかない記事は、道具の区分
        f = m[m.article == a].family
        return f.mode().iloc[0] if len(f) else '統計の作法・検定'
    return [f for f in FAM if sc[f] == best][0]
art['family_rule'] = [rule_primary(a) for a in art.article]
art = art.merge(man, on='num')
agree = float((art.family_rule == art.family_manual).mean())
# Cohen の κ
po = agree; pr = art.family_rule.value_counts(normalize=True); pm = art.family_manual.value_counts(normalize=True)
pe = float(sum(pr.get(f, 0) * pm.get(f, 0) for f in FAM)); kappa = (po - pe) / (1 - pe)
# 手作業の区分が、辞書の多重ラベルに含まれるか（取りこぼしの目安）
fams_of = m.groupby('article').family.apply(set)
recall = float(np.mean([r.family_manual in fams_of.get(r.article, set()) for r in art.itertuples()]))
S.update(primary_agree=round(agree, 3), primary_kappa=round(kappa, 3), manual_in_multilabel=round(recall, 3))
conf = pd.crosstab(art.family_manual, art.family_rule).reindex(index=FAM, columns=FAM).fillna(0).astype(int)
conf.to_csv(os.path.join(R, 'primary_confusion.csv'))
art[['article', 'num', 'title', 'family_manual', 'family_rule']].to_csv(os.path.join(R, 'article_primary_family.csv'), index=False)
hc = pd.read_csv(os.path.join(D, 'handcheck_sample.csv'))
S['handcheck_precision'] = [int(hc.correct.sum()), int(len(hc))]

# ---- 3. 時期：番号帯ごとの主な区分と、新しく出てきた手法 ----
bins = [0, 40, 80, 120, 160, 200]; labels = ['F01〜40', 'F41〜80', 'F81〜120', 'F121〜160', 'F161〜199']
art['band'] = pd.cut(art.num, bins=bins, labels=labels)
band_fam = pd.crosstab(art.band, art.family_manual).reindex(columns=FAM).fillna(0).astype(int)
band_fam.to_csv(os.path.join(R, 'band_family_manual.csv'))
first = m.groupby('method').num.min().sort_values()
cum = [(n, int((first <= n).sum())) for n in sorted(art.num)]
pd.DataFrame(cum, columns=['num', 'distinct_methods']).to_csv(os.path.join(R, 'cumulative_methods.csv'), index=False)
new_by_band = {l: int(((first > a) & (first <= b)).sum()) for l, a, b in zip(labels, bins[:-1], bins[1:])}
S['new_methods_by_band'] = new_by_band
S['first_appear_after_160'] = first[first > 160].index.tolist()
# 多様性：番号帯ごとの主な区分のエントロピー（手作業）と、道具を使った記事の割合
ent = {}
for l in labels:
    p = band_fam.loc[l]; p = p[p > 0] / p.sum(); ent[l] = round(float(-(p * np.log2(p)).sum()), 2)
S['band_entropy_manual'] = ent
tool_share = {}
for l in labels:
    arts = art[art.band == l].article
    tool_share[l] = round(float(m[m.article.isin(arts) & m.method.isin(TOOLS)].article.nunique() / len(arts)), 2)
S['band_tool_share'] = tool_share
x = art.assign(t=art.article.isin(m[m.method.isin(TOOLS)].article)).groupby('band', observed=True).t.agg(['sum', 'count'])
S['tool_trend_chi2_p'] = float(stats.chi2_contingency(np.c_[x['sum'], x['count'] - x['sum']])[1])
S['per_article_by_band'] = per_art.groupby(art.set_index('article').band).mean().round(2).to_dict()

# ---- 4. 手法の区分 × データのグループ ----
fam_long = m[['article', 'family']].drop_duplicates()
dg_long = ed[['article', 'group']].drop_duplicates()
S['data_edges'] = int(len(ed)); S['data_articles_matched'] = int(ed.article.nunique())
dcnt = ed.groupby('dataset').article.nunique().sort_values(ascending=False)
dcnt.to_csv(os.path.join(R, 'dataset_counts.csv'), header=['articles'])
S['top_datasets'] = [[k, int(v)] for k, v in dcnt.head(10).items()]
def crosstab(fl):
    j = fl.merge(dg_long, on='article')
    return pd.crosstab(j.family, j.group).reindex(index=FAM, columns=DG).fillna(0).astype(int)
def gaps(ct, art_fam, art_dg, thr=3.0):
    # 独立なら何本が見込まれるか（記事の数で）。見込みが thr 本以上なのに 0 本の組み合わせ
    nf = art_fam.groupby('family').article.nunique().reindex(FAM).fillna(0)
    ng = art_dg.groupby('group').article.nunique().reindex(DG).fillna(0)
    exp = np.outer(nf, ng) / N
    out = []
    for i, f in enumerate(FAM):
        for k, g in enumerate(DG):
            out.append((f, g, int(ct.loc[f, g]), round(float(exp[i, k]), 2), round(float((ct.loc[f, g] + 0.5) / (exp[i, k] + 0.5)), 2)))
    df = pd.DataFrame(out, columns=['family', 'group', 'observed', 'expected', 'ratio'])
    return df, df[(df.observed == 0) & (df.expected >= thr)].sort_values('expected', ascending=False)
ct = crosstab(fam_long); ct.to_csv(os.path.join(R, 'family_x_datagroup.csv'))
cells, zero = gaps(ct, fam_long, dg_long)
cells.to_csv(os.path.join(R, 'family_x_datagroup_cells.csv'), index=False); zero.to_csv(os.path.join(R, 'unused_combinations.csv'), index=False)
S['unused_combinations'] = zero[['family', 'group', 'expected']].values.tolist()
S['zero_cells'] = int((cells.observed == 0).sum()); S['cells'] = int(len(cells))
top_ratio = cells[cells.observed >= 5].sort_values('ratio', ascending=False).head(8)
S['over_represented'] = top_ratio[['family', 'group', 'observed', 'expected']].values.tolist()
# 手作業の主な区分で同じことをする（1記事1区分）
mfl = art[['article', 'family_manual']].rename(columns={'family_manual': 'family'})
ct_m = crosstab(mfl); _, zero_m = gaps(ct_m, mfl, dg_long, thr=2.0)
S['unused_manual_primary'] = zero_m[['family', 'group', 'expected']].values.tolist()
# 細かい手法×細かいデータでの「使われていない」組み合わせの割合
fine = m[['article', 'method']].drop_duplicates().merge(ed[['article', 'dataset']].drop_duplicates(), on='article')
S['fine_pairs_used'] = int(fine[['method', 'dataset']].drop_duplicates().shape[0])
S['fine_pairs_possible'] = int(m.method.nunique() * ed.dataset.nunique())

# ---- 5. 手法どうしのつながり（同じ記事で使った） ----
pairs = {}
for a, g in m.groupby('article'):
    for u, v in itertools.combinations(sorted(set(g.method)), 2): pairs[(u, v)] = pairs.get((u, v), 0) + 1
G = nx.Graph()
fam_of = dict(zip(m.method, m.family))
for u in m.method.unique(): G.add_node(u, family=fam_of[u], articles=int(cnt.set_index('method').articles[u]))
for (u, v), w in pairs.items():
    if w >= 2: G.add_edge(u, v, weight=w)
comms = nx.community.greedy_modularity_communities(G, weight='weight', resolution=1.0)
memb = {n: i for i, c in enumerate(comms) for n in c}
nx.set_node_attributes(G, memb, 'community')
btw = nx.betweenness_centrality(G, weight=None)
deg = dict(G.degree())
cross = {}
for n in G.nodes:
    nb = list(G.neighbors(n)); cross[n] = round(sum(fam_of[x] != fam_of[n] for x in nb) / max(len(nb), 1), 2)
nodes = pd.DataFrame([(n, fam_of[n], G.nodes[n]['articles'], deg[n], round(btw[n], 3), memb[n], cross[n]) for n in G.nodes],
                     columns=['method', 'family', 'articles', 'degree', 'betweenness', 'community', 'share_other_family_neighbors'])
nodes.sort_values('betweenness', ascending=False).to_csv(os.path.join(R, 'method_network_nodes.csv'), index=False)
pd.DataFrame([(u, v, d['weight']) for u, v, d in G.edges(data=True)], columns=['u', 'v', 'articles']).sort_values('articles', ascending=False).to_csv(os.path.join(R, 'method_network_edges.csv'), index=False)
S['net'] = dict(nodes=G.number_of_nodes(), edges=G.number_of_edges(), isolated=int(sum(1 for n in G if G.degree(n) == 0)),
                communities=len(comms), modularity=round(nx.community.modularity(G, comms, weight='weight'), 3))
S['top_betweenness'] = nodes.sort_values('betweenness', ascending=False).head(6)[['method', 'betweenness', 'degree']].values.tolist()
S['top_pairs'] = sorted([(u, v, w) for (u, v), w in pairs.items()], key=lambda x: -x[2])[:8]
S['top_pairs_nontool'] = sorted([(u, v, w) for (u, v), w in pairs.items() if u not in TOOLS and v not in TOOLS], key=lambda x: -x[2])[:8]
# 区分の混ざり具合：コミュニティの中の手法が何区分にまたがるか
S['community_families'] = [[len(c), len({fam_of[n] for n in c})] for c in comms]
# 区分が同じ手法どうしの線の割合と、並べ替えでの基準
same = np.mean([fam_of[u] == fam_of[v] for u, v in G.edges()])
rng = np.random.default_rng(200); labs = [fam_of[n] for n in G.nodes]; idx = {n: i for i, n in enumerate(G.nodes)}
perm = []
for _ in range(2000):
    p = rng.permutation(labs); perm.append(np.mean([p[idx[u]] == p[idx[v]] for u, v in G.edges()]))
S['same_family_edge_share'] = round(float(same), 3); S['same_family_perm_mean'] = round(float(np.mean(perm)), 3)
S['same_family_perm_p'] = float((np.sum(np.array(perm) >= same) + 1) / (len(perm) + 1))

# ---- 6. 頑健性 ----
rob = []
def famshare(e):
    return e.groupby('family').article.nunique().reindex(FAM).fillna(0) / N
base_rank = cnt.set_index('method').articles
for k in ['full', 'title']:
    c2 = em[k].groupby('method').article.nunique()
    common = base_rank.index.intersection(c2.index)
    rho = stats.spearmanr(base_rank[common], c2[common]).correlation
    top_b = set(cnt[cnt.is_tool == 0].head(10).method); top_k = set(c2.drop([t for t in TOOLS if t in c2.index]).sort_values(ascending=False).head(10).index)
    fs = famshare(em[k]); fb = famshare(m)
    ct2 = crosstab(em[k][['article', 'family']].drop_duplicates()); _, z2 = gaps(ct2, em[k][['article', 'family']].drop_duplicates(), dg_long)
    ov = len(set(map(tuple, zero[['family', 'group']].values)) & set(map(tuple, z2[['family', 'group']].values)))
    rob.append(dict(check=f'取り出す範囲：{ {"full": "README 全体", "title": "題名だけ"}[k]}', edges=int(len(em[k])), articles_tagged=int(em[k].article.nunique()),
                    spearman_counts=round(float(rho), 3), top10_nontool_overlap=len(top_b & top_k),
                    max_family_share_diff=round(float((fs - fb).abs().max()), 3), unused_combos=int(len(z2)), unused_overlap_with_main=ov))
# 振り返りの記事を除く
nm = m[~m.num.isin(META)]; c3 = nm.groupby('method').article.nunique()
common = base_rank.index.intersection(c3.index)
ct3 = crosstab(nm[['article', 'family']].drop_duplicates()); _, z3 = gaps(ct3, nm[['article', 'family']].drop_duplicates(), dg_long[~dg_long.article.isin(art[art.num.isin(META)].article)])
rob.append(dict(check='振り返りの記事14本を除く', edges=int(len(nm)), articles_tagged=int(nm.article.nunique()),
                spearman_counts=round(float(stats.spearmanr(base_rank[common], c3[common]).correlation), 3),
                top10_nontool_overlap=len(set(cnt[cnt.is_tool == 0].head(10).method) & set(c3.drop([t for t in TOOLS if t in c3.index]).sort_values(ascending=False).head(10).index)),
                max_family_share_diff=round(float((nm.groupby('family').article.nunique().reindex(FAM).fillna(0) / (N - len(META)) - famshare(m)).abs().max()), 3),
                unused_combos=int(len(z3)), unused_overlap_with_main=len(set(map(tuple, zero[['family', 'group']].values)) & set(map(tuple, z3[['family', 'group']].values)))))
# 見込みのしきい値（2・3・5本）
for thr in [2.0, 5.0]:
    _, zt = gaps(ct, fam_long, dg_long, thr=thr)
    rob.append(dict(check=f'「使われていない」の基準：見込み{thr:.0f}本以上で0本', unused_combos=int(len(zt)),
                    unused_overlap_with_main=len(set(map(tuple, zero[['family', 'group']].values)) & set(map(tuple, zt[['family', 'group']].values)))))
# 手作業の主な区分（1記事1区分）
rob.append(dict(check='手作業の主な区分（1記事1区分、見込み2本以上で0本）', unused_combos=int(len(zero_m)),
                unused_overlap_with_main=len(set(map(tuple, zero[['family', 'group']].values)) & set(map(tuple, zero_m[['family', 'group']].values)))))
# 辞書の語を1区分ずつ抜く（区分の組み合わせの0がどれだけ動くか）は区分ごとに自明なので、代わりに乱数で辞書の1割を抜く
rs = []
names = [n for n, p, f in dic['methods']]
for s in range(200):
    rnd = random.Random(s); drop = set(rnd.sample(names, k=len(names) // 10))
    mm = m[~m.method.isin(drop)][['article', 'family']].drop_duplicates()
    _, zz = gaps(crosstab(mm), mm, dg_long)
    rs.append(len(set(map(tuple, zero[['family', 'group']].values)) & set(map(tuple, zz[['family', 'group']].values))) / max(len(zero), 1))
rob.append(dict(check='辞書の手法を1割ずつ無作為に抜く（200回）', unused_overlap_with_main=f'平均 {np.mean(rs):.2f}（5%点 {np.percentile(rs, 5):.2f}）'))
rob.append(dict(check='主な区分：辞書と手作業の一致', unused_overlap_with_main=f'一致 {agree:.3f}、κ {kappa:.3f}'))
rob.append(dict(check='手作業での確認（無作為60件の当たり）', unused_overlap_with_main=f'{hc.correct.sum()}/{len(hc)}'))
pd.DataFrame(rob).to_csv(os.path.join(R, 'robustness.csv'), index=False)
S['robustness'] = rob
S['dict_drop_overlap_mean'] = round(float(np.mean(rs)), 3)
json.dump(S, open(os.path.join(R, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(S, ensure_ascii=False, indent=0, default=str)[:6000])

# ---- 7. 「使われていない組み合わせ」の安定性：6つの条件で何回 0 本（見込み以上）になったか ----
conds = {}
conds['主（題名＋手法、見込み3本）'] = zero
conds['見込み2本'] = gaps(ct, fam_long, dg_long, thr=2.0)[1]
for k, lab in [('full', 'README 全体'), ('title', '題名だけ')]:
    e2 = em[k][['article', 'family']].drop_duplicates(); conds[lab] = gaps(crosstab(e2), e2, dg_long, thr=2.0)[1]
e3 = nm[['article', 'family']].drop_duplicates(); conds['振り返りを除く'] = gaps(crosstab(e3), e3, dg_long[~dg_long.article.isin(art[art.num.isin(META)].article)], thr=2.0)[1]
conds['手作業の主な区分'] = zero_m
stab = {}
for lab, z in conds.items():
    for f, g in z[['family', 'group']].values: stab.setdefault((f, g), []).append(lab)
st = pd.DataFrame([(f, g, len(v), '・'.join(v)) for (f, g), v in stab.items()], columns=['family', 'group', 'n_conditions', 'conditions']).sort_values('n_conditions', ascending=False)
st = st.merge(cells[['family', 'group', 'observed', 'expected']], on=['family', 'group'])
st.to_csv(os.path.join(R, 'unused_stability.csv'), index=False)
S['unused_stable'] = st[st.n_conditions >= 3][['family', 'group', 'n_conditions', 'observed', 'expected']].values.tolist()
S['manual_primary_counts'] = art.family_manual.value_counts().reindex(FAM).fillna(0).astype(int).to_dict()
S['band_family_manual'] = band_fam.to_dict(orient='index')
json.dump(S, open(os.path.join(R, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(st.head(12).to_string()); print(S['manual_primary_counts']); print(band_fam.to_string())

# ---- 8. 番号帯での主な区分の変化（手作業の区分、Fisher の正確検定） ----
def fisher(fam, cut):
    a = art[art.num <= cut]; b = art[art.num > cut]
    t = [[int((a.family_manual == fam).sum()), int((a.family_manual != fam).sum())], [int((b.family_manual == fam).sum()), int((b.family_manual != fam).sum())]]
    return dict(family=fam, cut=cut, early=f'{t[0][0]}/{len(a)}', late=f'{t[1][0]}/{len(b)}', p=round(float(stats.fisher_exact(t)[1]), 4))
S['fisher'] = [fisher('因果推論', 40), fisher('統計の作法・検定', 80), fisher('分布・極値', 160), fisher('ベイズ・階層', 40), fisher('時系列', 100)]
json.dump(S, open(os.path.join(R, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(S['fisher'])
