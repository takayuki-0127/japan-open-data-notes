"""03 分析：物価と賃金の共和分（Engle–Granger・Johansen）と誤差修正モデル。
主な系列：消費者物価（持家の帰属家賃を除く総合）と、毎月勤労統計の「きまって支給する給与」指数（5人以上・調査産業計）。
四半期平均の対数をとり、STL（周期4）で季節成分を除いてから検定する。"""
import warnings; warnings.filterwarnings('ignore')
import pandas as pd, numpy as np, json, pathlib
from statsmodels.tsa.stattools import coint, adfuller, kpss
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.vector_ar.vecm import coint_johansen, VECM
import statsmodels.api as sm
np.random.seed(0)
H = pathlib.Path(__file__).resolve().parents[1]; RES = H/'results'
q = pd.read_csv(H/'data/quarterly.csv')
q['y'] = q.quarter.str[:4].astype(int)

def sa(s):
    """対数系列の季節成分を STL で除く（欠測のない区間だけ）"""
    s = np.log(s); ok = s.notna()
    out = s.copy(); out[ok] = s[ok] - STL(s[ok].values, period=4, robust=True).fit().seasonal
    return out
for c in ['cpi_ex_rent','cpi_all','cpi_core','wage_regular','wage_total','wage_hourly','employment','hours']:
    q['l_'+c] = sa(q[c]); q['n_'+c] = np.log(q[c])
q['l_gdp'] = np.log(q.gdp_real_sa)
# 労働生産性（近似）：実質GDP ÷（毎勤の常用雇用指数 × 総実労働時間指数）
q['l_prod'] = q.l_gdp - q.l_employment - q.l_hours
q.to_csv(H/'data/quarterly_sa.csv', index=False)

PERIODS = {'1981–1995':(1981,1995),'1996–2026':(1996,2026),'1996–2019':(1996,2019),'2013–2026':(2013,2026),'1970–2026（参考）':(1970,2026)}
def sub(a,b,cols): return q[(q.y>=a)&(q.y<=b)].dropna(subset=cols)

# 1 単位根
rows=[]
for name,(a,b) in PERIODS.items():
    s=sub(a,b,['l_wage_regular','l_cpi_ex_rent'])
    for v,lab in [('l_wage_regular','賃金'),('l_cpi_ex_rent','物価')]:
        x=s[v]
        rows.append(dict(期間=name,系列=lab,n=len(x),
            ADF水準_定数トレンド_p=adfuller(x,regression='ct',autolag='AIC')[1],
            ADF差分_定数_p=adfuller(x.diff().dropna(),regression='c',autolag='AIC')[1],
            KPSS差分_p=kpss(x.diff().dropna(),regression='c',nlags='auto')[1]))
    r=s.l_wage_regular-s.l_cpi_ex_rent
    rows.append(dict(期間=name,系列='実質賃金（賃金−物価）',n=len(r),ADF水準_定数トレンド_p=adfuller(r,regression='ct',autolag='AIC')[1],
        ADF差分_定数_p=adfuller(r.diff().dropna(),regression='c',autolag='AIC')[1],ADF水準_定数_p=adfuller(r,regression='c',autolag='AIC')[1]))
ur=pd.DataFrame(rows); ur.to_csv(RES/'unit_root.csv',index=False)

# 2 Engle–Granger（賃金・物価の系列とトレンドの入れ方を変える）
WAGES={'きまって支給する給与':'l_wage_regular','現金給与総額':'l_wage_total','時間あたり（きまって÷総実労働時間）':'l_wage_hourly'}
CPIS={'持家の帰属家賃を除く総合':'l_cpi_ex_rent','総合':'l_cpi_all','生鮮食品を除く総合':'l_cpi_core'}
eg=[]
for name,(a,b) in PERIODS.items():
    for wl,wv in WAGES.items():
        for cl,cv in CPIS.items():
            s=sub(a,b,[wv,cv])
            for tr,tl in [('c','定数'),('ct','定数＋トレンド')]:
                t,p,_=coint(s[wv],s[cv],trend=tr,autolag='aic',maxlag=8)
                X=sm.add_constant(s[cv]) if tr=='c' else sm.add_constant(np.column_stack([s[cv],np.arange(len(s))]))
                beta=sm.OLS(s[wv].values,X).fit().params[1]
                eg.append(dict(期間=name,賃金=wl,物価=cl,トレンド=tl,n=len(s),EG統計量=t,p値=p,物価の係数=beta))
