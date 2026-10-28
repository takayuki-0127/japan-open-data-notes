# 02_整形：e-Stat の表（JSON にした Excel）と、他の記事のデータから分析用の表を作る
import sys, os, json, re, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); from common import P, CATS, TEN

raw = json.load(open(P('data/raw/f114_estat_raw.json'), encoding='utf-8'))
# 検索結果の並び（01_取得.md）から statInfId → 年
IDX = dict(zip(["000040506879", "000040286464", "000040189633", "000040072780", "000027383441", "000032206118", "000032118470",
                "000031953650", "000031837106", "000031730026", "000031586410", "000031456092", "000031457330"],
               [2025, 2024, 2023, 2022, 2013, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014]))
WGT = dict(zip(["000040506880", "000027383442", "000040286465", "000040189634", "000040072781", "000032206119", "000032119310",
                "000031953654", "000031837110", "000031730030", "000031586411", "000031456032", "000030319930"],
               [2025, 2013, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014]))

def num(x):
    if isinstance(x, (int, float)): return float(x)
    return np.nan

def parse(sheet):
    """5桁の地域コード＋地域名のあとに続く12の値を取り出す（新旧どちらの様式でも使える）"""
    rows = []
    for r in sheet:
        s = [x for x in r if x is not None and not (isinstance(x, str) and x.strip() == '')]
        for i in range(len(s) - 1):
            c, nm = s[i], s[i + 1]
            if isinstance(c, str) and re.fullmatch(r'\d{5}', c.strip()) and isinstance(nm, str) and re.search(r'[぀-鿿]', nm):
                vals = s[i + 2:i + 14]
                if len(vals) == 12 and isinstance(vals[0], (int, float)):
                    rows.append([c.strip(), nm.strip()] + [num(v) for v in vals])
                break
    d = pd.DataFrame(rows, columns=['code', 'name'] + CATS).drop_duplicates('code')
    return d

def level(code):
    if code == '00000': return '全国'
    if code.startswith('000'): return '地方'
    if code.endswith('000'): return '都道府県'
    return '都市'

out = []
for kind, mp in [('index', IDX), ('weight', WGT)]:
    for sid, yr in mp.items():
        key = ('idx_' if kind == 'index' else 'w_') + sid
        d = parse(raw[key]['data'][0]); d.insert(0, 'year', yr); d.insert(0, 'table', kind)
        d['level'] = d.code.map(level); out.append(d)
        npref = (d.level == '都道府県').sum()
        assert npref == 47, (kind, yr, npref)
reg = pd.concat(out, ignore_index=True)
reg['pref'] = np.where(reg.level == '都道府県', reg.code.str[:2].astype(int), np.nan)
reg.to_csv(P('data/regional_index_long.csv'), index=False)
print('地域差指数・ウエイト', reg.groupby(['table', 'year']).size().unstack(0).to_string())

# 家計調査：住居の所有関係別の10大費目の支出（2024年）
def kakei(sheet, cols_row_key):
    hdr = next(r for r in sheet if r and '一連番号' in [x for x in r if x is not None])
    hdr = [x for x in hdr if x is not None]
    names = hdr[6:]
    rec = {}
    for r in sheet:
        s = [x for x in r if x is not None]
        for j, x in enumerate(s):
            if isinstance(x, str) and x in ['消費支出'] + TEN + ['家賃地代'] and j + 2 < len(s) and s[j + 1] == '円':
                vals = s[j + 2:j + 2 + len(names)]
                rec.setdefault(x, [num(v) for v in vals])
                break
    return pd.DataFrame(rec, index=names[:len(next(iter(rec.values())))])
k1 = kakei(raw['kakei_000040246943']['data'][0], '総世帯')
k2 = kakei(raw['kakei_000040246957']['data'][0], '平均')
k2.index = ['単身_' + i for i in k2.index]
hh = pd.concat([k1, k2])
hh = hh[hh[TEN].notna().all(axis=1)]
hh.index.name = 'type'
hh.to_csv(P('data/household_spending_2024.csv'))
print(hh[['消費支出', '住居', '家賃地代']].to_string())

# 所得
# (1) 課税対象所得 ÷ 納税義務者数：市区町村の合計を都道府県にまとめる（2015・2017・2020年、F40/F76 の表）
m = pd.read_csv(P('data/raw/f40_municipal_panel.csv'), dtype={'code': str})
g = m.groupby(['year', 'pref']).agg(taxinc=('C120110', 'sum'), taxpayers=('C120120', 'sum'), pop=('A1101', 'sum')).reset_index()
g['inc_tp'] = g.taxinc / g.taxpayers   # 千円
g['src'] = '市区町村の合計'
# (2) 都道府県の値そのもの（社会・人口統計体系 D02206：2005・2010・2013・2024年）
s = pd.read_csv(P('data/raw/ssds_pref_selected.csv'))
s = s[s.code == 'D02206'].melt(id_vars=['code', 'edition', 'year'], value_vars=[f'p{i:02d}' for i in range(1, 48)], var_name='p', value_name='inc_tp')
s['pref'] = s.p.str[1:].astype(int); s['src'] = '都道府県の値'
inc = pd.concat([g[['year', 'pref', 'inc_tp', 'taxpayers', 'src']], s[['year', 'pref', 'inc_tp', 'src']]], ignore_index=True)
# 重なる年（2005・2010）で2つの作り方が一致するか
chk = inc[inc.year.isin([2005, 2010])].pivot_table(index=['year', 'pref'], columns='src', values='inc_tp')
print('市区町村の合計と都道府県の値の差（%）:', ((chk['市区町村の合計'] / chk['都道府県の値'] - 1) * 100).abs().describe().round(3).to_dict())
inc.to_csv(P('data/income_per_taxpayer.csv'), index=False)
# (3) 1人当たり県民所得（県民経済計算、2011〜2023年度、F71 の表の v2023）
k = pd.read_csv(P('data/raw/kenmin_long_all_vintages.csv'))
k = k[k.vintage == 'v2023'][['code', 'year', 'y', 'pop']].rename(columns={'code': 'pref', 'y': 'inc_pc'})
k.to_csv(P('data/income_per_capita_kenmin.csv'), index=False)
print('県民所得', k.year.min(), k.year.max(), len(k))

# 都市（都道府県庁所在市・政令市）の課税対象所得（2020年）。東京都区部は23区の合計
mm = m[m.year == 2020].copy()
mm['ccode'] = np.where(mm.code.str.startswith('131'), '13100', mm.code)
c = mm.groupby('ccode').agg(taxinc=('C120110', 'sum'), taxpayers=('C120120', 'sum')).reset_index()
c['inc_tp'] = c.taxinc / c.taxpayers
c.to_csv(P('data/city_income_2020.csv'), index=False)
