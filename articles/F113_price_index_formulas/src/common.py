import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
P = lambda *a: os.path.join(ROOT, *a)
FRESH = ['魚介類', '野菜・海藻', '果物']

def load_panel():
    d = pd.read_csv(P('data/items_panel.csv'), dtype={'code': str})
    d.loc[d.code == '430', 'name'] = '電気代'; d.loc[d.code == '432', 'name'] = 'プロパンガス'; d.loc[d.code == '433', 'name'] = '灯油'
    return d

def wide(d):
    p = d.pivot(index='code', columns='year', values='price')
    q = d.pivot(index='code', columns='year', values='q')
    return p, q

def bilateral(p0, p1, q0, q1):
    """2時点の指数（比）。共通の品目だけを使う"""
    m = p0.notna() & p1.notna() & q0.notna() & q1.notna()
    p0, p1, q0, q1 = p0[m], p1[m], q0[m], q1[m]
    L = (p1 * q0).sum() / (p0 * q0).sum()
    Pa = (p1 * q1).sum() / (p0 * q1).sum()
    F = np.sqrt(L * Pa)
    s0 = p0 * q0 / (p0 * q0).sum(); s1 = p1 * q1 / (p1 * q1).sum()
    T = np.exp((0.5 * (s0 + s1) * np.log(p1 / p0)).sum())
    r = p1 / p0
    J = np.exp(np.log(r).mean()); C = r.mean(); D = p1.mean() / p0.mean()
    # 幾何ラスパイレス（基準時の支出シェアで幾何平均）
    GL = np.exp((s0 * np.log(r)).sum())
    return dict(L=L, P=Pa, F=F, T=T, GL=GL, J=J, C=C, D=D, n=int(m.sum()))

def chain(p, q, years, kind):
    v = [1.0]
    for a, b in zip(years[:-1], years[1:]):
        v.append(v[-1] * bilateral(p[a], p[b], q[a], q[b])[kind])
    return pd.Series(v, index=years)

def fixed(p, q, base, years, kind):
    return pd.Series([bilateral(p[base], p[y], q[base], q[y])[kind] if y != base else 1.0 for y in years], index=years)

def lowe_rebased(p, q, years, bases=(2002, 2005, 2010, 2015, 2020)):
    """CPI のやり方に近い：5年ごとに基準（ウエイト）を改め、基準年でつなぐラスパイレス"""
    v = pd.Series(index=years, dtype=float); cur = 1.0; b = years[0]
    for y in years:
        if y in bases and y != years[0]:
            cur = cur * bilateral(p[b], p[y], q[b], q[y])['L']; b = y
        v[y] = cur * (bilateral(p[b], p[y], q[b], q[y])['L'] if y != b else 1.0)
    return v
