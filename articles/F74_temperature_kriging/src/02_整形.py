# 気象庁の平年値（1991〜2020年）から、地点ごとの月平均気温・日最高・日最低の平年値と位置・標高の表を作る
import pandas as pd, numpy as np, io
from pathlib import Path
B = Path(__file__).resolve().parents[1]
txt = (B/'data/raw/f74_jma_normals.txt').read_text(encoding='utf-8')
st_txt, tmp_txt = txt.split('##TEMP\n')
st_txt = st_txt.replace('##STATION\n', '')
st = pd.read_csv(io.StringIO(st_txt), header=None, skiprows=2, dtype=str)
st = st.iloc[:, :15]
st.columns = ['id','name','kana','roma','lat_d','lat_m','lon_d','lon_m','alt','anemo','prec','wind','temp','sun','snow']
st = st.dropna(subset=['id'])
st['id'] = st['id'].str.strip()
st['name'] = st['name'].str.strip().str.replace('　', '')
st['lat'] = st['lat_d'].astype(float) + st['lat_m'].astype(float)/60
st['lon'] = st['lon_d'].astype(float) + st['lon_m'].astype(float)/60
st['alt'] = st['alt'].astype(float)
st = st[['id','name','lat','lon','alt']].drop_duplicates('id')
rows = []
for l in tmp_txt.strip().split('\n'):
    c = l.split(',')
    if len(c) < 32: continue
    sid, el, nyr = c[1], c[2], int(c[3])
    vals = [int(c[6+2*i]) if c[7+2*i] == '8' else np.nan for i in range(13)]
    rows.append([sid, {'0500':'mean','0600':'max','0700':'min'}[el], nyr] + vals)
cols = ['id','elem','years'] + [f'm{i}' for i in range(1,13)] + ['annual']
t = pd.DataFrame(rows, columns=cols)
for c in cols[3:]: t[c] = t[c]/10
d = t.merge(st, on='id', how='left')
d['area'] = d['id'].str[:2].astype(int)
d.to_csv(B/'data/normals_temp_long.csv', index=False)
m = d[d.elem=='mean'].dropna(subset=['annual','m1','m8','lat'])
# 同じ緯度・経度の地点が2組ある（気象台とアメダスの重複など）。クリギングの行列が特異になるので、統計年数の長いほうを残す
m = m.sort_values('years', ascending=False).drop_duplicates(['lat','lon']).sort_values('id')
m.to_csv(B/'data/normals_mean_temp.csv', index=False)
print(len(st), 'stations;', d.elem.value_counts().to_dict(), '; mean-temp stations with all values:', len(m))
print(m[['lat','lon','alt','annual','m1','m8']].describe().round(2))
