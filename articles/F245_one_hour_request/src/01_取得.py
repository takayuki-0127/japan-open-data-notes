# データは新しく取得していない。F233（articles/F233_calendar_weather_sales/data/raw/f135_retail_monthly.csv、
# 経済産業省「商業動態統計」）からドラッグストアの販売額（全国・地域・品目）を切り出した。
import pandas as pd, sys
src = sys.argv[1] if len(sys.argv) > 1 else '../F233_calendar_weather_sales/data/raw/f135_retail_monthly.csv'
d = pd.read_csv(src); x = d[(d.業態 == 'ドラッグストア') & (d.指標 == '販売額')]
x.to_csv('data/drugstore_monthly.csv', index=False); print(x.shape)
