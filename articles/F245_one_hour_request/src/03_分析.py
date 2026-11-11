# F245 1時間で答える：架空の依頼「あおばドラッグ（架空）の8月は前年同月比−1.0%。業界も落ちている？うちだけ？年間の着地は？」
import pandas as pd, numpy as np, json, warnings, os
warnings.filterwarnings('ignore')
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
B=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d=pd.read_csv(f'{B}/data/drugstore_monthly.csv'); d['ym']=pd.PeriodIndex(d.ym,freq='M')
CH=-1.0  # 架空のチェーンの8月の前年同月比（依頼文に書かれた数字。実在の会社ではない）
CHAIN_MIX={'調剤医薬品':0.02,'ＯＴＣ医薬品':0.14,'ヘルスケア用品（衛生用品）・介護・ベビー':0.09,'健康食品':0.04,'ビューティケア（化粧品・小物）':0.22,'トイレタリー':0.11,'家庭用品・日用消耗品・ペット用品':0.13,'食品':0.22,'その他':0.03}  # 架空の品目構成
R={}
nat=d[(d.地域=='全国')&(d.品目=='商品販売額')].set_index('ym').値.sort_index()
yoy=(nat/nat.shift(12)-1)*100
R['A_industry_aug_yoy']=round(yoy['2026-08'],2)
reg=d[(d.品目=='販売額')].pivot(index='ym',columns='地域',values='値').sort_index()
ryoy=(reg/reg.shift(12)-1)*100
R['A_region_aug_yoy']={k:round(v,2) for k,v in ryoy.loc['2026-08'].items()}
R['A_industry_3m_yoy']=round((nat['2026-06':'2026-08'].sum()/nat['2025-06':'2025-08'].sum()-1)*100,2)
R['A_kanto_3m_yoy']=round((reg['関東']['2026-06':'2026-08'].sum()/reg['関東']['2025-06':'2025-08'].sum()-1)*100,2)
# 24か月の推移
out=pd.DataFrame({'全国':yoy,'関東':ryoy['関東']}).loc['2024-09':'2026-08']; out.index=out.index.astype(str); out.round(2).to_csv(f'{B}/results/A_yoy_recent.csv')
# 品目別の寄与（8月）
it=d[(d.地域=='全国')&(~d.品目.isin(['商品販売額']))].pivot(index='ym',columns='品目',values='値').sort_index()
a,b=it.loc['2026-08'],it.loc['2025-08']; tot=b.sum()
con=((a-b)/tot*100).sort_values(); g=(a/b-1)*100
pd.DataFrame({'寄与_pt':con.round(3),'伸び率_%':g.round(2),'構成比_2025':(b/tot).round(3),'架空チェーンの構成比':pd.Series(CHAIN_MIX)}).to_csv(f'{B}/results/B_item_contrib_aug.csv')
R['B_item_contrib']={k:round(v,2) for k,v in con.items()}; R['B_item_growth']={k:round(v,1) for k,v in g.items()}
R['B_items_sum_vs_total']=round(con.sum()-yoy['2026-08'],3)
# 比べ方を4通り
mixg=sum(CHAIN_MIX[k]*g[k] for k in CHAIN_MIX)
exrx=((a.drop('調剤医薬品').sum()/b.drop('調剤医薬品').sum())-1)*100
c=pd.read_csv(f'{B}/data/f233_monthly_contrib.csv'); c=c[(c.業態=='ドラッグストア')&(c.ym=='2026-08')].iloc[0]
comp={'業界全体（全国）':yoy['2026-08'],'関東':ryoy['関東']['2026-08'],'調剤を除く':exrx,'架空チェーンの品目構成に合わせる':mixg,'カレンダー・天気を除く（F233）':c['調整後']}
R['C_comparisons']={k:round(v,2) for k,v in comp.items()}; R['C_calendar']=round(c['カレンダー寄与'],2); R['C_weather']=round(c['天気寄与'],2)
R['C_gap_vs_chain']={k:round(CH-v,2) for k,v in comp.items()}
# 構成比を変えたときの幅（頑健性）：チェーンの構成をランダムに±50%揺らす
rng=np.random.default_rng(245); sims=[]
for _ in range(2000):
    w=np.array([CHAIN_MIX[k] for k in CHAIN_MIX])*rng.uniform(0.5,1.5,len(CHAIN_MIX)); w/=w.sum()
    sims.append(float(np.dot(w,[g[k] for k in CHAIN_MIX])))
R['C_mix_range_5_95']=[round(np.percentile(sims,5),2),round(np.percentile(sims,95),2)]
# 年間の着地（業界）：9〜12月を予測
tr=nat[:'2026-08']; tr_cov=tr.copy()
def fc(model,y):
    if model=='SARIMA': m=SARIMAX(np.log(y),order=(1,1,1),seasonal_order=(0,1,1,12)).fit(disp=False,maxiter=60); p=np.exp(m.get_forecast(4).predicted_mean.values)
    elif model=='ETS': m=ExponentialSmoothing(np.log(y),trend='add',seasonal='add',seasonal_periods=12).fit(); p=np.exp(m.forecast(4).values)
    else: p=y[-12:-8].values*(y[-12:].sum()/y[-24:-12].sum())  # 季節ナイーブ＋直近1年の伸び
    return p
y25=nat['2025-01':'2025-12'].sum(); jan_aug=nat['2026-01':'2026-08'].sum(); rows=[]
for mdl in ['SARIMA','ETS','季節ナイーブ']:
    for start in ['2014-01','2018-01','2022-01']:
        y=tr[start:]; y.index=y.index.to_timestamp()
        try: p=fc(mdl,y)
        except Exception as e: continue
        rows.append({'モデル':mdl,'学習の始まり':start,'9_12月合計':p.sum(),'2026年の着地_前年比':(jan_aug+p.sum())/y25*100-100})
L=pd.DataFrame(rows); L.round(3).to_csv(f'{B}/results/D_annual_landing.csv',index=False)
R['D_landing']=L.groupby('モデル')['2026年の着地_前年比'].agg(['min','max']).round(2).to_dict('index')
R['D_landing_main']=round(float(L[(L.モデル=='SARIMA')&(L.学習の始まり=='2014-01')]['2026年の着地_前年比'].iloc[0]),2)
R['D_jan_aug_yoy']=round((jan_aug/nat['2025-01':'2025-08'].sum()-1)*100,2)
# 4か月先の外れの目安：F231 の年間合計の外れ（1年目 SARIMA 1.63%）を残り4か月分に按分
R['D_err_note']='F231の年間合計の外れ（1年目SARIMA 1.63%）。残り4か月だけを予測するので、外れの目安は年間で約0.5%（推測）'
# 過去の8月に「業界との差−4ポイント」がどれだけ珍しいか：地域間の8月前年比のばらつき
sd=ryoy.loc[[p for p in ryoy.index if p.month==8 and p.year>=2016]].std(axis=1)
R['E_region_sd_aug']={str(k.year):round(v,2) for k,v in sd.items()}
json.dump(R,open(f'{B}/results/main.json','w'),ensure_ascii=False,indent=1)
print(json.dumps(R,ensure_ascii=False,indent=1))
