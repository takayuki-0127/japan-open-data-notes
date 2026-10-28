# F115 02 整形：国民生活基礎調査（令和7年）所得票 年次推移 第2・1・6・7表を、年×階級の長い表と年ごとの公表値の表にする
import re, json, pandas as pd, numpy as np
from pathlib import Path
A = Path(__file__).resolve().parents[1]; R = A/'data'/'raw'
o = json.load(open(R / 'f115_kokumin_r7.json', encoding='utf-8'))
for k in ['t01', 't02', 't06', 't07']:
    (R / f'{k}.csv').write_text(o[k], encoding='utf-8')
z2h = str.maketrans('０１２３４５６７８９', '0123456789')

def rows(name):
    import csv
    return list(csv.reader(open(R/f'{name}.csv', encoding='utf-8')))

def year_of(s):
    m = re.match(r'(\d{4})\(', s.strip()); return int(m.group(1)) if m else None

def num(s):
    try: return float(s.strip().replace(',', ''))
    except ValueError: return np.nan  # 「…」「・」（令和元年の所得は調査なし）と表題行

# 第2表：相対度数分布（％）。年は「所得の年」
r2 = rows('t02'); hdr = next(r for r in r2 if r and r[0] == '所得金額階級'); years = [year_of(c) for c in hdr[1:]]
start = next(i for i, r in enumerate(r2) if r and r[0] == '相対度数分布'); end = next(i for i, r in enumerate(r2) if r and r[0] == '累積度数分布')
recs = []
for r in r2[start+1:end]:
    lab = r[0].replace('　', '').replace(' ', '').translate(z2h)
    if not lab or lab.startswith('総'): continue
    if '未満' in lab: lo, hi = 0, int(re.findall(r'\d+', lab)[0])
    elif '以上' in lab: lo, hi = int(re.findall(r'\d+', lab)[0]), np.inf
    else: lo, hi = map(int, re.findall(r'\d+', lab)[:2])
    for y, v in zip(years, r[1:]):
        if y: recs.append(dict(year=y, lo=lo, hi=hi, share=num(v)))
bins = pd.DataFrame([r for r in recs if r['year'] <= 2024]).dropna(subset=['share']).sort_values(['year', 'lo'])
bins.to_csv(A/'data'/'bins_long.csv', index=False)

# 第1表（平均）、第6表（五分位階級の平均）、第7表（五分位値・中央値）
pub = {}
for r in rows('t01'):
    y = year_of(r[0]) if r else None
    if y and len(r) >= 2: pub.setdefault(y, {})['mean'] = num(r[1])
r6 = rows('t06'); sec = None
for r in r6:
    if r and r[0].startswith('１世帯当たり'): sec = 'hh'; continue
    if r and r[0].startswith('世帯人員'): sec = None; continue
    y = year_of(r[0]) if r else None
    if y and sec == 'hh':
        for j, v in enumerate(r[2:7], 1): pub.setdefault(y, {})[f'qmean{j}'] = num(v)
for r in rows('t07'):
    y = year_of(r[0]) if r else None
    if y and len(r) >= 6:
        for j, v in enumerate(r[1:5], 1): pub.setdefault(y, {})[f'p{20*j}'] = num(v)
        pub[y]['median'] = num(r[5])
pubdf = pd.DataFrame({y: v for y, v in pub.items() if y <= 2024}).T.rename_axis('year').reset_index().dropna(subset=['mean'])
# 五分位の所得シェア（各階級は世帯の20%）＝ 階級平均 ÷（5 × 全体平均）
for j in range(1, 6): pubdf[f'qshare{j}'] = pubdf[f'qmean{j}'] / (5 * pubdf['mean'])
pubdf.to_csv(A/'data'/'published.csv', index=False)

# 検算
chk = bins.groupby('year').share.sum()
print('years', bins.year.nunique(), 'bins/年', bins.groupby('year').size().unique(), 'share合計 範囲', chk.min(), chk.max())
print('五分位平均の平均 − 全体平均（最大の差, 万円）', (pubdf[[f'qmean{j}' for j in range(1,6)]].mean(axis=1) - pubdf['mean']).abs().max().round(2))
print(pubdf.tail(3).T)
