"""02 整形：取得した JSON を市区町村×年の表（data/panel_long.csv）にする"""
import json, numpy as np, pandas as pd
from common import ROOT, is_ward


def tidy(rows, y):
    h = rows[0]; out = []
    for r in rows[1:]:
        code, name = r[0].split('_', 1)
        rec = {'code': code, 'name': name, 'year': y}
        for c, v in zip(h[1:], r[1:]):
            k = c.split('_')[0]; v = v.replace(',', '')
            try: rec[k] = float(v)
            except ValueError: rec[k] = np.nan      # '-' は値なし
        out.append(rec)
    return pd.DataFrame(out)


def load(years=(2008, 2010, 2013, 2015)):
    d = json.load(open(ROOT / 'data/raw/ssds_municipal.json', encoding='utf-8'))
    frames = {}
    for k, rows in d.items():
        y = int(k[:4])
        if y in years:
            frames.setdefault(y, []).append(tidy(rows, y))
    out = []
    for y, fs in frames.items():
        m = fs[0]
        for f in fs[1:]:
            add = f.drop(columns=['name', 'year'])
            add = add[[c for c in add.columns if c == 'code' or c not in m.columns]]
            m = m.merge(add, on='code', how='outer')
        out.append(m)
    p = pd.concat(out, ignore_index=True)
    p = p[~p.code.apply(is_ward) & (p.code != '13100')]
    return p


if __name__ == '__main__':
    p = load()
    keep = ['code', 'name', 'year', 'A1101', 'A1405', 'A130202', 'A1303', 'A7101', 'A810105', 'B1103',
            'F110102', 'F110802', 'F2201', 'F2211', 'F2221', 'C120110', 'C120120', 'E9101', 'E9106',
            'H1101', 'H1310', 'H1320', 'H1401', 'H1403']
    p = p[[c for c in keep if c in p.columns]]
    p.to_csv(ROOT / 'data/panel_long.csv', index=False, encoding='utf-8')
    for y, g in p.groupby('year'):
        msg = f'{y} 市区町村 {g.code.nunique()}'
        if 'H1101' in g and g.H1101.notna().any():
            msg += f'  住宅の値がある {int(g.H1101.notna().sum())}（{g.H1101.isna().mean():.1%} が欠測）'
        print(msg)
