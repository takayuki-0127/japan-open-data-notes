"""02 整形：JSON から 市区町村×年 の表（data/panel.csv）を作る
政令指定都市は市全体、東京23区は区ごと。単位：1人あたり所得は万円"""
import json, numpy as np, pandas as pd
from common import ROOT, YEARS, is_ward, is_tokyo23, PREF, BLOCK


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


d = json.load(open(ROOT / 'data/raw/ssds_municipal.json', encoding='utf-8'))
frames = []
for y in YEARS:
    b2 = tidy(d[f'{y}b2'], y)[['code', 'name', 'year', 'C120110', 'C120120']]
    b1 = tidy(d[f'{y}b1'], y)
    pop = b1[['code', 'A1101']] if 'A1101' in b1.columns and y != 2017 else pd.DataFrame({'code': b1.code, 'A1101': np.nan})
    frames.append(b2.merge(pop, on='code', how='left'))
p = pd.concat(frames, ignore_index=True)
# 政令指定都市の区は名前が「県 市 区」の3語になる（東京23区は「東京都 千代田区」の2語）。区を除き市全体を残す
p = p[(p.name.str.split().str.len() == 2) & (p.code != '13100')].copy()
p['pref'] = p.code.str[:2].astype(int)
p['pref_name'] = p.pref.map(lambda i: PREF[i - 1])
p['block'] = p.pref.map(BLOCK)
p['tokyo23'] = p.code.apply(is_tokyo23)
p['inc_tp'] = p.C120110 / p.C120120 / 10      # 納税者1人あたり（万円）
p['inc_pc'] = p.C120110 / p.A1101 / 10        # 人口1人あたり（万円）
ok = (p.C120120 > 0) & (p.C120110 > 0)
print('除いた行（納税者0・欠測）:', (~ok).sum(), p.loc[~ok, ['code', 'name', 'year']].to_string())
p = p[ok]
p.to_csv(ROOT / 'data/panel.csv', index=False, encoding='utf-8')
for y, g in p.groupby('year'):
    print(y, len(g), '課税対象所得(兆円)', round(g.C120110.sum() / 1e9, 1), '納税者(万人)', round(g.C120120.sum() / 1e4),
          '平均(万円)', round(g.C120110.sum() / g.C120120.sum() / 10, 1))
