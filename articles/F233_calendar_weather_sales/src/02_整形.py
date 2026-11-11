"""02 整形：必要な系列だけを取り出し、カレンダーの変数を作る"""
import pandas as pd, numpy as np, jpholiday, datetime as dt
from pathlib import Path
B = Path(__file__).resolve().parents[1]
r = pd.read_csv(B/'data/raw/f135_retail_monthly.csv')
SEL = [('百貨店','合計','既存店'),('スーパー','合計','既存店'),('コンビニ','合計','販売額'),
       ('ドラッグストア','商品販売額','販売額'),('ホームセンター','商品販売額','販売額'),('家電大型専門店','商品販売額','販売額')]
out = []
for g,it,ind in SEL:
    x = r[(r.業態==g)&(r.地域=='全国')&(r.品目==it)&(r.指標==ind)][['ym','値']].copy()
    x['業態']=g; x['指標']=ind; out.append(x)
sales = pd.concat(out); sales = sales[sales.ym>='2011-01']
sales.to_csv(B/'data/sales_monthly.csv', index=False)

# カレンダー（2011-01〜2027-12。2027年は来年の補正表に使う）
days = pd.date_range('2011-01-01','2027-12-31',freq='D')
cal = pd.DataFrame({'date':days})
cal['hol'] = cal.date.map(lambda d: jpholiday.is_holiday(d.date()))
cal['dow'] = cal.date.dt.dayofweek  # 0=月
cal['off'] = (cal.dow>=5)|cal.hol
# 年末年始（12/31〜1/3）も休みとして扱う
md = cal.date.dt.strftime('%m-%d')
cal['off2'] = cal.off | md.isin(['12-31','01-01','01-02','01-03'])
# 3日以上続く休み（連休）の日
run = (cal.off2 != cal.off2.shift()).cumsum()
rl = cal.groupby(run).off2.transform('size')
cal['renkyu'] = cal.off2 & (rl>=3)
cal['ym'] = cal.date.dt.strftime('%Y-%m')
g = cal.groupby('ym')
m = pd.DataFrame({
  'n_days': g.size(),
  'n_sat': g.apply(lambda d: ((d.dow==5)&~d.hol).sum()),
  'n_sun': g.apply(lambda d: ((d.dow==6)|((d.dow==5)&d.hol)).sum()),  # 日曜と土曜祝日
  'n_hol_wd': g.apply(lambda d: (d.hol&(d.dow<5)).sum()),            # 平日の祝日（振替含む）
  'n_off': g.off.sum(),
  'n_renkyu': g.renkyu.sum(),
}).reset_index()
for k in range(7):
    m[f'dow{k}'] = g.apply(lambda d,k=k: (d.dow==k).sum()).values
m.to_csv(B/'data/calendar_monthly.csv', index=False)
cal[['date','dow','hol','off2','renkyu']].to_csv(B/'data/calendar_daily.csv.gz', index=False)

w = pd.read_csv(B/'data/raw/f135_weather_monthly.csv')
wn = w.groupby('ym')[['rain1','rain10','ptot','tmean','rain1_off']].mean().reset_index()
w3 = w[w.地点.isin(['東京','名古屋','大阪'])].groupby('ym')[['rain1','tmean']].mean().add_suffix('_3c').reset_index()
wn.merge(w3,on='ym').to_csv(B/'data/weather_national.csv', index=False)
print(sales.groupby('業態').ym.agg(['min','max','size'])); print(m.tail(3)); print(wn.tail(2))
