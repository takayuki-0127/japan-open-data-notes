"""02 整形：CPI（品目・財サービス分類）を年平均に、家計調査の区分別支出を CPI の中分類に対応づける。
入力：data/raw/cpi_items_long.csv, cpi_goods_services_long.csv, kakei_q5_age_2020_2025.csv,
      ../F113_price_index_formulas/data/items_panel.csv（品目別の価格と数量、F113 で整形済み）
出力：data/cpi_items_annual.csv, data/cpi_gs_annual.csv, data/cpi_items_monthly.csv.gz,
      data/hh_weights.csv, data/items_panel_f113.csv
"""
import csv, re, os, shutil
import pandas as pd

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(H, 'data', 'raw')
OUT = os.path.join(H, 'data')


def read_cpi(path):
    r = list(csv.reader(open(path, encoding='utf-8')))
    names, codes, weights = r[0], r[2], r[4]
    rows = [x for x in r[6:] if x and re.fullmatch(r'\d{6}', x[0])]
    meta = pd.DataFrame({'col': range(1, len(names)), 'name': names[1:], 'code': codes[1:],
                         'weight': [float(w) if w else float('nan') for w in weights[1:]]})
    data = {}
    for x in rows:
        data[x[0]] = [float(v) if v not in ('', '-', '…') else float('nan') for v in x[1:len(names)]]
    df = pd.DataFrame.from_dict(data, orient='index')
    df.index.name = 'ym'
    df.columns = [f'{n}|{c}' for n, c in zip(names[1:], codes[1:])]
    return meta, df


meta_i, mi = read_cpi(os.path.join(RAW, 'cpi_items_long.csv'))
meta_g, mg = read_cpi(os.path.join(RAW, 'cpi_goods_services_long.csv'))
mi = mi[mi.index >= '201501']
mg = mg[mg.index >= '201501']
mi.to_csv(os.path.join(OUT, 'cpi_items_monthly.csv.gz'), compression='gzip')
mg.to_csv(os.path.join(OUT, 'cpi_gs_monthly.csv'))
meta_i.to_csv(os.path.join(OUT, 'cpi_items_meta.csv'), index=False)
meta_g.to_csv(os.path.join(OUT, 'cpi_gs_meta.csv'), index=False)

def annual(m):
    m = m.copy()
    m['year'] = m.index.str[:4].astype(int)
    a = m.groupby('year').mean(numeric_only=True)
    cnt = m.groupby('year').size()
    return a[cnt == 12]

annual(mi).to_csv(os.path.join(OUT, 'cpi_items_annual.csv'))
annual(mg).to_csv(os.path.join(OUT, 'cpi_gs_annual.csv'))

# 家計調査：中分類（諸雑費は小分類）を CPI の類に対応づける
kk = pd.read_csv(os.path.join(RAW, 'kakei_q5_age_2020_2025.csv'), dtype=str)
MAP = {
    '1.1': '穀類', '1.2': '魚介類', '1.3': '肉類', '1.4': '乳卵類', '1.5': '野菜・海藻', '1.6': '果物',
    '1.7': '油脂・調味料', '1.8': '菓子類', '1.9': '調理食品', '1.10': '飲料', '1.11': '酒類', '1.12': '外食',
    '2.1': '持家の帰属家賃を除く家賃', '2.2': '設備修繕・維持',
    '3.1': '電気代', '3.2': 'ガス代', '3.3': '他の光熱', '3.4': '上下水道料',
    '4.1': '家庭用耐久財', '4.2': '室内装備品', '4.3': '寝具類', '4.4': '家事雑貨', '4.5': '家事用消耗品', '4.6': '家事サービス',
    '5.1': '和服', '5.2': '洋服', '5.3': 'シャツ・セーター類', '5.4': '下着類', '5.5': '他の被服', '5.6': '他の被服',
    '5.7': '履物類', '5.8': '被服関連サービス',
    '6.1': '医薬品・健康保持用摂取品', '6.2': '医薬品・健康保持用摂取品', '6.3': '保健医療用品・器具', '6.4': '保健医療サービス',
    '7.1': '交通', '7.2': '自動車等関係費', '7.3': '通信',
    '8.1': '授業料等', '8.2': '教科書・学習参考教材', '8.3': '補習教育',
    '9.1': '教養娯楽用耐久財', '9.2': '教養娯楽用品', '9.3': '書籍・他の印刷物', '9.4': '教養娯楽サービス',
    '10.1.1': '理美容サービス', '10.1.2': '理美容用品', '10.1.3': '身の回り用品', '10.1.4': 'たばこ', '10.1.5': '他の諸雑費',
}
rows = []
for (yr, tab), g0 in kk.groupby(['year', 'tab']):
    g = g0[g0.code != '00000'].drop_duplicates('code', keep='first')
    for code, cpi in MAP.items():
        hit = g[g.code == code]
        if hit.empty:
            raise SystemExit(f'missing {yr} {tab} {code}')
        h = hit.iloc[0]
        for k in ['g0', 'g1', 'g2', 'g3', 'g4', 'g5', 'g6']:
            v = h[k]
            if isinstance(v, str) and v.strip() not in ('', '-'):
                rows.append({'year': int(yr), 'tab': tab, 'kcode': code, 'kname': h['name'], 'cpi': cpi,
                             'group': k, 'yen': float(v)})
    cons = g0[g0.name == '消費支出'].iloc[0]
    for k in ['g0', 'g1', 'g2', 'g3', 'g4', 'g5', 'g6']:
        v = cons[k]
        if isinstance(v, str) and v.strip():
            rows.append({'year': int(yr), 'tab': tab, 'kcode': 'total', 'kname': '消費支出', 'cpi': '', 'group': k, 'yen': float(v)})
pd.DataFrame(rows).to_csv(os.path.join(OUT, 'hh_weights.csv'), index=False)

src = os.path.join(H, '..', 'F113_price_index_formulas', 'data', 'items_panel.csv')
shutil.copy(src, os.path.join(OUT, 'items_panel_f113.csv'))
print('ok')
