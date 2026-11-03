"""手作業の判定（data/hand_labels.csv）と自動の種類分け（data/interim/）を合わせて集計する。"""
import pathlib, os, json, re, collections
import numpy as np, pandas as pd
from scipy import stats
HERE = pathlib.Path(__file__).resolve().parent.parent; os.chdir(HERE)
os.makedirs('results', exist_ok=True)
rng = np.random.default_rng(163)
TYPES = ['期間・時期','対象を絞る・除く','定義・指標','変数・調整','モデル・推定法','設定値・パラメータ','データ源・集計単位','検証の分け方','プラセボ・並べ替え']
H = pd.read_csv('data/hand_labels.csv', dtype=str).fillna('')
H['n'] = H.fid.str[1:].astype(int); H = H.sort_values('n').reset_index(drop=True)
H['judged'] = H.level != ''
H['lv'] = pd.to_numeric(H.level, errors='coerce')
coded = {m: json.load(open(f'data/interim/coded_{m}.json')) for m in ['main','text','strict']}
items = json.load(open('data/interim/items.json'))

def used_types(mode='any'):
    u = collections.defaultdict(set)
    for x in coded['main']:
        ts = x['types'] if mode == 'any' else [x['primary']]
        for t in ts:
            if t in TYPES: u[x['fid']].add(t)
    return u
U = used_types('any'); Up = used_types('primary')
# checks per article (表の行と箇条書き、基本の行と判定のない地の文を除く)
nchk = collections.Counter(x['fid'] for x in coded['main'] if x['kind'] in ('row','bul','ext') and x['primary'] != 'まとめ（複数のチェック）')
H['n_checks'] = H.fid.map(lambda f: nchk.get(f, 0))
H['n_types'] = H.fid.map(lambda f: len(U.get(f, ())))
J = H[H.judged].copy()

out = {}
out['n_articles'] = len(H); out['n_judged'] = int(J.shape[0])
out['level_counts'] = {int(k): int(v) for k, v in J.lv.value_counts().sort_index().items()}
out['level_share'] = {int(k): round(v, 3) for k, v in J.lv.value_counts(normalize=True).sort_index().items()}
out['checks_median'] = float(H.n_checks.median()); out['checks_iqr'] = [float(H.n_checks.quantile(.25)), float(H.n_checks.quantile(.75))]
out['types_median'] = float(H.n_types.median())

def boot(fn, df, B=2000):
    v = [fn(df.sample(len(df), replace=True, random_state=int(rng.integers(1e9)))) for _ in range(B)]
    return np.percentile(v, [2.5, 97.5]).round(3).tolist()

# 1. 種類ごと：使った記事の割合、動かした記事の数、効き目（使った記事のうち、その種類が動かした割合）
def type_table(df, Uset, lvmin=1):
    rows = []
    for t in TYPES:
        ran = df[df.fid.map(lambda f: t in Uset.get(f, ()))]
        moved = ran[(ran.lv >= lvmin) & (ran.mover == t)]
        moved_all = df[(df.lv >= lvmin) & (df.mover == t)]
        rows.append(dict(type=t, ran=len(ran), ran_share=round(len(ran)/len(df), 3),
                         moved=len(moved_all), moved_among_ran=len(moved),
                         hit_rate=round(len(moved)/len(ran), 3) if len(ran) else np.nan))
    return pd.DataFrame(rows)
T1 = type_table(J, U, 1); T2 = type_table(J, U, 2)
T1['hit_ci'] = [boot(lambda d, t=t: ((d.fid.map(lambda f: t in U.get(f, ()))) & (d.lv >= 1) & (d.mover == t)).sum() / max(1, d.fid.map(lambda f: t in U.get(f, ())).sum()), J, 1000) for t in TYPES]
T = T1.merge(T2[['type','moved','moved_among_ran','hit_rate']], on='type', suffixes=('', '_lv2'))
T = T.sort_values('hit_rate', ascending=False); T.to_csv('results/type_effect.csv', index=False)
out['type_effect'] = T.to_dict('records')

# 2. 判定の分布の区間
out['level_ci'] = {k: boot(lambda d, k=k: (d.lv == k).mean(), J) for k in [0, 1, 2]}

# 3. F125 の結論の判定と
F = pd.read_csv('data/raw/f125_articles.csv')[['fid','type','outcome','family']]
M = J.merge(F, on='fid', how='left')
ct = pd.crosstab(M.outcome, M.lv); ct.to_csv('results/by_f125_outcome.csv')
out['by_f125_outcome'] = {o: {int(k): int(v) for k, v in ct.loc[o].items()} for o in ct.index}
m2 = M.dropna(subset=['outcome'])
a = ((m2.outcome == 'Y') & (m2.lv == 2)).sum(); b = ((m2.outcome == 'Y') & (m2.lv < 2)).sum()
c = ((m2.outcome != 'Y') & (m2.lv == 2)).sum(); d = ((m2.outcome != 'Y') & (m2.lv < 2)).sum()
out['fisher_clear_vs_lv2'] = dict(table=[[int(a), int(b)], [int(c), int(d)]], p=round(stats.fisher_exact([[a, b], [c, d]])[1], 3))
ct2 = pd.crosstab(M.type, M.lv); ct2.to_csv('results/by_article_type.csv')
out['by_article_type'] = {o: {int(k): int(v) for k, v in ct2.loc[o].items()} for o in ct2.index}
fam = M.groupby('family').agg(n=('lv', 'size'), lv2=('lv', lambda s: (s == 2).mean()), lv1p=('lv', lambda s: (s >= 1).mean())).round(3)
fam.to_csv('results/by_family.csv'); out['by_family'] = fam.reset_index().to_dict('records')

