"""σ収束・β収束・動学パネル（OLS／固定効果／Arellano–Bond の差分GMM／system GMM）"""
import numpy as np, pandas as pd, pathlib, json, warnings, io, contextlib
import statsmodels.formula.api as smf
warnings.filterwarnings('ignore')
H = pathlib.Path(__file__).resolve().parents[1]; R = H/'results'
p = pd.read_csv(H/'data/panel_rel_income.csv')
OKI = 47; TKY = 13
out = {}

# ---- σ収束：相対所得（対数）の県の間の標準偏差 ----
def sd_by_year(df, w=False):
    def f(g):
        if w:
            ww = g['pop']; m = np.average(g['r'], weights=ww)
            return np.sqrt(np.average((g['r']-m)**2, weights=ww))
        return g['r'].std(ddof=0)
    return df.groupby('year').apply(f)
sig = pd.DataFrame({
    'sd46_沖縄除く': sd_by_year(p[p.code != OKI]),
    'sd47': sd_by_year(p[p.year >= 1972]),
    'sd46_東京除く': sd_by_year(p[(p.code != TKY) & (p.code != OKI)]),
    'sd47_人口重み': sd_by_year(p[(p.year >= 1975)], w=True),
    'sd46_段差を消さない': sd_by_year(p[p.code != OKI].assign(r=lambda x: x.r_naive))})
sig.to_csv(R/'sigma_by_year.csv')
s = sig['sd46_沖縄除く']
out['sigma'] = {str(y): round(float(s[y]), 4) for y in [1955, 1961, 1970, 1975, 1980, 1990, 1991, 2000, 2007, 2010, 2015, 2019, 2020, 2022]}
out['sigma_min_year'] = int(s.idxmin()); out['sigma_min'] = round(float(s.min()), 4)
out['sigma_max_year'] = int(s.idxmax()); out['sigma_max'] = round(float(s.max()), 4)

# ---- β収束（横断面）：期間ごとに、初めの相対所得で年率の伸びを回帰 ----
periods = [(1955, 1975), (1975, 1990), (1990, 2007), (2007, 2022), (1955, 2022), (1975, 2022)]
bet = []
for a, b in periods:
    for lab, cond in [('全県', p.code > 0), ('東京除く', p.code != TKY)]:
        q = p[cond]
        x = q[q.year == a].set_index('code')['r']; yb = q[q.year == b].set_index('code')['r']
        dd = pd.concat([x.rename('r0'), yb.rename('r1')], axis=1).dropna()
        dd['g'] = (dd.r1 - dd.r0)/(b - a)
        m = smf.ols('g ~ r0', dd).fit(cov_type='HC1')
        bT = m.params['r0']*(b-a)              # 期間全体での縮み（r1-r0 = bT * r0）
        lam = -np.log(1 + bT)/(b-a) if 1 + bT > 0 else np.nan
        bet.append(dict(期間=f'{a}-{b}', 対象=lab, 県=len(dd), beta_年率=m.params['r0'], 下=m.conf_int().loc['r0', 0], 上=m.conf_int().loc['r0', 1],
                        R2=m.rsquared, 収束速度λ=lam, 半減期_年=np.log(2)/lam if lam and lam > 0 else np.nan))
for a, b in [(1955, 1975), (1975, 1990), (1990, 2007), (2007, 2022), (1975, 2022)]:
    x = p[p.year == a].set_index('code')['r_naive']; yb = p[p.year == b].set_index('code')['r_naive']
    dd = pd.concat([x.rename('r0'), yb.rename('r1')], axis=1).dropna(); dd['g'] = (dd.r1-dd.r0)/(b-a)
    m = smf.ols('g ~ r0', dd).fit(cov_type='HC1'); bT = m.params['r0']*(b-a); lam = -np.log(1+bT)/(b-a) if 1+bT > 0 else np.nan
    bet.append(dict(期間=f'{a}-{b}', 対象='全県・段差を消さない', 県=len(dd), beta_年率=m.params['r0'], 下=m.conf_int().loc['r0', 0], 上=m.conf_int().loc['r0', 1],
                    R2=m.rsquared, 収束速度λ=lam, 半減期_年=np.log(2)/lam if lam and lam > 0 else np.nan))
bet = pd.DataFrame(bet); bet.to_csv(R/'beta_cross_section.csv', index=False)

# ---- 動学パネル：5年ごと r_it = ρ r_i,t-5 + μ_i + τ_t ----
def panel(step=5, start=1955, end=2020, drop=(), okinawa_from=1975):
    yrs = list(range(start, end+1, step))
    q = p[p.year.isin(yrs) & ~p.code.isin(drop)].copy()
    q = q[~((q.code == OKI) & (q.year < okinawa_from))]
    q = q.sort_values(['code', 'year'])
    q['t'] = q.groupby('code').cumcount()
    q['L1'] = q.groupby('code')['r'].shift(1)
    return q
