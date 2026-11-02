"""各記事で「最低賃金がどれだけばらついていたか（識別に使える変動）」を同じ物差し（log最低賃金、%）で測る"""
import numpy as np, pandas as pd, json
from common import RAW, DATA
def resid(df,col,fe,trend=False):
    d=df.copy(); y=d[col].astype(float)
    X=pd.get_dummies(d[fe].astype(str),drop_first=False).astype(float)
    if trend:
        for c in sorted(d['code'].unique()):
            X[f't{c}']=((d['code']==c)*(d['year']-d['year'].mean())).astype(float)
    b,*_=np.linalg.lstsq(X.values,y.values,rcond=None)
    return y.values-X.values@b
rows=[]
p=pd.read_csv(RAW/'F01_panel.csv')
for per,(a,bb) in {'2008–2019':(2008,2019),'2008–2025':(2008,2025)}.items():
    d=p[(p.year>=a)&(p.year<=bb)].reset_index(drop=True)
    tot=d.log_mw.std()*100
    r=resid(d,'log_mw',['code','year'])
    rt=resid(d,'log_mw',['code','year'],trend=True)
    ry=resid(d,'emp_rate',['code','year'])
    rows.append(dict(study='F01',design='県×年の固定効果',period=per,n=len(d),sd_total_pct=tot,sd_resid_pct=r.std()*100,sd_resid_trend_pct=rt.std()*100,sd_y_resid=ry.std()))
# F15: 接するペアの中の Δlog最低賃金（2015→20年度）の差
m=pd.read_csv(RAW/'F15_muni.csv'); pr=pd.read_csv(RAW/'F15_pairs.csv')
dm=m.set_index('code').dlog_mw
for kind in ['touch','all']:
    q=pr if kind=='all' else pr[pr.kind=='touch']
    q=q[q.code_a.isin(dm.index)&q.code_b.isin(dm.index)]
    gap=(dm.loc[q.code_a].values-dm.loc[q.code_b].values)*100
    rows.append(dict(study='F15',design='県境ペアの差（2015→20年度の上昇率の差）',period='2016→2021' if kind=='touch' else '2016→2021（20km以内も）',n=len(q),sd_total_pct=m.drop_duplicates('pref').dlog_mw.std()*100,sd_resid_pct=np.std(gap),sd_resid_trend_pct=np.nan,sd_y_resid=np.nan,max_abs_gap_pct=np.abs(gap).max()))
# F17: 処置＝前年からの最低賃金の上昇率（%）を年で中心化したもの
f=pd.read_csv(RAW/'F17_panel.csv')
f=f[~f.year.isin([2020,2021,2022])]
tr=f.treat_pct
r=tr-f.groupby('year').treat_pct.transform('mean')
rows.append(dict(study='F17',design='前年差＋機械学習で調整（上昇率の年平均からのずれ）',period='2010–2025（2020–22除く）',n=len(f),sd_total_pct=tr.std(),sd_resid_pct=r.std(),sd_resid_trend_pct=np.nan,sd_y_resid=np.nan))
v=pd.DataFrame(rows); v.to_csv(DATA/'variation.csv',index=False,encoding='utf-8-sig'); print(v.round(3).to_string())
