"""家計調査 第4-3表（2020・2025年）と F113・F209 の写しから品目のパネルを作る。"""
import openpyxl, pandas as pd, numpy as np, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
SHEETS = {'exp': '二人（支出金額）', 'q': '二人（購入数量）', 'p': '二人（平均価格）'}
COLS = ['avg', 'q1', 'q2', 'q3', 'q4', 'q5']
rows = []
for y in (2020, 2025):
    wb = openpyxl.load_workbook(f'data/raw/y{y}_43.xlsx', read_only=True)
    for var, sh in SHEETS.items():
        ws = wb[sh]
        cur_big = None
        for r in ws.iter_rows(values_only=True):
            if r[0] is None or not str(r[0]).startswith('403'):
                continue
            code, name, unit = r[10], r[11], r[12]
            if code is None or name is None:
                continue
            if str(r[9]).strip() == '2' and not str(code).strip().startswith('0'):
                cur_big = str(name).strip()
            vals = r[13:19]
            for c, v in zip(COLS, vals):
                try:
                    v = float(str(v).replace(',', ''))
                except Exception:
                    v = np.nan
                rows.append(dict(year=y, var=var, code=str(code).strip(), level=r[9], name=str(name).strip(), unit=unit, grp=c, val=v, seq=r[7], big=cur_big))
d = pd.DataFrame(rows)
d.to_csv('data/kakei43_long.csv', index=False)
print(d.shape, d['var'].value_counts().to_dict())
# household size
hs = d[(d.name == '世帯人員') & (d['var'] == 'exp')].pivot_table(index='grp', columns='year', values='val')
print(hs)
