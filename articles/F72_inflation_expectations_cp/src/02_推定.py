"""Carlson–Parkin 法で「1年後の物価の見通し」の回答割合から予想インフレ率を推定し、実際の物価と比べる。
出力: results/ 以下の csv と summary.json
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats, optimize
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
R = ROOT/'results'; R.mkdir(exist_ok=True)
nat = pd.read_csv(ROOT/'data/expect_national.csv')
grp = pd.read_csv(ROOT/'data/expect_groups.csv')
cpi = pd.read_csv(ROOT/'data/cpi_monthly.csv').set_index('ym')
C7 = ['d5', 'd2_5', 'd0_2', 'zero', 'u0_2', 'u2_5', 'u5']

def cuts7(delta):
    return np.array([-5, -2, -delta, delta, 2, 5])

def probs(mu, sig, cuts, dist):
    F = dist.cdf((cuts - mu) / sig)
    F = np.concatenate([[0], F, [1]])
    return np.clip(np.diff(F), 1e-12, 1)

def fit_month(p, cuts, dist, x0=(1.0, 2.0)):
    p = np.asarray(p, float); p = p / p.sum()
    def nll(th):
        return -(p * np.log(probs(th[0], np.exp(th[1]), cuts, dist))).sum()
    r = optimize.minimize(nll, [x0[0], np.log(x0[1])], method='Nelder-Mead',
                          options={'xatol': 1e-6, 'fatol': 1e-10, 'maxiter': 4000})
    return r.x[0], float(np.exp(r.x[1])), r.fun

def fit_series(P, delta, dist=stats.norm, cutsfun=cuts7):
    out = []; x0 = (1.0, 2.0)
    for p in P:
        mu, sig, f = fit_month(p, cutsfun(delta), dist, x0)
        out.append((mu, sig, f)); x0 = (mu, sig)
    return np.array(out)

d2 = nat[nat.hh == '二人以上'].reset_index(drop=True)
P = d2[C7].values

# 1) 共通の δ（「0%程度」と答える幅）をプロファイル尤度で推定
grid = np.round(np.arange(0.1, 2.01, 0.05), 2)
prof = []
for dl in grid:
    res = fit_series(P, dl)
    prof.append(res[:, 2].sum())
prof = np.array(prof)
dhat = float(grid[prof.argmin()])
pd.DataFrame({'delta': grid, 'neg_loglik_sum': prof}).to_csv(R/'r1_delta_profile.csv', index=False)
# 期間別の δ
def best_delta(Psub):
    pr = [fit_series(Psub, dl)[:, 2].sum() for dl in grid]
    return float(grid[int(np.argmin(pr))])
pre = (d2.ym < '2013-04').values
dpre, dpost = best_delta(P[pre]), best_delta(P[~pre])

base = fit_series(P, dhat)
d2['mu'] = base[:, 0]; d2['sigma'] = base[:, 1]
# 中点の単純平均（比較）
mid = np.array([-6, -3.5, -1, 0, 1, 3.5, 6])
d2['mid'] = (P / P.sum(1, keepdims=True)) @ mid
d2['up5'] = d2.u5 / d2[C7].sum(1) * 100
# 頑健性
rob = {}
for dl in [0.25, 0.5, 1.0]:
    rob[f'delta{dl}'] = fit_series(P, dl)[:, 0]
rob['t5'] = fit_series(P, dhat, dist=stats.t(5))[:, 0]
rob['mid_open8'] = (P / P.sum(1, keepdims=True)) @ np.array([-8, -3.5, -1, 0, 1, 3.5, 8])
rob['logistic'] = fit_series(P, dhat, dist=stats.logistic)[:, 0]
# 「分からない」を下に寄せる（全員0%と見なす）
Pdk = d2[C7].values.copy(); Pdk[:, 3] += d2.dk.values
rob['dk_as_zero'] = fit_series(Pdk, dhat)[:, 0]
for k, v in rob.items(): d2['rob_'+k] = v

# 2) 実際の物価と比べる
for s in ['all', 'core', 'corecore', 'food']:
    d2[s+'_now'] = d2.ym.map(cpi[s+'_yoy'])
    fut = cpi[s+'_yoy'].shift(-12)
    d2[s+'_t12'] = d2.ym.map(fut)
d2.to_csv(R/'r2_cp_series.csv', index=False)

def period(ym):
    if ym < '2013-04': return '2004/4〜2013/3'
    if ym < '2022-01': return '2013/4〜2021/12'
    return '2022/1〜'
d2['period'] = d2.ym.map(period)
v = d2.dropna(subset=['all_t12'])
tab = []
for per, g in list(v.groupby('period')) + [('全期間', v)]:
    gg = d2[d2.period == per] if per != '全期間' else d2
    tab.append({'period': per, 'n_months': len(g),
                'mu_mean': g.mu.mean(), 'sigma_mean': g.sigma.mean(),
                'cpi_now_mean': g.all_now.mean(), 'cpi_t12_mean': g.all_t12.mean(),
                'bias_t12': (g.mu - g.all_t12).mean(), 'mae_t12': (g.mu - g.all_t12).abs().mean(),
                'corr_mu_t12': g.mu.corr(g.all_t12), 'corr_mu_now': g.mu.corr(g.all_now),
                'mu_mean_all_months': gg.mu.mean()})
tab = pd.DataFrame(tab); tab.to_csv(R/'r3_compare_period.csv', index=False)

# ずらした相関
lags = range(-12, 13)
cc = []
for L in lags:
    x = d2.ym.map(cpi['all_yoy'].shift(-L))
    m = ~x.isna()
    cc.append({'lag_months': L, 'corr': np.corrcoef(d2.mu[m], x[m])[0, 1], 'n': int(m.sum())})
cc = pd.DataFrame(cc); cc.to_csv(R/'r4_leadlag.csv', index=False)

# 後ろ向き・前向き：mu_t = a + b*今の物価 + c*1年後の物価
def reg(df, ycol='mu'):
    X = sm.add_constant(df[['all_now', 'all_t12']])
    m = sm.OLS(df[ycol], X).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    return {'const': m.params['const'], 'b_now': m.params['all_now'], 'b_now_se': m.bse['all_now'],
            'c_t12': m.params['all_t12'], 'c_t12_se': m.bse['all_t12'], 'r2': m.rsquared, 'n': int(m.nobs)}
rg = []
for per, g in list(v.groupby('period')) + [('全期間', v)]:
    r = reg(g); r['period'] = per; rg.append(r)
# 消費税の月を除く（実績が税率引上げの影響を受ける月）
tax = v[~v.ym.between('2013-04', '2015-03') & ~v.ym.between('2018-10', '2020-09')]
r = reg(tax); r['period'] = '全期間（消費税の影響月を除く）'; rg.append(r)
rg = pd.DataFrame(rg); rg.to_csv(R/'r5_backward_forward.csv', index=False)

# 3) 属性別（年齢・年収）。9区分→7区分にまとめて同じ δ で推定
g = grp.copy()
g['d5'] = g.d10.fillna(0) + g.d5_10.fillna(0)
g['u5'] = g.u5_10.fillna(0) + g.u10.fillna(0)
G7 = ['d5', 'd2_5', 'd0_2', 'zero', 'u0_2', 'u2_5', 'u5']
g = g[g[G7].sum(1) > 0].copy()
est = []
for (t, sn, gr), sub in g.groupby(['type', 'sheet', 'group'], sort=False):
    sub = sub.sort_values('ym')
    rr = fit_series(sub[G7].values, dhat)
    # 9区分のまま（±10% の切れ目を足す）
    if sn.startswith('年齢階級別（平成25') or t == '年収':
        C9 = ['d10', 'd5_10', 'd2_5', 'd0_2', 'zero', 'u0_2', 'u2_5', 'u5_10', 'u10']
        P9 = sub[C9].fillna(0).values
        r9 = fit_series(P9, dhat, cutsfun=lambda dl: np.array([-10, -5, -2, -dl, dl, 2, 5, 10]))[:, 0]
    else:
        r9 = np.full(len(sub), np.nan)
    est.append(pd.DataFrame({'type': t, 'sheet': sn, 'group': gr, 'ym': sub.ym.values,
                             'n': sub.n.values, 'mu': rr[:, 0], 'sigma': rr[:, 1], 'mu9': r9}))
est = pd.concat(est); est.to_csv(R/'r6_groups_series.csv', index=False)
est['period'] = est.ym.map(period)
gsum = est.groupby(['type', 'sheet', 'group', 'period'], sort=False).agg(mu=('mu', 'mean'), sigma=('sigma', 'mean'), mu9=('mu9', 'mean'), months=('mu', 'size'), n_mean=('n', 'mean')).reset_index()
gsum.to_csv(R/'r7_groups_summary.csv', index=False)

# 4) 頑健性まとめ（期間平均）
rows = []
for k in ['mu', 'mid'] + ['rob_'+k for k in rob]:
    row = {'setting': k}
    for per in ['2004/4〜2013/3', '2013/4〜2021/12', '2022/1〜']:
        row[per] = d2.loc[d2.period == per, k].mean()
    row['corr_with_base'] = d2[k].corr(d2.mu)
    row['latest_2026_09'] = d2[k].iloc[-1]
    vv = d2.dropna(subset=['all_t12'])
    row['corr_with_cpi_t12'] = vv[k].corr(vv.all_t12)
    rows.append(row)
robt = pd.DataFrame(rows); robt.to_csv(R/'r8_robustness.csv', index=False)

# 要点
last = d2.iloc[-1]
summ = {
 'delta_hat': dhat, 'delta_pre2013': dpre, 'delta_post2013': dpost,
 'n_months': len(d2), 'first': d2.ym.iloc[0], 'last': d2.ym.iloc[-1],
 'mu_last': last.mu, 'sigma_last': last.sigma, 'up5_last': last.up5,
 'mu_2013_03': float(d2.loc[d2.ym == '2013-03', 'mu'].iloc[0]),
 'mu_2013_04': float(d2.loc[d2.ym == '2013-04', 'mu'].iloc[0]),
 'mu_min': [d2.mu.min(), d2.loc[d2.mu.idxmin(), 'ym']],
 'mu_max': [d2.mu.max(), d2.loc[d2.mu.idxmax(), 'ym']],
 'peak_corr_lag': cc.loc[cc['corr'].idxmax()].to_dict(),
 'share_mu_above_2': float((d2.mu > 2).mean()),
 'months_mu_above_2_by_period': d2.groupby('period').apply(lambda g: float((g.mu > 2).mean())).to_dict(),
 'corr_sigma_mu': d2.sigma.corr(d2.mu),
 'corr_mu_mid': d2.mu.corr(d2.mid),
}
json.dump(summ, open(R/'summary.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(summ, ensure_ascii=False, indent=1, default=float))
print(tab.round(2).to_string()); print(rg.round(3).to_string()); print(robt.round(2).to_string())
print(gsum[gsum.sheet.str.contains('平成25')].round(2).to_string())
print(gsum[gsum.type=='年収'].round(2).to_string())
