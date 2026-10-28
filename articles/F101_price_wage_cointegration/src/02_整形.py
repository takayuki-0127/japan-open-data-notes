"""02 整形：月次の物価・賃金を四半期平均の対数にそろえる。"""
import pandas as pd, numpy as np, pathlib
H = pathlib.Path(__file__).resolve().parents[1]
R = H/'data/raw'
# CPI
c = pd.read_csv(R/'cpi.csv', header=None, dtype=str)
codes = c.iloc[2].tolist()
body = c.iloc[6:].copy(); body = body[body[0].str.fullmatch(r'\d{6}')]
cpi = pd.DataFrame({'month': pd.to_datetime(body[0], format='%Y%m')})
for code, name in [('0001','cpi_all'),('0163','cpi_ex_rent'),('0161','cpi_core')]:
    cpi[name] = pd.to_numeric(body[codes.index(code)], errors='coerce').values
# wage
w = pd.read_csv(R/'wage.csv', dtype=str)
w = w[(w['種別']=='指数') & w['月'].str.fullmatch(r'\d\d') & (w['就業形態'].str.strip()=='0')]
wg = pd.DataFrame({'month': pd.to_datetime(w['年']+'-'+w['月']+'-01')})
for col, name in [('現金給与総額','wage_total'),('きまって支給する給与','wage_regular'),('総実労働時間','hours'),
                  ('常用雇用','employment'),('実質賃金指数（きまって支給する給与）','real_wage_regular_pub')]:
    wg[name] = pd.to_numeric(w[col], errors='coerce').values
m = cpi.merge(wg, on='month', how='outer').sort_values('month')
m['wage_hourly'] = m.wage_regular / m.hours * 100
m.to_csv(H/'data/monthly.csv', index=False)
# quarterly averages (only complete quarters)
m['q'] = m.month.dt.to_period('Q')
cols = ['cpi_all','cpi_ex_rent','cpi_core','wage_total','wage_regular','wage_hourly','hours','employment','real_wage_regular_pub']
g = m.groupby('q')[cols]
q = g.mean().where(g.count()==3)
gdp = pd.read_csv(R/'gdp_real_sa.csv'); gdp['q'] = pd.PeriodIndex(gdp.quarter, freq='Q')
q = q.join(gdp.set_index('q').gdp_real_sa)
q.index.name = 'quarter'; q = q.reset_index(); q['quarter'] = q.quarter.astype(str)
q.to_csv(H/'data/quarterly.csv', index=False)
print(q.dropna(subset=['cpi_ex_rent','wage_regular']).iloc[[0,-1]].T)
