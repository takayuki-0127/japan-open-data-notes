"""データの系譜：記事×データの二部グラフと、記事どうしの再利用ネットワークを集計する"""
import os, json, itertools
import pandas as pd, numpy as np, networkx as nx
from scipy import stats
D = os.path.join(os.path.dirname(__file__), '..', 'data'); R = os.path.join(os.path.dirname(__file__), '..', 'results')
art = pd.read_csv(f'{D}/articles.csv'); ad = pd.read_csv(f'{D}/article_dataset.csv'); ad_s = pd.read_csv(f'{D}/article_dataset_srconly.csv')
ru = pd.read_csv(f'{D}/article_reuse.csv'); lab = pd.read_csv(f'{D}/f122_items_labeled.csv')
N = len(art); out = {}
# 1) どのデータがよく使われたか
deg = ad.groupby(['dataset', 'group']).article.nunique().reset_index(name='n_articles').sort_values('n_articles', ascending=False)
deg['share'] = deg.n_articles / N; deg.to_csv(f'{R}/dataset_degree.csv', index=False)
per_art = ad.groupby('article').dataset.nunique()
out['n_articles'] = N; out['n_datasets'] = int(deg.shape[0]); out['links'] = int(len(ad))
out['datasets_per_article_mean'] = round(float(per_art.reindex(art.article, fill_value=0).mean()), 2)
out['articles_no_match'] = int((per_art.reindex(art.article, fill_value=0) == 0).sum())
out['top10'] = deg.head(10)[['dataset', 'n_articles']].values.tolist()
c = deg.n_articles.sort_values(ascending=False).cumsum() / deg.n_articles.sum()
out['n_datasets_for_half_links'] = int((c < 0.5).sum() + 1)
top5 = set(deg.head(5).dataset)
out['share_articles_using_top5'] = round(float(ad[ad.dataset.isin(top5)].article.nunique() / N), 3)
once = deg[deg.n_articles == 1]; out['datasets_used_once'] = int(len(once))
grp = ad.groupby('group').article.nunique().sort_values(ascending=False); grp.to_csv(f'{R}/group_degree.csv')
# データの共起（2つのデータを同じ記事で使った回数）
co = {}
for a, g in ad.groupby('article'):
    for x, y in itertools.combinations(sorted(set(g.dataset)), 2): co[(x, y)] = co.get((x, y), 0) + 1
pd.DataFrame([(x, y, w) for (x, y), w in co.items()], columns=['a', 'b', 'w']).sort_values('w', ascending=False).to_csv(f'{R}/dataset_cooccurrence.csv', index=False)
# 2) 記事どうしの再利用
def reuse_stats(df, tag):
    G = nx.DiGraph(); G.add_nodes_from(art.article); G.add_edges_from(zip(df.from_article, df.to_article))
    users = [n for n in G if G.in_degree(n) > 0]; srcs = sorted(G.nodes, key=lambda n: -G.out_degree(n))
    dag = nx.is_directed_acyclic_graph(G)
    lp = nx.dag_longest_path(G) if dag else []
    comps = sorted((len(c) for c in nx.weakly_connected_components(G) if len(c) > 1), reverse=True)
    num = dict(zip(art.article, art.num))
    bins = pd.cut(art.num, [0, 20, 40, 60, 80, 100, 120], labels=['F01–20', 'F21–40', 'F41–60', 'F61–80', 'F81–100', 'F101–120'])
    trend = art.assign(bin=bins, uses=art.article.isin(users)).groupby('bin', observed=True).uses.mean().round(3)
    return dict(edges=int(G.number_of_edges()), n_reusers=len(users), share_reusers=round(len(users) / N, 3),
                top_sources=[(s, G.out_degree(s)) for s in srcs[:8]], is_dag=dag, longest_chain=lp,
                components=comps[:5], trend=trend.to_dict(), users=sorted(users, key=lambda a: num[a]))
