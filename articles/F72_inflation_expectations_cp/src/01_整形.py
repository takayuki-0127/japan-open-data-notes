"""消費動向調査（物価の見通し）と消費者物価指数を整える。
入力: data/raw/f72_shouhi_price.json（e-Stat 消費動向調査 長期時系列表 2026年9月調査分をページ内で読んだもの）
      data/raw/cpi_f12.csv（F12 で取得した消費者物価指数 中分類 月次）
出力: data/expect_national.csv, data/expect_groups.csv, data/cpi_monthly.csv
"""
import json, re
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
raw = json.load(open(ROOT/'data/raw/f72_shouhi_price.json', encoding='utf-8'))

def num(x):
    if x is None or x == '' or x == '***':
        return 0.0 if x == '***' else np.nan
    try: return float(x)
    except: return np.nan

def ym(code):
    s = str(code)
    return pd.Period(f"{s[:4]}-{int(s[-2:]):02d}", 'M')

# --- 全国（7区分）
cols7 = ['d5', 'd2_5', 'd0_2', 'zero', 'u0_2', 'u2_5', 'u5', 'dk']
idx = [4, 5, 6, 10, 13, 14, 15, 19]
rows = []
for key, label in [('nation2p', '二人以上'), ('nation1p', '単身'), ('natall', '総世帯')]:
    sheet = list(raw[key]['sheets'].values())[0]
    for r in sheet:
        if r and isinstance(r[0], (int, float)) and r[0] > 2000000000:
            rec = {'hh': label, 'ym': str(ym(r[0]))}
            for c, i in zip(cols7, idx):
                rec[c] = num(r[i]) if i < len(r) else np.nan
            rows.append(rec)
nat = pd.DataFrame(rows)
nat.to_csv(ROOT/'data/expect_national.csv', index=False)

# --- 属性別（9区分。集計世帯数つき）
cols9 = ['n', 'd10', 'd5_10', 'd2_5', 'd0_2', 'zero', 'u0_2', 'u2_5', 'u5_10', 'u10', 'dk']
grow = []
for key, gtype in [('age2p', '年齢'), ('income2p', '年収')]:
    for sname, sheet in raw[key]['sheets'].items():
        head = sheet[2]
        for r in sheet:
            if r and isinstance(r[0], (int, float)) and r[0] > 2000000000:
                for j in range(3, len(head), 11):
                    g = head[j]
                    if g is None: continue
                    rec = {'type': gtype, 'sheet': sname, 'group': g, 'ym': str(ym(r[0]))}
                    for k, c in enumerate(cols9):
                        v = r[j+k] if j+k < len(r) else None
                        rec[c] = num(v)
                    grow.append(rec)
grp = pd.DataFrame(grow)
grp.to_csv(ROOT/'data/expect_groups.csv', index=False)

# --- 消費者物価指数（月次）
c = pd.read_csv(ROOT/'data/raw/cpi_f12.csv', dtype=str)
c = c[c.iloc[:, 0].str.fullmatch(r'\d{6}', na=False)]
keep = {'総合': 'all', '生鮮食品を除く総合': 'core', '生鮮食品及びエネルギーを除く総合': 'corecore', '食料': 'food'}
cpi = pd.DataFrame({'ym': [f"{s[:4]}-{s[4:]}" for s in c.iloc[:, 0]]})
for jp, en in keep.items():
    cpi[en] = pd.to_numeric(c[jp].values, errors='coerce')
cpi = cpi.set_index('ym')
for en in keep.values():
    cpi[en+'_yoy'] = (cpi[en] / cpi[en].shift(12) - 1) * 100
cpi.reset_index().to_csv(ROOT/'data/cpi_monthly.csv', index=False)
print(nat.groupby('hh').ym.agg(['min', 'max', 'count']))
print(grp.groupby(['type', 'sheet']).group.unique())
print(cpi.dropna().index.min(), cpi.index.max())
