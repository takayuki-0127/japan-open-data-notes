# 記述のみ。因果は言わない。スキは「公開からの日数」で割った率で比べる
import pandas as pd, numpy as np, pathlib, json
from scipy import stats
import statsmodels.api as sm, statsmodels.formula.api as smf
B = pathlib.Path(__file__).resolve().parents[1]; R = B/'results'; R.mkdir(exist_ok=True)
df = pd.read_csv(B/'data/articles.csv')
rng = np.random.default_rng(164)
out = {}
def garwood(k, t, a=0.05):
    lo = stats.chi2.ppf(a/2, 2*k)/2 if k > 0 else 0.0
    hi = stats.chi2.ppf(1-a/2, 2*k+2)/2
    return lo/t*30, hi/t*30
def table(g, name):
    t = df.groupby(g, observed=True).agg(n=('key','size'), likes=('like','sum'), comments=('comment','sum'),
        days=('days','sum'), any_like=('like', lambda s: (s>0).mean()), chars=('chars','median'), figs=('n_img','median')).reset_index()
    t['likes_per30d'] = t.likes/t.days*30
    ci = [garwood(k, d) for k, d in zip(t.likes, t.days)]
    t['ci_lo'] = [c[0] for c in ci]; t['ci_hi'] = [c[1] for c in ci]
    t.to_csv(R/f'by_{name}.csv', index=False); return t
tf = table('fig_bin', 'figures'); tfam = table('family', 'family')
df['period'] = np.where(pd.to_datetime(df.publishAt, utc=True) < pd.Timestamp('2026-10-17', tz='UTC'), '2026年8〜9月', '2026年10月17日以降')
tp = table('period', 'period')
df['tl_bin'] = pd.cut(df.title_len, [0,45,70,100], labels=['45字以下','46〜70字','71字以上']); ttl = table('tl_bin', 'title_len')
out['total'] = dict(n=len(df), likes=int(df.like.sum()), comments=int(df.comment.sum()), zero_like=int((df.like==0).sum()),
                    days_sum=float(df.days.sum()), rate30=float(df.like.sum()/df.days.sum()*30))
# 順位相関（スキ/日 と 作りの各指標）と置換検定
df['rate'] = df.like/df.days
def perm_spearman(x, y, B_=10000):
    r0 = stats.spearmanr(x, y).statistic; c = 0
    for _ in range(B_):
        c += abs(stats.spearmanr(x, rng.permutation(y)).statistic) >= abs(r0)
    return float(r0), float((c+1)/(B_+1))
cor = {}
for v in ['n_img','chars','title_len','n_h2','n_tags','days']:
    cor[v] = perm_spearman(df[v].values, df.rate.values)
out['spearman_rate'] = cor
# ポアソン回帰（日数をオフセット）
m = smf.glm('like ~ n_img + I(chars/1000) + I(title_len/10)', data=df, family=sm.families.Poisson(), offset=np.log(df.days)).fit()
out['poisson'] = {k: [float(np.exp(m.params[k])), float(np.exp(m.conf_int().loc[k,0])), float(np.exp(m.conf_int().loc[k,1])), float(m.pvalues[k])] for k in m.params.index}
out['poisson_dispersion'] = float(m.pearson_chi2/m.df_resid)
# --- 頑健性 ---
rob = {}
# (1) 10月17日以降だけ（分析シリーズの期間）
d2 = df[df.period=='2026年10月17日以降']
rob['since1017_spearman_img'] = list(perm_spearman(d2.n_img.values, d2.rate.values, 5000))
m2 = smf.glm('like ~ n_img', data=d2, family=sm.families.Poisson(), offset=np.log(d2.days)).fit()
rob['since1017_poisson_img'] = [float(np.exp(m2.params['n_img'])), float(np.exp(m2.conf_int().loc['n_img',0])), float(np.exp(m2.conf_int().loc['n_img',1]))]
# (2) 指標を「スキが1つ以上ついたか」に（ロジスティック、日数の対数を入れる）
df['anyl'] = (df.like>0).astype(int); df['ldays'] = np.log(df.days)
try:
    m3 = smf.glm('anyl ~ n_img + ldays', data=df, family=sm.families.Binomial()).fit()
    rob['any_like_logit_img_OR'] = [float(np.exp(m3.params['n_img'])), float(np.exp(m3.conf_int().loc['n_img',0])), float(np.exp(m3.conf_int().loc['n_img',1]))]
