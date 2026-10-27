"""03 分析：最小二乗法と分位点回帰（10〜90%点）、ブートストラップの信頼区間、分位点の間の差の検定、頑健性"""
import json, numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.regression.quantile_regression import QuantReg
from common import *

rng = np.random.default_rng(SEED)
R = ROOT / 'results'
B = 500   # ブートストラップの回数


def design(d, cols=XNAMES, pref=False):
    X = d[cols].copy()
    if pref:
        X = X.join(pd.get_dummies(d['pref'], prefix='県', drop_first=True).astype(float))
    return sm.add_constant(X)


def fit_q(y, X, q):
    return QuantReg(y, X).fit(q=q, max_iter=5000).params


def run(d, y='log所得', cols=XNAMES, pref=False, qs=QS, boot=True, tag='base', nboot=None):
    nb = nboot or B
    z = standardize(d, cols)
    X = design(z, cols, pref); Y = z[y]
    ols = sm.OLS(Y, X).fit(cov_type='HC3')
    rows = []
    for c in cols:
        rows.append({'model': 'OLS', 'q': np.nan, 'var': c, 'coef': ols.params[c],
                     'lo': ols.conf_int().loc[c, 0], 'hi': ols.conf_int().loc[c, 1]})
    est = {q: fit_q(Y, X, q) for q in qs}
    bs = {q: [] for q in qs}
    if boot:
        n = len(Y); Xv = X.values; Yv = Y.values
        for b in range(nb):
            i = rng.integers(0, n, n)
            for q in qs:
                try:
                    p = QuantReg(Yv[i], Xv[i]).fit(q=q, max_iter=5000).params
                except Exception:
                    continue
                bs[q].append(p)
    for q in qs:
        for j, c in enumerate(X.columns):
            if c not in cols: continue
            if boot and bs[q]:
                arr = np.array(bs[q])[:, j]
                lo, hi = np.percentile(arr, [2.5, 97.5])
            else:
                lo = hi = np.nan
            rows.append({'model': 'QR', 'q': q, 'var': c, 'coef': est[q][c], 'lo': lo, 'hi': hi})
    res = pd.DataFrame(rows); res['tag'] = tag
    return res, est, bs, list(X.columns), ols


if __name__ == '__main__':
    d = make_xy(2020)
    print('市区町村数', len(d), '所得の分位点', d['所得'].quantile([.1, .25, .5, .75, .9]).round(1).to_dict())
    # 1) 本体：全国、対数所得、県ダミーなし、9分位点（係数の推移の図用）は点推定だけ細かく
    res, est, bs, cols_all, ols = run(d, qs=QS, tag='base')
    res.to_csv(R / 'coef_base.csv', index=False, encoding='utf-8')
    print('OLS R2', round(ols.rsquared, 3))
    # 係数の推移（5%刻み）：点推定
    z = standardize(d); X = design(z); Y = z['log所得']
    grid = []
    for q in QGRID:
        p = fit_q(Y, X, q)
        for c in XNAMES: grid.append({'q': q, 'var': c, 'coef': p[c]})
    pd.DataFrame(grid).to_csv(R / 'coef_grid.csv', index=False, encoding='utf-8')
    # 2) 分位点の間の差（90%点 − 10%点）：ブートストラップ
    j = {c: cols_all.index(c) for c in XNAMES}
    a10 = np.array(bs[0.1]); a90 = np.array(bs[0.9]); m = min(len(a10), len(a90))
    diff = []
    for c in XNAMES:
        dd = a90[:m, j[c]] - a10[:m, j[c]]
        pt = est[0.9][c] - est[0.1][c]
        lo, hi = np.percentile(dd, [2.5, 97.5])
        p = 2 * min((dd <= 0).mean(), (dd >= 0).mean())
        diff.append({'var': c, 'q90_minus_q10': pt, 'lo': lo, 'hi': hi, 'p_boot': p})
    diff = pd.DataFrame(diff); diff.to_csv(R / 'diff_q90_q10.csv', index=False, encoding='utf-8')
    print(diff.round(4).to_string())
    # 3) 予測した分布：1地域ごとに一様乱数 u を引き、5%刻みの分位点の予測を線でつないで Q(u|x) を作る
    preds = np.column_stack([X.values @ fit_q(Y, X, q).values for q in QGRID])
    preds = np.sort(preds, axis=1)   # 分位点の交差を並べ替えで直す
    sim = []
    for r in range(20):
        u = rng.uniform(0.05, 0.95, len(Y))
        sim.append(np.array([np.interp(uu, QGRID, row) for uu, row in zip(u, preds)]))
    sim = np.concatenate(sim)
    # OLS＋正規誤差で作った分布（比較）
    olsr = sm.OLS(Y, X).fit()
    sim_ols = np.concatenate([olsr.fittedvalues.values + rng.normal(0, np.sqrt(olsr.scale), len(Y)) for _ in range(20)])
    qq = pd.DataFrame({'q': np.round(np.arange(0.01, 1.0, 0.01), 2)})
    qq['実際'] = np.quantile(Y, qq.q); qq['分位点回帰'] = np.quantile(sim, qq.q); qq['最小二乗法＋正規誤差'] = np.quantile(sim_ols, qq.q)
    for c in ['実際', '分位点回帰', '最小二乗法＋正規誤差']:
        qq[c + '_万円'] = np.exp(qq[c])   # 対数所得 → 万円
    qq.to_csv(R / 'dist_compare.csv', index=False, encoding='utf-8')
    print(qq[qq.q.isin([0.05, 0.1, 0.5, 0.9, 0.95, 0.99])].round(1).to_string())

    # 4) 頑健性（10・50・90%点、ブートストラップは200回）
    rob = []
    d_nobig = d[[not (is_seirei(c) or is_tokyo23(c)) for c in d.index]]
    for tag, dd, kw in [('23区・政令市を除く', d_nobig, {}),
                        ('県ダミーあり', d, {'pref': True}),
                        ('所得を対数にしない', d, {'y': '所得'}),
                        ('2015年', make_xy(2015), {})]:
        r, *_ = run(dd, qs=[0.1, 0.5, 0.9], tag=tag, nboot=200, **kw)
        r['n'] = len(dd)
        r['unit'] = '万円' if kw.get('y') == '所得' else 'log'
        rob.append(r)
        print(tag, len(dd))
    base3 = res[(res.model == 'OLS') | res.q.isin([0.1, 0.5, 0.9])].copy(); base3['n'] = len(d)
    rob = pd.concat([base3] + rob, ignore_index=True)
    rob.to_csv(R / 'robustness.csv', index=False, encoding='utf-8')
    summ = {'n': len(d), 'ols_r2': ols.rsquared,
            'income_q': d['所得'].quantile([.1, .25, .5, .75, .9]).round(1).to_dict(),
            'income_mean': d['所得'].mean(), 'income_max_name': d['所得'].idxmax()}
    json.dump(summ, open(R / 'summary.json', 'w'), ensure_ascii=False, indent=1, default=str)
