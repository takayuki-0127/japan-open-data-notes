"""02 整形: FIT/FIP 都道府県別 導入件数・導入容量（新規認定分・移行認定分）を縦長の表にする。
入力: data/raw/f134_fit_quarterly.json（fit-portal A表 2017年6月末〜2026年3月末の四半期）
      data/raw/f134_fit_monthly_old.json（資源エネルギー庁 過去公表分：A表 2014年4月末・2017年3月末ほか、
                                          設備認定状況 2014年3月末＝括弧内の運転開始分）
      data/raw/f134_fit_monthly_old2.json（取得できた場合：過去公表分 A表 2014年5月〜2017年2月）
出力: data/fit_pref_long.csv（pref, date, series, value）
"""
import json, os, re, pandas as pd
RAW = 'data/raw'
PREFS = None
def labelpick(L, row, want):
    return row[L.index(want)] if want in L else None

def from_A(sheets):
    sheets = {re.sub('^表(?!A)', '表A', k): v for k, v in sheets.items()}  # 2014年5月のファイルはシート名が「表②－１」
    out = {}
    c1 = sheets.get('表A①－１'); c2 = sheets.get('表A①－２'); k1 = sheets.get('表A②－１'); k2 = sheets.get('表A②－２')
    for rows_idx in range(len(k1['rows'])):
        pref = k1['rows'][rows_idx][0]
        r = {}
        L = k1['L']; row = k1['rows'][rows_idx]
        def s(*labels, L=L, row=row):
            v = 0
            for lb in labels:
                x = labelpick(L, row, lb)
                v += float(x) if isinstance(x, (int, float)) else 0
            return v
        r['res_kw_new'] = s('太陽光発電設備/10kW未満')
        r['big_kw_new'] = s('太陽光発電設備/10kW以上')
        r['wind_kw_new'] = s('風力発電設備/20kW未満', '風力発電設備/20kW以上')
        bio = [lb for lb in L if lb.startswith('バイオマス発電設備（バイオマス比率考慮あり）')]
        r['bio_kw_new'] = s(*bio)
        r['hydro_kw_new'] = s(*[lb for lb in L if lb.startswith('水力発電設備/') and 'うち' not in lb])
        r['geo_kw_new'] = s(*[lb for lb in L if lb.startswith('地熱発電設備/')])
        # counts
        cL = c1['L']; crow = [x for x in c1['rows'] if x[0] == pref][0]
        r['res_cnt_new'] = float(labelpick(cL, crow, '太陽光発電設備/10kW未満') or 0)
        r['big_cnt_new'] = float(labelpick(cL, crow, '太陽光発電設備/10kW以上') or 0)
        if c2:
            mL = c2['L']; mrow = [x for x in c2['rows'] if x[0] == pref][0]
            r['res_cnt_mig'] = float(labelpick(mL, mrow, '太陽光発電設備/10kW未満') or 0)
        if k2:
            mL = k2['L']; mrow = [x for x in k2['rows'] if x[0] == pref][0]
            r['res_kw_mig'] = float(labelpick(mL, mrow, '太陽光発電設備/10kW未満') or 0)
            r['wind_kw_mig'] = sum(float(labelpick(mL, mrow, lb) or 0) for lb in ['風力発電設備/20kW未満', '風力発電設備/20kW以上'])
        out[pref] = r
    return out

def from_setsubi(a):
    """2014年3月末の設備認定状況：県名の行が認定、次の行（県名なし）が運転開始分。件数ブロックと容量ブロック。"""
    hdr = None; out = {}; block = 'cnt'
    if all(str(r[0]) == '' for r in a if r):  # 2012年の一部は左端に空の列がある
        a = [r[1:] for r in a]
    for i, row in enumerate(a):
        t = str(row[0])
        if '単位' in t and ('容量' in t or '出力' in t): block = 'kw'
        if len(row) > 3 and str(row[1]).startswith('太陽光（10kW未満）'):
            hdr = row
        if re.search('[都道府県]$', t) and i + 1 < len(a) and hdr:
            nxt = a[i + 1]
            col = {h: j for j, h in enumerate(hdr) if h}
            def v(name): 
                x = nxt[col[name]]; return float(x) if isinstance(x, (int, float)) else 0.0
            r = out.setdefault(t, {})
            if block == 'cnt':
                r['res_cnt_new'] = v('太陽光（10kW未満）'); r['big_cnt_new'] = v('太陽光（10kW以上）')
            else:
                r['res_kw_new'] = v('太陽光（10kW未満）'); r['big_kw_new'] = v('太陽光（10kW以上）')
                r['wind_kw_new'] = v('風力（20kW未満）') + v('風力（20kW以上）')
    return out

recs = []
q = json.load(open(f'{RAW}/f134_fit_quarterly.json'))
for r in q:
    date = f"{r['y']}-{r['m']:02d}"
    for pref, vals in from_A(r['sheets']).items():
        for k, v in vals.items(): recs.append((pref, date, k, v, 'fit-portal'))
olds = json.load(open(f'{RAW}/f134_fit_monthly_old.json'))
if os.path.exists(f'{RAW}/f134_fit_monthly_old2.json'):
    olds += json.load(open(f'{RAW}/f134_fit_monthly_old2.json'))
for r in olds:
    if r.get('err') or not r.get('sheets'): continue
    date = f"{r['ym'][:4]}-{r['ym'][4:]}"
    if r['kind'] == 'A':
        r['sheets'] = {re.sub('^表(?!A)', '表A', k): v for k, v in r['sheets'].items()}
        if '表A②－１' not in r['sheets'] or not r['sheets']['表A②－１'].get('rows'): continue
        res = from_A(r['sheets'])
    else:
        cand = [a for k, a in r['sheets'].items() if len(a) >= 50 and any('括弧内' in ''.join(map(str, x[:2])) for x in a[:10]) and '修正' not in k]
        if not cand: continue
        a = cand[0]
        res = from_setsubi(a)
    for pref, vals in res.items():
        for k, v in vals.items(): recs.append((pref, date, k, v, 'enecho-past'))
df = pd.DataFrame(recs, columns=['pref', 'date', 'series', 'value', 'source'])
df = df.drop_duplicates(['pref', 'date', 'series'])
# 2012年11月末の「運転開始」は翌月より多く、認定件数と同じ値の県が多い（移行分を含むとみられる）ため除く
df = df[df.date != '2012-11']
df.to_csv('data/fit_pref_long.csv', index=False)
print(df.groupby('series').date.agg(['min', 'max', 'nunique']))
print(df[(df.pref == '合計')].pivot(index='date', columns='series', values='value')[['res_cnt_new', 'res_kw_new', 'big_kw_new', 'wind_kw_new']].to_string())
