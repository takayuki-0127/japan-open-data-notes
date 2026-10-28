"""Oaxaca–Blinder 分解（集計データ版）と、セルの組み合わせを使った組み替え（DFL型）による確認。"""
import json
import numpy as np, pandas as pd
from common import DATA, RES, AGES, AGE_MID, EDUS, TENS, TEN_MID

t1 = pd.read_csv(DATA/'cells_industry_size.csv')
t2 = pd.read_csv(DATA/'cells_tenure.csv')
tot = json.load(open(DATA/'published_totals.json', encoding='utf-8'))
out = {}
out['published'] = {'men_shoteinai': tot['男']['shoteinai'], 'women_shoteinai': tot['女']['shoteinai'],
                    'ratio': round(tot['女']['shoteinai']/tot['男']['shoteinai'], 4)}

# ---- 本体：産業(16)×規模(3)×学歴(6)×年齢(12) のセル（性別）
c = t1[(t1.industry!='産業計') & (t1['size']!='計')].copy()
c = c.dropna(subset=['shoteinai','workers','tenure','hours'])
c = c[(c.workers>0) & (c.shoteinai>0) & (c.hours>0)]
c['lw'] = np.log(c.shoteinai)
c['lw_hour'] = np.log(c.shoteinai/c.hours)
c['lw_kimatte'] = np.log(c.kimatte)
c['annual'] = 12*c.kimatte + c.bonus
c['lw_annual'] = np.log(c['annual'])
out['cells_main'] = {s:int((c.sex==s).sum()) for s in ['男','女']}

GROUPS = {'年齢': ['age'], '学歴': ['edu'], '勤続': ['tenure','tenure2'], '産業': ['industry'], '企業規模': ['size']}

def design(df, groups):
    X = pd.DataFrame(index=df.index); X['const'] = 1.0
    gmap = {}
    for g, vars_ in groups.items():
        cols=[]
        for v in vars_:
            if v=='tenure': X['tenure']=df.tenure; cols.append('tenure')
            elif v=='tenure2': X['tenure2']=df.tenure**2/100; cols.append('tenure2')
            else:
                dm = pd.get_dummies(df[v], prefix=v, drop_first=False).astype(float)
                base = sorted(dm.columns)[0]
                dm = dm.drop(columns=[base]); X = pd.concat([X, dm], axis=1); cols += list(dm.columns)
        gmap[g]=cols
    return X, gmap

def wls(X, y, w):
    W = np.sqrt(w.values)
    b, *_ = np.linalg.lstsq(X.values*W[:,None], y.values*W, rcond=None)
    return pd.Series(b, index=X.columns)

def oaxaca(df, ycol='lw', groups=GROUPS, ref='男', weighted=True):
    X, gmap = design(df, groups)
    w = df.workers if weighted else pd.Series(1.0, index=df.index)
    m, f = df.sex=='男', df.sex=='女'
    Xm = (X[m].mul(w[m],axis=0).sum()/w[m].sum()); Xf = (X[f].mul(w[f],axis=0).sum()/w[f].sum())
    ym = np.average(df.loc[m,ycol], weights=w[m]); yf = np.average(df.loc[f,ycol], weights=w[f])
    bm = wls(X[m], df.loc[m,ycol], w[m]); bf = wls(X[f], df.loc[f,ycol], w[f])
    if ref=='男': bref = bm
    elif ref=='女': bref = bf
    else:  # プール（性別ダミーつき、Neumark/Fortin 型）
        Xp = X.copy(); Xp['female'] = f.astype(float)
        bref = wls(Xp, df[ycol], w).drop('female')
    gap = ym - yf
    expl = ((Xm - Xf)*bref)
    det = {g: float(expl[cols].sum()) for g, cols in gmap.items()}
    E = float(expl.sum())
    return dict(gap=float(gap), explained=E, unexplained=float(gap-E), share_explained=float(E/gap), detail=det)

res = {}
res['基本（男性の係数）'] = oaxaca(c)
res['女性の係数'] = oaxaca(c, ref='女')
res['プールの係数'] = oaxaca(c, ref='プール')
res['時間あたり（所定内÷所定内時間）'] = oaxaca(c, ycol='lw_hour')
res['きまって支給（残業代込み）'] = oaxaca(c, ycol='lw_kimatte')
res['年間（12×きまって＋賞与）'] = oaxaca(c, ycol='lw_annual')
res['産業・規模を入れない'] = oaxaca(c, groups={k:v for k,v in GROUPS.items() if k in ['年齢','学歴','勤続']})
res['勤続を入れない'] = oaxaca(c, groups={k:v for k,v in GROUPS.items() if k!='勤続'})
res['セルを重みづけしない'] = oaxaca(c, weighted=False)
out['oaxaca'] = res

# 男女の係数の比較（主なもの）
X, gmap = design(c, GROUPS)
coefs = {}
for s in ['男','女']:
    m = c.sex==s
    coefs[s] = wls(X[m], c.loc[m,'lw'], c.workers[m])
cdf = pd.DataFrame(coefs); cdf.to_csv(RES/'coefficients.csv', encoding='utf-8')

