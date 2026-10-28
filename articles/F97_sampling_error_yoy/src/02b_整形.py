"""家計調査（月）と完全失業率を、分析に使う形にそろえる。"""
import pandas as pd
from common import DATA, RAW, CATS
ITEMS18 = pd.read_csv(DATA/'kakei_se_items_2018.csv').item.tolist()
d = pd.read_csv(RAW/'kakei_monthly_long_F11.csv')
d = d[d.item.isin(set(CATS)|set(ITEMS18))][['date','item','amount','nom','real']]
d.to_csv(DATA/'kakei_monthly.csv', index=False)
# 年平均（月の単純平均）。2018・2019年は家計簿の改正で名目の水準がそのままつながらないので、年の増減率の計算から外す
d['year'] = d.date.str[:4].astype(int)
a = d.groupby(['item','year']).agg(amount=('amount','mean'), n=('amount','size')).reset_index()
a = a[a.n == 12]
a['yoy'] = a.groupby('item').amount.pct_change()*100
a.loc[a.year.isin([2018,2019]), 'yoy'] = float('nan')
a.to_csv(DATA/'kakei_annual.csv', index=False)
u = pd.read_csv(RAW/'monthly_levels_F18.csv')[['month','完全失業率']].dropna()
u.columns = ['month','urate']; u.to_csv(DATA/'lfs_urate_sa.csv', index=False)
print(d.item.nunique(), d.date.min(), d.date.max(), a.year.max(), len(u), u.month.max())