loose = reuse_stats(ru, 'loose'); strict = reuse_stats(ru[ru.in_code == 1], 'strict'); readme = reuse_stats(ru[ru.in_readme == 1], 'readme')
out['reuse_loose'] = {k: v for k, v in loose.items() if k != 'users'}; out['reuse_strict'] = {k: v for k, v in strict.items() if k != 'users'}
out['reuse_readme'] = {k: v for k, v in readme.items() if k != 'users'}
# 前半と後半で再利用の割合に差があるか（Fisher）
u = art.article.isin(loose['users']); early = art.num <= 60
tab = [[int((u & early).sum()), int((~u & early).sum())], [int((u & ~early).sum()), int((~u & ~early).sum())]]
out['early_vs_late'] = dict(table=tab, p=round(float(stats.fisher_exact(tab)[1]), 4))
# 3) 再利用した記事と、しなかった記事で「つまずき」の出方は違うか（F122 の分類を使う）
lab['labs'] = lab['labels'].fillna('')
cats = sorted(set(itertools.chain.from_iterable(x.split('|') for x in lab.labs if x)))
rows = []
for cat in cats:
    has = lab[lab.labs.str.contains(cat, regex=False)].fid.unique()
    a1 = art.article.isin(has)
    t = [[int((a1 & u).sum()), int((~a1 & u).sum())], [int((a1 & ~u).sum()), int((~a1 & ~u).sum())]]
    rows.append(dict(category=cat, reusers=round(t[0][0] / u.sum(), 3), non_reusers=round(t[1][0] / (~u).sum(), 3),
                     diff=round(t[0][0] / u.sum() - t[1][0] / (~u).sum(), 3), p=round(float(stats.fisher_exact(t)[1]), 4)))
pit = pd.DataFrame(rows).sort_values('diff', ascending=False); pit.to_csv(f'{R}/pitfalls_reuse_vs_not.csv', index=False)
out['pitfalls'] = pit.head(12).values.tolist(); out['n_reusers'] = int(u.sum())
# 4) データの量
sz = art.assign(mb=art.data_bytes / 1e6, uses=u)
out['data_mb_median'] = dict(reusers=round(float(sz[sz.uses].mb.median()), 2), others=round(float(sz[~sz.uses].mb.median()), 2),
                            mw_p=round(float(stats.mannwhitneyu(sz[sz.uses].mb, sz[~sz.uses].mb).pvalue), 4))
# 頑健性
rb = {}
deg_s = ad_s.groupby('dataset').article.nunique()
m = deg.set_index('dataset').n_articles.to_frame('main').join(deg_s.rename('src_only'), how='outer').fillna(0)
rb['R1_source_only_spearman'] = round(float(stats.spearmanr(m.main, m.src_only)[0]), 3)
rb['R1_top5_overlap'] = len(top5 & set(deg_s.sort_values(ascending=False).head(5).index))
rb['R2_group_rank'] = grp.to_dict()
rb['R3_strict_vs_loose'] = dict(loose=loose['share_reusers'], strict=strict['share_reusers'], readme=readme['share_reusers'])
ex = art[~art.num.isin([89, 100, 118, 119, 120])]
uex = ex.article.isin(loose['users'])
bins = pd.cut(ex.num, [0, 20, 40, 60, 80, 100, 120])
rb['R4_trend_excluding_synthesis'] = ex.assign(b=bins.astype(str), u=uex).groupby('b').u.mean().round(3).to_dict()
rb['R4_share_excluding_synthesis'] = round(float(uex.mean()), 3)
# R5 名寄せの粒度を粗くしても上位が変わらないか：粗い区分（group）での記事数
rb['R5_top3_groups'] = grp.head(3).to_dict()

# R6 時期（前半・後半）をそろえても、つまずきの差は残るか（Mantel–Haenszel のオッズ比）
from statsmodels.stats.contingency_tables import StratifiedTable
r6 = {}
for cat in ['期間・ほかの場面への一般化', '不確実性・検出力', '定義・測定のずれ', '既存データの再利用']:
    has = lab[lab.labs.str.contains(cat, regex=False)].fid.unique(); a1 = art.article.isin(has)
    tabs = []
    for half in [early, ~early]:
        tabs.append(np.array([[int((a1 & u & half).sum()), int((~a1 & u & half).sum())], [int((a1 & ~u & half).sum()), int((~a1 & ~u & half).sum())]]) + 0.5)
    st = StratifiedTable(tabs)
    r6[cat] = dict(or_mh=round(float(st.oddsratio_pooled), 2), p=round(float(st.test_null_odds().pvalue), 4))
rb['R6_mh_by_half'] = r6
out['robustness'] = rb
json.dump(out, open(f'{R}/summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
pd.DataFrame([dict(check=k, value=json.dumps(v, ensure_ascii=False, default=str)) for k, v in rb.items()]).to_csv(f'{R}/robustness.csv', index=False)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:6000])
