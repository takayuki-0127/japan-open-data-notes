# 森林資源の現況（2007・2012・2017・2022年3月末）の樹種別・齢級別の面積と蓄積、
# 木材統計の樹種別素材生産量を、縦長の CSV に整える
import pandas as pd, json, re, unicodedata
from pathlib import Path
R = Path(__file__).resolve().parents[1] / 'data' / 'raw'
D = Path(__file__).resolve().parents[1] / 'data'
YEARS = {'h19': 2007, 'h24': 2012, 'h29': 2017, 'r4': 2022}
SP = {'人工林': '人工林計', 'スギ': 'スギ', 'ヒノキ': 'ヒノキ', 'マツ類': 'マツ類', 'カラマツ': 'カラマツ',
      'トドマツ': 'トドマツ', 'エゾマツ': 'エゾマツ', 'その他Ｎ': '人工その他針葉樹', 'クヌギ': 'クヌギ',
      'ナラ類': 'ナラ類', 'その他Ｌ': '人工その他広葉樹', '天然林': '天然林計'}

def norm_sheet(s):
    s = s.replace('ﾞ', '')
    if s in ('人工林（5条）', '人工林(5条)'): return '人工林計_民有林'
    if s in ('人工林（7条の2）', '人工林(7条の2)'): return '人工林計_国有林'
    if '条' in s: return None
    if s == '人工林': return '人工林計'
    if s == '天然林': return '天然林計'
    if s.startswith('人工林'): return SP.get(s[3:])
    return None

rows = []
for k, y in YEARS.items():
    for kind, unit in [('ha', 'area_ha'), ('m3', 'stock_m3')]:
        f = next(R.glob(f'{k}_{kind}.xls*'))
        x = pd.ExcelFile(f)
        for s in x.sheet_names:
            sp = norm_sheet(s)
            if not sp: continue
            df = x.parse(s, header=None)
            hdr = df.iloc[4].tolist()
            cols = {}
            for j, h in enumerate(hdr):
                if pd.isna(h): continue
                t = unicodedata.normalize('NFKC', str(h)).strip()
                m = re.match(r'^(\d+)(\.0)?(\+)?$', t)
                if m: cols[j] = int(m.group(1)) if not m.group(3) else int(m.group(1))  # 最後の「21+」「19+」は上限の階級
            last = max(cols.values())
            for i in range(5, len(df)):
                name = df.iloc[i, 2]
                if pd.isna(name): continue
                name = str(name).strip()
                if name == '齢級': break
                pref = '全国' if name == '計' else name
                for j, a in cols.items():
                    v = pd.to_numeric(df.iloc[i, j], errors='coerce')
                    rows.append(dict(year=y, kind=unit, species=sp, pref=pref, age_class=a,
                                     top=(a == last), value=0.0 if pd.isna(v) else float(v)))
                if pref == '全国': break
fa = pd.DataFrame(rows)
# 上限の階級（2007・2012 は 19+、2017・2022 は 21+）をそろえ、19齢級以上を 19 にまとめる
fa['age19'] = fa['age_class'].clip(upper=19)
fa = fa.groupby(['year', 'kind', 'species', 'pref', 'age19'], as_index=False)['value'].sum().rename(columns={'age19': 'age_class'})
fa.to_csv(D / 'forest_age_class.csv', index=False)

# 木材統計：樹種別素材生産量（全国・年、千m3）
import csv, io
w = json.load(open(R / 'f142_wood.json'))
num = lambda v: pd.to_numeric(str(v).replace(',', '').replace('-', '0').strip() or 'nan', errors='coerce')
recs = []
for k in ['nat_H21', 'nat_H26', 'nat_R1', 'nat_R6']:
    base = None
    for c in csv.reader(io.StringIO(list(w[k].values())[0])):
        if not c: continue
        if c[0].startswith('対前年比'): break
        lab = unicodedata.normalize('NFKC', c[0]).replace(' ', '').replace('\u3000', '')
        m = re.match(r'^(平成|令和)?(元|\d+)年?$', lab)
        if not m or len(c) < 10: continue
        n = 1 if m.group(2) == '元' else int(m.group(2))
        if m.group(1): base = 1988 if m.group(1) == '平成' else 2018
        v = [num(x) for x in c[1:10]]
        recs.append(dict(year=base + n, total=v[0], conifer=v[1], pine=v[2], sugi=v[3], hinoki=v[4],
                         karamatsu=v[5], ezo_todo=v[6], other_conifer=v[7], broadleaf=v[8]))
wd = pd.DataFrame(recs).drop_duplicates('year', keep='last').sort_values('year')
wd.to_csv(D / 'log_production_national.csv', index=False)

# 都道府県別の素材生産量（2009・2014・2019・2024 の4年、千m3）
precs = []
for k, yr in [('pref_H21', 2009), ('pref_H26', 2014), ('pref_R1', 2019), ('pref_R6', 2024)]:
    for c in csv.reader(io.StringIO(list(w[k].values())[0])):
        if len(c) < 12: continue
        nm = next((x for x in c[:3] if x.strip()), '')
        nm = re.sub(r'\s', '', nm)
        if not nm or len(nm) > 4 or not re.match(r'^[^\d(（]+$', nm): continue
        idx = [i for i, x in enumerate(c) if i > 1 and re.match(r'^\s*([\d,]+|-)\s*$', x)]
        if len(idx) < 9: continue
        v = [num(c[i]) for i in idx[:9]]
        precs.append(dict(year=yr, pref=nm, total=v[0], conifer=v[1], sugi=v[3], hinoki=v[4], karamatsu=v[5], broadleaf=v[8]))
pp = pd.DataFrame(precs)
pp.to_csv(D / 'log_production_pref.csv', index=False)
print(fa.query("pref=='全国' and kind=='area_ha' and species=='人工林計'").pivot(index='age_class', columns='year', values='value').round(0))
print(wd)
print(pp.groupby('year').size()); print(pp.head(3))