def ols_fe(q):
    d = q.dropna(subset=['L1'])
    o = smf.ols('r ~ L1 + C(year)', d).fit(cov_type='cluster', cov_kwds={'groups': d.code})
    f = smf.ols('r ~ L1 + C(year) + C(code)', d).fit(cov_type='cluster', cov_kwds={'groups': d.code})
    return (o.params['L1'], o.bse['L1']), (f.params['L1'], f.bse['L1'])
import sys; sys.path.insert(0, str(H/'src'))
from gmm_ab import estimate
def gmm(q, system, lags):
    g = estimate(q[['code', 't', 'r']], lags=lags, system=system)
    return dict(rho=g['rho'], se=g['se_1step'], n_inst=g['n_inst'], hansen_p=g['hansen_p'], ar2_p=g['ar2_p'], rho1=g['rho_1step'])
def run(label, q, step, lags=(2, 4)):
    o, f = ols_fe(q)
    res = dict(設定=label, 間隔=step, 県=q.code.nunique(), 観測=int(q.L1.notna().sum()),
               OLS=o[0], OLS_se=o[1], FE=f[0], FE_se=f[1])
    for name, sysflag in [('差分GMM', False), ('systemGMM', True)]:
        try:
            g = gmm(q, sysflag, lags)
            res[name] = g['rho']; res[name+'_1段階'] = g['rho1']; res[name+'_se'] = g['se']; res[name+'_操作変数'] = g['n_inst']
            res[name+'_Hansen_p'] = g['hansen_p']; res[name+'_AR2_p'] = g['ar2_p']
        except Exception as e:
            res[name] = np.nan; res[name+'_err'] = str(e)[:80]
    for name in ['OLS', 'FE', '差分GMM', 'systemGMM']:
        rho = res.get(name, np.nan)
        lam = -np.log(rho)/step if rho and 0 < rho < 1 else np.nan
        res[name+'_半減期'] = np.log(2)/lam if lam == lam else np.nan
    return res
rows = []
rows.append(run('基本（1955〜2020、5年ごと）', panel(), 5))
rows.append(run('東京を除く', panel(drop=(TKY,)), 5))
rows.append(run('1975〜2020（47県）', panel(start=1975, okinawa_from=1975), 5))
rows.append(run('1990〜2020', panel(start=1990, okinawa_from=1975), 5))
rows.append(run('1955〜1990', panel(start=1955, end=1990), 5))
rows.append(run('3年ごと（1955〜2020）', panel(step=3, start=1956, end=2020), 3))
rows.append(run('操作変数のラグ 2:3', panel(), 5, lags=(2, 3)))
rows.append(run('操作変数のラグ 2:6', panel(), 5, lags=(2, 6)))
rows.append(run('操作変数のラグ 3:5（AR(2)対策）', panel(), 5, lags=(3, 5)))
p_save = p; p = p.assign(r=p.r_naive)
rows.append(run('基準改定の段差を消さない', panel(), 5))
p = p_save
pt = pd.DataFrame(rows); pt.to_csv(R/'dynamic_panel.csv', index=False)

# ---- 10年ごとの移動β（どこで収束が止まったか） ----
roll = []
for a in range(1955, 2013):
    b = a + 10
    x = p[p.year == a].set_index('code')['r']; yb = p[p.year == b].set_index('code')['r']
    dd = pd.concat([x.rename('r0'), yb.rename('r1')], axis=1).dropna()
    m = smf.ols('I((r1-r0)/10) ~ r0', dd).fit(cov_type='HC1')
    roll.append(dict(始まり=a, 終わり=b, beta=m.params['r0'], 下=m.conf_int().iloc[1, 0], 上=m.conf_int().iloc[1, 1]))
pd.DataFrame(roll).to_csv(R/'rolling_beta_10y.csv', index=False)
# 順位の入れ替わり
piv = p.pivot(index='code', columns='year', values='r')
rk = {}
for a, b in [(1955, 1975), (1975, 1990), (1990, 2007), (2007, 2022), (1975, 2022)]:
    c = piv[[a, b]].dropna(); rk[f'{a}-{b}'] = round(float(c.rank().corr(method='spearman').iloc[0, 1]), 3)
out['rank_corr'] = rk
top = piv[2022].sort_values(ascending=False)
out['top5_2022'] = [(int(c), round(float(v), 3)) for c, v in top.head(5).items()]
out['tokyo_r'] = {str(y): round(float(piv.loc[TKY, y]), 3) for y in [1955, 1975, 1990, 2000, 2007, 2022]}
pn = p.pivot(index='code', columns='year', values='r_naive')
out['tokyo_r_naive'] = {str(y): round(float(pn.loc[TKY, y]), 3) for y in [1955, 1975, 1990, 2000, 2007, 2022]}
ex = piv.drop(index=[TKY, OKI])
out['p10_p90_ex'] = {str(y): [round(float(ex[y].quantile(.1)), 3), round(float(ex[y].quantile(.9)), 3)] for y in [1955, 1975, 2000, 2022]}
json.dump(out, open(R/'summary.json', 'w'), ensure_ascii=False, indent=1)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
print(json.dumps(out, ensure_ascii=False))
print(bet.round(4))
print(pt.round(3).T)
