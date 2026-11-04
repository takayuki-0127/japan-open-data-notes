# 社会教育調査（e-Stat の Excel を CSV にした JSON）と F136 の鉄道データを、分析用の CSV に整える
import json, csv, io, re, os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'data', 'raw')
OUT = os.path.join(HERE, '..', 'data')
d = json.load(open(os.path.join(RAW, 'f194_shakai_kyoiku.json'), encoding='utf-8'))

def rows(key):
    s = list(d[key].values())[0]
    return list(csv.reader(io.StringIO(s)))

def num(x):
    x = (x or '').replace(',', '').replace('"', '').strip()
    if x in ('－', '-', '…', '', '#REF!'):
        return None
    try:
        return float(x)
    except ValueError:
        return None

ERA = {'昭和': 1925, '平成': 1988, '令和': 2018}
def fy(era, y):
    y = 1 if y == '元' else int(y)
    return ERA[era] + y

# --- 1) 年次統計：入館者数（表8, 千人）と1館当たり（表9, 人） ---
TYPES = ['総合', '科学', '歴史', '美術', '野外', '動物園', '植物園', '動植物園', '水族館']
def nen(key):
    out = []
    for r in rows(key):
        if len(r) > 3 and r[0] in ERA and '年度間' in r[2]:
            v = [num(c) for c in r[3:13]]
            out.append([fy(r[0], r[1])] + v)
    return pd.DataFrame(out, columns=['fy', '合計'] + TYPES)
vis = nen('nen8')     # 千人
per = nen('nen9')     # 人 / 館
vis.to_csv(os.path.join(OUT, 'national_visitors_by_type.csv'), index=False)
fac = vis.copy()
for c in ['合計'] + TYPES:
    fac[c] = (vis[c] * 1000 / per[c]).round()
fac.to_csv(os.path.join(OUT, 'national_facilities_by_type_derived.csv'), index=False)

# --- 2) 年次統計：施設の種類別の利用者数（表7, 千人） ---
use_cols = ['合計', '公民館', '図書館', '博物館', '博物館類似施設', '青少年教育施設', '女性教育施設', '社会体育施設', '民間体育施設', '生涯学習センター']
out = []
for r in rows('nenUse'):
    if len(r) > 3 and r[0] in ERA and '年度間' in r[2]:
        out.append([fy(r[0], r[1])] + [num(c) for c in r[3:13]])
use = pd.DataFrame(out, columns=['fy'] + use_cols)
use.to_csv(os.path.join(OUT, 'national_users_by_facility.csv'), index=False)

# --- 3) 都道府県別：博物館（登録＋相当/指定）と博物館類似施設 ---
PREF = ['北海道','青森','岩手','宮城','秋田','山形','福島','茨城','栃木','群馬','埼玉','千葉','東京','神奈川',
        '新潟','富山','石川','福井','山梨','長野','岐阜','静岡','愛知','三重','滋賀','京都','大阪','兵庫','奈良','和歌山',
        '鳥取','島根','岡山','広島','山口','徳島','香川','愛媛','高知','福岡','佐賀','長崎','熊本','大分','宮崎','鹿児島','沖縄']
REGION = {'北海道': ['北海道'], '東北': ['青森','岩手','宮城','秋田','山形','福島'],
          '関東': ['茨城','栃木','群馬','埼玉','千葉','東京','神奈川','山梨'],
          '北陸信越': ['新潟','富山','石川','長野'], '中部': ['福井','岐阜','静岡','愛知','三重'],
          '近畿': ['滋賀','京都','大阪','兵庫','奈良','和歌山'], '中国': ['鳥取','島根','岡山','広島','山口'],
          '四国': ['徳島','香川','愛媛','高知'], '九州': ['福岡','佐賀','長崎','熊本','大分','宮崎','鹿児島'], '沖縄': ['沖縄']}
P2R = {p: r for r, ps in REGION.items() for p in ps}
def norm(x):
    x = re.sub(r'\s', '', x or '')
    if x in ('北海道', '京都', '東京'):
        return x
    if x in ('京都府', '東京都'):
        return x[:2]
    return re.sub(r'[都府県]$', '', x)

def pref_table(key):
    res = {}
    after = False
    for r in rows(key):
        joined = ''.join(r)
        if '都道府県別' in joined:
            after = True
        if not after:
            continue
        name = None
        for c in r[:3]:
            n = norm(c)
            if n in PREF or n == '全国':
                name = n
                break
        if not name:
            continue
        idx = [i for i, c in enumerate(r) if norm(c) == name][0]
        cells = [c for c in r[idx + 1:] if c.strip() != '']
        vals = [num(c) if num(c) is not None else 0.0 for c in cells]
        # 並び：開館数, 特別展実施館数, 入館者総数, うち特別展, ...
        res[name] = dict(halls=vals[0], visitors=vals[2], special=vals[3] if len(vals) > 3 else None)
    return res

recs = []
for year, mk, sk in [(2017, 'h30m_p', 'h30s_p'), (2020, 'r3m_p', 'r3s_p'), (2023, 'r6m_p', 'r6s_p')]:
    for kind, key in [('博物館', mk), ('博物館類似施設', sk)]:
        t = pref_table(key)
        assert len([p for p in PREF if p in t]) == 47, (key, len(t))
        for p in PREF + ['全国']:
            v = t[p]
            recs.append(dict(fy=year, kind=kind, pref=p, region=P2R.get(p, '全国'), halls=v['halls'], visitors=v['visitors'], special=v['special']))
pref = pd.DataFrame(recs)
# 都道府県の合計と全国の値が合うか確かめる
chk = pref[pref.pref != '全国'].groupby(['fy', 'kind']).visitors.sum().reset_index().merge(
    pref[pref.pref == '全国'][['fy', 'kind', 'visitors']], on=['fy', 'kind'], suffixes=('_sum', '_nat'))
chk['diff'] = chk.visitors_sum - chk.visitors_nat
print(chk.to_string())
pref.to_csv(os.path.join(OUT, 'pref_visitors_museum_similar.csv'), index=False)

# --- 4) 鉄道（F136 と同じ鉄道輸送統計 表2-2）を年度に集計 ---
rail = pd.read_csv(os.path.join(RAW, 'f136_rail_monthly_t22.csv'))
rail['y'] = rail.ym.str[:4].astype(int); rail['m'] = rail.ym.str[5:7].astype(int)
rail['fy'] = rail.y - (rail.m < 4)
cnt = rail.groupby(['unit', 'fy']).ym.count().rename('n').reset_index()
rf = rail.groupby(['unit', 'fy'])[['teiki', 'teikigai', 'total']].sum().reset_index().merge(cnt, on=['unit', 'fy'])
rf = rf[rf.n == 12]
rf.to_csv(os.path.join(OUT, 'rail_fiscal_year.csv'), index=False)
print(rf[rf.unit == '全国'].to_string())
