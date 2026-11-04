# 03 分析：白書・年ごとの読みやすさの指標を計算し、時間の傾きを推定する。
# 入力 data/raw/sentences.parquet（本文の文。GitHub には置かない）
# 出力 data/metrics_by_year.csv（白書×年の指標）、results/*.csv
import re, sys, json
import numpy as np, pandas as pd
import fugashi
import statsmodels.api as sm

RAW = sys.argv[1] if len(sys.argv) > 1 else 'data/raw'
OUT = sys.argv[2] if len(sys.argv) > 2 else '.'
rng = np.random.default_rng(176)
df = pd.read_parquet(f'{RAW}/sentences.parquet')
tagger = fugashi.Tagger()

KAN = re.compile(r'[一-鿿々〆ヶ]')
KANNUM = re.compile(r'[〇一二三四五六七八九十百千万億兆]')
KATA = re.compile(r'[ァ-ヺー]')
PUNCT = re.compile(r'[、。，．・「」『』（）()〔〕［］【】〈〉《》―…：；！？!?\-－—〜～/／"\'“”‘’]')
DIGLAT = re.compile(r'[0-9０-９A-Za-zＡ-Ｚａ-ｚ.,%％]')

def charstats(s):
    s = re.sub(r'\s', '', s)
    n = len(s); k = len(KAN.findall(s)); kn = len(KANNUM.findall(s)); ka = len(KATA.findall(s))
    p = len(PUNCT.findall(s)); dl = len(DIGLAT.findall(s))
    base = max(1, n - p - dl)
    return n, k, kn, ka, base, s.count('、') + s.count('，') + s.count(',')

def morph(s):
    toks = [w for w in tagger(s) if w.feature.pos1 not in ('補助記号', '空白')]
    g = [w.feature.goshu for w in toks]
    return dict(words=len(toks), kango=sum(x == '漢' for x in g), wago=sum(x == '和' for x in g),
                gairai=sum(x == '外' for x in g), verb=sum(w.feature.pos1 == '動詞' for w in toks),
                joshi=sum(w.feature.pos1 == '助詞' for w in toks))

def jread(m):
    W = max(1, m['words'])
    wl = m['words'] / m['n']
    return (wl * -0.056 + 100 * m['kango'] / W * -0.126 + 100 * m['wago'] / W * -0.042
            + 100 * m['verb'] / W * -0.145 + 100 * m['joshi'] / W * -0.044 + 11.724)

def agg(g, nmorph):
    cs = np.array([charstats(s) for s in g['sent']])
    n, k, kn, ka, base, comma = cs.T
    r = dict(sents=len(g), chars=int(n.sum()), len_mean=n.mean(), len_median=np.median(n),
             long100=(n >= 100).mean(), comma_per_sent=comma.mean(),
             kanji_all=k.sum() / n.sum(), kanji_text=k.sum() / base.sum(),
             kanji_nonum=(k - kn).sum() / (base - kn).sum(), kata_text=ka.sum() / base.sum())
    idx = rng.choice(len(g), size=min(nmorph, len(g)), replace=False)
    M = dict(n=0, words=0, kango=0, wago=0, gairai=0, verb=0, joshi=0)
    for s in g['sent'].values[idx]:
        m = morph(s); M['n'] += 1
        for a in m: M[a] += m[a]
    W = max(1, M['words'])
    r.update(words_per_sent=M['words'] / M['n'], kango=M['kango'] / W, gairai=M['gairai'] / W,
             wago=M['wago'] / W, jread=jread(M))
    return r

def table(d, nmorph=400, by=('wp', 'year')):
    out = []
    for key, g in d.groupby(list(by)):
        if len(g) < 30: continue
        r = agg(g, nmorph); r.update(dict(zip(by, key))); out.append(r)
    return pd.DataFrame(out)

def slope(t, col, y0=None, y1=None):
    t = t.dropna(subset=[col])
    if y0: t = t[t.year >= y0]
    if y1: t = t[t.year <= y1]
    X = sm.add_constant((t.year - 2000) / 10)
    f = sm.OLS(t[col], X).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
    lo, hi = f.conf_int().iloc[1]
    return dict(n=len(t), y0=int(t.year.min()), y1=int(t.year.max()), per10y=f.params.iloc[1], lo=lo, hi=hi, p=f.pvalues.iloc[1])

