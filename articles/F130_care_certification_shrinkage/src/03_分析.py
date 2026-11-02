# 03 分析：年齢調整（間接法・直接法）と、保険者の階層ベイズ縮小
import json, warnings
import numpy as np, pandas as pd
import pymc as pm
warnings.filterwarnings('ignore')
SEED = 130
rng = np.random.default_rng(SEED)
df0 = pd.read_csv('data/insurer_panel.csv')
LV_ALL = ['要支援1', '要支援2', '要介護1', '要介護2', '要介護3', '要介護4', '要介護5']
SETS = {'all': LV_ALL, 'care2p': ['要介護2', '要介護3', '要介護4', '要介護5'], 'support': ['要支援1', '要支援2']}

def prep(df, levels='all', bands=3):
    df = df.copy()
    lv = SETS[levels]
    for b in ['6574', '7584', '85p']:
        df[f'O_{b}'] = df[[f'c{b}_{l}' for l in lv]].sum(axis=1)
    if bands == 3:
        B = [('O_6574', 'ins_6574'), ('O_7584', 'ins_7584'), ('O_85p', 'ins_85p')]
    else:  # 2つの帯：65〜74歳、75歳以上
        df['O_75p'] = df.O_7584 + df.O_85p
        df['ins_75p'] = df.ins_7584 + df.ins_85p
        B = [('O_6574', 'ins_6574'), ('O_75p', 'ins_75p')]
    df['O'] = sum(df[o] for o, _ in B)
    nat = {o: df[o].sum() / df[n].sum() for o, n in B}
    df['E'] = sum(nat[o] * df[n] for o, n in B)               # 間接法の期待数
    df['E0'] = df.ins_total * df.O.sum() / df.ins_total.sum()  # 年齢を調整しない期待数
    w = {n: df[n].sum() / df.ins_total.sum() for _, n in B}   # 全国の年齢構成（直接法の標準人口）
    df['crude'] = df.O / df.ins_total
    df['direct'] = sum(w[n] * np.where(df[n] > 0, df[o] / df[n].where(df[n] > 0, 1), 0) for o, n in B)
    df['SR'] = df.O / df.E
    df['share85'] = df.ins_85p / df.ins_total
    df['share75'] = (df.ins_7584 + df.ins_85p) / df.ins_total
    return df

def wvar(x, w):
    m = np.average(x, weights=w); return np.average((x - m) ** 2, weights=w)

def fit(O, E, grp, sd_prior=0.5, draws=1500, tune=1500):
    gi, gl = pd.factorize(grp)
    with pm.Model():
        mu = pm.Normal('mu', 0, 1)
        tp = pm.HalfNormal('tau_pref', sd_prior)
        ti = pm.HalfNormal('tau_ins', sd_prior)
        zp = pm.Normal('zp', 0, 1, shape=len(gl))
        # 保険者の層は、データが多いので中心化した形にする（収束のため）
        lt = pm.Normal('lt', mu + tp * zp[gi], ti, shape=len(O))
        pm.Poisson('y', mu=np.asarray(E) * pm.math.exp(lt), observed=np.asarray(O).astype(int))
        tr = pm.sample(draws=draws, tune=tune, chains=4, cores=2, random_seed=SEED, progressbar=False,
                       target_accept=0.9, compute_convergence_checks=False)
    p = tr.posterior
    tp_, ti_ = p['tau_pref'].values.ravel(), p['tau_ins'].values.ravel()
    tot = tp_ ** 2 + ti_ ** 2
    lt_ = p['lt'].values.reshape(-1, len(O))
    theta = np.exp(lt_)  # 全国の年齢別認定率で見込んだ数に対する比
    import arviz as az
    rhat = max(float(az.rhat(p[v].values)) for v in ['tau_pref', 'tau_ins'])
    return dict(tau_pref=float(tp_.mean()), tau_ins=float(ti_.mean()), var_tot=float(tot.mean()),
                var_tot_ci=[float(np.quantile(tot, .025)), float(np.quantile(tot, .975))],
                pref_share=float((tp_ ** 2 / tot).mean()), rhat=rhat,
                theta=theta.mean(0), theta_lo=np.quantile(theta, .05, 0), theta_hi=np.quantile(theta, .95, 0),
                tot_draws=tot)

