"""02 整形：各項目にカテゴリ（複数可）と、記事に手法の系統を付ける。"""
import re, pandas as pd, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import zz_f122_rules as rules
D = pathlib.Path(__file__).resolve().parent.parent / 'data'
d = pd.read_csv(D / 'items.csv')
d = d[~((d.kind.str.startswith('change')) & d.text.str.contains(rules.ADMIN, regex=True))].copy()
d.loc[d.kind == 'change_readme', 'kind'] = 'change'
def labels(text, dic, strict=False):
    out = []
    for k, pat in dic.items():
        p = '|'.join(pat.split('|')[:rules.STRICT_N]) if strict else pat
        if re.search(p, text): out.append(k)
    return out
for col, strict in (('labels', False), ('labels_strict', True)):
    d[col] = [ '|'.join(labels(t, rules.CHANGE if k == 'change' else rules.CANNOT, strict)) if k in ('change', 'cannot') else ''
               for t, k in zip(d.text, d.kind)]
meth = d[d.kind.isin(['title', 'method'])].groupby('fid').text.apply(' '.join)
fam = {}
for fid, t in meth.items():
    title = d[(d.fid == fid) & (d.kind == 'title')].text.iloc[0]
    paren = ' '.join(re.findall(r'（([^）]*)）', title))
    hit = next((f for f, p in rules.METHOD if re.search(p, paren)), None) or next((f for f, p in rules.METHOD if re.search(p, t)), 'その他')
    fam[fid] = hit
d['family'] = d.fid.map(fam)
d['num'] = d.fid.str[1:].astype(int)
d[d.kind.isin(['change', 'cannot'])].to_csv(D / 'items_labeled.csv', index=False)
pd.Series(fam, name='family').rename_axis('fid').to_csv(D / 'article_family.csv')
print(d[d.kind.isin(['change','cannot'])].groupby('kind').labels.apply(lambda s: (s == '').mean()).round(3).to_dict())
print(pd.Series(fam).value_counts().to_dict())