except Exception as e: rob['any_like_logit_img_OR'] = str(e)
# (3) スキ＋コメント
df['eng'] = df.like + df.comment
m4 = smf.glm('eng ~ n_img + I(chars/1000) + I(title_len/10)', data=df, family=sm.families.Poisson(), offset=np.log(df.days)).fit()
rob['like_plus_comment_img_RR'] = [float(np.exp(m4.params['n_img'])), float(np.exp(m4.conf_int().loc['n_img',0])), float(np.exp(m4.conf_int().loc['n_img',1]))]
# (4) 日数の扱い：オフセットなし（累計スキそのもの）／日数の平方根
for nm, off in [('no_offset', None), ('sqrt_days', np.log(np.sqrt(df.days)))]:
    mm = smf.glm('like ~ n_img + I(chars/1000) + I(title_len/10)', data=df, family=sm.families.Poisson(), offset=off).fit()
    rob[f'{nm}_img_RR'] = [float(np.exp(mm.params['n_img'])), float(np.exp(mm.conf_int().loc['n_img',0])), float(np.exp(mm.conf_int().loc['n_img',1]))]
# (5) 1本ずつ外す（図の係数の幅）
loo = []
for i in df.index:
    dd = df.drop(i)
    mm = smf.glm('like ~ n_img + I(chars/1000) + I(title_len/10)', data=dd, family=sm.families.Poisson(), offset=np.log(dd.days)).fit()
    loo.append(float(np.exp(mm.params['n_img'])))
rob['loo_img_RR_range'] = [min(loo), max(loo)]
# (6) どれだけの差なら見分けられたか：2群（図5枚以上 vs 4枚以下）の率比、検出力80%の最小率比（シミュレーション）
g = df.n_img >= 5; T1, T0 = df.days[g].sum(), df.days[~g].sum(); base = df.like.sum()/df.days.sum()
def power(rr, sims=2000):
    hit = 0
    for _ in range(sims):
        l0 = base*(T0+T1)/(T0+rr*T1); k1 = rng.poisson(l0*rr*T1); k0 = rng.poisson(l0*T0); n = k1+k0
        if n == 0: continue
        p = T1*rr/(T1*rr+T0)  # not used
        pv = stats.binomtest(k1, n, T1/(T1+T0)).pvalue
        hit += pv < 0.05
    return hit/sims
mdr = None
for rr in [1.5,2,2.5,3,3.5,4,5,6,8,10]:
    pw = power(rr)
    if pw >= 0.8: mdr = rr; break
rob['min_detectable_RR_fig5plus'] = mdr
rob['obs_RR_fig5plus'] = [float((df.like[g].sum()/T1)/(df.like[~g].sum()/T0)) if df.like[~g].sum()>0 else None, int(df.like[g].sum()), float(T1), int(df.like[~g].sum()), float(T0)]
bt = stats.binomtest(int(df.like[g].sum()), int(df.like.sum()), T1/(T1+T0)); rob['fig5plus_binom_p'] = float(bt.pvalue)
out['robust'] = rob
json.dump(out, open(R/'summary.json','w'), ensure_ascii=False, indent=1)
for t in [tf, tfam, tp, ttl]: print(t.round(3).to_string()); print()
print(json.dumps(out, ensure_ascii=False, indent=1))
# (7) 同じ期間（10/17以降）の中で、図5枚以上と4枚以下を、日数の扱い3通りで比べる
rows = []
for nm, w in [('日数で割る', d2.days), ('日数の平方根で割る', np.sqrt(d2.days)), ('割らない（累計）', pd.Series(1.0, index=d2.index))]:
    g2 = d2.n_img >= 5
    a, b = d2.like[g2].sum(), d2.like[~g2].sum(); ta, tb = w[g2].sum(), w[~g2].sum()
    rr = (a/ta)/(b/tb) if b > 0 else float('nan')
    p = stats.binomtest(int(a), int(a+b), float(ta/(ta+tb))).pvalue
    rows.append(dict(exposure=nm, likes_5plus=int(a), n_5plus=int(g2.sum()), likes_other=int(b), n_other=int((~g2).sum()), rate_ratio=rr, binom_p=p))
pd.DataFrame(rows).to_csv(R/'exposure_sensitivity.csv', index=False); print(pd.DataFrame(rows).round(3).to_string())
