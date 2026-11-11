# 02 整形：相対取引価格（全銘柄平均・新潟コシヒカリ一般）、企業物価（精米・玄米）、
#          東京都区部の小売価格（うるち米 コシヒカリ・コシヒカリ以外）、全国CPI（うるち米A・B）を月次の1表にする
import pandas as pd, numpy as np, re, json, os, glob, gzip
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(B, 'data', 'raw'); OUT = os.path.join(B, 'data', 'processed'); os.makedirs(OUT, exist_ok=True)
# GitHub では Excel を raw_excel.zip にまとめて置いている。フォルダが無ければ展開する
import zipfile
if not os.path.isdir(os.path.join(RAW, 'maff_past')):
    zipfile.ZipFile(os.path.join(RAW, 'raw_excel.zip')).extractall(RAW)
idx = json.load(open(os.path.join(RAW, 'index.json')))
def num(v):
    try:
        if isinstance(v, str): v = v.replace(',', '').strip()
        return float(v)
    except Exception: return np.nan
def wa(s):  # 年産ラベル -> 西暦
    m = re.search(r'(平成|令和)(\d+|元)年産', s); n = 1 if m.group(2) == '元' else int(m.group(2))
    return (1988 if m.group(1) == '平成' else 2018) + n
# --- 相対取引価格：年産ごとの月別一覧（9月〜翌8月）
rows = []
for x in idx:
    if not re.search(r'相対取引価格（速報）（(平成|令和)', x['label']) or x['file'].endswith('.pdf'): continue
    y = wa(x['label']); d = pd.read_excel(os.path.join(RAW, x['dir'], x['file']), header=None)
    d[1] = d[1].ffill()
    def vals(r):
        v = [num(a) for a in r.values[3:]]
        v = [a for a in v if not np.isnan(a)] if False else v
        return v
    allr = d[d[1].astype(str).str.contains('全銘柄平均')].iloc[0]
    # 月の列：見出し行（「9月」を含む行）から12列を特定
    hdr = d[d.apply(lambda r: r.astype(str).str.contains('9月').any(), axis=1)].iloc[0]
    c9 = [i for i, v in enumerate(hdr.values) if '9月' in str(v)][0]; cols = list(range(c9, c9 + 12))
    kos = d[(d[1].astype(str).str.contains('新潟')) & (d[2].astype(str).str.contains('コシヒカリ')) &
            (d.apply(lambda r: '一般' in str(r[2]) + str(r[3]), axis=1))].iloc[0]
    for k, c in enumerate(cols):
        mth = pd.Timestamp(y + (1 if k >= 4 else 0), (9 + k - 1) % 12 + 1, 1)
        rows.append({'month': mth, 'crop_year': y, 'aitai_all': num(allr[c]), 'aitai_niigata_koshi': num(kos[c]), 'src': x['file']})
# 令和7年産：月ごとの速報ファイル（当月の値）
r7 = [x for x in idx if re.search(r'令和7年産米の相対取引価格・数量（(令和\d+)年(\d+)月）', x['label']) and x['file'].endswith('.xlsx')]
for x in r7:
    m = re.search(r'（令和(\d+)年(\d+)月）', x['label']); mth = pd.Timestamp(2018 + int(m.group(1)), int(m.group(2)), 1)
    d = pd.read_excel(os.path.join(RAW, x['dir'], x['file']), header=None)
    a = np.nan
    for _, r in d.iterrows():
        v = list(r.values)
        for i, c in enumerate(v):
            if '全銘柄平均価格' in str(c):
                a = [num(z) for z in v[i + 1:] if not np.isnan(num(z))][0]; break
        if not np.isnan(a): break
    k = d[(d[1].astype(str).str.contains('新潟')) & (d[2].astype(str).str.contains('コシヒカリ（一般）'))].iloc[0]
    rows.append({'month': mth, 'crop_year': 2025, 'aitai_all': a, 'aitai_niigata_koshi': num(k[3]), 'src': x['file']})
