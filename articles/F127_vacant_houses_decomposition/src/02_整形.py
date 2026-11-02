"""02 整形：住宅・土地統計調査（令和5年 時系列表）から都道府県×調査年のパネルを作る。
入力 data/raw/f127_hlts_timeseries.json（01_取得.md 参照）
出力 data/panel_pref.csv
"""
import json, io, csv, re
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
d = json.load(open(ROOT/'data/raw/f127_hlts_timeseries.json'))
YEARS = [2003, 2008, 2013, 2018, 2023]
JY = {2003:'平成15年',2008:'平成20年',2013:'平成25年',2018:'平成30年',2023:'令和5年'}

def rows(k):
    return list(csv.reader(io.StringIO(d[k])))

def num(x):
    x = x.replace(',', '').strip()
    return float(x) if re.fullmatch(r'-?\d+(\.\d+)?', x) else None

def pref_rows(rs):
    """都道府県の行（コード01〜47）だけを {code: [数値…]} で返す（大都市の行は除く）"""
    out = {}
    for r in rs:
        code = None; start = None
        for i, c in enumerate(r[:4]):
            m = re.match(r'^\s*(\d{2})(?:\D|$)', c.replace('　', ' '))
            if m and 1 <= int(m.group(1)) <= 47 and not re.match(r'^\d{5}', c):
                code = int(m.group(1)); start = i; break
        if code is None or code in out:
            continue
        vals = [num(c) for c in r[start+1:]]
        vals = [v for v in vals if v is not None]
        if vals:
            out[code] = vals
    return out

names = {}
for r in rows('t12__平成30年'):
    if len(r) > 2 and re.fullmatch(r'\d{2}', r[1]) and 1 <= int(r[1]) <= 47:
        names[int(r[1])] = r[2]

recs = []
def colmap(rs, cat_row_kw, cats):
    """見出し行から (分類, 年) → 列番号 を作る。分類は左から順に cats（見出しを前方に埋める）"""
    yr = next(r for r in rs if r[1] == 'Area')
    cr = next(r for r in rs if any(cat_row_kw == c.strip() for c in r))
    m = {}; cur = None; k = -1
    for j, c in enumerate(cr):
        if c.strip() and not re.match(r'^[A-Za-z]', c.strip()) and j >= 5:
            k += 1; cur = cats[k]
        if cur and j < len(yr) and re.fullmatch(r'\d{4}', yr[j].strip()):
            m[(cur, int(yr[j]))] = j
    return m

def pref_cols(rs):
    out = {}
    for r in rs:
        if len(r) > 2 and re.fullmatch(r'\d{2}', r[1].strip()) and 1 <= int(r[1]) <= 47 and int(r[1]) not in out:
            out[int(r[1])] = r
    return out
r3 = rows('t3__003'); m3 = colmap(r3, '住宅数', ['stock', 'households'])
r4 = rows('t4__総数'); m4 = colmap(r4, '賃貸用の空き家', ['vacant', 'vac_other', 'vac_rent', 'vac_sale', 'vac_second'])
t3 = pref_cols(r3); t4 = pref_cols(r4)
print(sorted(set(k[0] for k in m4)), len(m3), len(m4), len(t3), len(t4))
for y in YEARS:
    t12 = pref_rows(rows('t12__' + JY[y]))
    t22 = pref_rows(rows('t22__' + JY[y]))
    i14 = [1958,1963,1968,1973,1978,1983,1988,1993,1998,2003,2008,2013,2018,2023].index(y)
    i9 = [1983,1988,1993,1998,2003,2008,2013,2018,2023].index(y)
    for c in range(1, 48):
        a3, a4, a12, a22 = t3[c], t4[c], t12[c], t22[c]
        pop_idx = 4 if y == 2023 else 11
        recs.append(dict(
            code=c, pref=names[c], year=y,
            stock=num(a3[m3[('stock', y)]]), households=num(a3[m3[('households', y)]]),
            occupied=a12[1],
            vacant=num(a4[m4[('vacant', y)]]), vac_other=num(a4[m4[('vac_other', y)]]),
            vac_rent=num(a4[m4[('vac_rent', y)]]), vac_sale=num(a4[m4[('vac_sale', y)]]), vac_second=num(a4[m4[('vac_second', y)]]),
            hh_t22=a22[0], pop_hh=a22[pop_idx],
        ))
df = pd.DataFrame(recs)
# 整合チェック
chk = (df.vac_other + df.vac_rent + df.vac_sale + df.vac_second - df.vacant).abs() / df.vacant
assert chk.max() < 0.01, chk.max()
assert ((df.households - df.hh_t22).abs() / df.households).max() < 0.01
assert (df.occupied < df.stock).all()
df['vac_rate'] = df.vacant / df.stock
df['vac_other_rate'] = df.vac_other / df.stock
df['vac_rent_rate'] = df.vac_rent / df.stock
df['hh_size'] = df.pop_hh / df.households
df = df.drop(columns='hh_t22')
df.to_csv(ROOT/'data/panel_pref.csv', index=False)
nat = df.groupby('year')[['stock','households','occupied','vacant','vac_other','vac_rent','pop_hh']].sum()
print(nat.astype(int)); print(df.groupby('year').vac_rate.describe()[['mean','min','max']])
