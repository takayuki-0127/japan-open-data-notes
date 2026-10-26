"""02 整形：e-Stat 社会・人口統計体系（市区町村データ）の取得結果を、市区町村×年の表にする"""
import json, numpy as np, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def tidy(rows, y):
    h = rows[0]; out = []
    for r in rows[1:]:
        code, name = r[0].split('_', 1)
        rec = {'code': code, 'name': name, 'year': y}
        for c, v in zip(h[1:], r[1:]):
            k = c.split('_')[0]; v = v.replace(',', '')
            try: rec[k] = float(v)
            except ValueError: rec[k] = np.nan
        out.append(rec)
    return pd.DataFrame(out)

def is_ward(code):
    # 政令指定都市の区（例 01101）は除き、市全体（例 01100）を残す。東京23区は残す
    return code[2] == '1' and code[4] != '0' and code[:2] != '13'

def load():
    d = json.load(open(ROOT / 'data/raw/f16_ssds_municipal.json', encoding='utf-8'))
    frames = {}
    for k, rows in d.items():
        frames.setdefault(int(k[:4]), []).append(tidy(rows, int(k[:4])))
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
    p.to_csv(ROOT / 'data/panel_long.csv', index=False, encoding='utf-8')
    for y, g in p.groupby('year'):
        s = {c: round(g[c].sum() / 1e3) for c in ['A1101', 'A1405', 'J2506', 'J2545', 'J2546', 'F110102', 'F110802'] if c in g and g[c].notna().any()}
        print(y, g.code.nunique(), s)