ai = pd.DataFrame(rows).dropna(subset=['aitai_all']).sort_values('month')
assert not ai['month'].duplicated().any(), ai[ai['month'].duplicated(keep=False)]
ai.to_csv(os.path.join(OUT, 'aitai_monthly.csv'), index=False)
# --- 企業物価（日本銀行）
b = pd.read_csv(os.path.join(RAW, 'boj_cgpi_rice.csv'), dtype={'date': str})
b['month'] = pd.to_datetime(b['date'], format='%Y%m'); b = b.pivot(index='month', columns='code', values='value')
b = b.rename(columns={'PRCG20_2202050002': 'cgpi_seimai', 'PRCG20_2202050001': 'cgpi_genmai', 'PRCG20_1202050002': 'cgpi_seimai_ex',
                      'PRCG20_1202050001': 'cgpi_genmai_ex', 'PRCG20_2200000000': 'cgpi_all', 'PRCG20_1200000000': 'cgpi_all_ex'})
# --- 全国CPI（F209 のデータ、2020年=100）
cpi = pd.read_csv(os.path.join(RAW, 'cpi_items_monthly.csv.gz'), usecols=['ym', 'うるち米Ａ|1001', 'うるち米Ｂ|1002', '米類|0004', '総合|0001'])
cpi['month'] = pd.to_datetime(cpi['ym'].astype(str), format='%Y%m')
cpi = cpi.rename(columns={'うるち米Ａ|1001': 'cpi_rice_a', 'うるち米Ｂ|1002': 'cpi_rice_b', '米類|0004': 'cpi_rice', '総合|0001': 'cpi_all'}).set_index('month').drop(columns='ym')
# --- 東京都区部の小売価格（小売物価統計調査 動向編 第2表、13か月分ずつの表を17本つなぐ）
rows = []
for f in sorted(glob.glob(os.path.join(RAW, 'estat_kouri', 'tokyo_*'))):
    y, me = int(re.search(r'tokyo_(\d{4})(\d\d)_', f).group(1)), int(re.search(r'tokyo_\d{4}(\d\d)_', f).group(1))
    d = pd.read_excel(f, header=None)
    hr = [i for i in range(len(d)) if any(str(v).strip() in ('1001', '1001.0') for v in d.iloc[i].values)][0]
    c1 = [j for j, v in enumerate(d.iloc[hr].values) if str(v).strip() in ('1001', '1001.0')][0]
    c2 = [j for j, v in enumerate(d.iloc[hr].values) if str(v).strip() in ('1002', '1002.0')][0]
    data = []
    for i in range(hr + 1, len(d)):
        a = pd.to_numeric(d.iat[i, c1], errors='coerce'); b2 = pd.to_numeric(d.iat[i, c2], errors='coerce')
        if f.endswith('xlsx'):
            mm = re.match(r'(\d{4})年(\d+)月', str(d.iat[i, 9]))
            if mm and not np.isnan(a): data.append((pd.Timestamp(int(mm.group(1)), int(mm.group(2)), 1), a, b2))
        elif not pd.isna(pd.to_numeric(d.iat[i, 1], errors='coerce')) and not np.isnan(a):
            data.append((None, a, b2))
    if not f.endswith('xlsx'):  # 旧形式：最後の行が表の終わりの月。13行を順に並べる
        st = pd.Timestamp(y, me, 1) - pd.DateOffset(months=len(data) - 1)
        data = [(st + pd.DateOffset(months=k), a, b2) for k, (_, a, b2) in enumerate(data)]
    rows += [{'month': t, 'tokyo_koshi_5kg': a, 'tokyo_other_5kg': b2} for t, a, b2 in data]
tk = pd.DataFrame(rows)
chk = tk.groupby('month').agg(mn=('tokyo_koshi_5kg', 'min'), mx=('tokyo_koshi_5kg', 'max'))
assert (chk.mn == chk.mx).all(), '重なる月の値が表によって違う'
tk = tk.drop_duplicates('month').set_index('month').sort_index()
# --- 1つの月次表にまとめる
df = ai.set_index('month')[['crop_year', 'aitai_all', 'aitai_niigata_koshi']].join(b, how='outer').join(cpi, how='outer').join(tk, how='outer')
df = df[df.index >= '2005-01-01']
df.to_csv(os.path.join(OUT, 'monthly_panel.csv'))
print(df.loc['2009-12':].notna().sum().to_string())
print('aitai', ai.month.min().date(), ai.month.max().date(), len(ai), '| tokyo', tk.index.min().date(), tk.index.max().date(), len(tk))
