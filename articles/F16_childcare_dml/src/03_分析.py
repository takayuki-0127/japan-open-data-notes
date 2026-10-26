"""03 分析：保育所等に通う子どもが増えた市区町村で、女性の労働力率は上がったか（ダブル機械学習）"""
import json, warnings
import numpy as np, pandas as pd
import statsmodels.api as sm
import doubleml as dml
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LassoCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMRegressor
from common import ROOT, SEED, wide, lfpr, emp, enroll, covariates, change_controls, pref_dummies
warnings.filterwarnings('ignore')
RES = ROOT / 'results'; RES.mkdir(exist_ok=True)
w = wide()
UNIT = 10  # 効果は「0〜5歳100人あたりの在所児が10人増えたとき」で表す
MIN_CHILD = 100  # 0〜5歳が100人未満の町村は、割合が大きく振れるので除く


def build(a=2010, b=2015, y_fn=lfpr, d_a=None, d_b=None, x_pre=True, extra_drop=None):
    X = covariates(w)
    if not x_pre:
        X = X.drop(columns=['前の5年の労働力率の変化', '前の5年の在所児の変化', '女性の労働力率（2010）'])
    C = change_controls(w, a, b) if b in w and 'A1101' in w[b] else change_controls(w, 2010, 2015)
    P = pref_dummies(X.index)
    Y = y_fn(w[b]) - y_fn(w[a])
    D = ((d_b if d_b is not None else enroll(w[b])) - (d_a if d_a is not None else enroll(w[a]))) / UNIT
    df = pd.concat([Y.rename('Y'), D.rename('D'), X, C, P], axis=1)
    df = df[(w[2010].A1405 >= MIN_CHILD).reindex(df.index).fillna(False)]
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    if extra_drop is not None:
        df = extra_drop(df)
    return df


def learners(kind):
    if kind == 'rf':
        m = RandomForestRegressor(n_estimators=200, min_samples_leaf=5, max_features=0.33, n_jobs=-1, random_state=SEED)
        return m, m
    if kind == 'lgbm':
        m = LGBMRegressor(n_estimators=300, learning_rate=0.04, num_leaves=15, min_child_samples=20, subsample=0.8, subsample_freq=1, colsample_bytree=0.7, verbose=-1, random_state=SEED)
        return m, m
    if kind == 'lasso':
        m = make_pipeline(StandardScaler(), LassoCV(cv=5, random_state=SEED, max_iter=20000))
        return m, m


CACHE_F = RES / '_cache.json'
CACHE = json.load(open(CACHE_F)) if CACHE_F.exists() else {}


def dml_fit(df, kind='rf', folds=5, reps=5, seed=SEED, key=None):
    if key and key in CACHE:
        return CACHE[key]
    out = _dml_fit(df, kind, folds, reps, seed)
    if key:
        CACHE[key] = out; json.dump(CACHE, open(CACHE_F, 'w'), ensure_ascii=False)
        print('done', key, round(out['coef'], 4), round(out['lo'], 4), round(out['hi'], 4), flush=True)
    return out


def _dml_fit(df, kind='rf', folds=5, reps=5, seed=SEED):
    xcols = [c for c in df.columns if c not in ('Y', 'D')]
    data = dml.DoubleMLData(df, y_col='Y', d_cols='D', x_cols=xcols)
    ml_l, ml_m = learners(kind)
    np.random.seed(seed)
    m = dml.DoubleMLPLR(data, ml_l=ml_l, ml_m=ml_m, n_folds=folds, n_rep=reps, score='partialling out')
    m.fit(store_predictions=True)
    ci = m.confint().iloc[0]
    out = dict(coef=float(m.coef[0]), se=float(m.se[0]), lo=float(ci.iloc[0]), hi=float(ci.iloc[1]), p=float(m.pval[0]), n=len(df),
               reps=[float(v) for v in np.ravel(m.all_coef)])
    # 予測の当てはまり（それぞれの部分の R²）
    pl = m.predictions['ml_l'][:, 0, 0]; pm = m.predictions['ml_m'][:, 0, 0]
    out['r2_y'] = float(1 - np.mean((df.Y - pl) ** 2) / np.var(df.Y))
    out['r2_d'] = float(1 - np.mean((df.D - pm) ** 2) / np.var(df.D))
    return out


def ols(df, controls=True):
    cols = ['D'] + ([c for c in df.columns if c not in ('Y', 'D')] if controls else [])
    r = sm.OLS(df.Y, sm.add_constant(df[cols])).fit(cov_type='HC3')
    lo, hi = r.conf_int().loc['D']
    return dict(coef=float(r.params['D']), se=float(r.bse['D']), lo=float(lo), hi=float(hi), p=float(r.pvalues['D']), n=len(df))