MET = ['len_mean', 'len_median', 'long100', 'words_per_sent', 'comma_per_sent', 'kanji_all', 'kanji_text', 'kanji_nonum', 'kata_text', 'kango', 'gairai', 'jread']

if __name__ == '__main__':
    base = table(df)
    base.to_csv(f'{OUT}/data/metrics_by_year.csv', index=False, float_format='%.5f')
    res = []
    PER = {'all': (None, None), '2004-2025': (2004, 2025), '1947-1969': (1947, 1969), '1970-1999': (1970, 1999), '2000-2025': (2000, 2025)}
    for wp in base.wp.unique():
        t = base[base.wp == wp]
        for pn, (a, b) in PER.items():
            if a and (t.year.min() > a + 5 or t.year.max() < b - 5): continue
            for c in MET: res.append(dict(wp=wp, metric=c, period=pn, **slope(t, c, a, b)))
    pd.DataFrame(res).to_csv(f'{OUT}/results/trend_slopes.csv', index=False, float_format='%.5f')
    base.assign(dec=base.year // 10 * 10).groupby(['wp', 'dec'])[MET + ['sents']].mean().to_csv(f'{OUT}/results/decade_means.csv', float_format='%.4f')
    # 頑健性0：1文の長さ（2004〜2025年、3つの白書）を、文の選び方を変えて測り直す
    HASNUM = df.sent.str.contains(r'[0-9０-９〇一二三四五六七八九十百千万億兆]')
    HASQ = df.sent.str.contains('「')
    df['n'] = df.sent.str.replace(r'\s', '', regex=True).str.len()
    conds = {'基本（平均）': df.index == df.index, '中央値': None, '数字を含まない文だけ': ~HASNUM, '「」を含まない文だけ': ~HASQ,
             'ページの前1/3': df.pos <= 1 / 3, 'ページの中1/3': (df.pos > 1 / 3) & (df.pos <= 2 / 3), 'ページの後1/3': df.pos > 2 / 3}
    NAME = {'keizai': '経済', 'joho': '情報通信', 'kokudo': '国土交通'}
    rs = []
    for wp in ['keizai', 'joho', 'kokudo']:
        for cn, mask in conds.items():
            d = df[(df.wp == wp) & (df.year >= 2004)] if mask is None else df[(df.wp == wp) & (df.year >= 2004) & mask]
            if d.empty: continue
            g = d.groupby('year').n.agg(['mean', 'median', 'size']).reset_index()
            g = g[g['size'] >= 30]
            col = 'median' if cn == '中央値' else 'mean'
            s = slope(g.rename(columns={col: 'v'}), 'v')
            rs.append(dict(label=f'{NAME[wp]}：{cn}', wp=wp, cond=cn, **s))
    pd.DataFrame(rs).to_csv(f'{OUT}/results/robust_summary.csv', index=False, float_format='%.4f')
    # 頑健性1：章の選び方（ページの順番で前・中・後の3つに分ける）
    df['third'] = pd.cut(df.pos, [-0.01, 1 / 3, 2 / 3, 1.01], labels=['前', '中', '後'])
    rr = []
    for th, d in df.groupby('third', observed=True):
        t = table(d, nmorph=200)
        for wp in t.wp.unique():
            for c in ['len_mean', 'kanji_nonum', 'kango', 'jread']:
                rr.append(dict(part=th, wp=wp, metric=c, **slope(t[t.wp == wp], c)))
    pd.DataFrame(rr).to_csv(f'{OUT}/results/robust_chapter.csv', index=False, float_format='%.5f')
    # 頑健性2：形態素解析に使う文の数（200・400・800）と乱数の種
    rr = []
    for nm in (200, 800):
        t = table(df, nmorph=nm)
        for wp in t.wp.unique():
            for c in ['words_per_sent', 'kango', 'jread']:
                rr.append(dict(nmorph=nm, wp=wp, metric=c, **slope(t[t.wp == wp], c)))
    pd.DataFrame(rr).to_csv(f'{OUT}/results/robust_sample.csv', index=False, float_format='%.5f')
    print(base.groupby('wp').size())
