"""02 品目を税の区分に分け、群の指数を作る。
入力：data/cpi_items_monthly.csv.gz, data/cpi_items_meta.csv
出力：data/item_class.csv（品目・類・区分）, data/item_logidx.csv.gz（品目の 100×ln 指数）
"""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(__file__), '..', 'data')
meta = pd.read_csv(os.path.join(D, 'cpi_items_meta.csv'), dtype={'code': str})
mon = pd.read_csv(os.path.join(D, 'cpi_items_monthly.csv.gz'), dtype={'ym': str}).set_index('ym')

# 品目→直前の類（表の並び順。0157 以降は再掲の集計なので見ない）
rows, cls, big = [], None, None
BIG = {'0002': '食料', '0045': '住居', '0054': '光熱・水道', '0060': '家具・家事用品', '0082': '被服及び履物',
       '0107': '保健医療', '0111': '交通・通信', '0118': '教育', '0122': '教養娯楽', '0145': '諸雑費'}
for r in meta.itertuples():
    if r.code == '0157':
        break
    if r.code.startswith('0'):
        cls = r.code
        if r.code in BIG:
            big = r.code
        continue
    rows.append(dict(code=r.code, name=r.name, cls=cls, big=big, weight=r.weight))
it = pd.DataFrame(rows)

FOOD_EXCL = {'0041', '0042', '0043'}          # 酒類・外食・一般外食（学校給食 0044 は軽減）
NONTAX_CLS = {'0046', '0047', '0048', '0050', '0119'}   # 家賃・持家の帰属家賃・授業料等
NONTAX_ITEM = {'診療代', '教科書', '火災・地震保険料', '自動車保険料（自賠責）', '自動車保険料（任意）',
               '傷害保険料', '介護料', '行政証明書手数料', 'パスポート取得料', '自動車免許手数料', '学童保育料'}
EXCLUDE = {'保育所保育料'}                     # 2019年10月の幼児教育・保育の無償化
ENERGY = {'電気代', '都市ガス代', 'プロパンガス', '灯油', 'ガソリン'}
FRESH_CLS = {'0009', '0022', '0028'}          # 生鮮魚介・生鮮野菜・生鮮果物

def taxclass(r):
    if r['name'] in EXCLUDE:
        return '除外'
    if r['big'] == '0002' and r['cls'] not in FOOD_EXCL:
        return '軽減'
    if r['cls'] == '0135':
        return '軽減'
    if r['cls'] in NONTAX_CLS or r['name'] in NONTAX_ITEM:
        return '非課税'
    return '標準'
it['tax'] = it.apply(taxclass, axis=1)
it['energy'] = it['name'].isin(ENERGY)
it['fresh'] = it['cls'].isin(FRESH_CLS)

cols = {c.split('|')[1]: c for c in mon.columns}
it['col'] = it['code'].map(cols)
X = mon[[c for c in it['col']]].apply(pd.to_numeric, errors='coerce')
X.columns = it['code'].values
it['complete'] = X.notna().all().values & (X > 0).all().values
it.to_csv(os.path.join(D, 'item_class.csv'), index=False)
L = 100 * np.log(X.loc[:, it.loc[it.complete, 'code'].values])
L.to_csv(os.path.join(D, 'item_logidx.csv.gz'), compression='gzip')
print(it.groupby(['tax', 'complete']).size())
print(it.loc[it.complete].groupby('tax').weight.sum() / it.loc[it.complete].weight.sum())