def run(df, label, sd_prior=0.5, keep=False):
    a = fit(df.O, df.E, df.pref, sd_prior)   # 年齢調整あり
    b = fit(df.O, df.E0, df.pref, sd_prior)  # 年齢調整なし
    expl = 1 - a['tot_draws'] / b['tot_draws']
    r = dict(label=label, n=len(df),
             sd_adj=float(np.sqrt(a['var_tot'])), sd_unadj=float(np.sqrt(b['var_tot'])),
             explained=float(expl.mean()), explained_ci=[float(np.quantile(expl, .025)), float(np.quantile(expl, .975))],
             pref_share_adj=a['pref_share'], pref_share_unadj=b['pref_share'], rhat=max(a['rhat'], b['rhat']),
             range90_adj=[float(np.quantile(a['theta'], .05)), float(np.quantile(a['theta'], .95))],
             range90_unadj=[float(np.quantile(b['theta'], .05)), float(np.quantile(b['theta'], .95))])
    print(label, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    return (r, a, b) if keep else r

res = {}
d24 = prep(df0[df0.year == 2024])
# --- 記述：粗い認定率と年齢調整のあと ---
w = d24.ins_total
lc, lsr = np.log(d24.crude), np.log(d24.SR.clip(lower=1e-3))
X = np.log(d24.E / d24.ins_total)
beta = np.polyfit(X, lc, 1, w=np.sqrt(w))
pred = np.polyval(beta, X)
r2 = 1 - wvar(lc - pred, w) / wvar(lc, w)
res['desc'] = dict(n=len(d24), nat_rate=float(d24.O.sum() / d24.ins_total.sum()),
                   crude_p5_p95=[float(np.percentile(d24.crude, 5)), float(np.percentile(d24.crude, 95))],
                   SR_p5_p95=[float(np.percentile(d24.SR, 5)), float(np.percentile(d24.SR, 95))],
                   sd_log_crude=float(np.sqrt(wvar(lc, w))), sd_log_SR=float(np.sqrt(wvar(lsr, w))),
                   r2_crude_on_expected=float(r2), slope=float(beta[0]),
                   corr_crude_share85=float(np.corrcoef(d24.crude, d24.share85)[0, 1]),
                   corr_SR_share85=float(np.corrcoef(d24.SR, d24.share85)[0, 1]),
                   band_rates={b: float(d24[f'O_{b}'].sum() / d24[f'ins_{b}'].sum()) for b in ['6574', '7584', '85p']},
                   share85_p5_p95=[float(np.percentile(d24.share85, 5)), float(np.percentile(d24.share85, 95))],
                   corr_direct_indirect=float(np.corrcoef(d24.direct, d24.SR)[0, 1]))
# ファンネル：ポアソンの95%・99.8%の範囲の外にある保険者の割合
from scipy.stats import poisson
lo95, hi95 = poisson.ppf(.025, d24.E) / d24.E, poisson.ppf(.975, d24.E) / d24.E
lo998, hi998 = poisson.ppf(.001, d24.E) / d24.E, poisson.ppf(.999, d24.E) / d24.E
res['funnel'] = dict(out95=float(((d24.SR < lo95) | (d24.SR > hi95)).mean()),
                     out998=float(((d24.SR < lo998) | (d24.SR > hi998)).mean()))
print(res['desc'], res['funnel'], flush=True)

# --- 本推定：2024年度、3つの年齢の帯、全ての要介護度 ---
main, a, b = run(d24, 'main_2024', keep=True)
res['main'] = main
d24['theta'] = a['theta']; d24['theta_lo'] = a['theta_lo']; d24['theta_hi'] = a['theta_hi']
d24['theta_unadj'] = b['theta']
# 縮小の大きさ：生の比と縮小後の比の差を、保険者の規模別に
d24['size'] = pd.qcut(d24.ins_total, 5, labels=['最小', '小', '中', '大', '最大'])
d24['shrink'] = 1 - (np.log(d24.theta) / np.log(d24.SR.clip(lower=1e-3)).replace(0, np.nan)).clip(-5, 5)
tab = d24.groupby('size', observed=True).apply(lambda g: pd.Series(dict(
    n=len(g), ins_median=g.ins_total.median(),
    raw_out20=((g.SR < .8) | (g.SR > 1.2)).mean(), post_out20=((g.theta < .8) | (g.theta > 1.2)).mean(),
    abs_log_raw=np.abs(np.log(g.SR.clip(lower=1e-3))).median(), abs_log_post=np.abs(np.log(g.theta)).median(),
    ci_width=(g.theta_hi - g.theta_lo).median())))
res['by_size'] = tab.reset_index().to_dict('records')
res['out20'] = dict(raw=float(((d24.SR < .8) | (d24.SR > 1.2)).mean()), post=float(((d24.theta < .8) | (d24.theta > 1.2)).mean()),
                    post_ci_excl1=float(((d24.theta_lo > 1) | (d24.theta_hi < 1)).mean()))
print(tab, res['out20'], flush=True)
d24.drop(columns=['size']).to_csv('results/insurer_2024_estimates.csv', index=False)

# --- 頑健性 ---
rob = []
rob.append(run(prep(df0[df0.year == 2024], bands=2), 'bands2'))
rob.append(run(prep(df0[df0.year == 2024], levels='care2p'), 'care2plus'))
rob.append(run(prep(df0[df0.year == 2024], levels='support'), 'support_only'))
rob.append(run(d24[d24.ins_total >= 3000].copy(), 'exclude_small_lt3000'))
rob.append(run(d24, 'prior_sd0.1', sd_prior=0.1))
rob.append(run(d24, 'prior_sd2', sd_prior=2.0))
# 年度
yr_theta = {}
for y in [2020, 2021, 2022, 2023]:
    dy = prep(df0[df0.year == y])
    r, ay, _ = run(dy, f'year_{y}', keep=True)
    rob.append(r)
    yr_theta[y] = pd.Series(ay['theta'], index=dy.pref + '|' + dy.insurer)
yr_theta[2024] = pd.Series(d24.theta.values, index=d24.pref + '|' + d24.insurer)
raw_sr = {y: (lambda dy: pd.Series(dy.SR.values, index=dy.pref + '|' + dy.insurer))(prep(df0[df0.year == y])) for y in [2020, 2024]}
common = yr_theta[2020].index.intersection(yr_theta[2024].index)
res['year_corr'] = dict(post_2020_2024=float(np.corrcoef(np.log(yr_theta[2020][common]), np.log(yr_theta[2024][common]))[0, 1]),
                        raw_2020_2024=float(np.corrcoef(np.log(raw_sr[2020][common].clip(lower=1e-3)), np.log(raw_sr[2024][common].clip(lower=1e-3)))[0, 1]),
                        n=int(len(common)))
print(res['year_corr'], flush=True)
# 経験ベイズ（ガンマ・ポアソン、モーメント法）
def eb(O, E):
    sr = O / E; wts = E / E.sum(); m = np.sum(wts * sr)
    s2 = np.sum(wts * (sr - m) ** 2) - m / E.mean()
    s2 = max(s2, 1e-6); a_ = m ** 2 / s2; b_ = m / s2
    return (O + a_) / (E + b_), np.sqrt(s2) / m
th_eb, cv_eb = eb(d24.O.values, d24.E.values)
th_eb0, cv_eb0 = eb(d24.O.values, d24.E0.values)
res['eb'] = dict(cv_adj=float(cv_eb), cv_unadj=float(cv_eb0), explained=float(1 - cv_eb ** 2 / cv_eb0 ** 2),
                 corr_with_hb=float(np.corrcoef(np.log(th_eb), np.log(d24.theta))[0, 1]))
print(res['eb'], flush=True)
# 都道府県単位（取れないときの代替）
p = df0[df0.year == 2024].groupby('pref').sum(numeric_only=True).reset_index()
p['insurer'] = p.pref
dp = prep(p)
wp = dp.ins_total
from scipy.stats import chi2
def pref_desc(dp):
    lc, ls = np.log(dp.crude), np.log(dp.SR)
    return dict(sd_log_crude=float(np.sqrt(wvar(lc, wp))), sd_log_SR=float(np.sqrt(wvar(ls, wp))),
                explained_naive=float(1 - wvar(ls, wp) / wvar(lc, wp)),
                SR_min_max=[float(dp.SR.min()), float(dp.SR.max())], crude_min_max=[float(dp.crude.min()), float(dp.crude.max())])
res['pref_level'] = pref_desc(dp)
dp[['pref', 'ins_total', 'O', 'E', 'crude', 'SR', 'direct', 'share85']].to_csv('results/pref_2024.csv', index=False)
print(res['pref_level'], flush=True)
res['robustness'] = rob
json.dump(res, open('results/results.json', 'w'), ensure_ascii=False, indent=1, default=float)
