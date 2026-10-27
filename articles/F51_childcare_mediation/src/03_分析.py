"""03 分析：媒介分析（処置→女性の労働力率→出生率）。積の方法＋ブートストラップ、感度分析、statsmodels の Mediation で照合"""
import json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings("ignore")
from common import ROOT, SEED, UNIT

d = pd.read_csv(ROOT / 'data/analysis.csv', dtype={'code': str})
BASE_X = [c for c in d.columns if c not in ('code', 'T', 'M', 'Y', 'M_emp', 'tfr_1317', 'tfr_1822', 'pop_f20', 'pop2010')]
PREF = [c for c in BASE_X if c.startswith('県_')]
rng = np.random.default_rng(SEED)


def fit(df, M='M', X=None):
    """a（T→M）、b（M→Y｜T）、c'（直接）、c（総合）を最小二乗法で推定"""
    X = X if X is not None else BASE_X + ['tfr_1317']
    Z = sm.add_constant(df[['T'] + X].astype(float))
    ma = sm.OLS(df[M], Z).fit()
    mc = sm.OLS(df['Y'], Z).fit()
    mb = sm.OLS(df['Y'], sm.add_constant(df[['T', M] + X].astype(float))).fit()
    return dict(a=ma.params['T'], b=mb.params[M], cp=mb.params['T'], c=mc.params['T'],
                ab=ma.params['T'] * mb.params[M], ma=ma, mb=mb, mc=mc)


def boot(df, M='M', X=None, B=1000, cluster=False):
    out = []
    groups = df.code.str[:2].values
    ug = np.unique(groups)
    for _ in range(B):
        if cluster:
            pick = rng.choice(ug, len(ug), replace=True)
            idx = np.concatenate([np.where(groups == g)[0] for g in pick])
        else:
            idx = rng.integers(0, len(df), len(df))
        f = fit(df.iloc[idx], M, X)
        out.append([f['a'], f['b'], f['cp'], f['c'], f['ab']])
    o = np.array(out)
    return {k: [float(np.percentile(o[:, i], 2.5)), float(np.percentile(o[:, i], 97.5))] for i, k in enumerate(['a', 'b', 'cp', 'c', 'ab'])}


def summary(df, M='M', X=None, B=1000, cluster=False):
    f = fit(df, M, X)
    ci = boot(df, M, X, B, cluster)
    r = {k: float(f[k]) for k in ['a', 'b', 'cp', 'c', 'ab']}
    r['ci'] = ci
    r['n'] = int(len(df))
    r['share'] = float(f['ab'] / f['c']) if abs(f['c']) > 1e-12 else None
    return r, f


R = {}
R['describe'] = dict(n=len(d), T_mean=float(d['T'].mean() * UNIT), T_sd=float(d['T'].std() * UNIT),
                     M_mean=float(d.M.mean()), M_sd=float(d.M.std()), Y_mean=float(d.Y.mean()), Y_sd=float(d.Y.std()),
                     tfr1317=float(d.tfr_1317.mean()), tfr1822=float(d.tfr_1822.mean()),
                     corr_TM=float(d[['T', 'M']].corr().iloc[0, 1]), corr_MY=float(d[['M', 'Y']].corr().iloc[0, 1]), corr_TY=float(d[['T', 'Y']].corr().iloc[0, 1]))
R['main'], f = summary(d)
R['main_cluster'], _ = summary(d, cluster=True, B=500)

# 感度分析（Imai, Keele & Yamamoto 2010 の線形モデルの式）：媒介モデルと結果モデル（媒介なし）の誤差の相関 ρ を動かす
e1 = f['ma'].resid; e2 = f['mc'].resid
s1, s2 = e1.std(ddof=0), e2.std(ddof=0)
rt = float(np.corrcoef(e1, e2)[0, 1])
def acme(rho):
    return f['a'] * s1 / s2 * (rt - rho * np.sqrt((1 - rt ** 2) / (1 - rho ** 2)))
rhos = np.round(np.arange(-0.9, 0.91, 0.01), 2)
R['sens'] = dict(rho_tilde=rt, rho_zero=rt, grid=[[float(r), float(acme(r))] for r in rhos], acme0=float(acme(0)))
# 符号が変わる ρ は ρ̃ そのもの（この式の性質）。b の推定値の何倍の交絡があれば消えるかも記録
R['sens']['note'] = 'ACME(ρ)=0 となるのは ρ=ρ̃'

# statsmodels の Mediation（シミュレーション）で照合
from statsmodels.stats.mediation import Mediation
X = BASE_X + ['tfr_1317']
dd = d[['T', 'M', 'Y'] + X].astype(float)
om = sm.OLS.from_formula('M ~ T + ' + ' + '.join(f'Q("{c}")' for c in X), dd)
oy = sm.OLS.from_formula('Y ~ T + M + ' + ' + '.join(f'Q("{c}")' for c in X), dd)
med = Mediation(oy, om, 'T', 'M').fit(n_rep=500)
s = med.summary()
R['statsmodels'] = {i: [float(s.loc[i, 'Estimate']), float(s.loc[i, 'Lower CI bound']), float(s.loc[i, 'Upper CI bound'])] for i in ['ACME (average)', 'ADE (average)', 'Total effect', 'Prop. mediated (average)']}

# 頑健性
rob = {}
rob['基本'] = R['main']
rob['媒介を就業率に'], _ = summary(d.dropna(subset=['M_emp']), M='M_emp', B=500)
rob['県ダミーなし'], _ = summary(d, X=[c for c in BASE_X if c not in PREF] + ['tfr_1317'], B=500)
rob['前の出生率で調整しない'], _ = summary(d, X=BASE_X, B=500)
rob['人口1万人以上'], _ = summary(d[d.pop2010 >= 10000], B=500)
q = d['T'].quantile([.01, .99]); qm = d.M.quantile([.01, .99])
rob['処置と媒介の外れ値を除く'], _ = summary(d[d['T'].between(*q) & d.M.between(*qm)], B=500)
rob['条件は県ダミーと前の出生率だけ'], _ = summary(d, X=PREF + ['tfr_1317'], B=500)
rob['県でまとめたブートストラップ'] = R['main_cluster']
R['robust'] = rob

# 人口規模で分けた a と b（効き方の違い）
d['size'] = pd.qcut(d.pop2010, 3, labels=['小', '中', '大'])
R['by_size'] = {}
for k, g in d.groupby('size', observed=True):
    r, _ = summary(g, B=300)
    R['by_size'][str(k)] = r

json.dump(R, open(ROOT / 'results/results.json', 'w'), ensure_ascii=False, indent=1)
rows = [dict(設定=k, n=v['n'], a=v['a'], b=v['b'], 間接効果=v['ab'], 間接の下限=v['ci']['ab'][0], 間接の上限=v['ci']['ab'][1], 直接効果=v['cp'], 総合効果=v['c'], 総合の下限=v['ci']['c'][0], 総合の上限=v['ci']['c'][1]) for k, v in rob.items()]
pd.DataFrame(rows).round(5).to_csv(ROOT / 'results/robustness.csv', index=False)
pd.DataFrame(R['sens']['grid'], columns=['rho', 'ACME']).round(6).to_csv(ROOT / 'results/sensitivity.csv', index=False)
print(json.dumps({k: R[k] for k in ['describe', 'main', 'statsmodels']}, ensure_ascii=False, indent=1)[:3000])
print(pd.DataFrame(rows).round(4).to_string())
print('rho_tilde', rt)
for k, v in R['by_size'].items(): print(k, v['n'], round(v['a'], 4), round(v['b'], 4), round(v['ab'], 5), v['ci']['ab'])
