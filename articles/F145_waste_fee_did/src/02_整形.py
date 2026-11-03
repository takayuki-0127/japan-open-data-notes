# 02 整形：実態調査の抽出 JSON（data/raw/f145_waste.json）を市区町村×年度のパネルにする
import json, sys, os
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = json.load(open(os.path.join(ROOT, 'data/raw/f145_waste.json'), encoding='utf-8'))
YMAP = {'h24': 2012, 'h25': 2013, 'h26': 2014, 'h27': 2015, 'h28': 2016, 'h29': 2017, 'h30': 2018,
        'r1': 2019, 'r2': 2020, 'r3': 2021, 'r4': 2022, 'r5': 2023}

def status(lbl):
    """手数料の区分 → 1=有料, 0.5=一部有料, 0=無料, nan=不明/収集なし"""
    if lbl == '有料': return 1.0
    if lbl == '一部有料': return 0.5
    if lbl == '無料': return 0.0
    return np.nan

rows = []
for y, d in raw['fee'].items():
    for code, rec in d.items():
        if code.startswith('_') or code.endswith('000') or not code.isdigit():
            continue
        name, mixed, burn = rec
        s = status(burn)
        src = '可燃'
        if np.isnan(s):           # 可燃ごみの収集がない（混合収集）なら混合ごみの区分を使う
            s = status(mixed); src = '混合'
        rows.append(dict(code=code[:5], year=YMAP[y], name_fee=name, fee=s, fee_src=src, burn_lbl=burn, mixed_lbl=mixed))
fee = pd.DataFrame(rows)

rows = []
for y, d in raw['amt'].items():
    if not d: continue
    for code, rec in d['out'].items():
        if code.endswith('000'): continue
        name, pop, tot, sei, kat, jig, rec_ = rec
        rows.append(dict(code=code[:5], year=YMAP[y], name=name, pop=pop, total_gpd=tot, seikatsu_gpd=sei,
                         katei_gpd=kat, jigyo_gpd=jig, recycle=rec_))
amt = pd.DataFrame(rows)
for c in ['pop', 'total_gpd', 'seikatsu_gpd', 'katei_gpd', 'jigyo_gpd', 'recycle']:
    amt[c] = pd.to_numeric(amt[c], errors='coerce')

panel = amt.merge(fee, on=['code', 'year'], how='left')
panel = panel.sort_values(['code', 'year']).reset_index(drop=True)
panel.to_csv(os.path.join(ROOT, 'data/panel.csv'), index=False, encoding='utf-8')
print(panel.shape, panel.year.value_counts().sort_index().to_dict())
print(panel.groupby('year').fee.value_counts(dropna=False).unstack().to_string())