# 4. 番号帯
H['band'] = pd.cut(H.n, [0, 40, 80, 125], labels=['F01〜40', 'F41〜80', 'F81〜125'])
band = H.groupby('band', observed=True).agg(n=('fid', 'size'), checks=('n_checks', 'median'), types=('n_types', 'median'),
                                            judged=('judged', 'sum'), lv2=('lv', lambda s: (s == 2).sum()), lv1=('lv', lambda s: (s == 1).sum()), lv0=('lv', lambda s: (s == 0).sum()))
band.to_csv('results/by_band.csv'); out['by_band'] = band.reset_index().astype({'band': str}).to_dict('records')
rho = stats.spearmanr(H.n, H.n_checks); out['checks_trend_spearman'] = [round(rho[0], 3), round(rho[1], 4)]
# チェックの数と判定
out['checks_by_level'] = J.groupby('lv').n_checks.median().to_dict()
out['types_by_level'] = J.groupby('lv').n_types.median().to_dict()
kw = stats.kruskal(*[J[J.lv == k].n_checks for k in [0, 1, 2]]); out['kruskal_checks_level_p'] = round(kw.pvalue, 3)

# 5. 自動判定と手作業の一致
lvmap = {'変わらない': 0, '弱まる・動いた': 1, '変わった': 2}
agree = []
for m, r in coded.items():
    a = collections.defaultdict(lambda: np.nan)
    for x in r:
        if x['outcome'] in lvmap: a[x['fid']] = np.nanmax([a[x['fid']], lvmap[x['outcome']]])
    au = J.fid.map(lambda f: a[f])
    ok = ~au.isna()
    ex = (au[ok] == J.lv[ok]).mean()
    po = ex; pe = sum((au[ok] == k).mean() * (J.lv[ok] == k).mean() for k in [0, 1, 2]); kap = (po - pe) / (1 - pe)
    two = ((au[ok] == 2) == (J.lv[ok] == 2)).mean()
    agree.append(dict(mode=m, n=int(ok.sum()), exact=round(ex, 3), kappa=round(kap, 3), lv2_agree=round(two, 3),
                      auto_lv2_share=round((au[ok] == 2).mean(), 3)))
A_ = pd.DataFrame(agree); A_.to_csv('results/auto_vs_hand.csv', index=False); out['auto_vs_hand'] = agree

# 6. 頑健性：数え方を変えても「効き目の上位」は同じか
def top(df, Uset, lvmin):
    t = type_table(df, Uset, lvmin).sort_values(['hit_rate', 'moved'], ascending=False)
    return t
base = top(J, U, 1).set_index('type').hit_rate
rob = []
def add(name, t):
    r = stats.spearmanr(base.loc[t.type], t.hit_rate.values)[0]
    rob.append(dict(check=name, top3='・'.join(t.type.head(3)), spearman=round(r, 2),
                    period=float(t.set_index('type').hit_rate.get('期間・時期')), definition=float(t.set_index('type').hit_rate.get('定義・指標')),
                    variables=float(t.set_index('type').hit_rate.get('変数・調整')), model=float(t.set_index('type').hit_rate.get('モデル・推定法')),
                    sample=float(t.set_index('type').hit_rate.get('対象を絞る・除く')),
                    rank_sample=int(list(t.sort_values('hit_rate', ascending=False).type).index('対象を絞る・除く')) + 1,
                    rank_datasrc=int(list(t.sort_values('hit_rate', ascending=False).type).index('データ源・集計単位')) + 1))
add('基本（1以上・使ったかは全部の種類で判定）', top(J, U, 1))
add('結論が変わった（2）だけ', top(J, U, 2))
add('使ったかを主な種類だけで判定', top(J, Up, 1))
add('まとめ記事 F118〜F125 を除く', top(J[J.n < 118], U, 1))
add('前半 F01〜F62', top(J[J.n <= 62], U, 1))
add('後半 F63〜F125', top(J[J.n > 62], U, 1))
# 「動かしたチェック」を1件あたりで数える（記事ではなく項目で割る）
per_item = []
cnt = collections.Counter(t for x in coded['main'] if x['kind'] in ('row','bul','ext') for t in x['types'] if t in TYPES)
moved = J[J.lv >= 1].mover.value_counts()
pi = pd.DataFrame([dict(type=t, hit_rate=moved.get(t, 0) / cnt[t] * 10 if cnt[t] else np.nan) for t in TYPES]).sort_values('hit_rate', ascending=False)
add('項目10件あたりで数える', pi)
R = pd.DataFrame(rob); R.to_csv('results/robustness.csv', index=False); out['robustness'] = R.to_dict('records')

# 7. 動かしたチェックの種類（全体）
mv = J[J.lv >= 1].mover.value_counts(); mv2 = J[J.lv == 2].mover.value_counts()
out['movers_lv1p'] = mv.to_dict(); out['movers_lv2'] = mv2.to_dict()
H.drop(columns=['band']).to_csv('results/articles.csv', index=False)
json.dump(out, open('results/summary.json', 'w'), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print(json.dumps({k: out[k] for k in ['n_judged','level_counts','level_share','level_ci','checks_median','checks_iqr','types_median','fisher_clear_vs_lv2','checks_trend_spearman','checks_by_level','kruskal_checks_level_p']}, ensure_ascii=False, default=str))
print(T[['type','ran','ran_share','moved','hit_rate','hit_ci','moved_lv2','hit_rate_lv2']].to_string())
print(A_.to_string()); print(R.to_string()); print(band.to_string()); print(fam.to_string()); print(ct.to_string()); print(ct2.to_string())
