"""03 対照の置き方6通りで、2019年10月の消費税率引き上げの転嫁を測り、時点のプラセボで偶然の幅を測る。
入力：data/item_class.csv, data/item_logidx.csv.gz
出力：results/*.csv, results/main.json
"""
import os, json, numpy as np, pandas as pd
from scipy.optimize import nnls
B = os.path.join(os.path.dirname(__file__), '..')
D, R = os.path.join(B, 'data'), os.path.join(B, 'results')
os.makedirs(R, exist_ok=True)
it = pd.read_csv(os.path.join(D, 'item_class.csv'), dtype={'code': str, 'cls': str, 'big': str})
it = it[it.complete].set_index('code')
L = pd.read_csv(os.path.join(D, 'item_logidx.csv.gz'), dtype={'ym': str}).set_index('ym')
I = np.exp(L / 100)
YM = list(L.index); pos = {y: k for k, y in enumerate(YM)}
MONTH = np.array([int(y[4:]) for y in YM])
TARGET = 1.0 * 100 * np.log(110 / 108)   # 全部転嫁の目安（100×ln）
FULL_PCT = (110 / 108 - 1) * 100

def group(codes, eq=False):
    if eq:
        return 100 * np.log(I[codes].mean(axis=1))
    w = it.loc[codes, 'weight']
    return 100 * np.log((I[codes] * w.values).sum(axis=1) / w.sum())

def sets(excl_energy_fresh=False, c8_nofresh=False):
    T = it.index[(it.tax == '標準')]
    if excl_energy_fresh:
        T = it.index[(it.tax == '標準') & ~it.energy & ~it.fresh]
    C8 = it.index[(it.tax == '軽減')]
    if c8_nofresh:
        C8 = it.index[(it.tax == '軽減') & ~it.fresh]
    CN = it.index[(it.tax == '非課税')]
    return list(T), list(C8), list(CN)

def m1(y, k, h):   # 前後比較
    return y[k:k + h].mean() - y[k - 3:k].mean()

def m2(y, k, h):   # 前年同月比の差
    yy = y[12:] - y[:-12]; kk = k - 12
    return yy[kk:kk + h].mean() - yy[kk - 3:kk].mean()

def m3(y, k, h, P):  # 中断時系列：傾き＋月の効果（13個の係数なので前の期間が14か月未満なら計算しない）
    if P < 14:
        return np.nan
    idx = np.arange(k - P, k)
    def Xm(ix):
        X = np.column_stack([np.ones(len(ix)), ix] + [(MONTH[ix] == m).astype(float) for m in range(2, 13)])
        return X
    beta, *_ = np.linalg.lstsq(Xm(idx), y[idx], rcond=None)
    post = np.arange(k, k + h)
    return (y[post] - Xm(post) @ beta).mean()

def m6(y, D_, k, h, P):  # 合成対照：非負・合計1、前の P か月の平均を引いて合わせる
    pre = slice(k - P, k); post = slice(k, k + h)
    yt = y[pre] - y[pre].mean(); Xd = D_[pre] - D_[pre].mean(axis=0)
    lam = 1e3
    A = np.vstack([Xd, lam * np.ones(Xd.shape[1])]); b = np.concatenate([yt, [lam]])
    w, _ = nnls(A, b)
    fit = (y[post] - y[pre].mean()) - (D_[post] - D_[pre].mean(axis=0)) @ w
    return fit.mean(), w

METHODS = ['M1 前後比較', 'M2 前年同月比の差', 'M3 中断時系列', 'M4 軽減税率の品目と差の差', 'M5 非課税の品目と差の差', 'M6 合成対照']

def estimate(yT, yC8, yCN, Dn, k, h, P, keepw=False):
    e6, w = m6(yT, Dn, k, h, P)
    out = [m1(yT, k, h), m2(yT, k, h), m3(yT, k, h, P), m1(yT - yC8, k, h), m1(yT - yCN, k, h), e6]
    return (out, w) if keepw else out

def run(variant='main', P=24, hs=(1, 3, 6, 12), eq=False, efr=False, c8nf=False):
    T, C8, CN = sets(efr, c8nf)
    yT, yC8, yCN = group(T, eq).values, group(C8, eq).values, group(CN, eq).values
    donors = list(it.index[it.tax.isin(['軽減', '非課税'])])
    if c8nf:
        donors = [c for c in donors if not it.loc[c, 'fresh']]
    Dn = L[donors].values
    rows = []
    k0 = pos['201910']
    for h in hs:
        est, w = estimate(yT, yC8, yCN, Dn, k0, h, P, keepw=True)
        for m, e in zip(METHODS, est):
            rows.append(dict(variant=variant, P=P, h=h, kind='本番', t0='201910', method=m, est=e))
        if h == 3 and variant == 'main':
            ww = pd.Series(w, index=donors); ww = ww[ww > 1e-4].sort_values(ascending=False)
            pd.DataFrame({'code': ww.index, 'name': it.loc[ww.index, 'name'].values, 'tax': it.loc[ww.index, 'tax'].values, 'w': ww.values}).to_csv(os.path.join(R, 'C_synth_weights_201910.csv'), index=False)
        for per, (a, b) in {'落ち着いた期間': ('201701', None), '荒れた期間': ('202201', None)}.items():
            ka = max(pos[a], P, 15)
            kb = (pos['201910'] - h) if per == '落ち着いた期間' else (len(YM) - h)
            for k in range(ka, kb + 1):
                for m, e in zip(METHODS, estimate(yT, yC8, yCN, Dn, k, h, P)):
                    rows.append(dict(variant=variant, P=P, h=h, kind=per, t0=YM[k], method=m, est=e))
    return pd.DataFrame(rows)

def band(df):
    g = df[df.kind != '本番'].groupby(['variant', 'P', 'h', 'kind', 'method']).est
    s = g.agg(n='size', mean='mean', p5=lambda x: np.percentile(x, 5), p95=lambda x: np.percentile(x, 95),
              sd='std', mae=lambda x: np.abs(x).mean()).reset_index()
    s['half90'] = (s.p95 - s.p5) / 2
    return s

if __name__ == '__main__':
    allr = [run('main', 24)]
    allr += [run('P12', 12, hs=(3,)), run('P36', 36, hs=(3,))]
    allr += [run('エネルギー・生鮮を除くT', 24, hs=(3,), efr=True), run('軽減の対照から生鮮を除く', 24, hs=(3,), c8nf=True),
             run('単純平均', 24, hs=(3,), eq=True)]
    df = pd.concat(allr, ignore_index=True)
    df.to_csv(os.path.join(R, 'A_all_estimates.csv.gz'), index=False, compression='gzip')
    bd = band(df); bd.to_csv(os.path.join(R, 'B_bands.csv'), index=False)
    real = df[df.kind == '本番'].merge(bd[bd.kind == '落ち着いた期間'][['variant', 'P', 'h', 'method', 'p5', 'p95', 'half90', 'mean']], on=['variant', 'P', 'h', 'method'], how='left')
    real['outside'] = (real.est < real.p5) | (real.est > real.p95)
    real.to_csv(os.path.join(R, 'B_real_vs_band.csv'), index=False)
    pd.set_option('display.width', 200)
    print(real[real.variant == 'main'].round(3).to_string())
    print(bd[(bd.variant == 'main')].round(3).to_string())
