"""4本（F01・F15・F17・F89）の答えを、手法ごとに「何を比べたか」「どこまで見えるか」で並べる"""
import numpy as np, pandas as pd, json
from scipy.stats import norm
from common import RAW, DATA, RES
est=pd.read_csv(RAW/'estimates_common_unit.csv'); C=json.load(open(RAW/'constants.json')); S=json.load(open(RAW/'F89_summary.json'))
def power(true,se,a=0.05):
    z=norm.ppf(1-a/2); return norm.cdf(abs(true)/se-z)+norm.cdf(-abs(true)/se-z)
def mde(se,a=0.05,pw=0.8): return (norm.ppf(1-a/2)+norm.ppf(pw))*se
emp=est[est.outcome=='emp'].copy()
main=emp[emp.main].copy()
pool=dict(study='F89',spec='3本の統合（固定効果）',est=S['emp_main']['fe'],se=S['emp_main']['fe_se'],design='メタ分析')
main=pd.concat([main,pd.DataFrame([pool])],ignore_index=True)
for t in (0.1,0.2,0.3): main[f'power_{t}']=power(t,main.se)
main['mde80']=mde(main.se); main['lo']=main.est-1.96*main.se; main['hi']=main.est+1.96*main.se
main['covers_lit_band']=(main.lo<=-0.3)|(main.hi>=0)  # 区間が文献の範囲 [-0.3,0] と重なる
main[['study','spec','design','est','se','lo','hi','mde80','power_0.1','power_0.2','power_0.3']].to_csv(RES/'main_power.csv',index=False,encoding='utf-8-sig')
# 記事の中のばらつき（仕様違い）と、記事の間のばらつき
w=emp.groupby('study').est.agg(['count','min','max','median','std']).reset_index()
w['range']=w['max']-w['min']; w.to_csv(RES/'within_study_spread.csv',index=False,encoding='utf-8-sig')
between=main[main.study!='F89'].est.std()
# 識別に使った変動と標準誤差
v=pd.read_csv(DATA/'variation.csv')
# 頑健性1：単位のそろえ方
r=[]
f01=est[(est.study=='F01')&(est.outcome=='emp')&est.main].iloc[0]
beta=f01.est*C['emp_rate_mean_2008_19']; beta_se=f01.se*C['emp_rate_mean_2008_19']
r.append(dict(check='F01 を2008–25年の就業率の平均で割る',est=beta/C['emp_rate_mean_2008_25'],se=beta_se/C['emp_rate_mean_2008_25']))
p17=pd.read_csv(RAW/'F17_panel.csv'); b19=p17.drop_duplicates('code').bite.median()
f17=est[(est.study=='F17')&(est.outcome=='emp')&est.main].iloc[0]
k=(1/C['bite_2015'])/(1/b19)
r.append(dict(check=f'F17 の1単位を bite の中央値（{b19:.3f}、平均は{C["bite_2015"]:.3f}）で換算',est=f17.est*k,se=f17.se*k))
# 頑健性2：見つけられる大きさの基準
for a,pw in [(0.05,0.9),(0.10,0.8)]:
    for _,m in main.iterrows(): r.append(dict(check=f'MDE（α={a}、検出力{int(pw*100)}%）・{m.study}',est=np.nan,se=m.se,mde=mde(m.se,a,pw)))
# 頑健性3：コロナ期を外した仕様だけで並べる
cv=emp[emp.spec.str.contains('2020–22|除く')]
for _,m in cv.iterrows(): r.append(dict(check=f'コロナ期を外す・{m.study}・{m.spec}',est=m.est,se=m.se,mde=mde(m.se)))
# 頑健性4：F01 の期間を2008–25年にしたときの変動
rob=pd.DataFrame(r); rob.to_csv(RES/'robustness.csv',index=False,encoding='utf-8-sig')
# F26 の過去記事 MDE
f26=pd.read_csv(RAW/'F26_past_flagships.csv')
out=dict(between_sd=between, within=w.set_index('study')[['count','min','max','range']].round(3).to_dict('index'),
 variation=v[['study','period','sd_total_pct','sd_resid_pct','sd_resid_trend_pct']].round(3).to_dict('records'),
 main=main[['study','est','se','lo','hi','mde80','power_0.1','power_0.2','power_0.3']].round(3).to_dict('records'),
 robustness=rob.round(3).to_dict('records'), bite_median=b19,
 needed_like_f01_for_0p1=S.get('studies_needed'))
json.dump(out,open(RES/'summary.json','w'),ensure_ascii=False,indent=1,default=float)
print(main[['study','est','se','lo','hi','mde80','power_0.1','power_0.2','power_0.3']].round(3).to_string()); print(w.round(3).to_string()); print('between sd',round(between,3)); print(rob.round(3).to_string())
