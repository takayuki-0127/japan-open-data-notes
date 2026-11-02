"""03 分析：設計から変えたこと（change）と言えないこと（cannot）を、カテゴリ別・手法の系統別に集計する。
主の集計＝記事単位（そのカテゴリが1回でも出た記事の割合）。頑健性＝(1) 項目数で数える (2) 辞書を厳しくする (3) 単一ラベル (4) 前半 F01–F60 と後半 F61–F120 に分ける。"""
import pandas as pd, numpy as np, json, pathlib
D = pathlib.Path(__file__).resolve().parent.parent / 'data'
R = pathlib.Path(__file__).resolve().parent.parent / 'results'; R.mkdir(exist_ok=True)
d = pd.read_csv(D / 'items_labeled.csv').fillna({'labels': '', 'labels_strict': ''})
fam = pd.read_csv(D / 'article_family.csv').set_index('fid').family
N = fam.size
out = {'n_articles': int(N), 'n_change': int((d.kind == 'change').sum()), 'n_cannot': int((d.kind == 'cannot').sum())}

def explode(x, col):
    e = x.assign(cat=x[col].str.split('|')).explode('cat')
    return e[e.cat != '']

rows = []
for kind in ('change', 'cannot'):
    x = d[d.kind == kind]
    out[f'unlabeled_{kind}'] = round(float((x.labels == '').mean()), 3)
    e = explode(x, 'labels')
    art = e.groupby('cat').fid.nunique() / N                      # 主：記事の割合
    items = e.groupby('cat').size() / len(x)                       # 頑健性1：項目の割合
    es = explode(x, 'labels_strict')
    strict = es.groupby('cat').fid.nunique() / N                   # 頑健性2：厳しい辞書
    first = x.assign(cat=x.labels.str.split('|').str[0]); first = first[first.cat != '']
    single = first.groupby('cat').fid.nunique() / N                # 頑健性3：単一ラベル
    early = e[e.num <= 60].groupby('cat').fid.nunique() / (fam.index.str[1:].astype(int) <= 60).sum()
    late = e[e.num > 60].groupby('cat').fid.nunique() / (fam.index.str[1:].astype(int) > 60).sum()
    t = pd.DataFrame({'記事の割合': art, '項目の割合': items, '厳しい辞書': strict, '単一ラベル': single, '前半F01-60': early, '後半F61-120': late}).fillna(0)
    t['kind'] = kind
    t['順位_主'] = t['記事の割合'].rank(ascending=False, method='min')
    for c in ['項目の割合', '厳しい辞書', '単一ラベル', '前半F01-60', '後半F61-120']:
        t[f'順位_{c}'] = t[c].rank(ascending=False, method='min')
    rows.append(t)
cat = pd.concat(rows).round(3)
cat.to_csv(R / 'category_rates.csv')

# 順位の一致（スピアマン）
from scipy.stats import spearmanr
rob = []
for kind, t in cat.groupby('kind'):
    for c in ['項目の割合', '厳しい辞書', '単一ラベル', '前半F01-60', '後半F61-120']:
        rho = spearmanr(t['記事の割合'], t[c]).statistic
        top_same = t['記事の割合'].idxmax() == t[c].idxmax()
        rob.append(dict(kind=kind, check=c, spearman=round(float(rho), 3), top1_same=bool(top_same), top1=t[c].idxmax()))
rob = pd.DataFrame(rob); rob.to_csv(R / 'robustness.csv', index=False)

# 手法の系統 × カテゴリ（記事の割合）、系統ごとの記事数
fams = fam.value_counts()
ct = []
for kind in ('change', 'cannot'):
    e = explode(d[d.kind == kind], 'labels')
    m = e.groupby(['family', 'cat']).fid.nunique().unstack(fill_value=0)
    m = m.div(fams.reindex(m.index), axis=0)
    m['kind'] = kind; m['n_articles'] = fams.reindex(m.index)
    ct.append(m)
fc = pd.concat(ct).round(3); fc.to_csv(R / 'family_by_category.csv')

# 系統ごとに「全体より多い」カテゴリ（記事の割合の差、記事5本以上の系統のみ）
lift = []
for kind in ('change', 'cannot'):
    m = fc[fc.kind == kind].drop(columns=['kind'])
    base = cat[cat.kind == kind]['記事の割合']
    for f, r in m.iterrows():
        if r.n_articles < 5: continue
        diff = (r.drop('n_articles') - base.reindex(r.drop('n_articles').index)).dropna()
        k = diff.idxmax()
        lift.append(dict(kind=kind, family=f, n=int(r.n_articles), top_cat=k, rate=round(float(r[k]), 2), overall=round(float(base[k]), 2), diff=round(float(diff[k]), 2)))
lift = pd.DataFrame(lift); lift.to_csv(R / 'family_top_pitfall.csv', index=False)

# 1記事あたりの項目数の推移（前半と後半）
per = d.groupby(['fid', 'kind']).size().unstack(fill_value=0).reindex(fam.index, fill_value=0)
per['num'] = per.index.str[1:].astype(int)
per.to_csv(R / 'items_per_article.csv')
out['per_article'] = {k: {'all': round(float(per[k].mean()), 2), 'early': round(float(per[per.num <= 60][k].mean()), 2), 'late': round(float(per[per.num > 60][k].mean()), 2)} for k in ('change', 'cannot')}
out['top_change'] = cat[cat.kind == 'change']['記事の割合'].sort_values(ascending=False).head(3).to_dict()
out['top_cannot'] = cat[cat.kind == 'cannot']['記事の割合'].sort_values(ascending=False).head(3).to_dict()
out['robustness_min_spearman'] = float(rob.spearman.min())
json.dump(out, open(R / 'summary.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1)); print(rob); print(lift)
