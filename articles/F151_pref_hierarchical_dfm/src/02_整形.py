"""JSON の CSV シートを 都道府県×月 の表に整える"""
import json, io, re
import pandas as pd
from pathlib import Path
B = Path(__file__).resolve().parents[1]
d = json.load(open(B/'data/raw/f151_jobs_pref.json'))
Z = str.maketrans('０１２３４５６７８９', '0123456789')
def tidy(name):
    df = pd.read_csv(io.StringIO(d[name]), header=None, dtype=str)
    cols = df.iloc[1].tolist()
    rows = []
    for _, r in df.iloc[3:].iterrows():
        y, m = r[0], r[2]
        if not isinstance(y, str) or not isinstance(m, str) or '年' not in y: continue
        ym = pd.Period(f"{int(y[:4])}-{int(m.translate(Z).replace('月','').strip())}", 'M')
        vals = {c: float(str(v).replace(',', '').strip()) for c, v in zip(cols[3:], r[3:]) if isinstance(c, str) and isinstance(v, str) and v.strip() not in ('', '-', '…')}
        vals['ym'] = ym; rows.append(vals)
    return pd.DataFrame(rows).set_index('ym').sort_index()
out = {}
for key, pat in [('offers', '第１１表ー９'), ('seekers', '第１１表ー１０'), ('ratio', '第１１表ー１２'), ('new_ratio', '第１１表ー１１'),
                 ('new_offers', '第１１表ー７'), ('w_ratio', '第１８表ー８'), ('w_offers', '第１８表ー６')]:
    name = [k for k in d if k.startswith(pat)][0]
    t = tidy(name); out[key] = t
    t.to_csv(B/f'data/{key}_sa.csv')
    print(key, t.shape, t.index.min(), t.index.max())
