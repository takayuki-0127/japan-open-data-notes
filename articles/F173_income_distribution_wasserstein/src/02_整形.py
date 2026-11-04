# F173 02 整形：F101 の月次 CPI から、暦年平均（1985〜2024年）を作る
# 使い方：python src/02_整形.py <F101 の data/monthly.csv>
import sys, os
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '..', 'F101_price_wage_cointegration', 'data', 'monthly.csv')
d = pd.read_csv(src, parse_dates=['month']); d['year'] = d.month.dt.year
a = d[(d.year >= 1985) & (d.year <= 2024)].groupby('year')[['cpi_all', 'cpi_ex_rent']].mean().round(3)
assert (d[(d.year >= 1985) & (d.year <= 2024)].groupby('year').size() == 12).all()
a.to_csv(os.path.join(ROOT, 'data', 'cpi_annual.csv'))
print(a.tail())