# 平均の違い（説明変数）
def wmean(df, s, col): m=df.sex==s; return float(np.average(df.loc[m,col], weights=df.workers[m]))
out['means'] = {s:{'tenure':wmean(c,s,'tenure'),'hours':wmean(c,s,'hours'),'mean_age':wmean(c,s,'mean_age'),
                   'wage':wmean(c,s,'shoteinai')} for s in ['男','女']}
shares=[]
for v in ['edu','industry','size','age']:
    g = c.groupby(['sex',v]).workers.sum().unstack(0); g = g/g.sum()
    for k,row in g.iterrows(): shares.append(dict(var=v, level=k, men=row.get('男',0), women=row.get('女',0)))
pd.DataFrame(shares).to_csv(RES/'composition.csv', index=False, encoding='utf-8')

# ---- 年齢別の分解（年齢の中で、学歴・勤続・産業・規模）
byage=[]
for a in AGES:
    d = c[c.age==a]
    if (d.sex=='女').sum()<30: continue
    r = oaxaca(d, groups={k:v for k,v in GROUPS.items() if k!='年齢'})
    byage.append(dict(age=a, gap=r['gap'], explained=r['explained'], unexplained=r['unexplained'], **{'d_'+k:v for k,v in r['detail'].items()}))
pd.DataFrame(byage).to_csv(RES/'by_age.csv', index=False, encoding='utf-8')

# ---- ノンパラメトリックな組み替え（第2表：規模×学歴×年齢×勤続階級）
t = t2[t2['size']!='計'].dropna(subset=['shoteinai','workers'])
t = t[(t.workers>0)&(t.shoteinai>0)]
key = ['size','edu','age','tenure_class']
pm = t[t.sex=='男'].set_index(key); pf = t[t.sex=='女'].set_index(key)
common = pm.index.intersection(pf.index)
sm = pm.workers/pm.workers.sum(); sf = pf.workers/pf.workers.sum()
cover_m = float(sm.loc[common].sum()); cover_f = float(sf.loc[common].sum())
smc = sm.loc[common]/sm.loc[common].sum(); sfc = sf.loc[common]/sf.loc[common].sum()
lwm = np.log(pm.shoteinai.loc[common]); lwf = np.log(pf.shoteinai.loc[common])
gap = float((smc*lwm).sum() - (sfc*lwf).sum())
# 女性の賃金表で、男性の構成にしたら
cf_f = float((smc*lwf).sum()); cf_m = float((sfc*lwm).sum())
expl_f = cf_f - float((sfc*lwf).sum())   # 女性の賃金で評価
expl_m = float((smc*lwm).sum()) - cf_m   # 男性の賃金で評価
out['reweight'] = dict(cells=len(common), cover_men=cover_m, cover_women=cover_f, gap=gap,
                       explained_women_wages=expl_f, explained_men_wages=expl_m,
                       share_w=expl_f/gap, share_m=expl_m/gap)
# 同じ組み替えを、変数を1つずつ外して（どの区分の構成の違いが効くか）
contrib={}
for drop in key:
    k2=[x for x in key if x!=drop]
    gm = t[t.sex=='男'].groupby(k2).apply(lambda g: pd.Series({'w':g.workers.sum(),'lw':np.average(np.log(g.shoteinai),weights=g.workers)}), include_groups=False)
    gf = t[t.sex=='女'].groupby(k2).apply(lambda g: pd.Series({'w':g.workers.sum(),'lw':np.average(np.log(g.shoteinai),weights=g.workers)}), include_groups=False)
    cm = gm.index.intersection(gf.index)
    a_m = gm.w.loc[cm]/gm.w.loc[cm].sum(); a_f = gf.w.loc[cm]/gf.w.loc[cm].sum()
    e = float((a_m*gm.lw.loc[cm]).sum()-(a_f*gm.lw.loc[cm]).sum())
    contrib[drop]=e
out['reweight']['explained_without_each'] = contrib

# 年間で見た男女差の大きさ（円）
out['levels'] = {s: {'shoteinai_k': wmean(c,s,'shoteinai'), 'annual_k': wmean(c,s,'annual'), 'hourly_yen': 1000*wmean(c,s,'shoteinai')/wmean(c,s,'hours')} for s in ['男','女']}

json.dump(out, open(RES/'summary.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
rob = pd.DataFrame([dict(setting=k, gap=v['gap'], explained=v['explained'], unexplained=v['unexplained'], share_explained=v['share_explained'], **{'d_'+g:x for g,x in v['detail'].items()}) for k,v in res.items()])
rob.to_csv(RES/'robustness.csv', index=False, encoding='utf-8')
print(json.dumps({k:{kk:(round(vv,4) if isinstance(vv,float) else vv) for kk,vv in v.items()} for k,v in res.items()}, ensure_ascii=False, indent=0))
print(json.dumps(out['reweight'], ensure_ascii=False, indent=0)); print(out['means'], out['levels'], out['cells_main'])
print(pd.DataFrame(byage).round(3).to_string())