eg=pd.DataFrame(eg); eg.to_csv(RES/'engle_granger.csv',index=False)

# 3 Johansen（ラグと確定項を変える）
jo=[]
for name,(a,b) in PERIODS.items():
    s=sub(a,b,['l_wage_regular','l_cpi_ex_rent'])
    for k in [1,2,4,6]:
        for det,dl in [(0,'定数'),(1,'トレンド')]:
            j=coint_johansen(s[['l_wage_regular','l_cpi_ex_rent']].values,det,k)
            jo.append(dict(期間=name,ラグ=k,確定項=dl,n=len(s),trace_r0=j.lr1[0],cv95_r0=j.cvt[0,1],trace_r1=j.lr1[1],cv95_r1=j.cvt[1,1],
                           maxeig_r0=j.lr2[0],mcv95_r0=j.cvm[0,1],
                           ランク=int((j.lr1[0]>j.cvt[0,1]) + ((j.lr1[0]>j.cvt[0,1]) and (j.lr1[1]>j.cvt[1,1]))),
                           beta_物価=float(np.real(-j.evec[1,0]/j.evec[0,0]))))
jo=pd.DataFrame(jo); jo.to_csv(RES/'johansen.csv',index=False)

# 4 誤差修正モデル（EG の2段階：長期の関係からのずれ ec を使う）
def ecm(s, wv='l_wage_regular', cv='l_cpi_ex_rent', lags=2, trend=False):
    X=sm.add_constant(np.column_stack([s[cv]]+([np.arange(len(s))] if trend else [])))
    lr=sm.OLS(s[wv].values,X).fit(); ec=pd.Series(lr.resid,index=s.index)
    d=pd.DataFrame({'dw':s[wv].diff(),'dp':s[cv].diff(),'ec1':ec.shift(1)})
    for L in range(1,lags+1): d[f'dw{L}']=d.dw.shift(L); d[f'dp{L}']=d.dp.shift(L)
    d=d.dropna(); out={}
    for dep in ['dw','dp']:
        xs=['ec1']+[c for c in d if c.startswith(('dw','dp')) and c[-1].isdigit()]
        f=sm.OLS(d[dep],sm.add_constant(d[xs])).fit(cov_type='HAC',cov_kwds={'maxlags':4})
        out[dep]=dict(alpha=f.params['ec1'],se=f.bse['ec1'],t=f.tvalues['ec1'],p=f.pvalues['ec1'])
    speed=out['dw']['alpha']-lr.params[1]*out['dp']['alpha']   # ずれ全体が1期に縮む割合（短期の項を除いた近似）
    hl=np.log(0.5)/np.log(1+speed) if -2<speed<0 else np.nan
    # ずれそのものの AR(1) による半減期（参考）
    ar=sm.OLS(ec.values[1:],sm.add_constant(ec.values[:-1])).fit().params[1]
    return dict(beta=lr.params[1],alpha_w=out['dw']['alpha'],alpha_w_t=out['dw']['t'],alpha_w_p=out['dw']['p'],
                alpha_p=out['dp']['alpha'],alpha_p_t=out['dp']['t'],alpha_p_p=out['dp']['p'],
                speed=speed,half_life_q=hl,ec_ar1=ar,ec_half_life_q=np.log(0.5)/np.log(ar) if 0<ar<1 else np.nan), ec
ecms=[]; ecs={}
for name,(a,b) in PERIODS.items():
    s=sub(a,b,['l_wage_regular','l_cpi_ex_rent'])
    for lags in [1,2,4]:
        for tr in [False,True]:
            r,ec=ecm(s,lags=lags,trend=tr); r.update(期間=name,ラグ=lags,トレンド='あり' if tr else 'なし',n=len(s)); ecms.append(r)
            if lags==2 and not tr: ecs[name]=ec