if __name__ == '__main__':
    R = {}
    df = build()
    df.to_csv(ROOT / 'data/analysis_2010_2015.csv', encoding='utf-8')
    R['describe'] = dict(n=len(df), Y_mean=float(df.Y.mean()), Y_sd=float(df.Y.std()), D_mean=float(df.D.mean() * UNIT), D_sd=float(df.D.std() * UNIT),
                         enroll2010_med=float(df['保育所等に通う子ども（2010）'].median()), n_x=len(df.columns) - 2,
                         corr=float(np.corrcoef(df.Y, df.D)[0, 1]))
    print('n', len(df), R['describe'])
    # 1. 比べ方による違い
    R['ols_naive'] = ols(df, False)
    R['ols_ctrl'] = ols(df, True)
    for k in ['lasso', 'rf', 'lgbm']:
        R['dml_' + k] = dml_fit(df, k, key='dml_' + k)
        print(k, {a: round(b, 4) for a, b in R['dml_' + k].items() if a != 'reps'})
    print('ols', R['ols_naive'], R['ols_ctrl'])
    # 2. 交差適合の分け方を変えた繰り返し（ランダムフォレスト・20回）
    R['dml_rf_rep20'] = dml_fit(df, 'rf', reps=20, seed=SEED + 1, key='rep20')
    # 3. 都市と地方（人口密度で3つに分ける）
    t = pd.qcut(df['log人口密度'], 3, labels=['地方（密度が低い）', '中間', '都市（密度が高い）'])
    R['hetero'] = {}
    for lab in t.cat.categories:
        R['hetero'][lab] = dml_fit(df[t == lab], 'rf', key='h_' + lab)
    # 2010年の在所児の水準で分ける
    t2 = pd.qcut(df['保育所等に通う子ども（2010）'], 2, labels=['2010年に少なかった', '2010年に多かった'])
    for lab in t2.cat.categories:
        R['hetero'][lab] = dml_fit(df[t2 == lab], 'rf', key='h_' + lab)
    # 4. 頑健性
    rob = {}
    rob['分割 2'] = dml_fit(df, 'rf', folds=2, key='r_分割 2')
    rob['分割 10'] = dml_fit(df, 'rf', folds=10, key='r_分割 10')
    rob['乱数を変える'] = dml_fit(df, 'rf', seed=SEED + 99, key='r_乱数を変える')
    q = df.D.quantile([0.01, 0.99]); qy = df.Y.quantile([0.01, 0.99])
    rob['極端な1%を除く'] = dml_fit(df[df.D.between(*q) & df.Y.between(*qy)], 'rf', key='r_極端な1%を除く')
    rob['人口1万人未満を除く'] = dml_fit(df[np.exp(df['log人口']) >= 10000], 'rf', key='r_人口1万人未満を除く')
    rob['県の違いを入れない'] = dml_fit(df[[c for c in df.columns if not c.startswith('県_')]], 'rf', key='r_県の違いを入れない')
    rob['前の傾向を入れない'] = dml_fit(df.drop(columns=['前の5年の労働力率の変化', '前の5年の在所児の変化']), 'rf', key='r_前の傾向を入れない')
    d2 = build(y_fn=emp)
    rob['結果を就業率に'] = dml_fit(d2, 'rf', key='r_結果を就業率に')
    # 10年の長い差：在所児 2010→2017（認定こども園を足す）、労働力率 2010→2020
    g17 = w[2017].copy(); g17['A1405'] = w[2015].A1405  # 2017年の0〜5歳人口はないので2015年の値で割る
    d3 = build(a=2010, b=2020, d_a=enroll(w[2010]), d_b=enroll(g17, kodomoen=True))
    rob['長い差（2010→20、こども園を含む）'] = dml_fit(d3, 'rf', key='r_長い差（2010→20、こども園を含む）')
    R['robust'] = rob
    # 5. プラセボ：前の5年（2005→10）の労働力率の変化を、後の在所児の変化（2010→15）で説明できてしまうか
    dp = build(x_pre=False)
    dp['Y'] = (lfpr(w[2010]) - lfpr(w[2005])).reindex(dp.index)
    dp = dp.drop(columns=['女性65歳以上の割合の変化', '女性15〜64歳の割合の変化', '0〜5歳の割合の変化', '人口増減率']).dropna()
    R['placebo'] = dml_fit(dp, 'rf', key='placebo')
    # 6. 何が予測に効いたか（ランダムフォレストの重要度、全データで当てはめ）
    xcols = [c for c in df.columns if c not in ('Y', 'D')]
    imp = {}
    for tgt in ['Y', 'D']:
        rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, max_features=0.33, n_jobs=-1, random_state=SEED).fit(df[xcols], df[tgt])
        s = pd.Series(rf.feature_importances_, index=xcols)
        pref = s[[c for c in xcols if c.startswith('県_')]].sum()
        s = s[[c for c in xcols if not c.startswith('県_')]]
        s['都道府県（46のダミーの合計）'] = pref
        imp[tgt] = s.sort_values(ascending=False).head(12).round(4).to_dict()
    R['importance'] = imp
    # 1人あたりの換算：在所児が1人増えたとき、労働力の女性が何人増えたか
    g = w[2010].reindex(df.index)
    ratio = ((g.F110102 + g.F110802) / g.A1405).median()
    R['per_child'] = dict(women_per_child_median=float(ratio), women_per_extra_child=float(R['dml_rf']['coef'] * ratio / 10))
    json.dump(R, open(RES / 'results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rows = []
    for k in ['ols_naive', 'ols_ctrl', 'dml_lasso', 'dml_rf', 'dml_lgbm']:
        rows.append(dict(model=k, **{a: R[k][a] for a in ['coef', 'se', 'lo', 'hi', 'p', 'n']}))
    for k, v in R['robust'].items():
        rows.append(dict(model='頑健性:' + k, **{a: v[a] for a in ['coef', 'se', 'lo', 'hi', 'p', 'n']}))
    for k, v in R['hetero'].items():
        rows.append(dict(model='分けた推定:' + k, **{a: v[a] for a in ['coef', 'se', 'lo', 'hi', 'p', 'n']}))
    rows.append(dict(model='プラセボ（2005→10）', **{a: R['placebo'][a] for a in ['coef', 'se', 'lo', 'hi', 'p', 'n']}))
    pd.DataFrame(rows).round(4).to_csv(RES / 'estimates.csv', index=False, encoding='utf-8')
    print(pd.DataFrame(rows).round(3).to_string())
    print(R['importance']); print(R['per_child'])
