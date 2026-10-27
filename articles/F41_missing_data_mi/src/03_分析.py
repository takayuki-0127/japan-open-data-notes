"""03 分析：欠測の形、4つの扱い方の比較（実データ）、わざと欠測を作るシミュレーション、頑健性
python 03_分析.py          … 全部（シミュレーションは数十分かかる）
python 03_分析.py --quick  … シミュレーションの回数を減らして試す
"""
import sys, json, warnings, numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LinearRegression
from common import *

warnings.filterwarnings('ignore')
QUICK = '--quick' in sys.argv
R = ROOT / 'results'
SC = {'持ち家率': 10, '一戸建て率': 10, '65歳以上の割合': 10, '大卒の割合': 10, '第1次産業の割合': 10,
      'log人口密度': 1, '単独世帯の割合': 10, '女性の労働力率': 10, 'log所得': 0.1}   # 係数は「この幅あたり」
REPORT = ['持ち家率', '65歳以上の割合', '大卒の割合', '第1次産業の割合', '単独世帯の割合', 'log所得']


def ols(df, xs=XALL):
    X = sm.add_constant(df[xs]); r = sm.OLS(df[Y], X).fit(cov_type='HC1')
    return r.params[xs] * pd.Series(SC)[xs], r.bse[xs] * pd.Series(SC)[xs], len(df)


def rubin(ests, ses):
    """ルービンのルールで m 組の推定をまとめる"""
    E = pd.DataFrame(ests); S = pd.DataFrame(ses); m = len(E)
    qbar = E.mean(); ubar = (S ** 2).mean(); b = E.var(ddof=1)
    t = ubar + (1 + 1 / m) * b
    df_ = (m - 1) * (1 + ubar / ((1 + 1 / m) * b)) ** 2
    fmi = ((1 + 1 / m) * b) / t
    return qbar, np.sqrt(t), df_, fmi


def impute_mice(df, m=20, seed=SEED, with_y=True, pref=False, aux=True, max_iter=15):
    cols = ([Y] if with_y else []) + XALL
    M = df[cols].copy()
    if aux:   # 分析には入れないが、欠け方に関わる人口を埋めるときの手がかりに使う
        M['log人口'] = np.log(df['人口'])
    if pref:
        M = pd.concat([M, pd.get_dummies(df['pref'], prefix='p', drop_first=True).astype(float)], axis=1)
    out = []
    for k in range(m):
        imp = IterativeImputer(estimator=BayesianRidge(), sample_posterior=True, max_iter=max_iter,
                               random_state=seed + k, skip_complete=True)
        A = pd.DataFrame(imp.fit_transform(M), index=M.index, columns=M.columns)
        dd = df.copy(); dd[XMISS] = A[XMISS]
        out.append(dd)
    return out


def fit_mice(df, **kw):
    sets = impute_mice(df, **kw)
    ests, ses = [], []
    for dd in sets:
        e, s, _ = ols(dd); ests.append(e); ses.append(s)
    return rubin(ests, ses), sets


def mean_impute(df):
    dd = df.copy()
    for c in XMISS: dd[c] = dd[c].fillna(dd[c].mean())
    return dd


def reg_impute(df):
    """回帰で1回だけ埋める（ばらつきを足さない）。結果の変数は使わない"""
    dd = df.copy(); obs = dd[XMISS[0]].notna()
    for c in XMISS:
        lr = LinearRegression().fit(dd.loc[obs, XFULL], dd.loc[obs, c])
        dd.loc[~obs, c] = lr.predict(dd.loc[~obs, XFULL])
    return dd


def methods_on(df, m=20, seed=SEED):
    """4つ＋1つの扱い方で係数を出す（持ち家率などの欠測がある df）"""
    res = {}
    e, s, n = ols(df.dropna(subset=XMISS)); res['完全ケース'] = (e, s, n, np.nan)
    e, s, n = ols(mean_impute(df)); res['平均で埋める'] = (e, s, n, np.nan)
    e, s, n = ols(reg_impute(df)); res['回帰で1回埋める'] = (e, s, n, np.nan)
    (q, t, _, f), _ = fit_mice(df, m=m, seed=seed); res['多重代入（結果も使う）'] = (q, t, len(df), f)
    (q, t, _, f), _ = fit_mice(df, m=m, seed=seed, with_y=False); res['多重代入（結果を使わない）'] = (q, t, len(df), f)
    return res