ecms=pd.DataFrame(ecms); ecms.to_csv(RES/'ecm.csv',index=False)
pd.DataFrame({k:v for k,v in ecs.items()}).assign(quarter=q.quarter).to_csv(RES/'ec_series.csv',index=False)

# 5 VECM（Johansen、ランク1、ラグ2、定数は共和分の外）で調整の速さ
vec=[]
for name in ['1981–1995','1996–2026','2013–2026']:
    a,b=PERIODS[name]; s=sub(a,b,['l_wage_regular','l_cpi_ex_rent'])
    m=VECM(s[['l_wage_regular','l_cpi_ex_rent']].values,k_ar_diff=2,coint_rank=1,deterministic='co').fit()
    vec.append(dict(期間=name,beta_物価=-m.beta[1,0]/m.beta[0,0],alpha_賃金=m.alpha[0,0]*m.beta[0,0],alpha_賃金_t=m.tvalues_alpha[0,0],
                    alpha_物価=m.alpha[1,0]*m.beta[0,0],alpha_物価_t=m.tvalues_alpha[1,0]))
pd.DataFrame(vec).to_csv(RES/'vecm.csv',index=False)

# 6 生産性を入れた3変数（1994–2026）：賃金＝物価＋生産性 の関係はあるか
pr=[]
for name,(a,b) in {'1994–2026':(1994,2026),'1994–2019':(1994,2019),'2013–2026':(2013,2026)}.items():
    s=sub(a,b,['l_wage_hourly','l_cpi_ex_rent','l_prod'])
    for k in [1,2,4]:
        j=coint_johansen(s[['l_wage_hourly','l_cpi_ex_rent','l_prod']].values,0,k)
        pr.append(dict(期間=name,ラグ=k,n=len(s),trace_r0=j.lr1[0],cv95_r0=j.cvt[0,1],trace_r1=j.lr1[1],cv95_r1=j.cvt[1,1],
                       ランク=int(sum(np.cumprod(j.lr1>j.cvt[:,1]))),
                       係数_物価=float(np.real(-j.evec[1,0]/j.evec[0,0])),係数_生産性=float(np.real(-j.evec[2,0]/j.evec[0,0]))))
    # 労働分配率に近い量（時間賃金−物価−生産性）が定常か
    ls=s.l_wage_hourly-s.l_cpi_ex_rent-s.l_prod
    t,p,_=coint(s.l_wage_hourly-s.l_cpi_ex_rent, s.l_prod, trend='c',autolag='aic')
    pr.append(dict(期間=name,ラグ='EG(実質時間賃金~生産性)',n=len(s),trace_r0=t,
                   ランク=None,EG_p=p,係数_生産性=sm.OLS((s.l_wage_hourly-s.l_cpi_ex_rent).values,sm.add_constant(s.l_prod.values)).fit().params[1],
                   分配率近似_ADF_p=adfuller(ls,regression='c',autolag='AIC')[1]))
pd.DataFrame(pr).to_csv(RES/'productivity_3var.csv',index=False)

# 7 15年の窓をずらした EG の p 値
roll=[]
idx=q.dropna(subset=['l_wage_regular','l_cpi_ex_rent']).reset_index(drop=True)
W=60
for i in range(0,len(idx)-W+1,2):
    s=idx.iloc[i:i+W]
    p_c=coint(s.l_wage_regular,s.l_cpi_ex_rent,trend='c',autolag='aic',maxlag=6)[1]
    p_ct=coint(s.l_wage_regular,s.l_cpi_ex_rent,trend='ct',autolag='aic',maxlag=6)[1]
    roll.append(dict(start=s.quarter.iloc[0],end=s.quarter.iloc[-1],p_const=p_c,p_trend=p_ct))
pd.DataFrame(roll).to_csv(RES/'rolling_eg.csv',index=False)

