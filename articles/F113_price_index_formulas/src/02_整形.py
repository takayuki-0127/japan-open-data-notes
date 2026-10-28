# 02_整形.py : 家計調査 年報 第5表（時系列 2002〜2024年、二人以上の世帯）の Excel から、
# 品目ごとの 年間支出金額・購入数量・平均価格 を縦長の表にする
import json, csv, io, re, os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
raw = json.load(open(os.path.join(ROOT, 'data/raw/f113_kakei_items.json'), encoding='utf-8'))

def clean(s):
    return re.sub(r'\s+', '', s or '')

def num(s):
    s = (s or '').replace(',', '').strip()
    if s in ('', '-', '…', '...', 'x', 'X', '－'): return None
    try: return float(s)
    except: return None

rows_out = []
for sid, sheets in raw.items():
    for sname, text in sheets.items():
        R = list(csv.reader(io.StringIO(text)))
        # 金額・数量・価格の行
        mk = next(i for i, r in enumerate(R) if sum('金' in c and '額' in c for c in r) >= 2)
        marks = [clean(c) for c in R[mk]]
        # コード行（"102～981" などがある行）と日本語名の行（年 月 の行）
        code_i = next(i for i in range(mk) if sum(bool(re.fullmatch(r'[0-9][0-9A-Z]{2}', clean(c))) for c in R[i]) >= 3)
        name_rows = [i for i in range(code_i + 1, mk - 6)]
        unit_i = mk - 1
        ncol = max(len(r) for r in R)
        def cell(i, j):
            return R[i][j] if j < len(R[i]) else ''
        # 日本語名：コード行の次の数行を縦に結合
        for j in range(ncol):
            if cell(mk, j) and clean(cell(mk, j)) == '金額':
                code = clean(cell(code_i, j)) or clean(cell(code_i, j + 1))
                nm = ''.join(clean(cell(i, k)) for i in range(code_i + 1, code_i + 5) for k in (j, j + 1, j + 2) if not re.fullmatch(r'[0-9A-Z･・～]*', clean(cell(i, k))))
                has_q = j + 1 < ncol and clean(cell(mk, j + 1)) == '数量'
                has_p = has_q and j + 2 < ncol and clean(cell(mk, j + 2)) == '価格'
                unit = next((clean(cell(unit_i, k)) for k in (j, j + 1, j + 2) if re.match(r'^1', clean(cell(unit_i, k)))), '')
                # 年のデータ行（最初の 2002〜2024 のブロック）
                seen = set()
                for r in R[mk + 1:]:
                    y = clean(r[7]) if len(r) > 7 else ''
                    if re.fullmatch(r'20\d\d', y) and y not in seen and (len(seen) == 0 or int(y) == max(int(s) for s in seen) + 1):
                        seen.add(y)
                        rows_out.append(dict(sheet=sname, col=j, code=code, name=nm, unit=unit, has_q=has_q, year=int(y),
                                             exp=num(r[j] if j < len(r) else ''),
                                             qty=num(r[j + 1]) if has_q and j + 1 < len(r) else None,
                                             price=num(r[j + 2]) if has_p and j + 2 < len(r) else None))
                    elif seen and re.fullmatch(r'20\d\d', y) and int(y) <= max(int(s) for s in seen):
                        break
df = pd.DataFrame(rows_out)
df.to_csv(os.path.join(ROOT, 'data/items_long_raw.csv'), index=False, encoding='utf-8')
print(df.shape, df.drop_duplicates(['sheet','col']).shape, df.year.min(), df.year.max())


# 品目（最下位の分類）で購入数量があるもの。食料と光熱（住居の家賃は除く）
df['leaf'] = df.code.fillna('').astype(str).str.fullmatch(r'[0-9][0-9A-Z]{2}')
it = df[df.leaf & df.has_q & (df.sheet != '住居')].copy()
it['price'] = it.price.where(it.price.notna(), it.exp / it.qty)  # 光熱は 金額÷数量
it = it[(it.exp > 0) & (it.price > 0)]
it['q'] = it.exp / it.price          # 価格×数量＝支出 になる「数量」（単位はそろう）
it['group'] = it.sheet.str.replace(r'（.*）', '', regex=True).replace({'世帯数分布～食料': '穀類', '光熱・水道': '光熱'})
it = it[['code', 'name', 'group', 'unit', 'year', 'exp', 'price', 'q']].sort_values(['code', 'year'])
it.to_csv(os.path.join(ROOT, 'data/items_panel.csv'), index=False, encoding='utf-8')
cov = it.groupby('code').year.agg(['min', 'max', 'count'])
print('items', it.code.nunique(), 'full 2002-2024:', (cov['count'] == 23).sum())
print(cov[cov['count'] < 23].join(it.drop_duplicates('code').set_index('code')[['name']]).to_string())