def tidy_res(res, tag=''):
    rows = []
    for k, (e, s, n, f) in res.items():
        for v in e.index:
            rows.append({'setting': tag, 'method': k, 'var': v, 'coef': e[v], 'se': s[v], 'lo': e[v] - 1.96 * s[v],
                         'hi': e[v] + 1.96 * s[v], 'n': n, 'fmi': (f[v] if isinstance(f, pd.Series) else np.nan)})
    return pd.DataFrame(rows)


def main():
    d = make_data()
    d = d[d[Y] > 0]
    d['欠測'] = d[FOCUS].isna().astype(int)
    summ = {'n': len(d), 'n_missing': int(d['欠測'].sum()), 'share_missing': round(d['欠測'].mean(), 4)}

    # --- 1 欠測の形 ---
    bins = [0, 3000, 5000, 10000, 15000, 20000, 50000, 1e9]
    lab = ['〜3千', '3千〜5千', '5千〜1万', '1万〜1.5万', '1.5万〜2万', '2万〜5万', '5万〜']
    d['人口区分'] = pd.cut(d['人口'], bins, labels=lab, right=False)
    pat = d.groupby('人口区分', observed=False).agg(市区町村=('欠測', 'size'), 欠測の割合=('欠測', 'mean')).reset_index()
    pat.to_csv(R / 'missing_by_pop.csv', index=False)
    comp = d.groupby('欠測')[[Y] + XFULL + ['人口']].mean().T
    comp.columns = ['値がある', '値がない']; comp.to_csv(R / 'missing_compare.csv')
    # 欠けるかどうかを人口などで説明（ロジット）
    z = standardize_cols(d, XFULL + [Y])
    z['log人口'] = np.log(d['人口']); z['log人口'] = (z['log人口'] - z['log人口'].mean()) / z['log人口'].std()
    lg = sm.Logit(d['欠測'], sm.add_constant(z[['log人口'] + XFULL + [Y]])).fit(disp=0)
    pd.DataFrame({'coef': lg.params, 'se': lg.bse, 'p': lg.pvalues}).to_csv(R / 'missing_logit.csv')
    lg1 = sm.Logit(d['欠測'], sm.add_constant(z[['log人口']])).fit(disp=0)
    lg2 = sm.Logit(d['欠測'], sm.add_constant(z[[Y]])).fit(disp=0)
    summ['logit_pseudoR2_pop_only'] = round(lg1.prsquared, 3)
    summ['logit_pseudoR2_all'] = round(lg.prsquared, 3)
    summ['logit_pseudoR2_y_only'] = round(lg2.prsquared, 3)
    summ['pop_range_observed'] = [float(d.loc[d['欠測'] == 0, '人口'].min()), float(d.loc[d['欠測'] == 0, '人口'].max())]
    summ['pop_range_missing'] = [float(d.loc[d['欠測'] == 1, '人口'].min()), float(d.loc[d['欠測'] == 1, '人口'].max())]
    summ['n_obs_under_15k'] = int(((d['欠測'] == 0) & (d['人口'] < 15185)).sum())

    # --- 2 実データで4つの扱い方 ---
    base = tidy_res(methods_on(d), 'base')
    base.to_csv(R / 'coef_methods.csv', index=False)
    (q, t, _, f), sets = fit_mice(d, m=20)
    # 埋めた値の分布（1組目〜5組目）
    imp_vals = pd.concat([pd.DataFrame({'set': k, '持ち家率': s.loc[d['欠測'] == 1, '持ち家率'].values}) for k, s in enumerate(sets[:5])])
    imp_vals.to_csv(R / 'imputed_values.csv', index=False)
    summ['imputed_mean_owner'] = round(float(imp_vals['持ち家率'].mean()), 2)
    summ['observed_mean_owner'] = round(float(d['持ち家率'].mean()), 2)
    summ['imputed_share_over100'] = round(float((imp_vals['持ち家率'] > 100).mean()), 4)

    # --- 3 シミュレーション：値が全部ある町で、わざと欠かせる ---
    full = d.dropna(subset=XMISS).copy()
    truth, _, _ = ols(full)
    reps = 20 if QUICK else 100; mm = 5 if QUICK else 10
    rng = np.random.default_rng(SEED)
    lp = np.log(full['人口']); lp = (lp - lp.mean()) / lp.std()
    oz = (full[FOCUS] - full[FOCUS].mean()) / full[FOCUS].std()
    yz = (full[Y] - full[Y].mean()) / full[Y].std()

    def miss_prob(kind, rate):
        if kind == 'MCAR': s = np.zeros(len(full))
        elif kind == 'MAR（人口で欠ける）': s = -2.0 * lp.values
        elif kind == 'MAR（結果で欠ける）': s = 2.0 * yz.values
        else: s = 2.0 * oz.values                                  # MNAR：持ち家率そのもので欠ける
        # 平均の欠測率が rate になるように切片を合わせる
        lo, hi = -20, 20
        for _ in range(60):
            a = (lo + hi) / 2; p = 1 / (1 + np.exp(-(a + s)))
            lo, hi = (a, hi) if p.mean() < rate else (lo, a)
        return p

    sim = []
    kinds = ['MCAR', 'MAR（人口で欠ける）', 'MAR（結果で欠ける）', 'MNAR（持ち家率で欠ける）']
    for kind in kinds:
        p = miss_prob(kind, 0.35)
        for r in range(reps):
            mask = rng.random(len(full)) < p
            dd = full.copy(); dd.loc[mask, XMISS] = np.nan
            res = methods_on(dd, m=mm, seed=SEED + 1000 * r)
            for meth, (e, s, n, f) in res.items():
                sim.append({'kind': kind, 'rep': r, 'method': meth, 'coef': e[FOCUS], 'se': s[FOCUS],
                            'cover': int(abs(e[FOCUS] - truth[FOCUS]) <= 1.96 * s[FOCUS])})
        print('sim done', kind, flush=True)
    sim = pd.DataFrame(sim); sim.to_csv(R / 'sim_reps.csv', index=False)
    agg = sim.groupby(['kind', 'method']).agg(平均=('coef', 'mean'), 標準偏差=('coef', 'std'), 平均SE=('se', 'mean'),
                                              カバー率=('cover', 'mean')).reset_index()
    agg['偏り'] = agg['平均'] - truth[FOCUS]
    agg['RMSE'] = np.sqrt(agg['偏り'] ** 2 + agg['標準偏差'] ** 2)
    agg.to_csv(R / 'sim_summary.csv', index=False)
    summ['truth_full_owner_per10'] = round(float(truth[FOCUS]), 3)
    # 持ち家率の効き方は町の大きさで違うか（値が全部ある町で、log人口との交互作用）
    h = full.copy(); h['lp'] = np.log(h['人口']); h['lp'] = h['lp'] - h['lp'].mean()
    h['持ち家率x人口'] = h['持ち家率'] * h['lp']
    rh = sm.OLS(h[Y], sm.add_constant(h[XALL + ['lp', '持ち家率x人口']])).fit(cov_type='HC1')
    summ['interaction_owner_x_logpop_per10'] = [round(float(rh.params['持ち家率x人口'] * 10), 3), round(float(rh.bse['持ち家率x人口'] * 10), 3)]
    big = full[full['人口'] >= full['人口'].median()]; small = full[full['人口'] < full['人口'].median()]
    summ['owner_coef_big_half'] = round(float(ols(big)[0][FOCUS]), 3)
    summ['owner_coef_small_half'] = round(float(ols(small)[0][FOCUS]), 3)

    # --- 4 欠測率を変える（MAR：人口で欠ける） ---
    rr = []
    for rate in [0.1, 0.2, 0.35, 0.5, 0.6]:
        p = miss_prob('MAR（人口で欠ける）', rate)
        for r in range(10 if QUICK else 60):
            mask = rng.random(len(full)) < p
            dd = full.copy(); dd.loc[mask, XMISS] = np.nan
            e, s, _ = ols(dd.dropna(subset=XMISS))
            (q2, t2, _, _), _ = fit_mice(dd, m=5, seed=SEED + 7 * r)
            rr += [{'rate': rate, 'rep': r, 'method': '完全ケース', 'coef': e[FOCUS], 'se': s[FOCUS]},
                   {'rate': rate, 'rep': r, 'method': '多重代入（結果も使う）', 'coef': q2[FOCUS], 'se': t2[FOCUS]}]
    rr = pd.DataFrame(rr); rr.to_csv(R / 'sim_rate_reps.csv', index=False)
    ra = rr.groupby(['rate', 'method']).agg(平均=('coef', 'mean'), 標準偏差=('coef', 'std'), 平均SE=('se', 'mean')).reset_index()
    ra['偏り'] = ra['平均'] - truth[FOCUS]
    ra.to_csv(R / 'sim_rate_summary.csv', index=False)
    print('rate done', flush=True)

    # --- 5 頑健性（実データ） ---
    rob = []

    def add(tag, q, t, n):
        for v in REPORT:
            rob.append({'setting': tag, 'var': v, 'coef': q[v], 'lo': q[v] - 1.96 * t[v], 'hi': q[v] + 1.96 * t[v], 'n': n})
    for m_ in [5, 20, 50]:
        (q, t, _, _), _ = fit_mice(d, m=m_); add(f'多重代入 m={m_}', q, t, len(d))
    (q, t, _, _), _ = fit_mice(d, m=20, seed=SEED + 99); add('多重代入 乱数の種を変える', q, t, len(d))
    (q, t, _, _), _ = fit_mice(d, m=20, pref=True); add('多重代入 都道府県も使う', q, t, len(d))
    (q, t, _, _), _ = fit_mice(d, m=20, with_y=False); add('多重代入 結果を使わない', q, t, len(d))
    # statsmodels の MICE（予測平均マッチング）
    try:
        from statsmodels.imputation import mice as smm
        dd = d[[Y] + XALL].copy(); dd.columns = ['y'] + [f'x{i}' for i in range(len(XALL))]
        imp = smm.MICEData(dd)
        np.random.seed(SEED)
        est, ses = [], []
        for k in range(20):
            imp.update_all(5)
            r_ = sm.OLS(imp.data['y'], sm.add_constant(imp.data[[f'x{i}' for i in range(len(XALL))]])).fit(cov_type='HC1')
            pr = pd.Series(r_.params.values[1:], index=XALL) * pd.Series(SC)[XALL]
            bs = pd.Series(r_.bse.values[1:], index=XALL) * pd.Series(SC)[XALL]
            est.append(pr); ses.append(bs)
        q, t, _, _ = rubin(est, ses); add('予測平均マッチング（statsmodels）', q, t, len(d))
    except Exception as ex:
        print('PMM skipped', ex)
    # 人口が観測のある範囲（3,585人以上）に絞る
    sub = d[d['人口'] >= d.loc[d['欠測'] == 0, '人口'].min()]
    (q, t, _, _), _ = fit_mice(sub, m=20); add('人口が観測のある範囲に絞る', q, t, len(sub))
    e, s, n = ols(sub.dropna(subset=XMISS)); add('完全ケース（同じ範囲）', e, s, n)
    # 2008年の住宅で
    d8 = make_data(house_year=2008); d8 = d8[d8[Y] > 0]
    e, s, n = ols(d8.dropna(subset=XMISS)); add('2008年の住宅 完全ケース', e, s, n)
    (q, t, _, _), _ = fit_mice(d8, m=20); add('2008年の住宅 多重代入', q, t, len(d8))
    pd.DataFrame(rob).to_csv(R / 'robustness.csv', index=False)

    json.dump(summ, open(R / 'summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False))
    print(base[base['var'] == FOCUS].round(3).to_string())
    print(agg.round(3).to_string())


if __name__ == '__main__':
    main()