# 8 累積の伸び（1996Q1=100 からの）
base=q[q.quarter=='1996Q1'].iloc[0]
g=q[q.y>=1996][['quarter']].copy()
for c in ['wage_regular','cpi_ex_rent']: g[c]=np.exp(q.loc[g.index,'l_'+c]-base['l_'+c])*100
g.to_csv(RES/'growth_since_1996.csv',index=False)
# 9 2013年以降の関係は消費税の引き上げで作られたものか、始まりの年でどう変わるか
from statsmodels.tsa.adfvalues import mackinnonp
rb=[]
def eg_manual(s, extra):
    X=sm.add_constant(np.column_stack([s.l_cpi_ex_rent]+[s[c] for c in extra]))
    f=sm.OLS(s.l_wage_regular.values,X).fit(); r=adfuller(f.resid,regression='n',autolag='AIC')
    return f.params[1], r[0], mackinnonp(r[0],regression='c',N=2+len(extra))
q['tax14']=(q.quarter>='2014Q2').astype(int); q['tax19']=(q.quarter>='2019Q4').astype(int)
for a,b,lab in [(2013,2026,'2013–2026'),(2013,2019,'2013–2019'),(2015,2026,'2015–2026（2014年の引き上げを外す）')]:
    s=sub(a,b,['l_wage_regular','l_cpi_ex_rent'])
    for ex,el in [([],'なし'),([c for c in ['tax14','tax19'] if s[c].nunique()>1],'消費税の段差ダミー')]:
        bt,t,pv=eg_manual(s,ex); rb.append(dict(検証='消費税',期間=lab,条件=el,n=len(s),物価の係数=bt,統計量=t,p値_近似=pv))
for a in range(2009,2018):
    s=sub(a,2026,['l_wage_regular','l_cpi_ex_rent'])
    t,pv,_=coint(s.l_wage_regular,s.l_cpi_ex_rent,trend='c',autolag='aic',maxlag=8)
    r,_=ecm(s,lags=2)
    rb.append(dict(検証='始まりの年',期間=f'{a}–2026',条件='定数',n=len(s),物価の係数=r['beta'],統計量=t,p値_近似=pv,alpha_賃金=r['alpha_w'],alpha_賃金_p=r['alpha_w_p'],alpha_物価=r['alpha_p'],alpha_物価_p=r['alpha_p_p'],半減期_四半期=r['half_life_q']))
# ECM に消費税の四半期（2014Q2・2019Q4）のダミーを足す
s=sub(2013,2026,['l_wage_regular','l_cpi_ex_rent']).copy()
X=sm.add_constant(s.l_cpi_ex_rent.values); lr=sm.OLS(s.l_wage_regular.values,X).fit(); ec=pd.Series(lr.resid,index=s.index)
d=pd.DataFrame({'dw':s.l_wage_regular.diff(),'dp':s.l_cpi_ex_rent.diff(),'ec1':ec.shift(1),
                'd14':(s.quarter=='2014Q2').astype(int),'d19':(s.quarter=='2019Q4').astype(int)})
for L in [1,2]: d[f'dw{L}']=d.dw.shift(L); d[f'dp{L}']=d.dp.shift(L)
d=d.dropna()
for dep in ['dw','dp']:
    f=sm.OLS(d[dep],sm.add_constant(d.drop(columns=['dw','dp']))).fit(cov_type='HAC',cov_kwds={'maxlags':4})
    rb.append(dict(検証='ECMに消費税ダミー',期間='2013–2026',条件=dep,n=len(d),alpha=f.params['ec1'],alpha_p=f.pvalues['ec1']))
rb=pd.DataFrame(rb); rb.to_csv(RES/'robust_2013.csv',index=False); print(rb.round(3).to_string())
# 10 2013–2026 で賃金・物価の系列を変えたとき
print(eg[eg.期間=='2013–2026'].round(3).to_string())
print(ur.round(3).to_string()); print(eg[(eg.賃金=='きまって支給する給与')&(eg.物価=='持家の帰属家賃を除く総合')].round(3).to_string())
print(jo.round(2).to_string()); print(ecms.round(3).to_string()); print(pd.DataFrame(vec).round(3)); print(pd.DataFrame(pr).round(3).to_string())
