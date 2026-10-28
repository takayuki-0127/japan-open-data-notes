"""就業構造基本調査（2022年 第66表、2017年 第7表）を、男女×配偶関係×年齢×所得×就業調整（×雇用形態）の縦長の表にそろえる。"""
import csv, re, pathlib
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'data'

BINS = ['0-49', '50-99', '100-149', '150-199', '200-249', '250-299', '300-399', '400-499', '500+']

def num(x):
    x = str(x).replace(',', '').strip()
    if x in ('', '-', '…', '***', 'X', 'x'): return 0.0
    try: return float(x)
    except ValueError: return float('nan')

# ---- 2022 第66表（縦長） ----
r = list(csv.reader(open(RAW / 'shugyo2022_t66.csv', encoding='utf-8')))
types = [re.sub(r'^\d+_', '', x) for x in r[6][12:20]]
rows = []
for row in r[9:]:
    if len(row) < 20 or not row[3]: continue
    sex = re.sub(r'^\d+_', '', row[3]); mar = re.sub(r'^\d+_', '', row[5])
    age = re.sub(r'^\d+_', '', row[7]); inc = re.sub(r'^\d+_', '', row[9]); adj = re.sub(r'^\d+_', '', row[11])
    for t, v in zip(types, row[12:20]):
        rows.append(dict(year=2022, sex=sex, married=mar, age=age, income=inc, adjust=adj, emp=t, n=num(v)))
d22 = pd.DataFrame(rows)

# ---- 2017 第7表（横長: 総数/うち配偶者あり × 男女計/男/女 × 総数/している/していない） ----
r = list(csv.reader(open(RAW / 'shugyo2017_t07.csv', encoding='utf-8')))
cols = [(s, m, a) for s in ['総数', '男', '女'] for m in ['総数', 'うち配偶者あり'] for a in ['総数', '就業調整をしている', '就業調整をしていない']]
rows = []; age = None
for row in r:
    if len(row) < 9 or not row[0].strip().startswith('007'): continue
    lab = row[7].replace('　', '').replace(' ', '')
    vals = [num(v) for v in row[10:28]]
    if '歳' in lab or lab == '総数':
        age = '総数' if lab == '総数' else lab
        inc = '総数'
    else:
        inc = lab
    for (s, m, a), v in zip(cols, vals):
        rows.append(dict(year=2017, sex=s, married=m, age=age, income=inc, adjust=a, emp='総数', n=v))
d17 = pd.DataFrame(rows)

def norm_inc(x):
    x = x.replace('万円', '').replace('～', '-').replace('〜', '-')
    if '未満' in x: return '0-49'
    if '以上' in x: return '500+'
    if x == '総数': return '総数'
    return x
def norm_age(x):
    return x.replace('～', '-').replace('〜', '-')
for d in (d22, d17):
    d['income'] = d['income'].map(norm_inc)
    d['age'] = d['age'].map(norm_age)
    d['married'] = d['married'].replace({'うち配偶者あり': '配偶者あり'})
df = pd.concat([d22, d17], ignore_index=True)
df.to_csv(OUT / 'shugyo_long.csv', index=False)
print(df.groupby('year').size())
print(sorted(df.income.unique()), sorted(df.age.unique())[:5])
# 検算: 所得階級の合計 = 総数
for y in (2017, 2022):
    s = df[(df.year == y) & (df.emp == '総数') & (df.age == '総数')]
    tot = s[s.income == '総数'].set_index(['sex', 'married', 'adjust']).n
    sm = s[s.income != '総数'].groupby(['sex', 'married', 'adjust']).n.sum()
    print(y, '所得の合計/総数 の最大ずれ', float(((sm - tot) / tot).abs().max()))
