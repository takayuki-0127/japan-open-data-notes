# -*- coding: utf-8 -*-
"""夜間光（ADM2・年）と県民経済計算（総括表）を、都道府県×年のパネルに整形する。
入力: data/raw/ntl_adm2_annual_jpn.csv.gz, data/raw/kenmin_soukatu.json,
      ../F166_benford_public_stats/data/muni_2026.csv があれば面積に使う（なければ data/pref_area.csv）
出力: data/ntl_pref_year.csv, data/kenmin_pref_year.csv, data/panel.csv
"""
import json, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '..', 'data')

# 世界銀行の境界データの都道府県名（訓令式）→ 都道府県コード
KUNREI = {
 'Hokkaidoo':1,'Aomori':2,'Iwate':3,'Miyagi':4,'Akita':5,'Yamagata':6,'Hukusima':7,'Ibaraki':8,'Totigi':9,'Gunma':10,
 'Saitama':11,'Tiba':12,'Tookyoo':13,'Kanagawa':14,'Niigata':15,'Toyama':16,'Isikawa':17,'Hukui':18,'Yamanasi':19,'Nagano':20,
 'Gifu':21,'Sizuoka':22,'Aiti':23,'Mie':24,'Siga':25,'Kyooto':26,'Oosaka':27,'Hyoogo':28,'Nara':29,'Wakayama':30,
 'Tottori':31,'Simane':32,'Okayama':33,'Hirosima':34,'Yamaguti':35,'Tokusima':36,'Kagawa':37,'Ehime':38,'Kooti':39,'Hukuoka':40,
 'Saga':41,'Nagasaki':42,'Kumamoto':43,'Ooita':44,'Miyazaki':45,'Kagosima':46,'Okinawa':47}
REGION = {}
for c in range(1,2): REGION[c]='北海道'
for c in range(2,8): REGION[c]='東北'
for c in range(8,15): REGION[c]='関東'
for c in range(15,24): REGION[c]='中部'
for c in range(24,31): REGION[c]='近畿'
for c in range(31,36): REGION[c]='中国'
for c in range(36,40): REGION[c]='四国'
for c in range(40,48): REGION[c]='九州・沖縄'

ntl = pd.read_csv(os.path.join(D, 'raw', 'ntl_adm2_annual_jpn.csv.gz'))
ntl['pref'] = ntl['NAM_1'].map(KUNREI)
assert ntl['pref'].notna().all()
sumcols = ['ntl_sum', 'ntl_gf_5km_sum', 'ntl_nogf_5km_sum', 'ntl_gf_10km_sum', 'ntl_nogf_10km_sum']
g = ntl.groupby(['pref', 'year'])
p = g[sumcols].sum()
p['n_adm2'] = g.size()
# 品質の割合は ADM2 の単純平均（画素数の重みは公開されていないため）
for c in ['ntl_quality_prop_na', 'ntl_quality_prop_0_good', 'ntl_quality_prop_1_poor', 'ntl_quality_prop_2_gapfilled']:
    p[c] = g[c].mean()
p['n_gasflaring_locs'] = g['n_gasflaring_locs'].sum()
# 県内の光の集中度：上位10% ADM2 の光の割合
def top10(s):
    s = np.sort(s.values)[::-1]; k = max(1, int(round(len(s) * 0.1))); return s[:k].sum() / s.sum()
p['top10_share'] = g['ntl_sum'].apply(top10)
p = p.reset_index()
p.to_csv(os.path.join(D, 'ntl_pref_year.csv'), index=False)

kj = json.load(open(os.path.join(D, 'raw', 'kenmin_soukatu.json'), encoding='utf-8'))
recs = []
for key, v in kj.items():
    ed, tab = key.split('_')
    var = {'soukatu1': 'gdp_nom', 'soukatu2': 'gdp_real', 'soukatu9': 'pop', 'soukatu10': 'workers'}[tab]
    for row in v['rows']:
        if not row[0]:
            continue
        for y, val in zip(v['years'], row[2:]):
            if val in ('-', '', None):
                continue
            recs.append(dict(edition=int(ed), pref=int(row[0]), name=row[1], fy=y, var=var, value=float(val)))
k = pd.DataFrame(recs).pivot_table(index=['edition', 'pref', 'name', 'fy'], columns='var', values='value').reset_index()
k.to_csv(os.path.join(D, 'kenmin_pref_year.csv'), index=False)

# 面積（km2）：SSDSE-A-2026 の市区町村の総面積を都道府県で合計
area_csv = os.path.join(D, 'pref_area.csv')
muni = os.path.join(HERE, '..', '..', 'F166_benford_public_stats', 'data', 'muni_2026.csv')
if os.path.exists(muni):
    m = pd.read_csv(muni, dtype={'area_code': str})
    m['area_code'] = m['area_code'].str.lstrip('R')
    m = m[m['area_code'].str.fullmatch(r'\d{5}')]
    m['pref'] = m['area_code'].str[:2].astype(int)
    a = (m.groupby('pref')['B1101'].sum() / 100).rename('area_km2').reset_index()  # 単位は ha → km2
    a.to_csv(area_csv, index=False)
a = pd.read_csv(area_csv)

# 暦年の光（1〜12月）と年度の生産（4〜翌3月）を、同じ数字の年で合わせる（9か月重なる）
panel = k.merge(p.rename(columns={'year': 'fy'}), on=['pref', 'fy']).merge(a, on='pref')
panel['region'] = panel['pref'].map(REGION)
panel.to_csv(os.path.join(D, 'panel.csv'), index=False)
print(panel.groupby('edition').fy.agg(['min', 'max', 'count']))
print(a.head(), a.area_km2.sum())
